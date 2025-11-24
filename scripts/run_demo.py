#!/usr/bin/env python3
"""End-to-end demo runner.

Usage:
  python scripts/run_demo.py --mode demo

Modes:
  demo  : use synthetic data and run the entire pipeline without heavy external libs
  live  : attempt to fetch a real RSS feed (requires feedparser)
"""
import argparse
from pprint import pprint


def run_demo():
    from forecasting.ingest import synthetic_events_expanded
    from forecasting.extract import extract_from_article
    from forecasting.storage import init_db, insert_articles, insert_extracted
    from forecasting.features import build_daily_aggregates, make_lag_features
    from forecasting.model import backtest

    print("Running demo pipeline (synthetic data)")
    articles = synthetic_events_expanded(days=60, seed=1)
    print(f"Generated {len(articles)} synthetic articles")

    db_path = "data/demo.db"
    init_db(db_path)
    insert_articles(db_path, articles)

    extracted = [extract_from_article(a, use_spacy=False) for a in articles]
    # merge content_type back into articles for feature generation
    id_to_type = {e["id"]: e.get("content_type") for e in extracted}
    for a in articles:
        ct = id_to_type.get(a.get("id"))
        if ct:
            a["content_type"] = ct

    insert_extracted(db_path, extracted)

    df = build_daily_aggregates(articles)
    df_lag = make_lag_features(df)
    print("Sample daily features:")
    print(df_lag.tail())

    metrics, preds = backtest(df_lag)
    print("Backtest metrics:")
    pprint(metrics)


def run_live_example(rss_url: str):
    from forecasting.ingest import fetch_rss_feed, default_public_feeds, fetch_multiple_feeds
    from forecasting.extract import extract_from_article
    from forecasting.storage import init_db, insert_articles, insert_extracted

    feeds = default_public_feeds()
    db_path = "data/live.db"
    print(f"Fetching {len(feeds)} public RSS feeds with dedupe and cooldown...")
    items = fetch_multiple_feeds(feeds, max_items_per_feed=80, db_path=db_path, per_domain_cooldown_sec=10)
    print(f"Fetched total {len(items)} items from feeds")
    if not items:
        print("No items fetched; check network or feed availability.")
        return
    db_path = "data/live.db"
    init_db(db_path)
    insert_articles(db_path, items)
    extracted = [extract_from_article(a, use_spacy=False) for a in items]
    insert_extracted(db_path, extracted)
    print(f"Stored live fetch into DB at {db_path}")

    # quick summary: counts per content type
    from collections import Counter

    types = [e.get("content_type") or "other" for e in extracted]
    cnt = Counter(types)
    print("Content-type distribution:")
    for k, v in cnt.most_common():
        print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="demo", choices=["demo", "live"])
    parser.add_argument("--rss", default="https://feeds.bbci.co.uk/news/world/rss.xml")
    args = parser.parse_args()
    if args.mode == "demo":
        run_demo()
    else:
        run_live_example(args.rss)


if __name__ == "__main__":
    main()
