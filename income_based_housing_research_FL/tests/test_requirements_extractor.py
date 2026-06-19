import re

from apply_requirements_extractor import DOCUMENT_PATTERNS


def test_document_patterns_match_common_requirements():
    text = "Applicants must provide government-issued ID, Social Security card, proof of income, and a background check."
    matches = [label for label, pattern in DOCUMENT_PATTERNS.items() if re.search(pattern, text, re.I)]
    assert "government-issued ID" in matches
    assert "Social Security card" in matches
    assert "proof of income" in matches
    assert "background check" in matches
