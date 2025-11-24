"""Simple persistence layer for prototype.

Uses SQLite (via builtin `sqlite3`) for small-scale persistence and JSON export.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT,
    text TEXT,
    published TEXT,
    source_url TEXT,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS extracted (
    id TEXT PRIMARY KEY,
    article_id TEXT,
    published TEXT,
    entities TEXT
);

CREATE TABLE IF NOT EXISTS feed_state (
    domain TEXT PRIMARY KEY,
    last_fetch_ts TEXT
);

CREATE TABLE IF NOT EXISTS ingest_log (
    content_hash TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen TEXT,
    count INTEGER,
    source_url TEXT
);
"""


def ensure_ingest_log_has_title(path: str):
    """Ensure `ingest_log` has a `title` column. Adds it if missing."""
    import sqlite3
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE ingest_log ADD COLUMN title TEXT")
        conn.commit()
    except Exception:
        # likely column already exists
        pass
    conn.close()


def backfill_ingest_log(path: str):
    """Backfill `ingest_log` from existing `articles` rows.

    For each article, compute content_hash if missing and insert/update ingest_log with title and counts.
    """
    import sqlite3
    import hashlib
    from datetime import datetime

    ensure_ingest_log_has_title(path)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # ensure articles table has content_hash column (may be missing in older DBs)
    try:
        cur.execute("ALTER TABLE articles ADD COLUMN content_hash TEXT")
        conn.commit()
    except Exception:
        pass
    cur.execute("SELECT id, title, text, published, source_url, content_hash FROM articles")
    rows = cur.fetchall()
    for r in rows:
        aid, title, text, published, source_url, content_hash = r
        text = text or ""
        if not content_hash:
            content_hash = hashlib.sha256(((title or "") + text).encode("utf-8")).hexdigest()
            # update article with content_hash
            try:
                cur.execute("UPDATE articles SET content_hash=? WHERE id=?", (content_hash, aid))
            except Exception:
                pass

        # insert or update ingest_log
        cur.execute("SELECT count FROM ingest_log WHERE content_hash=?", (content_hash,))
        existing = cur.fetchone()
        if existing:
            try:
                cur.execute(
                    "UPDATE ingest_log SET last_seen=?, count = count + 1, source_url = ? , title = ? WHERE content_hash = ?",
                    (str(published), source_url, title, content_hash),
                )
            except Exception:
                pass
        else:
            try:
                cur.execute(
                    "INSERT OR REPLACE INTO ingest_log (content_hash, first_seen, last_seen, count, source_url, title) VALUES (?,?,?,?,?,?)",
                    (content_hash, str(published or datetime.utcnow()), str(published or datetime.utcnow()), 1, source_url, title),
                )
            except Exception:
                pass
    conn.commit()
    conn.close()


def init_db(path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(DB_SCHEMA)
    conn.commit()
    conn.close()


def insert_articles(path: str, articles: List[Dict]):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for a in articles:
        try:
            text = a.get("text") or a.get("summary") or ""
            import hashlib

            content_hash = hashlib.sha256((str(a.get("title", "")) + text).encode("utf-8")).hexdigest()
            # skip if we've already seen this content_hash
            cur.execute("SELECT 1 FROM ingest_log WHERE content_hash=?", (content_hash,))
            if cur.fetchone():
                # update last_seen and count
                cur.execute(
                    "UPDATE ingest_log SET last_seen = ?, count = count + 1 WHERE content_hash = ?",
                    (str(a.get("published")), content_hash),
                )
                continue

            cur.execute(
                "INSERT OR REPLACE INTO articles (id,title,text,published,source_url,content_hash) VALUES (?,?,?,?,?,?)",
                (a.get("id"), a.get("title"), text, a.get("published"), a.get("source_url"), content_hash),
            )
            # add to ingest_log
            cur.execute(
                "INSERT OR REPLACE INTO ingest_log (content_hash, first_seen, last_seen, count, source_url) VALUES (?,?,?,?,?)",
                (content_hash, str(a.get("published")), str(a.get("published")), 1, a.get("source_url")),
            )
        except Exception:
            # skip bad rows
            continue
    conn.commit()
    conn.close()


def insert_extracted(path: str, extracted: List[Dict]):
    import json

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for e in extracted:
        try:
            cur.execute(
                "INSERT OR REPLACE INTO extracted (id,article_id,published,entities) VALUES (?,?,?,?)",
                (e.get("id"), e.get("id"), e.get("published"), json.dumps(e.get("entities", []))),
            )
        except Exception:
            continue
    conn.commit()
    conn.close()


def get_last_fetch(path: str, domain: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT last_fetch_ts FROM feed_state WHERE domain = ?", (domain,))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else None


def set_last_fetch(path: str, domain: str, ts: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO feed_state (domain, last_fetch_ts) VALUES (?,?)", (domain, ts))
    conn.commit()
    conn.close()


def export_json(path: str, out_path: str):
    import json
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT id,title,text,published,source_url FROM articles")
    rows = cur.fetchall()
    recs = []
    for r in rows:
        recs.append({"id": r[0], "title": r[1], "text": r[2], "published": r[3], "source_url": r[4]})
    with open(out_path, "w") as fh:
        json.dump(recs, fh, default=str, indent=2)


if __name__ == "__main__":
    init_db("data/demo.db")
    print("Initialized demo DB at data/demo.db")
