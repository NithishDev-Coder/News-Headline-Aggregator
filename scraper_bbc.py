
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BBC_HOME = "https://www.bbc.com/news"
BBC_SOURCE = "BBC News"
REQUEST_TIMEOUT = 10
REQUEST_DELAY = 5

HEADERS = {
    "User-Agent": "NewsHeadlineAggregator/1.0 (educational project)"
}

logging.basicConfig(level=logging.INFO)


def parse_headlines(html, seen_at=None):
    """Parse BBC article links from HTML."""
    headlines = []
    seen_urls = set()

    if seen_at is None:
        seen_at = datetime.now(timezone.utc).isoformat()

    soup = BeautifulSoup(html, "html.parser")

    for link in soup.select("a[href]"):
        title = link.get_text(" ", strip=True)
        href = link.get("href", "").strip()

        if not title or not href:
            continue

        url = urljoin(BBC_HOME, href)
        parsed = urlparse(url)

        if parsed.netloc not in ("bbc.com", "www.bbc.com"):
            continue

        if not parsed.path.startswith("/news/articles/"):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)
        headline_id = parsed.path.rstrip("/").split("/")[-1]

        headlines.append({
            "headline_id": headline_id or None,
            "title": title,
            "source": BBC_SOURCE,
            "section": None,
            "published_at": None,
            "url": url,
            "seen_at": seen_at,
        })

    return headlines


def get_headlines():
    """Collect BBC headlines as a list of dictionaries."""
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        robots_url = "https://www.bbc.com/robots.txt"
        robots_response = session.get(
            robots_url, timeout=REQUEST_TIMEOUT
        )
        robots_response.raise_for_status()

        robots = RobotFileParser()
        robots.set_url(robots_url)
        robots.parse(robots_response.text.splitlines())

        if not robots.can_fetch(HEADERS["User-Agent"], BBC_HOME):
            logging.warning("BBC robots.txt does not allow this page.")
            return []

        time.sleep(REQUEST_DELAY)

        response = session.get(
            BBC_HOME, timeout=REQUEST_TIMEOUT
        )

        if response.status_code in (403, 429):
            logging.warning(
                "BBC returned HTTP %s. Stopping scraper.",
                response.status_code,
            )
            return []

        response.raise_for_status()

        return parse_headlines(response.text)

    except requests.RequestException:
        logging.exception("BBC request failed")
        return []
    except Exception:
        logging.exception("BBC scraper failed")
        return []
    finally:
        session.close()
