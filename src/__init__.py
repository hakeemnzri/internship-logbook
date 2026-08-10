import os

from sqlalchemy import inspect, text

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from .config import Config

# Initialize extensions
db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"


def migrate_user_schema():
    """Remove the obsolete email column while retaining local user data."""
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "email" not in columns:
        return
    with db.engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys = OFF"))
        connection.execute(text("""
            CREATE TABLE users_revised (
                id INTEGER NOT NULL PRIMARY KEY,
                username VARCHAR(25) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL
            )
        """))
        connection.execute(text("""
            INSERT INTO users_revised (id, username, password_hash)
            SELECT id, username, password_hash FROM users
        """))
        connection.execute(text("DROP TABLE users"))
        connection.execute(text("ALTER TABLE users_revised RENAME TO users"))
        connection.execute(text("PRAGMA foreign_keys = ON"))


def create_app():
    """Create and configure the Flask application."""

    # Project root directory
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )

    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and set a unique value."
        )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Import models so SQLAlchemy knows about them
    from . import models

    # Create database tables if they don't exist
    with app.app_context():
        migrate_user_schema()
        db.create_all()

    # Register blueprints
    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
