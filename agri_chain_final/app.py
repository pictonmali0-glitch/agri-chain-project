import os
from flask import Flask

from config import Config
from models import db, seed_data, Notification
from auth import auth_bp
from routes import main_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(BASE_DIR, 'static'),
        static_url_path='/static'
    )

    app.config.from_object(Config)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_123')

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _migrate()      # ← MUST run before seed_data
        seed_data()

    return app


def _migrate():
    """Safely add new columns to existing tables without wiping data."""
    migrations = [
        "ALTER TABLE products ADD COLUMN image_data TEXT",
        "ALTER TABLE users ADD COLUMN webauthn_credential_id TEXT",
        "ALTER TABLE users ADD COLUMN webauthn_public_key TEXT",
        "ALTER TABLE users ADD COLUMN webauthn_sign_count INTEGER DEFAULT 0",
        "ALTER TABLE products ADD COLUMN price_per_kg FLOAT",
        "ALTER TABLE products ADD COLUMN resale_price_per_kg FLOAT",
        """CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            link VARCHAR(200),
            created_at TIMESTAMP DEFAULT NOW()
        )""",
    ]
    for sql in migrations:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
    print("Migrations complete.")


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
