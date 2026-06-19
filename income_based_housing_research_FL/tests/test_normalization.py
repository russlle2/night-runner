from utils.normalization_utils import likely_same_property, normalize_address, normalize_phone


def test_normalize_phone():
    assert normalize_phone("(352) 748-0047") == "3527480047"


def test_normalize_address():
    assert normalize_address("1000 Lee Street") == "1000 lee st"


def test_likely_same_property_by_name_and_phone():
    left = {"property_name": "Pepper Tree Apartments", "phone": "(352) 555-1212", "city": "Leesburg"}
    right = {"property_name": "Pepper Tree Apts", "phone": "352-555-1212", "city": "Leesburg"}
    assert likely_same_property(left, right) is True
