"""Critical pattern detection and alert system.

Detects complex multi-indicator patterns that signal imminent major events.
Examples:
- Carrier strike deployment + FTO designation + airspace closure = Imminent military action
- Multiple bank failures + Fed emergency lending + Treasury intervention = Systemic crisis
- AWACS sustained orbit + tanker surge + bomber deployment = Strike preparation
"""
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    IMMINENT = "imminent"


@dataclass
class PatternIndicator:
    """Individual indicator in a pattern."""
    domain: str
    keyword: str
    pattern: str  # Regex pattern
    weight: float  # Contribution to pattern match (0-1)
    required: bool = False  # Must match for pattern to trigger


@dataclass
class AlertPattern:
    """Complex multi-indicator alert pattern."""
    pattern_id: str
    name: str
    description: str
    indicators: List[PatternIndicator]
    level: AlertLevel
    min_indicators: int  # Minimum indicators that must match
    time_window: timedelta  # All indicators must occur within this window
    
    
@dataclass
class AlertMatch:
    """Detected alert pattern match."""
    pattern: AlertPattern
    matched_indicators: List[PatternIndicator]
    confidence: float
    timestamp: datetime
    evidence: List[str]  # Text snippets that matched
    
    def get_alert_message(self) -> str:
        """Generate human-readable alert message."""
        matched_names = [ind.keyword for ind in self.matched_indicators]
        return (
            f"🚨 {self.pattern.level.value.upper()} ALERT: {self.pattern.name}\n"
            f"Confidence: {self.confidence:.1%}\n"
            f"Matched Indicators: {', '.join(matched_names)}\n"
            f"Description: {self.pattern.description}\n"
            f"Time: {self.timestamp.isoformat()}"
        )


