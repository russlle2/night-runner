from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from config import (
    CALL_SCRIPT_MD,
    INTERMEDIATE_DIR,
    PIPELINE_LOG,
    RAW_HTML_DIR,
    SCREENSHOTS_DIR,
    SOURCE_LOG_MD,
)


def ensure_directories() -> None:
    for path in [RAW_HTML_DIR, SCREENSHOTS_DIR, INTERMEDIATE_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    for path in [PIPELINE_LOG, SOURCE_LOG_MD, CALL_SCRIPT_MD]:
        if not path.exists():
            path.write_text("", encoding="utf-8")


def slugify(value: str, max_length: int = 80) -> str:
    sanitized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    collapsed = "-".join(segment for segment in sanitized.split("-") if segment)
    return (collapsed or "item")[:max_length]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_log(message: str) -> None:
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PIPELINE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")

