#!/usr/bin/env python3
"""Generate a simple ingest report from `data/live.db`.

Exports `data/ingest_log.csv` and prints summaries.
"""
import sqlite3
import csv
from collections import Counter


def export_ingest_log(db_path: str = "data/live.db", out_csv: str = "data/ingest_log.csv"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT content_hash, first_seen, last_seen, count, source_url FROM ingest_log")
    rows = cur.fetchall()
    conn.close()
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["content_hash", "first_seen", "last_seen", "count", "source_url"])
        for r in rows:
            w.writerow(r)
    print(f"Exported {len(rows)} rows to {out_csv}")


def print_summary(db_path: str = "data/live.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    total = cur.fetchone()[0]
    cur.execute("SELECT source_url, COUNT(*) FROM articles GROUP BY source_url ORDER BY COUNT(*) DESC LIMIT 10")
    top_sources = cur.fetchall()
    cur.execute("SELECT entities FROM extracted")
    ent_rows = cur.fetchall()
    conn.close()
    print(f"Total stored articles: {total}")
    print("Top sources:")
    for s, c in top_sources:
        print(f"  {s}: {c}")


if __name__ == "__main__":
    export_ingest_log()
    print_summary()
