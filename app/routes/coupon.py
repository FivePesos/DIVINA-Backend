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