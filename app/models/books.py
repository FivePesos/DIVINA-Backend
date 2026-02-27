from datetime import datetime, timezone
from app import db, bcrypt
from app.user import full_name

class Books(db.Model): 
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    booked_store = db.Column(db.String(120), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datatime.now(timezone.utc) )
    is_expired = db.Column(db.Boolean, default=False)


    def to_dict(self) -> dict:
        return({
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "booked_store": self.booked_store,
            "created_at": self.created_at,
            "is_expired": self.expired
        })

    def __repr__(self):
        return f"<Details: {self.full_name} {self.booked_store} {self.created_at } >"


    """
        Need pa ni e test mga gar eghegegegeg
        kay di ko ka run ani trabahoan HAHAHAHAH
    """