from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from urllib.parse import quote_plus

from utils.scoring_utils import affordability_rank

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "housing_results.csv"
OUTPUT_CSV = BASE_DIR / "top_10_listings_phone.csv"
OUTPUT_HTML = BASE_DIR / "top_10_listings_phone.html"

EXPORT_COLUMNS = [
    "rank",
    "property_name",
    "city",
    "county",
    "address",
    "phone",
    "website_url",
    "application_url",
    "primary_source_url",
    "map_link",
    "program_type",
    "rent_type",
    "exact_published_rent_by_bedroom",
    "exact_published_rent_by_income_bracket",
    "waitlist_status",
    "vacancy_status",
    "vacancy_likelihood_score",
    "vacancy_likelihood_reason",
    "confidence_score",
    "required_documents",
    "notes",
]


def load_rows() -> list[dict[str, str]]:
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_phone_for_tel(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def first_source_url(source_urls: str) -> str:
    parts = [part.strip() for part in (source_urls or "").split(";") if part.strip()]
    return parts[0] if parts else ""


def build_map_link(address: str, city: str, state: str = "FL") -> str:
    query = ", ".join(part for part in [address, city, state] if part and "NOT FOUND" not in part)
    if not query:
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def top_ten_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    enriched = []
    for row in rows:
        ranked = dict(row)
        ranked["distance_miles_to_target_area"] = parse_float(row.get("distance_miles_to_target_area", ""))
        ranked["vacancy_likelihood_score"] = int(row.get("vacancy_likelihood_score") or 0)
        ranked["confidence_score"] = int(row.get("confidence_score") or 0)
        ranked["primary_source_url"] = first_source_url(row.get("source_urls", ""))
        ranked["map_link"] = build_map_link(row.get("address", ""), row.get("city", ""), row.get("state", "FL"))
        enriched.append(ranked)
    top = sorted(enriched, key=affordability_rank)[:10]
    output = []
    for index, row in enumerate(top, start=1):
        item = {}
        for column in EXPORT_COLUMNS:
            if column == "rank":
                continue
            value = row.get(column, "")
            item[column] = "" if value is None else str(value)
        item["rank"] = str(index)
        output.append(item)
    return output


def write_csv(rows: list[dict[str, str]]) -> None:
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def anchor(url: str, label: str) -> str:
    if not url:
        return ""
    safe_url = html.escape(url, quote=True)
    safe_label = html.escape(label)
    return f'<a href="{safe_url}">{safe_label}</a>'


def html_card(row: dict[str, str]) -> str:
    phone = row.get("phone", "")
    tel = normalize_phone_for_tel(phone)
    website_url = row.get("website_url", "")
    application_url = row.get("application_url", "")
    source_url = row.get("primary_source_url", "")
    map_link = row.get("map_link", "")
    rent_display = row.get("exact_published_rent_by_bedroom", "NOT FOUND")
    if rent_display == "NOT FOUND":
        rent_display = row.get("exact_published_rent_by_income_bracket", "NOT FOUND")
    return f"""
    <article class="card">
      <div class="rank">#{html.escape(row['rank'])}</div>
      <h2>{html.escape(row['property_name'])}</h2>
      <p><strong>City:</strong> {html.escape(row['city'])}</p>
      <p><strong>Address:</strong> {html.escape(row['address'])}</p>
      <p><strong>Program:</strong> {html.escape(row['program_type'])}</p>
      <p><strong>Rent type:</strong> {html.escape(row['rent_type'])}</p>
      <p><strong>Best rent info:</strong> {html.escape(rent_display)}</p>
      <p><strong>Vacancy:</strong> score {html.escape(row['vacancy_likelihood_score'])} — {html.escape(row['vacancy_likelihood_reason'])}</p>
      <p><strong>Confidence:</strong> {html.escape(row['confidence_score'])}</p>
      <p><strong>Phone:</strong> {anchor(f'tel:{tel}', phone) if tel else 'NEEDS CALL / NO CLEAN PHONE FOUND'}</p>
      <p class="links">
        {anchor(website_url, 'Website') if website_url else ''}
        {anchor(application_url, 'Apply') if application_url else ''}
        {anchor(source_url, 'Source') if source_url else ''}
        {anchor(map_link, 'Map') if map_link else ''}
      </p>
      <details>
        <summary>More details</summary>
        <p><strong>Waitlist:</strong> {html.escape(row['waitlist_status'])}</p>
        <p><strong>Vacancy status:</strong> {html.escape(row['vacancy_status'])}</p>
        <p><strong>Required documents:</strong> {html.escape(row['required_documents'])}</p>
        <p><strong>Notes:</strong> {html.escape(row['notes'])}</p>
      </details>
    </article>
    """


def write_html(rows: list[dict[str, str]]) -> None:
    cards = "\n".join(html_card(row) for row in rows)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Top 10 Affordable Housing Listings</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f5f7fb; color: #15202b; }}
    main {{ max-width: 900px; margin: 0 auto; padding: 16px; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    .sub {{ color: #4b5563; margin-bottom: 1rem; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; margin: 0 0 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
    .rank {{ display: inline-block; background: #2563eb; color: white; border-radius: 999px; padding: 4px 10px; font-weight: 700; margin-bottom: 8px; }}
    h2 {{ margin: 0 0 8px; font-size: 1.2rem; }}
    p {{ margin: 6px 0; line-height: 1.35; }}
    .links a {{ display: inline-block; margin-right: 12px; margin-top: 6px; color: #2563eb; text-decoration: none; font-weight: 600; }}
    summary {{ cursor: pointer; font-weight: 600; margin-top: 10px; }}
  </style>
</head>
<body>
  <main>
    <h1>Top 10 Affordable / Income-Based Housing Listings</h1>
    <p class="sub">Ranked using the existing workflow factors: affordability, income-based eligibility, vacancy likelihood, distance, confidence, and whether exact rent was published.</p>
    {cards}
  </main>
</body>
</html>
"""
    OUTPUT_HTML.write_text(document, encoding="utf-8")


def main() -> None:
    rows = load_rows()
    top_rows = top_ten_rows(rows)
    write_csv(top_rows)
    write_html(top_rows)
    print(f"Wrote {OUTPUT_CSV.name} and {OUTPUT_HTML.name}")


if __name__ == "__main__":
    main()
