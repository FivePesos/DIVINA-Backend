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
@booking_bp.route("/bookings/<int:booking_id>", methods=["GET"])
@jwt_required
def get_booking(booking_id):
    """Get a specific booking. Users can only view their own."""
    user = request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"booking": booking.to_dict()}), 200

#/api/bookings
@booking_bp.route("/bookings", methods=["POST"])
@jwt_required
def create_booking():
    """
    Book a diving schedule.

    Request body:
    {
        "schedule_id": 1,
        "slots": 1,
        "notes": "First time diver"
    }
    """
    user = request.current_user
    data = request.get_json() or {}

    schedule_id = data.get("schedule_id")
    slots = int(data.get("slots", 1))
    notes = (data.get("notes") or "").strip() or None

    if not schedule_id:
        return jsonify({"error": "schedule_id is required"}), 400
    if slots < 1:
        return jsonify({"error": "slots must be at least 1"}), 400

    schedule = DivingSchedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404
    if schedule.is_cancelled:
        return jsonify({"error": "This schedule has been cancelled"}), 400
    if not schedule.is_active:
        return jsonify({"error": "This schedule is no longer available"}), 400

    # Check if schedule date has passed
    if schedule.date < datetime.now(timezone.utc).date():
        return jsonify({"error": "Cannot book a past schedule"}), 400

    # Check slot availability
    if schedule.is_fully_booked:
        return jsonify({
            "error": "This schedule is fully booked",
            "available_slots": 0,
        }), 400
    if slots > schedule.available_slots:
        return jsonify({
            "error": f"Not enough slots available. Only {schedule.available_slots} slot(s) left",
            "available_slots": schedule.available_slots,
        }), 400

    # Check if user already booked this schedule
    existing = Booking.query.filter_by(
        user_id=user.id,
        schedule_id=schedule_id,
        is_cancelled=False,
    ).first()
    if existing:
        return jsonify({"error": "You have already booked this schedule"}), 409

    # Create booking and decrease available slots
    booking = Booking(
        user_id=user.id,
        schedule_id=schedule_id,
        slots=slots,
        notes=notes,
    )
    schedule.booked_slots += slots
    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "message": "Booking confirmed!",
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
    """Cancel a booking and restore the slot count."""
    user = request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    if booking.is_cancelled:
        return jsonify({"error": "Booking is already cancelled"}), 400

    # Restore slots
    schedule = booking.schedule
    if schedule:
        schedule.booked_slots = max(0, schedule.booked_slots - booking.slots)

    booking.is_cancelled = True
    db.session.commit()

    return jsonify({
        "message": "Booking cancelled successfully",
        "booking": booking.to_dict(),
    }), 200