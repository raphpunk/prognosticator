# 🔄 Migration Guide: Prognosticator v1.0 → v2.0

## What Changed

Prognosticator v2.0 consolidates all functionality into a single unified application with GUI-based configuration. This makes it much easier to use - **no more manual file editing**.

---

## 🗂️ File Migrations

### Configuration Files

**v1.0** had 3 separate configuration files:
```
feeds.json                  # Ollama settings + feeds
config/feeds.yaml         # Trending feeds config
config/model_config.json  # GPT-5 remote model config
```

**v2.0** consolidates into:
```
prognosticator.json       # Main config (auto-created)
data/config.db           # SQLite settings database
```

### Application Scripts

**v1.0** had multiple entry points:
```
scripts/app.py            # Main dashboard
scripts/admin_ui.py       # Admin interface
scripts/dashboard.py      # Secondary dashboard
```

**v2.0** has one entry point:
```
scripts/app_complete.py   # ← Single unified app
```

---

## 🚀 Migration Steps

### Step 1: Backup Everything
```bash
# Backup your current configuration
cp feeds.json feeds.json.backup
cp config/feeds.yaml config/feeds.yaml.backup
cp config/model_config.json config/model_config.json.backup
cp data/live.db data/live.db.backup
```

### Step 2: Install New Files
```bash
# Get the latest version
git pull  # or download latest

# Install any new dependencies
pip install -r requirements.txt
```

### Step 3: Run Setup
```bash
python setup.py
```

This will:
- ✅ Create directories
- ✅ Initialize `prognosticator.json`
- ✅ Create `data/config.db`
- ✅ Auto-migrate settings from old files

### Step 4: Verify Migration
```bash
# Check if prognosticator.json was created
ls -la prognosticator.json

# Check if config database was created
ls -la data/config.db

# Verify config was imported
python -c "
import sys
sys.path.insert(0, 'src')
from forecasting.config_manager import UnifiedConfigManager
mgr = UnifiedConfigManager()
print('Sections:', mgr.list_sections())
"
```

### Step 5: Launch New App
```bash
streamlit run scripts/app_complete.py
```

---

## 📊 What Gets Migrated

### Automatically Migrated ✅
- RSS feed URLs → `prognosticator.json`
- Ollama host/port settings → `config.db`
- Local threat settings → `config.db`
- Trending feeds configuration → `config.db`
- GPT-5 model settings → `config.db`
- All articles in `data/live.db` (unchanged)

### Manual Updates ⚠️
- Any custom feeds not in the default list
- Custom CSS/styling (if any)
- Local cron jobs (manually re-add if needed)

---

## 🎯 Configuration in v2.0

All settings are now accessible through the GUI:

### In the App:
1. Click **⚙️ Configuration** (top right)
2. Choose section:
   - **🎯 Quick Start** - Setup guide
   - **🤖 AI Models** - Ollama settings
   - **📡 Feeds** - RSS configuration
   - **🚨 Threats** - Local threat settings
   - **⚡ Advanced** - Database, logging

### Changes From v1.0:
| Setting | v1.0 | v2.0 |
|---------|------|------|
| Ollama host | `feeds.json` | GUI → 🤖 AI Models |
| RSS feeds | `feeds.json` | GUI → 📡 Feeds |
| Trending feeds | `config/feeds.yaml` | GUI → 📡 Feeds |
| Model config | `config/model_config.json` | GUI → 🤖 AI Models |
| Local threats | Code config | GUI → 🚨 Threats |

---

## 🔍 Troubleshooting Migration

### Issue: "Cannot find old configuration"
```
✅ Solution:
The migration tool looks for these files:
  - feeds.json (in project root)
  - config/feeds.yaml
  - config/model_config.json
  
If they don't exist, new defaults are created.
```

### Issue: "Settings didn't migrate"
```
✅ Solution:
1. Check logs: tail -f logs/app.log
2. Manually check old files exist
3. Run: python setup.py again
4. Verify: python -c "from forecasting.config_manager import initialize_config_system; initialize_config_system()"
```

### Issue: "Analysis not finding articles"
```
✅ Solution:
The old data/live.db is preserved.
Migration doesn't touch articles.
They should still be there.
```

