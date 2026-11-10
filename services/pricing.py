"""Weekday-dependent ticket prices and package price calculations."""

from decimal import Decimal

from sqlalchemy import select

from models import TicketPrice, db

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def ticket_price_for(showtime):
    day = WEEKDAYS[showtime.date_time.weekday()]
    price = db.session.scalar(select(TicketPrice).where(TicketPrice.day_of_week == day))
    if price is None:
        raise ValueError(f"Ticket pricing has not been configured for {day}.")
    return price.price


def package_unit_price(showtime, package):
    """Each package includes ONE ticket plus its discounted snack bundle."""
    return ticket_price_for(showtime) + package.price


def package_retail_food_total(package):
    return sum((entry.food_beverage.price * entry.quantity for entry in package.components), Decimal("0.00"))
