from enrich_official_sources import preferred_address, preferred_phone, result_matches_property


def test_result_matches_property_avoids_irrelevant_pepper_results():
    assert not result_matches_property(
        "Pepper Tree Apts",
        "Black pepper - Wikipedia",
        "Black pepper is one of the most commonly traded spices in the world.",
        "https://en.wikipedia.org/wiki/Black_pepper",
    )


def test_preferred_phone_skips_toll_free_numbers():
    assert preferred_phone(["1-877-428-8844", "(352) 323-3303"]) == "(352) 323-3303"


def test_preferred_address_skips_long_garbage_addresses():
    addresses = [
        "5 low income housing resources nearby Spring Lake Cove Apartments Fruitland Park 1508 Spring Lake Cove Lane Fruitland Park",
        "303 Urick St",
    ]
    assert preferred_address(addresses) == "303 Urick St"
