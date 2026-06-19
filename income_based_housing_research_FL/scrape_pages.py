from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from config import DISCOVERED_URLS_CSV, EXTRACTED_SNIPPETS_CSV, INTERMEDIATE_DIR, MAX_PLAYWRIGHT_SCREENSHOTS
from models import SnippetRecord
from utils.http_utils import can_fetch_url, fetch_url
from utils.io_utils import append_log, ensure_directories, read_csv, slugify, write_csv, write_json
from utils.text_utils import (
    extract_addresses,
    extract_dates,
    extract_emails,
    extract_phones,
    infer_program_terms,
    normalize_whitespace,
    property_name_candidates,
    snippets_with_keywords,
    soup_to_text,
)

KEYWORD_MAP = {
    "rent": ["rent", "income based", "call for rent", "affordable"],
    "application": ["application", "apply", "apply now", "paper application"],
    "waitlist": ["waitlist", "waiting list", "availability", "available now", "accepting applications"],
    "requirements": ["social security", "proof of income", "birth certificate", "background check", "deposit"],
}


def cache_path_for_url(url: str, extension: str = "html") -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    filename = f"{slugify(parsed.netloc)}-{digest}.{extension}"
    return Path("raw_html") / filename


def screenshot_path_for_url(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    filename = f"{slugify(parsed.netloc)}-{digest}.png"
    return Path("screenshots") / filename


def try_capture_screenshot(url: str, screenshot_path: Path) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        return ""

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1600})
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()
        return str(screenshot_path)
    except Exception as exc:  # noqa: BLE001
        append_log(f"scrape_pages.py: screenshot failed for {url}: {exc}")
        return ""


def extract_sumter_resource_rows(html: str, source_url: str, source_quality: str) -> list[SnippetRecord]:
    soup = BeautifulSoup(html, "lxml")
    records: list[SnippetRecord] = []
    text = soup.get_text("\n", strip=True)
    for line in text.splitlines():
        if " - " not in line or "Apartments" not in line and "Commons" not in line and "Townhomes" not in line and "Terrace" not in line:
            continue
        parts = [part.strip() for part in line.split(" - ", 1)]
        if len(parts) != 2:
            continue
        name, phone = parts
        records.append(
            SnippetRecord(
                source_url=source_url,
                candidate_property_name=name,
                source_quality=source_quality,
                city_hint="Wildwood" if "Wildwood" in name else "",
                county_hint="Sumter County",
                contact_phone=phone,
                snippet_type="lead",
                snippet_text=line,
            )
        )
    return records


