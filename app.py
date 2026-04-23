from flask import Flask
from models import db
from auth import auth_bp
from routes import main_bp
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # IMPORTANT: use Render DATABASE_URL if available
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        app.config.get("SQLALCHEMY_DATABASE_URI")
    )

    # Required fix for PostgreSQL on Render
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True
    }

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)