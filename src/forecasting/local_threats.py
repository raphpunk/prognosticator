"""Local threat monitoring via police dispatch feed integration.

Scrapes real-time police dispatch data from Virginia jurisdictions and correlates
with geopolitical threat patterns.
"""
import re
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

logger = logging.getLogger(__name__)

# Jurisdiction mapping: zip code -> dispatch URLs
JURISDICTION_MAP = {
    # Chesterfield County
    "23112": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23831": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23832": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23834": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23235": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23236": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    "23237": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
    
    # Richmond City
    "23220": ["https://apps.richmondgov.com/applications/activecalls"],
    "23221": ["https://apps.richmondgov.com/applications/activecalls"],
    "23222": ["https://apps.richmondgov.com/applications/activecalls"],
    "23223": ["https://apps.richmondgov.com/applications/activecalls"],
    "23224": ["https://apps.richmondgov.com/applications/activecalls"],
    "23225": ["https://apps.richmondgov.com/applications/activecalls"],
    
    # Henrico County
    "23228": ["https://henrico.us/police/active-calls/"],
    "23229": ["https://henrico.us/police/active-calls/"],
    "23230": ["https://henrico.us/police/active-calls/"],
    "23233": ["https://henrico.us/police/active-calls/"],
    "23294": ["https://henrico.us/police/active-calls/"],
    
    # Colonial Heights
    "23834": ["https://www.colonialheightsva.gov/police"],
}

# Incident severity mapping (1=routine, 5=critical)
INCIDENT_SEVERITY = {
    # Critical (5)
    "SHOTS FIRED": 5,
    "SHOOTING": 5,
    "ARMED ROBBERY": 5,
    "OFFICER DOWN": 5,
    "ACTIVE SHOOTER": 5,
    "HOMICIDE": 5,
    "STABBING": 5,
    "HOSTAGE": 5,
    
    # High (4)
    "ASSAULT": 4,
    "ROBBERY": 4,
    "DOMESTIC": 4,
    "WEAPONS": 4,
    "CARJACKING": 4,
    "PURSUIT": 4,
    "RIOT": 4,
    "CIVIL UNREST": 4,
    
    # Medium (3)
    "BURGLARY": 3,
    "THEFT": 3,
    "VANDALISM": 3,
    "TRESPASSING": 3,
    "SUSPICIOUS": 3,
    "DISTURBANCE": 3,
    "FIGHT": 3,
    
    # Low (2)
    "TRAFFIC": 2,
    "ACCIDENT": 2,
    "PARKING": 2,
    "NOISE": 2,
    "WELFARE CHECK": 2,
    
    # Routine (1)
    "INFORMATION": 1,
    "ASSIST": 1,
    "DETAIL": 1,
}


@dataclass
class DispatchCall:
    """Normalized dispatch call data."""
    incident_id: str
    incident_type: str
    location: str
    jurisdiction: str
    units: List[str]
    timestamp: str
    severity: int
    coordinates: Optional[Tuple[float, float]] = None
    raw_data: Optional[Dict] = None


@dataclass
class ThreatPattern:
    """Detected threat escalation pattern."""
    pattern_type: str  # "escalation", "coordination", "spread"
    severity: int
    incident_count: int
    timespan_minutes: int
    locations: List[str]
    description: str
    alert_level: str  # "info", "warning", "critical"


