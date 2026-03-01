"""
Admin routes for managing dive operator verification.
Only users with role="admin" can access these endpoints.
"""

from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, DiveOperatorDocument, UserRole, VerificationStatus
from app.utils.jwt_helper import jwt_required

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator: requires valid JWT + admin role."""
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if request.current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ── LIST ALL DIVE OPERATORS ───────────────────────────────────────────────────

@admin_bp.route("/dive-operators", methods=["GET"])
@admin_required
def list_dive_operators():
    """
    List all dive operators with full credentials.
    Defaults to showing PENDING operators first.
    Optional: ?status=pending|approved|rejected|all
    """
    status = request.args.get("status", "pending")  # ✅ defaults to pending

    query = User.query.filter_by(role=UserRole.DIVE_OPERATOR)

    if status != "all":
        query = query.filter_by(verification_status=status)

    operators = query.order_by(User.created_at.desc()).all()

    return jsonify({
        "total": len(operators),
        "filter": status,
        "dive_operators": [_operator_detail(u) for u in operators],
    }), 200


@admin_bp.route("/dive-operators/summary", methods=["GET"])
@admin_required
def operators_summary():
    """
    Quick count summary of all operator statuses.
    Useful for admin dashboard badges.
    """
    pending  = User.query.filter_by(role=UserRole.DIVE_OPERATOR, verification_status=VerificationStatus.PENDING).count()
    approved = User.query.filter_by(role=UserRole.DIVE_OPERATOR, verification_status=VerificationStatus.APPROVED).count()
    rejected = User.query.filter_by(role=UserRole.DIVE_OPERATOR, verification_status=VerificationStatus.REJECTED).count()

    return jsonify({
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total": pending + approved + rejected,
    }), 200


@admin_bp.route("/dive-operators/<int:user_id>", methods=["GET"])
@admin_required
def get_dive_operator(user_id):
    """Get full credentials and documents for a specific dive operator."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404
    return jsonify({"dive_operator": _operator_detail(user)}), 200


# ── APPROVE ───────────────────────────────────────────────────────────────────

@admin_bp.route("/dive-operators/<int:user_id>/approve", methods=["POST"])
@admin_required
def approve_dive_operator(user_id):
    """Approve a dive operator — grants them full access."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404
    if user.verification_status == VerificationStatus.APPROVED:
        return jsonify({"error": "Dive operator is already approved"}), 400

    user.verification_status = VerificationStatus.APPROVED
    user.verified_at = datetime.now(timezone.utc)
    user.rejection_reason = None
    db.session.commit()

    return jsonify({
        "message": f"✅ {user.full_name} has been approved as a dive operator.",
        "dive_operator": _operator_detail(user),
    }), 200


# ── REJECT ────────────────────────────────────────────────────────────────────

@admin_bp.route("/dive-operators/<int:user_id>/reject", methods=["POST"])
@admin_required
def reject_dive_operator(user_id):
    """Reject a dive operator with a required reason."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404

    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "A rejection reason is required"}), 400

    user.verification_status = VerificationStatus.REJECTED
    user.rejection_reason = reason
    user.verified_at = None
    db.session.commit()

    return jsonify({
        "message": f"❌ {user.full_name} has been rejected.",
        "dive_operator": _operator_detail(user),
    }), 200


# ── RESET ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/dive-operators/<int:user_id>/reset", methods=["POST"])
@admin_required
def reset_dive_operator(user_id):
    """Reset a rejected operator back to pending."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404

    user.verification_status = VerificationStatus.PENDING
    user.rejection_reason = None
    user.verified_at = None
    db.session.commit()

    return jsonify({
        "message": f"🔄 {user.full_name} has been reset to pending.",
        "dive_operator": _operator_detail(user),
    }), 200


# ── HELPER: full operator detail ──────────────────────────────────────────────

def _operator_detail(user: User) -> dict:
    """
    Returns full operator info including personal details and documents.
    This is what the admin sees when reviewing an application.
    """
    docs = DiveOperatorDocument.query.filter_by(user_id=user.id).all()

    bir_doc  = next((d for d in docs if d.doc_type == "bir"), None)
    cert_doc = next((d for d in docs if d.doc_type == "certification"), None)

    return {
        # ── Identity ──
        "id": user.id,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,

        # ── Account ──
        "role": user.role,
        "is_active": user.is_active,
        "registered_at": user.created_at.isoformat(),

        # ── Verification ──
        "verification_status": user.verification_status,
        "verified_at": user.verified_at.isoformat() if user.verified_at else None,
        "rejection_reason": user.rejection_reason,

        # ── Documents ──
        "documents": {
            "bir": _doc_detail(bir_doc),
            "certification": _doc_detail(cert_doc),
        },
    }


def _doc_detail(doc: DiveOperatorDocument) -> dict | None:
    """Returns document details or None if not uploaded."""
    if not doc:
        return None
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "file_size_kb": round(doc.file_size / 1024, 1) if doc.file_size else None,
        "mime_type": doc.mime_type,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }