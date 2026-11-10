"""Shared validation, authorization and image-upload utilities."""

import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required
from PIL import Image, UnidentifiedImageError

from models import UserRole


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


customer_required = role_required(UserRole.customer)
staff_required = role_required(UserRole.management_staff)


def get_positive_int(value, field, maximum=999):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number.")
    if not (1 <= number <= maximum):
        raise ValueError(f"{field} must be between 1 and {maximum}.")
    return number


def get_nonnegative_int(value, field, maximum=999):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number.")
    if not (0 <= number <= maximum):
        raise ValueError(f"{field} must be between 0 and {maximum}.")
    return number


def get_money(value, field="Price"):
    try:
        amount = Decimal(str(value))
    except (TypeError, InvalidOperation):
        raise ValueError(f"{field} must be a valid monetary amount.")
    if not amount.is_finite() or amount < 0 or amount > Decimal("10000") or amount.as_tuple().exponent < -2:
        raise ValueError(f"{field} must be from €0 to €10,000 with at most two decimals.")
    return amount.quantize(Decimal("0.01"))


def save_poster(upload):
    """Decode and re-encode image uploads so only safe raster files are served."""
    if not upload or not upload.filename:
        return None
    if Path(upload.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Choose a JPG, PNG or WebP poster image.")
    try:
        upload.stream.seek(0)
        with Image.open(upload.stream) as source:
            source.verify()
        upload.stream.seek(0)
        with Image.open(upload.stream) as source:
            if source.width > 4000 or source.height > 6000 or source.width < 100 or source.height < 100:
                raise ValueError("Poster dimensions must be between 100 px and 4000 × 6000 px.")
            converted = source.convert("RGB")
            converted.thumbnail((900, 1350))
            name = uuid.uuid4().hex + ".webp"
            folder = Path(current_app.static_folder) / "uploads" / "posters"
            folder.mkdir(parents=True, exist_ok=True)
            converted.save(folder / name, "WEBP", quality=84)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("That file is not a valid image.")
    return "uploads/posters/" + name
