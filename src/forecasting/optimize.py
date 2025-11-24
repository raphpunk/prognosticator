"""Performance optimization: DB indexes, query caching, optimized dedup."""
import sqlite3
from functools import lru_cache


def create_db_indexes(path: str):
    """Create indexes on frequently-queried columns for performance."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_source_url ON articles(source_url)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ingest_log_content_hash ON ingest_log(content_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ingest_log_title ON ingest_log(title)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_extracted_article_id ON extracted(article_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_feed_state_domain ON feed_state(domain)")
        conn.commit()
        print("✓ Indexes created")
    except Exception as e:
        print(f"Index creation warning: {e}")
    conn.close()


@lru_cache(maxsize=128)
def get_ingest_log_titles_cached(db_path: str):
    """Cache ingest_log titles for fuzzy matching (cleared between runs)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT title FROM ingest_log WHERE title IS NOT NULL")
    titles = [t[0] for t in cur.fetchall()]
    conn.close()
    return tuple(titles)


def optimize_db(path: str):
    """Run VACUUM and ANALYZE to optimize DB."""
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("VACUUM")
        cur.execute("ANALYZE")
        conn.commit()
        conn.close()
        print("✓ DB optimized (VACUUM + ANALYZE)")
    except Exception as e:
        print(f"Optimize warning: {e}")


if __name__ == "__main__":
    create_db_indexes("data/live.db")
    optimize_db("data/live.db")
