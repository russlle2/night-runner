from models import HousingProperty
from rent_extractor import extract_exact_rent_values, infer_rent_type


def test_infer_rent_type_lihtc():
    record = HousingProperty(property_name="Rolling Acres")
    text = "This LIHTC community serves households at 60% AMI."
    assert infer_rent_type(record, text) == "max LIHTC rent"


def test_infer_rent_type_income_based():
    record = HousingProperty(property_name="Housing Plaza", program_type="Public Housing")
    text = "Rent is income based and adjusted by household income."
    assert infer_rent_type(record, text) == "income-based"


def test_extract_exact_rent_values_ignores_income_limits():
    record = HousingProperty(
        property_name="Example Villas",
        notes="Income limits by household size are $48,400 and $59,500.",
        evidence_snippets=[
            "Income limits by household size are $48,400 and $59,500.",
            "Call for rent.",
        ],
    )
    values, call_for_rent = extract_exact_rent_values(record)
    assert values == []
    assert call_for_rent is True


def test_extract_exact_rent_values_from_price_context():
    record = HousingProperty(
        property_name="Tall Pines Villas",
        evidence_snippets=[
            "Price Per Month $735.00 Deposit Security deposit is equal to one month’s basic rent.",
            "Three Bedroom Flat Price Per Month $759.00",
        ],
    )
    values, call_for_rent = extract_exact_rent_values(record)
    assert "$735.00" in values
    assert "$759.00" in values
    assert call_for_rent is False


def test_extract_exact_rent_values_ignores_zipcode_median_rent():
    record = HousingProperty(
        property_name="Turtle Oaks Apartments",
        evidence_snippets=[
            "HUD residents usually pay 30% of their gross income for rent. Median apartment rental rate in this zip code: $911 Population in zip code: 39,977.",
            "Rent Beds Baths SqFt Call for Rents",
        ],
    )
    values, call_for_rent = extract_exact_rent_values(record)
    assert values == []
    assert call_for_rent is True
