"""
AgriChain Backend - Flask REST API
Agricultural Blockchain Supply Chain Tracking System
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'agrichain-dev-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///agrichain.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-agrichain-secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    # Mail config (update with real SMTP for production)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@agrichain.app')

    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Blueprints ────────────────────────────────────────────────
    from routes.auth_routes import auth_bp
    from routes.product_routes import product_bp
    from routes.transfer_routes import transfer_bp
    from routes.blockchain_routes import blockchain_bp
    from routes.admin_routes import admin_bp
    from routes.receiver_routes import receiver_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(product_bp,    url_prefix='/api/products')
    app.register_blueprint(transfer_bp,   url_prefix='/api/transfers')
    app.register_blueprint(blockchain_bp, url_prefix='/api/blockchain')
    app.register_blueprint(admin_bp,      url_prefix='/api/admin')
    app.register_blueprint(receiver_bp,   url_prefix='/api/receiver')

    # ── DB Init ───────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    """Create default admin if not exists."""
    from models.user import User
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name='AgriChain Admin',
            email='admin@agrichain.app',
            role='admin',
            is_verified=True
        )
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created: admin@agrichain.app / Admin@123")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
