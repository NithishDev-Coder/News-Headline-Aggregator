"""
run_refresh.py
Headline Aggregator Refresh Pipeline

This script collects news headlines from BBC News and The Guardian,
cleans them, checks them with a monitor (if available), and saves them to the database.
"""

import logging
import os
from datetime import datetime, timezone

# Import scraper modules
import scraper_bbc
import scraper_guardian

# Import cleaning function
from cleaner import clean

# Import database functions
from database import save_headlines, get_all_headlines

# Step 5: Try to import check_run from monitor.py (made by a teammate).
# If monitor.py is not in the folder yet, catch the ImportError and skip the check.
try:
    from monitor import check_run
except ImportError:
    check_run = None

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging to write detailed messages to logs/refresh.log
logging.basicConfig(
    filename="logs/refresh.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


def get_previous_count(source_name):
    """
    Find how many active headlines currently exist in the database for a source.
    If the count is unknown (or the database is empty/unavailable), return 0.
    """
    try:
        all_headlines = get_all_headlines()
        return sum(
            1 for h in all_headlines
            if h.get("source") == source_name and h.get("status") != "removed"
        )
    except Exception:
        # Return 0 when the previous count cannot be determined
        return 0


def run_once():
    """
    Execute a single run of the headline collection pipeline.

    Order:
      1. For each source (BBC News and The Guardian):
         a. Collect the headline list from the scraper.
         b. Clean the list with clean() from cleaner.py.
         c. Call check_run(source_name, cleaned_list, previous_count) from monitor.py.
            (Skip check if monitor.py is not available; use previous_count = 0 if unknown).
         d. If check_run says ok is False, do NOT save this source's headlines,
            add warnings to the warnings list, and continue to the next source.
      2. Save all approved headlines using save_headlines() from database.py.
      3. Print and append the run summary line to refresh_log.txt.

    Returns:
      dict: {'parsed': int, 'failed': int, 'saved': int, 'warnings': list}
    """
    # Track counts and warnings across all sources
    parsed_count = 0
    failed_count = 0
    saved_count = 0
    warnings = []

    # Lists to hold headlines and source names that pass the monitor check
    headlines_to_save = []
    sources_to_save = []

    # Define the news sources to scrape: (source_name, scraper_function)
    sources = [
        ("BBC News", scraper_bbc.get_headlines),
        ("The Guardian", scraper_guardian.get_headlines),
    ]

    # Process each source one by one
    for source_name, scraper_func in sources:
        # Step 6: If one scraper crashes, catch the error, log it, and continue.
        # Never crash the whole run.
        try:
            raw_headlines = scraper_func()
            if not isinstance(raw_headlines, list):
                logging.error("%s scraper returned invalid data type: %s", source_name, type(raw_headlines))
                failed_count += 1
                warnings.append(f"{source_name} scraper returned invalid data type")
                continue
        except Exception as err:
            logging.exception("%s scraper failed: %s", source_name, err)
            failed_count += 1
            warnings.append(f"{source_name} scraper error: {err}")
            continue

        # Add the number of raw headlines parsed
        parsed_count += len(raw_headlines)

        # Step 2: Clean the headlines using cleaner.py
        try:
            cleaned_list = clean(raw_headlines)
        except Exception as err:
            logging.exception("Cleaning failed for %s: %s", source_name, err)
            failed_count += 1
            warnings.append(f"{source_name} cleaner error: {err}")
            continue

        # Step 2 & 5: Call check_run from monitor.py if available
        check_ok = True
        source_warnings = []

        if check_run is not None:
            # Step 2: Use previous_count = 0 when the previous count is unknown
            previous_count = get_previous_count(source_name)

            try:
                check_result = check_run(source_name, cleaned_list, previous_count)

                # Beginner-friendly handling: check_result may be a dict, object, tuple, or bool
                if isinstance(check_result, dict):
                    check_ok = check_result.get("ok", True)
                    w = check_result.get("warnings", [])
                    if isinstance(w, list):
                        source_warnings.extend(w)
                    elif w:
                        source_warnings.append(str(w))
                elif hasattr(check_result, "ok"):
                    check_ok = bool(getattr(check_result, "ok"))
                    w = getattr(check_result, "warnings", [])
                    if isinstance(w, list):
                        source_warnings.extend(w)
                    elif w:
                        source_warnings.append(str(w))
                elif isinstance(check_result, (tuple, list)):
                    check_ok = bool(check_result[0])
                    if len(check_result) > 1:
                        w = check_result[1]
                        if isinstance(w, list):
                            source_warnings.extend(w)
                        elif w:
                            source_warnings.append(str(w))
                elif isinstance(check_result, bool):
                    check_ok = check_result
                    if not check_ok:
                        source_warnings.append(f"Monitor check failed for {source_name}")

            except Exception as err:
                logging.exception("Monitor check failed for %s: %s", source_name, err)
                source_warnings.append(f"Monitor check error for {source_name}: {err}")

        # Step 3: If check_run says ok is False, do NOT save that source's headlines.
        # Add its warnings to the warnings list and continue with the other source.
        if not check_ok:
            logging.warning("Monitor check reported ok=False for %s", source_name)
            if not source_warnings:
                source_warnings.append(f"Monitor check reported ok=False for {source_name}")
            warnings.extend(source_warnings)
            continue

        # If check passed, record any warnings and keep the headlines for saving
        if source_warnings:
            warnings.extend(source_warnings)

        if cleaned_list:
            headlines_to_save.extend(cleaned_list)
            sources_to_save.append(source_name)

    # Step 4: Pass the headlines that passed the check to save_headlines() from database.py.
    if headlines_to_save:
        try:
            # We supply sources so the database only manages removed status for active sources
            result = save_headlines(headlines_to_save, sources=sources_to_save)
            if isinstance(result, dict):
                saved_count = (
                    result.get("new", 0)
                    + result.get("updated", 0)
                    + result.get("unchanged", 0)
                )
            elif isinstance(result, int) and not isinstance(result, bool):
                saved_count = result
            else:
                saved_count = len(headlines_to_save)
        except TypeError:
            # Fallback if save_headlines is a mock that only accepts headlines
            try:
                result = save_headlines(headlines_to_save)
                if isinstance(result, dict):
                    saved_count = (
                        result.get("new", 0)
                        + result.get("updated", 0)
                        + result.get("unchanged", 0)
                    )
                elif isinstance(result, int) and not isinstance(result, bool):
                    saved_count = result
                else:
                    saved_count = len(headlines_to_save)
            except Exception as err:
                logging.exception("Database save failed: %s", err)
                failed_count += 1
                warnings.append(f"Database save error: {err}")
        except Exception as err:
            logging.exception("Database save failed: %s", err)
            failed_count += 1
            warnings.append(f"Database save error: {err}")

    # Build the required counts dictionary
    counts = {
        "parsed": parsed_count,
        "failed": failed_count,
        "saved": saved_count,
        "warnings": warnings,
    }

    # Step 7: Print and append to a log file refresh_log.txt one line per run with a timestamp and the counts.
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_line = (
        f"{timestamp} - parsed: {counts['parsed']}, failed: {counts['failed']}, "
        f"saved: {counts['saved']}, warnings: {counts['warnings']}"
    )

    print(log_line)

    try:
        with open("refresh_log.txt", "a", encoding="utf-8") as log_file:
            log_file.write(log_line + "\n")
    except Exception as err:
        logging.exception("Failed to write to refresh_log.txt: %s", err)

    return counts


def run_refresh():
    """Backward compatibility wrapper that calls run_once()."""
    return run_once()


if __name__ == "__main__":
    result = run_once()
    print("Run completed:", result)
