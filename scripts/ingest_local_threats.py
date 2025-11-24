#!/usr/bin/env python3
"""Standalone script to ingest local threat data from Virginia police dispatch feeds.

This script can be run manually or as a scheduled job (e.g., cron every 5 minutes).
It scrapes dispatch data, converts to feed format, and inserts into the articles database.

Usage:
    python scripts/ingest_local_threats.py

Options (set via environment variables):
    LOOKBACK_HOURS: Pattern detection window (default: 6)
    MIN_SEVERITY: Minimum severity to include (default: 3, range 1-5)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking
from forecasting.storage import insert_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/local_threats_ingest.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main ingestion routine."""
    logger.info("=" * 60)
    logger.info("Starting local threat ingestion")
    logger.info("=" * 60)
    
    # Fetch local threat feeds
    try:
        feed_items = fetch_local_threat_feeds_with_health_tracking(
            jurisdictions=None,  # All Virginia jurisdictions
            lookback_hours=6,
            tracker_db_path="data/local_threats.db",
            health_db_path="data/feed_health.db"
        )
        
        if not feed_items:
            logger.warning("No local threat items returned")
            return 0
        
        logger.info(f"Fetched {len(feed_items)} local threat feed items")
        
        # Show sample
        logger.info("Sample item:")
        sample = feed_items[0]
        logger.info(f"  ID: {sample['id']}")
        logger.info(f"  Title: {sample['title']}")
        logger.info(f"  Jurisdiction: {sample.get('jurisdiction', 'Unknown')}")
        logger.info(f"  Severity: {sample.get('severity', 0)}/5")
        
        # Insert into articles database
        try:
            articles = []
            for item in feed_items:
                articles.append({
                    "id": item["id"],
                    "title": item["title"],
                    "text": item.get("text", item.get("summary", "")),
                    "source_url": item["source_url"],
                    "published": item.get("published", datetime.utcnow().isoformat()),
                    "fetched_from": item.get("fetched_from", "local_dispatch"),
                })
            
            inserted_count = insert_articles("data/live.db", articles)
            # insert_articles doesn't return count, so use len(articles) as estimate
            logger.info(f"✓ Successfully processed {len(articles)} local threat articles")
            logger.info("  (Duplicates automatically skipped by content hash)")
            
            return len(articles)
            
        except Exception as e:
            logger.error(f"Failed to insert articles: {e}", exc_info=True)
            return 0
            
    except Exception as e:
        logger.error(f"Failed to fetch local threat feeds: {e}", exc_info=True)
        return 0
    
    finally:
        logger.info("=" * 60)
        logger.info("Local threat ingestion complete")
        logger.info("=" * 60)


if __name__ == "__main__":
    inserted = main()
    # Exit 0 if any items were processed, 1 if nothing was done
    sys.exit(0 if inserted and inserted > 0 else 1)
