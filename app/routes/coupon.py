
"""
Coupon routes

Admin:
  POST   /api/admin/coupons              - create coupon
  GET    /api/admin/coupons              - list all coupons
  GET    /api/admin/coupons/<id>         - get coupon detail + redemptions
  PUT    /api/admin/coupons/<id>         - update coupon
  DELETE /api/admin/coupons/<id>         - deactivate coupon
  POST   /api/admin/coupons/generate     - auto-generate bulk coupon codes

Public (authenticated user):
  POST   /api/coupons/validate           - check if a coupon is valid for a booking
"""

import random
import string
from datetime import datetime,timezone
from flask import Blueprint, request, jsonify
from app import db
from app.models.coupon import Coupon, CouponRedemption, generate_coupon_code
from app.models.store import DivingSchedule
from app.models.user import UserRole
from app.utils.jwt_helper import jwt_required
from functools import wraps

coupon_bp = Blueprint("coupons", __name__)
admin_coupon_bp = Blueprint("admin_coupon_bp", __name__)