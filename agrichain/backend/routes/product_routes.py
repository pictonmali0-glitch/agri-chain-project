"""Product management routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.user import User
from models.product import Product
from utils.qr_utils import generate_product_qr, get_qr_base64, save_uploaded_image, generate_batch_number
from datetime import date
import json

product_bp = Blueprint('products', __name__)


def _current_user():
    return User.query.get(get_jwt_identity())


# ── Create product ─────────────────────────────────────────────
@product_bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    user = _current_user()
    if user.role != 'farmer':
        return jsonify({'error': 'Only farmers can add products.'}), 403

    data = request.get_json() or {}

    name     = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    quantity = float(data.get('quantity', 0))
    unit     = data.get('unit', 'kg')
    origin   = (data.get('origin') or user.location or '').strip()
    description = data.get('description', '')
    harvest_date_str = data.get('harvest_date')

    if not name or quantity <= 0:
        return jsonify({'error': 'Product name and quantity are required.'}), 400

    harvest_date = None
    if harvest_date_str:
        try:
            harvest_date = date.fromisoformat(harvest_date_str)
        except ValueError:
            return jsonify({'error': 'Invalid harvest_date format. Use YYYY-MM-DD.'}), 400

    batch = generate_batch_number(category or name)
    product = Product(
        name=name,
        batch_number=batch,
        category=category,
        quantity=quantity,
        unit=unit,
        description=description,
        origin=origin,
        harvest_date=harvest_date,
        current_location=origin,
        farmer_id=user.id,
        current_holder_id=user.id,
        status='pending'
    )
    db.session.add(product)
    db.session.flush()  # Get ID before QR

    # Generate QR code
    qr_path = generate_product_qr(product.id, batch)
    product.qr_code_path = qr_path

    db.session.commit()

    return jsonify({
        'message': 'Product created successfully.',
        'product': product.to_dict(),
        'qr_base64': get_qr_base64(product.id),
    }), 201


# ── List farmer's products ─────────────────────────────────────
@product_bp.route('/', methods=['GET'])
@jwt_required()
def list_products():
    user = _current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    query = Product.query
    if user.role == 'farmer':
        query = query.filter_by(farmer_id=user.id)
    elif user.role == 'receiver':
        query = query.filter_by(current_holder_id=user.id)
    # admin sees all

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Product.name.ilike(like),
                Product.batch_number.ilike(like),
                Product.category.ilike(like),
            )
        )
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'products': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
    }), 200


# ── Get single product ─────────────────────────────────────────
@product_bp.route('/<product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'product': product.to_dict(),
        'qr_base64': get_qr_base64(product.id),
    }), 200


# ── Search products ────────────────────────────────────────────
@product_bp.route('/search', methods=['GET'])
@jwt_required()
def search_products():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'results': []}), 200

    like = f'%{q}%'
    products = Product.query.join(User, Product.farmer_id == User.id).filter(
        db.or_(
            Product.name.ilike(like),
            Product.batch_number.ilike(like),
            Product.category.ilike(like),
            User.name.ilike(like),
        )
    ).limit(20).all()

    return jsonify({
        'results': [
            {
                'id': p.id,
                'name': p.name,
                'batch_number': p.batch_number,
                'farmer_name': p.farmer.name,
                'status': p.status,
                'quantity': f"{p.quantity} {p.unit}",
            }
            for p in products
        ]
    }), 200


# ── Upload product images ──────────────────────────────────────
@product_bp.route('/<product_id>/images', methods=['POST'])
@jwt_required()
def upload_images(product_id):
    user = _current_user()
    product = Product.query.get_or_404(product_id)

    if product.farmer_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Not authorized.'}), 403

    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded.'}), 400

    files = request.files.getlist('files')
    existing = json.loads(product.images) if product.images else []

    for f in files:
        path = save_uploaded_image(f, subfolder='products')
        existing.append(path)

    product.images = json.dumps(existing)
    db.session.commit()

    return jsonify({'message': f'{len(files)} image(s) uploaded.', 'images': existing}), 200


# ── Regenerate QR code ─────────────────────────────────────────
@product_bp.route('/<product_id>/qr', methods=['GET'])
@jwt_required()
def get_qr(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.qr_code_path:
        qr_path = generate_product_qr(product.id, product.batch_number)
        product.qr_code_path = qr_path
        db.session.commit()

    return jsonify({
        'product_id': product.id,
        'batch_number': product.batch_number,
        'qr_base64': get_qr_base64(product.id),
        'qr_path': product.qr_code_path,
    }), 200


# ── Tracking history ──────────────────────────────────────────
@product_bp.route('/<product_id>/history', methods=['GET'])
@jwt_required()
def product_history(product_id):
    from models.blockchain import Transfer
    product = Product.query.get_or_404(product_id)
    transfers = Transfer.query.filter_by(product_id=product_id)\
        .order_by(Transfer.created_at.asc()).all()

    timeline = []
    for t in transfers:
        timeline.append({
            'transfer_id': t.id,
            'stage': t.transfer_type,
            'from': t.from_location,
            'to': t.to_location,
            'handler': t.sender.name if t.sender else 'Unknown',
            'receiver': t.receiver.name if t.receiver else 'Unknown',
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
        'timeline': timeline,
        'farmer': product.farmer.to_dict() if product.farmer else None,
    }), 200
