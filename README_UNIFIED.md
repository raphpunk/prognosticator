# 🔮 Prognosticator - Unified Application

A complete geopolitical forecasting system powered by multi-agent AI, featuring local threat monitoring, RSS feed ingestion, and Ollama LLM integration.

**Single entry point. Full GUI configuration. No manual file editing.**

---

## 🎯 What's New (v2.0)

✅ **Single Unified App** - All functionality in one Streamlit dashboard
✅ **GUI Configuration** - Configure everything through the web interface
✅ **Unified Configuration** - Single `prognosticator.json` file (auto-migrates from legacy)
✅ **SQLite Backend** - All settings persisted in `data/config.db`
✅ **Auto-Database Setup** - Initializes on first run
✅ **No Manual Editing** - Everything configurable in GUI

---

## 🚀 Quick Start (5 minutes)

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run setup (creates directories, initializes DB)
python setup.py
```

### 2. Install Ollama
```bash
# Download from https://ollama.ai
# Then start the service:
ollama serve
```

### 3. Pull Models (in another terminal)
```bash
ollama pull llama2
ollama pull gemma:2b
ollama pull qwen2.5:0.5b
```

### 4. Launch App
```bash
streamlit run scripts/app_complete.py
```

Then open `http://localhost:8501` in your browser.

---

## 📋 Configuration

All configuration is done through the GUI. The app stores settings in:
- **JSON**: `prognosticator.json` (for export/version control)
- **Database**: `data/config.db` (runtime configuration)

### Configuration Sections

#### 🤖 AI Models
- Ollama host/port configuration
- Available models list
- Model pulling interface
- Expert agent selection

#### 📡 Data Sources
- RSS feed management (add/edit/disable)
- Feed ingestion controls
- Database optimization tools

#### 🚨 Local Threats
- Enable/disable local threat monitoring
- Minimum severity level filter
- Scrape interval configuration
- Available jurisdictions

#### ⚡ Advanced
- Cache TTL settings
- Database management tools
- Log level configuration
- Data retention policies

---

## 🏗️ Architecture

### Directory Structure
```
/home/legion/work/
├── scripts/
│   ├── app_complete.py        # ← MAIN APP (streamlit run this)
│   ├── app.py                 # (legacy - will be replaced)
│   ├── admin_ui.py            # (legacy)
│   └── dashboard.py           # (legacy)
├── src/forecasting/
│   ├── database_manager.py    # ✨ NEW - DB initialization
│   ├── config_manager.py      # ✨ NEW - Unified config
│   ├── agents.py
│   ├── ollama_utils.py
│   ├── local_threats.py
│   ├── dispatch_discovery.py
│   ├── ingest.py
│   └── ...
├── data/
│   ├── live.db               # Main database
│   ├── config.db             # Configuration database
│   ├── local_threats.db
│   └── feed_health.db
├── config/
│   └── (legacy config files)
├── prognosticator.json       # ← NEW - Unified config file
├── setup.py                  # ← NEW - Setup script
└── requirements.txt
```

### Database Schema

**Articles Table** (`live.db`)
```
- id, title, summary, content
- source_url, article_url, image_url
- published, fetched_at
- relevance_score, bias_score
- country_mentioned, region_mentioned
- key_entities, sentiment, indexed
```

**Predictions Table**
```
- id, scenario, prediction_date
- probability, confidence
- agents_count, context_article_ids
- result, verdict, reasoning
```

**Configuration Table** (`config.db`)
```
- key, value, type
- expires_at, created_at
- description
```

**RSS Feeds Table**
```
- id, name, url, active
- added_at, fetch_error, last_fetch
- article_count, health_score
```

---

## 🔄 Migration from Legacy

The app automatically migrates from older configurations:
- `feeds.json` → `config.db` (on first run)
- `config/feeds.yaml` → `config.db`
- `config/model_config.json` → `config.db`

**Note**: Keep originals for backup. Delete after confirming migration worked.

---

## 📊 Application Tabs

### Main View
- **📊 Dashboard** - Article ingestion stats, top sources, trends
- **🔮 Analysis** - Multi-agent scenario analysis
- **🚨 Threats** - Local threat monitoring by location

