# Staff movie editor — installation and usage

This update adds a staff-only editor to the **Screenlane Classic Cinema** version (dark grey with red buttons), without changing the schema or removing existing features.

## Install into your EXISTING project (recommended)

1. **Stop Flask** in VS Code with `Ctrl+C`.
2. **Back up your existing project** and `instance/cinema.db` before replacing files.
3. Download `Screenlane_Movie_Editor_Patch.zip` and select **Extract All**.
4. Open the extracted folder. It contains `routes`, `templates`, `static`, `tests`, and this document.
5. Copy those folders into your existing **inner** `screenlane` folder — the one that actually contains `app.py`, `models.py`, `main.py`, and the same four folders. Windows should **merge folders** and ask to **replace matching files**. Do not delete the existing folders or poster uploads.
6. Start Flask with `python app.py`; refresh the browser with `Ctrl+F5`.
7. Sign in as management staff, open **Staff dashboard → Movies** and click **Edit** next to a movie. A staff-only **Edit this movie** link is also available on movie detail pages.
8. Change the title, genre, rating or choose a new poster. Your draft will preview immediately **without saving**. Click **Save changes** when ready. **Reset draft** restores the form fields, while **Cancel** leaves the database untouched.

There is **no database migration** and **no need to re-run `python main.py seed`**. Your existing users, movie records, showtimes, seat reservations and uploaded posters will remain in place.

## Files introduced / changed

| File | Why |
|---|---|
| `routes/admin.py` | Adds a protected `GET/POST /admin/movies/<id>/edit` endpoint that validates and saves changes. |
| `templates/admin/movie_edit.html` | Editing form, CSRF token, Save/Reset/Cancel, and live preview. |
| `templates/admin/movies.html` | Adds an Edit action for each movie. |
| `templates/admin/_nav.html` | Keeps Movies highlighted while editing. |
| `templates/movie_detail.html` | Adds a staff-only Edit this movie link. |
| `static/js/movie_editor.js` | Updates draft title, genre, rating and poster in the browser. |
| `static/css/classic-cinema.css` | Styles the editing page to match the existing dark/red theme. |
| `tests/test_movie_edit.py` | Tests staff authorization, metadata persistence, image uploads, validation, CSRF and XSS escaping. |

## Verify functionality

In the Python virtual environment, optionally install pytest:

```powershell
python -m pip install pytest
python -m pytest -q
```

This runs existing tests as well as movie editor tests. Staff editing is server-side protected even if a customer guesses the URL. The server validates and re-encodes uploaded images. **No poster is uploaded until Save changes is clicked**; the preview is local to your browser.

## Customization

The editor is intentionally modular: modify `templates/admin/movie_edit.html` to change the layout, the `EDIT MOVIE` section near the end of `static/css/classic-cinema.css` to modify the visual design, or `static/js/movie_editor.js` to change live-preview behavior. Don't remove `csrf_token` or the `@staff_required` decorator.

### Alternative: complete project ZIP

If you are starting a new installation, download `Screenlane_Classic_With_Movie_Editor.zip`. **Do not** replace your populated database with a fresh one; prefer applying the patch to your working project instead.
