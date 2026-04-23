from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify, make_response
from functools import wraps
from models import db, User, Product, Transaction, Block, AuditLog
from blockchain import Blockchain
from datetime import datetime, date
import json, uuid, qrcode, io, base64

main_bp = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('user_role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

@main_bp.route('/')
def index():
    return render_template('landing.html')

# ─── Farmer ───────────────────────────────────────────────────────────────────

@main_bp.route('/farmer/dashboard')
@login_required
@role_required('farmer')
def farmer_dashboard():
    user = User.query.get(session['user_id'])
    products = Product.query.filter_by(farmer_id=user.id).all()
    txs = Transaction.query.join(Product).filter(Product.farmer_id == user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
    return render_template('farmer_dashboard.html', user=user, products=products, transactions=txs)

@main_bp.route('/farmer/add_product', methods=['GET', 'POST'])
@login_required
@role_required('farmer')
def add_product():
    if request.method == 'POST':
        crop = request.form['crop_type']
        qty = float(request.form['quantity'])
        loc = request.form['location']
        hdate = date.fromisoformat(request.form['harvest_date'])
        grade = request.form.get('quality_grade', 'A')
        notes = request.form.get('notes', '')
        code = f'PC-{datetime.utcnow().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
        p = Product(
            product_code=code, crop_type=crop, quantity=qty, unit='kg',
            location=loc, district='Kasese', harvest_date=hdate,
            quality_grade=grade, status='harvested',
            farmer_id=session['user_id'], current_owner_id=session['user_id'],
            notes=notes
        )
        db.session.add(p)
        db.session.flush()
        bc = Blockchain()
        block = bc.add_block({'action': 'harvested', 'product_id': p.id, 'crop': crop,
                               'farmer_id': session['user_id'], 'qty': qty, 'location': loc})
        p.blockchain_hash = block.hash
        tx = Transaction(
            tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
            product_id=p.id, action='harvested',
            sender_id=session['user_id'],
            block_index=block.index, block_hash=block.hash,
            previous_hash=block.previous_hash,
            payload=json.dumps({'crop': crop, 'qty': qty, 'location': loc, 'grade': grade})
        )
        db.session.add(tx)
        db.session.commit()
        flash(f'Product {code} added to blockchain!', 'success')
        return redirect(url_for('main.farmer_dashboard'))
    return render_template('add_product.html')

@main_bp.route('/farmer/transfer/<int:product_id>', methods=['POST'])
@login_required
@role_required('farmer')
def transfer_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))
    receiver_email = request.form.get('receiver_email')
    receiver = User.query.filter_by(email=receiver_email).first()
    if not receiver:
        flash('Receiver not found.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))
    product.current_owner_id = receiver.id
    product.status = 'transferred'
    bc = Blockchain()
    block = bc.add_block({'action': 'transferred', 'product_id': product.id,
                           'from': session['user_id'], 'to': receiver.id})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='transferred',
        sender_id=session['user_id'], receiver_id=receiver.id,
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)
    db.session.commit()
    flash(f'Product transferred to {receiver.name}!', 'success')
    return redirect(url_for('main.farmer_dashboard'))

# ─── Buyer ────────────────────────────────────────────────────────────────────

@main_bp.route('/buyer/dashboard')
@login_required
@role_required('buyer')
def buyer_dashboard():
    user = User.query.get(session['user_id'])
    products = Product.query.filter(Product.status.in_(['transferred', 'harvested'])).all()
    owned = Product.query.filter_by(current_owner_id=user.id).all()
    txs = Transaction.query.filter(
        (Transaction.sender_id == user.id) | (Transaction.receiver_id == user.id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    return render_template('buyer_dashboard.html', user=user, products=products, owned=owned, transactions=txs)

@main_bp.route('/buyer/confirm_purchase/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def confirm_purchase(product_id):
    product = Product.query.get_or_404(product_id)
    product.current_owner_id = session['user_id']
    product.status = 'purchased'
    bc = Blockchain()
    block = bc.add_block({'action': 'purchased', 'product_id': product.id, 'buyer_id': session['user_id']})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='purchased',
        sender_id=product.farmer_id, receiver_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)
    db.session.commit()
    flash('Purchase confirmed on blockchain!', 'success')
    return redirect(url_for('main.buyer_dashboard'))

# ─── Transporter ──────────────────────────────────────────────────────────────

@main_bp.route('/transporter/dashboard')
@login_required
@role_required('transporter')
def transporter_dashboard():
    user = User.query.get(session['user_id'])
    products = Product.query.filter(Product.status.in_(['purchased', 'transferred', 'in_transit'])).all()
    return render_template('transporter_dashboard.html', user=user, products=products)

@main_bp.route('/transporter/update_status/<int:product_id>', methods=['POST'])
@login_required
@role_required('transporter')
def update_transport_status(product_id):
    product = Product.query.get_or_404(product_id)
    new_status = request.form.get('status')
    product.status = new_status
    bc = Blockchain()
    block = bc.add_block({'action': new_status, 'product_id': product.id, 'transporter_id': session['user_id']})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action=new_status,
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)
    db.session.commit()
    flash(f'Status updated to {new_status}!', 'success')
    return redirect(url_for('main.transporter_dashboard'))

# ─── Regulator ────────────────────────────────────────────────────────────────

@main_bp.route('/regulator/dashboard')
@login_required
@role_required('regulator')
def regulator_dashboard():
    user = User.query.get(session['user_id'])
    products = Product.query.all()
    flagged = Product.query.filter_by(is_flagged=True).all()
    bc = Blockchain()
    chain_valid = bc.is_chain_valid()
    return render_template('regulator_dashboard.html', user=user, products=products, flagged=flagged, chain_valid=chain_valid)

@main_bp.route('/regulator/approve/<int:product_id>', methods=['POST'])
@login_required
@role_required('regulator')
def approve_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_approved = True
    product.status = 'approved'
    bc = Blockchain()
    block = bc.add_block({'action': 'approved', 'product_id': product.id, 'regulator_id': session['user_id']})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='approved_by_regulator',
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)
    db.session.commit()
    flash('Product approved on blockchain!', 'success')
    return redirect(url_for('main.regulator_dashboard'))