def extract_usda_rows(html: str, source_url: str, source_quality: str) -> list[SnippetRecord]:
    soup = BeautifulSoup(html, "lxml")
    records: list[SnippetRecord] = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = [normalize_whitespace(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            if len(cells) >= 2 and cells[0].lower() not in {"name", "", "home/ select state/ select county/ properties"}:
                property_name = cells[0]
                town = cells[1]
                if "rental properties located in" in property_name.lower():
                    continue
                if not property_name or property_name == town:
                    continue
                records.append(
                    SnippetRecord(
                        source_url=source_url,
                        candidate_property_name=property_name,
                        source_quality=source_quality,
                        city_hint=town,
                        county_hint="Lake County" if "cnty=069" in source_url else "Sumter County",
                        snippet_type="lead",
                        snippet_text=f"{property_name} | {town}",
                    )
                )
    return records


def generic_records_from_page(html: str, row: dict[str, str], raw_html_path: str, screenshot_path: str) -> list[SnippetRecord]:
    soup = BeautifulSoup(html, "lxml")
    title = normalize_whitespace(soup.title.get_text(" ", strip=True) if soup.title else row.get("title", ""))
    text = soup_to_text(html)
    city_hint = row.get("city", "")
    county_hint = row.get("county", "")
    phones = extract_phones(text)
    emails = extract_emails(text)
    addresses = extract_addresses(text)
    dates = extract_dates(text)
    names = property_name_candidates(" | ".join([title, text[:5000]]))
    names = names[:6] if names else ([title] if title else [])
    source_quality = row.get("source_quality", "unknown")

    snippets: list[SnippetRecord] = []
    for name in names or ["Unknown Property"]:
        snippets.append(
            SnippetRecord(
                source_url=row["url"],
                source_title=title,
                candidate_property_name=name,
                source_quality=source_quality,
                city_hint=city_hint,
                county_hint=county_hint,
                contact_phone=phones[0] if phones else "",
                email=emails[0] if emails else "",
                address=addresses[0] if addresses else "",
                management_company_hint="",
                website_url=row["url"],
                snippet_type="page_summary",
                snippet_text=text[:700],
                raw_html_path=raw_html_path,
                screenshot_path=screenshot_path,
                last_updated_date_from_source=dates[0] if dates else "",
            )
        )
        for snippet_type, keywords in KEYWORD_MAP.items():
            for snippet in snippets_with_keywords(text, keywords, window=220)[:4]:
                snippets.append(
                    SnippetRecord(
                        source_url=row["url"],
                        source_title=title,
                        candidate_property_name=name,
                        source_quality=source_quality,
                        city_hint=city_hint,
                        county_hint=county_hint,
                        contact_phone=phones[0] if phones else "",
                        email=emails[0] if emails else "",
                        address=addresses[0] if addresses else "",
                        management_company_hint="",
                        website_url=row["url"],
                        snippet_type=snippet_type,
                        snippet_text=snippet,
                        raw_html_path=raw_html_path,
                        screenshot_path=screenshot_path,
                        last_updated_date_from_source=dates[0] if dates else "",
                    )
                )
        program_terms = infer_program_terms(text)
        if program_terms:
            snippets.append(
                SnippetRecord(
                    source_url=row["url"],
                    source_title=title,
                    candidate_property_name=name,
                    source_quality=source_quality,
                    city_hint=city_hint,
                    county_hint=county_hint,
                    contact_phone=phones[0] if phones else "",
                    email=emails[0] if emails else "",
                    address=addresses[0] if addresses else "",
                    management_company_hint="",
                    website_url=row["url"],
                    snippet_type="program_terms",
                    snippet_text=", ".join(program_terms),
                    raw_html_path=raw_html_path,
                    screenshot_path=screenshot_path,
                    last_updated_date_from_source=dates[0] if dates else "",
                )
            )
    return snippets


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch discovered pages and extract raw snippets.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for number of URLs to fetch.")
    parser.add_argument("--city", dest="city_filter", help="Only process discovered URLs tagged to one city.")
    args = parser.parse_args()

    ensure_directories()
    rows = read_csv(DISCOVERED_URLS_CSV)
    if args.city_filter:
        rows = [row for row in rows if row.get("city", "").lower() == args.city_filter.lower()]
    if args.limit:
        rows = rows[: args.limit]

    append_log(f"scrape_pages.py: processing {len(rows)} URLs")
    all_snippets: list[dict] = []
    cache_index: list[dict] = []
    screenshots_taken = 0

    for row in rows:
        url = row["url"]
        if not can_fetch_url(url):
            append_log(f"scrape_pages.py: skipped by robots {url}")
            continue
        try:
            response = fetch_url(url)
        except Exception as exc:  # noqa: BLE001
            append_log(f"scrape_pages.py: fetch failed {url}: {exc}")
            continue

        content_type = response.headers.get("content-type", "").lower()
        extension = "pdf" if "pdf" in content_type or url.lower().endswith(".pdf") else "html"
        raw_path = cache_path_for_url(url, extension=extension)
        absolute_raw_path = Path(raw_path)
        (Path.cwd() / absolute_raw_path).parent.mkdir(parents=True, exist_ok=True)
        if extension == "pdf":
            (Path.cwd() / absolute_raw_path).write_bytes(response.content)
            html = ""
        else:
            html = response.text
            (Path.cwd() / absolute_raw_path).write_text(html, encoding="utf-8", errors="ignore")

        screenshot_ref = ""
        if screenshots_taken < MAX_PLAYWRIGHT_SCREENSHOTS and extension == "html" and row.get("source_quality") in {
            "government",
            "HUD/USDA/FHFC",
            "housing_authority",
        }:
            target_path = Path.cwd() / screenshot_path_for_url(url)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot_ref = try_capture_screenshot(url, target_path)
            if screenshot_ref:
                screenshots_taken += 1

        page_snippets: list[SnippetRecord] = []
        if extension == "html":
            if "Rental-Assistance-Resources" in url:
                page_snippets.extend(extract_sumter_resource_rows(html, url, row.get("source_quality", "unknown")))
            if "rdmfhrentals.sc.egov.usda.gov" in url:
                page_snippets.extend(extract_usda_rows(html, url, row.get("source_quality", "unknown")))
            page_snippets.extend(generic_records_from_page(html, row, str(absolute_raw_path), screenshot_ref))

        all_snippets.extend([snippet.model_dump() for snippet in page_snippets])
        cache_index.append(
            {
                "source_url": url,
                "raw_path": str(absolute_raw_path),
                "screenshot_path": screenshot_ref,
                "content_type": content_type,
                "snippet_count": len(page_snippets),
            }
        )
        append_log(f"scrape_pages.py: processed {url} -> {len(page_snippets)} snippets")

    write_csv(EXTRACTED_SNIPPETS_CSV, all_snippets)
    write_json(INTERMEDIATE_DIR / "cache_index.json", cache_index)
    append_log(f"scrape_pages.py: wrote {len(all_snippets)} snippets")


if __name__ == "__main__":
    main()