# Predefined critical alert patterns
ALERT_PATTERNS = {
    "imminent_venezuela_action": AlertPattern(
        pattern_id="imminent_venezuela_action",
        name="Imminent Venezuela Military Action",
        description=(
            "Multiple indicators suggest imminent U.S. military action against Venezuela. "
            "Carrier strike deployment + FTO designation + restricted airspace + diplomatic expulsions."
        ),
        indicators=[
            PatternIndicator(
                domain="military",
                keyword="carrier strike group",
                pattern=r"carrier strike group.*(deploy|position|transit).*(?:Caribbean|Venezuela|Colombia)",
                weight=0.35,
                required=True
            ),
            PatternIndicator(
                domain="diplomatic",
                keyword="FTO designation",
                pattern=r"Foreign Terrorist Organization|FTO designation.*Venezuela",
                weight=0.25,
                required=True
            ),
            PatternIndicator(
                domain="military",
                keyword="airspace restriction",
                pattern=r"(airspace|NOTAM).*(restricted|closed|prohibited).*(?:Caribbean|Venezuela)",
                weight=0.20,
                required=False
            ),
            PatternIndicator(
                domain="diplomatic",
                keyword="embassy evacuation",
                pattern=r"(embassy|diplomatic).*(?:evacuation|drawdown|departure).*Venezuela",
                weight=0.20,
                required=False
            ),
        ],
        level=AlertLevel.IMMINENT,
        min_indicators=3,
        time_window=timedelta(days=7)
    ),
    
    "systemic_banking_crisis": AlertPattern(
        pattern_id="systemic_banking_crisis",
        name="Systemic Banking Crisis",
        description=(
            "Multiple regional bank failures with Fed emergency intervention signals systemic crisis. "
            "FDIC seizures + emergency lending + Treasury backstop + contagion spreading."
        ),
        indicators=[
            PatternIndicator(
                domain="banking",
                keyword="bank failure",
                pattern=r"(FDIC|bank).*(failure|seized|takeover|receivership)",
                weight=0.30,
                required=True
            ),
            PatternIndicator(
                domain="banking",
                keyword="emergency lending",
                pattern=r"(Fed|Federal Reserve).*(emergency|discount window|BTFP|lending facility)",
                weight=0.25,
                required=True
            ),
            PatternIndicator(
                domain="banking",
                keyword="deposit flight",
                pattern=r"deposit.*(flight|outflow|withdrawal|run)",
                weight=0.20,
                required=False
            ),
            PatternIndicator(
                domain="financial",
                keyword="Treasury intervention",
                pattern=r"Treasury.*(backstop|guarantee|intervention|support)",
                weight=0.25,
                required=False
            ),
        ],
        level=AlertLevel.CRITICAL,
        min_indicators=3,
        time_window=timedelta(days=5)
    ),
    
    "strike_preparation": AlertPattern(
        pattern_id="strike_preparation",
        name="Military Strike Preparation",
        description=(
            "Aviation indicators suggest preparation for major strike operation. "
            "AWACS sustained orbit + tanker surge + bomber deployment + fighter escorts."
        ),
        indicators=[
            PatternIndicator(
                domain="military",
                keyword="AWACS orbit",
                pattern=r"(AWACS|E-3|airborne early warning).*(orbit|sustained|extended|continuous)",
                weight=0.30,
                required=True
            ),
            PatternIndicator(
                domain="military",
                keyword="tanker surge",
                pattern=r"(tanker|KC-135|KC-46|refueling).*(surge|increase|deployment|repositioned)",
                weight=0.25,
                required=True
            ),
            PatternIndicator(
                domain="military",
                keyword="bomber deployment",
                pattern=r"(B-52|B-1|B-2|strategic bomber).*(deploy|forward|repositioned)",
                weight=0.25,
                required=False
            ),
            PatternIndicator(
                domain="military",
                keyword="fighter escort",
                pattern=r"(F-35|F-22|F/A-18|fighter).*(escort|CAP|combat air patrol)",
                weight=0.20,
                required=False
            ),
        ],
        level=AlertLevel.IMMINENT,
        min_indicators=3,
        time_window=timedelta(days=3)
    ),
    
    "infrastructure_cascade": AlertPattern(
        pattern_id="infrastructure_cascade",
        name="Infrastructure Cascade Failure",
        description=(
            "Multiple critical infrastructure failures cascading across sectors. "
            "Power + water + transport failures suggest coordinated attack or systemic collapse."
        ),
        indicators=[
            PatternIndicator(
                domain="infrastructure",
                keyword="power outage",
                pattern=r"(power|electrical|grid).*(outage|failure|blackout|disruption)",
                weight=0.30,
                required=True
            ),
            PatternIndicator(
                domain="infrastructure",
                keyword="water system",
                pattern=r"(water|treatment|distribution).*(failure|contamination|disruption)",
                weight=0.25,
                required=False
            ),
            PatternIndicator(
                domain="infrastructure",
                keyword="transport disruption",
                pattern=r"(transport|transit|traffic).*(halt|disruption|suspended|closed)",
                weight=0.25,
                required=False
            ),
            PatternIndicator(
                domain="local",
                keyword="emergency services",
                pattern=r"(emergency|911|dispatch).*(overwhelmed|unable|delay)",
                weight=0.20,
                required=False
            ),
        ],
        level=AlertLevel.CRITICAL,
        min_indicators=2,
        time_window=timedelta(hours=24)
    ),
    
    "local_coordinated_threat": AlertPattern(
        pattern_id="local_coordinated_threat",
        name="Coordinated Local Threat (Virginia)",
        description=(
            "Multiple simultaneous incidents across Virginia jurisdictions suggest coordinated attack. "
            "Multi-jurisdiction response + simultaneous events + infrastructure targets."
        ),
        indicators=[
            PatternIndicator(
                domain="local",
                keyword="multi-jurisdiction",
                pattern=r"(mutual aid|multiple.*(jurisdiction|department|agency)|all hands)",
                weight=0.35,
                required=True
            ),
            PatternIndicator(
                domain="local",
                keyword="simultaneous incidents",
                pattern=r"(simultaneous|multiple.*(incident|report|emergency)|coordinated)",
                weight=0.30,
                required=True
            ),
            PatternIndicator(
                domain="local",
                keyword="critical infrastructure",
                pattern=r"(power|water|gas|telecom).*(attack|sabotage|damage|failure)",
                weight=0.20,
                required=False
            ),
            PatternIndicator(
                domain="local",
                keyword="tactical response",
                pattern=r"(SWAT|tactical|hostage|active shooter|barricade)",
                weight=0.15,
                required=False
            ),
        ],
        level=AlertLevel.IMMINENT,
        min_indicators=3,
        time_window=timedelta(hours=6)
    ),
}


