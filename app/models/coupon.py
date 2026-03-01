import random
import string
from datetime import datetime, timezone
from app import db

class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True) #type (e.g DIVE20 or SUMMER500)
    description = db.Column(db.String(255), nullable=True)
    discount_type = db.Column(db.String(20), nullable=False, default="percentage")
    discount_value = db.Column(db.Float, nullable=False)


    min_price = db.Column(db.Float, nullable=True, default=500)
    max_discount = db.Column(db.Float, nullable=True)

    scope = db.Column(db.String(20), nullable=False, default="global")
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("diving_schedules.id"), nullable=True)

    max_uses = db.Column(db.Integer, nullale=True)
    uses_per_user = db.Column(db.Integer, nullable=False, default=1)
    total_used = db.Column(db.Integer, nullable=False, default=0)

    valid_from = db.Column(db.DateTime, nullable=False, dafault=lambda: datetime.now(timezone.utc))
    valid_until = db.Column(db.DateTime, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    redemptions = db.relationship("CouponRedemption", backref="coupon", lazy=True)
    