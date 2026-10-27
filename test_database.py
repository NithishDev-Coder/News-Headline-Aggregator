import sqlite3

import database
import pytest


def make_headline(headline_id, title, **values):
    """Build one headline dictionary with all seven expected input fields."""
    headline = {
        "headline_id": headline_id,
        "title": title,
        "source": "Example News",
        "section": "World",
        "published_at": "2026-10-27T09:00:00",
        "url": "https://example.com/" + str(headline_id),
        "seen_at": "2026-10-27T09:01:00",
    }
    headline.update(values)
    return headline


def test_init_db_creates_tables(tmp_path):
    """Check that initialization creates the required database tables."""
    db_path = tmp_path / "test.db"
    database.init_db(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"headlines", "runs", "run_changes"} <= tables


def test_first_save_marks_all_headlines_new(tmp_path):
    """Check that a first save inserts every valid headline as new."""
    db_path = tmp_path / "test.db"

    result = database.save_headlines(
        [make_headline("one", "First"), make_headline("two", "Second")],
        db_path,
    )

    assert result["new"] == 2
    assert result["updated"] == 0
    assert result["unchanged"] == 0
    assert result["failed"] == 0
    assert len(database.get_all_headlines(db_path)) == 2


def test_saving_same_headlines_twice_does_not_duplicate(tmp_path):
    """Check that a repeated refresh marks headlines unchanged without duplicates."""
    db_path = tmp_path / "test.db"
    headlines = [make_headline("one", "First"), make_headline("two", "Second")]
    database.save_headlines(headlines, db_path)

    result = database.save_headlines(headlines, db_path)

    assert result["unchanged"] == 2
    assert result["new"] == 0
    assert len(database.get_all_headlines(db_path)) == 2


def test_changed_title_is_updated_and_first_seen_is_preserved(tmp_path):
    """Check that a changed title updates the row but keeps its original first-seen time."""
    db_path = tmp_path / "test.db"
    database.save_headlines([make_headline("one", "Old title")], db_path)
    original = database.get_all_headlines(db_path)[0]["first_seen"]

    result = database.save_headlines([make_headline("one", "New title")], db_path)
    saved = database.get_all_headlines(db_path)[0]

    assert result["updated"] == 1
    assert saved["title"] == "New title"
    assert saved["first_seen"] == original
    assert saved["status"] == "updated"


def test_missing_headline_is_removed_not_deleted(tmp_path):
    """Check that absent headlines are marked removed and remain in the database."""
    db_path = tmp_path / "test.db"
    database.save_headlines(
        [make_headline("one", "First"), make_headline("two", "Second")], db_path
    )

    result = database.save_headlines([make_headline("one", "First")], db_path)
    saved = {row["headline_id"]: row for row in database.get_all_headlines(db_path)}

    assert result["removed"] == 1
    assert "two" in saved
    assert saved["two"]["status"] == "removed"


def test_invalid_headlines_are_skipped_and_counted(tmp_path):
    """Check that missing IDs or titles fail while valid records are still saved."""
    db_path = tmp_path / "test.db"
    headlines = [
        make_headline(None, "No ID"),
        make_headline("no-title", None),
        make_headline("valid", "Valid headline"),
    ]

    result = database.save_headlines(headlines, db_path)

    assert result["failed"] == 2
    assert result["new"] == 1
    assert [row["headline_id"] for row in database.get_all_headlines(db_path)] == [
        "valid"
    ]


def test_empty_list_does_not_mark_headlines_removed(tmp_path):
    """Check that an empty refresh is recorded as unsuccessful without changing headlines."""
    db_path = tmp_path / "test.db"
    database.save_headlines([make_headline("one", "First")], db_path)

    result = database.save_headlines([], db_path)
    saved = database.get_all_headlines(db_path)

    assert result["removed"] == 0
    assert saved[0]["status"] == "new"
    assert database.get_run_history(limit=1, db_path=db_path)[0]["success"] == 0


def test_last_successful_run_is_none_then_has_a_timestamp(tmp_path):
    """Check that only a successful run supplies the latest successful finish time."""
    db_path = tmp_path / "test.db"

    assert database.last_successful_run(db_path) is None

    database.save_headlines([make_headline("one", "First")], db_path)
    finished_at = database.last_successful_run(db_path)

    assert isinstance(finished_at, str)
    assert "T" in finished_at


def test_none_optional_values_do_not_crash(tmp_path):
    """Check that optional section and publication time may be None."""
    db_path = tmp_path / "test.db"
    headline = make_headline("one", "First", section=None, published_at=None)

    result = database.save_headlines([headline], db_path)
    saved = database.get_all_headlines(db_path)[0]

    assert result["new"] == 1
    assert saved["section"] is None
    assert saved["published_at"] is None


def test_sources_limit_which_headlines_can_be_removed(tmp_path):
    """Check that a source-limited refresh removes only headlines from that source."""
    db_path = tmp_path / "test.db"
    local = make_headline("local", "Local headline", source="Local News")
    global_news = make_headline("global", "Global headline", source="Global News")
    database.save_headlines([local, global_news], db_path)

    result = database.save_headlines(
        [global_news], db_path, sources=["Local News"]
    )
    saved = {row["headline_id"]: row for row in database.get_all_headlines(db_path)}

    assert result["removed"] == 1
    assert saved["local"]["status"] == "removed"
    assert saved["global"]["status"] == "unchanged"


def test_latest_changes_and_run_history_are_for_latest_run(tmp_path):
    """Check that change reporting and run history refer to the latest refresh."""
    db_path = tmp_path / "test.db"
    database.save_headlines([make_headline("one", "First")], db_path)

    changes = database.get_latest_changes(db_path)
    assert [(row["headline_id"], row["status"]) for row in changes] == [
        ("one", "new")
    ]

    database.save_headlines([make_headline("one", "First")], db_path)

    assert database.get_latest_changes(db_path) == []
    history = database.get_run_history(limit=2, db_path=db_path)
    assert len(history) == 2
    assert history[0]["run_id"] > history[1]["run_id"]


def test_save_rolls_back_the_whole_run_on_database_error(tmp_path):
    """Check that a database error rolls back both headlines and run records."""
    db_path = tmp_path / "test.db"
    invalid_value = make_headline("one", "First", section=["not", "supported"])

    with pytest.raises(sqlite3.ProgrammingError):
        database.save_headlines([invalid_value], db_path)

    assert database.get_all_headlines(db_path) == []
    assert database.get_run_history(db_path=db_path) == []
