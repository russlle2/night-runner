from __future__ import annotations

import re

from config import INTERMEDIATE_DIR
from models import HousingProperty
from utils.io_utils import append_log, ensure_directories, read_json, write_json
from utils.normalization_utils import choose_preferred_value
from utils.text_utils import extract_ami, extract_money

RANGE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?\s*(?:-|to)\s*\$\s?\d[\d,]*(?:\.\d{2})?", re.I)
HOUSEHOLD_RE = re.compile(r"\b(?:1|2|3|4|5|6|7|8)[-\s]*person\b.*?\$\s?\d[\d,]*", re.I)
RENT_KEYWORDS = (" rent", "rents", "price per month", "monthly", "floorplan", "1 br", "2 br", "3 br", "4 br", "bedroom")
RENT_EXCLUDE_KEYWORDS = ("deposit", "application fee", "income limit", "ami", "median income", "household", "security deposit")
NON_RENT_MONEY_CONTEXTS = (
    "median apartment rental rate",
    "median non-metropolitan income",
    "median household income",
    "population in zip code",
    "income limits",
    "state of florida median",
    "household income",
    "income requirements",
)


def load_properties() -> list[HousingProperty]:
    payload = read_json(INTERMEDIATE_DIR / "properties_enriched.json", default=[])
    return [HousingProperty(**item) for item in payload]


def save_properties(properties: list[HousingProperty]) -> None:
    write_json(INTERMEDIATE_DIR / "properties_rents.json", [item.model_dump() for item in properties])


def combined_text(property_record: HousingProperty) -> str:
    parts = [property_record.notes, property_record.program_type]
    parts.extend(property_record.evidence_snippets)
    return " || ".join(part for part in parts if part)


def money_value(raw: str) -> float:
    try:
        return float(raw.replace("$", "").replace(",", "").strip())
    except ValueError:
        return 0.0


def evidence_snippets(property_record: HousingProperty) -> list[str]:
    snippets = [property_record.notes]
    snippets.extend(property_record.evidence_snippets)
    return [snippet for snippet in snippets if snippet]


def rent_related_snippets(property_record: HousingProperty) -> list[str]:
    results = []
    for snippet in evidence_snippets(property_record):
        lower = snippet.lower()
        explicit_rent_context = any(
            phrase in lower for phrase in ["price per month", "monthly rent", "call for rent", "call for rents", "contact for rent", "rent:"]
        )
        if any(keyword in lower for keyword in RENT_KEYWORDS) and not (
            any(bad in lower for bad in RENT_EXCLUDE_KEYWORDS) and not explicit_rent_context
        ):
            results.append(snippet)
    return list(dict.fromkeys(results))


def extract_exact_rent_values(property_record: HousingProperty) -> tuple[list[str], bool]:
    snippets = rent_related_snippets(property_record)
    call_for_rent = False
    values: list[str] = []
    for snippet in snippets:
        lower = snippet.lower()
        if "call for rent" in lower or "call for rents" in lower or "contact for rent" in lower:
            call_for_rent = True
        if any(phrase in lower for phrase in NON_RENT_MONEY_CONTEXTS):
            continue
        explicit_context = any(
            phrase in lower for phrase in ["price per month", "monthly rent", "call for rent", "call for rents", "floorplan", "rent:"]
        ) or ("bedroom" in lower and "$" in snippet) or ("1 br" in lower and "$" in snippet) or ("2 br" in lower and "$" in snippet) or ("3 br" in lower and "$" in snippet) or ("4 br" in lower and "$" in snippet)
        if not explicit_context:
            continue
        for rent_range in RANGE_RE.findall(snippet):
            values.append(rent_range.replace(" to ", " - "))
        for raw in extract_money(snippet):
            amount = money_value(raw)
            if 0 < amount < 5000:
                values.append(raw)
    unique_values = list(dict.fromkeys(values))
    range_values = [value for value in unique_values if " - " in value]
    if range_values:
        return range_values, call_for_rent
    return unique_values, call_for_rent


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
        ami_values = extract_ami(text)
        household_limits = HOUSEHOLD_RE.findall(text)
        lower = text.lower()
        rent_values, call_for_rent = extract_exact_rent_values(property_record)

        property_record.rent_type = infer_rent_type(property_record, text)
        if rent_values:
            property_record.exact_published_rent_by_bedroom = choose_preferred_value(
                property_record.exact_published_rent_by_bedroom,
                "; ".join(rent_values[:6]),
            )
        elif call_for_rent:
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
