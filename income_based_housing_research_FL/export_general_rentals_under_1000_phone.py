from __future__ import annotations

import csv
import html
from pathlib import Path
import re
from statistics import mean
from urllib.parse import quote_plus

from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = PROJECT_DIR / "general_rentals_under_1000_phone.csv"
OUTPUT_HTML = PROJECT_DIR / "general_rentals_under_1000_phone.html"
ARTIFACT_DIR = Path("/opt/cursor/artifacts")
ARTIFACT_CSV = ARTIFACT_DIR / OUTPUT_CSV.name
ARTIFACT_HTML = ARTIFACT_DIR / OUTPUT_HTML.name

REFERENCE_POINTS = [
    {
        "label": "1524 Husson Ave, Palatka, FL 32177",
        "slug": "husson",
        "query": "1524 Husson Ave, Palatka, FL 32177",
    },
    {
        "label": "706 Desert Hills Dr, Sun City Center, FL",
        "slug": "desert_hills",
        "query": "706 Desert Hills Dr, Sun City Center, FL",
    },
]

# Curated from current public listing snippets and pages already surfaced during research.
# Intentionally excludes retirement/senior-only communities.
CANDIDATES = [
    {
        "property_name": "6630 SW 22nd Way",
        "city": "Bushnell",
        "address": "6630 SW 22nd Way, Bushnell, FL 33513",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "800",
        "monthly_rent": 995,
        "source_url": "https://hotpads.com/6630-sw-22nd-way-bushnell-fl-33513-206mkxp/pad",
        "source_name": "HotPads",
        "source_note": "2 beds, 1 bath, 800 sqft, accepts applications, cats and small dogs allowed.",
        "listing_type": "general rental",
        "phone": "(321) 217-7746",
        "manager": "Josh Isleworth",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "Likely required but not published",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "301 S East St Apt 2",
        "city": "Leesburg",
        "address": "301 S East St Apt 2, Leesburg, FL 34748",
        "property_type": "Apartment",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "900",
        "monthly_rent": 800,
        "source_url": "https://www.realtor.com/rentals/details/301-S-East-St-Apt-2_Leesburg_FL_34748_M93185-41869",
        "source_name": "Realtor.com",
        "source_note": "Managed by landlord. Available today. 2 bedroom, 1 bathroom, 900 square feet.",
        "listing_type": "landlord-managed",
        "phone": "",
        "manager": "Landlord",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "301 S East St",
        "city": "Leesburg",
        "address": "301 S East St, Leesburg, FL 34748",
        "property_type": "Apartment",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "589",
        "monthly_rent": 800,
        "source_url": "https://www.realtor.com/rentals/details/301-S-East-St_Leesburg_FL_34748_M96058-49613",
        "source_name": "Realtor.com",
        "source_note": "Managed by landlord. Available today. 2 bedroom, 1 bathroom, 589 square feet.",
        "listing_type": "landlord-managed",
        "phone": "",
        "manager": "Landlord",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "200 Church St Apt F4",
        "city": "Leesburg",
        "address": "200 Church St Apt F4, Leesburg, FL 34748",
        "property_type": "Apartment",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "",
        "monthly_rent": 995,
        "source_url": "https://dwellsy.com/details/7317290",
        "source_name": "Dwellsy",
        "source_note": "Oak Grove Apartments. Monthly pest control included.",
        "listing_type": "property management",
        "phone": "",
        "manager": "Property management / owner approval required",
        "application_fee": "$75 per adult",
        "security_deposit": "$1,095",
        "move_in_fee": "$200 move-in processing fee",
        "pet_fee": "$250 non-refundable pet deposit",
        "first_month_required": "$995 first month rent",
        "move_in_total_published": "$2,365 before any optional pet charges",
        "retirement_only": False,
    },
    {
        "property_name": "203 Jackson St",
        "city": "Wildwood",
        "address": "203 Jackson St, Wildwood, FL 34785",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "672",
        "monthly_rent": 700,
        "source_url": "https://www.apartments.com/203-jackson-st-wildwood-fl/rgdhh82/",
        "source_name": "Apartments.com",
        "source_note": "Available listing surfaced on Apartments.com under-$1000 Wildwood results.",
        "listing_type": "general rental",
        "phone": "(407) 637-1228",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "205 Jackson St",
        "city": "Wildwood",
        "address": "205 Jackson St, Wildwood, FL 34785",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "672",
        "monthly_rent": 700,
        "source_url": "https://www.apartments.com/205-jackson-st-wildwood-fl/bc96sr8/",
        "source_name": "Apartments.com",
        "source_note": "Available May 5. Cute 2 bed, 1 bath home.",
        "listing_type": "general rental",
        "phone": "(407) 637-1228",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "403 Kilgore St",
        "city": "Wildwood",
        "address": "403 Kilgore St, Wildwood, FL 34785",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "672",
        "monthly_rent": 850,
        "source_url": "https://www.apartments.com/403-kilgore-st-wildwood-fl/6cevsrr/",
        "source_name": "Apartments.com",
        "source_note": "Available under-$1000 Wildwood listing surfaced in Apartments.com results.",
        "listing_type": "general rental",
        "phone": "(407) 637-1228",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "805 Peters St",
        "city": "Wildwood",
        "address": "805 Peters St, Wildwood, FL 34785",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "672",
        "monthly_rent": 700,
        "source_url": "https://www.apartments.com/805-peters-st-wildwood-fl/dbg56zk/",
        "source_name": "Apartments.com",
        "source_note": "Available now. Cute 2 bed, 1 bath home.",
        "listing_type": "general rental",
        "phone": "(407) 637-1228",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "7068 County Road 213",
        "city": "Wildwood",
        "address": "7068 County Road 213, Wildwood, FL 34785",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "",
        "monthly_rent": 650,
        "source_url": "https://www.apartments.com/7068-county-road-213-wildwood-fl/3rsv26e/",
        "source_name": "Apartments.com",
        "source_note": "Recently remodeled cozy 2 bedroom 1 bath home.",
        "listing_type": "general rental",
        "phone": "",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "7050 County Road 213 Unit A",
        "city": "Wildwood",
        "address": "7050 County Road 213 Unit A, Wildwood, FL 34785",
        "property_type": "Apartment / Duplex Unit",
        "bedrooms": 3,
        "bathrooms": "1",
        "sqft": "1944",
        "monthly_rent": 700,
        "source_url": "https://www.apartments.com/7050-county-road-213-wildwood-fl-unit-a/s192wt4/",
        "source_name": "Apartments.com",
        "source_note": "Very clean 3 bedroom 1 bath duplex. Recently remodeled.",
        "listing_type": "general rental",
        "phone": "",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "NOT FOUND / NEEDS CALL",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "NOT FOUND / NEEDS CALL",
        "first_month_required": "NOT FOUND / NEEDS CALL",
        "move_in_total_published": "NOT FOUND / NEEDS CALL",
        "retirement_only": False,
    },
    {
        "property_name": "2573 County Road 426A",
        "city": "Lake Panasoffkee",
        "address": "2573 County Road 426A, Lake Panasoffkee, FL 33538",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": "1",
        "sqft": "",
        "monthly_rent": 1000,
        "source_url": "https://hotpads.com/2573-county-road-426a-lake-panasoffkee-fl-33538-1n7mzpk/pad",
        "source_name": "HotPads",
        "source_note": "Most recently listed at $1,000/mo. Renter is responsible for utilities.",
        "listing_type": "general rental",
        "phone": "",
        "manager": "",
        "application_fee": "NOT FOUND / NEEDS CALL",
        "security_deposit": "$1,000",
        "move_in_fee": "NOT FOUND / NEEDS CALL",
        "pet_fee": "$200 one-time non-refundable pet fee",
        "first_month_required": "$1,000 first month rent",
        "move_in_total_published": "$2,000 before pet fee",
        "retirement_only": False,
    },
]


