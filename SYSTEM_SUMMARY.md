# 🔮 Prognosticator v2.0 - Unified Application Summary

## Executive Summary

Prognosticator v2.0 is a complete consolidation of the forecasting system into a single unified application with:
- ✅ **One entry point** (`scripts/app_complete.py`)
- ✅ **One configuration system** (GUI-based, SQLite-backed)
- ✅ **All features integrated** (analytics, threats, feeds, models)
- ✅ **Automated setup** (no manual configuration needed)
- ✅ **Legacy migration** (auto-imports old settings)

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           Streamlit Web Interface (app_complete.py)    │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Tabs: Dashboard | Analysis | Threats              │ │
│  │ Settings: Models | Feeds | Threats | Advanced    │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│           Configuration Management Layer                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ config_manager.py                                 │ │
│  │ - UnifiedConfigManager class                      │ │
│  │ - SQLite config.db backend                        │ │
│  │ - prognosticator.json export                      │ │
│  │ - Legacy migration (feeds.json, feeds.yaml, etc) │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Database Layer                             │
│  ┌─────────────────┬──────────────┬─────────────────┐  │
│  │  live.db        │  config.db   │  Threat DBs    │  │
│  │  - Articles     │  - Settings  │  - Events      │  │
│  │  - Predictions  │  - Feeds     │  - Health      │  │
│  │  - Agents       │  - Cache     │  - Tracking    │  │
│  │  - Analysis     │  - Models    │                │  │
│  └─────────────────┴──────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│           Forecasting Engine Modules                    │
│  ┌──────────────┬──────────────┬──────────────────┐    │
│  │ Agents       │ Data Ingest  │ Threat Monitor   │    │
│  │ - 16 experts │ - RSS feeds  │ - Dispatch APIs  │    │
│  │ - Consensus  │ - Trending   │ - ZIP scraping   │    │
│  │ - Reasoning  │ - Storage    │ - Heuristics     │    │
│  └──────────────┴──────────────┴──────────────────┘    │
│  ┌──────────────┬──────────────┬──────────────────┐    │
│  │ Ollama LLM   │ Models       │ Utilities        │    │
│  │ - HTTP API   │ - Management │ - Date parsing   │    │
│  │ - Local      │ - Pulling    │ - Cache          │    │
│  │ - Remote     │ - Listing    │ - Storage        │    │
│  └──────────────┴──────────────┴──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 New Files Added

### Core System
- **`src/forecasting/config_manager.py`** (400+ lines)
  - `UnifiedConfigManager` class
  - SQLite config database
  - Legacy migration logic
  - Feed management API
  - JSON import/export

- **`src/forecasting/database_manager.py`** (350+ lines)
  - `DatabaseManager` class
  - Schema initialization
  - Table management
  - `DataRetentionManager` for archiving
  - Database verification

### Application
- **`scripts/app_complete.py`** (1,000+ lines)
  - Unified Streamlit application
  - GUI configuration panels
  - All main features integrated
  - Database auto-initialization
  - Configuration auto-migration

### Setup & Documentation
- **`setup.py`** (200+ lines)
  - One-command initialization
  - Dependency verification
  - Directory creation
  - Database setup
  - Configuration migration

- **`README_UNIFIED.md`** (300+ lines)
  - Complete feature documentation
  - Architecture overview
  - Configuration reference
  - Usage examples
  - Troubleshooting

- **`QUICK_START.md`** (200+ lines)
  - 5-minute quick start
  - Common workflows
  - File locations
  - Troubleshooting
  - Keyboard shortcuts

- **`MIGRATION_GUIDE.md`** (250+ lines)
  - v1.0 → v2.0 migration steps
  - Configuration migration
  - Rollback instructions
  - Checklist

---

## 🔄 Configuration System

### Two-Tier Configuration

#### 1. JSON Configuration (`prognosticator.json`)
```json
{
  "app": { "name": "Prognosticator", "version": "2.0" },
  "ollama": { "host": "http://localhost", "port": 11434 },
  "feeds": { "rss": [...], "trending": {...} },
  "local_threats": { "enabled": true, "min_severity": 3 },
  "advanced": { "cache_ttl_seconds": 900, ... }
}
```

**Purpose**: Export/version control, human-readable format

#### 2. SQLite Configuration (`data/config.db`)
```
Tables:
- config (key-value pairs)
- config_sections (large config blocks)
- rss_feeds (feed management)
- model_config (model settings)
```

**Purpose**: Runtime configuration, fast access, type safety

### Configuration Flow

```
User Input (GUI)
    ↓
Streamlit Component
    ↓
config_manager.set_value()
    ↓
SQLite config.db updated
    ↓
prognosticator.json updated (on save)
    ↓
App uses updated values
    ↓
Settings persist across restarts
```

