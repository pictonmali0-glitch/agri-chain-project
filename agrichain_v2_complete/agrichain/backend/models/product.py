"""Product model for AgriChain."""

from app import db
from datetime import datetime
import uuid


class Product(db.Model):
    __tablename__ = 'products'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name         = db.Column(db.String(120), nullable=False)
    batch_number = db.Column(db.String(50), unique=True, nullable=False)
    category     = db.Column(db.String(60), nullable=True)   # maize, coffee, beans, etc.
    quantity     = db.Column(db.Float, nullable=False)
    unit         = db.Column(db.String(20), default='kg')    # kg, tonnes, bags, litres
    description  = db.Column(db.Text, nullable=True)
    origin       = db.Column(db.String(200), nullable=True)  # farm/location of harvest
    harvest_date = db.Column(db.Date, nullable=True)
    qr_code_path = db.Column(db.String(300), nullable=True)
    images       = db.Column(db.Text, nullable=True)         # JSON list of image paths
    current_location = db.Column(db.String(200), nullable=True)
    current_holder_id= db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    farmer_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    status       = db.Column(db.String(30), default='pending')
    # pending | in_transit | delivered | acknowledged | flagged
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transfers     = db.relationship('Transfer', backref='product', lazy=True)
    current_holder= db.relationship('User', foreign_keys=[current_holder_id])

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'name': self.name,
            'batch_number': self.batch_number,
            'category': self.category,
            'quantity': self.quantity,
            'unit': self.unit,
            'description': self.description,
            'origin': self.origin,
            'harvest_date': self.harvest_date.isoformat() if self.harvest_date else None,
            'qr_code_path': self.qr_code_path,
            'images': json.loads(self.images) if self.images else [],
            'current_location': self.current_location,
            'current_holder': self.current_holder.to_dict() if self.current_holder else None,
            'farmer': self.farmer.to_dict() if self.farmer else None,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<Product {self.batch_number} - {self.name}>'
