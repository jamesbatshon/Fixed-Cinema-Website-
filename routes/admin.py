"""Staff-only catalog, screen, screening and pricing management."""

from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from models import (Booking, FoodBeverage, Movie, PackageComponent, Screen,
                    Showtime, TicketPrice, User, UserRole, db)
from services.pricing import WEEKDAYS, package_retail_food_total
from utils import (get_money, get_nonnegative_int, get_positive_int,
                   save_poster, staff_required)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@staff_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        movie_count=db.session.scalar(select(func.count(Movie.id))) or 0,
        upcoming_count=db.session.scalar(select(func.count(Showtime.id)).where(Showtime.date_time >= datetime.now())) or 0,
        booking_count=db.session.scalar(select(func.count(Booking.id))) or 0,
        customer_count=db.session.scalar(select(func.count(User.id)).where(User.role == UserRole.customer)) or 0,
        showtimes=db.session.scalars(
            select(Showtime).options(joinedload(Showtime.movie), joinedload(Showtime.screen))
            .where(Showtime.date_time >= datetime.now())
            .order_by(Showtime.date_time).limit(6)
        ).all(),
    )


@bp.get("/movies")
@staff_required
def movies():
    return render_template("admin/movies.html", movies=db.session.scalars(
        select(Movie).order_by(Movie.created_at.desc(), Movie.id.desc())
    ).all())


@bp.route("/movies/new", methods=["GET", "POST"])
@staff_required
def movie_new():
    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            synopsis = request.form.get("synopsis", "").strip()
            duration = get_positive_int(request.form.get("duration"), "Duration", 600)
            rating = request.form.get("age_rating", "").strip()
            if not 1 <= len(title) <= 160 or not 1 <= len(synopsis) <= 5000:
                raise ValueError("Enter a title (up to 160 characters) and synopsis (up to 5000 characters).")
            if not 1 <= len(rating) <= 16:
                raise ValueError("An age rating is required (up to 16 characters).")
            fields = {name: request.form.get(name, "").strip() for name in
                      ("genre", "director", "casting", "release_date")}
            for name, value, max_len in (("genre", fields["genre"], 120),
                                         ("director", fields["director"], 160),
                                         ("casting", fields["casting"], 500),
                                         ("release_date", fields["release_date"], 20)):
                if len(value) > max_len:
                    raise ValueError(f"{name.capitalize()} is too long.")
            poster = save_poster(request.files.get("poster")) or "img/placeholder_poster.svg"
            movie = Movie(title=title, synopsis=synopsis, duration=duration,
                          age_rating=rating, poster=poster, **fields)
            db.session.add(movie)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Movie added successfully.", "success")
            return redirect(url_for("admin.movies"))
    return render_template("admin/movie_form.html")


@bp.route("/movies/<int:movie_id>/edit", methods=["GET", "POST"])
@staff_required
def movie_edit(movie_id):
    """Preview changes in the browser; persist only after a staff member saves."""
    movie = db.get_or_404(Movie, movie_id)
    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            genre = request.form.get("genre", "").strip()
            age_rating = request.form.get("age_rating", "").strip()

            if not 1 <= len(title) <= 160:
                raise ValueError("Movie title must contain 1 to 160 characters.")
            if len(genre) > 120:
                raise ValueError("Genre must contain no more than 120 characters.")
            if not 1 <= len(age_rating) <= 16:
                raise ValueError("Age rating must contain 1 to 16 characters.")

            # Validating the entire form before assigning anything prevents
            # a failed upload from leaving partially updated movie metadata.
            new_poster = save_poster(request.files.get("poster"))
            movie.title = title
            movie.genre = genre
            movie.age_rating = age_rating
            if new_poster:
                movie.poster = new_poster
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(f"{movie.title} updated successfully.", "success")
            return redirect(url_for("admin.movies"))

    return render_template("admin/movie_edit.html", movie=movie)


@bp.get("/screens")
@staff_required
def screens():
    return render_template("admin/screens.html", screens=db.session.scalars(
        select(Screen).order_by(Screen.identifier)
    ).all())


@bp.post("/screens/new")
@staff_required
def screen_new():
    try:
        identifier = request.form.get("identifier", "").strip()
        if not 1 <= len(identifier) <= 80:
            raise ValueError("Enter a screen name of up to 80 characters.")
        capacity = get_positive_int(request.form.get("capacity"), "Capacity", 5000)
        db.session.add(Screen(identifier=identifier, capacity=capacity))
        db.session.commit()
    except (ValueError, IntegrityError) as error:
        db.session.rollback()
        flash("That screen name is already in use." if isinstance(error, IntegrityError) else str(error), "error")
    else:
        flash("Screen added.", "success")
    return redirect(url_for("admin.screens"))


@bp.get("/showtimes")
@staff_required
def showtimes():
    items = db.session.scalars(
        select(Showtime).options(joinedload(Showtime.movie), joinedload(Showtime.screen))
        .order_by(Showtime.date_time.desc()).limit(250)
    ).all()
    return render_template("admin/showtimes.html", showtimes=items)


