from __future__ import annotations

import hashlib
import re
from pathlib import Path

from config import INTERMEDIATE_DIR
from models import HousingProperty
from search_sources import infer_source_quality_from_url
from utils.evidence_utils import add_evidence
from utils.http_utils import call_serpapi_search, call_tavily_search, can_fetch_url, fetch_url
from utils.io_utils import append_log, ensure_directories, read_json, slugify, write_json
from utils.normalization_utils import choose_preferred_value
from utils.text_utils import (
    extract_addresses,
    extract_dates,
    extract_emails,
    extract_phones,
    normalize_whitespace,
    snippets_with_keywords,
    soup_to_text,
)

BEDROOM_RE = re.compile(r"\b(?:studio|1|2|3|4|5)[-\s]*(?:bed|bedroom)s?\b", re.I)
UNIT_COUNT_RE = re.compile(r"\b(\d{1,4})\s+units?\b", re.I)
MANAGEMENT_RE = re.compile(r"(?:managed by|property manager|management company)\s*[:\-]?\s*([^.|;]+)", re.I)


def cache_name_for_url(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return Path("raw_html") / f"enrich-{slugify(url)}-{digest}.html"


def load_properties() -> list[HousingProperty]:
    payload = read_json(INTERMEDIATE_DIR / "properties_normalized.json", default=[])
    return [HousingProperty(**item) for item in payload]


def save_properties(properties: list[HousingProperty]) -> None:
    write_json(INTERMEDIATE_DIR / "properties_enriched.json", [item.model_dump() for item in properties])


def property_search_results(property_record: HousingProperty) -> list[dict]:
    query = f'"{property_record.property_name}" "{property_record.city}" Florida affordable housing'
    results: list[dict] = []
    for item in call_serpapi_search(query, max_results=4):
        if item.get("link"):
            results.append(
                {
                    "url": item["link"],
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source_quality": infer_source_quality_from_url(item["link"]),
                }
            )
    for item in call_tavily_search(query, max_results=4):
        if item.get("url"):
            results.append(
                {
                    "url": item["url"],
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "source_quality": infer_source_quality_from_url(item["url"]),
                }
            )
    deduped = []
    seen = set()
    for item in results:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        deduped.append(item)
    return deduped[:6]


def infer_program_type(text: str) -> str:
    lower = text.lower()
    if "usda" in lower or "rural development" in lower:
        return "USDA RD 515"
    if "public housing" in lower:
        return "Public Housing"
    if "project based section 8" in lower or "pbra" in lower:
        return "HUD PBRA"
    if "section 8" in lower:
        return "Section 8"
    if "lihtc" in lower or "low-income housing tax credit" in lower:
        return "LIHTC 30/50/60/80 AMI"
    if "voucher" in lower:
        return "HCV accepted"
    if "ship" in lower or "home program" in lower:
        return "HOME / SHIP affordable rental"
    return "Unknown"


def infer_property_type(text: str) -> str:
    lower = text.lower()
    if "62+" in lower or "elderly" in lower or "senior" in lower:
        return "Senior 62+"
    if "55+" in lower:
        return "Senior 55+"
    if "disabled" in lower:
        return "Disabled"
    if "family" in lower:
        return "Family"
    if "affordable" in lower:
        return "Mixed Affordable"
    return "Unknown"


def infer_population_served(text: str) -> str:
    lower = text.lower()
    if "elderly" in lower or "senior" in lower:
        return "senior"
    if "disabled" in lower:
        return "disabled"
    if "family" in lower:
        return "family"
    if "low-income" in lower or "income based" in lower:
        return "general low-income"
    return ""


def infer_application_method(text: str) -> str:
    lower = text.lower()
    if "apply online" in lower or "online application" in lower:
        return "online"
    if "paper application" in lower:
        return "paper application"
    if "in person" in lower or "visit office" in lower:
        return "in person"
    if "call" in lower or "contact" in lower:
        return "call office"
    return "call office"


def enrich_from_text(property_record: HousingProperty, text: str, url: str, source_quality: str, raw_path: str) -> None:
    phones = extract_phones(text)
    emails = extract_emails(text)
    addresses = extract_addresses(text)
    dates = extract_dates(text)
    bedrooms = list(dict.fromkeys(match.group(0) for match in BEDROOM_RE.finditer(text)))
    unit_count = UNIT_COUNT_RE.search(text)
    management = MANAGEMENT_RE.search(text)
    key_snippets = snippets_with_keywords(
        text,
        ["rent", "income", "waitlist", "available", "application", "deposit", "utilities", "pet", "credit", "background"],
        window=200,
    )[:6]

    property_record.phone = choose_preferred_value(property_record.phone, phones[0] if phones else "")
    property_record.email = choose_preferred_value(property_record.email, emails[0] if emails else "")
    property_record.address = choose_preferred_value(property_record.address, addresses[0] if addresses else "")
    property_record.last_updated_date_from_source = choose_preferred_value(
        property_record.last_updated_date_from_source, dates[0] if dates else ""
    )
    property_record.bedroom_sizes = choose_preferred_value(property_record.bedroom_sizes, ", ".join(bedrooms))
    property_record.unit_count = choose_preferred_value(
        property_record.unit_count, unit_count.group(1) if unit_count else ""
    )
    property_record.management_company = choose_preferred_value(
        property_record.management_company, normalize_whitespace(management.group(1)) if management else ""
    )
    property_record.program_type = choose_preferred_value(property_record.program_type, infer_program_type(text))
    property_record.property_type = choose_preferred_value(property_record.property_type, infer_property_type(text))
    property_record.population_served = choose_preferred_value(
        property_record.population_served, infer_population_served(text)
    )
    property_record.application_method = choose_preferred_value(
        property_record.application_method, infer_application_method(text)
    )
    if not property_record.website_url and source_quality == "official_property_site":
        property_record.website_url = url

    add_evidence(
        property_record,
        source_url=url,
        source_quality=source_quality,
        confirmed_fields=["address", "phone", "program_type", "property_type", "application_method"],
        snippet=" || ".join(key_snippets) if key_snippets else text[:250],
        raw_html_path=raw_path,
        notes="Targeted enrichment search result.",
    )


def main() -> None:
    ensure_directories()
    properties = load_properties()
    append_log(f"enrich_official_sources.py: enriching {len(properties)} properties")
    for property_record in properties:
        try:
            results = property_search_results(property_record)
        except Exception as exc:  # noqa: BLE001
            append_log(f"enrich_official_sources.py: search failed for {property_record.property_name}: {exc}")
            continue

        for result in results:
            url = result["url"]
            source_quality = result["source_quality"]
            if source_quality == "unknown":
                source_quality = property_record.source_quality
            if not can_fetch_url(url):
                continue
            try:
                response = fetch_url(url)
            except Exception as exc:  # noqa: BLE001
                append_log(f"enrich_official_sources.py: fetch failed {url}: {exc}")
                continue
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                continue
            text = soup_to_text(response.text)
            if property_record.property_name.lower().split()[0] not in text.lower():
                if property_record.city.lower() not in text.lower():
                    continue
            raw_path = Path.cwd() / cache_name_for_url(url)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(response.text, encoding="utf-8", errors="ignore")
            if ".gov" in url or any(token in url.lower() for token in ["apartments", "rentcafe", "zillow", "affordablehousing"]):
                property_record.website_url = choose_preferred_value(property_record.website_url, url)
            enrich_from_text(property_record, text, url, source_quality, str(raw_path))

    save_properties(properties)
    append_log("enrich_official_sources.py: enrichment complete")


if __name__ == "__main__":
    main()
