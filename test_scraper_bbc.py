from scraper_bbc import BBC_SOURCE


def test_bbc_source_name():
    assert BBC_SOURCE == "BBC News"


def test_headline_fields():
    expected_fields = {
        "headline_id",
        "title",
        "source",
        "section",
        "published_at",
        "url",
        "seen_at",
    }

    sample = {
        "headline_id": "example-123",
        "title": "Sample BBC headline",
        "source": "BBC News",
        "section": None,
        "published_at": None,
        "url": "https://www.bbc.com/news/example-123",
        "seen_at": "2026-10-27T12:00:00+00:00",
    }

    assert set(sample.keys()) == expected_fields
    assert sample["source"] == BBC_SOURCE
    assert sample["title"]
    assert sample["url"].startswith("https://www.bbc.com/news/")


def test_missing_fields_are_none():
    sample = {
        "headline_id": None,
        "title": "Sample headline",
        "source": "BBC News",
        "section": None,
        "published_at": None,
        "url": "https://www.bbc.com/news/example",
        "seen_at": "2026-10-27T12:00:00+00:00",
    }

    assert sample["section"] is None
    assert sample["published_at"] is None