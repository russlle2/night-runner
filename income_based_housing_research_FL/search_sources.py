from __future__ import annotations

import argparse
from urllib.parse import urlparse

from config import (
    DISCOVERED_URLS_CSV,
    INTERMEDIATE_DIR,
    MAX_SEARCH_RESULTS_PER_QUERY,
    SEARCH_QUERIES,
    SEED_URLS_TXT,
    infer_city_from_query,
    infer_county_from_query,
)
from models import DiscoveredUrlRecord
from utils.http_utils import call_serpapi_search, call_tavily_search
from utils.io_utils import append_log, ensure_directories, write_csv, write_json
from utils.source_registry import get_official_seed_urls

EXCLUDED_DOMAINS = {
    "apartments.com",
    "after55.com",
    "forrent.com",
    "zillow.com",
    "trulia.com",
    "yelp.com",
    "hotpads.com",
    "realtor.com",
    "apartmentfinder.com",
    "findhelp.org",
    "facebook.com",
    "instagram.com",
    "rent.com",
    "spotify.com",
}


def infer_source_quality_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if ".gov" in host:
        if "hud" in host or "usda" in host or "flhousing" in host:
            return "HUD/USDA/FHFC"
        if "housing" in host or "county" in host:
            return "government"
        return "government"
    if any(token in host for token in ["housingauthority", "pha", "emphasys"]):
        return "housing_authority"
    if any(token in host for token in ["apartments.com", "zillow", "realtor", "rentcafe", "affordablehousing"]):
        return "apartment_listing"
    if any(token in host for token in ["lowincomehousing", "after55", "seniorhousingnet", "habitat"]):
        return "nonprofit_directory"
    return "unknown"


def manual_seed_records() -> list[DiscoveredUrlRecord]:
    records = []
    if not SEED_URLS_TXT.exists():
        return records
    for line in SEED_URLS_TXT.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        records.append(
            DiscoveredUrlRecord(
                url=url,
                title="Manual seed URL",
                discovery_method="manual_seed",
                source_quality=infer_source_quality_from_url(url),
                source_category="manual_seed",
            )
        )
    return records


def official_seed_records() -> list[DiscoveredUrlRecord]:
    records = []
    for item in get_official_seed_urls():
        records.append(
            DiscoveredUrlRecord(
                url=item["url"],
                title=item.get("title", ""),
                discovery_method="official_seed",
                city=item.get("city", ""),
                county=item.get("county", ""),
                source_quality=item.get("source_quality", "unknown"),
                source_category=item.get("source_category", "official_seed"),
            )
        )
    return records


def filter_queries(city_filter: str | None) -> list[str]:
    if not city_filter:
        return SEARCH_QUERIES
    return [query for query in SEARCH_QUERIES if city_filter.lower() in query.lower()]


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/")
    if parsed.query:
        return f"{parsed.scheme}://{netloc}{path}?{parsed.query}"
    return f"{parsed.scheme}://{netloc}{path}"


def is_location_relevant(url: str, title: str, snippet: str, query_city: str, query_county: str) -> bool:
    host = urlparse(url).netloc.lower()
    if any(domain in host for domain in EXCLUDED_DOMAINS):
        return False
    combined = " ".join([url, title, snippet]).lower()
    if not combined:
        return False
    florida_signal = any(token in combined for token in [" florida", " fl ", "_fl", "-fl", "/fl/", ",fl", "florida"])
    if query_city != "Unknown" and query_city.lower() in combined and (florida_signal or query_county.lower() in combined):
        return True
    if query_county != "Unknown" and query_county.lower() in combined:
        return True
    if any(domain in host for domain in ["hud.gov", "usda.gov", "rdmfhrentals.sc.egov.usda.gov", "floridahousingsearch.org"]):
        return True
    return False


def search_query(query: str) -> list[DiscoveredUrlRecord]:
    city = infer_city_from_query(query)
    county = infer_county_from_query(query)
    records: list[DiscoveredUrlRecord] = []

    for result in call_serpapi_search(query, max_results=MAX_SEARCH_RESULTS_PER_QUERY):
        url = result.get("link")
        if not url:
            continue
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        if not is_location_relevant(url, title, snippet, city, county):
            continue
        records.append(
            DiscoveredUrlRecord(
                url=url,
                title=title,
                snippet=snippet,
                discovery_method="serpapi",
                query=query,
                city=city,
                county=county,
                source_quality=infer_source_quality_from_url(url),
                source_category="search_result",
            )
        )

    for result in call_tavily_search(query, max_results=MAX_SEARCH_RESULTS_PER_QUERY):
        url = result.get("url")
        if not url:
            continue
        title = result.get("title", "")
        snippet = result.get("content", "")
        if not is_location_relevant(url, title, snippet, city, county):
            continue
        records.append(
            DiscoveredUrlRecord(
                url=url,
                title=title,
                snippet=snippet,
                discovery_method="tavily",
                query=query,
                city=city,
                county=county,
                source_quality=infer_source_quality_from_url(url),
                source_category="search_result",
            )
        )
    return records


def dedupe_records(records: list[DiscoveredUrlRecord]) -> list[DiscoveredUrlRecord]:
    deduped: dict[str, DiscoveredUrlRecord] = {}
    for record in records:
        record.url = canonicalize_url(record.url)
        if record.url not in deduped:
            deduped[record.url] = record
            continue
        existing = deduped[record.url]
        if len(record.title) > len(existing.title):
            existing.title = record.title
        if len(record.snippet) > len(existing.snippet):
            existing.snippet = record.snippet
        if record.discovery_method != "manual_seed":
            existing.discovery_method = f"{existing.discovery_method};{record.discovery_method}"
        if not existing.city and record.city:
            existing.city = record.city
        if not existing.county and record.county:
            existing.county = record.county
    return list(deduped.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover source URLs for affordable housing research.")
    parser.add_argument("--city", dest="city_filter", help="Run queries for only one target city.")
    args = parser.parse_args()

    ensure_directories()
    append_log("search_sources.py: starting discovery")

    records: list[DiscoveredUrlRecord] = []
    records.extend(official_seed_records())
    records.extend(manual_seed_records())

    for query in filter_queries(args.city_filter):
        try:
            records.extend(search_query(query))
            append_log(f"search_sources.py: completed query '{query}'")
        except Exception as exc:  # noqa: BLE001
            append_log(f"search_sources.py: query failed '{query}': {exc}")

    deduped = dedupe_records(records)
    rows = [record.model_dump() for record in deduped]
    write_csv(DISCOVERED_URLS_CSV, rows)
    write_json(INTERMEDIATE_DIR / "discovered_urls.json", rows)
    append_log(f"search_sources.py: wrote {len(rows)} discovered URLs")


if __name__ == "__main__":
    main()
