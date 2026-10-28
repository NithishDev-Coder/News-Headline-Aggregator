# Data Dictionary: News Headlines Aggregator

## Headlines Table Fields
| Field | Type | Meaning | Example |
| :--- | :--- | :--- | :--- |
| `headline_id` | TEXT (Primary Key) | Unique identifier for headline | `abc123` |
| `title` | TEXT | Headline title | `Sample title` |
| `source` | TEXT | Source publisher name | `BBC News` |
| `section` | TEXT | News category | `World` |
| `published_at` | TEXT (ISO 8601) | Published timestamp | `2026-10-26T10:31:00` |
| `url` | TEXT | Link to article | `https://...` |
| `seen_at` | TEXT (ISO 8601) | Scraped timestamp | `2026-10-26T10:42:00` |
| `first_seen` | TEXT (ISO 8601) | First saved timestamp | `2026-10-26T10:42:00` |
| `last_seen` | TEXT (ISO 8601) | Last updated timestamp | `2026-10-26T10:42:00` |
| `status` | TEXT | State: new, updated, removed, unchanged | `new` |

## Runs Table Fields
| Field | Type | Meaning | Example |
| :--- | :--- | :--- | :--- |
| `run_id` | INTEGER | Auto run ID | `1` |
| `started_at` | TEXT | Run start time | `2026-10-26T10:42:00` |
| `finished_at` | TEXT | Run finish time | `2026-10-26T10:42:00` |
| `success` | INTEGER | 1 for success, 0 for fail | `1` |
| `saved_count` | INTEGER | Total saved | `15` |
| `failed_count` | INTEGER | Total failed | `0` |

## Status Values
- **`new`**: First time seen.
- **`updated`**: Title changed.
- **`removed`**: Not in current run.
- **`unchanged`**: No changes.