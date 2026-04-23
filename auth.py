from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, AuditLog
from datetime import datetime

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
