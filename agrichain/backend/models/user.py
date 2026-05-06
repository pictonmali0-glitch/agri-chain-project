"""User model for AgriChain."""

from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid


class User(db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone        = db.Column(db.String(20), nullable=True)
    password_hash= db.Column(db.String(256), nullable=False)
    role         = db.Column(db.String(20), nullable=False, default='farmer')  # farmer | receiver | admin
    is_verified  = db.Column(db.Boolean, default=False)
    profile_pic  = db.Column(db.String(300), nullable=True)
    location     = db.Column(db.String(200), nullable=True)
    fingerprint_enabled = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_login   = db.Column(db.DateTime, nullable=True)

    # Relationships
    products      = db.relationship('Product', backref='farmer', lazy=True, foreign_keys='Product.farmer_id')
    sent_transfers    = db.relationship('Transfer', backref='sender',   lazy=True, foreign_keys='Transfer.sender_id')
    received_transfers= db.relationship('Transfer', backref='receiver', lazy=True, foreign_keys='Transfer.receiver_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_verified': self.is_verified,
            'profile_pic': self.profile_pic,
            'location': self.location,
            'fingerprint_enabled': self.fingerprint_enabled,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        return data

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class OTPCode(db.Model):
    __tablename__ = 'otp_codes'

    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(120), nullable=False, index=True)
    code       = db.Column(db.String(6), nullable=False)
    purpose    = db.Column(db.String(30), nullable=False)  # registration | login | reset | verification
    is_used    = db.Column(db.Boolean, default=False)
    attempts   = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        from datetime import datetime
        return not self.is_used and datetime.utcnow() < self.expires_at and self.attempts < 5

    def __repr__(self):
        return f'<OTP {self.email} [{self.purpose}]>'