### Automatic Migration

When app starts:
1. Checks for `data/config.db`
2. If missing, creates new
3. Looks for legacy files:
   - `feeds.json` → imports to config.db
   - `config/feeds.yaml` → imports to config.db
   - `config/model_config.json` → imports to config.db
4. Creates `prognosticator.json` with merged settings
5. All old settings now in GUI

---

## 🗄️ Database Schema

### Articles Table (`live.db`)
```sql
- id, title, summary, content
- source_url, article_url, image_url
- published, fetched_at
- relevance_score, bias_score
- country_mentioned, region_mentioned
- key_entities, sentiment, indexed
```

### Configuration Table (`config.db`)
```sql
-- Key-value settings
config (key, value, type, updated_at, description)

-- Large config sections
config_sections (section, data, updated_at, description)

-- RSS feed list
rss_feeds (id, name, url, active, added_at, fetch_error, last_fetch, article_count)

-- Model settings
model_config (name, value, updated_at)
```

---

## 🎨 User Interface

### Main Navigation
```
Sidebar:
  ⚙️ Configuration
    • 🎯 Quick Start
    • 🤖 AI Models
    • 📡 Data Sources
    • 🚨 Local Threats
    • ⚡ Advanced

Main Area:
  • 📊 Dashboard - Stats, ingestion metrics
  • 🔮 Analysis - Multi-agent predictions
  • 🚨 Threats - Local dispatch monitoring
```

### Configuration Panels

#### 🤖 AI Models
- Ollama host/port settings
- Connection test button
- Available models list
- Model pulling interface
- Expert agent selector

#### 📡 Data Sources
- RSS feed editor (add/edit/delete)
- Feed status indicators
- Manual fetch button
- Database optimization
- Health tracking

#### 🚨 Local Threats
- Enable/disable toggle
- Severity filter
- Scrape interval
- Jurisdiction selector
- Location search

#### ⚡ Advanced
- Cache TTL settings
- Database stats and tools
- Log level selector
- Log viewer
- Retention policies

---

## 🚀 Usage Workflows

### First-Time Setup
```bash
python setup.py              # Initialize everything
ollama serve                 # Start Ollama (Terminal 1)
ollama pull llama2          # Pull a model (Terminal 2)
streamlit run scripts/app_complete.py  # Launch app (Terminal 3)
```

### Analyze a Scenario
1. Navigate to 🔮 **Analysis** tab
2. Enter question: "What disruptions emerging?"
3. Set lookback (7-90 days) and article count (3-20)
4. Click 🚀 **Analyze**
5. Wait 1-3 minutes for multi-agent synthesis
6. View probability, confidence, expert opinions

### Monitor Local Threats
1. Navigate to 🚨 **Threats** tab
2. Enter ZIP code or location
3. Click 🔍 **Fetch Threats**
4. View dispatch calls by severity level
5. Filter by minimum severity in ⚙️ Settings

### Add RSS Feed
1. Go to ⚙️ → 📡 **Data Sources**
2. Click expander for new feed slot
3. Enter feed name and URL
4. Click 🔄 **Fetch All Feeds**
5. New articles appear in 📊 Dashboard

---

## 🔌 API Reference

### Configuration Manager
```python
from forecasting.config_manager import UnifiedConfigManager

mgr = UnifiedConfigManager()

# Get/set values
mgr.set_value("key", "value", type_="string")
value = mgr.get_value("key", default=None)

# Get/set sections
mgr.set_section("feeds", {...})
section = mgr.get_section("feeds")

# RSS feed operations
mgr.add_rss_feed("BBC", "https://...")
feeds = mgr.get_rss_feeds(active_only=True)
mgr.update_rss_feed_status("BBC", False)

# Import/export
mgr.load_from_json()
mgr.save_to_json()
```

### Database Manager
```python
from forecasting.database_manager import ensure_database_ready, DataRetentionManager

# Initialize
ensure_database_ready()

# Get statistics
retention = DataRetentionManager()
stats = retention.get_database_stats()

# Maintenance
retention.archive_old_articles(days=90)
retention.prune_old_predictions(days=180)
```

---

## 📊 Key Metrics & Monitoring

### Dashboard Metrics
- Total articles ingested
- Number of unique sources
- Latest article timestamp
- Top domains by article count

### Analysis Metrics
- Probability estimate (0-100%)
- Confidence level (0-100%)
- Number of experts consulted
- Number of sources analyzed

### Database Metrics
- Total articles
- Total predictions
- Total agents
- Database size

