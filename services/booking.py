"""All booking prices and availability are calculated and enforced server-side."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update

from models import Booking, BookingFoodItem, FoodBeverage, Showtime, db
from services.pricing import ticket_price_for


class BookingError(ValueError):
    pass


def create_booking(user, showtime_id, seat_count, requested_items):
    """Reserve seats atomically, including packages, in one database transaction.

    requested_items maps product IDs to integer quantities; prices from the browser
    are never trusted. An UPDATE with an availability condition prevents overselling.
    """
    now = datetime.now()
    showtime = db.session.get(Showtime, showtime_id)
    if showtime is None or showtime.date_time <= now:
        raise BookingError("This screening is no longer available.")
    if seat_count < 1 or seat_count > 5000:
        raise BookingError("Choose between 1 and 5,000 seats.")

    product_ids = [product_id for product_id, quantity in requested_items.items() if quantity > 0]
    products = {}
    if product_ids:
        products = {p.id: p for p in db.session.scalars(
            select(FoodBeverage).where(FoodBeverage.id.in_(product_ids), FoodBeverage.is_active.is_(True))
        ).all()}
        if len(products) != len(product_ids):
            raise BookingError("One or more selected items are no longer available.")

    package_count = sum(quantity for product_id, quantity in requested_items.items()
                        if quantity > 0 and products[product_id].is_package)
    if package_count > seat_count:
        raise BookingError("You cannot add more ticket packages than booked seats.")

    ticket_price = ticket_price_for(showtime)
    total = (seat_count - package_count) * ticket_price
    lines = []
    for product_id, quantity in requested_items.items():
        if quantity == 0:
            continue
        product = products[product_id]
        maximum = 5000 if product.is_package else 30
        if quantity < 0 or quantity > maximum:
            raise BookingError(f"Quantity for {product.name} must be between 0 and {maximum}.")
        if product.is_package and not product.components:
            raise BookingError(f"The {product.name} package is not configured.")
        unit_price = product.price + ticket_price if product.is_package else product.price
        line_price = unit_price * quantity
        details = ""
        if product.is_package:
            details = ", ".join(f"{component.quantity}× {component.food_beverage.name}"
                                 for component in product.components)
        lines.append(BookingFoodItem(
            quantity=quantity, unit_price=unit_price, line_price=line_price,
            name_snapshot=product.name, details_snapshot=details[:600],
            is_package_snapshot=product.is_package, food_beverage_id=product.id
        ))
        total += line_price

    # This single conditional UPDATE is atomic even when simultaneous requests
    # use different database sessions. An unsuccessful request changes nothing.
    updated = db.session.execute(
        update(Showtime)
        .where(Showtime.id == showtime_id, Showtime.remaining_seats >= seat_count)
        .values(remaining_seats=Showtime.remaining_seats - seat_count)
    )
    if updated.rowcount != 1:
        db.session.rollback()
        raise BookingError("Not enough seats remain for this screening.")

    booking = Booking(
        user_id=user.id, showtime_id=showtime_id,
        number_of_seats=seat_count, ticket_unit_price=ticket_price, total_price=total,
        food_items=lines
    )
    db.session.add(booking)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return booking
