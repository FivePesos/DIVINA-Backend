"""
Booking routes — users book a specific diving schedule
    GET    /api/bookings              - list bookings (admin=all, user=own)
    GET    /api/bookings/my           - current user's bookings
    GET    /api/bookings/<id>         - get specific booking
    POST   /api/bookings              - create booking for a schedule
    DELETE /api/bookings/<id>         - cancel booking
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from app import db
from app.models.books import Booking 
from app.models.store import DivingSchedule
from app.models.coupon import Coupon, CouponRedemption
from app.models.user import UserRole
from app.utils.jwt_helper import jwt_required

booking_bp = Blueprint("bookings", __name__)


# GET /api/bookings
@booking_bp.route("/bookings", methods=["GET"])
@jwt_required
def get_all_bookings():
    """Admin sees all bookings. Regular users see only their own."""
    user   = request.current_user
    status = request.args.get("status")  

    query = Booking.query if user.role == UserRole.ADMIN \
            else Booking.query.filter_by(user_id=user.id)

    if status == "active":
        query = query.filter_by(is_cancelled=False)
    elif status == "cancelled":
        query = query.filter_by(is_cancelled=True)

    bookings = query.order_by(Booking.created_at.desc()).all()
    return jsonify({
        "total":    len(bookings),
        "bookings": [b.to_dict() for b in bookings],
    }), 200


# GET /api/bookings/my
@booking_bp.route("/bookings/my", methods=["GET"])
@jwt_required
def my_bookings():
    """Get current logged-in user's bookings."""
    bookings = Booking.query.filter_by(
        user_id=request.current_user.id
    ).order_by(Booking.created_at.desc()).all()

    return jsonify({
        "total":    len(bookings),
        "bookings": [b.to_dict() for b in bookings],
    }), 200


# GET /api/bookings/<id>
@booking_bp.route("/bookings/<int:booking_id>", methods=["GET"])
@jwt_required
def get_booking(booking_id):
    """Get a specific booking. Users can only view their own."""
    user    = request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"booking": booking.to_dict()}), 200


# POST /api/bookings
@booking_bp.route("/bookings", methods=["POST"])
@jwt_required
def create_booking():
    """
    Book a diving schedule, optionally with a coupon code.

    Request body:
    {
        "schedule_id": 1,
        "slots":       1,
        "notes":       "First time diver",
        "coupon_code": "DIVE20"    // optional
    }
    """
    user = request.current_user
    data = request.get_json() or {}

    schedule_id = data.get("schedule_id")
    slots       = int(data.get("slots", 1))
    notes       = (data.get("notes") or "").strip() or None
    coupon_code = (data.get("coupon_code") or "").strip().upper() or None

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
    if schedule.date < datetime.now(timezone.utc).date():
        return jsonify({"error": "Cannot book a past schedule"}), 400
    if schedule.is_fully_booked:
        return jsonify({"error": "This schedule is fully booked", "available_slots": 0}), 400
    if slots > schedule.available_slots:
        return jsonify({
            "error": f"Only {schedule.available_slots} slot(s) left",
            "available_slots": schedule.available_slots,
        }), 400

    # Prevent duplicate booking
    existing = Booking.query.filter_by(
        user_id=user.id, schedule_id=schedule_id, is_cancelled=False
    ).first()
    if existing:
        return jsonify({"error": "You have already booked this schedule"}), 409

    # ── COUPON ────────────────────────────────────────────────────────────────
    original_price   = schedule.price * slots
    discount_applied = 0.0
    final_price      = original_price
    coupon           = None

    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if not coupon:
            return jsonify({"error": f"Coupon '{coupon_code}' not found"}), 404
        if not coupon.is_valid:
            return jsonify({"error": "This coupon is invalid, expired, or exhausted"}), 400
        if coupon.scope == "store" and schedule.store_id != coupon.store_id:
            return jsonify({"error": "This coupon is only valid for a specific store"}), 400
        if coupon.scope == "schedule" and schedule.id != coupon.schedule_id:
            return jsonify({"error": "This coupon is only valid for a specific schedule"}), 400
        if coupon.min_price and original_price < coupon.min_price:
            return jsonify({"error": f"Minimum booking of ₱{coupon.min_price:,.2f} required"}), 400

        user_uses = CouponRedemption.query.filter_by(
            coupon_id=coupon.id, user_id=user.id
        ).count()
        if user_uses >= coupon.uses_per_user:
            return jsonify({"error": "You have already used this coupon the maximum number of times"}), 400

        discount_applied = coupon.compute_discount(original_price)
        final_price      = round(original_price - discount_applied, 2)

    # ── CREATE BOOKING ────────────────────────────────────────────────────────
    booking = Booking(
        user_id          = user.id,
        schedule_id      = schedule_id,
        slots            = slots,
        notes            = notes,
        original_price   = original_price,
        discount_applied = discount_applied,
        final_price      = final_price,
    )
    schedule.booked_slots += slots
    db.session.add(booking)
    db.session.flush()

    if coupon:
        redemption = CouponRedemption(
            coupon_id        = coupon.id,
            user_id          = user.id,
            booking_id       = booking.id,
            original_price   = original_price,
            discount_applied = discount_applied,
            final_price      = final_price,
        )
        coupon.total_used += 1
        db.session.add(redemption)

    db.session.commit()

    response = {
        "message": "Booking confirmed! 🤿",
        "booking": booking.to_dict(),
    }
    if coupon:
        response["coupon_applied"] = {
            "code":             coupon.code,
            "original_price":   original_price,
            "discount_applied": discount_applied,
            "final_price":      final_price,
            "savings":          f"You saved ₱{discount_applied:,.2f}!",
        }

    return jsonify(response), 201


# DELETE /api/bookings/<id>
@booking_bp.route("/bookings/<int:booking_id>", methods=["DELETE"])
@jwt_required
def cancel_booking(booking_id):
    """Cancel a booking and restore the slot count."""
    user    = request.current_user
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if user.role != UserRole.ADMIN and booking.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    if booking.is_cancelled:
        return jsonify({"error": "Booking is already cancelled"}), 400

    # Restore slots back to schedule
    if booking.schedule:
        booking.schedule.booked_slots = max(
            0, booking.schedule.booked_slots - booking.slots
        )

    booking.is_cancelled = True
    db.session.commit()

    return jsonify({
        "message": "Booking cancelled successfully",
        "booking": booking.to_dict(),
    }), 200