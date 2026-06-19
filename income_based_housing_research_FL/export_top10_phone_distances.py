from __future__ import annotations

import csv
import html
from pathlib import Path
from urllib.parse import quote_plus

from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

PROJECT_DIR = Path(__file__).resolve().parent
TOP10_INPUT = PROJECT_DIR / "top_10_listings_phone.csv"
OUTPUT_CSV = PROJECT_DIR / "top_10_listings_phone_with_distances.csv"
OUTPUT_HTML = PROJECT_DIR / "top_10_listings_phone_with_distances.html"
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


def load_rows() -> list[dict[str, str]]:
    with TOP10_INPUT.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_address(address: str, city: str, state: str = "FL") -> str:
    if not address or "NOT FOUND" in address:
        return ""
    return ", ".join(part for part in [address, city, state] if part)


def city_fallback_query(city: str, state: str = "FL") -> str:
    if not city:
        return ""
    return f"{city}, {state}"


def google_directions_link(origin: str, destination: str) -> str:
    if not origin or not destination:
        return ""
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}&travelmode=driving"
    )


def geocode_queries(queries: list[str]) -> dict[str, tuple[float, float] | None]:
    geolocator = Nominatim(user_agent="housing-top10-distance-export")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    results: dict[str, tuple[float, float] | None] = {}
    for query in queries:
        location = geocode(query, timeout=20)
        results[query] = (location.latitude, location.longitude) if location else None
    return results


def build_distance_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    listing_queries = [clean_address(row.get("address", ""), row.get("city", "")) for row in rows]
    fallback_queries = [city_fallback_query(row.get("city", "")) for row in rows]
    reference_queries = [item["query"] for item in REFERENCE_POINTS]
    all_queries = [query for query in listing_queries + fallback_queries + reference_queries if query]
    coords = geocode_queries(all_queries)

    output_rows: list[dict[str, str]] = []
    for row, listing_query, fallback_query in zip(rows, listing_queries, fallback_queries):
        listing_coords = coords.get(listing_query) if listing_query else None
        used_query = listing_query
        geocode_note = "exact address"
        if not listing_coords and fallback_query:
            listing_coords = coords.get(fallback_query)
            used_query = fallback_query
            geocode_note = "city fallback"
        record = dict(row)
        record["listing_query_address"] = used_query or "NEEDS LOCATION CHECK"
        record["distance_basis"] = geocode_note if listing_coords else "unresolved"
        for reference in REFERENCE_POINTS:
            ref_coords = coords.get(reference["query"])
            if listing_coords and ref_coords:
                miles = geodesic(ref_coords, listing_coords).miles
                record[f"distance_{reference['slug']}_miles"] = f"{miles:.1f}"
            else:
                record[f"distance_{reference['slug']}_miles"] = ""
            record[f"directions_from_{reference['slug']}"] = google_directions_link(reference["query"], used_query)
        if record["distance_husson_ave_miles"] and record["distance_desert_hills_miles"]:
            gap = abs(float(record["distance_husson_ave_miles"]) - float(record["distance_desert_hills_miles"]))
            record["distance_gap_miles"] = f"{gap:.1f}"
        else:
            record["distance_gap_miles"] = ""
        output_rows.append(record)
    return output_rows


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = [
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
        "distance_basis",
        "directions_from_husson_ave",
        "directions_from_desert_hills",
        "program_type",
        "rent_type",
        "exact_published_rent_by_bedroom",
        "exact_published_rent_by_income_bracket",
        "vacancy_likelihood_score",
        "vacancy_likelihood_reason",
        "confidence_score",
        "required_documents",
        "notes",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def link(url: str, label: str) -> str:
    if not url:
        return ""
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def render_card(row: dict[str, str]) -> str:
    phone = row.get("phone", "")
    return f"""
    <article class="card">
      <div class="rank">#{html.escape(row['rank'])}</div>
      <h2>{html.escape(row['property_name'])}</h2>
      <p><strong>City:</strong> {html.escape(row['city'])}</p>
      <p><strong>Address:</strong> {html.escape(row['address'])}</p>
      <p><strong>Phone:</strong> {link(f"tel:{''.join(ch for ch in phone if ch.isdigit())}", phone) if phone else 'NEEDS CALL'}</p>
      <p><strong>Program:</strong> {html.escape(row['program_type'])}</p>
      <p><strong>Best rent info:</strong> {html.escape(row['exact_published_rent_by_bedroom'] or row['exact_published_rent_by_income_bracket'])}</p>
      <p><strong>Distance from 1524 Husson Ave:</strong> {html.escape(row['distance_husson_ave_miles'] or 'unknown')} miles</p>
      <p><strong>Distance from 706 Desert Hills:</strong> {html.escape(row['distance_desert_hills_miles'] or 'unknown')} miles</p>
      <p><strong>How close to halfway:</strong> {html.escape(row['distance_gap_miles'] or 'unknown')} mile gap</p>
      <p><strong>Distance basis:</strong> {html.escape(row.get('distance_basis', ''))}</p>
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
    cards = "\n".join(render_card(row) for row in rows)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Top 10 Housing Listings With Distances</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f5f7fb; color: #15202b; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 16px; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    .sub {{ color: #4b5563; margin-bottom: 1rem; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; margin: 0 0 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
    .rank {{ display: inline-block; background: #2563eb; color: white; border-radius: 999px; padding: 4px 10px; font-weight: 700; margin-bottom: 8px; }}
    h2 {{ margin: 0 0 8px; font-size: 1.2rem; }}
    p {{ margin: 6px 0; line-height: 1.35; }}
    .links a {{ display: inline-block; margin-right: 12px; margin-top: 6px; color: #2563eb; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <main>
    <h1>Top 10 Affordable / Income-Based Listings With Distance</h1>
    <p class="sub">Distances are approximate straight-line miles from both reference addresses, plus quick map/directions links for phone use.</p>
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
    distance_rows = build_distance_rows(rows)
    write_csv(distance_rows)
    write_html(distance_rows)
    copy_to_artifacts()
    print(f"Wrote {OUTPUT_CSV.name}, {OUTPUT_HTML.name}, and artifact copies.")


if __name__ == "__main__":
    main()
