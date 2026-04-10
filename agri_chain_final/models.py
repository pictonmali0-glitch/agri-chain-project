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
    role = db.Column(db.String(20), nullable=False)  # farmer, buyer, transporter, regulator, admin
    is_active = db.Column(db.Boolean, default=True)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    quality_grade = db.Column(db.String(10), default='A')
    status = db.Column(db.String(30), default='harvested')
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blockchain_hash = db.Column(db.String(64))
    is_flagged = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    current_owner = db.relationship('User', foreign_keys=[current_owner_id])
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


def seed_data():
    if User.query.count() > 0:
        return

    users = [
        User(name='Admin User', email='admin@agrichain.ug', password=generate_password_hash('admin123'), role='admin', location='Kampala'),
        User(name='John Muhindo', email='farmer@agrichain.ug', password=generate_password_hash('farmer123'), role='farmer', location='Kasese', phone='+256700000001'),
        User(name='Grace Birungi', email='buyer@agrichain.ug', password=generate_password_hash('buyer123'), role='buyer', location='Kampala', phone='+256700000002'),
        User(name='David Bwambale', email='transporter@agrichain.ug', password=generate_password_hash('transport123'), role='transporter', location='Kasese', phone='+256700000003'),
        User(name='Dr. Ruth Kyomugisha', email='regulator@agrichain.ug', password=generate_password_hash('regulator123'), role='regulator', location='Kampala', phone='+256700000004'),
        User(name='Peter Kato', email='farmer2@agrichain.ug', password=generate_password_hash('farmer123'), role='farmer', location='Kasese', phone='+256700000005'),
    ]
    db.session.add_all(users)
    db.session.flush()

    from blockchain import Blockchain
    bc = Blockchain()

    products_data = [
        ('Maize', 500, 'Hima, Kasese', '2024-03-15', 'A', 'delivered'),
        ('Coffee', 200, 'Kilembe, Kasese', '2024-03-10', 'A+', 'approved'),
        ('Beans', 150, 'Bugoye, Kasese', '2024-03-20', 'B', 'in_transit'),
        ('Tomatoes', 80, 'Maliba, Kasese', '2024-03-22', 'A', 'harvested'),
        ('Maize', 300, 'Rukoki, Kasese', '2024-03-18', 'A', 'transferred'),
        ('Sorghum', 120, 'Kisinga, Kasese', '2024-03-12', 'B+', 'delivered'),
    ]

    from datetime import date
    for i, (crop, qty, loc, hdate, grade, status) in enumerate(products_data):
        farmer_id = users[1].id if i % 2 == 0 else users[5].id
        p = Product(
            product_code=f'PC-2024-{str(i+1).zfill(4)}',
            crop_type=crop, quantity=qty, unit='kg',
            location=loc, district='Kasese',
            harvest_date=date.fromisoformat(hdate),
            quality_grade=grade, status=status,
            farmer_id=farmer_id,
            current_owner_id=users[2].id if status in ['delivered', 'approved'] else farmer_id,
            is_approved=(status == 'approved'),
            notes=f'Sample {crop} harvest from Kasese district'
        )
        db.session.add(p)
        db.session.flush()

        block = bc.add_block({'action': 'harvested', 'product_id': p.id, 'crop': crop, 'farmer': users[farmer_id - 1].name if farmer_id <= len(users) else 'Farmer'})
        p.blockchain_hash = block.hash

        tx = Transaction(
            tx_id=f'TX{p.id:04d}A',
            product_id=p.id,
            action='harvested',
            sender_id=farmer_id,
            block_index=block.index,
            block_hash=block.hash,
            previous_hash=block.previous_hash,
            payload=f'{{"crop":"{crop}","qty":{qty},"location":"{loc}"}}'
        )
        db.session.add(tx)

    db.session.commit()
