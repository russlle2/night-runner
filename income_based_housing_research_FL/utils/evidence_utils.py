from __future__ import annotations

from typing import Any

from models import EvidenceRecord, HousingProperty


def add_evidence(
    property_record: HousingProperty,
    source_url: str,
    source_quality: str,
    confirmed_fields: list[str],
    snippet: str,
    raw_html_path: str = "",
    screenshot_path: str = "",
    notes: str = "",
) -> None:
    property_record.add_evidence(
        EvidenceRecord(
            source_url=source_url,
            source_quality=source_quality,
            confirmed_fields=confirmed_fields,
            snippet=snippet,
            raw_html_path=raw_html_path,
            screenshot_path=screenshot_path,
            notes=notes,
        )
    )


def evidence_lines(property_record: HousingProperty) -> list[str]:
    lines = []
    for evidence in property_record.evidence:
        lines.append(
            f"- {evidence.source_url} [{evidence.source_quality}] — "
            f"confirmed: {', '.join(evidence.confirmed_fields) or 'general lead'}"
        )
        if evidence.snippet:
            lines.append(f"  - snippet: {evidence.snippet}")
        if evidence.raw_html_path:
            lines.append(f"  - raw_html: {evidence.raw_html_path}")
        if evidence.screenshot_path:
            lines.append(f"  - screenshot: {evidence.screenshot_path}")
        if evidence.notes:
            lines.append(f"  - notes: {evidence.notes}")
    return lines


def flatten_evidence_for_notes(evidence_items: list[dict[str, Any]]) -> str:
    parts = []
    for item in evidence_items:
        snippet = item.get("snippet", "").strip()
        if snippet:
            parts.append(snippet)
    return " || ".join(parts[:8])
