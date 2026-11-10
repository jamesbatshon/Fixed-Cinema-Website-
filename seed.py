"""Idempotent example catalog and optional management-staff account."""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from sqlalchemy import select

from models import (FoodBeverage, Movie, PackageComponent, Screen, Showtime,
                    TicketPrice, User, UserRole, db)
from services.pricing import WEEKDAYS
from utils import EMAIL_PATTERN


MOVIES = [
    ("The Last Horizon", "A cartographer chases a mysterious signal beyond the edge of the known world, discovering what it means to find home.", 128, "PG-13", "Sci-Fi", "Maya Torres", "Lena Park, Jonah Reed", "2026-09-18", "#6a3cba", "#251343"),
    ("Midnight in Kyoto", "A chance encounter on the last train takes two strangers through a city of secrets, music and surprising connections.", 103, "PG", "Romance", "Elliot Kim", "Nina Wells, Theo Tan", "2026-10-02", "#e37b77", "#542c64"),
    ("Static Bloom", "A young sound engineer finds an impossible frequency woven into her recordings and follows it toward a life-changing revelation.", 111, "12A", "Thriller", "Morgan Vale", "Iris Chen, Luca Hart", "2026-09-25", "#246d88", "#0b2639"),
    ("The Paper Kingdom", "An inventive child enters a city folded from stories where every decision has the power to rewrite the ending.", 96, "PG", "Animation", "Avery Silva", "Featuring an original voice ensemble", "2026-10-10", "#df9a45", "#783f30"),
    ("After the Rain", "An intimate portrait of a family reunited for one summer, learning that forgiveness is rarely a straight road.", 117, "15", "Drama", "Sam Okafor", "Amara Lewis, Gabriel Ruiz", "2026-10-08", "#427e77", "#163f4a"),
    ("Neon Velocity", "When an underground race threatens a citywide blackout, two rival drivers must team up for one impossible last run.", 109, "PG-13", "Action", "Jules Mercer", "David Holt, Sofia Ray", "2026-09-30", "#e26c4b", "#592241"),
]


