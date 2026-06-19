from models import HousingProperty
from rent_extractor import infer_rent_type


def test_infer_rent_type_lihtc():
    record = HousingProperty(property_name="Rolling Acres")
    text = "This LIHTC community serves households at 60% AMI."
    assert infer_rent_type(record, text) == "max LIHTC rent"


def test_infer_rent_type_income_based():
    record = HousingProperty(property_name="Housing Plaza", program_type="Public Housing")
    text = "Rent is income based and adjusted by household income."
    assert infer_rent_type(record, text) == "income-based"
