#!/usr/bin/env python3
"""
Backfill Agent Tags

Updates existing articles in database with agent tags based on content analysis.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.forecasting.article_tagging import tag_article_json


def backfill_agent_tags(db_path: str = "data/live.db", batch_size: int = 100):
    """Backfill agent tags for existing articles"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get articles without tags
    cursor.execute("""
        SELECT id, title, text, source_url
        FROM articles
        WHERE agent_tags IS NULL OR agent_tags = ''
    """)
    
    articles = cursor.fetchall()
    total = len(articles)
    
    print(f"Backfilling agent tags for {total} articles...")
    
    updated = 0
    for i, (article_id, title, text, source_url) in enumerate(articles, 1):
        try:
            # Generate tags
            agent_tags = tag_article_json(title or "", text or "", source_url or "")
            
            # Update database
            cursor.execute("""
                UPDATE articles
                SET agent_tags = ?
                WHERE id = ?
            """, (agent_tags, article_id))
            
            updated += 1
            
            if i % batch_size == 0:
                conn.commit()
                print(f"  Progress: {i}/{total} ({i/total*100:.1f}%)")
        
        except Exception as e:
            print(f"  Error tagging article {article_id}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Backfilled {updated}/{total} articles")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill agent tags for existing articles")
    parser.add_argument("--db", default="data/live.db", help="Path to database")
    parser.add_argument("--batch", type=int, default=100, help="Commit batch size")
    
    args = parser.parse_args()
    
    backfill_agent_tags(db_path=args.db, batch_size=args.batch)
