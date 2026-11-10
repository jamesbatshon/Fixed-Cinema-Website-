"""Customer registration, sign in and sign out."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select

from models import User, UserRole, db
from utils import EMAIL_PATTERN

bp = Blueprint("auth", __name__, url_prefix="/account")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if len(email) > 255 or not EMAIL_PATTERN.fullmatch(email):
            flash("Enter a valid email address.", "error")
        elif len(password) < 10 or len(password) > 128:
            flash("Password must be between 10 and 128 characters.", "error")
        elif password != confirmation:
            flash("The passwords do not match.", "error")
        elif db.session.scalar(select(User.id).where(User.email == email)) is not None:
            flash("An account already exists with that email.", "error")
        else:
            user = User(email=email, role=UserRole.customer)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash("Could not create your account. Please try again.", "error")
            else:
                login_user(user)
                flash("Your account is ready. Welcome to Screenlane!", "success")
                return redirect(url_for("public.index"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None or not user.check_password(password):
            flash("Incorrect email or password.", "error")
        else:
            login_user(user)
            flash("Welcome back!", "success")
            # Redirect internally rather than accepting an arbitrary external 'next' URL.
            return redirect(url_for("admin.dashboard" if user.is_staff else "bookings.index"))
    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You've signed out.", "info")
    return redirect(url_for("public.index"))