### Health Metrics
- Feed fetch success rate
- Feed response time
- Article quality score
- Cache hit rate

---

## 🔐 Data & Security

### Data Storage
- ✅ All data stored locally (no cloud)
- ✅ SQLite databases (portable)
- ✅ Configuration in JSON (human-readable)
- ✅ Encrypted if database file encrypted

### Access Control
- ✅ Local network only (by default)
- ✅ No API keys required
- ✅ Optional remote Ollama (if configured)

### Data Retention
- Articles: 90 days (configurable)
- Predictions: 180 days (configurable)
- Logs: 30 days (configurable)
- Cache: TTL-based (default 15 min)

### Backup
```bash
# Configuration
cp prognosticator.json prognosticator.json.backup
cp data/config.db data/config.db.backup

# Data
cp data/live.db data/live.db.backup
```

---

## 🐛 Debugging

### Enable Debug Logging
```
⚙️ Configuration → ⚡ Advanced → Log Level: DEBUG
```

### View Logs
```bash
tail -f logs/app.log
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Cannot reach Ollama" | Start: `ollama serve`, Test in GUI |
| "No articles showing" | Fetch: 📡 Data Sources → 🔄 Fetch All |
| "Analysis too slow" | Reduce articles/days sliders |
| "Database errors" | Run: `python setup.py`, Check logs |
| "Config not saving" | Click: 💾 Save Configuration button |

---

## 📈 Performance Optimization

### For Speed
- Use smaller models: `qwen2.5:0.5b` or `gemma:2b`
- Reduce article count (topk slider)
- Reduce lookback period
- Optimize database: ⚙️ → ⚡ Advanced → 🧹 Optimize DB

### For Accuracy
- Use larger models: `llama2` or `mistral`
- Increase article count
- Increase lookback period
- Enable more expert agents

### For Storage
- Archive old articles: ⚙️ → ⚡ Advanced
- Disable inactive feeds: 📡 Data Sources
- Run VACUUM: Database Optimization

---

## 🔄 Maintenance Tasks

### Daily
- Monitor dashboard for new articles
- Check feed health (if manual ingestion)
- Review any error logs

### Weekly
- Archive old articles (automatic)
- Clean up cache (automatic)
- Verify backup copies exist

### Monthly
- Review database size
- Optimize database: 🧹 Optimize DB
- Check model updates: `ollama list`

### Quarterly
- Full backup: `cp data data.backup -r`
- Review retention policies
- Update application: `git pull && pip install -r requirements.txt`

---

## 🎓 Advanced Configuration

### Custom RSS Feeds
Edit in GUI: 📡 **Data Sources** → Edit feed URLs

### Remote Ollama
In GUI: 🤖 **AI Models** → Enter remote host

### High-Performance Setup
```
- Use faster SSD for data/ directory
- Configure larger cache: ⚙️ → ⚡ Advanced
- Increase article retention for better analysis
- Pull multiple models for parallel queries
```

### Integration with External Systems
```python
# Import modules to use in custom scripts
import sys
sys.path.insert(0, "src")

from forecasting.agents import run_conversation
from forecasting.config_manager import UnifiedConfigManager
from forecasting.database_manager import DataRetentionManager

# Use API to integrate with your systems
result = run_conversation(question="...", db_path="data/live.db")
```

---

## 📞 Support & Resources

### Documentation
- **README_UNIFIED.md** - Complete reference
- **QUICK_START.md** - 5-minute setup
- **MIGRATION_GUIDE.md** - Upgrading from v1.0

### Troubleshooting
1. Check logs: `logs/app.log`
2. Run setup: `python setup.py`
3. Test connections: Use GUI test buttons
4. Review error messages (often have solutions)

### Code Resources
- Configuration API: `src/forecasting/config_manager.py`
- Database API: `src/forecasting/database_manager.py`
- Main app: `scripts/app_complete.py` (examples in code)

---

## ✅ Verification Checklist

- [ ] Python 3.10+
- [ ] All dependencies installed
- [ ] `python setup.py` successful
- [ ] `prognosticator.json` created
- [ ] `data/config.db` created
- [ ] Ollama installed and running
- [ ] `scripts/app_complete.py` launches
- [ ] 🧪 Test Connection works
- [ ] First analysis completes
- [ ] Local threats working
- [ ] RSS feeds ingesting

---

## 🎉 Success!

You now have a fully unified, production-ready forecasting system:
- ✅ Single app entry point
- ✅ Complete GUI configuration
- ✅ Persistent data storage
- ✅ Automatic setup and migration
- ✅ All features integrated

**Next**: Launch the app and start analyzing!

```bash
streamlit run scripts/app_complete.py
```
