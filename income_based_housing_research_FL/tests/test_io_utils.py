from utils.io_utils import sanitize_html_content


def test_sanitize_html_content_redacts_mapbox_tokens():
    token = "pk." + "abc123DEF456ghi789JKL"
    raw = f"mapbox token {token} embedded"
    sanitized = sanitize_html_content(raw)
    assert token not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
