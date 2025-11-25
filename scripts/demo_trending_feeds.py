#!/usr/bin/env python3
"""Demo script for trending feeds module.

Demonstrates fetching and processing trending signals from multiple sources.

This is the NEW feed system that supports:
- RSS feeds
- Google Trends
- Exploding Topics
- Web scraping

For production use, see: src/forecasting/trending_feeds_integration.py
"""

import sys
import logging
from pathlib import Path

# Add sources to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "sources"))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("=" * 70)
print("TRENDING FEEDS MODULE DEMO")
print("=" * 70)
print()

# Test imports
print("Testing module imports...")
try:
    from sources.feeds import (
        fetch_rss_feed,
        fetch_google_trends,
        fetch_exploding_topics,
        fetch_all_trending_feeds,
        load_feeds_config,
        Signal,
    )
    print("✓ Successfully imported feeds module")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()
print("-" * 70)
print("TEST 1: Fetch single RSS feed (Hacker News)")
print("-" * 70)
try:
    signals = fetch_rss_feed(
        url="https://news.ycombinator.com/rss",
        source_name="hackernews_demo",
        max_items=3
    )
    print(f"✓ Fetched {len(signals)} signals")
    if signals:
        print("\nFirst signal:")
        s = signals[0]
        print(f"  Title: {s.title[:60]}...")
        print(f"  Link: {s.link}")
        print(f"  ID: {s.signal_id}")
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("-" * 70)
print("TEST 2: Fetch Google Trends (if pytrends installed)")
print("-" * 70)
try:
    signals = fetch_google_trends(geo="US", max_trends=3)
    print(f"✓ Fetched {len(signals)} trending topics")
    if signals:
        print("\nTop trends:")
        for s in signals[:3]:
            rank = s.metadata.get('rank', '?')
            interest = s.metadata.get('avg_interest', 'N/A')
            print(f"  #{rank}: {s.title} (interest: {interest}/100)")
except ImportError:
    print("⚠ Skipped: pytrends not installed")
    print("  Install with: pip install pytrends")
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("-" * 70)
print("TEST 3: Load configuration and fetch all feeds")
print("-" * 70)
try:
    config = load_feeds_config("config/feeds.yaml")
    
    # Count enabled sources
    rss_enabled = sum(1 for f in config.get('rss_feeds', []) if f.get('enabled'))
    scrapers_enabled = sum(1 for s in config.get('scrapers', {}).values() if s.get('enabled'))
    
    print(f"Configuration loaded:")
    print(f"  - {len(config.get('rss_feeds', []))} RSS feeds ({rss_enabled} enabled)")
    print(f"  - {len(config.get('scrapers', {}))} scrapers ({scrapers_enabled} enabled)")
    
    print("\nFetching all enabled feeds...")
    all_signals = fetch_all_trending_feeds(config)
    
    print(f"✓ Total: {len(all_signals)} signals collected")
    
    # Breakdown by source
    if all_signals:
        from collections import Counter
        sources = Counter(s.source for s in all_signals)
        print("\nBreakdown by source:")
        for source, count in sources.most_common():
            print(f"  - {source:30} {count:3} signals")
            
except FileNotFoundError:
    print("⚠ Config file not found, using defaults")
    config = None
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("-" * 70)
print("TEST 4: Signal to dict conversion")
print("-" * 70)
try:
    from sources.feeds import signals_to_dict
    
    # Create test signal
    test_signal = Signal(
        source="test_source",
        title="Test Signal",
        link="https://example.com/test",
        timestamp="2025-11-25T12:00:00Z",
        summary="This is a test signal",
        metadata={"key": "value"}
    )
    
    signal_dict = signals_to_dict([test_signal])[0]
    print("✓ Signal converted to dict:")
    print(f"  Keys: {list(signal_dict.keys())}")
    print(f"  Signal ID: {signal_dict['signal_id']}")
    
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 70)
print("DEMO COMPLETE")
print("=" * 70)
print()
print("Next steps:")
print("1. Install dependencies:")
print("   pip install feedparser pytrends beautifulsoup4 pyyaml requests")
print()
print("2. Run production integration:")
print("   python src/forecasting/trending_feeds_integration.py")
print()
print("3. View stats:")
print("   python src/forecasting/trending_feeds_integration.py --stats")
print()
print("📝 Note: This replaces the old scripts/ingest_rss_feeds.py script")
print("   which only supported basic RSS. This new system is more capable.")
print()
