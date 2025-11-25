## Advanced Features - Specialized Intelligence Analysis

This document describes the advanced intelligence analysis features added to the Prognosticator system.

## Table of Contents
1. [Specialized Agents](#specialized-agents)
2. [Cascade Modeling](#cascade-modeling)
3. [Critical Alert System](#critical-alert-system)
4. [Enhanced Reputation & Validation](#enhanced-reputation--validation)
5. [Real-time Data Sources](#real-time-data-sources)
6. [Virginia Local News Feeds](#virginia-local-news-feeds)

---

## Specialized Agents

**Location**: `src/forecasting/specialized_agents.py`

Three specialized agents with deep domain expertise and keyword-based relevance detection:

### 1. OSINT Flight Tracker (`🛩️`)
**Domain**: military/osint  
**Model**: gemma:2b  
**Weight**: 1.3

Monitors military aviation patterns for operational indicators:
- **Keywords**: tanker, KC-135, carrier strike group, AWACS, strategic bomber, reconnaissance
- **Priority Patterns**: 
  - Carrier strike deployment
  - Tanker unusual patterns
  - Bomber forward deployment
  - AWACS sustained orbits
  - Strategic airlift surges

**Use Case**: Detects pre-operational military aviation indicators like tanker surges, AWACS sustained presence, and strategic bomber movements that precede major military operations.

### 2. Banking Crisis Analyst (`🏦`)
**Domain**: financial/banking  
**Model**: gemma:2b  
**Weight**: 1.3

Monitors regional banking stress and systemic risk indicators:
- **Keywords**: FDIC, liquidity crisis, deposit flight, regional bank, unrealized loss, commercial real estate, contagion
- **Priority Patterns**:
  - FDIC takeovers
  - Emergency lending activation
  - Deposit flight events
  - CRE delinquency spikes
  - Systemic risk warnings

**Use Case**: Early detection of banking sector stress before it cascades into broader financial crisis. Tracks 2023-style regional bank failures and BTFP emergency lending.

### 3. Local Threat Monitor (`🚨`)
**Domain**: local/virginia  
**Model**: gemma:2b  
**Weight**: 2.5 (elevated for local relevance)

Monitors Virginia-specific security events and emergency response patterns:
- **Keywords**: Richmond, Midlothian, Chesterfield, evacuation, active shooter, hazmat, mass casualty, infrastructure failure
- **Priority Patterns**:
  - Evacuation orders
  - Active shooter situations
  - Multi-jurisdiction responses
  - SWAT deployments
  - Infrastructure failures

**Use Case**: Provides hyperlocal threat intelligence for Virginia jurisdictions, detecting escalation patterns and coordinated incidents.

### Usage Example

```python
from src.forecasting.specialized_agents import (
    get_specialized_agents,
    filter_agents_by_content,
    OSINT_FLIGHT_TRACKER
)

# Get all specialized agents
agents = get_specialized_agents()

# Filter agents by content relevance
article_text = "Multiple KC-135 tankers deployed to forward operating bases..."
relevant_agents = filter_agents_by_content(article_text, min_relevance=0.3)

# Check priority signals
priority_matches = OSINT_FLIGHT_TRACKER.detect_priority_signals(article_text)
print(f"Priority alerts: {priority_matches}")
```

---

## Cascade Modeling

**Location**: `src/forecasting/cascade_modeling.py`

Analyzes how events in one domain trigger cascading effects across multiple domains.

### Cascade Relationships

Predefined cascade edges model multi-domain event propagation:

```
Military → Energy → Financial → Banking → Real Estate
    ↓          ↓         ↓           ↓          ↓
  Hours     Days      Days        Weeks     Months
```

**Example Cascades**:
1. **Military → Energy → Banking**
   - Carrier deployment → Oil supply uncertainty (6h lag) → Inflation fears (2d lag) → Bank credit stress (7d lag)

2. **Banking → Real Estate → Local Economy**
   - Bank liquidity crisis → Lending freeze (14d lag) → CRE distress (14d lag) → Municipal revenue decline (90d lag)

3. **Cyber → Infrastructure → Local Security**
   - Cyber attack → Power disruption (12h lag) → Civil order breakdown (2d lag)

### Usage Example

```python
from src.forecasting.cascade_modeling import analyze_event_cascade

# Analyze cascades from a trigger event
result = analyze_event_cascade(
    trigger_domain="military",
    trigger_event="Carrier strike group deployed to Caribbean",
    max_depth=4,
    min_probability=0.3
)

print(f"Total pathways: {result['total_pathways']}")
print(f"Critical pathways: {result['critical_pathways']}")

# Print cascade reports
for report in result['reports']:
    print(report)
```

### Sample Output

```
=== CASCADE ANALYSIS ===
Trigger: Carrier strike group deployed to Caribbean
Overall Probability: 42.0%
Total Lag Time: 23 days
Detection Confidence: 82.5%

Cascade Sequence:

1. MILITARY [trigger]
   Event: Carrier strike group deployed to Caribbean
   Probability: 100.0%
   ↓
   Carrier deployment/bomber forward basing → Oil supply uncertainty → Price spike
   Lag: 0d 6h

2. ENERGY [primary]
   Event: Oil supply uncertainty → Price spike
   Probability: 75.0%
   ↓
   Oil price spike → Inflation expectations → Fed policy tightening fears
   Lag: 2d 0h

3. FINANCIAL [secondary]
   Event: Inflation expectations → Fed policy tightening fears
   Probability: 70.0%
```

---

## Critical Alert System

**Location**: `src/forecasting/critical_alerts.py`

Detects complex multi-indicator patterns that signal imminent major events.

### Predefined Alert Patterns

#### 1. Imminent Venezuela Action
**Indicators Required**: 3+ of 4
- Carrier strike group deployment (required)
- FTO designation (required)
- Airspace restriction
- Embassy evacuation

**Time Window**: 7 days  
**Alert Level**: IMMINENT

#### 2. Systemic Banking Crisis
**Indicators Required**: 3+ of 4
- Bank failure/FDIC takeover (required)
- Fed emergency lending (required)
- Deposit flight
- Treasury intervention

**Time Window**: 5 days  
**Alert Level**: CRITICAL

#### 3. Military Strike Preparation
**Indicators Required**: 3+ of 4
- AWACS sustained orbit (required)
- Tanker surge (required)
- Bomber deployment
- Fighter escorts

**Time Window**: 3 days  
**Alert Level**: IMMINENT

#### 4. Infrastructure Cascade Failure
**Indicators Required**: 2+ of 4
- Power outage (required)
- Water system failure
- Transport disruption
- Emergency services overwhelmed

**Time Window**: 24 hours  
**Alert Level**: CRITICAL

#### 5. Coordinated Local Threat (Virginia)
**Indicators Required**: 3+ of 4
- Multi-jurisdiction response (required)
- Simultaneous incidents (required)
- Critical infrastructure attack
- Tactical (SWAT) response

**Time Window**: 6 hours  
**Alert Level**: IMMINENT

### Usage Example

```python
from src.forecasting.critical_alerts import check_for_critical_events

# Check recent articles for critical patterns
articles = [
    "Carrier strike group USS Abraham Lincoln transiting Caribbean...",
    "State Department designates Venezuelan security forces as FTO...",
    "FAA issues NOTAM restricting airspace over Caribbean waters..."
]

result = check_for_critical_events(articles, min_confidence=0.6)

print(f"Total alerts: {result['total_alerts']}")
print(f"Imminent events: {result['imminent_count']}")
print(f"Critical events: {result['critical_count']}")

print(result['report'])
```

### Sample Alert Output

```
============================================================
CRITICAL PATTERN DETECTION REPORT
============================================================
Total Alerts: 1
Generated: 2025-11-25T14:30:00

[Alert 1] IMMINENT
🚨 IMMINENT ALERT: Imminent Venezuela Military Action
Confidence: 85.0%
Matched Indicators: carrier strike group, FTO designation, airspace restriction
Description: Multiple indicators suggest imminent U.S. military action against Venezuela...
Time: 2025-11-25T14:30:00

Evidence:
  • carrier strike group: ...Carrier strike group USS Abraham Lincoln transiting Caribbean...
  • FTO designation: ...State Department designates Venezuelan security forces as FTO...
  • airspace restriction: ...FAA issues NOTAM restricting airspace over Caribbean waters...
------------------------------------------------------------
```

---

## Enhanced Reputation & Validation

**Location**: `src/forecasting/reputation.py`

New methods for tracking prediction accuracy and updating agent reputations.

### Prediction Validation

The `validate_prediction()` method compares predicted probabilities to actual outcomes:

```python
from src.forecasting.reputation import ReputationTracker

tracker = ReputationTracker()

# Validate a prediction
result = tracker.validate_prediction(
    prediction_id="pred_12345",
    predicted_probability=0.75,  # Agent predicted 75% chance
    predicted_confidence=0.80,   # With 80% confidence
    actual_outcome=True,         # Event actually occurred
    outcome_context="Carrier deployed as predicted"
)

print(f"Accuracy score: {result['accuracy_score']:.1%}")
print(f"Brier score: {result['brier_score']:.3f}")
print(f"Calibration error: {result['calibration_error']:.1%}")
print(f"Outcome match: {result['outcome_match']}")
print(f"Classification: {result['outcome_classification']}")
```

### Metrics Explained

**Brier Score**: Probabilistic prediction accuracy (lower is better, 0 = perfect)
- Formula: `(predicted_probability - actual_outcome)^2`
- Range: 0.0 (perfect) to 1.0 (completely wrong)

**Accuracy Score**: Inverse of Brier score (higher is better)
- Formula: `1 - brier_score`
- Range: 0.0 (wrong) to 1.0 (perfect)

**Calibration Error**: How well confidence matches actual accuracy
- Formula: `|predicted_confidence - accuracy_score|`
- Low calibration error = well-calibrated agent

**Outcome Classification**:
- `correct`: Prediction matched outcome with high accuracy (>0.8)
- `partial`: Right direction but poor calibration
- `incorrect`: Prediction did not match outcome

### Batch Validation

```python
validations = [
    {
        "prediction_id": "pred_001",
        "predicted_probability": 0.75,
        "predicted_confidence": 0.80,
        "actual_outcome": True
    },
    {
        "prediction_id": "pred_002",
        "predicted_probability": 0.30,
        "predicted_confidence": 0.60,
        "actual_outcome": False
    }
]

batch_result = tracker.batch_validate_predictions(validations)
print(f"Accuracy rate: {batch_result['accuracy_rate']:.1%}")
print(f"Average accuracy score: {batch_result['average_accuracy_score']:.1%}")
```

---

## Real-time Data Sources

**Location**: `src/monitoring/realtime_sources.py`

Stubs for integrating non-RSS real-time data sources. These are framework implementations requiring API keys and additional integration work.

### ADS-B Flight Tracking

**Services**: OpenSky Network, ADS-B Exchange, FlightAware

```python
from src.monitoring.realtime_sources import ADSBFlightTracker

tracker = ADSBFlightTracker(api_key="your_key")

# Get flights in geographic area
flights = tracker.get_flights_in_area(
    lat_min=36.0, lat_max=38.0,
    lon_min=-78.0, lon_max=-76.0,
    include_military=True
)

# Track military patterns
patterns = tracker.track_military_pattern(
    aircraft_types=['KC-135', 'B-52'],
    region='caribbean',
    hours_lookback=24
)

# Detect tanker surge (operational indicator)
surge = tracker.detect_tanker_surge(
    region='persian_gulf',
    baseline_days=7
)
print(f"Surge detected: {surge['surge_detected']}")
```

### Market Data Feed

**Services**: Yahoo Finance, Alpha Vantage, FRED

```python
from src.monitoring.realtime_sources import MarketDataFeed

feed = MarketDataFeed(api_key="your_key")

# Get financial stress indicators
indicators = feed.get_stress_indicators()
print(f"VIX: {indicators['VIX'].price}")
print(f"TED Spread: {indicators['TED'].price}")

# Detect credit market stress
stress = feed.detect_credit_stress(lookback_days=30)
print(f"Stress level: {stress['stress_level']}")

# Track regional bank index (KRE)
banks = feed.get_regional_bank_index()
print(f"Regional banks: {banks.change_percent:.1%}")
```

### Dispatch Audio Parsing

**Services**: Broadcastify, Scanner Radio

```python
from src.monitoring.realtime_sources import DispatchAudioParser

parser = DispatchAudioParser(jurisdiction="Richmond")

# Stream and parse real-time dispatch audio (requires STT)
parser.stream_dispatch_audio(feed_url="https://...")

# Parse transcript to structured event
event = parser.parse_dispatch_transcript(
    transcript="All units, 10-33 at Main and 5th, multiple vehicles involved...",
    timestamp=datetime.utcnow()
)

# Detect multi-jurisdiction coordination
coordinated = parser.detect_multi_jurisdiction_response(
    time_window=timedelta(hours=1)
)
```

**Note**: These are stub implementations. Production use requires:
- API keys and authentication
- Rate limiting and caching
- Speech-to-text integration (Google, AWS, OpenAI Whisper)
- Error handling and retry logic

---

## Virginia Local News Feeds

Added 4 Virginia local news RSS feeds to `feeds.json`:

| Feed | Category | Cooldown |
|------|----------|----------|
| Richmond Times-Dispatch | local/virginia | 300s |
| WRIC ABC 8News | local/virginia | 300s |
| NBC12 News | local/virginia | 300s |
| CBS 6 WTVR | local/virginia | 300s |

These feeds provide hyperlocal context for the Local Threat Monitor agent and enable early detection of Virginia-specific security events.

---

## Integration with Existing System

All new modules integrate seamlessly with the existing codebase:

### In Multi-Agent Analysis

```python
from src.forecasting.agents import run_conversation
from src.forecasting.specialized_agents import get_specialized_agents
from src.forecasting.cascade_modeling import analyze_event_cascade
from src.forecasting.critical_alerts import check_for_critical_events

# Run analysis with specialized agents
result = run_conversation(
    question="What is the probability of military action in Venezuela within 7 days?",
    db_path="data/live.db",
    enabled_agents=[agent.name for agent in get_specialized_agents()]
)

# Check for critical alerts
alerts = check_for_critical_events(
    texts=[item['snippet'] for item in result['context_items']],
    min_confidence=0.6
)

# Analyze cascades
cascades = analyze_event_cascade(
    trigger_domain="military",
    trigger_event=result['question'],
    max_depth=3
)
```

### In Reputation Tracking

```python
from src.forecasting.reputation import ReputationTracker

tracker = ReputationTracker()

# After event occurs, validate predictions
tracker.validate_prediction(
    prediction_id=result['prediction_id'],
    predicted_probability=result['summary']['probability'],
    predicted_confidence=result['summary']['confidence'],
    actual_outcome=True  # Manually verified outcome
)

# Updated reputation automatically affects future predictions
```

---

## Future Enhancements

1. **Real-time Source Integration**: Complete ADS-B, market data, and dispatch audio implementations
2. **Automated Outcome Verification**: Scrape news sources to automatically verify prediction outcomes
3. **Cascade Visualization**: Web UI for interactive cascade pathway exploration
4. **Alert Notification System**: Email/SMS/Slack notifications for critical alerts
5. **Machine Learning Cascade Prediction**: Train models on historical cascades to predict new pathways
6. **Custom Pattern Builder**: UI for users to define custom alert patterns

---

## Testing

Run tests for new modules:

```bash
# Test specialized agents
python -c "from src.forecasting.specialized_agents import *; print(len(get_specialized_agents()))"

# Test cascade modeling
python -c "from src.forecasting.cascade_modeling import analyze_event_cascade; \
  r = analyze_event_cascade('military', 'Test event'); print(r['total_pathways'])"

# Test critical alerts
python -c "from src.forecasting.critical_alerts import check_for_critical_events; \
  r = check_for_critical_events(['test']); print(r['total_alerts'])"

# Test reputation validation
python -c "from src.forecasting.reputation import ReputationTracker; \
  t = ReputationTracker(); print('Reputation system loaded')"
```

---

## Configuration

No additional configuration required - all features work with existing `feeds.json` and database structure. Optional API keys can be added for real-time source integrations.

---

## License & Attribution

These advanced features are part of the Prognosticator geopolitical forecasting system. Use responsibly for analytical purposes only.
