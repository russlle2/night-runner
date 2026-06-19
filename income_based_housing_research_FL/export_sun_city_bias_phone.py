from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path
from statistics import mean
from urllib.parse import quote_plus

from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from utils.scoring_utils import affordability_rank

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_CSV = PROJECT_DIR / "housing_results.csv"
INTERMEDIATE_JSON = PROJECT_DIR / "intermediate" / "properties_final.json"
OUTPUT_CSV = PROJECT_DIR / "top_10_sun_city_bias_phone.csv"
OUTPUT_HTML = PROJECT_DIR / "top_10_sun_city_bias_phone.html"
ARTIFACT_DIR = Path("/opt/cursor/artifacts")
ARTIFACT_CSV = ARTIFACT_DIR / OUTPUT_CSV.name
ARTIFACT_HTML = ARTIFACT_DIR / OUTPUT_HTML.name

REFERENCE_POINTS = [
    {
        "label": "1524 Husson Ave 32177",
        "query": "1524 Husson Ave, Palatka, FL 32177",
        "slug": "husson_ave",
    },
    {
        "label": "706 Desert Hills, Sun City Center FL",
        "query": "706 Desert Hills Dr, Sun City Center, FL",
        "slug": "desert_hills",
    },
]

BEDROOM_PATTERNS = {
    "2br": re.compile(
        r"(?:Two|2)\s+Bedroom(?:\s+\w+){0,8}?(?:Price Per Month|Rent:?|Per Month)?\s*\$([0-9,]+(?:\.\d{2})?)"
        r"(?:\s*-\s*\$([0-9,]+(?:\.\d{2})?))?",
        re.I,
    ),
    "3br": re.compile(
        r"(?:Three|3)\s+Bedroom(?:\s+\w+){0,8}?(?:Price Per Month|Rent:?|Per Month)?\s*\$([0-9,]+(?:\.\d{2})?)"
        r"(?:\s*-\s*\$([0-9,]+(?:\.\d{2})?))?",
        re.I,
    ),
}


def load_rows() -> list[dict[str, str]]:
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_evidence_index() -> dict[tuple[str, str], dict]:
    items = json.loads(INTERMEDIATE_JSON.read_text(encoding="utf-8"))
    return {(item["property_name"], item["city"]): item for item in items}


def clean_address(address: str, city: str, state: str = "FL") -> str:
    if not address or "NOT FOUND" in address:
        return ""
    return ", ".join(part for part in [address, city, state] if part)


def city_fallback_query(city: str, state: str = "FL") -> str:
    return f"{city}, {state}" if city else ""


def google_maps_search(query: str) -> str:
    if not query:
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def google_directions_link(origin: str, destination: str) -> str:
    if not origin or not destination:
        return ""
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}&travelmode=driving"
    )


def geocode_queries(queries: list[str]) -> dict[str, tuple[float, float] | None]:
    geolocator = Nominatim(user_agent="housing-sun-city-bias-export")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    results: dict[str, tuple[float, float] | None] = {}
    for query in queries:
        location = geocode(query, timeout=20)
        results[query] = (location.latitude, location.longitude) if location else None
    return results


