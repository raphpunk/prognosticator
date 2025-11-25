#!/usr/bin/env python3
"""Quick verification script for trending feeds module.

Runs minimal tests to verify the module is working correctly.
"""

import sys
from pathlib import Path

# Add sources to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

print("Prognosticator Trending Feeds - Quick Verification")
print("=" * 70)

# Test 1: Module imports
print("\n1. Testing module imports...")
try:
    from sources.feeds import (
        Signal,
        fetch_rss_feed,
        fetch_google_trends,
        fetch_all_trending_feeds,
        load_feeds_config,
        signals_to_dict,
    )
    print("   ✅ All core functions imported successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Signal creation
print("\n2. Testing Signal dataclass...")
try:
    signal = Signal(
        source="test",
        title="Test Signal",
        link="https://example.com",
        timestamp="2025-11-25T12:00:00Z",
        summary="Test summary"
    )
    assert signal.signal_id is not None
    assert len(signal.signal_id) == 16
    print(f"   ✅ Signal created with ID: {signal.signal_id}")
except Exception as e:
    print(f"   ❌ Signal creation failed: {e}")
    sys.exit(1)

# Test 3: Configuration loading
print("\n3. Testing configuration loading...")
try:
    config = load_feeds_config("config/feeds.yaml")
    rss_count = len(config.get('rss_feeds', []))
    scraper_count = len(config.get('scrapers', {}))
    print(f"   ✅ Config loaded: {rss_count} RSS feeds, {scraper_count} scrapers")
except Exception as e:
    print(f"   ⚠️  Config load warning: {e}")
    print("   Using default configuration")

# Test 4: RSS feed fetch (small)
print("\n4. Testing RSS feed fetch...")
try:
    signals = fetch_rss_feed(
        url="https://news.ycombinator.com/rss",
        source_name="test_hn",
        max_items=3
    )
    print(f"   ✅ Fetched {len(signals)} signals from Hacker News")
    if signals:
        print(f"   Sample: {signals[0].title[:50]}...")
except Exception as e:
    print(f"   ❌ RSS fetch failed: {e}")

# Test 5: Integration module
print("\n5. Testing integration module...")
try:
    from src.forecasting.trending_feeds_integration import (
        signals_to_articles,
        fetch_and_integrate_trending_feeds,
    )
    print("   ✅ Integration module imported successfully")
    
    # Test signal conversion
    test_signals = [signal]
    articles = signals_to_articles(test_signals)
    assert len(articles) == 1
    assert 'title' in articles[0]
    assert 'source_url' in articles[0]
    print("   ✅ Signal → Article conversion working")
    
except ImportError as e:
    print(f"   ⚠️  Integration module not available: {e}")
except Exception as e:
    print(f"   ❌ Integration test failed: {e}")

# Test 6: Dependencies check
print("\n6. Checking optional dependencies...")
deps_status = {}

try:
    import feedparser
    deps_status['feedparser'] = '✅'
except ImportError:
    deps_status['feedparser'] = '❌'

try:
    import yaml
    deps_status['pyyaml'] = '✅'
except ImportError:
    deps_status['pyyaml'] = '❌'

try:
    import requests
    deps_status['requests'] = '✅'
except ImportError:
    deps_status['requests'] = '❌'

try:
    from bs4 import BeautifulSoup
    deps_status['beautifulsoup4'] = '✅'
except ImportError:
    deps_status['beautifulsoup4'] = '❌'

try:
    from pytrends.request import TrendReq
    deps_status['pytrends'] = '✅'
except ImportError:
    deps_status['pytrends'] = '⚠️  (optional)'

for dep, status in deps_status.items():
    print(f"   {status} {dep}")

# Summary
print("\n" + "=" * 70)
print("Verification Summary")
print("=" * 70)

missing = [k for k, v in deps_status.items() if v == '❌']
if missing:
    print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
    print("Install with: pip install " + " ".join(missing))
else:
    print("\n✅ All required dependencies installed")

print("\n📚 Documentation:")
print("   - Full guide: docs/TRENDING_FEEDS.md")
print("   - Quick ref: docs/TRENDING_FEEDS_QUICKREF.md")
print("   - Summary: docs/TRENDING_FEEDS_SUMMARY.md")

print("\n🚀 Next steps:")
print("   1. Run demo: python scripts/demo_trending_feeds.py")
print("   2. Integrate: python src/forecasting/trending_feeds_integration.py")
print("   3. View stats: python src/forecasting/trending_feeds_integration.py --stats")

print("\n✅ Verification complete!\n")
