import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


# Create logs folder and save cleaner messages
import os

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/cleaner.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# Exact shared headline format
HEADLINE_KEYS = [
    "headline_id",
    "title",
    "source",
    "section",
    "published_at",
    "url",
    "seen_at",
]


def current_time():
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value):
    """Remove extra spaces from text."""
    if value is None:
        return None

    text = " ".join(str(value).split())
    return text if text else None


def normalize_url(url):
    """Remove URL fragments without changing the article path."""
    url = clean_text(url)

    if not url:
        return None

    try:
        parts = urlsplit(url)

        if parts.scheme not in ("http", "https") or not parts.netloc:
            return None

        # Fragments such as #comments are not part of the article URL.
        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            parts.query,
            ""
        ))
    except (ValueError, TypeError):
        return None


def make_headline_id(url):
    """Create a stable ID from the normalized article URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def normalize_date(value):
    """Convert a valid date into ISO format; missing or invalid dates become None."""
    if value is None:
        return None

    value = clean_text(value)

    if not value:
        return None

    try:
        # Supports ISO timestamps, including timestamps ending in Z.
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.isoformat(timespec="seconds")
    except (ValueError, TypeError):
        logging.warning("Invalid published_at date: %r", value)
        return None


def clean_with_stats(headlines):
    """
    Clean headline dictionaries.

    Returns:
        (cleaned_headlines, failed_count)
    """
    cleaned = []
    seen_urls = set()
    failed_count = 0

    for item in headlines:
        if not isinstance(item, dict):
            logging.warning("Skipped invalid record: not a dictionary")
            failed_count += 1
            continue

        title = clean_text(item.get("title"))
        url = normalize_url(item.get("url"))

        # A title and a valid article URL are required.
        if not title or not url:
            logging.warning(
                "Skipped broken record: title=%r, url=%r",
                item.get("title"),
                item.get("url")
            )
            failed_count += 1
            continue

        # Remove duplicate articles by URL.
        if url in seen_urls:
            logging.info("Duplicate headline skipped: %s", url)
            continue

        seen_urls.add(url)

        # Preserve missing values as None. Do not invent data.
        headline = {
            "headline_id": make_headline_id(url),
            "title": title,
            "source": clean_text(item.get("source")),
            "section": clean_text(item.get("section")),
            "published_at": normalize_date(item.get("published_at")),
            "url": url,
            "seen_at": current_time(),
        }

        # Ensure every record follows the exact shared format.
        headline = {key: headline[key] for key in HEADLINE_KEYS}
        cleaned.append(headline)

    logging.info(
        "Cleaner finished: input=%d, cleaned=%d, failed=%d",
        len(headlines), len(cleaned), failed_count
    )

    return cleaned, failed_count


def clean(headlines):
    """Main function used by the project runner."""
    cleaned, _ = clean_with_stats(headlines)
    return cleaned


if __name__ == "__main__":
    sample = [
        {
            "title": "  Sample News   Headline ",
            "source": "BBC News",
            "section": "World",
            "published_at": "2026-10-26T10:31:00Z",
            "url": "https://example.com/news/1",
        },
        {
            "title": "Broken record",
            "source": "BBC News",
            "url": None,
        },
    ]

    result = clean(sample)

    for headline in result:
        print(headline)

