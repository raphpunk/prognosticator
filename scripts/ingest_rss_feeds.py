#!/usr/bin/env python3
"""
RSS Feed Ingestion Script

Collects articles from all configured RSS feeds in feeds.json
and stores them in the articles database.

Usage:
    python scripts/ingest_rss_feeds.py
"""

import sys
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import tagging system
from src.forecasting.article_tagging import tag_article_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def ingest_rss_feeds(feeds_config_path: str = "feeds.json", 
                     db_path: str = "data/live.db",
                     max_items_per_feed: int = 50) -> int:
    """
    Ingest RSS feeds and store in database
    
    Args:
        feeds_config_path: Path to feeds.json
        db_path: Path to SQLite database
        max_items_per_feed: Maximum articles to fetch per feed
        
    Returns:
        Number of new articles stored
    """
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return 0
    
    # Load feeds configuration
    try:
        with open(feeds_config_path, 'r') as f:
            config = json.load(f)
        feeds = config.get('feeds', [])
        logger.info(f"Loaded {len(feeds)} feeds from {feeds_config_path}")
    except Exception as e:
        logger.error(f"Failed to load feeds config: {e}")
        return 0
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure articles table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                published TEXT,
                source_url TEXT,
                content_hash TEXT UNIQUE,
                agent_tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return 0
    
    total_new = 0
    total_processed = 0
    
    for feed_config in feeds:
        url = feed_config.get('url')
        if not url:
            continue
            
        active = feed_config.get('active', True)
        if not active:
            logger.info(f"Skipping inactive feed: {url}")
            continue
        
        category = feed_config.get('category', 'unknown')
        
        try:
            logger.info(f"Fetching: {category} - {url}")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                logger.warning(f"  Parse warning for {url}: {feed.bozo_exception}")
            
            entries = feed.entries[:max_items_per_feed]
            logger.info(f"  Found {len(entries)} entries")
            
            for entry in entries:
                try:
                    # Extract article data
                    title = entry.get('title', 'Untitled')
                    
                    # Get content (try multiple fields)
                    text = ''
                    if hasattr(entry, 'content') and entry.content:
                        text = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        text = entry.summary
                    elif hasattr(entry, 'description'):
                        text = entry.description
                    
                    # Remove HTML tags (basic cleanup)
                    import re
                    text = re.sub(r'<[^>]+>', '', text)
                    text = text.strip()
                    
                    if not text:
                        continue
                    
                    # Get published date
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        from time import struct_time
                        pub_time = entry.published_parsed
                        published = datetime(*pub_time[:6]).isoformat()
                    else:
                        published = datetime.utcnow().isoformat()
                    
                    # Get source URL
                    source_url = entry.get('link', url)
                    
                    # Generate unique ID and content hash
                    article_id = hashlib.sha256(
                        f"{title}{source_url}".encode()
                    ).hexdigest()[:16]
                    
                    content_hash = hashlib.sha256(
                        f"{title}{text}".encode()
                    ).hexdigest()
                    
                    # Tag article for relevant agents
                    agent_tags = tag_article_json(title, text, source_url)
                    
                    # Insert into database (ignore duplicates)
                    cursor.execute("""
                        INSERT OR IGNORE INTO articles 
                        (id, title, text, published, source_url, content_hash, agent_tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (article_id, title, text, published, source_url, content_hash, agent_tags))
                    
                    if cursor.rowcount > 0:
                        total_new += 1
                    
                    total_processed += 1
                    
                except Exception as e:
                    logger.warning(f"  Failed to process entry: {e}")
                    continue
            
            conn.commit()
            logger.info(f"  ✓ Processed {len(entries)} entries from {category}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to fetch {url}: {e}")
            continue
    
    conn.close()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"RSS Feed Ingestion Complete")
    logger.info(f"{'='*60}")
    logger.info(f"Total processed: {total_processed}")
    logger.info(f"New articles: {total_new}")
    logger.info(f"Duplicates skipped: {total_processed - total_new}")
    
    return total_new


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest RSS feeds into database")
    parser.add_argument("--config", default="feeds.json", help="Path to feeds.json")
    parser.add_argument("--db", default="data/live.db", help="Path to database")
    parser.add_argument("--max-items", type=int, default=50, help="Max items per feed")
    
    args = parser.parse_args()
    
    new_count = ingest_rss_feeds(
        feeds_config_path=args.config,
        db_path=args.db,
        max_items_per_feed=args.max_items
    )
    
    sys.exit(0 if new_count >= 0 else 1)
