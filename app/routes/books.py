from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from app import db
from app.models.books import Booking
from app.models.store import DivingSchedule
from app.models.user import UserRole
from app.utils.jwt_helper import jwt_required
"""
Booking routes — users book a specific diving schedule
    GET    /api/bookings              - list bookings (admin=all, user=own)
    GET    /api/bookings/my           - current user's bookings
    GET    /api/bookings/<id>         - get specific booking
    POST   /api/bookings              - create booking for a schedule
    DELETE /api/bookings/<id>         - cancel booking
"""
DEFAULT_EXPIRY_DAYS = 7
booking_bp = Blueprint("bookings", __name__)


#/api/bookings 
#list all bookings
@booking_bp.route("/bookings", methods=["GET"])
@jwt_required
def get_all_bookings():
    """Admin sees all bookings. Regular users see only their own."""
    user = request.current_user
    status = request.args.get("status")  # active | cancelled

    query = Booking.query if user.role == UserRole.ADMIN else Booking.query.filter_by(user_id=user.id)

    if status == "active":
        query = query.filter_by(is_cancelled=False)
    elif status == "cancelled":
        query = query.filter_by(is_cancelled=True)

    bookings = query.order_by(Booking.created_at.desc()).all()
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

#/api/bookings/<id>  
@booking_bp.route("/bookings/<int:booking_id>", methods=["PUT"])
@jwt_required
def update_booking(booking_id):
    """
    Update a booking's store, notes, or expiry date.
    Users can only update their own bookings.
    Cannot update expired or cancelled bookings.
    """
    user = request.current_user
    booking= Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    if booking.is_cancelled:
        return jsonify({"error": "Cannot update a cancelled booking"}), 400
    if booking.is_expired:
        return jsonify({"error": "Cannot update an expired booking"}), 400
    
    data = request.get_json() or {}

    if data.get("booked_store"):
        booking.booked_store = data["booked_store"].strip()
    if "notes" in data:
        booking.notes = data["notes"].strip() or None
    if data.get("expires_at"):
        try:
            new_expiry = datetime.fromisoformat(data["expires_at"])
            if new_expiry.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
                return jsonify({"error": "expires_at must be a future date"}), 400
            booking.expires_at = new_expiry
            booking.is_expired = False
        except ValueError:
            return jsonify({"error": "Invalid expires_at format. Use ISO format: YYYY-MM-DDTHH:MM:SS"}), 400

    db.session.commit()

    return jsonify({
        "message": "Booking updated successfully",
        "booking": booking.to_dict(),
    }), 200

@booking_bp.route("/bookings/<int:booking_id>", methods=["DELETE"])
@jwt_required
def cancel_booking(booking_id):
    """
    Cancel a booking. Users can only cancel their own.
    Admins can cancel any booking.
    """
    user =request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 403 
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access Denied"}), 403
    if booking.is_cancelled:
        return jsonify({"error": "Booking is already cancelled"}), 400
    
    booking.is_cancelled = True
    db.session.commit()

    return jsonify({
        "message": "Booking cancelled successfully",
        "booking": booking.to_dict(),
    }), 200

@booking_bp.route("/booking/my", methods=["GET"])
@jwt_required
def my_bookings():
    user = request.current_user
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()

    for b in bookings:
        b.check_and_update_expiry()
    db.session.commit()

    return jsonify({
        "total": len(bookings),
        "bookings": [b.to_dict() for b in bookings],
    }), 200