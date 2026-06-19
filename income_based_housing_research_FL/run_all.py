from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from config import INTERMEDIATE_DIR
from utils.io_utils import append_log, ensure_directories, read_json
from utils.scoring_utils import affordability_rank

STEPS = [
    "search_sources.py",
    "scrape_pages.py",
    "normalize_properties.py",
    "enrich_official_sources.py",
    "rent_extractor.py",
    "apply_requirements_extractor.py",
    "vacancy_estimator.py",
    "export_results.py",
]


def run_step(script_name: str) -> bool:
    append_log(f"run_all.py: starting {script_name}")
    result = subprocess.run([sys.executable, script_name], check=False)
    if result.returncode != 0:
        append_log(f"run_all.py: step failed {script_name} exit={result.returncode}")
        return False
    append_log(f"run_all.py: completed {script_name}")
    return True


def print_phone_verification_priority() -> None:
    payload = read_json(INTERMEDIATE_DIR / "properties_final.json", default=[])
    ranked = sorted(payload, key=affordability_rank)
    print("\nProperties needing phone verification (ranked):")
    for item in ranked[:15]:
        print(
            f"- {item['property_name']} | {item['city']} | program={item['program_type']} | "
            f"vacancy={item['vacancy_likelihood_score']} | distance={item.get('distance_miles_to_target_area')} | "
            f"confidence={item['confidence_score']} | phone={item.get('phone') or 'NOT FOUND / NEEDS CALL'}"
        )


def main() -> None:
    ensure_directories()
    Path("raw_html").mkdir(exist_ok=True)
    Path("screenshots").mkdir(exist_ok=True)
    Path("intermediate").mkdir(exist_ok=True)

    failures = []
    for step in STEPS:
        if not run_step(step):
            failures.append(step)
    print_phone_verification_priority()
    if failures:
        print("\nCompleted with failures:")
        for step in failures:
            print(f"- {step}")
    else:
        print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