@bp.route("/showtimes/new", methods=["GET", "POST"])
@staff_required
def showtime_new():
    movies = db.session.scalars(select(Movie).order_by(Movie.title)).all()
    screens = db.session.scalars(select(Screen).order_by(Screen.identifier)).all()
    if request.method == "POST":
        try:
            movie = db.session.get(Movie, get_positive_int(request.form.get("movie_id"), "Movie"))
            screen = db.session.get(Screen, get_positive_int(request.form.get("screen_id"), "Screen"))
            if movie is None or screen is None:
                raise ValueError("Select a valid movie and screen.")
            try:
                start = datetime.strptime(request.form.get("date_time", ""), "%Y-%m-%dT%H:%M")
            except ValueError:
                raise ValueError("Enter a valid screening date and time.")
            if start <= datetime.now():
                raise ValueError("Screenings must be scheduled in the future.")
            if start > datetime.now() + timedelta(days=365):
                raise ValueError("Screenings may be scheduled at most one year ahead.")
            end = start + timedelta(minutes=movie.duration + 15)
            occupied = db.session.scalars(
                select(Showtime).options(joinedload(Showtime.movie))
                .where(Showtime.screen_id == screen.id,
                       Showtime.date_time > start - timedelta(hours=12),
                       Showtime.date_time < end)
            ).all()
            for existing in occupied:
                existing_end = existing.date_time + timedelta(minutes=existing.movie.duration + 15)
                if start < existing_end and existing.date_time < end:
                    raise ValueError("The screen is already occupied at that time (including a 15-minute turnover).")
            db.session.add(Showtime(date_time=start, movie_id=movie.id,
                                    screen_id=screen.id, remaining_seats=screen.capacity))
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Showtime scheduled.", "success")
            return redirect(url_for("admin.showtimes"))
    return render_template("admin/showtime_form.html", movies=movies, screens=screens)


@bp.get("/products")
@staff_required
def products():
    items = db.session.scalars(
        select(FoodBeverage).options(selectinload(FoodBeverage.components).joinedload(PackageComponent.food_beverage))
        .order_by(FoodBeverage.is_package.desc(), FoodBeverage.name)
    ).all()
    return render_template("admin/products.html", products=items,
                           package_retail_food_total=package_retail_food_total)


def disable_invalid_packages_for(item):
    """Do not offer bundles containing unavailable or non-discounted food."""
    if item.is_package:
        return
    affected = db.session.scalars(
        select(FoodBeverage)
        .join(PackageComponent, PackageComponent.package_id == FoodBeverage.id)
        .where(PackageComponent.food_beverage_id == item.id,
               FoodBeverage.is_package.is_(True), FoodBeverage.is_active.is_(True))
    ).all()
    for package in affected:
        if not item.is_active or package.price >= package_retail_food_total(package):
            package.is_active = False


def product_form_values(product, standalone):
    """Validate form fields and construct new package components."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Snack").strip()
    price = get_money(request.form.get("price"), "Price")
    if not 1 <= len(name) <= 120 or len(description) > 1000 or not 1 <= len(category) <= 50:
        raise ValueError("Use a name (max 120), description (max 1000) and category (max 50).")
    if product is None:
        kind = request.form.get("kind", "item")
        if kind not in ("item", "package"):
            raise ValueError("Choose a valid product type.")
        product = FoodBeverage(is_package=(kind == "package"))
    product.name = name
    product.description = description
    product.category = category
    product.price = price
    product.is_active = request.form.get("is_active") == "on"

    if product.is_package:
        components = []
        retail = 0
        for item in standalone:
            quantity = get_nonnegative_int(request.form.get(f"component_{item.id}", "0"),
                                           f"Quantity for {item.name}", 20)
            if quantity:
                if not item.is_active:
                    raise ValueError(f"{item.name} is not available for new packages.")
                components.append(PackageComponent(food_beverage_id=item.id, quantity=quantity))
                retail += item.price * quantity
        if not components:
            raise ValueError("A ticket package must contain at least one snack or drink.")
        if price >= retail:
            raise ValueError(f"Discounted food add-on must cost less than the regular food total (€{retail:.2f}).")
        product.components = components
    return product


@bp.route("/products/new", methods=["GET", "POST"])
@staff_required
def product_new():
    standalone = db.session.scalars(select(FoodBeverage).where(FoodBeverage.is_package.is_(False))
                                    .order_by(FoodBeverage.name)).all()
    if request.method == "POST":
        try:
            product = product_form_values(None, standalone)
            db.session.add(product)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Catalog item created.", "success")
            return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", product=None, standalone=standalone)


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@staff_required
def product_edit(product_id):
    product = db.get_or_404(FoodBeverage, product_id)
    standalone = db.session.scalars(select(FoodBeverage).where(FoodBeverage.is_package.is_(False))
                                    .order_by(FoodBeverage.name)).all()
    if request.method == "POST":
        try:
            product_form_values(product, standalone)
            disable_invalid_packages_for(product)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Catalog item updated.", "success")
            return redirect(url_for("admin.products"))
    quantities = {entry.food_beverage_id: entry.quantity for entry in product.components}
    return render_template("admin/product_form.html", product=product,
                           standalone=standalone, quantities=quantities)


@bp.post("/products/<int:product_id>/deactivate")
@staff_required
def product_deactivate(product_id):
    product = db.get_or_404(FoodBeverage, product_id)
    product.is_active = False
    disable_invalid_packages_for(product)
    db.session.commit()
    flash(f"{product.name} is no longer on sale. Previous bookings are preserved.", "info")
    return redirect(url_for("admin.products"))


@bp.route("/pricing", methods=["GET", "POST"])
@staff_required
def pricing():
    existing = {item.day_of_week: item for item in db.session.scalars(select(TicketPrice)).all()}
    if request.method == "POST":
        try:
            parsed = {day: get_money(request.form.get(day), f"{day} price") for day in WEEKDAYS}
            for day, price in parsed.items():
                if day in existing:
                    existing[day].price = price
                else:
                    db.session.add(TicketPrice(day_of_week=day, price=price))
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Weekly ticket prices updated.", "success")
            return redirect(url_for("admin.pricing"))
    return render_template("admin/pricing.html", weekdays=WEEKDAYS, prices=existing)
