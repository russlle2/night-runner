from pydantic import ValidationError

from models import HousingProperty


def test_housing_property_defaults():
    record = HousingProperty(property_name="Example Apartments")
    assert record.address == "NOT FOUND / NEEDS CALL"
    assert record.waitlist_status == "call_required"
    assert record.vacancy_likelihood_score == 2


def test_housing_property_rejects_invalid_vacancy_score():
    try:
        HousingProperty(property_name="Example Apartments", vacancy_likelihood_score=5)
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for invalid vacancy score")
