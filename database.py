import logging
import os
import sqlite3
from datetime import datetime


DB_PATH = "headlines.db"
logger = logging.getLogger(__name__)


def _connect(db_path):
    """Open a database connection that returns rows by column name."""
    connection = sqlite3.connect(os.fspath(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path=DB_PATH):
    """Create the headline, run, and run-change tables if they do not exist."""
    connection = _connect(db_path)
    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS headlines (
                    headline_id TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    section TEXT,
                    published_at TEXT,
                    url TEXT,
                    seen_at TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    status TEXT CHECK (
                        status IN ('new', 'updated', 'removed', 'unchanged')
                    )
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT,
                    finished_at TEXT,
                    success INTEGER CHECK (success IN (0, 1)),
                    saved_count INTEGER,
                    failed_count INTEGER
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS run_changes (
                    run_id INTEGER NOT NULL,
                    headline_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (run_id, headline_id)
                )
                """
            )
    except sqlite3.Error:
        logger.exception("Could not initialize the headline database")
        raise
    finally:
        connection.close()


def save_headlines(list_of_dicts, db_path=DB_PATH, sources=None):
    """Save a refresh as one transaction and return its change counts."""
    init_db(db_path)
    source_filter = None if sources is None else set(sources)
    started_at = datetime.now().isoformat(timespec="seconds")
    counts = {
        "new": 0,
        "updated": 0,
        "removed": 0,
        "unchanged": 0,
        "failed": 0,
    }

    valid_headlines = {}
    for record in list_of_dicts:
        if not isinstance(record, dict):
            logger.warning("Skipping a headline that is not a dictionary")
            counts["failed"] += 1
            continue

        headline_id = record.get("headline_id")
        title = record.get("title")
        if not headline_id or not title:
            logger.warning("Skipping a headline missing headline_id or title")
            counts["failed"] += 1
            continue

        valid_headlines[headline_id] = {
            "headline_id": headline_id,
            "title": title,
            "source": record.get("source"),
            "section": record.get("section"),
            "published_at": record.get("published_at"),
            "url": record.get("url"),
            "seen_at": record.get("seen_at"),
        }

    connection = _connect(db_path)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO runs (
                    started_at, finished_at, success, saved_count, failed_count
                ) VALUES (?, NULL, 0, 0, 0)
                """,
                (started_at,),
            )
            run_id = cursor.lastrowid

            for headline in valid_headlines.values():
                existing = connection.execute(
                    "SELECT title FROM headlines WHERE headline_id = ?",
                    (headline["headline_id"],),
                ).fetchone()
                now = datetime.now().isoformat(timespec="seconds")

                if existing is None:
                    status = "new"
                    connection.execute(
                        """
                        INSERT INTO headlines (
                            headline_id, title, source, section, published_at,
                            url, seen_at, first_seen, last_seen, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            headline["headline_id"],
                            headline["title"],
                            headline["source"],
                            headline["section"],
                            headline["published_at"],
                            headline["url"],
                            headline["seen_at"],
                            now,
                            now,
                            status,
                        ),
                    )
                elif existing["title"] != headline["title"]:
                    status = "updated"
                    connection.execute(
                        """
                        UPDATE headlines
                        SET title = ?, source = ?, section = ?, published_at = ?,
                            url = ?, seen_at = ?, last_seen = ?, status = ?
                        WHERE headline_id = ?
                        """,
                        (
                            headline["title"],
                            headline["source"],
                            headline["section"],
                            headline["published_at"],
                            headline["url"],
                            headline["seen_at"],
                            now,
                            status,
                            headline["headline_id"],
                        ),
                    )
                else:
                    status = "unchanged"
                    connection.execute(
                        """
                        UPDATE headlines
                        SET last_seen = ?, status = ?
                        WHERE headline_id = ?
                        """,
                        (now, status, headline["headline_id"]),
                    )

                counts[status] += 1
                if status != "unchanged":
                    connection.execute(
                        """
                        INSERT INTO run_changes (run_id, headline_id, status)
                        VALUES (?, ?, ?)
                        """,
                        (run_id, headline["headline_id"], status),
                    )

            if valid_headlines:
                present_ids = set(valid_headlines)
                candidates = connection.execute(
                    """
                    SELECT headline_id, source
                    FROM headlines
                    WHERE status != 'removed'
                    """
                ).fetchall()
                for candidate in candidates:
                    if candidate["headline_id"] in present_ids:
                        continue
                    if (
                        source_filter is not None
                        and candidate["source"] not in source_filter
                    ):
                        continue
                    connection.execute(
                        "UPDATE headlines SET status = 'removed' WHERE headline_id = ?",
                        (candidate["headline_id"],),
                    )
                    counts["removed"] += 1
                    connection.execute(
                        """
                        INSERT INTO run_changes (run_id, headline_id, status)
                        VALUES (?, ?, 'removed')
                        """,
                        (run_id, candidate["headline_id"]),
                    )

            finished_at = datetime.now().isoformat(timespec="seconds")
            connection.execute(
                """
                UPDATE runs
                SET finished_at = ?, success = ?, saved_count = ?, failed_count = ?
                WHERE run_id = ?
                """,
                (
                    finished_at,
                    int(bool(valid_headlines)),
                    len(valid_headlines),
                    counts["failed"],
                    run_id,
                ),
            )
    except sqlite3.Error:
        logger.exception("Could not save headline refresh")
        raise
    finally:
        connection.close()

    counts["run_id"] = run_id
    return counts


def last_successful_run(db_path=DB_PATH):
    """Return the finish time of the latest successful run, or None."""
    init_db(db_path)
    connection = _connect(db_path)
    try:
        row = connection.execute(
            """
            SELECT finished_at
            FROM runs
            WHERE success = 1
            ORDER BY run_id DESC
            LIMIT 1
            """
        ).fetchone()
        return None if row is None else row["finished_at"]
    except sqlite3.Error:
        logger.exception("Could not read the latest successful run")
        raise
    finally:
        connection.close()


def get_all_headlines(db_path=DB_PATH):
    """Return all headlines with the newest published or first-seen items first."""
    init_db(db_path)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM headlines
            ORDER BY COALESCE(published_at, first_seen) DESC, first_seen DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Could not read saved headlines")
        raise
    finally:
        connection.close()


def get_latest_changes(db_path=DB_PATH):
    """Return new, updated, or removed headlines from the most recent run."""
    init_db(db_path)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT h.headline_id, h.title, h.source, h.section, h.published_at,
                   h.url, h.seen_at, h.first_seen, h.last_seen, c.status
            FROM run_changes AS c
            JOIN headlines AS h ON h.headline_id = c.headline_id
            WHERE c.run_id = (SELECT MAX(run_id) FROM runs)
            ORDER BY h.headline_id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Could not read changes from the latest run")
        raise
    finally:
        connection.close()


def get_run_history(limit=10, db_path=DB_PATH):
    """Return recent run records, newest first, up to the requested limit."""
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    init_db(db_path)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT run_id, started_at, finished_at, success, saved_count, failed_count
            FROM runs
            ORDER BY run_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Could not read run history")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    example_headlines = [
        {
            "headline_id": "example-1",
            "title": "Example headline one",
            "source": "Example News",
            "section": "World",
            "published_at": None,
            "url": "https://example.com/one",
            "seen_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "headline_id": "example-2",
            "title": "Example headline two",
            "source": "Example News",
            "section": "Technology",
            "published_at": None,
            "url": "https://example.com/two",
            "seen_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "headline_id": "example-3",
            "title": "Example headline three",
            "source": "Example News",
            "section": "Business",
            "published_at": None,
            "url": "https://example.com/three",
            "seen_at": datetime.now().isoformat(timespec="seconds"),
        },
    ]
    print(save_headlines(example_headlines))