class CriticalPatternDetector:
    """Detect critical multi-indicator patterns in real-time."""
    
    def __init__(self, patterns: Optional[Dict[str, AlertPattern]] = None):
        """Initialize detector with alert patterns.
        
        Args:
            patterns: Dictionary of alert patterns (defaults to ALERT_PATTERNS)
        """
        self.patterns = patterns if patterns is not None else ALERT_PATTERNS.copy()
        self.recent_matches: List[Tuple[datetime, str]] = []  # (timestamp, text)
        self.alert_history: List[AlertMatch] = []
    
    def add_pattern(self, pattern: AlertPattern) -> None:
        """Add a custom alert pattern.
        
        Args:
            pattern: Alert pattern to add
        """
        self.patterns[pattern.pattern_id] = pattern
    
    def check_critical_patterns(
        self,
        texts: List[str],
        min_confidence: float = 0.6
    ) -> List[AlertMatch]:
        """Check texts for critical pattern matches.
        
        Args:
            texts: List of text content to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of detected alert matches
        """
        alerts = []
        
        # Store recent matches for time window checking
        now = datetime.utcnow()
        for text in texts:
            self.recent_matches.append((now, text))
        
        # Clean old matches outside longest time window
        max_window = max(p.time_window for p in self.patterns.values())
        cutoff = now - max_window
        self.recent_matches = [
            (ts, txt) for ts, txt in self.recent_matches
            if ts >= cutoff
        ]
        
        # Check each pattern
        for pattern in self.patterns.values():
            match = self._check_pattern(pattern, now)
            if match and match.confidence >= min_confidence:
                alerts.append(match)
                self.alert_history.append(match)
        
        # Sort by level (imminent > critical > warning > info)
        level_priority = {
            AlertLevel.IMMINENT: 0,
            AlertLevel.CRITICAL: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.INFO: 3
        }
        alerts.sort(key=lambda a: level_priority[a.pattern.level])
        
        return alerts
    
    def _check_pattern(
        self,
        pattern: AlertPattern,
        timestamp: datetime
    ) -> Optional[AlertMatch]:
        """Check if a pattern is matched in recent content.
        
        Args:
            pattern: Pattern to check
            timestamp: Current timestamp
            
        Returns:
            AlertMatch if pattern detected, None otherwise
        """
        # Get texts within time window
        cutoff = timestamp - pattern.time_window
        recent_texts = [
            txt for ts, txt in self.recent_matches
            if ts >= cutoff
        ]
        
        if not recent_texts:
            return None
        
        # Check each indicator
        matched_indicators = []
        evidence = []
        total_weight = 0.0
        
        for indicator in pattern.indicators:
            for text in recent_texts:
                if re.search(indicator.pattern, text, re.IGNORECASE):
                    matched_indicators.append(indicator)
                    total_weight += indicator.weight
                    # Extract matching snippet
                    match = re.search(indicator.pattern, text, re.IGNORECASE)
                    if match:
                        snippet = text[max(0, match.start()-50):match.end()+50]
                        evidence.append(f"{indicator.keyword}: ...{snippet}...")
                    break  # Only count each indicator once
        
        # Check if pattern threshold met
        if len(matched_indicators) < pattern.min_indicators:
            return None
        
        # Check required indicators
        required_matched = all(
            any(m.keyword == req.keyword for m in matched_indicators)
            for req in pattern.indicators
            if req.required
        )
        
        if not required_matched:
            return None
        
        # Calculate confidence based on matched weight
        max_weight = sum(ind.weight for ind in pattern.indicators)
        confidence = total_weight / max_weight if max_weight > 0 else 0.0
        
        return AlertMatch(
            pattern=pattern,
            matched_indicators=matched_indicators,
            confidence=confidence,
            timestamp=timestamp,
            evidence=evidence
        )
    
    def get_active_alerts(
        self,
        time_window: timedelta = timedelta(hours=24)
    ) -> List[AlertMatch]:
        """Get alerts triggered within time window.
        
        Args:
            time_window: Time window to check
            
        Returns:
            List of active alerts
        """
        cutoff = datetime.utcnow() - time_window
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff
        ]
    
    def format_alerts_report(
        self,
        alerts: List[AlertMatch]
    ) -> str:
        """Format alerts as a report.
        
        Args:
            alerts: List of alert matches
            
        Returns:
            Formatted report string
        """
        if not alerts:
            return "No critical patterns detected."
        
        report = []
        report.append("="*60)
        report.append("CRITICAL PATTERN DETECTION REPORT")
        report.append("="*60)
        report.append(f"Total Alerts: {len(alerts)}")
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        for i, alert in enumerate(alerts, 1):
            report.append(f"\n[Alert {i}] {alert.pattern.level.value.upper()}")
            report.append(alert.get_alert_message())
            report.append("\nEvidence:")
            for evidence in alert.evidence[:3]:  # Show top 3 pieces of evidence
                report.append(f"  • {evidence}")
            report.append("-"*60)
        
        return "\n".join(report)


def check_for_critical_events(
    texts: List[str],
    patterns: Optional[Dict[str, AlertPattern]] = None,
    min_confidence: float = 0.6
) -> Dict[str, any]:
    """Convenience function to check texts for critical patterns.
    
    Args:
        texts: List of texts to analyze
        patterns: Custom patterns (defaults to ALERT_PATTERNS)
        min_confidence: Minimum confidence threshold
        
    Returns:
        Dictionary with detection results
    """
    detector = CriticalPatternDetector(patterns)
    alerts = detector.check_critical_patterns(texts, min_confidence)
    
    return {
        "total_alerts": len(alerts),
        "imminent_count": sum(1 for a in alerts if a.pattern.level == AlertLevel.IMMINENT),
        "critical_count": sum(1 for a in alerts if a.pattern.level == AlertLevel.CRITICAL),
        "alerts": alerts,
        "report": detector.format_alerts_report(alerts)
    }


__all__ = [
    'AlertLevel',
    'PatternIndicator',
    'AlertPattern',
    'AlertMatch',
    'CriticalPatternDetector',
    'ALERT_PATTERNS',
    'check_for_critical_events'
]
