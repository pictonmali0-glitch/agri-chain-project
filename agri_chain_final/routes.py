from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify, make_response
from functools import wraps
from models import db, User, Product, Transaction, Block, AuditLog, Notification, PurchaseRequest
from blockchain import Blockchain
from datetime import datetime, date
import json, uuid, qrcode, io, base64

main_bp = Blueprint('main', __name__)

def notify(user_id, title, message, link=None):
    """Create an in-app notification for a user."""
    n = Notification(user_id=user_id, title=title, message=message, link=link)
    db.session.add(n)



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
    # Show pending purchase requests for farmer's products
    purchase_requests = PurchaseRequest.query.join(Product).filter(
        Product.farmer_id == user.id,
        PurchaseRequest.status == 'pending'
    ).all()
    return render_template('farmer_dashboard.html', user=user, products=products,
                           transactions=txs, purchase_requests=purchase_requests)

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

        # ── Handle produce photo ──
        image_data = None
        photo = request.files.get('produce_image')
        if photo and photo.filename:
            mime = photo.mimetype or 'image/jpeg'
            raw = photo.read()
            # Reject files over 5MB
            if len(raw) <= 5 * 1024 * 1024:
                encoded = base64.b64encode(raw).decode('utf-8')
                image_data = f'data:{mime};base64,{encoded}'

        price_per_kg = request.form.get('price_per_kg', None)
        price_per_kg = float(price_per_kg) if price_per_kg else None

        p = Product(
            product_code=code, crop_type=crop, quantity=qty, unit='kg',
            location=loc, district='Kasese', harvest_date=hdate,
            quality_grade=grade, status='harvested',
            farmer_id=session['user_id'], current_owner_id=session['user_id'],
            notes=notes,
            image_data=image_data,
            price_per_kg=price_per_kg
        )
        db.session.add(p)
        db.session.flush()

        bc = Blockchain()
        block = bc.add_block({
            'action': 'harvested', 'product_id': p.id, 'crop': crop,
            'farmer_id': session['user_id'], 'qty': qty, 'location': loc,
            'has_photo': image_data is not None
        })
        p.blockchain_hash = block.hash

        tx = Transaction(
            tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
            product_id=p.id, action='harvested',
            sender_id=session['user_id'],
            block_index=block.index, block_hash=block.hash,
            previous_hash=block.previous_hash,
            payload=json.dumps({'crop': crop, 'qty': qty, 'location': loc, 'grade': grade, 'has_photo': image_data is not None})
        )
        db.session.add(tx)
        db.session.commit()

        flash(f'Product {code} added to blockchain!', 'success')
        return redirect(url_for('main.farmer_dashboard'))

    return render_template('add_product.html')


@main_bp.route('/farmer/reject_request/<int:request_id>', methods=['POST'])
@login_required
@role_required('farmer')
def reject_purchase_request(request_id):
    pr = PurchaseRequest.query.get_or_404(request_id)
    product = Product.query.get(pr.product_id)
    if product.farmer_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))
    pr.status = 'rejected'
    notify(pr.buyer_id, '❌ Purchase Request Rejected',
           f'Your request to buy {product.crop_type} ({product.product_code}) was rejected by the farmer.',
           link='/buyer/dashboard')
    db.session.commit()
    flash('Purchase request rejected.', 'info')
    return redirect(url_for('main.farmer_dashboard'))

