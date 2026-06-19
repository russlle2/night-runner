from __future__ import annotations

import re

from config import INTERMEDIATE_DIR
from models import HousingProperty
from utils.io_utils import append_log, ensure_directories, read_json, write_json
from utils.normalization_utils import choose_preferred_value

DOCUMENT_PATTERNS = {
    "government-issued ID": r"\bgovernment[- ]issued id\b|\bphoto id\b|\bidentification\b",
    "Social Security card": r"\bsocial security\b|\bssn\b",
    "birth certificate": r"\bbirth certificate\b",
    "proof of income": r"\bproof of income\b|\bpay stubs?\b|\bbenefits letter\b",
    "bank statements": r"\bbank statements?\b",
    "SSI/SSDI award letter": r"\bssi\b|\bssdi\b|\baward letter\b",
    "tax returns": r"\btax returns?\b",
    "rental history": r"\brental history\b|\blandlord references?\b",
    "background check": r"\bbackground check\b|\bcriminal background\b",
    "credit check": r"\bcredit check\b|\bcredit report\b",
    "disability verification": r"\bdisability verification\b|\bdisability documentation\b",
    "student status": r"\bstudent status\b",
    "citizenship or immigration documents": r"\bcitizenship\b|\bimmigration\b|\beligible immigration status\b",
}


def load_properties() -> list[HousingProperty]:
    payload = read_json(INTERMEDIATE_DIR / "properties_rents.json", default=[])
    return [HousingProperty(**item) for item in payload]


def save_properties(properties: list[HousingProperty]) -> None:
    write_json(INTERMEDIATE_DIR / "properties_requirements.json", [item.model_dump() for item in properties])


def text_blob(property_record: HousingProperty) -> str:
    return " || ".join([property_record.notes, *property_record.evidence_snippets]).lower()


def main() -> None:
    ensure_directories()
    properties = load_properties()
    fee_re = re.compile(r"(?:application fee|admin fee)\D{0,20}(\$\s?\d[\d,]*(?:\.\d{2})?)", re.I)
    deposit_re = re.compile(r"(?:deposit|security deposit)\D{0,20}(\$\s?\d[\d,]*(?:\.\d{2})?)", re.I)

    for property_record in properties:
        blob = text_blob(property_record)
        documents = [label for label, pattern in DOCUMENT_PATTERNS.items() if re.search(pattern, blob, re.I)]
        if documents:
            property_record.required_documents = "; ".join(documents)
        if "pet" in blob:
            property_record.pet_policy = "Published pet-related language found; property verification recommended."
        if "utilities included" in blob:
            property_record.utilities_included = "Utilities included language found in source; confirm exact utilities."
        if "credit" in blob:
            property_record.credit_policy = "Published credit-related language found; property verification recommended."
        if "criminal background" in blob or "background check" in blob:
            property_record.criminal_background_policy = (
                "Published background-check language found; property verification recommended."
            )
        if "eviction" in blob:
            property_record.eviction_policy = "Published eviction-history language found; property verification recommended."
        if "online application" in blob or "apply online" in blob:
            property_record.application_method = choose_preferred_value(property_record.application_method, "online")
        elif "paper application" in blob:
            property_record.application_method = choose_preferred_value(
                property_record.application_method, "paper application"
            )
        elif "in person" in blob:
            property_record.application_method = choose_preferred_value(property_record.application_method, "in person")

        fee_match = fee_re.search(blob)
        deposit_match = deposit_re.search(blob)
        if fee_match:
            property_record.application_fee = fee_match.group(1).replace(" ", "")
        if deposit_match:
            property_record.deposit = deposit_match.group(1).replace(" ", "")

    save_properties(properties)
    append_log("apply_requirements_extractor.py: requirements extraction complete")


if __name__ == "__main__":
    main()
