from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # WebAuthn / biometric login
    webauthn_credential_id = db.Column(db.Text, nullable=True)
    webauthn_public_key    = db.Column(db.Text, nullable=True)
    webauthn_sign_count    = db.Column(db.Integer, default=0)

    products = db.relationship('Product', backref='farmer', lazy=True, foreign_keys='Product.farmer_id')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'email': self.email,
            'role': self.role, 'is_active': self.is_active,
            'phone': self.phone, 'location': self.location,
            'created_at': self.created_at.isoformat()
        }


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(20), unique=True, nullable=False)
    crop_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='kg')
    location = db.Column(db.String(100))
    district = db.Column(db.String(100), default='Kasese')
    harvest_date = db.Column(db.Date)
    quality_grade = db.Column(db.String(10), default='Pending')
    status = db.Column(db.String(30), default='harvested')
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Buyer who tapped "Buy" — farmer may transfer only to this user while status is harvested.
    purchase_requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    current_owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blockchain_hash = db.Column(db.String(64))
    is_flagged = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    image_data = db.Column(db.Text, nullable=True)
    # ── Price system ──
    price_per_kg = db.Column(db.Float, nullable=True)        # farmer sets this
    resale_price_per_kg = db.Column(db.Float, nullable=True) # buyer/distributor sets this
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    current_owner = db.relationship('User', foreign_keys=[current_owner_id])
    purchase_requester = db.relationship('User', foreign_keys=[purchase_requested_by_id])
    purchase_requests = db.relationship(
        'PurchaseRequest', backref='product', lazy='dynamic', cascade='all, delete-orphan'
    )
    transactions = db.relationship('Transaction', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'product_code': self.product_code,
            'crop_type': self.crop_type, 'quantity': self.quantity,
            'unit': self.unit, 'location': self.location,
            'district': self.district,
            'harvest_date': self.harvest_date.isoformat() if self.harvest_date else None,
            'quality_grade': self.quality_grade, 'status': self.status,
            'farmer_id': self.farmer_id, 'blockchain_hash': self.blockchain_hash,
            'is_flagged': self.is_flagged, 'is_approved': self.is_approved,
            'has_image': self.image_data is not None,
            'price_per_kg': self.price_per_kg,
            'resale_price_per_kg': self.resale_price_per_kg,
            'created_at': self.created_at.isoformat()
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    tx_id = db.Column(db.String(64), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    block_index = db.Column(db.Integer)
    block_hash = db.Column(db.String(64))
    previous_hash = db.Column(db.String(64))
    payload = db.Column(db.Text)
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

    def to_dict(self):
        return {
            'id': self.id, 'tx_id': self.tx_id,
            'product_id': self.product_id, 'action': self.action,
            'sender': self.sender.name if self.sender else 'System',
            'receiver': self.receiver.name if self.receiver else 'System',
            'block_index': self.block_index, 'block_hash': self.block_hash,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp.isoformat()
        }


class Block(db.Model):
    __tablename__ = 'blocks'
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer, unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.Text)
    previous_hash = db.Column(db.String(64))
    hash = db.Column(db.String(64), unique=True)
    nonce = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])



class PurchaseRequest(db.Model):
    """Multiple buyers can request the same listing; farmer accepts one or rejects requests."""
    __tablename__ = 'purchase_requests'
    __table_args__ = (
        db.UniqueConstraint('product_id', 'buyer_id', name='uq_purchase_request_product_buyer'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buyer = db.relationship('User', foreign_keys=[buyer_id])


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'link': self.link,
            'created_at': self.created_at.isoformat()
        }

def seed_data():
    """
    Ensures all test accounts exist with the correct passwords.
    Safe to run on every startup — upserts by email instead of
    checking total user count, so existing data is never wiped.
    """
    test_users = [
        {'name': 'Admin User',         'email': 'admin@agrichain.ug',       'password': 'admin123',      'role': 'admin',       'location': 'Kampala'},
        {'name': 'John Muhindo',        'email': 'farmer@agrichain.ug',      'password': 'farmer123',     'role': 'farmer',      'location': 'Kasese',  'phone': '+256700000001'},
        {'name': 'Grace Birungi',       'email': 'buyer@agrichain.ug',       'password': 'buyer123',      'role': 'buyer',       'location': 'Kampala', 'phone': '+256700000002'},
        {'name': 'David Bwambale',      'email': 'transporter@agrichain.ug', 'password': 'transport123',  'role': 'transporter', 'location': 'Kasese',  'phone': '+256700000003'},
        {'name': 'Dr. Ruth Kyomugisha', 'email': 'regulator@agrichain.ug',   'password': 'regulator123',  'role': 'regulator',   'location': 'Kampala', 'phone': '+256700000004'},
        {'name': 'Peter Kato',          'email': 'farmer2@agrichain.ug',     'password': 'farmer123',     'role': 'farmer',      'location': 'Kasese',  'phone': '+256700000005'},
    ]

    for u in test_users:
        existing = User.query.filter_by(email=u['email']).first()
        if existing:
            # Reset password in case it got corrupted
            existing.password = generate_password_hash(u['password'])
            existing.is_active = True
        else:
            new_user = User(
                name=u['name'],
                email=u['email'],
                password=generate_password_hash(u['password']),
                role=u['role'],
                location=u.get('location', ''),
                phone=u.get('phone', ''),
            )
            db.session.add(new_user)

    db.session.commit()
    print("Seed: test accounts verified/created.")