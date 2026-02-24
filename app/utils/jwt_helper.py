import jwt
from datetime import datetime, timezone
from functools import wraps
from flask import request, jsonify, current_app
from app.models.user import User


def generate_tokens(user_id: int) -> dict:
    """Generate access and refresh tokens for a user."""
    now = datetime.now(timezone.utc)

    access_payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
        "type": "access",
    }

    refresh_payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
        "type": "refresh",
    }

    access_token = jwt.encode(
        access_payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    refresh_token = jwt.encode(
        refresh_payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }


def decode_token(token: str, token_type: str = "access") -> dict:
    """Decode and validate a JWT token."""
    payload = jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=["HS256"],
    )
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def jwt_required(f):
    """Decorator to protect routes with JWT access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token, token_type="access")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Access token has expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        user = User.query.get(payload["sub"])
        if not user or not user.is_active:
            return jsonify({"error": "User not found or inactive"}), 401

        request.current_user = user
        return f(*args, **kwargs)

    return decorated