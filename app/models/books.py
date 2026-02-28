"""
Booking model — tracks who booked, what store, when it expires.
"""

from datetime import datetime, timezone, timedelta
from app import db


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    booked_store = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)  
    is_expired = db.Column(db.Boolean, default=False)
    is_cancelled = db.Column(db.Boolean, default=False)
    user = db.relationship("User", backref=db.backref("bookings", lazy=True))

    @property
    def is_active(self) -> bool:
        """Booking is active if not cancelled, not expired, and expiry hasn't passed."""
        if self.is_cancelled or self.is_expired:
            return False
        return datetime.now(timezone.utc) < self.expires_at.replace(tzinfo=timezone.utc)

    def check_and_update_expiry(self):
        """Auto-mark as expired if expiry date has passed."""
        if not self.is_expired and not self.is_cancelled:
            if datetime.now(timezone.utc) >= self.expires_at.replace(tzinfo=timezone.utc):
                self.is_expired = True

    def to_dict(self) -> dict:
        self.check_and_update_expiry()
        return {
            "id": self.id,
            "user_id": self.user_id,
            "booked_by": self.user.full_name if self.user else None,
            "email": self.user.email if self.user else None,
            "booked_store": self.booked_store,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_cancelled": self.is_cancelled,
        }

    def __repr__(self):
        return f"<Booking {self.id}: {self.user_id} → {self.booked_store} (expires: {self.expires_at})>"