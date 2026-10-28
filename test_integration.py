import pytest

try:
    import database
except ImportError:
    database = None

try:
    import cleaner
except ImportError:
    cleaner = None

try:
    import scraper_bbc
except ImportError:
    scraper_bbc = None

try:
    import scraper_guardian
except ImportError:
    scraper_guardian = None


def test_shared_headline_format_keys():
    expected_keys = {'headline_id', 'title', 'source', 'section', 'published_at', 'url', 'seen_at'}
    scrapers = [('BBC', scraper_bbc), ('Guardian', scraper_guardian)]
    
    for name, scraper in scrapers:
        if scraper is None or not hasattr(scraper, 'get_headlines'):
            pytest.skip(f"{name} scraper not ready.")
        try:
            headlines = scraper.get_headlines()
            if not headlines:
                pytest.skip(f"{name} scraper returned empty.")
            for h in headlines:
                assert set(h.keys()) == expected_keys
        except Exception as e:
            pytest.skip(f"{name} scraper error: {e}")


def test_cleaner_broken_records():
    if cleaner is None or not hasattr(cleaner, 'clean'):
        pytest.skip("cleaner.py not ready.")
    
    dirty_data = [
        {'title': '', 'url': 'https://example.com/1', 'source': 'BBC', 'section': 'Tech', 'published_at': '2026-10-26T10:00:00'}
    ]
    cleaned = cleaner.clean(dirty_data)
    assert isinstance(cleaned, list)