# Screenlane — Cinema Booking Website

A complete, customizable Python/Flask cinema application with responsive HTML/CSS, SQLite database, SQLAlchemy ORM, customer accounts, booking logic, food bundles and a staff management dashboard.

**Classic cinema edition:** Restyled from the basic prototype you supplied: black navigation bar, charcoal cards, red headings and buttons, compact movie grid and simplified forms. All original customer and management features remain part of the application.

> **Development project:** The default configuration is for local development. Configure HTTPS, persistent secrets, backups and production-grade hosting before exposing it publicly.

## Features

| Customer / visitor | Management staff |
| --- | --- |
| See all movies and search by title or genre | Add movies, including poster images |
| See details and future showtimes by day | Add screens and set their seating capacities |
| Register and sign in securely | Schedule screenings in specific rooms |
| Reserve one or more available seats without choosing seat numbers | Reject overlapping screen schedules (15-minute turnover) |
| Get a ticket price based on screening weekday | Update ticket prices for Monday–Sunday |
| Book discounted one-ticket-and-food bundles | Add and edit drinks, snacks and ticket bundles |
| Add individual snacks and drinks | Deactivate menu items while preserving historic receipts |
| View upcoming bookings and past receipts | See an overview of screenings and customers |
| Pay on arrival, no card information required | Staff access is restricted by server-side role checks |

### Booking package pricing

Each package includes **one admission ticket** plus bundled snacks/drinks. Its stored `FoodBeverage.price` is the **discounted FOOD add-on**, not the admission charge.

Example with admission €10 and popcorn (€4.50) + cola (€3.50) package food add-on €6:

- One regular ticket: €10.
- One combo ticket: €10 ticket + €6 discounted food = **€16** (instead of €18 separately).
- Three seats with two combos: 1 × €10 regular ticket + 2 × €16 combos = **€42**.
- Any separately booked extras are then added. Packages may not exceed the seat count.

All prices and availability checks are recalculated **on the server**. Changing browser input values cannot change prices.

## Requirements

- Python **3.11 or newer** (3.12/3.13 are suitable)
- pip
- No separate database server: SQLite is included in Python

## Installation in VS Code (Windows PowerShell)

Open the extracted `screenlane` folder in VS Code. Open **Terminal → New Terminal** (PowerShell) and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt, then run `.venv\Scripts\activate.bat`, or configure VS Code to use `.venv\Scripts\python.exe` and run `python` in that environment.

**WSL / Linux / macOS**, if you prefer that environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Set a session secret

Set an unpredictable secret for Flask sessions and CSRF tokens. You can generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

PowerShell example (replace the example value with the generated string):

```powershell
$env:SECRET_KEY="paste-your-generated-secret-here"
```

Linux/macOS/WSL:

```bash
export SECRET_KEY="paste-your-generated-secret-here"
```

For a local experiment, the app also generates a random secret if the variable isn't set, but it will invalidate sessions when you restart the server. Keep a stable secret across restarts.

### Create and seed the database

```bash
python main.py init
python main.py seed --admin-email manager@example.com --admin-password "ReplaceWithAVeryLongUniquePassword2026"
```

The `seed` command creates **7 weekday prices, 3 screens, example films, illustrated posters, food, drinks, discounted packages and a week of showtimes**. It also creates a management-staff account with the email/password you provide. Change these sample credentials.

Seed is generally safe to rerun: it avoids duplicate named example records. Staff passwords are **not** reset when reseeding.

If you omit the admin credentials, the sample content is created but **no staff account** is added. Customer sign-up cannot create staff accounts.

### Start the site

```bash
python app.py
```

Open **http://127.0.0.1:5000/** in your browser.

- To access staff tools: **Log in** using your `--admin-email` and `--admin-password`, then open **Staff dashboard**.
- To test booking: **Sign up** with a different customer email, choose a film/showtime and reserve tickets.
- Database file: `instance/cinema.db` by default.
- Uploaded posters: `static/uploads/posters/`.

The first run works with the samples; if you call `python main.py init` only, the app starts with an empty catalog until staff create records.

## Project structure

```text
screenlane/
├── app.py                      # Flask app factory and security configuration
├── main.py                     # Initialize database / seed data
├── models.py                   # Tables and ORM relationships
├── seed.py                     # Idempotent sample content
├── utils.py                    # Validation, roles and poster safety
├── requirements.txt
├── routes/
│   ├── auth.py                 # Register, login, logout
│   ├── public.py               # Movie and screening pages
│   ├── bookings.py             # Customer bookings + ownership checks
│   └── admin.py                # Staff-only management views
├── services/
│   ├── pricing.py              # Day-of-week ticket prices
│   └── booking.py              # Pricing and atomic reservation transaction
├── templates/
│   ├── base.html               # Shared site header/nav/footer
│   ├── index.html
│   ├── movie_detail.html
│   ├── showtime_detail.html
│   ├── auth/                   # Login, sign-up
│   ├── bookings/               # Booking list, reservation receipt
│   ├── admin/                  # Staff dashboard and editors
│   └── errors/                 # Consistent errors
├── static/
│   ├── css/styles.css          # Original layout and component foundations
│   ├── css/classic-cinema.css  # NEW: black / charcoal / red theme
│   ├── js/main.js              # Search, inputs and price preview
│   ├── img/                    # Posters and fallback artwork
│   └── uploads/posters/        # Re-encoded user-uploaded posters
└── tests/
    ├── conftest.py
    └── test_app.py
```

