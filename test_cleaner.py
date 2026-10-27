
# test_cleaner.py

from cleaner import clean, clean_with_stats, HEADLINE_KEYS


def test_valid_headline():
    data = [{
        "headline_id": "old-id",
        "title": "  Breaking   News  ",
        "source": " BBC News ",
        "section": " World ",
        "published_at": "2026-10-26T10:31:00Z",
        "url": "https://example.com/news/1",
        "seen_at": None,
    }]

    result = clean(data)

    assert len(result) == 1
    assert result[0]["title"] == "Breaking News"
    assert result[0]["source"] == "BBC News"
    assert result[0]["section"] == "World"
    assert result[0]["headline_id"] != "old-id"
    assert result[0]["published_at"] == "2026-10-26T10:31:00+00:00"
    assert list(result[0].keys()) == HEADLINE_KEYS


def test_duplicate_urls_removed():
    data = [
        {
            "title": "News A",
            "url": "https://example.com/news/1",
            "source": "BBC News",
        },
        {
            "title": "News A duplicate",
            "url": "https://example.com/news/1#comments",
            "source": "BBC News",
        },
    ]

    result = clean(data)

    assert len(result) == 1


def test_broken_records_skipped():
    data = [
        {"title": "", "url": "https://example.com/1"},
        {"title": "Missing URL", "url": None},
        None,
        {
            "title": "Valid news",
            "url": "https://example.com/valid",
        },
    ]

    result, failed = clean_with_stats(data)

    assert len(result) == 1
    assert failed == 3


def test_invalid_date_does_not_remove_headline():
    data = [{
        "title": "News with invalid date",
        "url": "https://example.com/date",
        "published_at": "not-a-real-date",
    }]

    result = clean(data)

    assert len(result) == 1
    assert result[0]["published_at"] is None


def test_missing_optional_fields_are_none():
    result = clean([{
        "title": "Simple news",
        "url": "https://example.com/simple",
    }])

    assert result[0]["source"] is None
    assert result[0]["section"] is None
    assert result[0]["published_at"] is None


def test_headline_id_is_stable():
    first = clean([{
        "title": "News",
        "url": "https://example.com/article",
    }])

    second = clean([{
        "title": "Updated News",
        "url": "https://example.com/article",
    }])

    assert first[0]["headline_id"] == second[0]["headline_id"]

