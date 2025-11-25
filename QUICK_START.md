# 🚀 Prognosticator v2.0 - Quick Reference

## TL;DR

```bash
# 1. One-time setup
python setup.py

# 2. Start Ollama (Terminal 1)
ollama serve

# 3. Pull a model (Terminal 2)
ollama pull llama2

# 4. Launch app (Terminal 3)
streamlit run scripts/app_complete.py

# 5. Open browser
http://localhost:8501
```

---

## Key Changes from v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Entry Point | Multiple scripts | **Single: `app_complete.py`** |
| Configuration | 3 JSON/YAML files | **Single: `prognosticator.json`** |
| Configuration Method | Manual file editing | **GUI panels** |
| Database | Multiple SQLite files | **Unified `data/live.db`** |
| Config Storage | JSON only | **JSON + SQLite `data/config.db`** |
| Setup | Manual directory creation | **Automated `python setup.py`** |
| Admin UI | Separate `admin_ui.py` | **Integrated in main app** |

---

## 🎯 Main Workflows

### Analyze a Scenario
```
📊 Dashboard → 🔮 Analysis
↓
Enter question (e.g., "Risk of supply chain disruption?")
↓
Select lookback period (7-90 days)
↓
Select article count to analyze (3-20)
↓
Click 🚀 Analyze
↓
Wait 1-3 minutes for multi-agent analysis
↓
View probability, confidence, verdict
```

### Check Local Threats
```
🚨 Threats tab
↓
Enter ZIP code or location
↓
Click 🔍 Fetch Threats
↓
View dispatch calls by severity
```

### Configure AI Models
```
⚙️ Configuration → 🤖 AI Models
↓
Enter Ollama host/port (default: localhost:11434)
↓
Click 🧪 Test Connection
↓
View available models
↓
(Optional) Pull new model by name
```

### Add/Edit RSS Feeds
```
⚙️ Configuration → 📡 Feeds
↓
Edit feed URLs in expanders
↓
Click 🔄 Fetch All Feeds
↓
Check Dashboard for new articles
```

---

## 📂 File Locations

| File | Purpose |
|------|---------|
| `scripts/app_complete.py` | **← Launch this** |
| `prognosticator.json` | Main config (auto-created) |
| `data/live.db` | Articles, predictions, analysis |
| `data/config.db` | App settings and RSS feeds |
| `logs/app.log` | Debugging information |
| `src/forecasting/config_manager.py` | Config system |
| `src/forecasting/database_manager.py` | Database system |

---

## 💾 Data Management

### Backup Configuration
```bash
cp prognosticator.json prognosticator.json.backup
cp data/config.db data/config.db.backup
```

### Export Articles
```bash
# SQL query - export to CSV
sqlite3 data/live.db ".mode csv" ".headers on" \
  "SELECT title, source_url, published FROM articles" > articles.csv
```

### Reset Application
```bash
# WARNING: Deletes all articles and analysis
rm data/live.db
rm data/config.db

# Then restart app (will reinitialize)
streamlit run scripts/app_complete.py
```

---

## 🔧 Common Tasks

### Test Ollama Connection
```
⚙️ Configuration → 🤖 AI Models → 🧪 Test Connection
```

### View Database Stats
```
⚙️ Configuration → ⚡ Advanced → Database metrics
```

### Optimize Database
```
⚙️ Configuration → ⚡ Advanced → 🧹 Optimize DB
```

### Check Application Logs
```bash
tail -f logs/app.log
```

### List Installed Models
```bash
ollama list
```

### Pull a New Model
```bash
ollama pull mistral      # or any model name
```

### Check Ollama Service
```bash
curl http://localhost:11434/api/models
```

---

## ⚙️ Configuration Options

### Ollama (AI Models tab)
- **Host**: Ollama server address (default: `http://localhost`)
- **Port**: Ollama port (default: `11434`)
- **Models**: Auto-detected from Ollama

### RSS Feeds (Feeds tab)
- **Feed URLs**: Edit to add/remove sources
- **Active Status**: Enable/disable feeds
- **Fetch Button**: Ingest all feeds manually

### Local Threats (Threats tab)
- **Min Severity**: Filter dispatch calls (1-5)
- **Scrape Interval**: How often to check (seconds)

### Advanced (Advanced tab)
- **Cache TTL**: Cache expiration time
- **Log Level**: DEBUG, INFO, WARNING, ERROR
- **Database**: Optimization and stats

---

## 🐛 Troubleshooting

### Problem: "Cannot reach Ollama"
```
✅ Solution:
1. Ensure Ollama is running: ollama serve
2. Check in AI Models tab: 🧪 Test Connection
3. Verify: curl http://localhost:11434/api/models
```

### Problem: No articles showing
```
✅ Solution:
1. Go to Feeds tab → 🔄 Fetch All Feeds
2. Wait 30 seconds for feeds to ingest
3. Check Dashboard for updated count
```

### Problem: Analysis takes too long
```
✅ Solution:
1. Reduce "Articles" slider (topk)
2. Reduce "Days" slider
3. Use faster model: ollama pull qwen2.5:0.5b
```

### Problem: Database errors
```
✅ Solution:
1. Check logs: tail -f logs/app.log
2. Run setup: python setup.py
3. If corrupted: rm data/live.db (WARNING: loses data!)
```

---

## 📊 Example Scenarios

### "Analyze geopolitical risks in next 3 months"
- Days: 30
- Articles: 10
- Question: "What are emerging geopolitical risks?"

### "Quick threat assessment"
- Days: 7
- Articles: 5
- Question: "Any major disruptions happening now?"

### "Deep market analysis"
- Days: 90
- Articles: 20
- Question: "What supply chain disruptions are forming?"

---

## 🔄 Update & Maintenance

### Check for Updates
```bash
git status  # If using git repository
```

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Run Setup Again
```bash
python setup.py  # Safe to run multiple times
```

---

## 📖 Learn More

- **Full Documentation**: `README_UNIFIED.md`
- **Trending Feeds**: `docs/TRENDING_FEEDS.md`
- **Local Threats**: `docs/LOCAL_THREATS.md`
- **API Reference**: Source code docstrings

---

## 🎓 Keyboard Shortcuts (Streamlit)

| Key | Action |
|-----|--------|
| `R` | Rerun app |
| `C` | Clear cache |
| `V` | Toggle dark/light theme |

---

## 📝 Notes

- **First run**: Setup initializes database (~30 seconds)
- **First analysis**: May take 2-3 minutes (model loading + processing)
- **Configuration**: Changes saved to `prognosticator.json` automatically
- **Data retention**: Articles archived after 90 days (configurable)

---

## 🚀 Next Steps

1. ✅ Run `python setup.py`
2. ✅ Start Ollama: `ollama serve`
3. ✅ Launch app: `streamlit run scripts/app_complete.py`
4. ✅ Try first analysis: Go to 🔮 Analysis tab
5. ✅ Customize settings: Use ⚙️ Configuration tabs

**Questions?** Check `logs/app.log` for error details.
