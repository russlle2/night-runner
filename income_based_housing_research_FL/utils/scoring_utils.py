from __future__ import annotations

import math
from datetime import datetime

from geopy.distance import geodesic

from config import CONFIDENCE_RULES, SOURCE_QUALITY_WEIGHTS, TARGET_LOCATIONS


def compute_distance_miles(city: str, latitude: float | None, longitude: float | None) -> float | None:
    if latitude is None or longitude is None:
        return None
    distances = []
    for location in TARGET_LOCATIONS:
        coords = (location["latitude"], location["longitude"])
        distances.append(geodesic(coords, (latitude, longitude)).miles)
    return round(min(distances), 1) if distances else None


def score_confidence(
    source_quality: str,
    source_count: int,
    has_official_address: bool,
    has_official_phone: bool,
    has_official_program: bool,
    last_updated_date_from_source: str,
    phone_verification_needed: bool,
    exact_rent_known: bool,
) -> int:
    base = int(SOURCE_QUALITY_WEIGHTS.get(source_quality, 0.45) * 60)
    score = base
    if has_official_address:
        score += CONFIDENCE_RULES["official_address_bonus"]
    if has_official_phone:
        score += CONFIDENCE_RULES["official_phone_bonus"]
    if has_official_program:
        score += CONFIDENCE_RULES["official_program_bonus"]
    if source_count >= 2:
        score += CONFIDENCE_RULES["multiple_sources_bonus"]
    if is_recent(last_updated_date_from_source):
        score += CONFIDENCE_RULES["recent_update_bonus"]
    elif last_updated_date_from_source:
        score -= CONFIDENCE_RULES["stale_penalty"]
    if phone_verification_needed:
        score -= CONFIDENCE_RULES["call_required_penalty"]
    if not exact_rent_known:
        score -= CONFIDENCE_RULES["missing_rent_penalty"]
    score = max(CONFIDENCE_RULES["minimum_score"], min(CONFIDENCE_RULES["maximum_score"], score))
    return int(score)


def is_recent(date_text: str) -> bool:
    if not date_text:
        return False
    formats = ["%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_text, fmt)
            age_days = (datetime.utcnow() - parsed).days
            return age_days <= 365
        except ValueError:
            continue
    return False


def affordability_rank(property_record: dict) -> tuple:
    rent_type = property_record.get("rent_type", "unknown")
    vacancy = property_record.get("vacancy_likelihood_score", 0)
    distance = property_record.get("distance_miles_to_target_area")
    confidence = property_record.get("confidence_score", 0)
    exact_rent = property_record.get("exact_published_rent_by_bedroom", "NOT FOUND")
    affordability_priority = {
        "income-based": 4,
        "max LIHTC rent": 3,
        "fixed affordable rent": 2,
        "market + vouchers accepted": 1,
        "unknown": 0,
    }.get(rent_type, 0)
    known_rent_bonus = 1 if exact_rent and "NOT FOUND" not in exact_rent else 0
    distance_value = distance if distance is not None else math.inf
    return (-affordability_priority, -vacancy, distance_value, -confidence, -known_rent_bonus)


def infer_vacancy_from_text(text: str) -> tuple[int, str, str, str]:
    lower = (text or "").lower()
    if any(phrase in lower for phrase in ["waitlist closed", "not accepting applications", "no availability"]):
        return 0, "Source states the waitlist is closed or no units are available.", "closed", "no_vacancy"
    if any(phrase in lower for phrase in ["available now", "units available", "move in now", "now leasing"]):
        return 4, "Source indicates units are available now.", "open", "available_now"
    if any(phrase in lower for phrase in ["waitlist open", "accepting applications", "apply now", "open waiting list"]):
        return 3, "Source indicates the property is accepting applications or has an open waitlist.", "open", "waitlist_only"
    if any(phrase in lower for phrase in ["call for availability", "contact for availability", "check availability"]):
        return 2, "Property appears active but vacancy must be confirmed with the property.", "call_required", "call_required"
    if any(phrase in lower for phrase in ["waitlist", "contact property", "availability unknown"]):
        return 1, "Listing exists, but availability information is stale or unclear.", "unknown", "unknown"
    return 2, "No reliable online vacancy evidence located; property verification is required.", "call_required", "call_required"