### Configuration
- **🎯 Quick Start** - Setup guide
- **🤖 AI Models** - Ollama connection, model management
- **📡 Feeds** - RSS feed configuration
- **🚨 Threats** - Local threat settings
- **⚡ Advanced** - Database, logging, retention

---

## 💻 Using the App

### Running Predictions
1. Go to **🔮 Analysis** tab
2. Enter a question: "What geopolitical disruptions are emerging?"
3. Set lookback period (days) and article count
4. Click **🚀 Analyze**
5. AI experts synthesize recent articles and provide probability estimates

### Monitoring Local Threats
1. Go to **🚨 Threats** tab
2. Enter a ZIP code or district name
3. Click **🔍 Fetch Threats**
4. View dispatch calls with severity levels

### Managing Data Sources
1. Go to ⚙️ **📡 Feeds** tab
2. Edit RSS feed URLs
3. Click **🔄 Fetch All Feeds** to ingest new articles
4. Use **🧹 Optimize Database** to clean up

---

## 🔧 Troubleshooting

### "Cannot reach Ollama"
- ✅ Verify: `ollama serve` is running
- ✅ Check host/port in settings
- ✅ Try: `curl http://localhost:11434/api/models`

### Database errors
- ✅ Check `logs/app.log` for details
- ✅ Run: `python setup.py` to reinitialize
- ✅ Reset database: `rm data/live.db` (deletes all articles!)

### Missing models
- ✅ Run: `ollama pull llama2`
- ✅ Refresh app after pulling

### Slow analysis
- ✅ Reduce number of articles (topk slider)
- ✅ Reduce lookback days
- ✅ Use faster model: `ollama pull qwen2.5:0.5b`

---

## 📈 Performance Tips

1. **Optimize database regularly** (Advanced tab → Database)
2. **Disable unused feeds** (Feeds tab)
3. **Use smaller models** for faster analysis (`gemma:2b`, `qwen2.5:0.5b`)
4. **Archive old articles** (set retention in Advanced settings)
5. **Enable local Ollama** (faster than remote GPT-5)

---

## 🔐 Security Notes

- ✅ All data stored locally (SQLite)
- ✅ No external API calls except RSS feeds
- ✅ Configuration file in JSON (human-readable)
- ✅ Logs accessible for auditing

**Configuration Backup:**
```bash
# Export current config
cp prognosticator.json prognosticator.json.backup

# Export database
cp data/config.db data/config.db.backup
```

---

## 📚 API Reference

### Core Modules

**config_manager.py**
```python
from forecasting.config_manager import UnifiedConfigManager

mgr = UnifiedConfigManager()
config = mgr.get_section("feeds")
mgr.set_section("feeds", updated_config)
mgr.save_to_json()
```

**database_manager.py**
```python
from forecasting.database_manager import ensure_database_ready

ensure_database_ready()  # Initialize on startup
```

**agents.py**
```python
from forecasting.agents import run_conversation

result = run_conversation(
    question="What's happening in the Middle East?",
    db_path="data/live.db",
    days=30,
    topk=10
)
```

---

## 🐛 Development

### Running Setup
```bash
python setup.py           # One-time setup
```

### Starting Development
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Streamlit
streamlit run scripts/app_complete.py
```

### Debugging
```bash
# Check logs
tail -f logs/app.log

# Test database
sqlite3 data/live.db ".tables"

# Test Ollama
curl http://localhost:11434/api/models
```

---

## 📝 Version History

### v2.0 (Current)
- ✅ Unified application
- ✅ GUI configuration system
- ✅ SQLite config database
- ✅ Auto database initialization
- ✅ Legacy configuration migration

### v1.0
- Multi-agent forecasting
- Local threat monitoring
- RSS feed ingestion
- Separate admin UI

---

## 📞 Support

For issues:
1. Check logs: `logs/app.log`
2. Run setup again: `python setup.py`
3. Verify Ollama: `ollama serve` (check port 11434)
4. Review configuration: `prognosticator.json`

---

## 📄 License

Prognosticator is provided as-is for research and forecasting purposes.

---

**🚀 Ready? Launch the app:**
```bash
streamlit run scripts/app_complete.py
```
