
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

BASE_DIR = __import__("pathlib").Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "news.db"
REFRESH_SECONDS = 300
MAX_AGE_HOURS = 24

RSS_FEEDS = {
    "Google News - India": (
        "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "National",
    ),
    "Google News - Technology": (
        "https://news.google.com/rss/search?q=technology"
        "&hl=en-IN&gl=IN&ceid=IN:en",
        "Technology",
    ),
    "Google News - World": (
        "https://news.google.com/rss/headlines/section/topic/WORLD"
        "?hl=en-IN&gl=IN&ceid=IN:en",
        "World",
    ),
}

HEADERS = {
    "User-Agent": "PulseNewsIntelligence/1.0 (educational project)"
}


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS headlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                section TEXT,
                published_at TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'New',
                last_seen TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)


def parse_published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")

    if parsed:
        from time import struct_time, mktime
        import calendar
        return datetime.fromtimestamp(
            calendar.timegm(parsed), tz=timezone.utc
        )

    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass

    return None


def fetch_feed(feed_name, feed_url, section):
    response = requests.get(
        feed_url, headers=HEADERS, timeout=15
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    items = []

    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        published = parse_published(entry)

        if not title or not url or not published:
            continue

        if published < cutoff or published > now + timedelta(minutes=5):
            continue

        items.append({
            "title": title,
            "source": feed_name,
            "section": section,
            "published_at": published.isoformat(),
            "url": url,
            "status": "New",
            "last_seen": now.isoformat(),
        })

    return items


def refresh_news(force=False):
    init_db()
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = 'last_refresh'"
        ).fetchone()

        if row and not force:
            try:
                last_refresh = datetime.fromisoformat(row["value"])
                if (now - last_refresh).total_seconds() < REFRESH_SECONDS:
                    return {"updated": 0, "errors": []}
            except ValueError:
                pass

    fetched = []
    errors = []

    for name, (url, section) in RSS_FEEDS.items():
        try:
            fetched.extend(fetch_feed(name, url, section))
        except (requests.RequestException, ValueError, Exception) as exc:
            errors.append(f"{name}: {exc}")

    with get_connection() as conn:
        for item in fetched:
            conn.execute("""
                INSERT INTO headlines
                    (title, source, section, published_at, url, status, last_seen)
                VALUES
                    (:title, :source, :section, :published_at, :url, :status, :last_seen)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    source = excluded.source,
                    section = excluded.section,
                    published_at = excluded.published_at,
                    last_seen = excluded.last_seen
            """, item)

        conn.execute("""
            INSERT INTO app_meta (key, value)
            VALUES ('last_refresh', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (now.isoformat(),))

        # Remove old records to keep the database focused on recent news.
        cutoff = (now - timedelta(hours=MAX_AGE_HOURS)).isoformat()
        conn.execute(
            "DELETE FROM headlines WHERE published_at < ?", (cutoff,)
        )

    return {"updated": len(fetched), "errors": errors}


def get_recent_headlines():
    init_db()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    ).isoformat()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT title, source, section, published_at, url, status, last_seen
            FROM headlines
            WHERE published_at >= ?
            ORDER BY published_at DESC
        """, (cutoff,)).fetchall()

    return [dict(row) for row in rows]


def get_refresh_status():
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = 'last_refresh'"
        ).fetchone()

    return row["value"] if row else None


init_db()
