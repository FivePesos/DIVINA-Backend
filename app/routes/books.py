from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from app import db
from app.models.books import Booking
from app.models.user import UserRole
from app.utils.jwt_helper import jwt_required
"""

Booking routes
    GET    /api/bookings              - list all bookings (admin) or own bookings (user) 
    GET    /api/bookings/<id>         - get a specific booking
    POST   /api/bookings              - create a new booking
    PUT    /api/bookings/<id>         - update a booking
    DELETE /api/bookings/<id>         - cancel a booking
    GET    /api/bookings/my           - get current user's bookings

"""
DEFAULT_EXPIRY_DAYS = 7
booking_bp = Blueprint("bookings", __name__)


#/api/bookings 
#list all bookings
@booking_bp.route("/bookings", methods=["GET"])
def get_all_bookings():
    """
    Admin: returns all bookings.
    Regular user / dive operator: returns only their own bookings.
    """
    user = request.current_user
    status = request.args.get("status")

    if user.role == UserRole.ADMIN:
        query = Booking.query
    else:
        query = Booking.query.filter_by(user_id=user.id)

    if status == "active":
        query = query.filter_by(is_expired=False, is_cancelled=False)
    elif status == "expired":
        query = query.filter_by(is_expired=True)
    elif status == "cancelled":
        query = query.filter_by(is_cancelled=True)

    bookings = query.order_by(Booking.created_at.desc()).all()

    for b in bookings:
        b.check_and_update_expiry()
    db.session.commit()

    return jsonify({
        "total": len(bookings),
        "bookings": [b.to_dict() for b in bookings],
    }), 200


