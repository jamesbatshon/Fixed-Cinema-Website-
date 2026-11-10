"""Test app and database fixtures."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import create_app
from models import (FoodBeverage, Movie, PackageComponent, Screen, Showtime,
                    TicketPrice, User, UserRole, db)
from services.pricing import WEEKDAYS


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "unit-tests-only-fixed-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        customer = User(email="customer@example.com", role=UserRole.customer)
        customer.set_password("customer-password-123")
        staff = User(email="staff@example.com", role=UserRole.management_staff)
        staff.set_password("staff-password-123")
        screen = Screen(identifier="Test Screen", capacity=5)
        movie = Movie(title="Test Movie", synopsis="A great movie.", duration=100,
                      age_rating="PG", genre="Drama", casting="", director="", release_date="")
        db.session.add_all([customer, staff, screen, movie])
        db.session.flush()
        showtime = Showtime(date_time=datetime.now() + timedelta(days=2),
                            movie_id=movie.id, screen_id=screen.id, remaining_seats=5)
        db.session.add(showtime)
        for weekday in WEEKDAYS:
            db.session.add(TicketPrice(day_of_week=weekday, price=Decimal("10.00")))
        popcorn = FoodBeverage(name="Popcorn", description="Crispy", price=Decimal("4.50"), category="Popcorn")
        cola = FoodBeverage(name="Cola", description="Cold", price=Decimal("3.50"), category="Drink")
        db.session.add_all([popcorn, cola])
        db.session.flush()
        combo = FoodBeverage(name="Snack Combo", description="Ticket and snacks",
                             price=Decimal("5.00"), is_package=True, category="Combo")
        combo.components = [PackageComponent(food_beverage_id=popcorn.id, quantity=1),
                            PackageComponent(food_beverage_id=cola.id, quantity=1)]
        db.session.add(combo)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def customer_login(client):
    response = client.post("/account/login", data={
        "email": "customer@example.com", "password": "customer-password-123"
    }, follow_redirects=True)
    assert response.status_code == 200
    return client


@pytest.fixture
def staff_login(client):
    response = client.post("/account/login", data={
        "email": "staff@example.com", "password": "staff-password-123"
    }, follow_redirects=True)
    assert response.status_code == 200
    return client
