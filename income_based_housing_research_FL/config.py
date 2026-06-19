from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_HTML_DIR = PROJECT_ROOT / "raw_html"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
INTERMEDIATE_DIR = PROJECT_ROOT / "intermediate"
UTILS_DIR = PROJECT_ROOT / "utils"
TESTS_DIR = PROJECT_ROOT / "tests"

DISCOVERED_URLS_CSV = PROJECT_ROOT / "discovered_urls.csv"
EXTRACTED_SNIPPETS_CSV = PROJECT_ROOT / "extracted_snippets.csv"
NORMALIZED_PROPERTIES_CSV = PROJECT_ROOT / "normalized_properties.csv"
FINAL_JSON = PROJECT_ROOT / "housing_results.json"
FINAL_CSV = PROJECT_ROOT / "housing_results.csv"
FINAL_XLSX = PROJECT_ROOT / "housing_results.xlsx"
SOURCE_LOG_MD = PROJECT_ROOT / "source_log.md"
CALL_SCRIPT_MD = PROJECT_ROOT / "call_script.md"
README_MD = PROJECT_ROOT / "README.md"
SEED_URLS_TXT = PROJECT_ROOT / "seed_urls.txt"
PIPELINE_LOG = PROJECT_ROOT / "pipeline.log"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "income-based-housing-research-bot/1.0"
)

REQUEST_TIMEOUT_SECONDS = 30
REQUEST_DELAY_SECONDS = 1.0
SEARCH_DELAY_SECONDS = 1.2
MAX_SEARCH_RESULTS_PER_QUERY = 5
MAX_PLAYWRIGHT_SCREENSHOTS = 8

TARGET_LOCATIONS = [
    {
        "city": "The Villages",
        "county": "Sumter County",
        "state": "FL",
        "zip": "",
        "latitude": 28.9270,
        "longitude": -82.0031,
    },
    {
        "city": "Lady Lake",
        "county": "Lake County",
        "state": "FL",
        "zip": "",
        "latitude": 28.9178,
        "longitude": -81.9234,
    },
    {
        "city": "Fruitland Park",
        "county": "Lake County",
        "state": "FL",
        "zip": "",
        "latitude": 28.8611,
        "longitude": -81.9065,
    },
    {
        "city": "Wildwood",
        "county": "Sumter County",
        "state": "FL",
        "zip": "",
        "latitude": 28.8655,
        "longitude": -82.0401,
    },
    {
        "city": "Leesburg",
        "county": "Lake County",
        "state": "FL",
        "zip": "",
        "latitude": 28.8108,
        "longitude": -81.8779,
    },
    {
        "city": "Lake Panasoffkee",
        "county": "Sumter County",
        "state": "FL",
        "zip": "",
        "latitude": 28.7897,
        "longitude": -82.1401,
    },
    {
        "city": "Sumterville",
        "county": "Sumter County",
        "state": "FL",
        "zip": "",
        "latitude": 28.7472,
        "longitude": -82.1034,
    },
]

TARGET_CITIES = [entry["city"] for entry in TARGET_LOCATIONS]
TARGET_COUNTIES = sorted({entry["county"] for entry in TARGET_LOCATIONS})

SEARCH_QUERIES = [
    "The Villages FL income based apartments",
    "The Villages FL low income housing",
    "The Villages FL subsidized apartments",
    "The Villages FL Section 8 apartments",
    "The Villages FL LIHTC apartments",
    "The Villages FL USDA rural rental assistance apartments",
    "Lady Lake FL income based apartments",
    "Lady Lake FL low income apartments",
    "Lady Lake FL affordable housing",
    "Lady Lake FL Section 8 apartments",
    "Lady Lake FL senior income based apartments",
    "Lady Lake FL LIHTC apartments",
    "Fruitland Park FL income based apartments",
    "Fruitland Park FL low income housing",
    "Fruitland Park FL subsidized apartments",
    "Fruitland Park FL affordable senior apartments",
    "Wildwood FL income based apartments",
    "Wildwood FL low income apartments",
    "Wildwood FL Section 8 apartments",
    "Wildwood FL affordable apartments",
    "Wildwood FL USDA rural development apartments",
    "Wildwood FL LIHTC apartments",
    "Leesburg FL income based apartments",
    "Leesburg FL low income apartments",
    "Leesburg FL Section 8 apartments",
    "Leesburg FL public housing",
    "Leesburg FL subsidized apartments",
    "Leesburg FL senior income based apartments",
    "Leesburg Housing Authority apartments",
    "Lake Panasoffkee FL income based apartments",
    "Lake Panasoffkee FL low income housing",
    "Lake Panasoffkee FL subsidized apartments",
    "Lake Panasoffkee FL USDA rental assistance",
    "Sumterville FL income based apartments",
    "Sumterville FL low income housing",
    "Sumterville FL subsidized apartments",
    "Sumterville FL USDA rental assistance",
    "Sumter County FL income based apartments",
    "Sumter County FL affordable housing",
    "Sumter County FL low income housing",
    "Sumter County FL Section 8 housing",
    "Sumter County FL USDA apartments",
    "Lake County FL income based apartments",
    "Lake County FL affordable housing",
    "Lake County FL Section 8 apartments",
    "Lake County FL public housing",
    "Lake County FL LIHTC apartments",
]

SOURCE_QUALITY_WEIGHTS = {
    "official_property_site": 1.00,
    "government": 0.96,
    "housing_authority": 0.93,
    "HUD/USDA/FHFC": 0.97,
    "apartment_listing": 0.72,
    "nonprofit_directory": 0.66,
    "unknown": 0.45,
}

CONFIDENCE_RULES = {
    "official_address_bonus": 12,
    "official_phone_bonus": 8,
    "official_program_bonus": 10,
    "multiple_sources_bonus": 8,
    "recent_update_bonus": 6,
    "stale_penalty": 15,
    "call_required_penalty": 8,
    "missing_rent_penalty": 4,
    "minimum_score": 10,
    "maximum_score": 100,
}

CITY_TO_COUNTY = {entry["city"]: entry["county"] for entry in TARGET_LOCATIONS}


def infer_city_from_query(query: str) -> str:
    lower = query.lower()
    for city in TARGET_CITIES:
        if city.lower() in lower:
            return city
    if "lake county" in lower:
        return "Leesburg"
    if "sumter county" in lower:
        return "Wildwood"
    return "Unknown"


def infer_county_from_query(query: str) -> str:
    city = infer_city_from_query(query)
    return CITY_TO_COUNTY.get(city, "Unknown")

