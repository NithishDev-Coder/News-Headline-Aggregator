
from pathlib import Path
from scraper_bbc import parse_headlines

def test_bbc_sample_html():
    html = Path("bbc_sample.html").read_text(encoding="utf-8")
    headlines = parse_headlines(html)

    assert len(headlines) == 2
    assert all(item["source"] == "BBC News" for item in headlines)
    assert all("/news/articles/" in item["url"] for item in headlines)

    print("BBC parser test passed!")
    print("Headlines found:", len(headlines))
    for item in headlines:
        print(item["title"])
