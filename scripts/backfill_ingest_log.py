#!/usr/bin/env python3
"""Backfill `ingest_log` from existing `articles` table."""
from forecasting.storage import backfill_ingest_log


def main():
    db_path = "data/live.db"
    print(f"Backfilling ingest_log from {db_path}...")
    backfill_ingest_log(db_path)
    print("Backfill complete.")


if __name__ == "__main__":
    main()