@main_bp.route('/regulator/flag/<int:product_id>', methods=['POST'])
@login_required
@role_required('regulator')
def flag_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_flagged = True
    db.session.commit()
    flash('Product flagged for review.', 'warning')
    return redirect(url_for('main.regulator_dashboard'))

# ─── Admin ────────────────────────────────────────────────────────────────────

@main_bp.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    users = User.query.all()
    products = Product.query.all()
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(20).all()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(30).all()
    bc = Blockchain()
    stats = {
        'total_users': len(users),
        'total_products': len(products),
        'total_transactions': Transaction.query.count(),
        'total_blocks': Block.query.count(),
        'flagged': Product.query.filter_by(is_flagged=True).count(),
        'approved': Product.query.filter_by(is_approved=True).count(),
        'chain_valid': bc.is_chain_valid()
    }
    return render_template('admin_dashboard.html', users=users, products=products,
                           transactions=transactions, logs=logs, stats=stats)

@main_bp.route('/admin/toggle_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {"activated" if user.is_active else "deactivated"}.', 'info')
    return redirect(url_for('main.admin_dashboard'))

# ─── Shared ───────────────────────────────────────────────────────────────────

@main_bp.route('/track')
@login_required
def track_product():
    query = request.args.get('q', '')
    product = None
    transactions = []
    if query:
        product = Product.query.filter(
            (Product.product_code == query) |
            (Product.id == query if query.isdigit() else False)
        ).first()
        if product:
            transactions = Transaction.query.filter_by(product_id=product.id).order_by(Transaction.timestamp).all()
    return render_template('track.html', product=product, transactions=transactions, query=query)

@main_bp.route('/blockchain_explorer')
@login_required
def blockchain_explorer():
    bc = Blockchain()
    chain = bc.get_chain()
    is_valid = bc.is_chain_valid()
    return render_template('blockchain_explorer.html', chain=chain, is_valid=is_valid)

@main_bp.route('/analytics')
@login_required
def analytics():
    from sqlalchemy import func
    crop_data = db.session.query(Product.crop_type, func.count(Product.id)).group_by(Product.crop_type).all()
    status_data = db.session.query(Product.status, func.count(Product.id)).group_by(Product.status).all()
    district_data = db.session.query(Product.district, func.count(Product.id)).group_by(Product.district).all()
    return render_template('analytics.html',
        crop_data=json.dumps([{'label': c, 'value': v} for c, v in crop_data]),
        status_data=json.dumps([{'label': s, 'value': v} for s, v in status_data]),
        district_data=json.dumps([{'label': d, 'value': v} for d, v in district_data]),
        total_txs=Transaction.query.count(),
        total_products=Product.query.count(),
        verified=Product.query.filter_by(is_approved=True).count(),
        flagged=Product.query.filter_by(is_flagged=True).count()
    )

@main_bp.route('/qr/<string:product_code>')
@login_required
def generate_qr(product_code):
    product = Product.query.filter_by(product_code=product_code).first_or_404()
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(request.host_url + f'track?q={product_code}')
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    return render_template('qr.html', product=product, qr_data=encoded)

@main_bp.route('/api/products')
@login_required
def api_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@main_bp.route('/api/chain')
@login_required
def api_chain():
    bc = Blockchain()
    return jsonify({'chain': bc.get_chain(), 'valid': bc.is_chain_valid()})
