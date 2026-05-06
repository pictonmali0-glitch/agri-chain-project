"""Transfer management routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.user import User
from models.product import Product
from models.blockchain import Transfer, BlockchainBlock
from utils.suspicious import check_suspicious
from datetime import datetime

transfer_bp = Blueprint('transfers', __name__)


def _current_user():
    return User.query.get(get_jwt_identity())


# ── Create transfer ────────────────────────────────────────────
@transfer_bp.route('/', methods=['POST'])
@jwt_required()
def create_transfer():
    user = _current_user()
    data = request.get_json() or {}

    product_id    = data.get('product_id')
    receiver_email= (data.get('receiver_email') or '').strip().lower()
    to_location   = (data.get('to_location') or '').strip()
    quantity_sent = float(data.get('quantity_sent', 0))
    unit          = data.get('unit', 'kg')
    transfer_type = data.get('transfer_type', 'transfer')
    note          = data.get('note', '')

    if not product_id or not to_location or quantity_sent <= 0:
        return jsonify({'error': 'product_id, to_location and quantity_sent are required.'}), 400

    product = Product.query.get_or_404(product_id)

    if product.current_holder_id != user.id:
        return jsonify({'error': 'You are not the current holder of this product.'}), 403

    if quantity_sent > product.quantity:
        return jsonify({'error': f'Cannot transfer more than available ({product.quantity} {product.unit}).'}), 400

    receiver = None
    if receiver_email:
        receiver = User.query.filter_by(email=receiver_email).first()
        if not receiver:
            return jsonify({'error': f'No user found with email {receiver_email}.'}), 404

    transfer = Transfer(
        product_id=product_id,
        sender_id=user.id,
        receiver_id=receiver.id if receiver else None,
        from_location=product.current_location,
        to_location=to_location,
        quantity_sent=quantity_sent,
        unit=unit,
        status='in_transit',
        transfer_type=transfer_type,
        note=note,
    )

    # Suspicious check
    is_sus, reason = check_suspicious(transfer, product)
    if is_sus:
        transfer.is_suspicious = True
        transfer.suspicious_reason = reason

    db.session.add(transfer)
    db.session.flush()

    # Mine blockchain block
    block = BlockchainBlock.add_transaction_block(transfer)
    db.session.add(block)
    db.session.flush()

    transfer.block_hash = block.current_hash

    # Update product state
    product.current_location = to_location
    product.current_holder_id = receiver.id if receiver else product.current_holder_id
    product.status = 'in_transit'

    db.session.commit()

    return jsonify({
        'message': 'Transfer initiated.',
        'transfer': transfer.to_dict(),
        'block': block.to_dict(),
    }), 201


# ── Acknowledge receipt ─────────────────────────────────────────
@transfer_bp.route('/<transfer_id>/acknowledge', methods=['POST'])
@jwt_required()
def acknowledge_transfer(transfer_id):
    user = _current_user()
    data = request.get_json() or {}

    transfer = Transfer.query.get_or_404(transfer_id)

    if transfer.receiver_id != user.id and user.role not in ('admin',):
        return jsonify({'error': 'Not authorized to acknowledge this transfer.'}), 403

    if transfer.status == 'acknowledged':
        return jsonify({'error': 'Transfer already acknowledged.'}), 409

    quantity_received = float(data.get('quantity_received', transfer.quantity_sent))
    note = data.get('note', '')

    transfer.quantity_received = quantity_received
    transfer.acknowledgement_note = note
    transfer.acknowledged_at = datetime.utcnow()
    transfer.status = 'acknowledged'

    product = Product.query.get(transfer.product_id)
    if product:
        product.status = 'acknowledged'
        product.quantity = quantity_received  # Update to confirmed qty

    # Suspicious: quantity mismatch > 5%
    if quantity_received < transfer.quantity_sent * 0.95:
        transfer.is_suspicious = True
        transfer.suspicious_reason = (
            f"Quantity discrepancy on acknowledgement: "
            f"sent {transfer.quantity_sent}, received {quantity_received}"
        )

    # Record acknowledgement as a new block
    ack_transfer = Transfer(
        product_id=transfer.product_id,
        sender_id=transfer.receiver_id or user.id,
        receiver_id=transfer.sender_id,
        from_location=transfer.to_location,
        to_location=transfer.to_location,
        quantity_sent=quantity_received,
        unit=transfer.unit,
        status='acknowledged',
        transfer_type='acknowledgement',
        note=f"Acknowledged by {user.name}. {note}",
    )
    db.session.add(ack_transfer)
    db.session.flush()

    block = BlockchainBlock.add_transaction_block(ack_transfer)
    db.session.add(block)
    db.session.flush()
    ack_transfer.block_hash = block.current_hash

    db.session.commit()

    return jsonify({
        'message': 'Receipt acknowledged successfully.',
        'transfer': transfer.to_dict(),
        'block_hash': block.current_hash,
    }), 200


# ── List transfers ─────────────────────────────────────────────
@transfer_bp.route('/', methods=['GET'])
@jwt_required()
def list_transfers():
    user = _current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if user.role == 'farmer':
        query = Transfer.query.filter_by(sender_id=user.id)
    elif user.role == 'receiver':
        query = Transfer.query.filter_by(receiver_id=user.id)
    else:
        query = Transfer.query

    pagination = query.order_by(Transfer.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'transfers': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
    }), 200


# ── Get single transfer ────────────────────────────────────────
@transfer_bp.route('/<transfer_id>', methods=['GET'])
@jwt_required()
def get_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    return jsonify({'transfer': transfer.to_dict()}), 200


# ── Reject transfer (receiver declines) ──────────────────────
@transfer_bp.route('/<transfer_id>/reject', methods=['POST'])
@jwt_required()
def reject_transfer(transfer_id):
    user = _current_user()
    data = request.get_json() or {}
    transfer = Transfer.query.get_or_404(transfer_id)

    if transfer.receiver_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Not authorized.'}), 403

    transfer.status = 'rejected'
    transfer.acknowledgement_note = data.get('reason', 'Rejected by receiver.')

    product = Product.query.get(transfer.product_id)
    if product:
        product.status = 'pending'
        product.current_holder_id = transfer.sender_id
        product.current_location = transfer.from_location

    db.session.commit()
    return jsonify({'message': 'Transfer rejected.', 'transfer': transfer.to_dict()}), 200
