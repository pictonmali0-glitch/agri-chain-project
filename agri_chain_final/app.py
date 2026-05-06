import os
from flask import Flask

from config import Config
from models import db, seed_data
from auth import auth_bp
from routes import main_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    # SECRET KEY
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_123')

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _migrate()      # add any missing columns safely
        seed_data()     # seed test users if DB is empty

    return app


def _migrate():
    """Safely add new columns to existing tables without wiping data."""
    try:
        db.session.execute(db.text(
            "ALTER TABLE products ADD COLUMN image_data TEXT"
        ))
        db.session.commit()
        print("Migration: added image_data column to products.")
    except Exception:
        # Column already exists — safe to ignore
        db.session.rollback()


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)