class LocalThreatTracker:
    """Track and analyze local police dispatch data."""
    
    def __init__(self, db_path: str = "data/local_threats.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize threat tracking database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Dispatch calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_calls (
                incident_id TEXT PRIMARY KEY,
                incident_type TEXT NOT NULL,
                location TEXT,
                jurisdiction TEXT NOT NULL,
                units TEXT,
                timestamp TEXT NOT NULL,
                severity INTEGER NOT NULL,
                coordinates TEXT,
                raw_data TEXT,
                ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Threat patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threat_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                severity INTEGER NOT NULL,
                incident_count INTEGER,
                timespan_minutes INTEGER,
                locations TEXT,
                description TEXT,
                alert_level TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Scraping errors log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_timestamp ON dispatch_calls(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_jurisdiction ON dispatch_calls(jurisdiction)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_severity ON dispatch_calls(severity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_detected ON threat_patterns(detected_at)")
        
        conn.commit()
        conn.close()
    
    def record_call(self, call: DispatchCall) -> None:
        """Record a dispatch call."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        coords_json = json.dumps(call.coordinates) if call.coordinates else None
        units_json = json.dumps(call.units)
        raw_json = json.dumps(call.raw_data) if call.raw_data else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO dispatch_calls
            (incident_id, incident_type, location, jurisdiction, units, timestamp, severity, coordinates, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            call.incident_id,
            call.incident_type,
            call.location,
            call.jurisdiction,
            units_json,
            call.timestamp,
            call.severity,
            coords_json,
            raw_json
        ))
        
        conn.commit()
        conn.close()
    
    def record_error(self, url: str, error_type: str, error_message: str) -> None:
        """Log scraping error for debugging."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scraping_errors (url, error_type, error_message)
            VALUES (?, ?, ?)
        """, (url, error_type, error_message[:500]))
        
        conn.commit()
        conn.close()
        
        logger.error(f"Scraping error for {url}: {error_type} - {error_message[:200]}")
    
    def get_recent_calls(self, jurisdiction: Optional[str] = None, hours: int = 24) -> List[DispatchCall]:
        """Get recent dispatch calls."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        query = """
            SELECT incident_id, incident_type, location, jurisdiction, units, 
                   timestamp, severity, coordinates, raw_data
            FROM dispatch_calls
            WHERE timestamp >= ?
        """
        params = [cutoff]
        
        if jurisdiction:
            query += " AND jurisdiction = ?"
            params.append(jurisdiction)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        calls = []
        for row in rows:
            calls.append(DispatchCall(
                incident_id=row[0],
                incident_type=row[1],
                location=row[2],
                jurisdiction=row[3],
                units=json.loads(row[4]) if row[4] else [],
                timestamp=row[5],
                severity=row[6],
                coordinates=json.loads(row[7]) if row[7] else None,
                raw_data=json.loads(row[8]) if row[8] else None
            ))
        
        return calls
    
    def detect_escalation_patterns(self, hours: int = 6) -> List[ThreatPattern]:
        """Detect threat escalation patterns in recent calls."""
        calls = self.get_recent_calls(hours=hours)
        
        if not calls:
            return []
        
        patterns = []
        
        # Pattern 1: Rapid severity escalation in same area
        location_severity = {}
        for call in calls:
            loc = call.location[:50] if call.location else "Unknown"
            if loc not in location_severity:
                location_severity[loc] = []
            location_severity[loc].append((call.severity, call.timestamp))
        
        for loc, events in location_severity.items():
            if len(events) >= 3:
                sorted_events = sorted(events, key=lambda x: x[1])
                severities = [s for s, _ in sorted_events]
                
                # Check for escalation (severity increasing)
                if len(severities) >= 3 and severities[-1] > severities[0] and severities[-1] >= 4:
                    patterns.append(ThreatPattern(
                        pattern_type="escalation",
                        severity=severities[-1],
                        incident_count=len(events),
                        timespan_minutes=hours * 60,
                        locations=[loc],
                        description=f"Severity escalation at {loc}: {severities[0]}→{severities[-1]}",
                        alert_level="warning" if severities[-1] >= 4 else "info"
                    ))
        
        # Pattern 2: Coordinated incidents (multiple high-severity events in short time)
        high_severity_calls = [c for c in calls if c.severity >= 4]
        if len(high_severity_calls) >= 3:
            timestamps = [datetime.fromisoformat(c.timestamp) for c in high_severity_calls]
            if timestamps:
                time_diff = (max(timestamps) - min(timestamps)).total_seconds() / 60
                
                if time_diff <= 60:  # Within 1 hour
                    patterns.append(ThreatPattern(
                        pattern_type="coordination",
                        severity=max(c.severity for c in high_severity_calls),
                        incident_count=len(high_severity_calls),
                        timespan_minutes=int(time_diff),
                        locations=[c.location for c in high_severity_calls],
                        description=f"{len(high_severity_calls)} high-severity incidents within {time_diff:.0f} minutes",
                        alert_level="critical" if len(high_severity_calls) >= 5 else "warning"
                    ))
        
        # Pattern 3: Geographic spread (same incident type across multiple locations)
        incident_types = {}
        for call in calls:
            if call.severity >= 3:
                itype = call.incident_type
                if itype not in incident_types:
                    incident_types[itype] = []
                incident_types[itype].append(call.location)
        
        for itype, locations in incident_types.items():
            unique_locations = set(locations)
            if len(unique_locations) >= 3:
                patterns.append(ThreatPattern(
                    pattern_type="spread",
                    severity=3,
                    incident_count=len(locations),
                    timespan_minutes=hours * 60,
                    locations=list(unique_locations),
                    description=f"{itype} reported in {len(unique_locations)} different locations",
                    alert_level="warning"
                ))
        
        # Record patterns in database
        if patterns:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            for pattern in patterns:
                cursor.execute("""
                    INSERT INTO threat_patterns
                    (pattern_type, severity, incident_count, timespan_minutes, locations, description, alert_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_type,
                    pattern.severity,
                    pattern.incident_count,
                    pattern.timespan_minutes,
                    json.dumps(pattern.locations),
                    pattern.description,
                    pattern.alert_level
                ))
            
            conn.commit()
            conn.close()
        
        return patterns
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get scraping error statistics for monitoring."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT error_type, COUNT(*) as count
            FROM scraping_errors
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY error_type
        """)
        
        stats = dict(cursor.fetchall())
        conn.close()
        
        return stats


class DispatchScraper:
    """Scrape police dispatch feeds using Playwright."""
    
    def __init__(self, tracker: LocalThreatTracker, timeout: int = 45):
        self.tracker = tracker
        self.timeout = timeout
        self.playwright_available = False
        
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright
            self.playwright_available = True
        except ImportError:
            logger.warning("Playwright not available - dispatch scraping disabled")
    
    def scrape_chesterfield(self, url: str = "https://www.chesterfield.gov/3999/Active-Police-Calls") -> List[DispatchCall]:
        """Scrape Chesterfield County active calls.
        
        Their site has a clean table structure with:
        - Incident Number
        - Type
        - Location
        - Units
        - Time
        """
        if not self.playwright_available:
            return []
        
        calls = []
        
        try:
            with self.playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set timeout based on historical patterns
                page.set_default_timeout(self.timeout * 1000)
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                except Exception as e:
                    self.tracker.record_error(url, "navigation_timeout", str(e))
                    browser.close()
                    return []
                
                # Wait for table to load (JS-rendered content)
                try:
                    page.wait_for_selector("table", timeout=10000)
                except Exception as e:
                    self.tracker.record_error(url, "table_not_found", str(e))
                    browser.close()
                    return []
                
                # Parse table rows
                try:
                    rows = page.query_selector_all("table tbody tr")
                    
                    for row in rows:
                        try:
                            cells = row.query_selector_all("td")
                            
                            if len(cells) >= 5:
                                incident_id = cells[0].inner_text().strip()
                                incident_type = cells[1].inner_text().strip()
                                location = cells[2].inner_text().strip()
                                units_text = cells[3].inner_text().strip()
                                timestamp_text = cells[4].inner_text().strip()
                                
                                # Parse units
                                units = [u.strip() for u in units_text.split(",") if u.strip()]
                                
                                # Determine severity
                                severity = self._calculate_severity(incident_type)
                                
                                # Normalize timestamp
                                timestamp = self._normalize_timestamp(timestamp_text)
                                
                                call = DispatchCall(
                                    incident_id=f"chesterfield_{incident_id}",
                                    incident_type=incident_type,
                                    location=location,
                                    jurisdiction="Chesterfield",
                                    units=units,
                                    timestamp=timestamp,
                                    severity=severity,
                                    raw_data={
                                        "source": url,
                                        "raw_timestamp": timestamp_text,
                                        "raw_type": incident_type
                                    }
                                )
                                
                                calls.append(call)
                                self.tracker.record_call(call)
                                
                        except Exception as e:
                            self.tracker.record_error(url, "row_parse_error", f"Row parsing failed: {str(e)}")
                            continue
                    
                    logger.info(f"Scraped {len(calls)} calls from Chesterfield")
                    
                except Exception as e:
                    self.tracker.record_error(url, "table_parse_error", str(e))
                
                browser.close()
                
        except Exception as e:
            self.tracker.record_error(url, "playwright_error", str(e))
        
        return calls
    
    def _calculate_severity(self, incident_type: str) -> int:
        """Calculate severity from incident type."""
        incident_upper = incident_type.upper()
        
        # Check for exact matches
        for keyword, severity in INCIDENT_SEVERITY.items():
            if keyword in incident_upper:
                return severity
        
        # Default to medium severity
        return 3
    
    def _normalize_timestamp(self, timestamp_text: str) -> str:
        """Normalize timestamp to ISO format."""
        try:
            # Try parsing common formats
            # Format: "11/24/2025 4:30 PM"
            from dateutil import parser
            dt = parser.parse(timestamp_text)
            return dt.isoformat()
        except Exception:
            # Fallback to current time if parsing fails
            return datetime.utcnow().isoformat()
    
    def scrape_richmond(self, url: str = "https://www.rva.gov/emergency-communications/active-calls") -> List[DispatchCall]:
        """Scrape Richmond City active calls."""
        if not self.playwright_available:
            return []
        
        calls = []
        try:
            with self.playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(self.timeout * 1000)
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                except Exception as e:
                    self.tracker.record_error(url, "navigation_timeout", str(e))
                    browser.close()
                    return []
                
                # Try multiple selectors for Richmond's table
                try:
                    page.wait_for_selector("table", timeout=10000)
                except Exception:
                    logger.warning(f"Table not found at {url}, trying alternative selectors")
                    browser.close()
                    return []
                
                try:
                    rows = page.query_selector_all("table tbody tr")
                    
                    for row in rows:
                        try:
                            cells = row.query_selector_all("td")
                            if len(cells) >= 4:
                                # Richmond format varies, try to extract common fields
                                incident_id = cells[0].inner_text().strip()[:50]
                                incident_type = cells[1].inner_text().strip() if len(cells) > 1 else "UNKNOWN"
                                location = cells[2].inner_text().strip() if len(cells) > 2 else "Unknown"
                                
                                severity = self._calculate_severity(incident_type)
                                timestamp = self._normalize_timestamp("")
                                
                                call = DispatchCall(
                                    incident_id=f"richmond_{hashlib.md5(incident_id.encode()).hexdigest()[:8]}",
                                    incident_type=incident_type,
                                    location=location,
                                    jurisdiction="Richmond",
                                    units=[],
                                    timestamp=timestamp,
                                    severity=severity,
                                    coordinates=None,
                                    raw_data=None
                                )
                                calls.append(call)
                        except Exception as e:
                            logger.debug(f"Error parsing Richmond row: {e}")
                            continue
                    
                    if calls:
                        logger.info(f"Scraped {len(calls)} calls from Richmond")
                        for call in calls:
                            self.tracker.record_call(call)
                
                except Exception as e:
                    self.tracker.record_error(url, "parse_error", str(e))
                
                browser.close()
        
        except Exception as e:
            self.tracker.record_error(url, "playwright_error", str(e))
        
        return calls
    
    def scrape_henrico(self, url: str = "https://henrico.us/police/active-calls/") -> List[DispatchCall]:
        """Scrape Henrico County active calls."""
        if not self.playwright_available:
            return []
        
        calls = []
        try:
            with self.playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(self.timeout * 1000)
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                except Exception as e:
                    self.tracker.record_error(url, "navigation_timeout", str(e))
                    browser.close()
                    return []
                
                try:
                    page.wait_for_selector("table", timeout=10000)
                except Exception:
                    logger.warning(f"Table not found at {url}")
                    browser.close()
                    return []
                
                try:
                    rows = page.query_selector_all("table tbody tr")
                    
                    for row in rows:
                        try:
                            cells = row.query_selector_all("td")
                            if len(cells) >= 3:
                                incident_id = cells[0].inner_text().strip()[:50]
                                incident_type = cells[1].inner_text().strip() if len(cells) > 1 else "UNKNOWN"
                                location = cells[2].inner_text().strip() if len(cells) > 2 else "Unknown"
                                
                                severity = self._calculate_severity(incident_type)
                                timestamp = self._normalize_timestamp("")
                                
                                call = DispatchCall(
                                    incident_id=f"henrico_{hashlib.md5(incident_id.encode()).hexdigest()[:8]}",
                                    incident_type=incident_type,
                                    location=location,
                                    jurisdiction="Henrico",
                                    units=[],
                                    timestamp=timestamp,
                                    severity=severity,
                                    coordinates=None,
                                    raw_data=None
                                )
                                calls.append(call)
                        except Exception as e:
                            logger.debug(f"Error parsing Henrico row: {e}")
                            continue
                    
                    if calls:
                        logger.info(f"Scraped {len(calls)} calls from Henrico")
                        for call in calls:
                            self.tracker.record_call(call)
                
                except Exception as e:
                    self.tracker.record_error(url, "parse_error", str(e))
                
                browser.close()
        
        except Exception as e:
            self.tracker.record_error(url, "playwright_error", str(e))
        
        return calls
    
    def scrape_colonial_heights(self, url: str = "https://www.colonialheightsva.gov/police") -> List[DispatchCall]:
        """Scrape Colonial Heights active calls."""
        if not self.playwright_available:
            return []
        
        calls = []
        try:
            with self.playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(self.timeout * 1000)
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                except Exception as e:
                    self.tracker.record_error(url, "navigation_timeout", str(e))
                    browser.close()
                    return []
                
                try:
                    page.wait_for_selector("table", timeout=10000)
                except Exception:
                    logger.warning(f"Table not found at {url}")
                    browser.close()
                    return []
                
                try:
                    rows = page.query_selector_all("table tbody tr")
                    
                    for row in rows:
                        try:
                            cells = row.query_selector_all("td")
                            if len(cells) >= 3:
                                incident_id = cells[0].inner_text().strip()[:50]
                                incident_type = cells[1].inner_text().strip() if len(cells) > 1 else "UNKNOWN"
                                location = cells[2].inner_text().strip() if len(cells) > 2 else "Unknown"
                                
                                severity = self._calculate_severity(incident_type)
                                timestamp = self._normalize_timestamp("")
                                
                                call = DispatchCall(
                                    incident_id=f"colonialheights_{hashlib.md5(incident_id.encode()).hexdigest()[:8]}",
                                    incident_type=incident_type,
                                    location=location,
                                    jurisdiction="Colonial Heights",
                                    units=[],
                                    timestamp=timestamp,
                                    severity=severity,
                                    coordinates=None,
                                    raw_data=None
                                )
                                calls.append(call)
                        except Exception as e:
                            logger.debug(f"Error parsing Colonial Heights row: {e}")
                            continue
                    
                    if calls:
                        logger.info(f"Scraped {len(calls)} calls from Colonial Heights")
                        for call in calls:
                            self.tracker.record_call(call)
                
                except Exception as e:
                    self.tracker.record_error(url, "parse_error", str(e))
                
                browser.close()
        
        except Exception as e:
            self.tracker.record_error(url, "playwright_error", str(e))
        
        return calls

    def scrape_all_jurisdictions(self, zip_code: Optional[str] = None) -> List[DispatchCall]:
        """Scrape all configured jurisdictions or specific zip code.
        
        If zip_code is provided, scrapes only the jurisdiction for that zip code.
        Otherwise, scrapes all known jurisdictions.
        """
        all_calls = []
        
        urls_to_scrape = set()
        
        if zip_code and zip_code in JURISDICTION_MAP:
            urls_to_scrape.update(JURISDICTION_MAP[zip_code])
        else:
            # Scrape all unique URLs
            for urls in JURISDICTION_MAP.values():
                urls_to_scrape.update(urls)
        
        for url in urls_to_scrape:
            if "chesterfield" in url.lower():
                calls = self.scrape_chesterfield(url)
                all_calls.extend(calls)
            elif "richmondgov" in url.lower() or "rva.gov" in url.lower() or "activecalls" in url.lower():
                calls = self.scrape_richmond(url)
                all_calls.extend(calls)
            elif "henrico" in url.lower():
                calls = self.scrape_henrico(url)
                all_calls.extend(calls)
            elif "colonialheights" in url.lower():
                calls = self.scrape_colonial_heights(url)
                all_calls.extend(calls)
            else:
                logger.warning(f"No scraper implemented for {url}")
        
        return all_calls


def convert_to_feed_format(calls: List[DispatchCall], min_severity: int = 3) -> List[Dict]:
    """Convert dispatch calls to RSS-like format for existing pipeline integration.
    
    Only high-priority calls (severity >= min_severity) are converted.
    """
    feed_items = []
    
    for call in calls:
        if call.severity < min_severity:
            continue
        
        # Create RSS-like entry
        feed_items.append({
            "id": call.incident_id,
            "title": f"[LOCAL ALERT] {call.incident_type} in {call.jurisdiction}",
            "summary": f"Active dispatch: {call.incident_type} at {call.location}. "
                      f"Severity: {call.severity}/5. Units: {', '.join(call.units)}. "
                      f"Time: {call.timestamp}",
            "published": call.timestamp,
            "source_url": f"local_dispatch://{call.jurisdiction}/{call.incident_id}",
            "fetched_from": f"local_dispatch_{call.jurisdiction}",
            "text": f"{call.incident_type} reported at {call.location}. "
                   f"Multiple units responding. Severity level: {call.severity}/5. "
                   f"This is an active local incident that may indicate escalating threats.",
            "local_threat": True,
            "severity": call.severity,
            "jurisdiction": call.jurisdiction
        })
    
    return feed_items


def get_jurisdiction_for_zip(zip_code: str) -> Optional[str]:
    """Get jurisdiction name for a zip code."""
    urls = JURISDICTION_MAP.get(zip_code, [])
    if not urls:
        return None
    
    url = urls[0]
    if "chesterfield" in url:
        return "Chesterfield"
    elif "rva.gov" in url or "richmond" in url:
        return "Richmond"
    elif "henrico" in url:
        return "Henrico"
    elif "colonialheights" in url:
        return "Colonial Heights"
    
    return None


def get_available_zip_codes() -> Dict[str, str]:
    """Get all available Virginia zip codes and their jurisdictions.
    
    Returns:
        Dict mapping zip code to jurisdiction name
    """
    result = {}
    for zip_code, urls in JURISDICTION_MAP.items():
        jurisdiction = get_jurisdiction_for_zip(zip_code)
        if jurisdiction:
            result[zip_code] = jurisdiction
    return result


def get_jurisdictions() -> List[str]:
    """Get list of unique jurisdictions available.
    
    Returns:
        List of jurisdiction names
    """
    jurisdictions = set()
    for zip_code in JURISDICTION_MAP.keys():
        jurisdiction = get_jurisdiction_for_zip(zip_code)
        if jurisdiction:
            jurisdictions.add(jurisdiction)
    return sorted(list(jurisdictions))


__all__ = [
    "LocalThreatTracker",
    "DispatchScraper",
    "DispatchCall",
    "ThreatPattern",
    "convert_to_feed_format",
    "get_jurisdiction_for_zip",
    "get_available_zip_codes",
    "get_jurisdictions",
    "JURISDICTION_MAP",
    "INCIDENT_SEVERITY"
]
