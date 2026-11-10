"""Database tables and relationships for the Screenlane cinema."""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class UserRole(enum.Enum):
    customer = "customer"
    management_staff = "management_staff"


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    # Passwords are stored as salted, one-way hashes, never as plaintext.
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(db.Enum(UserRole), default=UserRole.customer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    @property
    def is_staff(self) -> bool:
        return self.role == UserRole.management_staff


class Movie(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(160), nullable=False)
    synopsis: Mapped[str] = mapped_column(db.Text, nullable=False)
    duration: Mapped[int] = mapped_column(nullable=False)
    age_rating: Mapped[str] = mapped_column(db.String(16), nullable=False)
    casting: Mapped[str] = mapped_column(db.String(500), default="", nullable=False)
    genre: Mapped[str] = mapped_column(db.String(120), default="", nullable=False)
    director: Mapped[str] = mapped_column(db.String(160), default="", nullable=False)
    release_date: Mapped[str] = mapped_column(db.String(20), default="", nullable=False)
    poster: Mapped[str] = mapped_column(db.String(255), default="img/placeholder_poster.svg", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    showtimes: Mapped[list["Showtime"]] = relationship(back_populates="movie")
    __table_args__ = (CheckConstraint("duration > 0", name="valid_duration"),)


class Screen(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(db.String(80), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)

    showtimes: Mapped[list["Showtime"]] = relationship(back_populates="screen")
    __table_args__ = (CheckConstraint("capacity > 0", name="valid_capacity"),)


class FoodBeverage(db.Model):
    """For a package, price is the discounted food add-on price per ticket."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    is_package: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    category: Mapped[str] = mapped_column(db.String(50), default="Snack", nullable=False)

    components: Mapped[list["PackageComponent"]] = relationship(
        back_populates="package", foreign_keys="PackageComponent.package_id",
        cascade="all, delete-orphan", order_by="PackageComponent.id"
    )
    __table_args__ = (CheckConstraint("price >= 0", name="valid_food_price"),)


class PackageComponent(db.Model):
    """Quantity of a standalone snack/drink included with ONE package ticket."""

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("food_beverage.id"), nullable=False)
    food_beverage_id: Mapped[int] = mapped_column(ForeignKey("food_beverage.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    package: Mapped["FoodBeverage"] = relationship(
        back_populates="components", foreign_keys=[package_id]
    )
    food_beverage: Mapped["FoodBeverage"] = relationship(foreign_keys=[food_beverage_id])
    __table_args__ = (
        CheckConstraint("quantity > 0", name="valid_component_quantity"),
        UniqueConstraint("package_id", "food_beverage_id", name="uq_package_item"),
    )


class Showtime(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    date_time: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movie.id"), nullable=False)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screen.id"), nullable=False)
    # Snapshot of the screen capacity. Updated atomically during ticket purchases.
    remaining_seats: Mapped[int] = mapped_column(nullable=False)

    movie: Mapped["Movie"] = relationship(back_populates="showtimes")
    screen: Mapped["Screen"] = relationship(back_populates="showtimes")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="showtime")
    __table_args__ = (
        CheckConstraint("remaining_seats >= 0", name="nonnegative_remaining_seats"),
        Index("ix_showtime_screen_datetime", "screen_id", "date_time"),
    )

    @property
    def booked_seats(self) -> int:
        return self.screen.capacity - self.remaining_seats


class TicketPrice(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[str] = mapped_column(db.String(12), unique=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    __table_args__ = (CheckConstraint("price >= 0", name="valid_ticket_price"),)


class Booking(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    number_of_seats: Mapped[int] = mapped_column(nullable=False)
    ticket_unit_price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    booking_time: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtime.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bookings")
    showtime: Mapped["Showtime"] = relationship(back_populates="bookings")
    food_items: Mapped[list["BookingFoodItem"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )
    __table_args__ = (CheckConstraint("number_of_seats > 0", name="positive_booking_seats"),)

    @property
    def package_ticket_count(self) -> int:
        return sum(item.quantity for item in self.food_items if item.is_package_snapshot)

    @property
    def regular_ticket_count(self) -> int:
        return self.number_of_seats - self.package_ticket_count


class BookingFoodItem(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    line_price: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    # Snapshots keep historical receipts correct after staff edit or deactivate items.
    name_snapshot: Mapped[str] = mapped_column(db.String(120), nullable=False)
    details_snapshot: Mapped[str] = mapped_column(db.String(600), default="", nullable=False)
    is_package_snapshot: Mapped[bool] = mapped_column(default=False, nullable=False)

    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id"), nullable=False)
    food_beverage_id: Mapped[int] = mapped_column(ForeignKey("food_beverage.id"), nullable=False)

    booking: Mapped["Booking"] = relationship(back_populates="food_items")
    food_beverage: Mapped["FoodBeverage"] = relationship()
    __table_args__ = (CheckConstraint("quantity > 0", name="positive_food_quantity"),)
