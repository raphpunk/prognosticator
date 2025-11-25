# Trending Feeds Quick Reference

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install feedparser pytrends beautifulsoup4 pyyaml requests

# 2. Test the module
python scripts/demo_trending_feeds.py

# 3. Integrate with Prognosticator
python src/forecasting/trending_feeds_integration.py
```

## 📋 Common Commands

```bash
# Fetch and integrate all trending feeds
python src/forecasting/trending_feeds_integration.py

# View trending feed statistics
python src/forecasting/trending_feeds_integration.py --stats

# Custom database path
python src/forecasting/trending_feeds_integration.py --db data/custom.db

# Custom config path
python src/forecasting/trending_feeds_integration.py --config my_feeds.yaml
```

## 🔧 Configuration Snippets

### Enable/Disable RSS Feed
```yaml
rss_feeds:
  - name: techcrunch
    url: https://feeds.feedburner.com/TechCrunch/
    enabled: true  # Change to false to disable
    max_items: 50
```

### Add Custom RSS Feed
```yaml
rss_feeds:
  - name: my_feed
    url: https://example.com/rss
    enabled: true
    max_items: 30
    description: "My custom feed"
```

### Configure Google Trends
```yaml
scrapers:
  google_trends:
    enabled: true
    geo: US      # US, GB, DE, or "" for global
    timeframe: now 1-d  # now 1-d, today 5-y, etc.
    max_trends: 20
```

## 🐍 Code Snippets

### Fetch Single Feed
```python
from sources.feeds import fetch_rss_feed

signals = fetch_rss_feed(
    url="https://news.ycombinator.com/rss",
    source_name="hackernews",
    max_items=50
)

for signal in signals:
    print(f"{signal.title} - {signal.link}")
```

### Fetch Google Trends
```python
from sources.feeds import fetch_google_trends

trends = fetch_google_trends(geo="US", max_trends=10)

for trend in trends:
    print(f"#{trend.metadata['rank']}: {trend.title}")
```

### Fetch All Feeds
```python
from sources.feeds import fetch_all_trending_feeds, load_feeds_config

config = load_feeds_config("config/feeds.yaml")
signals = fetch_all_trending_feeds(config)

print(f"Total: {len(signals)} signals")
```

### Integrate with Database
```python
from forecasting.trending_feeds_integration import fetch_and_integrate_trending_feeds

count = fetch_and_integrate_trending_feeds(
    config_path="config/feeds.yaml",
    db_path="data/live.db"
)

print(f"Inserted {count} new articles")
```

## 📊 Signal Schema

```python
Signal(
    source="hackernews_best",           # Feed identifier
    title="New AI breakthrough...",      # Headline
    link="https://example.com/article",  # URL
    timestamp="2025-11-25T12:00:00Z",   # ISO 8601
    summary="Article summary...",        # Description
    signal_id="abc123def456",           # Auto-generated
    metadata={                           # Extra fields
        "author": "John Doe",
        "tags": ["AI", "tech"],
        "rank": 1
    }
)
```

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ImportError: No module named 'feedparser'` | `pip install feedparser` |
| `ImportError: No module named 'pytrends'` | `pip install pytrends` |
| No signals fetched | Check feed URL, verify in browser |
| Parse warnings | Feed may have formatting issues, check logs |
| Google Trends blocked | Reduce max_trends, add delays |
| Exploding Topics fails | Site structure changed, disable scraper |

## 📁 File Structure

```
sources/
├── __init__.py                      # Package init
└── feeds.py                         # Main module (600+ lines)

src/forecasting/
└── trending_feeds_integration.py    # Pipeline integration (200+ lines)

config/
└── feeds.yaml                       # Configuration (80+ lines)

scripts/
└── demo_trending_feeds.py           # Demo script (100+ lines)

docs/
└── TRENDING_FEEDS.md                # Full documentation
```

## 🎯 Supported Sources

### RSS Feeds (6 default)
- ✅ Trend Hunter
- ✅ Hacker News
- ✅ TechCrunch
- ✅ Reddit /r/worldnews
- ✅ Product Hunt
- ✅ MarketWatch

### Scrapers (2 available)
- ⚠️  Google Trends (requires pytrends)
- ⚠️  Exploding Topics (may be unreliable)

## ⚙️ Default Configuration

```yaml
# 6 RSS feeds enabled
# 1 scraper enabled (Google Trends)
# 1 scraper disabled (Exploding Topics)

Rate limiting: 30 req/min
Cache TTL: 15 minutes
Error handling: Skip on error
```

## 📈 Performance Tips

1. **Cache results**: Avoid redundant fetches
2. **Adjust max_items**: Balance speed vs coverage
3. **Disable slow feeds**: Monitor fetch times
4. **Stagger requests**: Add delays between feeds
5. **Use async**: Consider async fetching (future enhancement)

## 🔗 Links

- Full Documentation: `docs/TRENDING_FEEDS.md`
- Demo Script: `scripts/demo_trending_feeds.py`
- Configuration: `config/feeds.yaml`
- Source Code: `sources/feeds.py`

## 💡 Tips

- Start with RSS feeds (more reliable)
- Test sources individually first
- Monitor logs for warnings
- Disable broken feeds promptly
- Review config regularly
