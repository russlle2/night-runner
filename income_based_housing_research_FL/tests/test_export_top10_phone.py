from export_top10_phone import build_map_link, first_source_url, normalize_phone_for_tel, top_ten_rows


def test_first_source_url_uses_first_semicolon_entry():
    assert first_source_url("https://one.example; https://two.example") == "https://one.example"


def test_normalize_phone_for_tel_formats_us_numbers():
    assert normalize_phone_for_tel("(352) 753-1006") == "+13527531006"


def test_build_map_link_contains_google_maps_query():
    assert "google.com/maps/search" in build_map_link("306 S Old Dixie Hwy", "Lady Lake")


def test_top_ten_rows_returns_ranked_subset():
    rows = [
        {
            "property_name": f"Property {i}",
            "city": "Test City",
            "state": "FL",
            "address": "123 Test St",
            "source_urls": "https://example.com",
            "rent_type": "income-based" if i == 0 else "unknown",
            "vacancy_likelihood_score": str(4 - min(i, 4)),
            "confidence_score": str(100 - i),
            "distance_miles_to_target_area": "0",
            "exact_published_rent_by_bedroom": "NOT FOUND",
        }
        for i in range(12)
    ]
    ranked = top_ten_rows(rows)
    assert len(ranked) == 10
    assert ranked[0]["property_name"] == "Property 0"
    assert ranked[0]["rank"] == "1"
