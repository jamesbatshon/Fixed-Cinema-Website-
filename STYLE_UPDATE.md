# Updating Screenlane with the black / grey / red theme

This is a **visual redesign** of the complete Screenlane cinema project. The source code for Flask routes, ORM models, pricing, authentication, authorization, seat availability and booking transactions is unchanged from the original Screenlane release.

## What changed

- `templates/base.html` — simple black navigation bar, account links and centred footer.
- `templates/index.html` — compact movie catalogue with red headings and charcoal movie cards. Movie search and genre filters are preserved.
- `templates/auth/login.html` and `templates/auth/register.html` — simple grey forms with red buttons; field names and CSRF remain intact.
- `static/css/classic-cinema.css` — **new, separate theme** applied consistently to movie details, showtimes, booking and food selection, receipts, staff pages and errors.
- `README.md` — customization guidance updated for this theme.

The original `static/css/styles.css` remains in place to provide shared layout and component foundations. The new stylesheet loads immediately after it in `base.html` and overrides its visual styling.

## Safest update if your original Screenlane already works

1. Stop the running Flask server (Ctrl+C in the terminal).
2. Back up your existing project, especially `instance/cinema.db`, `static/uploads/posters/` and any project-specific `.env` configuration.
3. Open the folder containing `app.py`, `main.py` and `models.py` (typically `Screenlane_Flask_Cinema_Project/screenlane/`).
4. Extract **Screenlane_Theme_Only_Patch.zip** into that folder, preserving subfolders and allowing the four templates to be replaced.
5. The `static/css/classic-cinema.css` file is new. No Python files, original CSS, data or uploads are overwritten by the patch.
6. Restart with `python app.py` and hard-refresh your browser with Ctrl+F5 so it loads the new CSS.

There is **no database migration needed**. Do not delete or replace your SQLite database just to update styling. Keep the same `SECRET_KEY` so existing Flask sessions remain valid.

If starting from scratch instead, extract the full **Screenlane_Classic_Cinema_Flask_Project.zip**, open its inner `screenlane` directory in VS Code, and follow `README.md` for installation and database setup.

## Easy customization

At the top of `static/css/classic-cinema.css`, adjust these CSS variables:

| CSS variable | Meaning | Default |
| --- | --- | --- |
| `--brand` | Red accent / headings / primary buttons | `#e50914` |
| `--brand-hover` | Red button hover | `#bc0710` |
| `--bg` | Main background | `#141414` |
| `--bg-card` | Card and form surface | `#2b2b2b` |
| `--bg-input` | Input background | `#1c1c1c` |
| `--container` | Page width | `1000px` |
| `--font-body` | Font stack | `Segoe UI`, Roboto, Helvetica, Arial |

The HTML templates continue using Jinja and the same Flask endpoints. Do not rename form `name=` attributes or `data-*` properties unless you also update the matching backend and JavaScript.

## Functional verification

Use this checklist on your computer after updating:

- Public: movie list, search, genre buttons, movie details, showtime links.
- Authentication: registration, login, logout.
- Customer: select seats, add ticket-and-food packages / individual snacks, check price, confirm booking, see upcoming/past bookings, print receipt.
- Staff: dashboard, add movies and upload posters, add screens and showtimes, manage food/drinks and packages, update weekday pricing.
- Security: staff-only pages remain protected and customers can only see their own bookings.

Run the project's original integration tests after installing the dependencies and pytest:

```powershell
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

**Review note:** In the isolated build environment, the Jinja templates parsed, the CSS and JavaScript passed syntax validation, the Python backend files were confirmed identical to the original, and a local browser preview exercised movie filters, mobile navigation and booking-price UI calculations. The full Flask/SQLite integration suite could not be run because installing Flask dependencies was unavailable in that environment. Run the tests above locally to verify the complete application against your local environment and database.
