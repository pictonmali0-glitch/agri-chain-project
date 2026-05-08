from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, AuditLog
from datetime import datetime
import json, base64

auth_bp = Blueprint('auth', __name__)

def log_action(user_id, action, details, ip=None):
    log = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.session.add(log)
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('Account deactivated. Contact admin.', 'danger')
                return redirect(url_for('auth.login'))
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['user_email'] = user.email
            log_action(user.id, 'LOGIN', f'User {user.email} logged in', request.remote_addr)
            role_map = {
                'farmer': 'main.farmer_dashboard',
                'buyer': 'main.buyer_dashboard',
                'transporter': 'main.transporter_dashboard',
                'regulator': 'main.regulator_dashboard',
                'admin': 'main.admin_dashboard'
            }
            return redirect(url_for(role_map.get(user.role, 'main.index')))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'farmer')
        phone = request.form.get('phone', '')
        location = request.form.get('location', '')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
        user = User(
            name=name, email=email,
            password=generate_password_hash(password),
            role=role, phone=phone, location=location
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'LOGOUT', f"User {session.get('user_email')} logged out")
    session.clear()
    return redirect(url_for('main.index'))



@auth_bp.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from models import Product, Transaction
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return redirect('/')

    # Clear foreign key references before deleting user
    # Nullify current_owner on products this user owns
    Product.query.filter_by(current_owner_id=user_id).update({'current_owner_id': None})
    # Nullify sender/receiver on transactions
    Transaction.query.filter_by(sender_id=user_id).update({'sender_id': None})
    Transaction.query.filter_by(receiver_id=user_id).update({'receiver_id': None})
    # KEEP audit logs for forensic trail — just nullify the user_id link
    # so the IP address, action and timestamp are preserved even after deletion
    AuditLog.query.filter_by(user_id=user_id).update({'user_id': None})
    db.session.flush()

    session.clear()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect('/')

# ─── WebAuthn / Biometric routes ──────────────────────────────────────────────

def get_rp_id():
    """Return relying party ID — the domain without port."""
    host = request.host.split(':')[0]
    return host

def get_origin():
    return request.host_url.rstrip('/')


@auth_bp.route('/webauthn/register/begin', methods=['POST'])
def webauthn_register_begin():
    """Logged-in user wants to register their fingerprint."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    import secrets
    challenge = secrets.token_bytes(32)
    session['webauthn_register_challenge'] = base64.b64encode(challenge).decode()

    rp_id = get_rp_id()

    options = {
        'challenge': base64.urlsafe_b64encode(challenge).rstrip(b'=').decode(),
        'rp': {'name': 'AgriChain Uganda', 'id': rp_id},
        'user': {
            'id': base64.urlsafe_b64encode(str(user.id).encode()).rstrip(b'=').decode(),
            'name': user.email,
            'displayName': user.name
        },
        'pubKeyCredParams': [
            {'alg': -7, 'type': 'public-key'},   # ES256
            {'alg': -257, 'type': 'public-key'}  # RS256
        ],
        'authenticatorSelection': {
            'authenticatorAttachment': 'platform',  # device fingerprint sensor
            'userVerification': 'required'
        },
        'timeout': 60000,
        'attestation': 'none'
    }
    return jsonify(options)


@auth_bp.route('/webauthn/register/complete', methods=['POST'])
def webauthn_register_complete():
    """Save the credential after fingerprint registration."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(session['user_id'])
    data = request.get_json()

    try:
        # Store credential ID and public key (simplified storage)
        credential_id = data.get('id')
        public_key = json.dumps(data.get('response', {}))

        user.webauthn_credential_id = credential_id
        user.webauthn_public_key = public_key
        user.webauthn_sign_count = 0
        db.session.commit()

        return jsonify({'success': True, 'message': 'Fingerprint registered successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/webauthn/login/begin', methods=['POST'])
def webauthn_login_begin():
    """Return challenge for fingerprint login."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'No account found with that email'}), 404
    if not user.webauthn_credential_id:
        return jsonify({'error': 'Fingerprint not registered for this account. Login with password first, then register your fingerprint in settings.'}), 400

    import secrets
    challenge = secrets.token_bytes(32)
    session['webauthn_login_challenge'] = base64.b64encode(challenge).decode()
    session['webauthn_login_email'] = email

    rp_id = get_rp_id()

    options = {
        'challenge': base64.urlsafe_b64encode(challenge).rstrip(b'=').decode(),
        'allowCredentials': [{
            'type': 'public-key',
            'id': user.webauthn_credential_id,
            'transports': ['internal']
        }],
        'userVerification': 'required',
        'timeout': 60000,
        'rpId': rp_id
    }
    return jsonify(options)


@auth_bp.route('/webauthn/login/complete', methods=['POST'])
def webauthn_login_complete():
    """Verify fingerprint assertion and log user in."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    # Basic check — credential ID matches
    user = User.query.filter_by(email=email).first()
    if not user or not user.webauthn_credential_id:
        return jsonify({'error': 'Fingerprint not set up for this account'}), 400

    if data.get('id') != user.webauthn_credential_id:
        return jsonify({'error': 'Credential mismatch'}), 400

    # Verify clientDataJSON contains our challenge
    try:
        client_data_raw = data['response']['clientDataJSON']
        padding = '=' * (4 - len(client_data_raw) % 4)
        client_data = json.loads(base64.urlsafe_b64decode(client_data_raw + padding))
        stored_challenge = session.get('webauthn_login_challenge', '')
        received_challenge = client_data.get('challenge', '')

        # Normalize both to base64url for comparison
        stored_b64url = base64.urlsafe_b64encode(
            base64.b64decode(stored_challenge)
        ).rstrip(b'=').decode()

        if received_challenge != stored_b64url:
            return jsonify({'error': 'Challenge mismatch — possible replay attack'}), 400

    except Exception as e:
        return jsonify({'error': f'Verification error: {str(e)}'}), 400

    if not user.is_active:
        return jsonify({'error': 'Account deactivated'}), 403

    # Log in the user
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_role'] = user.role
    session['user_email'] = user.email
    log_action(user.id, 'BIOMETRIC_LOGIN', f'User {user.email} logged in via fingerprint', request.remote_addr)

    role_map = {
        'farmer': '/farmer/dashboard',
        'buyer': '/buyer/dashboard',
        'transporter': '/transporter/dashboard',
        'regulator': '/regulator/dashboard',
        'admin': '/admin/dashboard'
    }
    return jsonify({'success': True, 'redirect': role_map.get(user.role, '/')})


@auth_bp.route('/webauthn/register/page')
def webauthn_register_page():
    """Simple page for logged-in users to register fingerprint."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    already_registered = bool(user.webauthn_credential_id)
    return render_template('register_fingerprint.html',
                           user=user, already_registered=already_registered)