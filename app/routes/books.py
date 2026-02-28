import jwt
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, DiveOperatorDocument, UserRole, VerificationStatus
from app.models.books import Books

auth_bp = Blueprint("api", __name__)
#/api/books
#/api/books/{id}
#/api/make_book
#/api/delete_book

@auth_bp.route("/books", methods=["POST"])
def get_all_bookings():
    pass