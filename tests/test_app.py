"""Integration tests for required features and security boundaries."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from models import Booking, FoodBeverage, Showtime, User, UserRole, db


def test_public_movie_browsing(client):
    homepage = client.get("/")
    assert homepage.status_code == 200
    assert b"Test Movie" in homepage.data
    detail = client.get("/movies/1")
    assert detail.status_code == 200
    assert b"Choose a showtime" in detail.data


def test_register_hashes_password_and_uses_customer_role(client, app):
    response = client.post("/account/register", data={
        "email": "NEW@EXAMPLE.COM", "password": "my-strong-password-123",
        "confirm_password": "my-strong-password-123"
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == "new@example.com"))
        assert user is not None
        assert user.role == UserRole.customer
        assert user.password != "my-strong-password-123"
        assert user.check_password("my-strong-password-123")


def test_login_rejects_wrong_password(client):
    response = client.post("/account/login", data={
        "email": "staff@example.com", "password": "wrong-password"
    }, follow_redirects=True)
    assert b"Incorrect email or password" in response.data
    assert client.get("/admin/").status_code == 302


def test_customer_cannot_access_admin(customer_login):
    assert customer_login.get("/admin/").status_code == 403
    assert customer_login.post("/admin/screens/new", data={
        "identifier": "Not allowed", "capacity": 50
    }).status_code == 403


def test_staff_cannot_book_seats(staff_login):
    assert staff_login.post("/bookings/new/1", data={"number_of_seats": "1"}).status_code == 403
    assert staff_login.get("/bookings/").status_code == 403
    assert staff_login.get("/admin/").status_code == 200


def test_booking_package_ticket_and_food_total(customer_login, app):
    with app.app_context():
        combo_id = db.session.scalar(select(FoodBeverage.id).where(FoodBeverage.is_package.is_(True)))
        popcorn_id = db.session.scalar(select(FoodBeverage.id).where(FoodBeverage.name == "Popcorn"))
    response = customer_login.post("/bookings/new/1", data={
        "number_of_seats": "3", f"product_{combo_id}": "2", f"product_{popcorn_id}": "1"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"RESERVATION CONFIRMED" in response.data
    with app.app_context():
        booking = db.session.scalar(select(Booking))
        # 1 regular seat (€10) + 2 ticket/food combos (€15 each) + popcorn (€4.50).
        assert booking.total_price == Decimal("44.50")
        assert booking.regular_ticket_count == 1
        assert booking.package_ticket_count == 2
        assert db.session.get(Showtime, 1).remaining_seats == 2


def test_cannot_oversell(customer_login, app):
    response = customer_login.post("/bookings/new/1", data={"number_of_seats": "6"},
                                   follow_redirects=True)
    assert b"Not enough seats remain" in response.data
    with app.app_context():
        assert db.session.scalar(select(Booking.id)) is None
        assert db.session.get(Showtime, 1).remaining_seats == 5


def test_package_quantity_cannot_exceed_seats(customer_login, app):
    with app.app_context():
        combo_id = db.session.scalar(select(FoodBeverage.id).where(FoodBeverage.is_package.is_(True)))
    response = customer_login.post("/bookings/new/1", data={
        "number_of_seats": "1", f"product_{combo_id}": "2"
    }, follow_redirects=True)
    assert b"cannot add more ticket packages" in response.data
    with app.app_context():
        assert db.session.get(Showtime, 1).remaining_seats == 5


def test_customer_cannot_read_someone_elses_booking(client, app):
    with app.app_context():
        original = db.session.get(User, 1)
        from services.booking import create_booking
        booking = create_booking(original, 1, 1, {})
        booking_id = booking.id
    client.post("/account/register", data={
        "email": "other@example.com", "password": "passphrase-unique-123",
        "confirm_password": "passphrase-unique-123"
    })
    assert client.get(f"/bookings/{booking_id}").status_code == 404


def test_staff_can_add_movie_and_showtime(staff_login, app):
    response = staff_login.post("/admin/movies/new", data={
        "title": "New Feature", "synopsis": "New film description", "duration": "119",
        "age_rating": "PG", "genre": "Comedy", "director": "Someone"
    }, follow_redirects=True)
    assert b"New Feature" in response.data
    with app.app_context():
        from models import Movie
        movie = db.session.scalar(select(Movie).where(Movie.title == "New Feature"))
        movie_id = movie.id
    future = (datetime.now() + timedelta(days=10)).replace(hour=21, minute=30).strftime("%Y-%m-%dT%H:%M")
    response = staff_login.post("/admin/showtimes/new", data={
        "movie_id": str(movie_id), "screen_id": "1", "date_time": future
    }, follow_redirects=True)
    assert b"Showtime scheduled" in response.data


def test_staff_can_update_weekday_ticket_prices(staff_login, app):
    from services.pricing import WEEKDAYS
    values = {day: "16.50" for day in WEEKDAYS}
    response = staff_login.post("/admin/pricing", data=values, follow_redirects=True)
    assert b"Weekly ticket prices updated" in response.data
    with app.app_context():
        from models import TicketPrice
        prices = db.session.scalars(select(TicketPrice)).all()
        assert len(prices) == 7
        assert all(item.price == Decimal("16.50") for item in prices)


def test_inactive_product_cannot_be_purchased(customer_login, app):
    with app.app_context():
        product = db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == "Popcorn"))
        product.is_active = False
        product_id = product.id
        db.session.commit()
    response = customer_login.post("/bookings/new/1", data={
        "number_of_seats": "1", f"product_{product_id}": "1"
    }, follow_redirects=True)
    assert b"not available" in response.data


def test_csrf_rejects_post_without_token(app):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    assert client.post("/account/register", data={
        "email": "new@example.com", "password": "password-12345",
        "confirm_password": "password-12345"
    }).status_code == 400


def test_movie_escaped_in_template(client, app):
    from models import Movie
    with app.app_context():
        db.session.add(Movie(title="<script>alert(1)</script>", synopsis="Safe film",
                             duration=100, age_rating="PG", casting="", genre="", director="", release_date=""))
        db.session.commit()
    response = client.get("/")
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
    assert b"<script>alert(1)</script>" not in response.data


def test_deactivating_snack_disables_packages_containing_it(staff_login, app):
    with app.app_context():
        popcorn = db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == "Popcorn"))
        popcorn_id = popcorn.id
    response = staff_login.post(f"/admin/products/{popcorn_id}/deactivate", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        popcorn = db.session.get(FoodBeverage, popcorn_id)
        package = db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == "Snack Combo"))
        assert not popcorn.is_active
        assert not package.is_active


def test_showtime_room_cannot_have_overlapping_movies(staff_login, app):
    with app.app_context():
        current = db.session.get(Showtime, 1)
        overlap = (current.date_time + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
    response = staff_login.post("/admin/showtimes/new", data={
        "movie_id": "1", "screen_id": "1", "date_time": overlap
    }, follow_redirects=True)
    assert b"screen is already occupied" in response.data
    with app.app_context():
        assert len(db.session.scalars(select(Showtime)).all()) == 1


def test_staff_can_create_discounted_package(staff_login, app):
    with app.app_context():
        popcorn_id = db.session.scalar(select(FoodBeverage.id).where(FoodBeverage.name == "Popcorn"))
        cola_id = db.session.scalar(select(FoodBeverage.id).where(FoodBeverage.name == "Cola"))
    response = staff_login.post("/admin/products/new", data={
        "kind": "package", "name": "Family Snack Pack", "description": "An admission and two snacks",
        "price": "5.50", "category": "Combo", "is_active": "on",
        f"component_{popcorn_id}": "1", f"component_{cola_id}": "1"
    }, follow_redirects=True)
    assert b"Family Snack Pack" in response.data
    with app.app_context():
        package = db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == "Family Snack Pack"))
        assert package.is_package
        assert len(package.components) == 2
