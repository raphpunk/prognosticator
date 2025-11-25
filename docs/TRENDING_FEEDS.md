# Trending Feeds Module

## Overview

The Trending Feeds module provides unified ingestion for trending signals from multiple sources including RSS feeds and web scrapers. All feeds are normalized into Prognosticator's Signal schema for downstream processing.

## Features

- **RSS Feed Support**: Ingest from standard RSS/Atom feeds
- **Web Scraping**: Extract trends from sources without RSS feeds
- **Unified Schema**: All sources normalized to Signal format
- **Config-Driven**: YAML-based configuration for easy source management
- **Error Handling**: Graceful handling of broken feeds with detailed logging
- **Metadata Preservation**: Source-specific fields retained for analysis

## Architecture

```
sources/
├── __init__.py
└── feeds.py              # Main feeds module

src/forecasting/
└── trending_feeds_integration.py  # Pipeline integration

config/
└── feeds.yaml            # Configuration file

scripts/
└── demo_trending_feeds.py  # Demo script
```

## Signal Schema

All feeds are normalized to this format:

```python
@dataclass
class Signal:
    source: str           # Feed identifier (e.g., "hackernews_best")
    title: str           # Headline or topic name
    link: str            # URL to original content
    timestamp: str       # ISO 8601 timestamp
    summary: str         # Description or snippet
    signal_id: str       # Unique identifier (auto-generated)
    metadata: dict       # Source-specific additional fields
```

## Supported Sources

### RSS Feeds
- **Trend Hunter**: Emerging consumer trends and innovations
- **Hacker News**: Tech and startup trends
- **TechCrunch**: Technology news
- **Reddit**: Social discussions (/r/worldnews, /r/technology)
- **Product Hunt**: Daily featured products
- **MarketWatch**: Financial market trends
- **Bloomberg**: Market news (optional)

### Scrapers
- **Google Trends**: Real-time search trends via pytrends API
- **Exploding Topics**: Rapidly growing search topics (via web scraping)

## Installation

### Core Dependencies
```bash
pip install feedparser beautifulsoup4 pyyaml requests
```

### Optional (for Google Trends)
```bash
pip install pytrends
```

### Verify Installation
```bash
python -m py_compile sources/feeds.py
python scripts/demo_trending_feeds.py
```

## Configuration

Edit `config/feeds.yaml` to enable/disable sources:

```yaml
rss_feeds:
  - name: hackernews_best
    url: https://news.ycombinator.com/rss
    enabled: true
    max_items: 50

scrapers:
  google_trends:
    enabled: true
    geo: US
    timeframe: now 1-d
    max_trends: 20
```

## Usage

### Basic Usage (Standalone)

```python
from sources.feeds import fetch_all_trending_feeds, load_feeds_config

# Load configuration
config = load_feeds_config("config/feeds.yaml")

# Fetch all enabled feeds
signals = fetch_all_trending_feeds(config)

# Process signals
for signal in signals:
    print(f"{signal.title} from {signal.source}")
```

### Fetch Single RSS Feed

```python
from sources.feeds import fetch_rss_feed

signals = fetch_rss_feed(
    url="https://news.ycombinator.com/rss",
    source_name="hackernews",
    max_items=50
)
```

### Fetch Google Trends

```python
from sources.feeds import fetch_google_trends

signals = fetch_google_trends(
    geo="US",           # Country code or "" for global
    timeframe="now 1-d", # now 1-d, today 5-y, etc.
    max_trends=20
)
```

### Integration with Prognosticator Pipeline

```python
from forecasting.trending_feeds_integration import fetch_and_integrate_trending_feeds

# Fetch and insert into database
inserted_count = fetch_and_integrate_trending_feeds(
    config_path="config/feeds.yaml",
    db_path="data/live.db"
)

print(f"Inserted {inserted_count} new articles")
```

### Command-Line Integration

```bash
# Fetch and integrate trending feeds
python src/forecasting/trending_feeds_integration.py

# With custom paths
python src/forecasting/trending_feeds_integration.py \
    --config config/feeds.yaml \
    --db data/live.db

# View statistics
python src/forecasting/trending_feeds_integration.py --stats
```

## API Reference

### Core Functions

#### `fetch_rss_feed(url, source_name, max_items=50)`
Fetch and normalize RSS/Atom feed into Signal objects.

**Args:**
- `url`: RSS/Atom feed URL
- `source_name`: Human-readable source identifier
- `max_items`: Maximum number of items to fetch

**Returns:** List of Signal objects

**Raises:** 
- `ImportError`: If feedparser is not installed
- `Exception`: If feed fetch or parse fails

#### `fetch_google_trends(geo="US", timeframe="now 1-d", max_trends=20)`
Fetch trending topics from Google Trends using pytrends API.

**Args:**
- `geo`: Geographic region code (e.g., "US", "GB", "")
- `timeframe`: Trend timeframe ("now 1-d", "today 5-y", etc.)
- `max_trends`: Maximum number of trends to return

**Returns:** List of Signal objects

**Raises:**
- `ImportError`: If pytrends is not installed
- `Exception`: If API request fails

#### `fetch_exploding_topics(category="technology", max_topics=20)`
Scrape emerging topics from Exploding Topics.

