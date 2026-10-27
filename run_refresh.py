
# run_refresh.py
# Run the complete headline collection pipeline

import logging
import os
from datetime import datetime, timezone

from cleaner import clean_with_stats
from scraper_bbc import get_headlines as get_bbc_headlines
from scraper_guardian import get_headlines as get_guardian_headlines
from database import save_headlines


# Create a folder for refresh logs
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/refresh.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


def current_time():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def collect_from_scraper(name, scraper):
    """Run one scraper without stopping the other scraper if it fails."""
    try:
        result = scraper()

        if not isinstance(result, list):
            logging.error("%s scraper returned an invalid result", name)
            return [], 1

        # Count records that are not dictionaries as failed.
        invalid_count = sum(
            1 for item in result if not isinstance(item, dict)
        )

        valid_records = [
            item for item in result if isinstance(item, dict)
        ]

        logging.info(
            "%s scraper: received=%d, invalid=%d",
            name, len(result), invalid_count
        )

        return valid_records, invalid_count

    except Exception:
        logging.exception("%s scraper failed", name)
        return [], 1


def run_refresh():
    started_at = current_time()

    print("=" * 45)
    print("NEWS HEADLINES AGGREGATOR")
    print("Refresh started:", started_at)
    print("=" * 45)

    # Step 1: Collect from both sources.
    bbc_headlines, bbc_failed = collect_from_scraper(
        "BBC News", get_bbc_headlines
    )

    guardian_headlines, guardian_failed = collect_from_scraper(
        "The Guardian", get_guardian_headlines
    )

    all_headlines = bbc_headlines + guardian_headlines
    parsed_count = len(all_headlines)

    # Step 2: Clean and validate.
    cleaned_headlines, cleaner_failed = clean_with_stats(all_headlines)

    failed_count = bbc_failed + guardian_failed + cleaner_failed

    # Step 3: Save to the database.
    saved_count = 0
    success = False

    try:
        if not cleaned_headlines:
            # Do not mark an empty collection as successful.
            # This prevents accidental marking of every headline removed.
            raise RuntimeError(
                "No valid headlines collected; database was not updated."
            )

        result = save_headlines(cleaned_headlines)

        # Recommended database contract:
        # save_headlines() returns the number of records it saved.
        # If it returns None, use the number submitted as a fallback.
        if result is None:
            saved_count = len(cleaned_headlines)
        elif isinstance(result, int) and not isinstance(result, bool):
            saved_count = result
        else:
            raise TypeError(
                "save_headlines() must return an integer or None"
            )

        success = True

    except Exception:
        logging.exception("Database save failed")
        failed_count += 1
        print("ERROR: Database save failed. Check logs/refresh.log")

    finished_at = current_time()

    # Step 4: Print and log the report.
    report = (
        f"Started: {started_at}\n"
        f"Finished: {finished_at}\n"
        f"Parsed: {parsed_count}\n"
        f"Cleaned: {len(cleaned_headlines)}\n"
        f"Failed: {failed_count}\n"
        f"Saved: {saved_count}\n"
        f"Success: {success}"
    )

    logging.info("Refresh report:\n%s", report)

    print("\nREFRESH REPORT")
    print("-" * 30)
    print("Parsed headlines :", parsed_count)
    print("Cleaned headlines:", len(cleaned_headlines))
    print("Failed items     :", failed_count)
    print("Saved count      :", saved_count)
    print("Success          :", success)
    print("Finished at      :", finished_at)
    print("\nFull log: logs/refresh.log")

    return {
        "started_at": started_at,
        "finished_at": finished_at,
        "parsed_count": parsed_count,
        "cleaned_count": len(cleaned_headlines),
        "failed_count": failed_count,
        "saved_count": saved_count,
        "success": success,
    }


if __name__ == "__main__":
    run_refresh()

