"""Feed health monitoring and anomaly detection."""
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeedHealth:
    """Health metrics for an RSS feed."""
    feed_url: str
    last_success: Optional[str]
    error_count: int
    reputation_score: float  # 0-1
    total_articles: int
    avg_article_length: float
    topic_diversity: float  # Shannon entropy of topics
    last_check: str


class FeedHealthTracker:
    """Track feed reliability and detect anomalies."""
    
    def __init__(self, db_path: str = "data/feed_health.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize feed health tracking tables."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Feed health metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_health (
                feed_url TEXT PRIMARY KEY,
                last_success TEXT,
                last_failure TEXT,
                error_count INTEGER DEFAULT 0,
                reputation_score REAL DEFAULT 0.5,
                total_articles INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Article metadata for anomaly detection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_articles (
                id TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                published TEXT NOT NULL,
                content_length INTEGER,
                topic_keywords TEXT,
                ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_url) REFERENCES feed_health(feed_url)
            )
        """)
        
        # Anomaly events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_url TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed ON feed_articles(feed_url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON feed_articles(published)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_feed ON feed_anomalies(feed_url)")
        
        conn.commit()
        conn.close()
    
    def record_success(self, feed_url: str) -> None:
        """Record successful feed fetch."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feed_health (feed_url, last_success, error_count)
            VALUES (?, ?, 0)
            ON CONFLICT(feed_url) DO UPDATE SET
                last_success = excluded.last_success,
                error_count = 0,
                updated_at = CURRENT_TIMESTAMP
        """, (feed_url, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
    
    def record_failure(self, feed_url: str, error_message: str) -> None:
        """Record failed feed fetch."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feed_health (feed_url, last_failure, error_count)
            VALUES (?, ?, 1)
            ON CONFLICT(feed_url) DO UPDATE SET
                last_failure = excluded.last_failure,
                error_count = error_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (feed_url, datetime.utcnow().isoformat()))
        
        # Log anomaly if error count is high
        cursor.execute("""
            SELECT error_count FROM feed_health WHERE feed_url = ?
        """, (feed_url,))
        
        row = cursor.fetchone()
        if row and row[0] >= 3:
            self._record_anomaly(
                cursor,
                feed_url,
                "repeated_failures",
                "high",
                f"Feed has failed {row[0]} consecutive times: {error_message}"
            )
        
        conn.commit()
        conn.close()
    
    def record_article(
        self,
        article_id: str,
        feed_url: str,
        published: str,
        content_length: int,
        topic_keywords: Optional[List[str]] = None
    ) -> None:
        """Record article ingestion for anomaly detection."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        keywords_json = ",".join(topic_keywords) if topic_keywords else ""
        
        cursor.execute("""
            INSERT OR IGNORE INTO feed_articles
            (id, feed_url, published, content_length, topic_keywords)
            VALUES (?, ?, ?, ?, ?)
        """, (article_id, feed_url, published, content_length, keywords_json))
        
        # Update total article count
        cursor.execute("""
            UPDATE feed_health
            SET total_articles = total_articles + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE feed_url = ?
        """, (feed_url,))
        
        conn.commit()
        conn.close()
    
    def check_feed_anomalies(self, feed_url: str) -> List[Dict]:
        """Detect anomalies in feed behavior.
        
        Returns:
            List of detected anomalies
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        anomalies = []
        
        # Check 1: Volume anomaly (sudden drop or spike)
        cursor.execute("""
            SELECT COUNT(*) as count, DATE(published) as date
            FROM feed_articles
            WHERE feed_url = ? AND published >= datetime('now', '-7 days')
            GROUP BY DATE(published)
            ORDER BY date DESC
        """, (feed_url,))
        
        daily_counts = [row[0] for row in cursor.fetchall()]
        if len(daily_counts) >= 3:
            avg_count = sum(daily_counts[1:]) / len(daily_counts[1:])
            recent_count = daily_counts[0]
            
            if recent_count < avg_count * 0.3:
                anomalies.append({
                    "type": "volume_drop",
                    "severity": "high",
                    "description": f"Article volume dropped to {recent_count} from average {avg_count:.0f}"
                })
                self._record_anomaly(cursor, feed_url, "volume_drop", "high", anomalies[-1]["description"])
            
            elif recent_count > avg_count * 3.0:
                anomalies.append({
                    "type": "volume_spike",
                    "severity": "medium",
                    "description": f"Article volume spiked to {recent_count} from average {avg_count:.0f}"
                })
                self._record_anomaly(cursor, feed_url, "volume_spike", "medium", anomalies[-1]["description"])
        
        # Check 2: Topic shift (sudden change in keywords)
        cursor.execute("""
            SELECT topic_keywords
            FROM feed_articles
            WHERE feed_url = ? AND published >= datetime('now', '-7 days')
            ORDER BY published DESC
            LIMIT 20
        """, (feed_url,))
        
        recent_keywords = []
        for row in cursor.fetchall():
            if row[0]:
                recent_keywords.extend(row[0].split(','))
        
        cursor.execute("""
            SELECT topic_keywords
            FROM feed_articles
            WHERE feed_url = ? 
              AND published >= datetime('now', '-14 days')
              AND published < datetime('now', '-7 days')
            ORDER BY published DESC
            LIMIT 20
        """, (feed_url,))
        
        historical_keywords = []
        for row in cursor.fetchall():
            if row[0]:
                historical_keywords.extend(row[0].split(','))
        
        if recent_keywords and historical_keywords:
            recent_topics = Counter(recent_keywords)
            historical_topics = Counter(historical_keywords)
            
            # Calculate topic overlap (Jaccard similarity)
            recent_set = set(recent_topics.keys())
            historical_set = set(historical_topics.keys())
            
            if recent_set and historical_set:
                overlap = len(recent_set & historical_set) / len(recent_set | historical_set)
                
                if overlap < 0.3:
                    anomalies.append({
                        "type": "topic_shift",
                        "severity": "medium",
                        "description": f"Topic overlap dropped to {overlap:.1%} (expected >30%)"
                    })
                    self._record_anomaly(cursor, feed_url, "topic_shift", "medium", anomalies[-1]["description"])
        
        # Check 3: Content length anomaly
        cursor.execute("""
            SELECT AVG(content_length)
            FROM feed_articles
            WHERE feed_url = ? AND published >= datetime('now', '-7 days')
        """, (feed_url,))
        
        recent_avg_length = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(content_length)
            FROM feed_articles
            WHERE feed_url = ? 
              AND published >= datetime('now', '-14 days')
              AND published < datetime('now', '-7 days')
        """, (feed_url,))
        
        historical_avg_length = cursor.fetchone()[0]
        
        if recent_avg_length and historical_avg_length:
            if recent_avg_length < historical_avg_length * 0.5:
                anomalies.append({
                    "type": "content_truncation",
                    "severity": "high",
                    "description": f"Average content length dropped to {recent_avg_length:.0f} from {historical_avg_length:.0f}"
                })
                self._record_anomaly(cursor, feed_url, "content_truncation", "high", anomalies[-1]["description"])
        
        conn.commit()
        conn.close()
        
        return anomalies
    
    def _record_anomaly(
        self,
        cursor: sqlite3.Cursor,
        feed_url: str,
        anomaly_type: str,
        severity: str,
        description: str
    ) -> None:
        """Record an anomaly event."""
        # Check if similar anomaly already exists and is unresolved
        cursor.execute("""
            SELECT id FROM feed_anomalies
            WHERE feed_url = ? 
              AND anomaly_type = ?
              AND resolved = 0
              AND detected_at >= datetime('now', '-24 hours')
        """, (feed_url, anomaly_type))
        
        if cursor.fetchone():
            return  # Don't duplicate recent unresolved anomalies
        
        cursor.execute("""
            INSERT INTO feed_anomalies
            (feed_url, anomaly_type, severity, description)
            VALUES (?, ?, ?, ?)
        """, (feed_url, anomaly_type, severity, description))
    
    def update_reputation(self, feed_url: str) -> float:
        """Calculate and update reputation score for a feed.
        
        Returns:
            Updated reputation score (0-1)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get health metrics
        cursor.execute("""
            SELECT error_count, total_articles FROM feed_health
            WHERE feed_url = ?
        """, (feed_url,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0.5
        
        error_count, total_articles = row
        
        # Base score from error rate
        error_penalty = min(error_count / 10.0, 0.5)  # Max 50% penalty
        base_score = 1.0 - error_penalty
        
        # Get anomaly count
        cursor.execute("""
            SELECT COUNT(*) FROM feed_anomalies
            WHERE feed_url = ? 
              AND resolved = 0
              AND detected_at >= datetime('now', '-7 days')
        """, (feed_url,))
        
        recent_anomalies = cursor.fetchone()[0]
        anomaly_penalty = min(recent_anomalies * 0.1, 0.3)  # Max 30% penalty
        
        # Calculate final reputation
        reputation_score = max(base_score - anomaly_penalty, 0.0)
        
        # Update database
        cursor.execute("""
            UPDATE feed_health
            SET reputation_score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE feed_url = ?
        """, (reputation_score, feed_url))
        
        conn.commit()
        conn.close()
        
        return reputation_score
    
    def get_feed_health(self, feed_url: str) -> Optional[FeedHealth]:
        """Get comprehensive health data for a feed."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_success, error_count, reputation_score, total_articles, updated_at
            FROM feed_health
            WHERE feed_url = ?
        """, (feed_url,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # Calculate average article length
        cursor.execute("""
            SELECT AVG(content_length)
            FROM feed_articles
            WHERE feed_url = ? AND published >= datetime('now', '-30 days')
        """, (feed_url,))
        
        avg_length = cursor.fetchone()[0] or 0.0
        
        # Calculate topic diversity (Shannon entropy)
        cursor.execute("""
            SELECT topic_keywords
            FROM feed_articles
            WHERE feed_url = ? AND published >= datetime('now', '-30 days')
        """, (feed_url,))
        
        all_keywords = []
        for kw_row in cursor.fetchall():
            if kw_row[0]:
                all_keywords.extend(kw_row[0].split(','))
        
        topic_diversity = self._calculate_entropy(all_keywords) if all_keywords else 0.0
        
        conn.close()
        
        return FeedHealth(
            feed_url=feed_url,
            last_success=row[0],
            error_count=row[1],
            reputation_score=row[2],
            total_articles=row[3],
            avg_article_length=avg_length,
            topic_diversity=topic_diversity,
            last_check=row[4]
        )
    
    def _calculate_entropy(self, items: List[str]) -> float:
        """Calculate Shannon entropy of item distribution."""
        import math
        counts = Counter(items)
        total = sum(counts.values())
        
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy
    
    def should_skip_feed(self, feed_url: str) -> bool:
        """Determine if feed should be skipped due to poor health.
        
        Returns:
            True if feed should be skipped
        """
        health = self.get_feed_health(feed_url)
        
        if not health:
            return False
        
        # Skip if error count too high or reputation too low
        if health.error_count > 5:
            logger.warning(f"Skipping feed {feed_url} - {health.error_count} consecutive errors")
            return True
        
        if health.reputation_score < 0.3:
            logger.warning(f"Skipping feed {feed_url} - low reputation ({health.reputation_score:.2f})")
            return True
        
        return False