def monthly_budget(annual_income: int) -> int:
    return round((annual_income * 0.30) / 12)


def budget_fit(rent: int, budget: int) -> str:
    return "At or under budget" if rent <= budget else "Above budget"


def google_maps_search(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def google_directions_link(origin: str, destination: str) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}&travelmode=driving"
    )


def geocode_queries(queries: list[str]) -> dict[str, tuple[float, float]]:
    geolocator = Nominatim(user_agent="general-rentals-under-1000-export")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    results: dict[str, tuple[float, float]] = {}
    for query in queries:
        location = geocode(query, timeout=20)
        if location:
            results[query] = (location.latitude, location.longitude)
    return results


def simplified_address(address: str) -> str:
    simplified = re.sub(r"\b(Apt|Apartment|Unit)\s+[A-Za-z0-9-]+\b", "", address, flags=re.I)
    simplified = simplified.replace("  ", " ").replace(" ,", ",")
    return simplified.strip()


def rank_key(item: dict) -> tuple:
    # Prefer results that are slightly closer to Sun City Center, then closest to halfway, then cheapest.
    sun_city_gap = item["distance_desert_hills_miles"] - item["distance_husson_miles"]
    sun_city_priority = 0 if sun_city_gap < 0 else 1
    owner_priority = 0 if item["listing_type"] in {"landlord-managed", "general rental"} else 1
    return (
        sun_city_priority,
        abs(sun_city_gap),
        item["monthly_rent"],
        owner_priority,
        -item["bedrooms"],
    )