## How to customize the website

**Colours / type / shape:** Edit the variables inside `:root { ... }` at the **top** of `static/css/classic-cinema.css`. This theme loads after the original `styles.css`, so its settings take priority.

The shared black navigation bar and footer live in `templates/base.html`. The movie catalog is in `templates/index.html`, and the redesigned login/register pages are in `templates/auth/`. Every other booking and staff view gets the same theme while retaining the original Jinja form names, CSRF tokens, data attributes and routes.

**To revert to the earlier design:** Remove the `classic-cinema.css` `<link>` from `templates/base.html`; to restore the old homepage and authentication layouts as well, copy back those templates and `base.html` from the original Screenlane ZIP.

| Variable | Controls |
| --- | --- |
| `--bg`, `--bg-card`, `--bg-elevated` | Background shades |
| `--text`, `--text-secondary` | Text colours |
| `--brand`, `--brand-hover`, `--brand-text` | Accent colour and buttons |
| `--font-body`, `--font-display` | Fonts |
| `--radius-sm`, `--radius-lg` | Rounded corners |
| `--container` | Maximum content width |

**Shared navigation and footer:** `templates/base.html`.

**Homepage layout:** `templates/index.html`.

**Movie detail and booking:** `templates/movie_detail.html` and `templates/showtime_detail.html`.

**All booking-price calculations:** `services/booking.py`; never rely on JS for security.

**New fields / database model:** Change `models.py`. **Important:** `db.create_all()` does **not** migrate existing tables. For production use Alembic/Flask-Migrate. During early local development only, you can delete `instance/cinema.db` (loses all data), then rerun the seed script.

**Sample images:** Generated in `static/img/posters/` using `seed.py`. Staff can upload JPG/PNG/WebP posters that are converted to WebP.

## Security notes

- Passwords use Werkzeug's salted one-way password hashes. They cannot be decrypted, even by staff.
- Customer and staff roles are checked at the beginning of protected routes.
- Only the booking owner can view their reservation.
- SQLAlchemy uses bound parameters to prevent SQL injection.
- Jinja templates automatically HTML-escape user content; no unsafe HTML insertion is used.
- Flask-WTF requires CSRF tokens for POST forms (including logout and staff forms).
- Content Security Policy and secure response headers restrict external scripts, framing and unsafe object embeds.
- Poster uploads are limited by file extension, size and dimensions and re-encoded as raster images.
- Signed session cookies are HttpOnly and SameSite=Lax. Set `SESSION_COOKIE_SECURE=1` when serving over HTTPS.
- A reservation uses an atomic conditional UPDATE of remaining seats to reduce oversell risk during concurrent bookings.
- No payment processing or storage of card numbers is implemented, per the coursework specification.

Additional real-world production controls such as rate limiting, email verification, password recovery, audit logging, backups, external monitoring, and TLS configuration should be added before public launch.

## Run tests

Install pytest (not required to launch the site):

```bash
python -m pip install pytest
python -m pytest -q
```

The test suite covers public browsing, registration/password hashes, login, role restrictions, booking totals, packages, available-seat limits, private receipts, staff editors, price updates, CSRF rejection and XSS escaping.

## Design decisions

- **Seat selection:** Only quantity, not individual numbered seats. This is explicitly allowed by the brief.
- **Payment:** At the cinema, not online, as permitted by the brief.
- **Multiple screens:** Fixed capacity per screen and one screening at a time per room, with a 15-minute turnover.
- **Historical prices:** `Booking.ticket_unit_price`, `Booking.total_price` and booking-food snapshots avoid changing prior receipts when menu prices are edited.
- **Product removal:** Soft-delete (`is_active=False`) instead of database deletion, to preserve historic booking references. Removing a snack/drink also disables active packages containing it.
- **Showtime/movie editing:** Adding is supported; editing/removal is optional in the brief and intentionally not exposed, to avoid accidentally modifying existing bookings.

## Known limitations / possible extensions

- Admin account provisioning is CLI-only; customers cannot promote themselves.
- No seat map, checkout, refunds, cancellation, SMS, email or ratings because they aren't required.
- `datetime.now()` assumes the server is running in the cinema's local timezone. If hosting remotely across timezones, convert showtime times explicitly to a configured IANA timezone.
- SQLite works well for this class project. For busy production deployments, use PostgreSQL and carefully review concurrency behavior.


## Editing an existing movie (new staff feature)

1. Sign in as a **management staff** user.
2. Open **Staff dashboard → Movies** and select **Edit** next to a movie, or visit its public details page and click **Edit this movie**.
3. Change the **title, genre, age rating**, or optionally choose a new **poster**. The preview updates immediately in your browser; no changes are saved at this stage.
4. Click **Save changes** to submit one protected POST request. Flask validates the fields and upload, then updates that **same movie** in the database.
5. **Reset draft** restores the form values to how they appeared when you opened the page. **Cancel** leaves the movie unchanged.

The new editor **does not change** the film synopsis, runtime, screens, showtimes, reservations, customers or ticket prices. Existing poster images are kept when no replacement is selected. This feature requires **no database migration**.

Client-side preview code: `static/js/movie_editor.js`  
Page: `templates/admin/movie_edit.html`  
Route: `routes/admin.py` → `movie_edit()`  
Styles: the `EDIT MOVIE` section at the end of `static/css/classic-cinema.css`

Run `python -m pytest -q` to run the included tests, including the movie editor tests.