### Issue: "Can't reach Ollama"
```
✅ Solution:
1. Check Ollama is running: ollama serve
2. Verify settings in GUI: 🤖 AI Models
3. Test connection: Click 🧪 Test Connection
4. Check URL format: Should be http://localhost (not localhost:11434)
```

---

## 📚 Old Files - Keep or Delete?

### Safe to Delete
```bash
rm scripts/admin_ui.py        # Functionality now in app_complete.py
rm scripts/dashboard.py       # Functionality now in app_complete.py
rm config/feeds.yaml          # Migrated to config.db
rm config/model_config.json   # Migrated to config.db
```

### Keep for Reference
```bash
# Keep originals as backup in case rollback needed
cp feeds.json feeds.json.backup
cp scripts/app.py scripts/app.py.v1_backup
```

### Never Delete
```bash
# These contain your data!
data/live.db                  # All articles and predictions
data/local_threats.db         # Local threat history
data/feed_health.db           # Feed performance metrics
```

---

## 🔄 Rollback to v1.0

If you need to go back:

```bash
# Restore from backup
cp feeds.json.backup feeds.json
cp config/feeds.yaml.backup config/feeds.yaml
cp config/model_config.json.backup config/model_config.json

# Remove new files
rm prognosticator.json
rm data/config.db

# Revert code
git checkout HEAD~1  # Or restore from backup

# Restart app
streamlit run scripts/app.py  # Old app
```

---

## 🆕 New Features in v2.0

### ✨ New Capabilities
- **GUI Configuration** - No more manual JSON editing
- **Unified Database** - Single source of truth for settings
- **Better UI** - Organized tabs and status indicators
- **Auto-Migration** - Old settings automatically imported
- **Database Management** - Built-in optimization and stats
- **Dependency Checking** - Verifies packages on startup

### 🚀 Improved UX
- All settings in one place
- Save/load configuration with one click
- Real-time validation
- Error messages with solutions
- Database optimization tools

### 🔧 Developer Features
- SQLite config database
- Structured configuration API
- Better logging
- Database migration system
- Automated setup

---

## 📋 Migration Checklist

- [ ] Backup all current data
- [ ] Run `python setup.py`
- [ ] Verify `prognosticator.json` created
- [ ] Verify `data/config.db` created
- [ ] Start Ollama: `ollama serve`
- [ ] Launch app: `streamlit run scripts/app_complete.py`
- [ ] Test database connection
- [ ] Test Ollama connection
- [ ] Try first analysis
- [ ] Verify RSS feeds working
- [ ] Check local threats working
- [ ] Delete old config files (optional)
- [ ] Done! ✅

---

## 🎓 Learning the New UI

### Configuration Workflow
```
1. Open app: http://localhost:8501
2. Click ⚙️ Configuration (top right)
3. Select a settings section
4. Make changes
5. Click 💾 Save Configuration (bottom of sidebar)
6. Changes persisted to prognosticator.json and config.db
```

### Using Analysis
```
1. Click main content area → 🔮 Analysis
2. Enter your question
3. Set lookback days and article count
4. Click 🚀 Analyze
5. Wait 1-3 minutes
6. View results
```

### Monitoring Local Threats
```
1. Click main content area → 🚨 Threats
2. Enter ZIP code or location
3. Click 🔍 Fetch Threats
4. View dispatch calls by severity
```

---

## 📞 Support

If you encounter issues after migration:

1. **Check logs**: `tail -f logs/app.log`
2. **Run setup again**: `python setup.py`
3. **Verify connections**: Use GUI test buttons
4. **Review README**: `README_UNIFIED.md`
5. **Check quick start**: `QUICK_START.md`

---

## ✅ Success Indicators

You've successfully migrated when:
- ✅ App launches without errors
- ✅ Configuration settings visible in GUI
- ✅ Database shows articles count
- ✅ Ollama connection works
- ✅ First analysis runs successfully
- ✅ RSS feeds ingesting new articles
- ✅ Configuration saves and persists

---

**Welcome to Prognosticator v2.0!** 🎉

Your unified, GUI-based forecasting system is ready.
