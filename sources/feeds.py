"""Trending feeds source module for Prognosticator.

This module provides unified ingestion for both RSS feeds and scraped trending sources.
All feeds are normalized into Prognosticator's Signal schema for downstream processing.

Signal Schema:
    - source: str (feed identifier)
    - title: str (headline/topic)
    - link: str (URL to content)
    - timestamp: str (ISO 8601 format)
    - summary: str (description/snippet)
    - metadata: dict (optional extra fields)

Supported Sources:
    RSS Feeds:
        - Trend Hunter (emerging trends)
        - Hacker News (tech/startup trends)
        - Reddit /r/worldnews (social trends)
        - Product Hunt (product trends)
        - MarketWatch (financial trends)
    
    Scraped Feeds:
        - Google Trends (via pytrends API)
        - Exploding Topics (via web scraping)

Usage:
    from sources.feeds import fetch_all_trending_feeds, load_feeds_config
    
    # Load configuration
    config = load_feeds_config("config/feeds.yaml")
    
    # Fetch all configured feeds
    signals = fetch_all_trending_feeds(config)
    
    # Process signals
    for signal in signals:
        print(f"{signal['title']} from {signal['source']}")
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Normalized signal format for Prognosticator pipeline.
    
    Attributes:
        source: Feed identifier (e.g., "trend_hunter_rss", "google_trends")
        title: Headline or topic name
        link: URL to original content
        timestamp: ISO 8601 timestamp string
        summary: Description or snippet text
        signal_id: Unique identifier (auto-generated hash)
        metadata: Additional source-specific fields
    """
    source: str
    title: str
    link: str
    timestamp: str
    summary: str
    signal_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Generate signal_id if not provided."""
        if self.signal_id is None:
            # Create deterministic ID from source + title + link
            id_str = f"{self.source}:{self.title}:{self.link}".encode('utf-8')
            self.signal_id = hashlib.sha256(id_str).hexdigest()[:16]


# ============================================================================
# RSS Feed Ingestion
# ============================================================================

def fetch_rss_feed(url: str, source_name: str, max_items: int = 50) -> List[Signal]:
    """Fetch and normalize RSS/Atom feed into Signal objects.
    
    Uses feedparser to parse standard RSS/Atom feeds and converts entries
    into Prognosticator's Signal format. Handles missing fields gracefully.
    
    Args:
        url: RSS/Atom feed URL
        source_name: Human-readable source identifier
        max_items: Maximum number of items to fetch
        
    Returns:
        List of Signal objects
        
    Raises:
        ImportError: If feedparser is not installed
        Exception: If feed fetch or parse fails
    """
    try:
        import feedparser
    except ImportError as e:
        logger.error("feedparser not installed. Run: pip install feedparser")
        raise ImportError("feedparser required for RSS ingestion") from e
    
    try:
        logger.info(f"Fetching RSS feed: {source_name} ({url})")
        feed = feedparser.parse(url)
        
        if feed.bozo:  # feedparser encountered parsing issues
            logger.warning(f"Feed parsing warning for {source_name}: {feed.bozo_exception}")
        
        signals = []
        for entry in feed.entries[:max_items]:
            try:
                # Extract timestamp (try multiple fields)
                timestamp_raw = (
                    getattr(entry, 'published', None) or
                    getattr(entry, 'updated', None) or
                    getattr(entry, 'created', None)
                )
                
                # Parse and normalize timestamp to ISO format
                if timestamp_raw:
                    try:
                        # feedparser provides struct_time
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            dt = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            dt = datetime(*entry.updated_parsed[:6])
                        else:
                            # Fallback to current time
                            dt = datetime.utcnow()
                        timestamp = dt.isoformat() + 'Z'
                    except Exception:
                        timestamp = datetime.utcnow().isoformat() + 'Z'
                else:
                    timestamp = datetime.utcnow().isoformat() + 'Z'
                
                # Extract core fields with fallbacks
                title = entry.get('title', 'Untitled')
                link = entry.get('link', entry.get('id', ''))
                summary = entry.get('summary', entry.get('description', ''))
                
                # Collect metadata
                metadata = {
                    'author': entry.get('author', ''),
                    'tags': [tag.term for tag in entry.get('tags', [])],
                    'raw_published': timestamp_raw,
                }
                
                signal = Signal(
                    source=source_name,
                    title=title,
                    link=link,
                    timestamp=timestamp,
                    summary=summary,
                    metadata=metadata
                )
                
                signals.append(signal)
                
            except Exception as e:
                logger.warning(f"Failed to parse entry from {source_name}: {e}")
                continue
        
        logger.info(f"✓ Fetched {len(signals)} signals from {source_name}")
        return signals
        
    except Exception as e:
        logger.error(f"✗ Failed to fetch RSS feed {source_name}: {e}")
        return []


# ============================================================================
# Google Trends Scraper
# ============================================================================

def fetch_google_trends(
    geo: str = "US",
    timeframe: str = "now 1-d",
    max_trends: int = 20
) -> List[Signal]:
    """Fetch trending topics from Google Trends using pytrends API.
    
    Uses the unofficial pytrends library to query Google's trending searches
    and converts them into Signal format. Each trend includes search volume
    and related metadata.
    
    Args:
        geo: Geographic region code (e.g., "US", "GB", "")
        timeframe: Trend timeframe ("now 1-d", "today 5-y", etc.)
        max_trends: Maximum number of trends to return
        
    Returns:
        List of Signal objects for trending topics
        
    Raises:
        ImportError: If pytrends is not installed
        Exception: If API request fails
    """
    try:
        from pytrends.request import TrendReq
    except ImportError as e:
        logger.error("pytrends not installed. Run: pip install pytrends")
        raise ImportError("pytrends required for Google Trends scraping") from e
    
    try:
        logger.info(f"Fetching Google Trends (geo={geo}, timeframe={timeframe})")
        
        # Initialize pytrends with retry logic
        pytrends = TrendReq(hl='en-US', tz=0, timeout=(10, 25), retries=2, backoff_factor=0.5)
        
        # Fetch trending searches
        trending = pytrends.trending_searches(pn=geo)
        
        signals = []
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        for idx, trend in enumerate(trending[0][:max_trends]):
            # For each trend, get detailed interest data
            try:
                # Query interest over time for this specific trend
                pytrends.build_payload([trend], cat=0, timeframe=timeframe, geo=geo)
                interest_df = pytrends.interest_over_time()
                
                # Calculate metadata
                if not interest_df.empty and trend in interest_df.columns:
                    avg_interest = int(interest_df[trend].mean())
                    max_interest = int(interest_df[trend].max())
                    trend_direction = "rising" if interest_df[trend].iloc[-1] > interest_df[trend].iloc[0] else "falling"
                else:
                    avg_interest = 0
                    max_interest = 0
                    trend_direction = "unknown"
                
                # Related queries for context
                try:
                    related_queries = pytrends.related_queries()
                    top_queries = related_queries.get(trend, {}).get('top', None)
                    rising_queries = related_queries.get(trend, {}).get('rising', None)
                    
                    related_topics = []
                    if top_queries is not None and not top_queries.empty:
                        related_topics.extend(top_queries['query'].head(3).tolist())
                    
                except Exception:
                    related_topics = []
                
                # Create signal
                signal = Signal(
                    source="google_trends",
                    title=trend,
                    link=f"https://trends.google.com/trends/explore?q={trend}&geo={geo}",
                    timestamp=timestamp,
                    summary=f"Trending search term (rank #{idx+1}). Average interest: {avg_interest}/100. Direction: {trend_direction}.",
                    metadata={
                        'rank': idx + 1,
                        'geo': geo,
                        'avg_interest': avg_interest,
                        'max_interest': max_interest,
                        'trend_direction': trend_direction,
                        'related_topics': related_topics,
                        'timeframe': timeframe,
                    }
                )
                
                signals.append(signal)
                
                # Rate limiting to avoid API blocks
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to fetch details for trend '{trend}': {e}")
                # Create basic signal without detailed metadata
                signal = Signal(
                    source="google_trends",
                    title=trend,
                    link=f"https://trends.google.com/trends/explore?q={trend}&geo={geo}",
                    timestamp=timestamp,
                    summary=f"Trending search term (rank #{idx+1})",
                    metadata={'rank': idx + 1, 'geo': geo}
                )
                signals.append(signal)
                continue
        
        logger.info(f"✓ Fetched {len(signals)} Google Trends signals")
        return signals
        
    except Exception as e:
        logger.error(f"✗ Failed to fetch Google Trends: {e}")
        return []


# ============================================================================
# Exploding Topics Scraper
# ============================================================================

def fetch_exploding_topics(category: str = "technology", max_topics: int = 20) -> List[Signal]:
    """Scrape emerging topics from Exploding Topics using web scraping.
    
    Exploding Topics tracks rapidly growing search terms across categories.
    This function scrapes their public listings and converts topics into
    Signal format. Uses requests + BeautifulSoup for scraping.
    
    Args:
        category: Topic category ("technology", "business", "health", etc.)
        max_topics: Maximum number of topics to scrape
        
    Returns:
        List of Signal objects for exploding topics
        
    Raises:
        ImportError: If requests or beautifulsoup4 not installed
        Exception: If scraping fails
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        logger.error("requests and beautifulsoup4 required. Run: pip install requests beautifulsoup4")
        raise ImportError("requests and beautifulsoup4 required for scraping") from e
    
    try:
        logger.info(f"Scraping Exploding Topics (category={category})")
        
        # Exploding Topics public page (note: structure may change)
        url = f"https://explodingtopics.com/topics-{category}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Prognosticator/1.0; +https://github.com/raphpunk/prognosticator)'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        signals = []
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Parse topic cards (structure specific to Exploding Topics site)
        # NOTE: This is a simplified parser - actual site structure may vary
        topic_elements = soup.find_all('div', class_='topic-card')[:max_topics]
        
        if not topic_elements:
            # Fallback: try alternate selectors
            topic_elements = soup.select('.topic, .trending-topic, article')[:max_topics]
        
        for idx, element in enumerate(topic_elements):
            try:
                # Extract topic name
                title_elem = element.find(['h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link_elem = element.find('a', href=True)
                link = link_elem['href'] if link_elem else f"https://explodingtopics.com/search/{title.replace(' ', '-')}"
                
                # Make link absolute if relative
                if link.startswith('/'):
                    link = f"https://explodingtopics.com{link}"
                
                # Extract growth metrics if available
                growth_elem = element.find(class_=lambda x: x and 'growth' in x.lower())
                growth_text = growth_elem.get_text(strip=True) if growth_elem else ""
                
                # Extract description/summary
                desc_elem = element.find(['p', 'div'], class_=lambda x: x and any(
                    term in str(x).lower() for term in ['desc', 'summary', 'text']
                ))
                summary = desc_elem.get_text(strip=True) if desc_elem else f"Emerging topic in {category}"
                
                signal = Signal(
                    source="exploding_topics",
                    title=title,
                    link=link,
                    timestamp=timestamp,
                    summary=summary,
                    metadata={
                        'category': category,
                        'rank': idx + 1,
                        'growth': growth_text,
                        'scrape_time': timestamp,
                    }
                )
                
                signals.append(signal)
                
            except Exception as e:
                logger.warning(f"Failed to parse topic element: {e}")
                continue
        
        # If scraping found nothing, log a warning
        if not signals:
            logger.warning(f"No topics scraped from Exploding Topics. Site structure may have changed.")
        else:
            logger.info(f"✓ Scraped {len(signals)} signals from Exploding Topics")
        
        return signals
        
    except requests.RequestException as e:
        logger.error(f"✗ HTTP error fetching Exploding Topics: {e}")
        return []
    except Exception as e:
        logger.error(f"✗ Failed to scrape Exploding Topics: {e}")
        return []


# ============================================================================
# Configuration and Orchestration
# ============================================================================

def load_feeds_config(config_path: str = "config/feeds.yaml") -> Dict[str, Any]:
    """Load trending feeds configuration from YAML file.
    
    Config format (feeds.yaml):
        rss_feeds:
          - name: "trend_hunter"
            url: "https://www.trendhunter.com/rss"
            enabled: true
          - name: "hackernews_best"
            url: "https://news.ycombinator.com/rss"
            enabled: true
        
        scrapers:
          google_trends:
            enabled: true
            geo: "US"
            timeframe: "now 1-d"
            max_trends: 20
          exploding_topics:
            enabled: true
            categories: ["technology", "business"]
            max_topics: 15
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary with feed settings
    """
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed, using default config")
        return get_default_config()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"✓ Loaded feeds config from {config_path}")
        return config
        
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return get_default_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}. Using defaults.")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Return default trending feeds configuration.
    
    Provides a sensible default set of RSS feeds and scraper settings
    when no config file is available.
    
    Returns:
        Default configuration dictionary
    """
    return {
        'rss_feeds': [
            {
                'name': 'trend_hunter',
                'url': 'https://www.trendhunter.com/rss',
                'enabled': True,
            },
            {
                'name': 'hackernews_best',
                'url': 'https://news.ycombinator.com/rss',
                'enabled': True,
            },
            {
                'name': 'reddit_worldnews',
                'url': 'https://www.reddit.com/r/worldnews/.rss',
                'enabled': True,
            },
            {
                'name': 'producthunt_daily',
                'url': 'https://www.producthunt.com/feed',
                'enabled': True,
            },
            {
                'name': 'marketwatch_topstories',
                'url': 'https://feeds.marketwatch.com/marketwatch/topstories/',
                'enabled': True,
            },
        ],
        'scrapers': {
            'google_trends': {
                'enabled': True,
                'geo': 'US',
                'timeframe': 'now 1-d',
                'max_trends': 20,
            },
            'exploding_topics': {
                'enabled': False,  # Disabled by default due to scraping reliability
                'categories': ['technology'],
                'max_topics': 15,
            },
        },
    }


def fetch_all_trending_feeds(config: Optional[Dict[str, Any]] = None) -> List[Signal]:
    """Fetch all enabled trending feeds based on configuration.
    
    Orchestrates fetching from multiple RSS feeds and scrapers, aggregating
    all signals into a single list. Skips broken feeds gracefully and logs
    errors for debugging.
    
    Args:
        config: Configuration dictionary (if None, loads from default location)
        
    Returns:
        Aggregated list of Signal objects from all sources
    """
    if config is None:
        config = load_feeds_config()
    
    all_signals = []
    
    # Fetch RSS feeds
    rss_feeds = config.get('rss_feeds', [])
    for feed_cfg in rss_feeds:
        if not feed_cfg.get('enabled', True):
            logger.info(f"Skipping disabled feed: {feed_cfg['name']}")
            continue
        
        try:
            signals = fetch_rss_feed(
                url=feed_cfg['url'],
                source_name=feed_cfg['name'],
                max_items=feed_cfg.get('max_items', 50)
            )
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_cfg['name']}: {e}")
            # Continue with other feeds
            continue
    
    # Fetch Google Trends
    scrapers = config.get('scrapers', {})
    google_cfg = scrapers.get('google_trends', {})
    if google_cfg.get('enabled', False):
        try:
            signals = fetch_google_trends(
                geo=google_cfg.get('geo', 'US'),
                timeframe=google_cfg.get('timeframe', 'now 1-d'),
                max_trends=google_cfg.get('max_trends', 20)
            )
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Failed to fetch Google Trends: {e}")
    
    # Fetch Exploding Topics
    exploding_cfg = scrapers.get('exploding_topics', {})
    if exploding_cfg.get('enabled', False):
        categories = exploding_cfg.get('categories', ['technology'])
        max_topics = exploding_cfg.get('max_topics', 15)
        
        for category in categories:
            try:
                signals = fetch_exploding_topics(
                    category=category,
                    max_topics=max_topics
                )
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Failed to fetch Exploding Topics ({category}): {e}")
    
    logger.info(f"✓ Total signals collected: {len(all_signals)}")
    return all_signals


def signals_to_dict(signals: List[Signal]) -> List[Dict[str, Any]]:
    """Convert Signal objects to dictionaries for JSON serialization.
    
    Args:
        signals: List of Signal objects
        
    Returns:
        List of signal dictionaries
    """
    return [asdict(signal) for signal in signals]


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("PROGNOSTICATOR TRENDING FEEDS MODULE - DEMO")
    print("=" * 70)
    print()
    
    # Example 1: Fetch single RSS feed
    print("Example 1: Fetching Hacker News RSS feed...")
    print("-" * 70)
    try:
        hn_signals = fetch_rss_feed(
            url="https://news.ycombinator.com/rss",
            source_name="hackernews_frontpage",
            max_items=5
        )
        print(f"✓ Fetched {len(hn_signals)} signals from Hacker News\n")
        if hn_signals:
            print("Sample signal:")
            sample = hn_signals[0]
            print(f"  Title: {sample.title}")
            print(f"  Source: {sample.source}")
            print(f"  Link: {sample.link}")
            print(f"  Timestamp: {sample.timestamp}")
            print(f"  ID: {sample.signal_id}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 70)
    
    # Example 2: Fetch Google Trends
    print("Example 2: Fetching Google Trends (US)...")
    print("-" * 70)
    try:
        trend_signals = fetch_google_trends(geo="US", max_trends=5)
        print(f"✓ Fetched {len(trend_signals)} trending topics\n")
        if trend_signals:
            print("Top 3 trending topics:")
            for signal in trend_signals[:3]:
                print(f"  {signal.metadata['rank']}. {signal.title}")
                print(f"     Interest: {signal.metadata.get('avg_interest', 'N/A')}/100")
    except ImportError as e:
        print(f"⚠ Skipped (dependency missing): {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 70)
    
    # Example 3: Fetch all configured feeds
    print("Example 3: Fetching all configured trending feeds...")
    print("-" * 70)
    try:
        # Use default config
        config = get_default_config()
        all_signals = fetch_all_trending_feeds(config)
        
        print(f"✓ Total signals collected: {len(all_signals)}")
        print(f"\nBreakdown by source:")
        
        # Count by source
        source_counts = {}
        for signal in all_signals:
            source_counts[signal.source] = source_counts.get(signal.source, 0) + 1
        
        for source, count in sorted(source_counts.items()):
            print(f"  - {source}: {count} signals")
        
        # Export to JSON example
        print("\nExporting to JSON format...")
        signals_dict = signals_to_dict(all_signals)
        print(f"✓ Converted {len(signals_dict)} signals to dict format")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install feedparser pytrends beautifulsoup4 pyyaml")
    print("2. Create config/feeds.yaml with your preferred sources")
    print("3. Import and use in your Prognosticator pipeline:")
    print()
    print("   from sources.feeds import fetch_all_trending_feeds")
    print("   signals = fetch_all_trending_feeds()")
    print("   # Process signals...")
    print()
