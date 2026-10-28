from pathlib import Path
from unittest.mock import Mock, patch

from scraper_guardian import get_headlines

SAMPLE_FILE = Path(__file__).parent / "guardian_sample.html"


def test_guardian_parser():
    html = SAMPLE_FILE.read_text(encoding="utf-8")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_response.raise_for_status.return_value = None

    with patch("scraper_guardian.requests.get", return_value=mock_response):
        headlines = get_headlines()

    assert len(headlines) == 3

    required_keys = {
        "headline_id",
        "title",
        "source",
        "section",
        "published_at",
        "url",
        "seen_at",
    }

    for headline in headlines:
        assert set(headline.keys()) == required_keys
        assert headline["title"]
        assert headline["source"] == "The Guardian"
        assert headline["url"].startswith(
            "https://www.theguardian.com/"
        )


def test_guardian_handles_http_403():
    mock_response = Mock()
    mock_response.status_code = 403

    with patch("scraper_guardian.requests.get", return_value=mock_response):
        assert get_headlines() == []


def test_guardian_handles_http_429():
    mock_response = Mock()
    mock_response.status_code = 429

    with patch("scraper_guardian.requests.get", return_value=mock_response):
        assert get_headlines() == []