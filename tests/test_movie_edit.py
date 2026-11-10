"""Movie editing: server persistence, security and existing-showtime preservation."""

from io import BytesIO

from PIL import Image
from sqlalchemy import select

from models import Movie, Showtime, db


def sample_poster():
    image = Image.new("RGB", (240, 360), "darkred")
    file_data = BytesIO()
    image.save(file_data, format="PNG")
    file_data.seek(0)
    return (file_data, "new-poster.png")


def test_staff_sees_movie_edit_links(staff_login):
    result = staff_login.get("/admin/movies")
    assert result.status_code == 200
    assert b"/admin/movies/1/edit" in result.data
    result = staff_login.get("/movies/1")
    assert b"Edit this movie" in result.data


def test_customers_do_not_see_staff_movie_edit_button(customer_login):
    response = customer_login.get("/movies/1")
    assert response.status_code == 200
    assert b"Edit this movie" not in response.data


def test_movie_edit_page_has_live_preview_and_csrf(staff_login):
    page = staff_login.get("/admin/movies/1/edit")
    assert page.status_code == 200
    for content in (b'id="movie-edit-form"', b'name="csrf_token"',
                    b'name="title"', b'name="genre"', b'name="age_rating"',
                    b'name="poster"', b'data-preview-title', b'data-preview-poster',
                    b"js/movie_editor.js", b"Save changes"):
        assert content in page.data


def test_unauthorized_users_cannot_edit_movies(client, customer_login, app):
    customer = customer_login
    assert customer.get("/admin/movies/1/edit").status_code == 403
    assert customer.post("/admin/movies/1/edit", data={
        "title": "Overwrite", "genre": "Horror", "age_rating": "18"}).status_code == 403
    with app.app_context():
        assert db.session.get(Movie, 1).title == "Test Movie"
    customer.post("/account/logout")
    assert client.get("/admin/movies/1/edit").status_code == 302
    assert client.post("/admin/movies/1/edit", data={
        "title": "Overwrite", "genre": "Horror", "age_rating": "18"}).status_code == 302


def test_edit_movie_saves_metadata_but_keeps_other_fields_and_showtimes(staff_login, app):
    with app.app_context():
        original = db.session.get(Movie, 1)
        original_poster = original.poster
        original_created_at = original.created_at
        original_synopsis = original.synopsis
        original_duration = original.duration
        original_showtime_id = db.session.scalar(select(Showtime.id).where(Showtime.movie_id == original.id))
    response = staff_login.post("/admin/movies/1/edit", data={
        "title": "  Updated Movie  ", "genre": "Mystery", "age_rating": "PG-13",
        "synopsis": "Forged replacement", "duration": "999", "poster": "other.png"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Movie updated successfully" in response.data
    with app.app_context():
        movie = db.session.get(Movie, 1)
        assert (movie.title, movie.genre, movie.age_rating) == ("Updated Movie", "Mystery", "PG-13")
        assert movie.poster == original_poster
        assert movie.created_at == original_created_at
        assert movie.synopsis == original_synopsis
        assert movie.duration == original_duration
        assert db.session.get(Showtime, original_showtime_id).movie_id == movie.id
        assert db.session.scalar(select(Movie.id).where(Movie.id == 2)) is None
    assert b"Updated Movie" in staff_login.get("/movies/1").data
    assert b"Updated Movie" in staff_login.get("/").data


def test_edit_movie_uploads_valid_poster(staff_login, app):
    response = staff_login.post("/admin/movies/1/edit", data={
        "title": "Test Movie", "genre": "Drama", "age_rating": "PG",
        "poster": sample_poster()
    }, content_type="multipart/form-data", follow_redirects=True)
    assert b"updated successfully" in response.data
    with app.app_context():
        movie = db.session.get(Movie, 1)
        assert movie.poster.startswith("uploads/posters/")
        poster_path = __import__("pathlib").Path(app.static_folder) / movie.poster
        assert poster_path.exists()
        with Image.open(poster_path) as converted:
            assert converted.format == "WEBP"
    poster_path.unlink()


def test_invalid_poster_rejected_without_partial_movie_update(staff_login, app):
    response = staff_login.post("/admin/movies/1/edit", data={
        "title": "Unwanted title", "genre": "New genre", "age_rating": "18",
        "poster": (BytesIO(b"not a valid PNG"), "fake.png")
    }, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert b"not a valid image" in response.data
    with app.app_context():
        assert db.session.get(Movie, 1).title == "Test Movie"
        assert db.session.get(Movie, 1).genre == "Drama"


def test_invalid_movie_metadata_is_rejected(staff_login, app):
    for values in (
        {"title": " ", "genre": "Drama", "age_rating": "PG"},
        {"title": "Title", "genre": "x" * 121, "age_rating": "PG"},
        {"title": "Title", "genre": "Drama", "age_rating": "x" * 17},
    ):
        result = staff_login.post("/admin/movies/1/edit", data=values)
        assert result.status_code == 200
        assert b"alert-error" in result.data
        with app.app_context():
            assert db.session.get(Movie, 1).title == "Test Movie"


def test_csrf_token_required_when_enabled(staff_login, app):
    app.config["WTF_CSRF_ENABLED"] = True
    response = staff_login.post("/admin/movies/1/edit", data={
        "title": "CSRF attack", "genre": "Drama", "age_rating": "PG"
    })
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Movie, 1).title == "Test Movie"


def test_edit_escapes_untrusted_text(staff_login):
    injection = "<img src=x onerror=alert(1)>"
    response = staff_login.post("/admin/movies/1/edit", data={
        "title": injection, "genre": "Drama", "age_rating": "PG"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"&lt;img src=x onerror=alert(1)&gt;" in response.data
    assert b'<img src=x onerror=alert(1)>' not in response.data