def build_rows() -> list[dict]:
    husson_budget = monthly_budget(21000)
    desert_budget = monthly_budget(41000)
    reference_queries = [item["query"] for item in REFERENCE_POINTS]
    queries = []
    for candidate in CANDIDATES:
        queries.append(candidate["address"])
        queries.append(simplified_address(candidate["address"]))
        queries.append(f"{candidate['city']}, FL")
    queries += reference_queries
    coords = geocode_queries(queries)

    husson_coords = coords[REFERENCE_POINTS[0]["query"]]
    desert_coords = coords[REFERENCE_POINTS[1]["query"]]

    rows = []
    for candidate in CANDIDATES:
        lookup_queries = [
            candidate["address"],
            simplified_address(candidate["address"]),
            f"{candidate['city']}, FL",
        ]
        listing_coords = None
        used_query = candidate["address"]
        for query in lookup_queries:
            if query in coords:
                listing_coords = coords[query]
                used_query = query
                break
        if listing_coords is None:
            continue
        husson_miles = geodesic(husson_coords, listing_coords).miles
        desert_miles = geodesic(desert_coords, listing_coords).miles
        gap = abs(desert_miles - husson_miles)
        lean = "Sun City Center closer" if desert_miles < husson_miles else "Palatka closer"
        row = dict(candidate)
        row["distance_husson_miles"] = round(husson_miles, 1)
        row["distance_desert_hills_miles"] = round(desert_miles, 1)
        row["distance_gap_miles"] = round(gap, 1)
        row["distance_preference"] = lean
        row["distance_basis"] = "exact address" if used_query == candidate["address"] else "fallback geocode"
        row["map_link"] = google_maps_search(candidate["address"])
        row["directions_from_husson"] = google_directions_link(REFERENCE_POINTS[0]["query"], candidate["address"])
        row["directions_from_desert_hills"] = google_directions_link(REFERENCE_POINTS[1]["query"], candidate["address"])
        row["income_21k_monthly_budget"] = f"${husson_budget}"
        row["income_41k_monthly_budget"] = f"${desert_budget}"
        row["income_21k_fit"] = budget_fit(candidate["monthly_rent"], husson_budget)
        row["income_41k_fit"] = budget_fit(candidate["monthly_rent"], desert_budget)
        rows.append(row)

    filtered = [row for row in rows if not row["retirement_only"] and row["monthly_rent"] <= 1000 and row["bedrooms"] >= 2]
    ranked = sorted(filtered, key=rank_key)[:10]
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return ranked


def average_summary(rows: list[dict]) -> dict[str, str]:
    two_br = [row["monthly_rent"] for row in rows if row["bedrooms"] == 2]
    three_br = [row["monthly_rent"] for row in rows if row["bedrooms"] == 3]
    return {
        "avg_2br_rent": f"${mean(two_br):.0f}" if two_br else "No 2BR data",
        "avg_3br_rent": f"${mean(three_br):.0f}" if three_br else "No 3BR data",
        "budget_21k": f"${monthly_budget(21000)}",
        "budget_41k": f"${monthly_budget(41000)}",
    }


