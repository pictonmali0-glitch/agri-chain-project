"""Transfer and BlockchainBlock models for AgriChain."""

from app import db
from datetime import datetime
import uuid
import hashlib
import json


class Transfer(db.Model):
    __tablename__ = 'transfers'

    id              = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id      = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    sender_id       = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    receiver_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    from_location   = db.Column(db.String(200), nullable=True)
    to_location     = db.Column(db.String(200), nullable=True)
    quantity_sent   = db.Column(db.Float, nullable=False)
    quantity_received = db.Column(db.Float, nullable=True)
    unit            = db.Column(db.String(20), default='kg')
    status          = db.Column(db.String(30), default='pending')
    # pending | in_transit | delivered | acknowledged | rejected
    transfer_type   = db.Column(db.String(40), default='transfer')
    # transfer | collection | warehouse | final_delivery
    note            = db.Column(db.Text, nullable=True)
    acknowledgement_note = db.Column(db.Text, nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    is_suspicious   = db.Column(db.Boolean, default=False)
    suspicious_reason = db.Column(db.String(300), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Blockchain reference
    block_hash      = db.Column(db.String(64), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product': self.product.to_dict() if self.product else None,
            'sender': self.sender.to_dict() if self.sender else None,
            'receiver': self.receiver.to_dict() if self.receiver else None,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'quantity_sent': self.quantity_sent,
            'quantity_received': self.quantity_received,
            'unit': self.unit,
            'status': self.status,
            'transfer_type': self.transfer_type,
            'note': self.note,
            'acknowledgement_note': self.acknowledgement_note,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'is_suspicious': self.is_suspicious,
            'suspicious_reason': self.suspicious_reason,
            'block_hash': self.block_hash,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class BlockchainBlock(db.Model):
    __tablename__ = 'blockchain_blocks'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    block_index   = db.Column(db.Integer, unique=True, nullable=False)
    transaction_id= db.Column(db.String(36), db.ForeignKey('transfers.id'), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=False)
    current_hash  = db.Column(db.String(64), unique=True, nullable=False)
    merkle_root   = db.Column(db.String(64), nullable=True)
    data          = db.Column(db.Text, nullable=False)  # JSON payload
    nonce         = db.Column(db.Integer, default=0)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    is_genesis    = db.Column(db.Boolean, default=False)

    transfer = db.relationship('Transfer', backref='block', uselist=False,
                                foreign_keys=[transaction_id])

    @staticmethod
    def compute_hash(index, previous_hash, timestamp, data, nonce=0):
        payload = f"{index}{previous_hash}{timestamp}{data}{nonce}"
        return hashlib.sha256(payload.encode()).hexdigest()

    @classmethod
    def create_genesis_block(cls):
        genesis_data = json.dumps({
            "type": "GENESIS",
            "message": "AgriChain Genesis Block – Uganda Agricultural Supply Chain",
            "created": datetime.utcnow().isoformat()
        })
        ts = datetime.utcnow().isoformat()
        current_hash = cls.compute_hash(0, "0" * 64, ts, genesis_data)
        block = cls(
            block_index=0,
            previous_hash="0" * 64,
            current_hash=current_hash,
            data=genesis_data,
            timestamp=datetime.utcnow(),
            is_genesis=True
        )
        return block

    @classmethod
    def add_transaction_block(cls, transfer):
        """Mine a new block for a transfer transaction."""
        last_block = cls.query.order_by(cls.block_index.desc()).first()
        if not last_block:
            genesis = cls.create_genesis_block()
            from app import db as _db
            _db.session.add(genesis)
            _db.session.flush()
            last_block = genesis

        index = last_block.block_index + 1
        previous_hash = last_block.current_hash
        ts = datetime.utcnow().isoformat()

        data_payload = json.dumps({
            "type": "TRANSFER",
            "transfer_id": transfer.id,
            "product_id": transfer.product_id,
            "sender_id": transfer.sender_id,
            "receiver_id": transfer.receiver_id,
            "from_location": transfer.from_location,
            "to_location": transfer.to_location,
            "quantity": transfer.quantity_sent,
            "unit": transfer.unit,
            "status": transfer.status,
            "timestamp": ts,
        })

        nonce = 0
        current_hash = cls.compute_hash(index, previous_hash, ts, data_payload, nonce)

        block = cls(
            block_index=index,
            transaction_id=transfer.id,
            previous_hash=previous_hash,
            current_hash=current_hash,
            data=data_payload,
            nonce=nonce,
            timestamp=datetime.utcnow()
        )
        return block

    def verify_integrity(self):
        recomputed = self.compute_hash(
            self.block_index,
            self.previous_hash,
            self.timestamp.isoformat(),
            self.data,
            self.nonce
        )
        return recomputed == self.current_hash

    def to_dict(self):
        return {
            'id': self.id,
            'block_index': self.block_index,
            'transaction_id': self.transaction_id,
            'previous_hash': self.previous_hash,
            'current_hash': self.current_hash,
            'data': json.loads(self.data),
            'nonce': self.nonce,
            'timestamp': self.timestamp.isoformat(),
            'is_genesis': self.is_genesis,
            'is_valid': self.verify_integrity(),
        }
