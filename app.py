from flask import Flask
from models import db
from auth import auth_bp
from routes import main_bp
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    # Create tables safely (NO seed_data on deploy)
    with app.app_context():
        db.create_all()

    return app


# IMPORTANT: Render entry point
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)