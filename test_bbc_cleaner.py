
from pathlib import Path

from scraper_bbc import parse_headlines
from cleaner import clean


def test_bbc_headlines_work_with_cleaner():
    html = Path("bbc_sample.html").read_text(encoding="utf-8")

    raw_headlines = parse_headlines(html)
    cleaned_headlines = clean(raw_headlines)

    assert len(cleaned_headlines) == 2

    for headline in cleaned_headlines:
        assert headline["headline_id"]
        assert headline["title"]
        assert headline["source"] == "BBC News"
        assert headline["url"].startswith("https://www.bbc.com/news/articles/")
        assert headline["seen_at"]

    print("BBC + Cleaner integration test passed!")


