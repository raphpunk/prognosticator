"""Ingestion utilities.

This module provides simple RSS ingestion helpers and a demo data generator.
All heavy external imports are done lazily so `--mode demo` runs without spaCy/feedparser.
"""
from datetime import datetime, timedelta
import random
import json
from typing import List, Dict


def fetch_rss_feed(url: str, max_items: int = 50) -> List[Dict]:
    """Fetch entries from an RSS/Atom feed using feedparser (lazy import).

    Returns list of dicts: {"id","title","summary","published","source_url"}
    """
    try:
        import feedparser
    except Exception as e:
        raise RuntimeError("feedparser is required for real ingestion. Install it or run demo mode.") from e

    d = feedparser.parse(url)
    out = []
    for entry in d.entries[:max_items]:
        pub = getattr(entry, "published", None) or getattr(entry, "updated", None)
        out.append({
            "id": getattr(entry, "id", entry.get("link", None)),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "published": pub,
            "source_url": entry.get("link", None),
            "raw": entry,
        })
    return out


def synthetic_timeseries_events(days: int = 30, seed: int = 0) -> List[Dict]:
    """Generate synthetic daily article counts with sporadic spikes to simulate events.

    Returns list of records with `date` and `article_count`.
    """
    random.seed(seed)
    base = 20
    out = []
    today = datetime.utcnow().date()
    for i in range(days):
        d = today - timedelta(days=(days - 1 - i))
        noise = random.randint(-5, 5)
        # occasional spikes
        spike = 0
        if random.random() < 0.08:
            spike = random.randint(20, 80)
        count = max(0, base + noise + spike)
        out.append({"date": d.isoformat(), "article_count": count})
    return out


def synthetic_events_expanded(days: int = 30, seed: int = 0) -> List[Dict]:
    """Create synthetic 'article' records (one per article) for demo ingestion.

    Each record contains `id`, `title`, `text`, and `published`.
    """
    series = synthetic_timeseries_events(days=days, seed=seed)
    out = []
    for rec in series:
        d = rec["date"]
        n = rec["article_count"]
        for j in range(n):
            out.append({
                "id": f"synthetic-{d}-{j}",
                "title": f"Synthetic news {j} on {d}",
                "text": f"This is synthetic content number {j} for date {d}.",
                "published": d,
                "source_url": "synthetic",
            })
    return out


def load_feeds_config(path: str = "feeds.json") -> List[Dict]:
    """Load feed configuration from `feeds.json` if present; otherwise return default list.

    Config format: {"feeds": [{"url":..., "cooldown": seconds, "active": bool}, ...]}
    """
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        # fallback default
        return [
            {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "cooldown": 300, "active": True},
            {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "cooldown": 600, "active": True},
            {"url": "https://www.aljazeera.com/xml/rss/all.xml", "cooldown": 300, "active": True},
            {"url": "https://www.reutersagency.com/feed/?best-topics=world", "cooldown": 300, "active": True},
            {"url": "https://www.theguardian.com/world/rss", "cooldown": 300, "active": True},
            {"url": "https://rss.cnn.com/rss/edition_world.rss", "cooldown": 300, "active": True},
            {"url": "https://feeds.feedburner.com/TechCrunch/", "cooldown": 300, "active": True},
        ]
    try:
        with open(p, "r") as fh:
            cfg = json.load(fh)
        return cfg.get("feeds", [])
    except Exception:
        return []


def default_public_feeds() -> List[str]:
    cfg = load_feeds_config()
    return [f["url"] for f in cfg if f.get("active", True)]


def fetch_multiple_feeds(urls: List[str], max_items_per_feed: int = 50, db_path: str = "data/live.db", per_domain_cooldown_sec: int = 60, feeds_config: str = "feeds.json") -> List[Dict]:
    """Fetch multiple RSS feeds and return combined list of entries with `source` provenance.

    Implements simple per-domain cooldown using `feed_state` in the SQLite DB to avoid re-polling domains too frequently.
    Deduplication is handled downstream by `insert_articles` via content hashes.
    """
    from urllib.parse import urlparse
    from time import time
    from forecasting.storage import get_last_fetch, set_last_fetch

    items = []
    now_ts = str(time())
    # load per-feed cooldowns
    feed_cfg = {}
    try:
        for f in load_feeds_config(feeds_config):
            feed_cfg[f.get("url")] = f
    except Exception:
        feed_cfg = {}

    for u in urls:
        try:
            domain = urlparse(u).netloc
        except Exception:
            domain = u

        # compute cooldown: check feed-specific first then default
        cooldown = per_domain_cooldown_sec
        try:
            if u in feed_cfg and isinstance(feed_cfg[u].get("cooldown"), (int, float)):
                cooldown = int(feed_cfg[u].get("cooldown"))
        except Exception:
            pass

        # check cooldown
        try:
            last = get_last_fetch(db_path, u)
            if last:
                try:
                    last_f = float(last)
                    if time() - last_f < cooldown:
                        # skip this feed due to cooldown
                        continue
                except Exception:
                    pass
        except Exception:
            # if DB unavailable, proceed
            pass

        try:
            feed_items = fetch_rss_feed(u, max_items=max_items_per_feed)
        except Exception:
            # skip failing feeds
            continue
        for it in feed_items:
            it["fetched_from"] = u
            # pre-check using title+summary to avoid parsing/extracting duplicates
            title = it.get("title", "")
            summary = it.get("summary", "") or it.get("description", "")
            try:
                import hashlib
                import sqlite3
                from difflib import SequenceMatcher

                h = hashlib.sha256((title + summary).encode("utf-8")).hexdigest()
                # check ingest_log to skip already-seen content
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM ingest_log WHERE content_hash=?", (h,))
                if cur.fetchone():
                    conn.close()
                    continue

                # fuzzy title check against existing titles in ingest_log to avoid near-duplicates
                cur.execute("SELECT title FROM ingest_log WHERE title IS NOT NULL")
                rows = cur.fetchall()
                skip = False
                for (existing_title,) in rows:
                    if not existing_title:
                        continue
                    try:
                        ratio = SequenceMatcher(None, existing_title.lower(), title.lower()).ratio()
                        if ratio >= 0.90:
                            skip = True
                            break
                    except Exception:
                        continue
                conn.close()
                if skip:
                    continue
            except Exception:
                # if any error, don't skip
                pass

            it["pre_hash"] = h
            items.append(it)

        # update last fetch for domain
        try:
            set_last_fetch(db_path, domain, now_ts)
        except Exception:
            pass

    return items


if __name__ == "__main__":
    # quick smoke demo
    items = synthetic_events_expanded(7)
    print(f"Generated {len(items)} synthetic articles")
