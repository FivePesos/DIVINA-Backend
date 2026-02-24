from datetime import datetime, timezone
from app import db, bcrypt


class UserRole:
    REGULAR = "regular"
    DIVE_OPERATOR = "dive_operator"
    ADMIN = "admin"


class VerificationStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    role = db.Column(db.String(20), nullable=False, default=UserRole.REGULAR)

    verification_status = db.Column(db.String(20), nullable=True, default=None)
    verified_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)

    documents = db.relationship(
        "DiveOperatorDocument", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_dive_operator(self) -> bool:
        return self.role == UserRole.DIVE_OPERATOR

    @property
    def is_approved(self) -> bool:
        return self.verification_status == VerificationStatus.APPROVED

    def to_dict(self) -> dict:
        base = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }
        if self.is_dive_operator:
            base.update({
                "verification_status": self.verification_status,
                "verified_at": self.verified_at.isoformat() if self.verified_at else None,
                "rejection_reason": self.rejection_reason,
                "documents": [doc.to_dict() for doc in self.documents],
            })
        return base

    def __repr__(self):                                          # ← fixed
        return f"<User {self.first_name} {self.last_name} [{self.role}]>"


class DiveOperatorDocument(db.Model):
    __tablename__ = "dive_operator_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    doc_type = db.Column(db.String(30), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "doc_type": self.doc_type,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "uploaded_at": self.uploaded_at.isoformat(),
        }

    def __repr__(self):
        return f"<DiveOperatorDocument {self.doc_type} - user {self.user_id}>"