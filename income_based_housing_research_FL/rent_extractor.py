from __future__ import annotations

import re

from config import INTERMEDIATE_DIR
from models import HousingProperty
from utils.io_utils import append_log, ensure_directories, read_json, write_json
from utils.normalization_utils import choose_preferred_value
from utils.text_utils import extract_ami, extract_money

RANGE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?\s*(?:-|to)\s*\$\s?\d[\d,]*(?:\.\d{2})?", re.I)
HOUSEHOLD_RE = re.compile(r"\b(?:1|2|3|4|5|6|7|8)[-\s]*person\b.*?\$\s?\d[\d,]*", re.I)


def load_properties() -> list[HousingProperty]:
    payload = read_json(INTERMEDIATE_DIR / "properties_enriched.json", default=[])
    return [HousingProperty(**item) for item in payload]


def save_properties(properties: list[HousingProperty]) -> None:
    write_json(INTERMEDIATE_DIR / "properties_rents.json", [item.model_dump() for item in properties])


def combined_text(property_record: HousingProperty) -> str:
    parts = [property_record.notes, property_record.program_type]
    parts.extend(property_record.evidence_snippets)
    return " || ".join(part for part in parts if part)


def infer_rent_type(property_record: HousingProperty, text: str) -> str:
    lower = text.lower()
    program_lower = property_record.program_type.lower()
    if any(term in lower for term in ["income based", "income-based", "based on adjusted income"]):
        return "income-based"
    if "lihtc" in lower or "low-income housing tax credit" in lower or "%ami" in lower.replace(" ", ""):
        return "max LIHTC rent"
    if "voucher" in lower and "market" in lower:
        return "market + vouchers accepted"
    if "affordable rent" in lower or "restricted rent" in lower:
        return "fixed affordable rent"
    if any(term in program_lower for term in ["public housing", "section 8", "usda", "hud pbra"]):
        return "income-based"
    return property_record.rent_type


def main() -> None:
    ensure_directories()
    properties = load_properties()
    for property_record in properties:
        text = combined_text(property_record)
        money_values = extract_money(text)
        ranges = RANGE_RE.findall(text)
        ami_values = extract_ami(text)
        household_limits = HOUSEHOLD_RE.findall(text)
        lower = text.lower()

        property_record.rent_type = infer_rent_type(property_record, text)
        if ranges:
            property_record.exact_published_rent_by_bedroom = choose_preferred_value(
                property_record.exact_published_rent_by_bedroom,
                "; ".join(dict.fromkeys(ranges)),
            )
        elif money_values:
            property_record.exact_published_rent_by_bedroom = choose_preferred_value(
                property_record.exact_published_rent_by_bedroom,
                "; ".join(dict.fromkeys(money_values[:6])),
            )
        elif "call for rent" in lower or "contact for rent" in lower:
            property_record.exact_published_rent_by_bedroom = "NOT FOUND"
            property_record.phone_verification_needed = True

        if household_limits:
            property_record.income_limits_by_household_size = "; ".join(dict.fromkeys(household_limits))
        if ami_values:
            property_record.AMI_brackets_supported = "; ".join(dict.fromkeys(ami_values))
        if "minimum income" in lower:
            property_record.minimum_income_requirement = "Published minimum income language found in source; property verification recommended."
        if "maximum income" in lower or "income may not exceed" in lower:
            property_record.maximum_income_requirement = "Published maximum income language found in source; property verification recommended."

        if property_record.rent_type == "income-based" and property_record.exact_published_rent_by_bedroom == "NOT FOUND":
            property_record.exact_published_rent_by_income_bracket = (
                "Likely based on adjusted income; exact tenant rent requires application/property verification."
            )
        if property_record.rent_type == "max LIHTC rent" and property_record.exact_published_rent_by_bedroom != "NOT FOUND":
            property_record.exact_published_rent_by_income_bracket = (
                "Published amounts appear to be maximum restricted LIHTC rents; confirm actual tenant rent with property."
            )

    save_properties(properties)
    append_log("rent_extractor.py: rent extraction complete")


if __name__ == "__main__":
    main()
