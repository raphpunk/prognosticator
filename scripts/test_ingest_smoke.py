#!/usr/bin/env python3
"""Smoke test for ingest helpers (non-pytest) to run quickly.

This script will run a quick live fetch of a single feed using the demo DB and print counts.
"""
from forecasting.ingest import load_feeds_config, fetch_multiple_feeds
from forecasting.storage import init_db

def main():
    db_path = "data/test_ingest.db"
    init_db(db_path)
    feeds = [f["url"] for f in load_feeds_config()[:1]]
    items = fetch_multiple_feeds(feeds, max_items_per_feed=5, db_path=db_path, per_domain_cooldown_sec=0)
    print(f"Fetched {len(items)} items")

if __name__ == "__main__":
    main()
