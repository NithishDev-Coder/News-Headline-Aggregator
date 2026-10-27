
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

from news_service import (
    refresh_news,
    get_recent_headlines,
    get_refresh_status,
)

app = Flask(__name__)
DB_PATH = Path(__file__).resolve().parent / "news.db"

PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pulse | News Intelligence</title>
    <link rel="stylesheet"
          href="{{ url_for('static', filename='style.css') }}">
    <meta http-equiv="refresh" content="300">
</head>
<body>
<div class="layout">

    <aside class="sidebar">
        <a class="brand" href="/">
            <span class="brand-icon">〰</span>
            <span><b>pulse<span class="cyan">.</span></b>
            <small>NEWS INTELLIGENCE</small></span>
        </a>

        <p class="side-label">WORKSPACE</p>
        <a class="nav active" href="/">◈ &nbsp; Overview</a>
        <a class="nav" href="#headlines">▤ &nbsp; Headlines</a>
        <a class="nav" href="#activity">⌁ &nbsp; Activity</a>
        <a class="nav" href="#sources">◎ &nbsp; Sources</a>

        <div class="sidebar-bottom">
            <div class="system-card">
                <span class="status-dot"></span> SYSTEM STATUS
                <h4>{{ "Waiting for live feed" if demo else "Live news connected" }}</h4>
                <p>{{ "No live headlines loaded yet. Check the feed connection."
                      if demo else "RSS headlines stored in local SQLite." }}</p>
            </div>
            <div class="profile">
                <div class="avatar">P</div>
                <div><b>Pulse Monitor</b>
                <small>News tracking workspace</small></div>
            </div>
        </div>
    </aside>

    <main class="main">
        <header class="topbar">
            <span>Workspace <span class="muted">/</span> Overview</span>
            <span class="mode">
                {{ "● WAITING FOR NEWS" if demo else "● LIVE NEWS MODE" }}
            </span>
        </header>

        <section class="hero">
            <div class="hero-copy">
                <div class="eyebrow">
                    <span class="status-dot"></span>
                    YOUR NEWS, IN MOTION
                </div>
                <h1>Every headline<br>has a <span class="cyan">pulse.</span></h1>
                <p>One clear view of the stories shaping the world.<br>
                   Track headlines, spot changes, stay ahead.</p>
                <a class="primary-button" href="#headlines">
                    Explore headlines <span>↘</span>
                </a>
            </div>

            <div class="ocean-art" aria-hidden="true">
                <div class="orbit orbit-outer"></div>
                <div class="orbit orbit-inner"></div>
                <div class="ocean-core">◈</div>
                <div class="wave wave-one"></div>
                <div class="wave wave-two"></div>
                <div class="wave wave-three"></div>
                <span class="floating-tag tag-one">● Signal detected</span>
                <span class="floating-tag tag-two">↗ Stories evolving</span>
            </div>

            <div class="hero-footer">
                <span>● RSS NEWS</span>
                <span>● LIVE HEADLINES</span>
                <span class="footer-right">SIGNAL OVER NOISE</span>
            </div>
        </section>

        {% if demo %}
        <div class="demo-banner">
            <b>ⓘ NO LIVE HEADLINES</b>
            <span>{{ demo_reason }} Check your internet connection and use Refresh News.</span>
        </div>
        {% endif %}

        {% if refresh_errors %}
        <div class="demo-banner">
            <b>FEED NOTICE</b>
            <span>{{ refresh_errors|join(" · ") }}</span>
        </div>
        {% endif %}

        <section class="section-title">
            <div>
                <span class="eyebrow">AT A GLANCE</span>
                <h2>Your news pulse</h2>
                <p>News published in the last 24 hours.</p>
            </div>
            <div class="refresh-card">
                <span class="cyan">↻</span>
                <div>
                    <small>LAST PAGE UPDATE</small>
                    <b>{{ now }}</b>
                </div>
                <a class="primary-button" href="/refresh">Refresh News ↻</a>
            </div>
        </section>

        <section class="metrics">
            <article class="metric featured">
                <div class="metric-label">Total headlines <span>▤</span></div>
                <strong>{{ all_count }}</strong>
                <small>Last 24 hours</small>
            </article>
            <article class="metric">
                <div class="metric-label">New stories <span class="green">✳</span></div>
                <strong>{{ new_count }}</strong>
                <small>Newly discovered stories</small>
            </article>
            <article class="metric">
                <div class="metric-label">Updated stories <span class="blue">⟳</span></div>
                <strong>{{ updated_count }}</strong>
                <small>Headline changes detected</small>
            </article>
            <article class="metric">
                <div class="metric-label">News sources <span class="violet">◎</span></div>
                <strong>{{ source_count }}</strong>
                <small>Available sources</small>
            </article>
        </section>

        <div class="content-grid">
            <section class="panel" id="headlines">
                <div class="panel-heading">
                    <div>
                        <span class="eyebrow">THE LATEST</span>
                        <h2>Headline explorer</h2>
                        <p>Search and filter monitored stories.</p>
                    </div>
                    <span class="result-count">{{ rows|length }} RESULTS</span>
                </div>

                <form class="filters" method="get" action="/">
                    <input name="q" value="{{ q }}"
                           placeholder="⌕  Search headlines..."
                           aria-label="Search headlines">

                    <select name="source" aria-label="Source">
                        <option value="All">All sources</option>
                        {% for item in sources %}
                        <option value="{{ item }}"
                            {% if selected_source == item %}selected{% endif %}>
                            {{ item }}
                        </option>
                        {% endfor %}
                    </select>

                    <select name="status" aria-label="Status">
                        <option value="All">All statuses</option>
                        {% for item in statuses %}
                        <option value="{{ item }}"
                            {% if selected_status == item %}selected{% endif %}>
                            {{ item }}
                        </option>
                        {% endfor %}
                    </select>

                    <button type="submit">Filter</button>
                </form>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>STORY</th>
                                <th>SOURCE</th>
                                <th>STATUS</th>
                                <th>PUBLISHED</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for h in rows %}
                        <tr>
                            <td class="story">
                                <span class="story-dot {{ h.status|lower }}"></span>
                                <div>
                                    <a href="{{ h.url }}" target="_blank"
                                       rel="noopener noreferrer">{{ h.title }}</a>
                                    <small>{{ h.section or "General" }}</small>
                                </div>
                            </td>
                            <td><span class="source-name">{{ h.source }}</span></td>
                            <td><span class="badge {{ h.status|lower }}">{{ h.status }}</span></td>
                            <td class="time">{{ h.relative }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="4" class="empty">
                                No matching headlines in the last 24 hours.
                                Try clearing your filters or refresh the feeds.
                            </td>
                        </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>

                <div class="panel-footer">
                    Showing {{ rows|length }} of {{ all_count }} records
                </div>
            </section>

            <div class="right-column">
                <section class="panel" id="activity">
                    <div class="panel-heading">
                        <div>
                            <span class="eyebrow">WHAT'S CHANGING</span>
                            <h2>Recent activity</h2>
                        </div>
                    </div>

                    <div class="activity-list">
                    {% for h in changes %}
                        <div class="activity">
                            <span class="activity-dot {{ h.status|lower }}"></span>
                            <div>
                                <b>{{ h.status }} headline</b>
                                <p>{{ h.title }}</p>
                                <small>{{ h.source }} · {{ h.last_seen }}</small>
                            </div>
                        </div>
                    {% else %}
                        <p class="muted">No recent activity available.</p>
                    {% endfor %}
                    </div>
                </section>

                <section class="panel" id="sources">
                    <div class="panel-heading">
                        <div>
                            <span class="eyebrow">COVERAGE</span>
                            <h2>Source breakdown</h2>
                        </div>
                    </div>

                    {% for item in source_breakdown %}
                    <div class="source-row">
                        <div>
                            <span>{{ item.name }}</span>
                            <b>{{ item.count }}</b>
                        </div>
                        <div class="progress">
                            <span style="width:{{ item.percent }}%"></span>
                        </div>
                    </div>
                    {% else %}
                    <p class="muted">No source records.</p>
                    {% endfor %}

                    <div class="source-note">
                        Based on news published in the last 24 hours.
                    </div>
                </section>
            </div>
        </div>

        <footer class="page-footer">
            <span><b>PULSE<span class="cyan">.</span></b> NEWS INTELLIGENCE</span>
            <span>Built to surface signal, not noise.</span>
            <span>{{ "WAITING FOR FEED" if demo else "LIVE RSS + SQLITE" }}</span>
        </footer>
    </main>
</div>
</body>
</html>
"""


def time_ago(value):
    if not value:
        return "Time unavailable"

    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)

        seconds = max(
            0,
            int(
                (
                    datetime.now(timezone.utc)
                    - moment.astimezone(timezone.utc)
                ).total_seconds()
            ),
        )

        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds // 60} min ago"
        if seconds < 86400:
            return f"{seconds // 3600} hr ago"

        return f"{seconds // 86400} days ago"

    except (ValueError, TypeError, OverflowError):
        return str(value)


@app.route("/")
def dashboard():
    refresh_result = refresh_news()
    headlines = get_recent_headlines()

    q = request.args.get("q", "").strip().casefold()
    selected_source = request.args.get("source", "All")
    selected_status = request.args.get("status", "All")

    sources = sorted({
        h.get("source", "Unknown")
        for h in headlines
        if h.get("source")
    })

    statuses = sorted({
        h.get("status", "New")
        for h in headlines
        if h.get("status")
    })

    if not statuses:
        statuses = ["New", "Updated", "Unchanged"]

    rows = []

    for headline in headlines:
        searchable = (
            f"{headline.get('title', '')} "
            f"{headline.get('source', '')} "
            f"{headline.get('section', '')}"
        ).casefold()

        if q and q not in searchable:
            continue

        if (
            selected_source != "All"
            and headline.get("source") != selected_source
        ):
            continue

        if (
            selected_status != "All"
            and headline.get("status") != selected_status
        ):
            continue

        item = dict(headline)
        item["relative"] = time_ago(item.get("published_at"))
        rows.append(item)

    changes = [
        h for h in headlines
        if h.get("status") in {"New", "Updated"}
    ][:4]

    source_breakdown = []

    for source in sources:
        count = sum(
            1 for h in headlines if h.get("source") == source
        )

        source_breakdown.append({
            "name": source,
            "count": count,
            "percent": round(
                count * 100 / max(len(headlines), 1)
            ),
        })

    return render_template_string(
        PAGE,
        rows=rows,
        q=request.args.get("q", ""),
        sources=sources,
        statuses=statuses,
        selected_source=selected_source,
        selected_status=selected_status,
        all_count=len(headlines),
        new_count=sum(
            h.get("status") == "New" for h in headlines
        ),
        updated_count=sum(
            h.get("status") == "Updated" for h in headlines
        ),
        source_count=len(sources),
        changes=changes,
        source_breakdown=source_breakdown,
        demo=(len(headlines) == 0),
        demo_reason="No recent RSS headlines were returned.",
        refresh_errors=refresh_result.get("errors", []),
        last_refresh=get_refresh_status(),
        now=datetime.now().astimezone().strftime(
            "%d %b %Y · %H:%M"
        ),
    )


@app.route("/refresh")
def manual_refresh():
    refresh_news(force=True)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    print("Pulse News Intelligence starting...")
    print(f"Database location: {DB_PATH}")
    print("News refresh interval: 5 minutes")
    app.run(debug=True)
