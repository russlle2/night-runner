from export_top10_phone_distances import clean_address, google_directions_link


def test_clean_address_formats_listing_query():
    assert clean_address("303 Urick St", "Fruitland Park") == "303 Urick St, Fruitland Park, FL"


def test_clean_address_drops_not_found():
    assert clean_address("NOT FOUND / NEEDS CALL", "Leesburg") == ""


def test_google_directions_link_contains_origin_and_destination():
    url = google_directions_link("A", "B")
    assert "google.com/maps/dir/" in url
    assert "origin=A" in url
    assert "destination=B" in url
