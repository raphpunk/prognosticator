#!/usr/bin/env python3
"""
Configuration Management for Prognosticator
Unified configuration system that consolidates feeds.json, feeds.yaml, and model_config.json
into a single prognosticator.json with full SQLite persistence.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UnifiedConfigManager:
    """Manages all application configuration in SQLite and JSON."""
    
    def __init__(self, db_path: str = "data/config.db", json_path: str = "prognosticator.json"):
        self.db_path = Path(db_path)
        self.json_path = Path(json_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize configuration database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            type TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_sections (
            section TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            active BOOLEAN DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fetch_error TEXT,
            last_fetch TIMESTAMP,
            article_count INTEGER DEFAULT 0
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_config (
            name TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def migrate_from_legacy(self):
        """Migrate configuration from legacy feeds.json, feeds.yaml, and model_config.json."""
        logger.info("Checking for legacy configuration files to migrate...")
        
        # Migrate feeds.json
        feeds_json = Path("feeds.json")
        if feeds_json.exists():
            try:
                with open(feeds_json) as f:
                    feeds_data = json.load(f)
                self.set_section("feeds", feeds_data)
                logger.info(f"✅ Migrated feeds.json")
            except Exception as e:
                logger.error(f"Failed to migrate feeds.json: {e}")
        
        # Migrate model_config.json
        model_json = Path("config/model_config.json")
        if model_json.exists():
            try:
                with open(model_json) as f:
                    model_data = json.load(f)
                self.set_section("model_config", model_data)
                logger.info(f"✅ Migrated model_config.json")
            except Exception as e:
                logger.error(f"Failed to migrate model_config.json: {e}")
        
        # Migrate feeds.yaml (if using pyyaml)
        feeds_yaml = Path("config/feeds.yaml")
        if feeds_yaml.exists():
            try:
                import yaml
                with open(feeds_yaml) as f:
                    feeds_data = yaml.safe_load(f)
                if feeds_data:
                    self.set_section("trending_feeds", feeds_data)
                    logger.info(f"✅ Migrated feeds.yaml")
            except Exception as e:
                logger.error(f"Failed to migrate feeds.yaml: {e}")
    
    def set_value(self, key: str, value: Any, type_: str = "string", description: str = ""):
        """Set a single configuration value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value, type, description)
            VALUES (?, ?, ?, ?)
        """, (key, value_str, type_, description))
        
        conn.commit()
        conn.close()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a single configuration value."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value, type FROM config WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                value, type_ = result
                if type_ in ["json", "dict", "list"]:
                    return json.loads(value)
                return value
            return default
        except Exception as e:
            logger.error(f"Error getting config value {key}: {e}")
            return default
    
    def set_section(self, section: str, data: Dict[str, Any]):
        """Set an entire configuration section."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data_str = json.dumps(data, indent=2)
        
        cursor.execute("""
            INSERT OR REPLACE INTO config_sections (section, data)
            VALUES (?, ?)
        """, (section, data_str))
        
        conn.commit()
        conn.close()
    
    def get_section(self, section: str, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Get an entire configuration section."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM config_sections WHERE section = ?", (section,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return default or {}
        except Exception as e:
            logger.error(f"Error getting config section {section}: {e}")
            return default or {}
    
    def list_sections(self) -> List[str]:
        """List all configuration sections."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT section FROM config_sections")
        sections = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sections
    
    def add_rss_feed(self, name: str, url: str, active: bool = True) -> bool:
        """Add an RSS feed to configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO rss_feeds (name, url, active)
                VALUES (?, ?, ?)
            """, (name, url, active))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"RSS feed '{name}' already exists")
            return False
    
    def get_rss_feeds(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get configured RSS feeds."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("SELECT * FROM rss_feeds WHERE active = 1")
        else:
            cursor.execute("SELECT * FROM rss_feeds")
        
        rows = cursor.fetchall()
        conn.close()
        
        feeds = []
        for row in rows:
            feeds.append({
                "id": row[0],
                "name": row[1],
                "url": row[2],
                "active": row[3],
                "added_at": row[4],
                "fetch_error": row[5],
                "last_fetch": row[6],
                "article_count": row[7],
            })
        return feeds
    
    def update_rss_feed_status(self, feed_name: str, active: bool):
        """Enable/disable an RSS feed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE rss_feeds SET active = ? WHERE name = ?
        """, (active, feed_name))
        
        conn.commit()
        conn.close()
    
    def save_to_json(self) -> bool:
        """Export entire configuration to JSON file."""
        try:
            config = {
                "exported_at": datetime.now().isoformat(),
                "sections": {},
            }
            
            # Export sections
            for section in self.list_sections():
                config["sections"][section] = self.get_section(section)
            
            # Export RSS feeds
            config["rss_feeds"] = self.get_rss_feeds(active_only=False)
            
            with open(self.json_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Configuration exported to {self.json_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def load_from_json(self) -> bool:
        """Import configuration from JSON file."""
        try:
            if not self.json_path.exists():
                return False
            
            with open(self.json_path) as f:
                config = json.load(f)
            
            # Import sections
            for section, data in config.get("sections", {}).items():
                self.set_section(section, data)
            
            logger.info(f"Configuration imported from {self.json_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False


def initialize_config_system():
    """Initialize and set up the unified configuration system."""
    manager = UnifiedConfigManager()
    
    # Migrate legacy configuration
    manager.migrate_from_legacy()
    
    # Ensure default configuration exists
    default_config = {
        "app": {
            "name": "Prognosticator",
            "version": "2.0",
            "theme": "dark",
        },
        "ollama": {
            "host": "http://localhost",
            "port": 11434,
        },
        "feeds": {
            "rss": [
                {
                    "name": "BBC World",
                    "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
                    "active": True
                },
                {
                    "name": "NYT World",
                    "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                    "active": True
                },
                {
                    "name": "Reuters",
                    "url": "https://www.reutersagency.com/feed/?best-topics=world",
                    "active": True
                },
                {
                    "name": "Al Jazeera",
                    "url": "https://www.aljazeera.com/xml/rss/all.xml",
                    "active": True
                },
                {
                    "name": "Guardian",
                    "url": "https://www.theguardian.com/world/rss",
                    "active": True
                },
                {
                    "name": "CNN",
                    "url": "https://rss.cnn.com/rss/edition_world.rss",
                    "active": True
                },
            ]
        },
        "local_threats": {
            "enabled": True,
            "min_severity": 3,
        }
    }
    
    # Set defaults if not present
    if not manager.get_section("app"):
        manager.set_section("app", default_config["app"])
    
    if not manager.get_section("ollama"):
        manager.set_section("ollama", default_config["ollama"])
    
    if not manager.get_section("feeds"):
        manager.set_section("feeds", default_config["feeds"])
    
    if not manager.get_section("local_threats"):
        manager.set_section("local_threats", default_config["local_threats"])
    
    return manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = initialize_config_system()
    
    print("✅ Configuration system initialized")
    print(f"Sections: {manager.list_sections()}")
    print(f"RSS Feeds: {len(manager.get_rss_feeds())}")
