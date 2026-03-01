import jwt
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, DiveOperatorDocument, UserRole, VerificationStatus
from app.utils.jwt_helper import generate_tokens, decode_token, jwt_required
from app.utils.file_helper import save_document

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    #For debugging
    print("=== SIGNUP HIT ===")
    print("CONTENT TYPE:", request.content_type)
    print("FORM DATA:", request.form)
    print("FILES:", request.files)

    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    data = request.form if is_multipart else (request.get_json() or {})

    first_name = (data.get("first_name") or "").strip()
    last_name  = (data.get("last_name")  or "").strip()
    email      = (data.get("email")      or "").strip().lower()
    password   =  data.get("password")   or ""

    validation_error = check_if_empty(first_name, last_name, email, password)
    if validation_error:
        return validation_error

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    is_dive_operator = str(data.get("is_dive_operator", "false")).lower() in ("true", "1", "yes")

    if is_dive_operator:
        return _signup_dive_operator( first_name, last_name, email, password)  
    else:
        return _signup_regular(first_name, last_name, email, password)           

def check_if_empty(first_name: str, last_name: str, email:str, password:str):
    if not first_name or not last_name or not email or not password:
        return (jsonify({"error": "first name, last name, email, and password are required"}), 400)
    if len(first_name) < 2 or len(last_name) < 2:
        return (jsonify({"error": "First and last name must be at least 2 characters"}), 400)
    if len(password) < 6:
        return (jsonify({"error": "Password must be at least 6 characters"}), 400)
    if "@" not in email:
        return (jsonify({"error": "Invalid email address"}), 400)
    return None

def _signup_regular(first_name: str, last_name: str, email: str, password: str):
    user = User(
        first_name=first_name,
        last_name=last_name,   
        email=email,
        role=UserRole.REGULAR,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    tokens = generate_tokens(user.id)
    return jsonify({
        "message": "Account created successfully",
        "user": user.to_dict(),
        **tokens,
    }), 201


def _signup_dive_operator(first_name: str, last_name: str, email: str, password: str):  

    # For debugging ra
    print("FILES RECEIVED:", request.files) 
    print("FORM DATA:", request.form)  

    bir_file  = request.files.get("bir_document")
    cert_file = request.files.get("certification_document")
    
    
    if not bir_file:
        return jsonify({"error": "bir_document is required for dive operator registration"}), 400
    if not cert_file:
        return jsonify({"error": "certification_document is required for dive operator registration"}), 400

    try:
        bir_info = save_document(bir_file, "bir")
    except ValueError as e:
        return jsonify({"error": f"BIR document: {str(e)}"}), 400

    try:
        cert_info = save_document(cert_file, "certification")
    except ValueError as e:
        return jsonify({"error": f"Certification document: {str(e)}"}), 400

    user = User(
        first_name=first_name,   
        last_name=last_name,
        email=email,
        role=UserRole.DIVE_OPERATOR,
        verification_status=VerificationStatus.PENDING,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    bir_doc = DiveOperatorDocument(user_id=user.id, doc_type="bir", **bir_info)
    cert_doc = DiveOperatorDocument(user_id=user.id, doc_type="certification", **cert_info)
    db.session.add(bir_doc)
    db.session.add(cert_doc)
    db.session.commit()

    tokens = generate_tokens(user.id)
    return jsonify({
        "message": (
            "Dive operator account created. Your documents are under review. "
            "You will be notified once your account is approved."
        ),
        "user": user.to_dict(),
        **tokens,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login with email and password.
    Dive operators get a warning in the response if pending or rejected.
    """
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password =  data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403

    extra = {}
    if user.is_dive_operator:
        if user.verification_status == VerificationStatus.PENDING:
            extra["warning"] = "Your dive operator account is still pending admin verification."
            extra["verification_status"] = VerificationStatus.PENDING
        elif user.verification_status == VerificationStatus.REJECTED:
            extra["warning"] = (
                f"Your dive operator account was rejected: "
                f"{user.rejection_reason or 'No reason provided.'}"
            )
            extra["verification_status"] = VerificationStatus.REJECTED
        elif user.verification_status == VerificationStatus.APPROVED:
            extra["verification_status"] = VerificationStatus.APPROVED

    tokens = generate_tokens(user.id)
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        **tokens,
        **extra,
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Issue a new access token using a valid refresh token."""
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    try:
        payload = decode_token(refresh_token, token_type="refresh")
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token has expired, please log in again"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid refresh token: {str(e)}"}), 401

    user = User.query.get(payload["sub"])
    if not user or not user.is_active:
        return jsonify({"error": "User not found or inactive"}), 401

    tokens = generate_tokens(user.id)
    return jsonify({"message": "Token refreshed successfully", **tokens}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    return jsonify({"user": request.current_user.to_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    return jsonify({"message": "Logged out successfully. Please discard your tokens."}), 200