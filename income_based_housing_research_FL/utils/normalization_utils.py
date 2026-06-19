from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz


def is_placeholder_value(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"", "unknown", "not found", "not found / needs call", "needs call"}


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def normalize_address(address: str) -> str:
    value = (address or "").lower().strip()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    replacements = {
        "street": "st",
        "avenue": "ave",
        "boulevard": "blvd",
        "circle": "cir",
        "court": "ct",
        "drive": "dr",
        "lane": "ln",
        "road": "rd",
        "terrace": "ter",
        "highway": "hwy",
        "county road": "cr",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value


def normalize_name(name: str) -> str:
    value = (name or "").lower().strip()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def likely_same_property(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_raw_address = left.get("address", "")
    right_raw_address = right.get("address", "")
    left_address = "" if is_placeholder_value(left_raw_address) else normalize_address(left_raw_address)
    right_address = "" if is_placeholder_value(right_raw_address) else normalize_address(right_raw_address)
    if left_address and right_address and left_address == right_address:
        return True

    left_raw_phone = left.get("phone", "")
    right_raw_phone = right.get("phone", "")
    left_phone = "" if is_placeholder_value(left_raw_phone) else normalize_phone(left_raw_phone)
    right_phone = "" if is_placeholder_value(right_raw_phone) else normalize_phone(right_raw_phone)
    if left_phone and right_phone and left_phone == right_phone:
        left_name = normalize_name(left.get("property_name", ""))
        right_name = normalize_name(right.get("property_name", ""))
        return fuzz.token_sort_ratio(left_name, right_name) >= 65

    left_name = normalize_name(left.get("property_name", ""))
    right_name = normalize_name(right.get("property_name", ""))
    if left_name and right_name and fuzz.token_sort_ratio(left_name, right_name) >= 90:
        if left.get("city", "").lower() == right.get("city", "").lower():
            return True
    return False


def merge_unique_strings(*values: str) -> str:
    ordered = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return " | ".join(ordered)


def choose_preferred_value(current: str, candidate: str) -> str:
    if not current and candidate:
        return candidate
    if "NOT FOUND" in current and candidate:
        return candidate
    if "NEEDS CALL" in current and candidate:
        return candidate
    return current or candidate