def numeric_distance(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 999999.0


def parse_rent_value(raw: str) -> float:
    return float(raw.replace(",", ""))


def rent_string_and_mean(match: re.Match[str]) -> tuple[str, float]:
    low = parse_rent_value(match.group(1))
    high_group = match.group(2)
    if high_group:
        high = parse_rent_value(high_group)
        return f"${match.group(1)} - ${high_group}", mean([low, high])
    return f"${match.group(1)}", low


def extract_bedroom_rent(property_item: dict, bedroom_key: str) -> tuple[str, float | None]:
    for snippet in property_item.get("evidence_snippets", []):
        match = BEDROOM_PATTERNS[bedroom_key].search(snippet)
        if match:
            return rent_string_and_mean(match)
    return "NOT PUBLISHED", None


def move_in_cost_summary(row: dict[str, str]) -> str:
    application_fee = (row.get("application_fee") or "").strip()
    deposit = (row.get("deposit") or "").strip()
    parts = []
    if application_fee and "NOT FOUND" not in application_fee:
        parts.append(f"Application fee: {application_fee}")
    if deposit and "NOT FOUND" not in deposit:
        parts.append(f"Deposit: {deposit}")
    return "; ".join(parts) if parts else "NOT FOUND / NEEDS CALL"


def budget_summary(monthly_budget: float, rent_value: float | None) -> str:
    if rent_value is None:
        return "Rent not published"
    return "At or under budget" if rent_value <= monthly_budget else "Above budget"


def first_source_url(source_urls: str) -> str:
    parts = [part.strip() for part in (source_urls or "").split(";") if part.strip()]
    return parts[0] if parts else ""


def build_ranked_rows(rows: list[dict[str, str]], evidence_index: dict[tuple[str, str], dict]) -> list[dict[str, str]]:
    listing_queries = [clean_address(row.get("address", ""), row.get("city", "")) for row in rows]
    fallback_queries = [city_fallback_query(row.get("city", "")) for row in rows]
    reference_queries = [item["query"] for item in REFERENCE_POINTS]
    coords = geocode_queries([query for query in listing_queries + fallback_queries + reference_queries if query])

    enriched: list[dict[str, str]] = []
    for row, listing_query, fallback_query in zip(rows, listing_queries, fallback_queries):
        working = dict(row)
        exact_query = listing_query
        listing_coords = coords.get(exact_query) if exact_query else None
        basis = "exact address"
        if not listing_coords and fallback_query:
            listing_coords = coords.get(fallback_query)
            exact_query = fallback_query
            basis = "city fallback"

        working["primary_source_url"] = first_source_url(working.get("source_urls", ""))
        working["map_link"] = google_maps_search(exact_query)
        working["distance_basis"] = basis if listing_coords else "unresolved"

        if listing_coords:
            husson_coords = coords[REFERENCE_POINTS[0]["query"]]
            desert_coords = coords[REFERENCE_POINTS[1]["query"]]
            husson = geodesic(husson_coords, listing_coords).miles if husson_coords else None
            desert = geodesic(desert_coords, listing_coords).miles if desert_coords else None
            working["distance_husson_ave_miles"] = f"{husson:.1f}" if husson is not None else ""
            working["distance_desert_hills_miles"] = f"{desert:.1f}" if desert is not None else ""
            if husson is not None and desert is not None:
                gap = desert - husson
                working["distance_gap_miles"] = f"{abs(gap):.1f}"
                working["sun_city_lean"] = "Sun City Center closer" if gap < 0 else "Palatka closer"
                working["_sun_city_gap_numeric"] = gap
            else:
                working["distance_gap_miles"] = ""
                working["sun_city_lean"] = "Unknown"
                working["_sun_city_gap_numeric"] = 999999.0
        else:
            working["distance_husson_ave_miles"] = ""
            working["distance_desert_hills_miles"] = ""
            working["distance_gap_miles"] = ""
            working["sun_city_lean"] = "Unknown"
            working["_sun_city_gap_numeric"] = 999999.0

        for reference in REFERENCE_POINTS:
            working[f"directions_from_{reference['slug']}"] = google_directions_link(reference["query"], exact_query)

        evidence_item = evidence_index.get((working["property_name"], working["city"]), {})
        two_br_text, two_br_avg = extract_bedroom_rent(evidence_item, "2br")
        three_br_text, three_br_avg = extract_bedroom_rent(evidence_item, "3br")
        working["published_2br_rent"] = two_br_text
        working["published_3br_rent"] = three_br_text
        working["_published_2br_avg"] = two_br_avg
        working["_published_3br_avg"] = three_br_avg

        working["income_21k_monthly_budget"] = "$525"
        working["income_41k_monthly_budget"] = "$1,025"
        working["income_21k_2br_fit"] = budget_summary(525.0, two_br_avg)
        working["income_41k_2br_fit"] = budget_summary(1025.0, two_br_avg)
        working["income_21k_3br_fit"] = budget_summary(525.0, three_br_avg)
        working["income_41k_3br_fit"] = budget_summary(1025.0, three_br_avg)
        working["move_in_cost_summary"] = move_in_cost_summary(working)
        enriched.append(working)

    def rank_key(item: dict[str, str]) -> tuple:
        gap = float(item["_sun_city_gap_numeric"])
        sun_city_priority = 0 if gap <= 0 else 1
        return (
            sun_city_priority,
            abs(gap),
            *affordability_rank(
                {
                    "rent_type": item.get("rent_type", "unknown"),
                    "vacancy_likelihood_score": int(item.get("vacancy_likelihood_score") or 0),
                    "distance_miles_to_target_area": float(item.get("distance_miles_to_target_area") or 0) if item.get("distance_miles_to_target_area") else None,
                    "confidence_score": int(item.get("confidence_score") or 0),
                    "exact_published_rent_by_bedroom": item.get("exact_published_rent_by_bedroom", "NOT FOUND"),
                }
            ),
        )

    ranked = sorted(enriched, key=rank_key)[:10]
    for idx, row in enumerate(ranked, start=1):
        row["rank"] = str(idx)
    return ranked


def top10_bedroom_averages(rows: list[dict[str, str]]) -> dict[str, str]:
    two_values = [row["_published_2br_avg"] for row in rows if row.get("_published_2br_avg") is not None]
    three_values = [row["_published_3br_avg"] for row in rows if row.get("_published_3br_avg") is not None]
    return {
        "avg_2br": f"${mean(two_values):.0f}" if two_values else "Not enough published 2BR rent data",
        "avg_3br": f"${mean(three_values):.0f}" if three_values else "Not enough published 3BR rent data",
    }


def csv_fieldnames() -> list[str]:
    return [
        "rank",
        "property_name",
        "city",
        "county",
        "address",
        "phone",
        "website_url",
        "primary_source_url",
        "map_link",
        "distance_husson_ave_miles",
        "distance_desert_hills_miles",
        "distance_gap_miles",
        "sun_city_lean",
        "distance_basis",
        "directions_from_husson_ave",
        "directions_from_desert_hills",
        "program_type",
        "rent_type",
        "published_2br_rent",
        "published_3br_rent",
        "income_21k_monthly_budget",
        "income_41k_monthly_budget",
        "income_21k_2br_fit",
        "income_41k_2br_fit",
        "income_21k_3br_fit",
        "income_41k_3br_fit",
        "move_in_cost_summary",
        "application_fee",
        "deposit",
        "exact_published_rent_by_bedroom",
        "exact_published_rent_by_income_bracket",
        "vacancy_likelihood_score",
        "vacancy_likelihood_reason",
        "confidence_score",
        "required_documents",
        "notes",
    ]


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = csv_fieldnames()
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def link(url: str, label: str) -> str:
    if not url:
        return ""
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def tel_link(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return ""
    return link(f"tel:{digits}", phone)


def render_card(row: dict[str, str]) -> str:
    return f"""
    <article class="card">
      <div class="rank">#{html.escape(row['rank'])}</div>
      <h2>{html.escape(row['property_name'])}</h2>
      <p><strong>Sun City lean:</strong> {html.escape(row['sun_city_lean'])}</p>
      <p><strong>Distance from Husson:</strong> {html.escape(row['distance_husson_ave_miles'] or 'unknown')} miles</p>
      <p><strong>Distance from Desert Hills:</strong> {html.escape(row['distance_desert_hills_miles'] or 'unknown')} miles</p>
      <p><strong>Halfway gap:</strong> {html.escape(row['distance_gap_miles'] or 'unknown')} miles</p>
      <p><strong>Move-in cost info:</strong> {html.escape(row['move_in_cost_summary'])}</p>
      <p><strong>Published 2BR rent:</strong> {html.escape(row['published_2br_rent'])}</p>
      <p><strong>Published 3BR rent:</strong> {html.escape(row['published_3br_rent'])}</p>
      <p><strong>$21k income budget:</strong> {html.escape(row['income_21k_monthly_budget'])}/mo — 2BR: {html.escape(row['income_21k_2br_fit'])}, 3BR: {html.escape(row['income_21k_3br_fit'])}</p>
      <p><strong>$41k income budget:</strong> {html.escape(row['income_41k_monthly_budget'])}/mo — 2BR: {html.escape(row['income_41k_2br_fit'])}, 3BR: {html.escape(row['income_41k_3br_fit'])}</p>
      <p><strong>Phone:</strong> {tel_link(row.get('phone', '')) or 'NEEDS CALL'}</p>
      <p><strong>Program:</strong> {html.escape(row['program_type'])}</p>
      <p><strong>Vacancy:</strong> score {html.escape(row['vacancy_likelihood_score'])} — {html.escape(row['vacancy_likelihood_reason'])}</p>
      <p class="links">
        {link(row.get('website_url', ''), 'Website')}
        {link(row.get('primary_source_url', ''), 'Source')}
        {link(row.get('map_link', ''), 'Map')}
        {link(row.get('directions_from_husson_ave', ''), 'Directions from Husson')}
        {link(row.get('directions_from_desert_hills', ''), 'Directions from Desert Hills')}
      </p>
    </article>
    """


def write_html(rows: list[dict[str, str]]) -> None:
    summaries = top10_bedroom_averages(rows)
    cards = "\n".join(render_card(row) for row in rows)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sun City Center-Leaning Top 10 Housing Listings</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f5f7fb; color: #15202b; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 16px; }}
    h1 {{ font-size: 1.55rem; margin-bottom: 0.25rem; }}
    .sub {{ color: #4b5563; margin-bottom: 1rem; }}
    .summary {{ background: #e8f0ff; border-radius: 12px; padding: 14px; margin-bottom: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; margin: 0 0 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
    .rank {{ display: inline-block; background: #2563eb; color: white; border-radius: 999px; padding: 4px 10px; font-weight: 700; margin-bottom: 8px; }}
    h2 {{ margin: 0 0 8px; font-size: 1.2rem; }}
    p {{ margin: 6px 0; line-height: 1.35; }}
    .links a {{ display: inline-block; margin-right: 12px; margin-top: 6px; color: #2563eb; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <main>
    <h1>Top 10 Listings Leaning Closer to Sun City Center</h1>
    <p class="sub">Ranked to prefer places where the Sun City Center side is shorter, while still staying as close to halfway as possible and preserving the original housing-priority factors.</p>
    <section class="summary">
      <p><strong>$21k income monthly housing budget at 30%:</strong> $525</p>
      <p><strong>$41k income monthly housing budget at 30%:</strong> $1,025</p>
      <p><strong>Average published 2BR rent among this shortlist:</strong> {html.escape(summaries['avg_2br'])}</p>
      <p><strong>Average published 3BR rent among this shortlist:</strong> {html.escape(summaries['avg_3br'])}</p>
      <p><strong>Move-in fee info rule:</strong> only published application fee / deposit information is shown; otherwise it is marked NEEDS CALL.</p>
    </section>
    {cards}
  </main>
</body>
</html>
"""
    OUTPUT_HTML.write_text(document, encoding="utf-8")


def copy_to_artifacts() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_CSV.write_text(OUTPUT_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    ARTIFACT_HTML.write_text(OUTPUT_HTML.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    rows = load_rows()
    evidence_index = load_evidence_index()
    ranked_rows = build_ranked_rows(rows, evidence_index)
    write_csv(ranked_rows)
    write_html(ranked_rows)
    copy_to_artifacts()
    print(f"Wrote {OUTPUT_CSV.name}, {OUTPUT_HTML.name}, and artifact copies.")


if __name__ == "__main__":
    main()
