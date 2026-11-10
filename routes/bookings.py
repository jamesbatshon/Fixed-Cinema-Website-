"""Customer-only booking creation and private booking history."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from models import Booking, FoodBeverage, Showtime, db
from services.booking import BookingError, create_booking
from utils import customer_required, get_nonnegative_int, get_positive_int

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bp.get("/")
@customer_required
def index():
    booking_list = db.session.scalars(
        select(Booking).options(joinedload(Booking.showtime).joinedload(Showtime.movie))
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.booking_time.desc())
    ).all()
    now = datetime.now()
    upcoming = sorted([b for b in booking_list if b.showtime.date_time >= now],
                      key=lambda b: b.showtime.date_time)
    past = [b for b in booking_list if b.showtime.date_time < now]
    return render_template("bookings/index.html", upcoming=upcoming, past=past)


@bp.get("/<int:booking_id>")
@customer_required
def detail(booking_id):
    # Ownership is enforced in the SQL query, not just hidden in templates.
    booking = db.session.scalar(
        select(Booking).options(
            joinedload(Booking.showtime).joinedload(Showtime.movie),
            joinedload(Booking.showtime).joinedload(Showtime.screen),
            selectinload(Booking.food_items)
        ).where(Booking.id == booking_id, Booking.user_id == current_user.id)
    )
    if booking is None:
        from flask import abort
        abort(404)
    return render_template("bookings/detail.html", booking=booking)


@bp.post("/new/<int:showtime_id>")
@customer_required
def create(showtime_id):
    showtime = db.get_or_404(Showtime, showtime_id)
    try:
        seat_count = get_positive_int(request.form.get("number_of_seats"), "Seat count", 5000)
        available = {
            item.id: item for item in db.session.scalars(
                select(FoodBeverage).where(FoodBeverage.is_active.is_(True))
            ).all()
        }
        choices = {}
        for product_id, product in available.items():
            key = f"product_{product_id}"
            max_quantity = 5000 if product.is_package else 30
            quantity = get_nonnegative_int(request.form.get(key, "0"), "Food quantity", max_quantity)
            if quantity:
                choices[product_id] = quantity
        # Prevent arbitrary submitted product IDs from being silently ignored.
        for key in request.form:
            if key.startswith("product_") and (not key[8:].isdigit() or int(key[8:]) not in available):
                raise BookingError("A selected item is not available.")
        booking = create_booking(current_user, showtime_id, seat_count, choices)
    except (ValueError, BookingError) as error:
        db.session.rollback()
        flash(str(error), "error")
        return redirect(url_for("public.showtime_detail", showtime_id=showtime_id))
    flash("Your seats are reserved! Pay at the cinema when you arrive.", "success")
    return redirect(url_for("bookings.detail", booking_id=booking.id))
