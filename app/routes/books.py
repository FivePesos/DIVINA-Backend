from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from app import db
from app.models.books import Booking
from app.models.user import UserRole
from app.utils.jwt_helper import jwt_required
"""

Booking routes
    GET    /api/bookings              - list all bookings (admin) or own bookings (user) #Done
    GET    /api/bookings/<id>         - get a specific booking #Done
    POST   /api/bookings              - create a new booking #Done
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
    status = request.args.get("status") #?status=

    if user.role == UserRole.ADMIN:
        query = Booking.query
    else:
        query = Booking.query.filter_by(user_id=user.id)

    if status == "active":
        query = query.filter_by(is_expired=False, is_cancelled=False) # returns only bookings where is_expired=False AND is_cancelled=False
    elif status == "expired":
        query = query.filter_by(is_expired=True) # returns only bookings where is_expired=True
    elif status == "cancelled":
        query = query.filter_by(is_cancelled=True) # return only booking where is_cancelled=True

    bookings = query.order_by(Booking.created_at.desc()).all()

     # Auto-update expiry status before returning
    for b in bookings:
        b.check_and_update_expiry()
    db.session.commit()

    return jsonify({
        "total": len(bookings),
        "bookings": [b.to_dict() for b in bookings],
    }), 200


#/api/bookings/<id>
@booking_bp("/bookings/<int:booking_id>", methods=["GET"])
@jwt_required
def get_booking(booking_id):
    """Get a specific booking by ID. Users can only view their own."""
    user = request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error", "Booking not found"}), 404
    
    #Only admin can view
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    
    booking.check_and_update_expiry()
    db.session.commit()
    
    return jsonify({"booking": booking.to_dict()}), 200

#/api/bookings
@booking_bp.route("/bookings", methods=["POST"])
@jwt_required
def create_booking():
    """
    Create a new booking for the logged-in user.

    Request body:
    {
        "booked_store": "Blue Sea Dive Shop",
        "notes": "Optional notes",
        "expires_at": "2024-12-31T23:59:59"  // optional, defaults to 7 days from now
    }
    """
    user = request.current_user
    data = request.get_json() or {}

    booked_store = (data.get("booked_store") or "").strip()
    notes = (data.get("notes") or "").strip()
    expires_at_str = data.get("expires_at")

    if not booked_store:
        return jsonify({"error": "booked_store is required"}), 400

    # Parse expiry date or default to 7 days from now
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Make sure expiry is in the future
            if expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
                return jsonify({"error": "expires_at must be a future date"}), 400
        except ValueError:
            return jsonify({"error": "Invalid expires_at format. Use ISO format: YYYY-MM-DDTHH:MM:SS"}), 400
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS)

    booking = Booking(
        user_id=user.id,
        booked_store=booked_store,
        notes=notes or None,
        expires_at=expires_at,
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "message": f"Booking created successfully for '{booked_store}'",
        "booking": booking.to_dict(),
    }), 201

