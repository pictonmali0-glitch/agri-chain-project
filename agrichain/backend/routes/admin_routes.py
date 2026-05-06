"""Admin routes - dashboard, analytics, suspicious transactions."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.user import User
from models.product import Product
from models.blockchain import Transfer, BlockchainBlock
from sqlalchemy import func, desc
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)


def _require_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return None
    return user


# ── Dashboard overview ─────────────────────────────────────────
@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    total_users    = User.query.count()
    total_farmers  = User.query.filter_by(role='farmer').count()
    total_receivers= User.query.filter_by(role='receiver').count()
    total_products = Product.query.count()
    total_transfers= Transfer.query.count()
    suspicious_count = Transfer.query.filter_by(is_suspicious=True).count()
    total_blocks   = BlockchainBlock.query.count()

    # Recent transactions (last 10)
    recent = Transfer.query.order_by(Transfer.created_at.desc()).limit(10).all()
    recent_list = []
    for t in recent:
        recent_list.append({
            'id': t.id,
            'farmer_name': t.product.farmer.name if t.product and t.product.farmer else 'Unknown',
            'sender_name': t.sender.name if t.sender else 'Unknown',
            'product_name': t.product.name if t.product else 'Unknown',
            'batch_number': t.product.batch_number if t.product else 'N/A',
            'quantity': f"{t.quantity_sent} {t.unit}",
            'from_location': t.from_location,
            'to_location': t.to_location,
            'status': t.status,
            'is_suspicious': t.is_suspicious,
            'timestamp': t.created_at.isoformat(),
            'description': (
                f"{t.sender.name if t.sender else '?'} transferred "
                f"{t.quantity_sent} {t.unit} "
                f"{t.product.name if t.product else '?'} to {t.to_location}"
            )
        })

    # Product status breakdown
    status_counts = db.session.query(
        Product.status, func.count(Product.id)
    ).group_by(Product.status).all()

    # Weekly transfer activity (last 7 days)
    weekly = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        start = day.replace(hour=0, minute=0, second=0)
        end   = day.replace(hour=23, minute=59, second=59)
        count = Transfer.query.filter(
            Transfer.created_at >= start,
            Transfer.created_at <= end
        ).count()
        weekly.append({'date': day.strftime('%Y-%m-%d'), 'count': count})

    return jsonify({
        'stats': {
            'total_users': total_users,
            'total_farmers': total_farmers,
            'total_receivers': total_receivers,
            'total_products': total_products,
            'total_transfers': total_transfers,
            'suspicious_count': suspicious_count,
            'total_blocks': total_blocks,
        },
        'recent_transactions': recent_list,
        'product_status': {s: c for s, c in status_counts},
        'weekly_activity': weekly,
    }), 200


# ── Product movement timeline ──────────────────────────────────
@admin_bp.route('/movements', methods=['GET'])
@jwt_required()
def product_movements():
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    product_id = request.args.get('product_id')

    query = Transfer.query
    if product_id:
        query = query.filter_by(product_id=product_id)

    pagination = query.order_by(Transfer.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    movements = []
    for t in pagination.items:
        movements.append({
            'transfer_id': t.id,
            'farmer_name': t.product.farmer.name if t.product and t.product.farmer else 'Unknown',
            'product_name': t.product.name if t.product else 'Unknown',
            'batch': t.product.batch_number if t.product else 'N/A',
            'handler': t.sender.name if t.sender else 'Unknown',
            'current_holder': t.receiver.name if t.receiver else 'Unknown',
            'from_location': t.from_location,
            'to_location': t.to_location,
            'quantity': f"{t.quantity_sent} {t.unit}",
            'stage': t.transfer_type,
            'status': t.status,
            'is_suspicious': t.is_suspicious,
            'timestamp': t.created_at.isoformat(),
        })

    return jsonify({
        'movements': movements,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
    }), 200


# ── Suspicious transactions ────────────────────────────────────
@admin_bp.route('/suspicious', methods=['GET'])
@jwt_required()
def suspicious_transactions():
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = Transfer.query.filter_by(is_suspicious=True)\
        .order_by(Transfer.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'suspicious': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
    }), 200


# ── Flag / unflag transaction ──────────────────────────────────
@admin_bp.route('/suspicious/<transfer_id>', methods=['PUT'])
@jwt_required()
def flag_transaction(transfer_id):
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    data = request.get_json() or {}
    transfer = Transfer.query.get_or_404(transfer_id)
    transfer.is_suspicious = data.get('is_suspicious', True)
    transfer.suspicious_reason = data.get('reason', transfer.suspicious_reason)
    db.session.commit()

    return jsonify({'message': 'Updated.', 'transfer': transfer.to_dict()}), 200


# ── All users ──────────────────────────────────────────────────
@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    role = request.args.get('role', '')
    query = User.query
    if role:
        query = query.filter_by(role=role)

    users = query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200


# ── Approve / reject a transfer ────────────────────────────────
@admin_bp.route('/transfers/<transfer_id>/approve', methods=['POST'])
@jwt_required()
def approve_transfer(transfer_id):
    admin = _require_admin()
    if not admin:
        return jsonify({'error': 'Admin access required.'}), 403

    data = request.get_json() or {}
    transfer = Transfer.query.get_or_404(transfer_id)
    action = data.get('action', 'approve')  # approve | reject

    if action == 'approve':
        transfer.status = 'delivered'
        if transfer.product:
            transfer.product.status = 'delivered'
    else:
        transfer.status = 'rejected'
        transfer.acknowledgement_note = data.get('reason', 'Rejected by admin.')

    db.session.commit()
    return jsonify({'message': f'Transfer {action}d.', 'transfer': transfer.to_dict()}), 200