def make_poster(movie, path):
    title, _, _, _, genre, *_rest, primary, secondary = movie
    words = title.split()
    midpoint = (len(words) + 1) // 2
    title_line_one = escape(" ".join(words[:midpoint]))
    title_line_two = escape(" ".join(words[midpoint:]))
    safe_genre = escape(genre.upper())
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
    <defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="{secondary}"/><stop offset="1" stop-color="{primary}"/></linearGradient>
    <radialGradient id="glow"><stop stop-color="#fff" stop-opacity=".32"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
    <rect width="600" height="900" fill="url(#g)"/>
    <circle cx="440" cy="300" r="310" fill="url(#glow)"/>
    <circle cx="440" cy="300" r="185" fill="none" stroke="#ffffff" stroke-opacity=".25" stroke-width="2"/>
    <circle cx="440" cy="300" r="134" fill="none" stroke="#ffffff" stroke-opacity=".22" stroke-width="2"/>
    <path d="M-120 665L185 335L385 625L620 265L740 760Z" fill="#0a102b" opacity=".45"/>
    <path d="M-70 760L190 535L325 690L505 458L690 735V900H0Z" fill="#070d20" opacity=".55"/>
    <path d="M0 736 Q160 700 300 780 T600 736V900H0Z" fill="#090e21" opacity=".5"/>
    <text x="48" y="65" font-family="Arial,sans-serif" font-size="20" font-weight="bold" letter-spacing="8" fill="#ffffff" opacity=".9">SCREENLANE</text>
    <text x="48" y="690" font-family="Arial,sans-serif" font-size="18" letter-spacing="5" fill="#f7d38e">{safe_genre}</text>
    <text x="47" y="757" font-family="Arial,sans-serif" font-size="54" font-weight="bold" letter-spacing="-2" fill="white">{title_line_one}</text>
    <text x="47" y="813" font-family="Arial,sans-serif" font-size="54" font-weight="bold" letter-spacing="-2" fill="white">{title_line_two}</text>
    <rect x="47" y="851" width="95" height="4" rx="2" fill="#f7d38e"/>
    </svg>'''
    path.write_text(svg, encoding="utf-8")


def seed_cinema(admin_email=None, admin_password=None):
    if admin_email or admin_password:
        if not admin_email or not admin_password:
            raise ValueError("Provide both --admin-email and --admin-password to create staff.")
        if not EMAIL_PATTERN.fullmatch(admin_email.strip()) or len(admin_email) > 255:
            raise ValueError("Staff email address is invalid.")
        if len(admin_password) < 12 or len(admin_password) > 128:
            raise ValueError("Staff password must contain between 12 and 128 characters.")
        email = admin_email.strip().lower()
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing is None:
            staff = User(email=email, role=UserRole.management_staff)
            staff.set_password(admin_password)
            db.session.add(staff)
            print(f"Staff account created: {email}")
        elif existing.role != UserRole.management_staff:
            raise ValueError("That email address already belongs to a customer.")
        else:
            print(f"Existing staff account left unchanged: {email}")

    for day in WEEKDAYS:
        if db.session.scalar(select(TicketPrice).where(TicketPrice.day_of_week == day)) is None:
            amount = "9.50" if day in ("Monday", "Tuesday", "Wednesday", "Thursday") else "13.50"
            db.session.add(TicketPrice(day_of_week=day, price=Decimal(amount)))

    for label, capacity in (("Screen 1 · Grand", 120), ("Screen 2 · Studio", 75), ("Screen 3 · Luxe", 48)):
        if db.session.scalar(select(Screen).where(Screen.identifier == label)) is None:
            db.session.add(Screen(identifier=label, capacity=capacity))

    poster_dir = Path(__file__).parent / "static" / "img" / "posters"
    poster_dir.mkdir(parents=True, exist_ok=True)
    for index, info in enumerate(MOVIES):
        if db.session.scalar(select(Movie).where(Movie.title == info[0])) is None:
            path = poster_dir / f"demo-{index + 1}.svg"
            make_poster(info, path)
            db.session.add(Movie(title=info[0], synopsis=info[1], duration=info[2],
                                age_rating=info[3], genre=info[4], director=info[5],
                                casting=info[6], release_date=info[7],
                                poster=f"img/posters/{path.name}"))
    db.session.flush()

    snacks = [
        ("Classic Popcorn", "Freshly popped, lightly salted.", "4.50", "Popcorn"),
        ("Caramel Popcorn", "Golden caramel-coated kernels.", "5.50", "Popcorn"),
        ("Cola", "Chilled, 500 ml.", "3.50", "Drink"),
        ("Sparkling Water", "Refreshing, 500 ml.", "2.50", "Drink"),
        ("Lemonade", "Chilled citrus lemonade, 500 ml.", "3.50", "Drink"),
        ("Nachos", "Corn chips with cheese sauce.", "6.50", "Snack"),
        ("Chocolate Bites", "A share-sized box of chocolate bites.", "4.00", "Sweet"),
    ]
    for name, description, price, category in snacks:
        if db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == name)) is None:
            db.session.add(FoodBeverage(name=name, description=description,
                                       price=Decimal(price), category=category))
    db.session.flush()
    base = {p.name: p for p in db.session.scalars(select(FoodBeverage).where(FoodBeverage.is_package.is_(False))).all()}
    packages = [
        ("Movie Night Combo", "One ticket, classic popcorn and a cola.", "6.00", [("Classic Popcorn", 1), ("Cola", 1)]),
        ("Sweet Escape", "One ticket, caramel popcorn and chocolate bites.", "7.00", [("Caramel Popcorn", 1), ("Chocolate Bites", 1)]),
        ("Big Screen Feast", "One ticket, nachos, classic popcorn and lemonade.", "10.50", [("Nachos", 1), ("Classic Popcorn", 1), ("Lemonade", 1)]),
    ]
    for name, description, price, components in packages:
        if db.session.scalar(select(FoodBeverage).where(FoodBeverage.name == name)) is None:
            package = FoodBeverage(name=name, description=description, price=Decimal(price),
                                   category="Combo", is_package=True)
            package.components = [PackageComponent(food_beverage_id=base[item].id, quantity=qty)
                                  for item, qty in components]
            db.session.add(package)

    db.session.flush()
    # Showtimes are inserted for each of the coming seven days, without touching
    # already-created screenings when the seed command is rerun.
    movies = db.session.scalars(select(Movie).order_by(Movie.id)).all()
    screens = db.session.scalars(select(Screen).order_by(Screen.id)).all()
    if movies and screens:
        for offset in range(7):
            day = datetime.now().date() + timedelta(days=offset)
            for screen_index, screen in enumerate(screens[:3]):
                for slot_index, hour in enumerate((14, 19)):
                    start = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=0)
                    if start <= datetime.now() + timedelta(minutes=45):
                        continue
                    if db.session.scalar(select(Showtime.id).where(
                        Showtime.screen_id == screen.id, Showtime.date_time == start)) is not None:
                        continue
                    movie = movies[(screen_index * 2 + slot_index + offset) % len(movies)]
                    db.session.add(Showtime(movie_id=movie.id, screen_id=screen.id,
                                            date_time=start, remaining_seats=screen.capacity))
    db.session.commit()
    print("Cinema sample catalog, ticket prices, screens, and showtimes are ready.")
    if not admin_email:
        print("No staff account created. Rerun seed with --admin-email and --admin-password to create one.")
