from __future__ import annotations

from pathlib import Path

from config import INTERMEDIATE_DIR, NORMALIZED_PROPERTIES_CSV
from models import HousingProperty
from utils.evidence_utils import add_evidence
from utils.io_utils import append_log, ensure_directories, read_csv, read_json, write_csv, write_json
from utils.normalization_utils import choose_preferred_value, likely_same_property, merge_unique_strings
from utils.source_registry import get_known_property_leads

MINIMUM_NAME_TOKENS = {"apartments", "apartment", "commons", "terrace", "townhomes", "manor", "villas", "reserve", "gardens"}
GENERIC_NAME_PHRASES = {
    "for rent in",
    "apartments for rent",
    "low income apartments and affordable housing",
    "senior housing & apartments",
    "affordable housing directory",
    "county fl low income housing apartments",
}


def sanitize_property_name(name: str) -> str:
    value = name.strip()
    for separator in [" | ", " - "]:
        if separator in value:
            value = value.split(separator, 1)[0].strip()
    return value


def looks_like_property_name(name: str) -> bool:
    lower = sanitize_property_name(name).lower()
    if any(phrase in lower for phrase in GENERIC_NAME_PHRASES):
        return False
    if len(lower.split()) > 8:
        return False
    return any(token in lower for token in MINIMUM_NAME_TOKENS)


def normalize_city_hint(city: str) -> str:
    value = city.strip()
    replacements = {
        "Fruitland Park Dr.": "Fruitland Park",
        "Lady Lake Fl": "Lady Lake",
    }
    return replacements.get(value, value)


def base_property_from_lead(lead: dict) -> HousingProperty:
    property_record = HousingProperty(
        property_name=lead["property_name"],
        property_type=lead.get("property_type", "Unknown"),
        address=lead.get("address", "NOT FOUND / NEEDS CALL"),
        city=lead.get("city", "Unknown"),
        county=lead.get("county", "Unknown"),
        state=lead.get("state", "FL"),
        zip=lead.get("zip", ""),
        phone=lead.get("phone", ""),
        source_urls=lead.get("source_urls", []),
        source_quality=lead.get("source_quality", "unknown"),
        housing_authority_or_agency=lead.get("housing_authority_or_agency", ""),
        program_type=lead.get("program_type", "Unknown"),
        notes=lead.get("notes", ""),
        discovered_from=["curated_official_lead"],
    )
    for url in property_record.source_urls:
        add_evidence(
            property_record,
            source_url=url,
            source_quality=property_record.source_quality,
            confirmed_fields=["property_name", "city", "phone"],
            snippet=lead.get("notes", ""),
            notes="Curated official lead from planning-stage verified source.",
        )
    return property_record


def base_property_from_snippet(snippet: dict) -> HousingProperty | None:
    name = sanitize_property_name(snippet.get("candidate_property_name", "").strip())
    if not name or not looks_like_property_name(name):
        return None
    property_record = HousingProperty(
        property_name=name,
        address=snippet.get("address", "") or "NOT FOUND / NEEDS CALL",
        city=normalize_city_hint(snippet.get("city_hint", "")) or "Unknown",
        county=snippet.get("county_hint", "") or "Unknown",
        state="FL",
        phone=snippet.get("contact_phone", ""),
        email=snippet.get("email", ""),
        website_url=snippet.get("website_url", ""),
        source_quality=snippet.get("source_quality", "unknown"),
        last_updated_date_from_source=snippet.get("last_updated_date_from_source", ""),
        notes=snippet.get("snippet_text", ""),
        discovered_from=[snippet.get("snippet_type", "snippet")],
    )
    add_evidence(
        property_record,
        source_url=snippet["source_url"],
        source_quality=snippet.get("source_quality", "unknown"),
        confirmed_fields=["property_name"],
        snippet=snippet.get("snippet_text", ""),
        raw_html_path=snippet.get("raw_html_path", ""),
        screenshot_path=snippet.get("screenshot_path", ""),
        notes=f"Snippet type: {snippet.get('snippet_type', '')}",
    )
    return property_record


def merge_properties(target: HousingProperty, incoming: HousingProperty) -> HousingProperty:
    target.property_name = choose_preferred_value(target.property_name, incoming.property_name)
    target.address = choose_preferred_value(target.address, incoming.address)
    target.city = choose_preferred_value(target.city, incoming.city)
    target.county = choose_preferred_value(target.county, incoming.county)
    target.zip = choose_preferred_value(target.zip, incoming.zip)
    target.phone = choose_preferred_value(target.phone, incoming.phone)
    target.email = choose_preferred_value(target.email, incoming.email)
    target.website_url = choose_preferred_value(target.website_url, incoming.website_url)
    target.management_company = choose_preferred_value(target.management_company, incoming.management_company)
    target.management_company_phone = choose_preferred_value(target.management_company_phone, incoming.management_company_phone)
    target.housing_authority_or_agency = choose_preferred_value(
        target.housing_authority_or_agency, incoming.housing_authority_or_agency
    )
    target.program_type = choose_preferred_value(target.program_type, incoming.program_type)
    target.property_type = choose_preferred_value(target.property_type, incoming.property_type)
    target.notes = merge_unique_strings(target.notes, incoming.notes)
    target.last_updated_date_from_source = choose_preferred_value(
        target.last_updated_date_from_source, incoming.last_updated_date_from_source
    )
    for url in incoming.source_urls:
        target.add_source_url(url)
    for evidence in incoming.evidence:
        target.add_evidence(evidence)
    for method in incoming.discovered_from:
        if method not in target.discovered_from:
            target.discovered_from.append(method)
    return target


def main() -> None:
    ensure_directories()
    snippets = read_csv(Path("extracted_snippets.csv"))
    properties: list[HousingProperty] = [base_property_from_lead(lead) for lead in get_known_property_leads()]

    for snippet in snippets:
        property_record = base_property_from_snippet(snippet)
        if property_record is None:
            continue
        merged = False
        for existing in properties:
            if likely_same_property(existing.model_dump(), property_record.model_dump()):
                merge_properties(existing, property_record)
                merged = True
                break
        if not merged:
            properties.append(property_record)

    properties.sort(key=lambda item: (item.city, item.property_name))
    rows = [item.export_dict() for item in properties]
    write_csv(NORMALIZED_PROPERTIES_CSV, rows)
    write_json(INTERMEDIATE_DIR / "properties_normalized.json", [item.model_dump() for item in properties])
    append_log(f"normalize_properties.py: wrote {len(properties)} normalized properties")


if __name__ == "__main__":
    main()
