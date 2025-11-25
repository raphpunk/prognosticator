#!/usr/bin/env python3
"""
Database Initialization and Migration
Ensures all required tables exist and schema is current.
Run on every application startup.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database initialization and migrations."""
    
    def __init__(self, db_path: str = "data/live.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_table_columns(self, cursor, table_name: str) -> List[str]:
        """Get a list of columns for a given table."""
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]

    def _migrate_articles_table(self, cursor):
        """Apply migrations to the articles table."""
        logger.info("Checking for articles table migrations...")
        columns = self._get_table_columns(cursor, "articles")
        
        if "country_mentioned" not in columns:
            try:
                logger.info("Adding 'country_mentioned' column to 'articles' table.")
                cursor.execute("ALTER TABLE articles ADD COLUMN country_mentioned TEXT;")
                logger.info("✅ Column 'country_mentioned' added.")
            except sqlite3.OperationalError as e:
                logger.error(f"Could not add 'country_mentioned' column: {e}")
        else:
            logger.info("Articles table schema is up to date.")

    def _execute_script(self, script: str):
        """Execute SQL script safely."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for statement in script.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as e:
                    # Table may already exist
                    if "already exists" not in str(e):
                        logger.error(f"SQL Error: {e}")
        
        # Apply migrations after ensuring table exists
        if "CREATE TABLE IF NOT EXISTS articles" in script:
            self._migrate_articles_table(cursor)

        conn.commit()
        conn.close()
    
    def init_articles_table(self):
        """Initialize articles table."""
        schema = """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT,
            source_url TEXT NOT NULL,
            article_url TEXT UNIQUE,
            image_url TEXT,
            published TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relevance_score REAL DEFAULT 0.5,
            bias_score REAL DEFAULT 0.0,
            country_mentioned TEXT,
            region_mentioned TEXT,
            key_entities TEXT,
            sentiment REAL,
            indexed BOOLEAN DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_url);
        CREATE INDEX IF NOT EXISTS idx_articles_country ON articles(country_mentioned);
        """
        self._execute_script(schema)
        logger.info("✅ Articles table initialized")
    
    def init_predictions_table(self):
        """Initialize predictions table."""
        schema = """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario TEXT NOT NULL,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            probability REAL,
            confidence REAL,
            agents_count INTEGER,
            context_article_ids TEXT,
            result TEXT,
            verdict TEXT,
            reasoning TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date DESC);
        """
        self._execute_script(schema)
        logger.info("✅ Predictions table initialized")
    
    def init_agents_table(self):
        """Initialize agents/experts table."""
        schema = """
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            domain TEXT,
            expertise_level REAL DEFAULT 0.5,
            reputation_score REAL DEFAULT 0.0,
            prediction_accuracy REAL DEFAULT 0.0,
            enabled BOOLEAN DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self._execute_script(schema)
        logger.info("✅ Agents table initialized")
    
    def init_cache_table(self):
        """Initialize cache table for feed/model results."""
        schema = """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
        """
        self._execute_script(schema)
        logger.info("✅ Cache table initialized")
    
    def init_feed_health_table(self):
        """Initialize feed health tracking table."""
        schema = """
        CREATE TABLE IF NOT EXISTS feed_health (
            feed_id INTEGER PRIMARY KEY,
            feed_name TEXT UNIQUE,
            last_fetch TIMESTAMP,
            fetch_error TEXT,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_fetch_time REAL DEFAULT 0.0,
            article_count INTEGER DEFAULT 0,
            health_score REAL DEFAULT 1.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self._execute_script(schema)
        logger.info("✅ Feed health table initialized")
    
    def init_local_threats_table(self):
        """Initialize local threats monitoring table."""
        schema = """
        CREATE TABLE IF NOT EXISTS local_threat_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            jurisdiction TEXT,
            event_type TEXT,
            severity INTEGER,
            title TEXT,
            description TEXT,
            url TEXT,
            published TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            longitude REAL,
            latitude REAL
        );
        CREATE INDEX IF NOT EXISTS idx_threats_zip ON local_threat_events(zip_code);
        CREATE INDEX IF NOT EXISTS idx_threats_jurisdiction ON local_threat_events(jurisdiction);
        CREATE INDEX IF NOT EXISTS idx_threats_published ON local_threat_events(published DESC);
        """
        self._execute_script(schema)
        logger.info("✅ Local threats table initialized")
    
    def init_analysis_results_table(self):
        """Initialize analysis results table."""
        schema = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT,
            query_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result_json TEXT,
            agents_involved TEXT,
            articles_used INTEGER
        );
        """
        self._execute_script(schema)
        logger.info("✅ Analysis results table initialized")
    
    def verify_schema_version(self) -> Tuple[bool, str]:
        """Verify database schema is current."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for required tables
            required_tables = [
                "articles",
                "predictions",
                "agents",
                "cache",
                "feed_health",
                "local_threat_events",
                "analysis_results"
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            conn.close()
            
            if missing_tables:
                return False, f"Missing tables: {', '.join(missing_tables)}"
            
            return True, "Schema is current"
        except Exception as e:
            return False, str(e)
    
    def initialize(self) -> bool:
        """Run complete database initialization."""
        logger.info(f"Initializing database at {self.db_path}")
        
        try:
            self.init_articles_table()
            self.init_predictions_table()
            self.init_agents_table()
            self.init_cache_table()
            self.init_feed_health_table()
            self.init_local_threats_table()
            self.init_analysis_results_table()
            
            is_valid, msg = self.verify_schema_version()
            logger.info(f"Schema verification: {msg}")
            
            return is_valid
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache WHERE expires_at < datetime('now')")
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")


class DataRetentionManager:
    """Manages data retention and archival policies."""
    
    def __init__(self, db_path: str = "data/live.db"):
        self.db_path = Path(db_path)
    
    def archive_old_articles(self, days: int = 90) -> int:
        """Archive articles older than specified days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Could move to archive database
        cursor.execute(f"""
            DELETE FROM articles 
            WHERE published < date('now', '-{days} days')
        """)
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Archived {deleted} articles older than {days} days")
        return deleted
    
    def prune_old_predictions(self, days: int = 180) -> int:
        """Remove old prediction entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM predictions 
            WHERE prediction_date < date('now', '-{days} days')
        """)
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            tables = [
                "articles", "predictions", "agents", 
                "local_threat_events", "analysis_results"
            ]
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except:
                    stats[table] = 0
            
            # Get database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            stats["size_mb"] = db_size / (1024 * 1024)
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Could not get database stats: {e}")
            return {}


def ensure_database_ready():
    """Ensure database is initialized and ready."""
    manager = DatabaseManager()
    
    if not manager.initialize():
        logger.error("Failed to initialize database!")
        return False
    
    # Verify schema
    is_valid, msg = manager.verify_schema_version()
    if not is_valid:
        logger.error(f"Schema verification failed: {msg}")
        return False
    
    # Clean up expired cache
    manager.cleanup_expired_cache()
    
    logger.info("✅ Database ready")
    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if ensure_database_ready():
        retention = DataRetentionManager()
        stats = retention.get_database_stats()
        print("Database Statistics:")
        for table, count in stats.items():
            print(f"  {table}: {count:,}" if isinstance(count, int) else f"  {table}: {count:.1f}")
