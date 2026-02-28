import jwt
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, DiveOperatorDocument, UserRole, VerificationStatus
from app.models.books import Books

auth_bp = Blueprint("api", __name__)
"""

Booking routes
    GET    /api/bookings              - list all bookings (admin) or own bookings (user)
    GET    /api/bookings/<id>         - get a specific booking
    POST   /api/bookings              - create a new booking
    PUT    /api/bookings/<id>         - update a booking
    DELETE /api/bookings/<id>         - cancel a booking
    GET    /api/bookings/my           - get current user's bookings

"""


@auth_bp.route("/books", methods=["POST"])
def get_all_bookings():
    pass