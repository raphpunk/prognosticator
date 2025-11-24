"""RSS feed verification and source reputation tracking."""
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SourceReputation:
    """Reputation metrics for a content source."""
    source_url: str
    reliability_score: float  # 0.0 - 1.0
    timeliness_score: float  # How quickly they publish breaking news
    accuracy_score: float  # Historical accuracy of content
    total_articles: int
    flagged_articles: int
    last_verified: datetime
    trust_level: str  # high, medium, low, untrusted


@dataclass
class ContentAnomaly:
    """Detected anomaly in content."""
    content_hash: str
    anomaly_type: str
    severity: str  # critical, high, medium, low
    description: str
    detected_at: datetime
    source_url: str


class FeedVerificationSystem:
    """Track source reputation and detect content anomalies."""
    
    def __init__(self, db_path: str = "data/feed_verification.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize verification database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Source reputation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_reputation (
                source_url TEXT PRIMARY KEY,
                reliability_score REAL DEFAULT 0.5,
                timeliness_score REAL DEFAULT 0.5,
                accuracy_score REAL DEFAULT 0.5,
                total_articles INTEGER DEFAULT 0,
                flagged_articles INTEGER DEFAULT 0,
                trust_level TEXT DEFAULT 'medium',
                last_verified TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Content anomalies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                source_url TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        
        # Content fingerprints for duplicate detection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_fingerprints (
                content_hash TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                seen_count INTEGER DEFAULT 1,
                content_length INTEGER,
                suspicious_patterns TEXT
            )
        """)
        
        # Source behavior patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_patterns (
                source_url TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_value TEXT NOT NULL,
                first_observed TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                PRIMARY KEY (source_url, pattern_type)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_source ON content_anomalies(source_url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON content_anomalies(severity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fingerprints_source ON content_fingerprints(source_url)")
        
        conn.commit()
        conn.close()
    
    def analyze_content(
        self,
        content: str,
        source_url: str,
        title: Optional[str] = None
    ) -> List[ContentAnomaly]:
        """Analyze content for suspicious patterns and anomalies."""
        anomalies = []
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check for duplicate/plagiarized content
        if self._is_duplicate_content(content_hash, source_url):
            anomalies.append(ContentAnomaly(
                content_hash=content_hash,
                anomaly_type="duplicate_content",
                severity="medium",
                description="Content appears to be duplicated from another source",
                detected_at=datetime.utcnow(),
                source_url=source_url
            ))
        
        # Check for sensationalist language
        if self._contains_sensationalism(content, title):
            anomalies.append(ContentAnomaly(
                content_hash=content_hash,
                anomaly_type="sensationalism",
                severity="low",
                description="Content contains sensationalist language patterns",
                detected_at=datetime.utcnow(),
                source_url=source_url
            ))
        
        # Check for coordinated messaging (same phrases across sources)
        if self._is_coordinated_messaging(content, source_url):
            anomalies.append(ContentAnomaly(
                content_hash=content_hash,
                anomaly_type="coordinated_messaging",
                severity="high",
                description="Content matches coordinated messaging patterns",
                detected_at=datetime.utcnow(),
                source_url=source_url
            ))
        
        # Check for suspicious link patterns
        if self._has_suspicious_links(content):
            anomalies.append(ContentAnomaly(
                content_hash=content_hash,
                anomaly_type="suspicious_links",
                severity="high",
                description="Content contains suspicious link patterns",
                detected_at=datetime.utcnow(),
                source_url=source_url
            ))
        
        # Check content length anomaly
        if len(content) < 100:
            anomalies.append(ContentAnomaly(
                content_hash=content_hash,
                anomaly_type="abnormal_length",
                severity="low",
                description=f"Unusually short content: {len(content)} chars",
                detected_at=datetime.utcnow(),
                source_url=source_url
            ))
        
        # Record fingerprint
        self._record_fingerprint(content_hash, source_url, len(content), anomalies)
        
        # Record anomalies
        if anomalies:
            self._record_anomalies(anomalies)
        
        return anomalies
    
    def _is_duplicate_content(self, content_hash: str, source_url: str) -> bool:
        """Check if content hash exists from different source."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_url FROM content_fingerprints
            WHERE content_hash = ? AND source_url != ?
        """, (content_hash, source_url))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def _contains_sensationalism(self, content: str, title: Optional[str]) -> bool:
        """Detect sensationalist language patterns."""
        text = (title or "") + " " + content
        text_lower = text.lower()
        
        sensationalist_patterns = [
            r'\b(shocking|outrageous|unbelievable|mind-blowing|you won\'t believe)\b',
            r'\b(everyone is talking about|viral|breaking the internet)\b',
            r'!!!+',  # Multiple exclamation marks
            r'\bALL CAPS\b.*\bALL CAPS\b',  # Excessive caps
        ]
        
        for pattern in sensationalist_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _is_coordinated_messaging(self, content: str, source_url: str) -> bool:
        """Detect coordinated messaging across sources."""
        # Extract key phrases (3+ words)
        words = content.lower().split()
        phrases = []
        
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            if len(phrase) > 15:  # Meaningful phrases only
                phrases.append(phrase)
        
        if not phrases:
            return False
        
        # Check if these exact phrases appear in recent content from other sources
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Sample check: see if any 3-word phrase appears >3 times from different sources
        for phrase in phrases[:5]:  # Check first 5 phrases
            pattern_hash = hashlib.sha256(phrase.encode()).hexdigest()[:16]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT source_url) FROM source_patterns
                WHERE pattern_type = 'phrase' 
                  AND pattern_value = ?
                  AND first_observed >= datetime('now', '-7 days')
            """, (pattern_hash,))
            
            count = cursor.fetchone()[0]
            if count >= 3:
                conn.close()
                return True
        
        conn.close()
        return False
    
    def _has_suspicious_links(self, content: str) -> bool:
        """Check for suspicious URL patterns."""
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        suspicious_indicators = [
            r'bit\.ly|tinyurl|shorturl',  # URL shorteners
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
            r'[a-z0-9]{20,}',  # Very long random strings
        ]
        
        for url in urls:
            for indicator in suspicious_indicators:
                if re.search(indicator, url, re.IGNORECASE):
                    return True
        
        return False
    
    def _record_fingerprint(
        self,
        content_hash: str,
        source_url: str,
        content_length: int,
        anomalies: List[ContentAnomaly]
    ) -> None:
        """Record content fingerprint for tracking."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        suspicious_patterns = ",".join([a.anomaly_type for a in anomalies]) if anomalies else None
        
        cursor.execute("""
            INSERT OR IGNORE INTO content_fingerprints
            (content_hash, source_url, first_seen, content_length, suspicious_patterns)
            VALUES (?, ?, ?, ?, ?)
        """, (content_hash, source_url, datetime.utcnow().isoformat(), content_length, suspicious_patterns))
        
        cursor.execute("""
            UPDATE content_fingerprints
            SET seen_count = seen_count + 1
            WHERE content_hash = ?
        """, (content_hash,))
        
        conn.commit()
        conn.close()
    
    def _record_anomalies(self, anomalies: List[ContentAnomaly]) -> None:
        """Record detected anomalies."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for anomaly in anomalies:
            cursor.execute("""
                INSERT INTO content_anomalies
                (content_hash, source_url, anomaly_type, severity, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                anomaly.content_hash,
                anomaly.source_url,
                anomaly.anomaly_type,
                anomaly.severity,
                anomaly.description
            ))
        
        conn.commit()
        conn.close()
    
    def update_source_reputation(self, source_url: str) -> SourceReputation:
        """Calculate and update reputation score for a source."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get source statistics
        cursor.execute("""
            SELECT COUNT(*) FROM content_fingerprints WHERE source_url = ?
        """, (source_url,))
        total_articles = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM content_anomalies 
            WHERE source_url = ? AND severity IN ('high', 'critical')
        """, (source_url,))
        flagged_articles = cursor.fetchone()[0]
        
        # Calculate scores
        reliability_score = max(0.0, 1.0 - (flagged_articles / max(total_articles, 1)))
        
        # Determine trust level
        if reliability_score >= 0.8:
            trust_level = "high"
        elif reliability_score >= 0.6:
            trust_level = "medium"
        elif reliability_score >= 0.4:
            trust_level = "low"
        else:
            trust_level = "untrusted"
        
        # Update reputation
        cursor.execute("""
            INSERT OR REPLACE INTO source_reputation
            (source_url, reliability_score, total_articles, flagged_articles, trust_level, last_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source_url,
            reliability_score,
            total_articles,
            flagged_articles,
            trust_level,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return SourceReputation(
            source_url=source_url,
            reliability_score=reliability_score,
            timeliness_score=0.5,  # TODO: Implement
            accuracy_score=0.5,  # TODO: Implement from prediction outcomes
            total_articles=total_articles,
            flagged_articles=flagged_articles,
            last_verified=datetime.utcnow(),
            trust_level=trust_level
        )
    
    def get_source_reputation(self, source_url: str) -> Optional[SourceReputation]:
        """Get reputation data for a source."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT reliability_score, timeliness_score, accuracy_score,
                   total_articles, flagged_articles, trust_level, last_verified
            FROM source_reputation
            WHERE source_url = ?
        """, (source_url,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SourceReputation(
            source_url=source_url,
            reliability_score=row[0],
            timeliness_score=row[1],
            accuracy_score=row[2],
            total_articles=row[3],
            flagged_articles=row[4],
            trust_level=row[6],
            last_verified=datetime.fromisoformat(row[6])
        )
    
    def get_trusted_sources(self, min_score: float = 0.7) -> List[str]:
        """Get list of trusted sources above threshold."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_url FROM source_reputation
            WHERE reliability_score >= ?
            ORDER BY reliability_score DESC
        """, (min_score,))
        
        sources = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return sources
    
    def get_anomaly_report(self, days: int = 7) -> Dict:
        """Get anomaly statistics for recent period."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT anomaly_type, severity, COUNT(*) as count
            FROM content_anomalies
            WHERE detected_at >= ? AND resolved = 0
            GROUP BY anomaly_type, severity
            ORDER BY count DESC
        """, (cutoff,))
        
        anomalies_by_type = defaultdict(dict)
        for row in cursor.fetchall():
            anomalies_by_type[row[0]][row[1]] = row[2]
        
        cursor.execute("""
            SELECT source_url, COUNT(*) as count
            FROM content_anomalies
            WHERE detected_at >= ? AND resolved = 0
            GROUP BY source_url
            ORDER BY count DESC
            LIMIT 10
        """, (cutoff,))
        
        top_sources = [(row[0], row[1]) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "period_days": days,
            "anomalies_by_type": dict(anomalies_by_type),
            "top_flagged_sources": top_sources
        }
