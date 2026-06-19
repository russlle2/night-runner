from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

PROPERTY_SUFFIXES = (
    "apartments",
    "apartment",
    "villas",
    "villa",
    "manor",
    "commons",
    "terrace",
    "townhomes",
    "townhome",
    "reserve",
    "gardens",
    "homes",
    "housing",
    "village",
    "court",
    "place",
    "pines",
)

PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
AMI_RE = re.compile(r"\b(?:30|40|50|60|80)%\s*AMI\b", re.I)
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b",
    re.I,
)
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Za-z0-9.\-]+\s+){1,5}"
    r"(?:Ave|Avenue|Blvd|Boulevard|Cir|Circle|Ct|Court|Dr|Drive|"
    r"Hwy|Highway|Ln|Lane|Rd|Road|St|Street|Ter|Terrace|Way|Trail|Pl|Place|Pkwy|Parkway|CR|County Road|Lk|Lake)\b"
    r"(?:\s+[A-Za-z0-9.\-]+){0,2}",
    re.I,
)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def soup_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return normalize_whitespace(soup.get_text(" ", strip=True))


def extract_phones(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).strip() for match in PHONE_RE.finditer(text or "")))


def extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).strip() for match in EMAIL_RE.finditer(text or "")))


def extract_addresses(text: str) -> list[str]:
    return list(dict.fromkeys(normalize_whitespace(match.group(0)) for match in ADDRESS_RE.finditer(text or "")))


def extract_money(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).replace(" ", "") for match in MONEY_RE.finditer(text or "")))


def extract_ami(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).upper().replace(" ", "") for match in AMI_RE.finditer(text or "")))


def extract_dates(text: str) -> list[str]:
    return list(dict.fromkeys(normalize_whitespace(match.group(0)) for match in DATE_RE.finditer(text or "")))


def property_name_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    sentences = re.split(r"[|•\n\r]+", text)
    for sentence in sentences:
        cleaned = normalize_whitespace(sentence)
        lower = cleaned.lower()
        if len(cleaned) < 4:
            continue
        if any(suffix in lower for suffix in PROPERTY_SUFFIXES):
            if len(cleaned.split()) <= 12:
                candidates.append(cleaned.title())
    return list(dict.fromkeys(candidates))


def snippets_with_keywords(text: str, keywords: Iterable[str], window: int = 220) -> list[str]:
    snippets: list[str] = []
    lower = text.lower()
    for keyword in keywords:
        start = 0
        while True:
            index = lower.find(keyword.lower(), start)
            if index == -1:
                break
            snippets.append(normalize_whitespace(text[max(0, index - window) : index + window]))
            start = index + len(keyword)
    return list(dict.fromkeys(snippets))


def infer_program_terms(text: str) -> list[str]:
    matches = []
    lowered = text.lower()
    for term in [
        "lihtc",
        "low-income housing tax credit",
        "section 8",
        "public housing",
        "hud",
        "usda",
        "rural development",
        "senior",
        "elderly",
        "disabled",
        "rental assistance",
        "voucher",
        "income based",
    ]:
        if term in lowered:
            matches.append(term)
    return matches


def first_non_empty(values: Iterable[str]) -> str:
    for value in values:
        if normalize_whitespace(value):
            return normalize_whitespace(value)
    return ""