@main_bp.route('/farmer/transfer/<int:product_id>', methods=['POST'])
@login_required
@role_required('farmer')
def transfer_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))
    # FIX 1: Prevent double selling — only allow transfer if still harvested
    if product.status != 'harvested':
        flash(f'Product cannot be transferred — current status is "{product.status}".', 'danger')
        return redirect(url_for('main.farmer_dashboard'))

    receiver_email = request.form.get('receiver_email')
    receiver = User.query.filter_by(email=receiver_email).first()
    if not receiver:
        flash('Receiver not found.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))
    if receiver.id == session['user_id']:
        flash('You cannot transfer a product to yourself.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))

    # FIX: Enforce buy request — buyer must have requested this product first
    purchase_req = PurchaseRequest.query.filter_by(
        product_id=product.id,
        buyer_id=receiver.id,
        status='pending'
    ).first()
    if not purchase_req:
        flash(f'{receiver.name} has not placed a purchase request for this product. They must tap "Buy" first.', 'danger')
        return redirect(url_for('main.farmer_dashboard'))

    # Mark the request as approved
    purchase_req.status = 'approved'
    # Reject all other pending requests for this product
    PurchaseRequest.query.filter(
        PurchaseRequest.product_id == product.id,
        PurchaseRequest.buyer_id != receiver.id,
        PurchaseRequest.status == 'pending'
    ).update({'status': 'rejected'})
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
    # Notify receiver
    notify(receiver.id, 'Product Transferred to You',
           f'{session.get("user_name")} has transferred {product.crop_type} ({product.product_code}) to you.',
           link=f'/verify?q={product.product_code}')
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

@main_bp.route('/buyer/request_purchase/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def request_purchase(product_id):
    """Buyer sends a purchase request — farmer must approve and transfer."""
    product = Product.query.get_or_404(product_id)

    # Only available harvested products can be requested
    if product.status != 'harvested':
        flash('This product is not available for purchase.', 'warning')
        return redirect(url_for('main.buyer_dashboard'))

    # Check no existing pending request from this buyer
    existing = PurchaseRequest.query.filter_by(
        product_id=product_id,
        buyer_id=session['user_id'],
        status='pending'
    ).first()
    if existing:
        flash('You already have a pending request for this product.', 'info')
        return redirect(url_for('main.buyer_dashboard'))

    # Check product not already requested by someone else
    other_request = PurchaseRequest.query.filter_by(
        product_id=product_id, status='pending'
    ).first()
    if other_request:
        flash('This product already has a pending purchase request.', 'warning')
        return redirect(url_for('main.buyer_dashboard'))

    pr = PurchaseRequest(product_id=product_id, buyer_id=session['user_id'], status='pending')
    db.session.add(pr)

    # Notify farmer
    notify(product.farmer_id, '🛒 New Purchase Request',
           f'{session.get("user_name")} wants to buy your {product.crop_type} ({product.product_code}).',
           link='/farmer/dashboard')
    db.session.commit()
    flash('Purchase request sent! Waiting for farmer to approve and transfer.', 'success')
    return redirect(url_for('main.buyer_dashboard'))


@main_bp.route('/buyer/set_resale_price/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def set_resale_price(product_id):
    product = Product.query.get_or_404(product_id)
    if product.current_owner_id != session['user_id']:
        flash('You do not own this product.', 'danger')
        return redirect(url_for('main.buyer_dashboard'))
    resale = request.form.get('resale_price_per_kg')
    if resale:
        product.resale_price_per_kg = float(resale)
        db.session.commit()
        flash(f'Resale price set to UGX {float(resale):,.0f}/kg', 'success')
    return redirect(url_for('main.buyer_dashboard'))

# ─── Transporter ──────────────────────────────────────────────────────────────

@main_bp.route('/transporter/dashboard')
@login_required
@role_required('transporter')
def transporter_dashboard():
    user = User.query.get(session['user_id'])
    # FIX 3: Only show products that have been transferred (seller confirmed transfer)
    # and products already in transit or pending delivery confirmation
    products = Product.query.filter(
        Product.status.in_(['transferred', 'in_transit', 'pending_delivery_confirmation'])
    ).all()
    return render_template('transporter_dashboard.html', user=user, products=products)

@main_bp.route('/transporter/update_status/<int:product_id>', methods=['POST'])
@login_required
@role_required('transporter')
def update_transport_status(product_id):
    product = Product.query.get_or_404(product_id)
    new_status = request.form.get('status')
    # FIX 4: Transporter can only set in_transit, not delivered directly
    # Delivered status requires buyer QR scan confirmation
    if new_status == 'delivered':
        flash('Delivery must be confirmed by the receiver scanning the QR code.', 'warning')
        return redirect(url_for('main.transporter_dashboard'))

    actual_status = new_status
    if new_status == 'pending_delivery_confirmation':
        actual_status = 'pending_delivery_confirmation'

    product.status = actual_status
    bc = Blockchain()
    block = bc.add_block({'action': actual_status, 'product_id': product.id, 'transporter_id': session['user_id']})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action=actual_status,
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)

    if actual_status == 'in_transit' and product.current_owner_id:
        notify(
            product.current_owner_id,
            'Product Picked Up',
            f'Your {product.crop_type} ({product.product_code}) has been picked up and is now in transit.',
            link=f'/verify?q={product.product_code}'
        )

    if actual_status == 'pending_delivery_confirmation':
        if product.current_owner_id:
            notify(
                product.current_owner_id,
                '📦 Delivery Arrived — Scan to Confirm',
                f'{product.crop_type} ({product.product_code}) has arrived. Please scan the QR code to confirm receipt.',
                link=f'/buyer/confirm_delivery/{product.id}'
            )

    db.session.commit()
    flash(f'Status updated!', 'success')
    return redirect(url_for('main.transporter_dashboard'))


@main_bp.route('/transporter/scan_pickup/<string:product_code>', methods=['POST'])
@login_required
@role_required('transporter')
def scan_pickup(product_code):
    """Transporter scans QR to confirm pickup — must come from camera scan."""
    # FIX: Only allow from AJAX (camera scanner), block direct form posts
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not is_ajax:
        flash('Pickup must be confirmed by scanning the product QR code with your camera.', 'danger')
        return redirect(url_for('main.transporter_dashboard'))

    product = Product.query.filter_by(product_code=product_code).first_or_404()
    # FIX 3: Only allow pickup if seller has transferred the product
    if product.status != 'transferred':
        return jsonify({'success': False, 'error': f'Product cannot be picked up — status is "{product.status}". The seller must transfer it first.'})

    product.status = 'in_transit'
    bc = Blockchain()
    block = bc.add_block({
        'action': 'in_transit',
        'product_id': product.id,
        'transporter_id': session['user_id'],
        'method': 'qr_scan'
    })
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='in_transit',
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash,
        payload=json.dumps({'method': 'qr_scan', 'transporter': session.get('user_name')})
    )
    db.session.add(tx)

    if product.current_owner_id:
        notify(
            product.current_owner_id,
            'Product Picked Up via QR Scan',
            f'{product.crop_type} ({product.product_code}) was scanned and picked up by transporter.',
            link=f'/verify?q={product.product_code}'
        )

    db.session.commit()

    # Return JSON for AJAX calls, redirect for normal form posts
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Pickup confirmed! {product_code} is now in transit.'})

    flash(f'Pickup confirmed for {product_code}! Product is now in transit.', 'success')
    return redirect(url_for('main.transporter_dashboard'))


@main_bp.route('/buyer/confirm_delivery/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('buyer')
def confirm_delivery(product_id):
    """Buyer scans QR code to confirm delivery. QR must match product."""
    product = Product.query.get_or_404(product_id)
    if product.current_owner_id != session['user_id']:
        flash('This product does not belong to you.', 'danger')
        return redirect(url_for('main.buyer_dashboard'))

    # FIX 5: Only allow confirmation if in transit or pending confirmation, not already delivered
    if product.status == 'delivered':
        flash('This product has already been confirmed as delivered.', 'info')
        return redirect(url_for('main.buyer_dashboard'))

    if product.status not in ['in_transit', 'pending_delivery_confirmation']:
        flash('Product is not ready for delivery confirmation yet.', 'warning')
        return redirect(url_for('main.buyer_dashboard'))

    if request.method == 'POST':
        scanned_code = request.form.get('scanned_code', '').strip()
        # FIX: Require QR scan — empty scanned_code means they bypassed scanner
        if not scanned_code:
            flash('You must scan the product QR code to confirm receipt. Manual confirmation is not allowed.', 'danger')
            return render_template('confirm_delivery.html', product=product, mismatch=False)
        # FIX 5: Verify scanned QR code matches this product
        if scanned_code != product.product_code:
            flash(f'QR code mismatch! Scanned "{scanned_code}" but expected "{product.product_code}". Wrong product.', 'danger')
            return render_template('confirm_delivery.html', product=product, mismatch=True)

        product.status = 'delivered'
        bc = Blockchain()
        block = bc.add_block({
            'action': 'delivery_confirmed',
            'product_id': product.id,
            'receiver_id': session['user_id'],
            'method': 'qr_scan_confirmation',
            'scanned_code': scanned_code or product.product_code
        })
        tx = Transaction(
            tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
            product_id=product.id, action='delivery_confirmed',
            sender_id=session['user_id'],
            block_index=block.index, block_hash=block.hash,
            previous_hash=block.previous_hash,
            payload=json.dumps({'confirmed_by': session.get('user_name'), 'method': 'qr_confirmation'})
        )
        db.session.add(tx)
        notify(product.farmer_id, '✅ Delivery Confirmed',
               f'{session.get("user_name")} confirmed receipt of your {product.crop_type} ({product.product_code}).',
               link=f'/verify?q={product.product_code}')
        db.session.commit()
        flash('Delivery confirmed on blockchain!', 'success')
        return redirect(url_for('main.buyer_dashboard'))

    return render_template('confirm_delivery.html', product=product, mismatch=False)

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
    # FIX 7: Once flagged, cannot be unflagged
    if product.is_flagged:
        flash('Product is already flagged and cannot be unflagged.', 'warning')
        return redirect(url_for('main.regulator_dashboard'))
    product.is_flagged = True
    # Record on blockchain
    bc = Blockchain()
    block = bc.add_block({'action': 'flagged', 'product_id': product.id, 'regulator_id': session['user_id']})
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='flagged_by_regulator',
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash
    )
    db.session.add(tx)
    # Notify farmer
    notify(product.farmer_id, '⚠️ Product Flagged',
           f'Your {product.crop_type} ({product.product_code}) has been flagged by a regulator for review.',
           link=f'/verify?q={product.product_code}')
    db.session.commit()
    flash('Product flagged for review. This action is permanent.', 'warning')
    return redirect(url_for('main.regulator_dashboard'))


@main_bp.route('/regulator/set_grade/<int:product_id>', methods=['POST'])
@login_required
@role_required('regulator')
def set_quality_grade(product_id):
    """Only regulators can set/change quality grade."""
    product = Product.query.get_or_404(product_id)
    grade = request.form.get('quality_grade')
    if not grade:
        flash('Please select a quality grade.', 'danger')
        return redirect(url_for('main.regulator_dashboard'))
    product.quality_grade = grade
    bc = Blockchain()
    block = bc.add_block({
        'action': 'quality_graded',
        'product_id': product.id,
        'grade': grade,
        'regulator_id': session['user_id']
    })
    tx = Transaction(
        tx_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
        product_id=product.id, action='quality_graded',
        sender_id=session['user_id'],
        block_index=block.index, block_hash=block.hash,
        previous_hash=block.previous_hash,
        payload=json.dumps({'grade': grade, 'graded_by': session.get('user_name')})
    )
    db.session.add(tx)
    notify(product.farmer_id, '🏅 Quality Grade Assigned',
           f'Your {product.crop_type} ({product.product_code}) has been graded {grade} by a regulator.',
           link=f'/verify?q={product.product_code}')
    db.session.commit()
    flash(f'Quality grade set to {grade} and recorded on blockchain.', 'success')
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
    qr.add_data(request.host_url + f'verify?q={product_code}')
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




# ─── Public Product Verification (no login required) ─────────────────────────

@main_bp.route('/verify')
def public_verify():
    query = request.args.get('q', '').strip()
    search = request.args.get('search', '').strip()
    product = None
    transactions = []
    search_results = []

    # Load all products for the dropdown
    all_products = Product.query.order_by(Product.created_at.desc()).all()

    # Search by crop name or farmer name
    if search:
        from sqlalchemy import or_
        search_results = Product.query.join(User, Product.farmer_id == User.id).filter(
            or_(
                Product.crop_type.ilike(f'%{search}%'),
                User.name.ilike(f'%{search}%'),
                Product.location.ilike(f'%{search}%')
            )
        ).all()

    # Direct product code lookup
    if query:
        product = Product.query.filter(
            (Product.product_code == query) |
            (Product.id == (int(query) if query.isdigit() else -1))
        ).first()
        if product:
            transactions = Transaction.query.filter_by(
                product_id=product.id
            ).order_by(Transaction.timestamp).all()

    return render_template('verify.html', product=product,
                           transactions=transactions, query=query,
                           search=search, search_results=search_results,
                           all_products=all_products)


# ─── Public Block Verification API ───────────────────────────────────────────

@main_bp.route('/api/verify_block/<string:product_code>')
def verify_block(product_code):
    product = Product.query.filter_by(product_code=product_code).first_or_404()
    block = Block.query.filter_by(hash=product.blockchain_hash).first()
    if not block:
        return jsonify({'error': 'Block not found'}), 404
    return jsonify({
        'index': block.index,
        'timestamp': block.timestamp.isoformat(),
        'data': json.loads(block.data),
        'previous_hash': block.previous_hash,
        'nonce': block.nonce,
        'stored_hash': block.hash
    })



# ─── Profile ──────────────────────────────────────────────────────────────────

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        # Handle profile picture upload
        photo = request.files.get('profile_picture')
        if photo and photo.filename:
            mime = photo.mimetype or 'image/jpeg'
            raw = photo.read()
            if len(raw) <= 5 * 1024 * 1024:  # 5MB max
                encoded = base64.b64encode(raw).decode('utf-8')
                user.profile_picture = f'data:{mime};base64,{encoded}'
                db.session.commit()
                session['user_pic'] = user.profile_picture
                flash('Profile picture updated!', 'success')
            else:
                flash('Image too large. Max 5MB.', 'danger')
        # Handle name/phone/location update
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        if name:
            user.name = name
            session['user_name'] = name
        if phone:
            user.phone = phone
        if location:
            user.location = location
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('main.profile'))
    return render_template('profile.html', user=user)

@main_bp.route('/profile/remove_picture', methods=['POST'])
@login_required
def remove_profile_picture():
    user = User.query.get(session['user_id'])
    user.profile_picture = None
    db.session.commit()
    flash('Profile picture removed.', 'info')
    return redirect(url_for('main.profile'))

# ─── Notifications ────────────────────────────────────────────────────────────

@main_bp.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(
        user_id=session['user_id']
    ).order_by(Notification.created_at.desc()).limit(50).all()
    # Mark all as read
    Notification.query.filter_by(
        user_id=session['user_id'], is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@main_bp.route('/api/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(
        user_id=session['user_id'], is_read=False
    ).count()
    return jsonify({'count': count})

# ─── PWA ──────────────────────────────────────────────────────────────────────

@main_bp.route('/manifest.json')
def manifest():
    from flask import Response
    import json
    data = {
        "name": "AgriChain Uganda",
        "short_name": "AgriChain",
        "description": "Blockchain Agricultural Supply Chain - Kasese, Uganda",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1f13",
        "theme_color": "#1a6b3c",
        "orientation": "portrait",
        "scope": "/",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        "shortcuts": [
            {"name": "Login", "url": "/auth/login"},
            {"name": "Track Product", "url": "/track"}
        ]
    }
    return Response(json.dumps(data), mimetype='application/manifest+json')

@main_bp.route('/service-worker.js')
def service_worker():
    js = """
const CACHE_NAME = 'agrichain-v2';
const STATIC_ASSETS = ['/', '/auth/login', '/auth/register'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request).then(cached => cached || caches.match('/')))
  );
});
"""
    from flask import Response
    response = Response(js, mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@main_bp.route('/icon-192.png')
def icon_192():
    import base64
    from flask import Response
    ICON_192_B64 = "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"
    return Response(base64.b64decode(ICON_192_B64), mimetype='image/png')

@main_bp.route('/icon-512.png')
def icon_512():
    import base64
    from flask import Response
    ICON_512_B64 = "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"
    return Response(base64.b64decode(ICON_512_B64), mimetype='image/png')