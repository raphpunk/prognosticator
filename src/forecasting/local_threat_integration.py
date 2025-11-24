"""Integration layer for local threat monitoring into the Prognosticator feed pipeline.

This module bridges the dispatch scraping system (local_threats.py) with the existing
RSS feed ingestion pipeline. It fetches dispatch data, converts it to feed format,
and inserts it into the articles database for analysis by the Local Threat Analyst agent.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
import sys

# Configure logging
logger = logging.getLogger(__name__)


def fetch_local_threat_feeds(
    jurisdictions: Optional[List[str]] = None,
    lookback_hours: int = 6,
    tracker_db_path: str = "data/local_threats.db"
) -> List[Dict]:
    """Fetch local threat data from police dispatch feeds and convert to feed format.
    
    This function:
    1. Initializes the LocalThreatTracker
    2. Scrapes dispatch data for specified jurisdictions (or all if None)
    3. Detects threat patterns (escalation, coordination, spread)
    4. Converts data to RSS-like feed format for pipeline integration
    
    Args:
        jurisdictions: List of jurisdiction names (e.g., ['chesterfield', 'richmond'])
                      If None, fetches all configured jurisdictions
        lookback_hours: How far back to look for pattern detection (default: 6 hours)
        tracker_db_path: Path to local threats database
        
    Returns:
        List of feed-formatted dicts with keys: id, title, summary, published, source_url
        Returns empty list on error (non-blocking for main pipeline)
    """
    try:
        from src.forecasting.local_threats import LocalThreatTracker, DispatchScraper
        
        # Initialize tracker and scraper
        tracker = LocalThreatTracker(db_path=tracker_db_path)
        scraper = DispatchScraper(tracker=tracker)  # Pass tracker to scraper
        
        # Scrape all jurisdictions (or filtered by zip code if needed)
        # Note: jurisdictions parameter kept for future expansion
        try:
            all_calls = scraper.scrape_all_jurisdictions(zip_code=None)
            logger.info(f"Fetched {len(all_calls)} dispatch calls from all jurisdictions")
            
            # Record calls in database
            for call in all_calls:
                tracker.record_call(call)
                
        except Exception as e:
            logger.error(f"Failed to scrape jurisdictions: {e}")
            tracker.record_error("all_jurisdictions", "ScrapeFailure", str(e))
            return []
        
        if not all_calls:
            logger.warning("No dispatch calls fetched from any jurisdiction")
            return []
        
        # Detect threat patterns
        patterns = tracker.detect_escalation_patterns(hours=lookback_hours)
        logger.info(f"Detected {len(patterns)} threat patterns")
        
        # Convert calls to feed format (standalone function)
        from src.forecasting.local_threats import convert_to_feed_format
        feed_items = convert_to_feed_format(calls=all_calls, min_severity=3)
        logger.info(f"Converted {len(feed_items)} items to feed format")
        
        # TODO: Add pattern information to feed items
        # For now, patterns are logged but not directly included in feed
        
        return feed_items
        
    except ImportError as e:
        logger.error(f"Failed to import local_threats module: {e}")
        logger.error("Make sure Playwright is installed: pip install playwright")
        return []
    except Exception as e:
        logger.error(f"Error fetching local threat feeds: {e}", exc_info=True)
        return []


def fetch_local_threat_feeds_with_health_tracking(
    jurisdictions: Optional[List[str]] = None,
    lookback_hours: int = 6,
    tracker_db_path: str = "data/local_threats.db",
    health_db_path: str = "data/feed_health.db"
) -> List[Dict]:
    """Fetch local threat feeds with integrated feed health tracking.
    
    This is the recommended entry point for production use. It wraps fetch_local_threat_feeds
    with feed health monitoring to track reliability and detect anomalies.
    
    Args:
        jurisdictions: List of jurisdiction names to scrape
        lookback_hours: Pattern detection lookback window
        tracker_db_path: Path to local threats database
        health_db_path: Path to feed health database
        
    Returns:
        List of feed-formatted items (empty list on error)
    """
    try:
        from src.forecasting.feed_health import FeedHealthTracker
        
        # Virtual feed URL for health tracking (not a real URL)
        feed_url = "local://dispatch/virginia"
        
        # Initialize health tracker
        health_tracker = FeedHealthTracker(db_path=health_db_path)
        
        # Check if we should skip due to previous failures
        if health_tracker.should_skip_feed(feed_url):
            logger.warning(f"Skipping local threat feeds due to poor health (feed_url={feed_url})")
            return []
        
        # Fetch the data
        feed_items = fetch_local_threat_feeds(
            jurisdictions=jurisdictions,
            lookback_hours=lookback_hours,
            tracker_db_path=tracker_db_path
        )
        
        if feed_items:
            # Record success
            health_tracker.record_success(feed_url)
            
            # Record articles for anomaly detection
            for item in feed_items:
                article_id = item.get("id", "")
                published = item.get("published", "")
                content = (item.get("title", "") + " " + item.get("summary", ""))
                
                if article_id and published:
                    health_tracker.record_article(
                        article_id=article_id,
                        feed_url=feed_url,
                        published=published,
                        content_length=len(content),
                        topic_keywords=None  # Could extract keywords if needed
                    )
            
            # Check for anomalies
            anomalies = health_tracker.check_feed_anomalies(feed_url)
            if anomalies:
                logger.warning(f"Local threat feed has {len(anomalies)} anomalies detected")
                for anomaly in anomalies:
                    logger.warning(f"  - {anomaly['anomaly_type']}: {anomaly.get('details', '')}")
            
            # Update reputation based on anomalies
            health_tracker.update_reputation(feed_url, bool(anomalies))
            
        else:
            # Record failure (no data returned)
            health_tracker.record_failure(
                feed_url,
                "No dispatch calls returned from any jurisdiction"
            )
        
        return feed_items
        
    except Exception as e:
        logger.error(f"Error in local threat health tracking: {e}", exc_info=True)
        # Fall back to direct fetch without health tracking
        return fetch_local_threat_feeds(jurisdictions, lookback_hours, tracker_db_path)


def test_local_threat_integration():
    """Test function to verify local threat integration is working.
    
    Run with: python -m forecasting.local_threat_integration
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Testing local threat integration...")
    
    # Test fetch with health tracking
    items = fetch_local_threat_feeds_with_health_tracking(
        jurisdictions=['chesterfield'],  # Start with just one for testing
        lookback_hours=6
    )
    
    if items:
        logger.info(f"✓ Successfully fetched {len(items)} local threat feed items")
        logger.info("Sample item:")
        import json
        print(json.dumps(items[0], indent=2))
    else:
        logger.warning("✗ No items returned from local threat fetch")
        logger.info("This may be expected if:")
        logger.info("  1. Playwright is not installed (run: pip install playwright)")
        logger.info("  2. No active dispatch calls in the jurisdiction")
        logger.info("  3. Dispatch website structure has changed")
    
    logger.info("Test complete.")


if __name__ == "__main__":
    test_local_threat_integration()
