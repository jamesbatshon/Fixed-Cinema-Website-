"""Smoke tests for the cinema theme: these pages must retain functional hooks."""


def test_theme_is_loaded_and_movie_filters_remain(client):
    result = client.get("/")
    assert result.status_code == 200
    assert b"classic-cinema.css" in result.data
    assert b'data-movie-card' in result.data
    assert b'id="movie-search"' in result.data
    assert b'data-genre="all"' in result.data
    assert b"Test Movie" in result.data


def test_customer_booking_form_keeps_required_inputs(client):
    result = client.get("/showtimes/1")
    assert result.status_code == 200
    assert b'id="booking-form"' in result.data
    assert b'name="number_of_seats"' in result.data
    assert b'name="csrf_token"' in result.data
    assert b'data-product-price' in result.data
    assert b'id="order-total"' in result.data


def test_login_and_register_keep_post_fields(client):
    for path, fields in (
        ("/account/login", [b'name="email"', b'name="password"']),
        ("/account/register", [b'name="email"', b'name="password"', b'name="confirm_password"']),
    ):
        result = client.get(path)
        assert result.status_code == 200
        assert b'name="csrf_token"' in result.data
        assert all(field in result.data for field in fields)


def test_staff_pages_keep_navigation(staff_login):
    result = staff_login.get("/admin/")
    assert result.status_code == 200
    for text in (b"Movies", b"Showtimes", b"Food &amp; combos", b"Ticket pricing"):
        assert text in result.data
