"""Flask application factory. Run: python app.py"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

from models import User, db

login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite needs an explicit PRAGMA to enforce relational constraints."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) if user_id.isdigit() else None


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///cinema.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=3 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        REMEMBER_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from routes.auth import bp as auth_bp
    from routes.public import bp as public_bp
    from routes.bookings import bp as bookings_bp
    from routes.admin import bp as admin_bp

    for blueprint in (auth_bp, public_bp, bookings_bp, admin_bp):
        app.register_blueprint(blueprint)

    @app.after_request
    def add_security_headers(response):
        # The UI uses external, same-origin scripts and styles only.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; "
        "script-src 'self'; font-src 'self'; form-action 'self'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
  )
        return response

    @app.context_processor
    def inject_globals():
        return {"current_year": datetime.now().year}

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/error.html", title="Bad request", message="The request could not be processed."), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/error.html", title="Access denied", message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/error.html", title="Page not found", message="We couldn't find that page."), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template("errors/error.html", title="File too large", message="Poster images must be smaller than 3 MB."), 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/error.html", title="Something went wrong", message="Please try again in a moment."), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
