from search_sources import canonicalize_url, is_location_relevant


def test_canonicalize_url_removes_www_and_trailing_slash():
    assert canonicalize_url("https://www.example.com/foo/") == "https://example.com/foo"


def test_location_filter_rejects_excluded_domain():
    assert not is_location_relevant(
        "https://www.zillow.com/leesburg-fl/apartments/",
        "Leesburg apartments",
        "Affordable apartments in Leesburg Florida",
        "Leesburg",
        "Lake County",
    )


def test_location_filter_keeps_target_county_source():
    assert is_location_relevant(
        "https://www.leesburgflorida.gov/my_city/departments/housing/index.php",
        "Leesburg Housing",
        "Affordable housing resources in Lake County Florida",
        "Leesburg",
        "Lake County",
    )
