import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import hashlib
import logging
import time

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Guardian international homepage
URL = "https://www.theguardian.com/international"

HEADERS = {
    "User-Agent": "NewsHeadlineAggregator/1.0 (educational project)"
}

REQUEST_TIMEOUT = 10
REQUEST_DELAY = 5

# Required output keys
REQUIRED_KEYS = [
    "headline_id",
    "title",
    "source",
    "section",
    "published_at",
    "url",
    "seen_at"
]


def get_headlines():
    """Collect headlines from The Guardian homepage."""

    headlines = []
    seen_urls = set()

    try:
        logging.info("Connecting to The Guardian...")

        # Send one request to the website
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        # Stop if the website denies or limits access
        if response.status_code in (403, 429):
            logging.warning(
                "Guardian returned HTTP %s. Stopping scraper.",
                response.status_code
            )
            return []

        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        seen_at = datetime.now(timezone.utc).isoformat()

        # Prefer article-related links where available.
        # Fall back to all links if these selectors find none.
        items = soup.select(
            "a[data-link-name='article'], "
            "a[data-testid='headline']"
        )

        if not items:
            logging.warning(
                "Article-specific selectors found no links. "
                "Trying general links."
            )
            items = soup.select("a[href]")

        for item in items:
            title = item.get_text(" ", strip=True)
            raw_url = item.get("href")

            # Ignore empty titles or links
            if not title or not raw_url:
                continue

            # Convert relative URL to absolute URL
            article_url = urljoin(URL, raw_url)
            parsed_url = urlparse(article_url)

            # Allow only Guardian article website links
            if parsed_url.hostname != "www.theguardian.com":
                continue

            # Ignore homepage and empty paths
            path = parsed_url.path

            if not path or path == "/":
                continue

            # Ignore navigation and preference pages
            excluded_paths = (
                "/preference/",
                "/help/",
                "/about/",
                "/info/",
                "/tone/",
                "/contact-us",
                "/signin",
                "/subscribe"
            )

            if path.startswith(excluded_paths):
                continue

            # Ignore very short text
            if len(title) < 20:
                continue

            # Remove URL fragments
            article_url = article_url.split("#")[0]

            # Remove duplicate URLs
            if article_url in seen_urls:
                continue

            seen_urls.add(article_url)

            # Create a stable ID from the URL
            headline_id = hashlib.sha256(
                article_url.encode("utf-8")
            ).hexdigest()[:12]

            # Get section from the URL path when possible
            path_parts = [
                part for part in path.strip("/").split("/")
                if part
            ]

            section = path_parts[0] if path_parts else None

            # Do not guess publication time.
            # The homepage may not provide it for every headline.
            published_at = None

            # Add headline using the team's required format
            headline = {
                "headline_id": headline_id,
                "title": title,
                "source": "The Guardian",
                "section": section,
                "published_at": published_at,
                "url": article_url,
                "seen_at": seen_at
            }

            headlines.append(headline)

        logging.info(
            "Guardian headlines collected: %s",
            len(headlines)
        )

        return headlines

    except requests.RequestException as error:
        logging.error("Guardian request failed: %s", error)
        return []

    except Exception:
        logging.exception(
            "Unexpected error while collecting headlines"
        )
        return []


def main():
    """Run the scraper and display sample results."""

    print("\nGuardian News Scraper")
    print("=" * 35)

    headlines = get_headlines()

    print("\nTotal headlines:", len(headlines))

    if not headlines:
        print(
            "\nNo headlines collected. Check the error message, "
            "network connection, robots.txt, and website terms."
        )
        return

    # Display the first five results
    for number, headline in enumerate(headlines[:5], start=1):
        print(f"\nHeadline {number}")
        print("-" * 30)

        for key in REQUIRED_KEYS:
            print(f"{key}: {headline.get(key)}")


if __name__ == "__main__":
    main()