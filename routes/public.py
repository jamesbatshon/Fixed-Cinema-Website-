"""Public movie listings and screening information."""

from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from models import FoodBeverage, Movie, Showtime, db
from services.pricing import package_retail_food_total, ticket_price_for

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    now = datetime.now()
    cutoff = now + timedelta(days=7)
    screenings = db.session.scalars(
        select(Showtime).options(joinedload(Showtime.movie), joinedload(Showtime.screen))
        .where(Showtime.date_time >= now, Showtime.date_time < cutoff)
        .order_by(Showtime.date_time)
    ).all()
    movie_ids = {screening.movie_id for screening in screenings}
    movies = db.session.scalars(select(Movie).order_by(Movie.title)).all()
    grouped = defaultdict(list)
    for screening in screenings:
        grouped[screening.movie_id].append(screening)
    genres = sorted({movie.genre for movie in movies if movie.genre})
    return render_template("index.html", movies=movies, grouped=grouped,
                           now=now, genres=genres, movie_ids=movie_ids)


@bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    showtimes = db.session.scalars(
        select(Showtime).options(joinedload(Showtime.screen))
        .where(Showtime.movie_id == movie_id, Showtime.date_time > datetime.now())
        .order_by(Showtime.date_time)
    ).all()
    grouped = defaultdict(list)
    for screening in showtimes:
        grouped[screening.date_time.date()].append(screening)
    return render_template("movie_detail.html", movie=movie, grouped=grouped)


@bp.get("/showtimes/<int:showtime_id>")
def showtime_detail(showtime_id):
    showtime = db.get_or_404(Showtime, showtime_id)
    if showtime.date_time <= datetime.now():
        flash("That screening has already started.", "info")
        return redirect(url_for("public.movie_detail", movie_id=showtime.movie_id))
    products = db.session.scalars(
        select(FoodBeverage).where(FoodBeverage.is_active.is_(True)).order_by(FoodBeverage.is_package.desc(), FoodBeverage.name)
    ).all()
    if any(product.is_package and not product.components for product in products):
        products = [product for product in products if not product.is_package or product.components]
    try:
        ticket_price = ticket_price_for(showtime)
    except ValueError:
        ticket_price = None
    packages = [p for p in products if p.is_package]
    snacks = [p for p in products if not p.is_package]
    return render_template("showtime_detail.html", showtime=showtime,
                           ticket_price=ticket_price, packages=packages, snacks=snacks,
                           package_retail_food_total=package_retail_food_total)