def csv_fieldnames() -> list[str]:
    return [
        "rank",
        "property_name",
        "city",
        "address",
        "property_type",
        "bedrooms",
        "bathrooms",
        "sqft",
        "monthly_rent",
        "distance_husson_miles",
        "distance_desert_hills_miles",
        "distance_gap_miles",
        "distance_preference",
        "distance_basis",
        "listing_type",
        "phone",
        "manager",
        "application_fee",
        "security_deposit",
        "move_in_fee",
        "pet_fee",
        "first_month_required",
        "move_in_total_published",
        "income_21k_monthly_budget",
        "income_41k_monthly_budget",
        "income_21k_fit",
        "income_41k_fit",
        "source_name",
        "source_url",
        "map_link",
        "directions_from_husson",
        "directions_from_desert_hills",
        "source_note",
    ]


def write_csv(rows: list[dict]) -> None:
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fieldnames())
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in csv_fieldnames()})


def link(url: str, label: str) -> str:
    if not url:
        return ""
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def tel_link(phone: str) -> str:
    digits = "".join(char for char in phone if char.isdigit())
    if not digits:
        return "NEEDS CALL"
    return f'<a href="tel:{digits}">{html.escape(phone)}</a>'


def render_card(row: dict) -> str:
    return f"""
    <article class="card">
      <div class="rank">#{row['rank']}</div>
      <h2>{html.escape(row['property_name'])}</h2>
      <p><strong>Rent:</strong> ${row['monthly_rent']}/month</p>
      <p><strong>Type:</strong> {html.escape(row['property_type'])} • {row['bedrooms']} bed • {html.escape(row['bathrooms'])} bath • {html.escape(row['sqft'] or 'sqft not published')}</p>
      <p><strong>Distance from Husson:</strong> {row['distance_husson_miles']} mi</p>
      <p><strong>Distance from Desert Hills:</strong> {row['distance_desert_hills_miles']} mi</p>
      <p><strong>Closer side:</strong> {html.escape(row['distance_preference'])} (gap {row['distance_gap_miles']} mi)</p>
      <p><strong>Move-in fees:</strong> {html.escape(row['move_in_total_published'])}</p>
      <p><strong>Application fee:</strong> {html.escape(row['application_fee'])}</p>
      <p><strong>Security deposit:</strong> {html.escape(row['security_deposit'])}</p>
      <p><strong>Move-in fee / processing:</strong> {html.escape(row['move_in_fee'])}</p>
      <p><strong>Pet fee:</strong> {html.escape(row['pet_fee'])}</p>
      <p><strong>$21k budget test:</strong> {html.escape(row['income_21k_monthly_budget'])}/mo → {html.escape(row['income_21k_fit'])}</p>
      <p><strong>$41k budget test:</strong> {html.escape(row['income_41k_monthly_budget'])}/mo → {html.escape(row['income_41k_fit'])}</p>
      <p><strong>Phone:</strong> {tel_link(row['phone'])}</p>
      <p><strong>Notes:</strong> {html.escape(row['source_note'])}</p>
      <p class="links">
        {link(row['source_url'], 'Source')}
        {link(row['map_link'], 'Map')}
        {link(row['directions_from_husson'], 'Directions from Husson')}
        {link(row['directions_from_desert_hills'], 'Directions from Desert Hills')}
      </p>
    </article>
    """


def write_html(rows: list[dict]) -> None:
    summary = average_summary(rows)
    cards = "\n".join(render_card(row) for row in rows)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>General Rentals Under $1000 Near The Villages Area</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f5f7fb; color: #15202b; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 16px; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
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
    <h1>General Rentals Under $1,000 (2+ Bedrooms Preferred)</h1>
    <p class="sub">Same target geography, excludes retirement / 55+ / 62+ communities, and ranks listings to lean closer to Sun City Center while staying as close to halfway as possible.</p>
    <section class="summary">
      <p><strong>Average published 2BR rent in this shortlist:</strong> {summary['avg_2br_rent']}</p>
      <p><strong>Average published 3BR rent in this shortlist:</strong> {summary['avg_3br_rent']}</p>
      <p><strong>$21k income monthly budget at 30%:</strong> {summary['budget_21k']}</p>
      <p><strong>$41k income monthly budget at 30%:</strong> {summary['budget_41k']}</p>
      <p><strong>Move-in fee rule:</strong> only published move-in fees are shown; otherwise fields are marked NEEDS CALL.</p>
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
    rows = build_rows()
    write_csv(rows)
    write_html(rows)
    copy_to_artifacts()
    print(f"Wrote {OUTPUT_CSV.name}, {OUTPUT_HTML.name}, and artifact copies.")


if __name__ == "__main__":
    main()
