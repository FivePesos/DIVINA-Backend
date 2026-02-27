import jwt
from flask import Blueprint, request, jsonify
from 
from app import db
from app.models.user import User, DiveOperatorDocument, UserRole, VerificationStatus
from app.utils.jwt_helper import generate_tokens, decode_token, jwt_required
from app.utils.file_helper import save_document

auth_bp = Blueprint("api", __name__)
#/api/books
#/api/books/{id}
#/api/make_book
#/api/delete_book



""""""
