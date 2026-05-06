"""Receiver routes - QR scan, tracking, acknowledgement."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.product import Product
from models.blockchain import Transfer
from utils.suspicious import flag_qr_abuse

receiver_bp = Blueprint('receiver', __name__)


def _current_user():
    return User.query.get(get_jwt_identity())


# ── Scan / verify product by QR payload ───────────────────────
@receiver_bp.route('/scan', methods=['POST'])
@jwt_required()
def scan_qr():
    user = _current_user()
    data = request.get_json() or {}

    # QR payload can contain product_id directly or as JSON string
    product_id = data.get('product_id')
    batch_number = data.get('batch')

    product = None
    if product_id:
        product = Product.query.get(product_id)
    elif batch_number:
        product = Product.query.filter_by(batch_number=batch_number).first()

    if not product:
        return jsonify({'error': 'Product not found. Invalid QR code.'}), 404

    # Check for QR abuse
    is_sus, reason = flag_qr_abuse(product.id, user.id)
    if is_sus:
        from app import db
        # Flag any pending transfers for this product
        pending = Transfer.query.filter_by(
            product_id=product.id, status='in_transit'
        ).first()
        if pending:
            pending.is_suspicious = True
            pending.suspicious_reason = reason
            db.session.commit()

    # Get tracking history
    transfers = Transfer.query.filter_by(product_id=product.id)\
        .order_by(Transfer.created_at.asc()).all()

    timeline = []
    for t in transfers:
        timeline.append({
            'stage': t.transfer_type,
            'handler': t.sender.name if t.sender else 'Unknown',
            'from': t.from_location,
            'to': t.to_location,
            'quantity': f"{t.quantity_sent} {t.unit}",
            'status': t.status,
            'timestamp': t.created_at.isoformat(),
            'block_hash': t.block_hash,
        })

    return jsonify({
        'product': product.to_dict(),
        'farmer': product.farmer.to_dict() if product.farmer else None,
        'timeline': timeline,
        'qr_abuse_detected': is_sus,
    }), 200


# ── Pending transfers for receiver ───────────────────────────
@receiver_bp.route('/pending', methods=['GET'])
@jwt_required()
def pending_transfers():
    user = _current_user()
    pending = Transfer.query.filter_by(
        receiver_id=user.id, status='in_transit'
    ).order_by(Transfer.created_at.desc()).all()

    return jsonify({
        'pending': [t.to_dict() for t in pending],
        'count': len(pending),
    }), 200


# ── Full tracking for a product (receiver view) ────────────────
@receiver_bp.route('/track/<product_id>', methods=['GET'])
@jwt_required()
def track_product(product_id):
    product = Product.query.get_or_404(product_id)
    transfers = Transfer.query.filter_by(product_id=product_id)\
        .order_by(Transfer.created_at.asc()).all()

    timeline = []
    for t in transfers:
        timeline.append({
            'id': t.id,
            'stage': t.transfer_type,
            'handler_name': t.sender.name if t.sender else 'Unknown',
            'receiver_name': t.receiver.name if t.receiver else 'Unknown',
            'from_location': t.from_location,
            'to_location': t.to_location,
            'quantity_sent': t.quantity_sent,
            'quantity_received': t.quantity_received,
            'unit': t.unit,
            'status': t.status,
            'timestamp': t.created_at.isoformat(),
            'acknowledged_at': t.acknowledged_at.isoformat() if t.acknowledged_at else None,
            'note': t.note,
            'block_hash': t.block_hash,
        })

    return jsonify({
        'product': product.to_dict(),
        'farmer': {
            'name': product.farmer.name,
            'location': product.farmer.location,
            'email': product.farmer.email,
        } if product.farmer else None,
        'harvest_date': product.harvest_date.isoformat() if product.harvest_date else None,
        'timeline': timeline,
        'current_status': product.status,
        'current_location': product.current_location,
    }), 200