**Args:**
- `category`: Topic category ("technology", "business", "health", etc.)
- `max_topics`: Maximum number of topics to scrape

**Returns:** List of Signal objects

**Raises:**
- `ImportError`: If requests or beautifulsoup4 not installed
- `Exception`: If scraping fails

#### `fetch_all_trending_feeds(config=None)`
Fetch all enabled trending feeds based on configuration.

**Args:**
- `config`: Configuration dictionary (if None, loads from default location)

**Returns:** Aggregated list of Signal objects from all sources

#### `load_feeds_config(config_path="config/feeds.yaml")`
Load trending feeds configuration from YAML file.

**Args:**
- `config_path`: Path to YAML configuration file

**Returns:** Configuration dictionary

### Integration Functions

#### `signals_to_articles(signals)`
Convert Signal objects to article format for Prognosticator ingestion.

**Args:**
- `signals`: List of Signal objects

**Returns:** List of article dictionaries ready for pipeline ingestion

#### `fetch_and_integrate_trending_feeds(config_path, db_path)`
Fetch trending feeds and integrate into Prognosticator database.

**Args:**
- `config_path`: Path to feeds configuration YAML
- `db_path`: Path to SQLite database

**Returns:** Number of new articles inserted

## Error Handling

The module implements graceful error handling:

- **Failed feeds**: Logged and skipped; other feeds continue processing
- **Parse errors**: Individual entries skipped with warnings
- **Missing dependencies**: Clear error messages with installation instructions
- **Network timeouts**: Configurable retries and backoff

All errors are logged for debugging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Performance Considerations

### Rate Limiting

Google Trends queries include built-in rate limiting:
- 0.5s delay between trend detail queries
- Retry logic with exponential backoff
- Configurable timeouts

### Caching

Consider implementing caching for expensive operations:

```python
# Example: Cache Google Trends for 15 minutes
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def cached_fetch_google_trends(geo, timeframe):
    return fetch_google_trends(geo, timeframe)
```

### Deduplication

The integration layer uses Prognosticator's existing deduplication:
- Content hashing (SHA256 of title + summary)
- Fuzzy title matching (90% similarity threshold)
- Source URL tracking

## Testing

### Run Demo Script
```bash
python scripts/demo_trending_feeds.py
```

### Run Integration Test
```bash
# Dry run (fetch only, no database insert)
python -c "
from sources.feeds import fetch_all_trending_feeds
signals = fetch_all_trending_feeds()
print(f'Fetched {len(signals)} signals')
"
```

### Verify Configuration
```bash
python -c "
from sources.feeds import load_feeds_config
config = load_feeds_config('config/feeds.yaml')
print(config)
"
```

## Extending the Module

### Adding New RSS Feeds

Edit `config/feeds.yaml`:

```yaml
rss_feeds:
  - name: my_new_feed
    url: https://example.com/rss
    enabled: true
    max_items: 50
    description: "My custom feed"
```

### Adding New Scrapers

1. Implement scraper function in `sources/feeds.py`:

```python
def fetch_my_custom_source() -> List[Signal]:
    """Scrape custom source."""
    # Implementation here
    pass
```

2. Add to configuration in `config/feeds.yaml`:

```yaml
scrapers:
  my_custom_source:
    enabled: true
    setting1: value1
```

3. Integrate in `fetch_all_trending_feeds()`:

```python
custom_cfg = scrapers.get('my_custom_source', {})
if custom_cfg.get('enabled', False):
    signals = fetch_my_custom_source()
    all_signals.extend(signals)
```

## Troubleshooting

### Issue: "No module named 'feedparser'"
**Solution:** Install dependencies
```bash
pip install feedparser
```

### Issue: "No signals fetched from feed"
**Solution:** 
1. Check feed URL is accessible: `curl -I <feed_url>`
2. Verify feed format: `curl <feed_url> | head -20`
3. Check logs for parsing warnings
4. Try increasing `max_items` in config

### Issue: "pytrends API blocks requests"
**Solution:**
1. Reduce `max_trends` in config
2. Increase delay between requests
3. Use rotating proxies (advanced)
4. Disable Google Trends temporarily

### Issue: "Exploding Topics scraper returns empty"
**Solution:**
Site structure may have changed. Check:
1. Visit https://explodingtopics.com manually
2. Inspect HTML structure
3. Update selectors in `fetch_exploding_topics()`
4. Consider disabling scraper if unreliable

## Best Practices

1. **Start with RSS feeds**: More reliable than scrapers
2. **Enable rate limiting**: Avoid API/site blocks
3. **Monitor logs**: Watch for parsing warnings
4. **Regular config reviews**: Disable broken feeds
5. **Cache aggressively**: Reduce redundant fetches
6. **Test individually**: Debug sources one at a time
7. **Document changes**: Comment custom configurations

## License

Same as Prognosticator main project.

## Contributing

When adding new sources:
1. Follow existing patterns in `sources/feeds.py`
2. Include comprehensive docstrings
3. Handle errors gracefully
4. Add to default config
5. Update this documentation
6. Test thoroughly before committing

## Support

For issues or questions:
- GitHub Issues: https://github.com/raphpunk/prognosticator/issues
- Check logs with `logging.basicConfig(level=logging.DEBUG)`
- Review demo script for examples
