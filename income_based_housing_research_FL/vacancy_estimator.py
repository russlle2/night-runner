from __future__ import annotations

from geopy.distance import geodesic

from config import INTERMEDIATE_DIR, TARGET_LOCATIONS
from models import HousingProperty
from utils.io_utils import append_log, ensure_directories, read_json, write_json
from utils.scoring_utils import infer_vacancy_from_text, score_confidence

CITY_COORDS = {
    "The Villages": (28.9270, -82.0031),
    "Lady Lake": (28.9178, -81.9234),
    "Fruitland Park": (28.8611, -81.9065),
    "Wildwood": (28.8655, -82.0401),
    "Leesburg": (28.8108, -81.8779),
    "Lake Panasoffkee": (28.7897, -82.1401),
    "Sumterville": (28.7472, -82.1034),
    "Bushnell": (28.6647, -82.1129),
    "Webster": (28.6122, -82.0556),
}


def load_properties() -> list[HousingProperty]:
    payload = read_json(INTERMEDIATE_DIR / "properties_requirements.json", default=[])
    return [HousingProperty(**item) for item in payload]


def save_properties(properties: list[HousingProperty]) -> None:
    write_json(INTERMEDIATE_DIR / "properties_final.json", [item.model_dump() for item in properties])


def distance_to_target(city: str) -> float | None:
    city_coord = CITY_COORDS.get(city)
    if not city_coord:
        return None
    distances = [geodesic(city_coord, (item["latitude"], item["longitude"])).miles for item in TARGET_LOCATIONS]
    return round(min(distances), 1)


def main() -> None:
    ensure_directories()
    properties = load_properties()
    for property_record in properties:
        text = " || ".join([property_record.notes, *property_record.evidence_snippets, property_record.program_type])
        score, reason, waitlist_status, vacancy_status = infer_vacancy_from_text(text)
        property_record.vacancy_likelihood_score = score
        property_record.vacancy_likelihood_reason = reason
        property_record.waitlist_status = waitlist_status
        property_record.vacancy_status = vacancy_status
        property_record.phone_verification_needed = property_record.phone_verification_needed or score < 4
        property_record.distance_miles_to_target_area = distance_to_target(property_record.city)

        has_official_address = any(
            "address" in evidence.confirmed_fields and evidence.source_quality in {"government", "housing_authority", "HUD/USDA/FHFC", "official_property_site"}
            for evidence in property_record.evidence
        )
        has_official_phone = any(
            "phone" in evidence.confirmed_fields and evidence.source_quality in {"government", "housing_authority", "HUD/USDA/FHFC", "official_property_site"}
            for evidence in property_record.evidence
        )
        has_official_program = any(
            "program_type" in evidence.confirmed_fields
            and evidence.source_quality in {"government", "housing_authority", "HUD/USDA/FHFC", "official_property_site"}
            for evidence in property_record.evidence
        )
        property_record.confidence_score = score_confidence(
            source_quality=property_record.source_quality,
            source_count=len(property_record.source_urls),
            has_official_address=has_official_address,
            has_official_phone=has_official_phone,
            has_official_program=has_official_program,
            last_updated_date_from_source=property_record.last_updated_date_from_source,
            phone_verification_needed=property_record.phone_verification_needed,
            exact_rent_known="NOT FOUND" not in property_record.exact_published_rent_by_bedroom,
        )

    save_properties(properties)
    append_log("vacancy_estimator.py: vacancy estimation complete")


if __name__ == "__main__":
    main()
