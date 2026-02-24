"""
Admin routes for managing dive operator verification.
Only users with role="admin" can access these endpoints.
"""


from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, UserRole, VerificationStatus
from app.utils.jwt_helper import jwt_required

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Extend @jwt_required to also require the admin role."""
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if request.current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/dive-operators", methods=["GET"])
@admin_required
def list_dive_operators():
    """List all dive operator accounts, optionally filtered by verification status."""
    status = request.args.get("status")  # pending | approved | rejected
    query = User.query.filter_by(role=UserRole.DIVE_OPERATOR)
    if status:
        query = query.filter_by(verification_status=status)
    operators = query.order_by(User.created_at.desc()).all()
    return jsonify({
        "total": len(operators),
        "dive_operators": [u.to_dict() for u in operators],
    }), 200


@admin_bp.route("/dive-operators/<int:user_id>", methods=["GET"])
@admin_required
def get_dive_operator(user_id):
    """Get full details for a specific dive operator."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404
    return jsonify({"dive_operator": user.to_dict()}), 200


@admin_bp.route("/dive-operators/<int:user_id>/approve", methods=["POST"])
@admin_required
def approve_dive_operator(user_id):
    """Approve a dive operator's account."""
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
        "message": f"Dive operator '{user.full_name}' has been approved.",
        "dive_operator": user.to_dict(),
    }), 200


@admin_bp.route("/dive-operators/<int:user_id>/reject", methods=["POST"])
@admin_required
def reject_dive_operator(user_id):
    """Reject a dive operator's account with an optional reason."""
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
        "message": f"Dive operator '{user.full_name}' has been rejected.",
        "dive_operator": user.to_dict(),
    }), 200


@admin_bp.route("/dive-operators/<int:user_id>/reset", methods=["POST"])
@admin_required
def reset_dive_operator(user_id):
    """Reset a rejected operator back to pending so they can resubmit."""
    user = User.query.filter_by(id=user_id, role=UserRole.DIVE_OPERATOR).first()
    if not user:
        return jsonify({"error": "Dive operator not found"}), 404

    user.verification_status = VerificationStatus.PENDING
    user.rejection_reason = None
    user.verified_at = None
    db.session.commit()

    return jsonify({
        "message": f"Dive operator '{user.full_name}' reset to pending.",
        "dive_operator": user.to_dict(),
    }), 200