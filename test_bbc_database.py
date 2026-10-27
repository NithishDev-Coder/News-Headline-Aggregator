
from pathlib import Path

from scraper_bbc import parse_headlines
from cleaner import clean
from database import save_headlines, get_all_headlines


def test_bbc_headlines_save_to_database(tmp_path):
    html = Path("bbc_sample.html").read_text(encoding="utf-8")
    raw_headlines = parse_headlines(html)
    cleaned_headlines = clean(raw_headlines)

    db_path = tmp_path / "test_headlines.db"

    result = save_headlines(
        cleaned_headlines,
        db_path=str(db_path),
        sources=["BBC News"],
    )

    saved = get_all_headlines(db_path=str(db_path))

    assert len(saved) == 2
    assert result["new"] == 2
    assert all(item["source"] == "BBC News" for item in saved)

    print("BBC + Cleaner + Database test passed!")
    print("Saved headlines:", len(saved))
