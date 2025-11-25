"""Integration layer for trending feeds into Prognosticator pipeline.

This module bridges the sources.feeds module with the existing Prognosticator
ingestion pipeline, converting Signal objects to the expected article format.
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add sources directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = PROJECT_ROOT / "sources"
if str(SOURCES_PATH) not in sys.path:
    sys.path.insert(0, str(SOURCES_PATH))

logger = logging.getLogger(__name__)


def signals_to_articles(signals: List[Any]) -> List[Dict[str, Any]]:
    """Convert Signal objects to article format for Prognosticator ingestion.
    
    Transforms the Signal schema into the article schema expected by
    the existing storage and processing pipeline.
    
    Signal Schema:
        - source: str
        - title: str
        - link: str
        - timestamp: str (ISO 8601)
        - summary: str
        - signal_id: str
        - metadata: dict
    
    Article Schema (for storage.insert_articles):
        - id: str
        - title: str
        - text: str (content)
        - published: str (ISO timestamp)
        - source_url: str
        - fetched_from: str (feed identifier)
        - summary: str
        - raw: dict (original signal data)
    
    Args:
        signals: List of Signal objects from sources.feeds
        
    Returns:
        List of article dictionaries ready for pipeline ingestion
    """
    articles = []
    
    for signal in signals:
        try:
            # Handle both Signal objects and dicts
            if hasattr(signal, '__dict__'):
                signal_dict = signal.__dict__
            else:
                signal_dict = signal
            
            article = {
                "id": signal_dict.get('signal_id', signal_dict.get('link', '')),
                "title": signal_dict.get('title', ''),
                "text": signal_dict.get('summary', ''),  # Use summary as text content
                "published": signal_dict.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                "source_url": signal_dict.get('link', ''),
                "fetched_from": signal_dict.get('source', 'unknown'),
                "summary": signal_dict.get('summary', ''),
                "raw": signal_dict,  # Preserve original signal data
            }
            
            articles.append(article)
            
        except Exception as e:
            logger.warning(f"Failed to convert signal to article: {e}")
            continue
    
    return articles


def fetch_and_integrate_trending_feeds(
    config_path: str = "config/feeds.yaml",
    db_path: str = "data/live.db"
) -> int:
    """Fetch trending feeds and integrate into Prognosticator database.
    
    This is the main entry point for adding trending feeds to the pipeline.
    It fetches all configured feeds, converts them to article format, and
    inserts them into the database with deduplication.
    
    Args:
        config_path: Path to feeds configuration YAML
        db_path: Path to SQLite database
        
    Returns:
        Number of new articles inserted
    """
    try:
        # Import trending feeds module
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'sources'))
        from feeds import fetch_all_trending_feeds, load_feeds_config
        
        # Load configuration and fetch feeds
        logger.info("Loading trending feeds configuration...")
        config = load_feeds_config(config_path)
        
        logger.info("Fetching all trending feeds...")
        signals = fetch_all_trending_feeds(config)
        
        if not signals:
            logger.warning("No signals fetched from trending feeds")
            return 0
        
        logger.info(f"Converting {len(signals)} signals to article format...")
        articles = signals_to_articles(signals)
        
        # Insert into database using existing storage module
        try:
            from forecasting.storage import insert_articles
            
            logger.info(f"Inserting {len(articles)} articles into database...")
            inserted_count = insert_articles(db_path, articles)
            
            logger.info(f"✓ Successfully inserted {inserted_count} new trending articles")
            return inserted_count
            
        except ImportError:
            logger.error("forecasting.storage module not available")
            logger.info("Articles converted but not inserted. Use storage.insert_articles() manually.")
            return 0
            
    except ImportError as e:
        logger.error(f"Failed to import trending feeds module: {e}")
        logger.info("Ensure sources/feeds.py is available and dependencies are installed")
        return 0
    except Exception as e:
        logger.error(f"Error integrating trending feeds: {e}")
        return 0


def get_trending_feed_stats(db_path: str = "data/live.db") -> Dict[str, int]:
    """Get statistics on trending feed ingestion.
    
    Queries the database to count articles by trending feed source.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Dictionary mapping feed source to article count
    """
    try:
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query article counts by trending feed sources
        trending_sources = [
            'trend_hunter',
            'hackernews_best',
            'reddit_worldnews',
            'producthunt_daily',
            'marketwatch_topstories',
            'google_trends',
            'exploding_topics',
        ]
        
        stats = {}
        for source in trending_sources:
            cursor.execute(
                "SELECT COUNT(*) FROM articles WHERE fetched_from = ?",
                (source,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                stats[source] = count
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get trending feed stats: {e}")
        return {}


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(
        description="Integrate trending feeds into Prognosticator pipeline"
    )
    parser.add_argument(
        "--config",
        default="config/feeds.yaml",
        help="Path to feeds configuration YAML"
    )
    parser.add_argument(
        "--db",
        default="data/live.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show trending feed statistics instead of fetching"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("PROGNOSTICATOR TRENDING FEEDS INTEGRATION")
    print("=" * 70)
    print()
    
    if args.stats:
        # Show statistics
        print("Fetching trending feed statistics...")
        print("-" * 70)
        stats = get_trending_feed_stats(args.db)
        
        if stats:
            print("Articles by trending feed source:")
            total = 0
            for source, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                print(f"  {source:30} {count:6,} articles")
                total += count
            print("-" * 70)
            print(f"  {'TOTAL':30} {total:6,} articles")
        else:
            print("No trending feed articles found in database")
    else:
        # Fetch and integrate feeds
        print(f"Configuration: {args.config}")
        print(f"Database: {args.db}")
        print()
        
        inserted = fetch_and_integrate_trending_feeds(
            config_path=args.config,
            db_path=args.db
        )
        
        print()
        print("=" * 70)
        if inserted > 0:
            print(f"✓ SUCCESS: Inserted {inserted} new trending articles")
        else:
            print("⚠ No new articles inserted (may be duplicates or errors)")
        print("=" * 70)
