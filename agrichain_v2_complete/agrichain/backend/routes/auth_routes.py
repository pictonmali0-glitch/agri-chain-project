"""Authentication routes for AgriChain."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app import db
from models.user import User, OTPCode
from utils.auth_utils import create_otp_record, send_otp_email, verify_otp_code
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)


def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))


def _validate_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', pw):
        return False, "Password must contain an uppercase letter."
    if not re.search(r'[0-9]', pw):
        return False, "Password must contain a digit."
    return True, ""


# ── Step 1: Request registration OTP ────────────────────────────
@auth_bp.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    purpose = data.get('purpose', 'registration')

    if not email or not _validate_email(email):
        return jsonify({'error': 'Invalid email address.'}), 400

    if purpose == 'registration' and User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 409

    if purpose in ('login', 'reset'):
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'No account found with this email.'}), 404

    code = create_otp_record(email, purpose)
    db.session.commit()
    send_otp_email(email, code, purpose)

    return jsonify({'message': f'OTP sent to {email}', 'purpose': purpose}), 200


# ── Step 2: Verify OTP ─────────────────────────────────────────
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    purpose = data.get('purpose', 'registration')

    if not email or not code:
        return jsonify({'error': 'Email and code required.'}), 400

    success, msg = verify_otp_code(email, code, purpose)
    db.session.commit()

    if not success:
        return jsonify({'error': msg}), 400

    return jsonify({'message': msg, 'email_verified': True}), 200


# ── Step 3: Complete registration ─────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    role     = data.get('role', 'farmer').lower()
    phone    = (data.get('phone') or '').strip()
    location = (data.get('location') or '').strip()
    otp_code = (data.get('otp_code') or '').strip()

    # Validations
    if not name or not email or not password:
        return jsonify({'error': 'Name, email and password are required.'}), 400
    if not _validate_email(email):
        return jsonify({'error': 'Invalid email address.'}), 400
    if role not in ('farmer', 'receiver', 'admin'):
        return jsonify({'error': 'Invalid role. Choose: farmer, receiver, admin.'}), 400

    valid_pw, pw_msg = _validate_password(password)
    if not valid_pw:
        return jsonify({'error': pw_msg}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 409

    # Verify OTP was completed
    success, msg = verify_otp_code(email, otp_code, 'registration')
    if not success:
        return jsonify({'error': f'OTP verification failed: {msg}'}), 400

    user = User(
        name=name,
        email=email,
        role=role,
        phone=phone,
        location=location,
        is_verified=True
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token  = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'message': 'Registration successful!',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
    }), 201


# ── Login ──────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not user.is_verified:
        return jsonify({'error': 'Account not verified. Check your email.'}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token  = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'message': 'Login successful!',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
    }), 200


# ── Password reset ─────────────────────────────────────────────
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email     = (data.get('email') or '').strip().lower()
    otp_code  = (data.get('otp_code') or '').strip()
    new_pw    = data.get('new_password') or ''

    valid_pw, pw_msg = _validate_password(new_pw)
    if not valid_pw:
        return jsonify({'error': pw_msg}), 400

    success, msg = verify_otp_code(email, otp_code, 'reset')
    if not success:
        return jsonify({'error': msg}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    user.set_password(new_pw)
    db.session.commit()
    return jsonify({'message': 'Password reset successfully.'}), 200


# ── Get current user profile ───────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


# ── Update profile ────────────────────────────────────────────
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'name' in data:     user.name = data['name'].strip()
    if 'phone' in data:    user.phone = data['phone'].strip()
    if 'location' in data: user.location = data['location'].strip()
    if 'fingerprint_enabled' in data:
        user.fingerprint_enabled = bool(data['fingerprint_enabled'])

    db.session.commit()
    return jsonify({'message': 'Profile updated.', 'user': user.to_dict()}), 200


# ── Upload profile picture ─────────────────────────────────────
@auth_bp.route('/profile/picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    from utils.qr_utils import save_uploaded_image
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400

    file = request.files['file']
    path = save_uploaded_image(file, subfolder='profiles')
    user.profile_pic = path
    db.session.commit()

    return jsonify({'message': 'Profile picture updated.', 'profile_pic': path}), 200


# ── Refresh token ──────────────────────────────────────────────
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200
