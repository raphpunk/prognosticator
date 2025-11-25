# ⚡ Prognosticator v2.0 - Quick Reference

## TL;DR - Get Running in 3 Minutes

```bash
# 1. Setup (once)
python setup.py

# 2. Start Ollama (Terminal 1)
ollama serve

# 3. Pull model (Terminal 2)
ollama pull llama2

# 4. Launch app (Terminal 3)
streamlit run scripts/app_complete.py

# 5. Open browser
http://localhost:8501
```

---

## Main Workflows

### Run Analysis
```
🔮 Analysis Tab
→ Enter question
→ Set days (7-90) & articles (3-20)
→ Click 🚀 Analyze
→ Wait 1-3 minutes
→ View results with probability
```

### Check Local Threats
```
🚨 Threats Tab
→ Enter ZIP code
→ Click 🔍 Fetch
→ View calls by severity
```

### Configure System
```
⚙️ Configuration → Select Tab
→ Make changes
→ Click 💾 Save Configuration
→ Settings persist
```

### Add RSS Feed
```
⚙️ Configuration → 📡 Feeds
→ Edit URL in expander
→ Click 🔄 Fetch All Feeds
→ Check dashboard for new articles
```

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `python setup.py` | Initialize everything |
| `ollama serve` | Start Ollama service |
| `ollama pull llama2` | Download model |
| `ollama list` | Show installed models |
| `streamlit run scripts/app_complete.py` | Launch app |
| `tail -f logs/app.log` | View logs |
| `sqlite3 data/live.db` | Query database |

---

## File Locations

| File | Purpose |
|------|---------|
| `scripts/app_complete.py` | Launch this |
| `prognosticator.json` | Config file |
| `data/live.db` | Articles database |
| `data/config.db` | Settings database |
| `logs/app.log` | Debug logs |

---

## Settings Locations

| Setting | Location |
|---------|----------|
| Ollama host/port | ⚙️ → 🤖 AI Models |
| RSS feeds | ⚙️ → 📡 Feeds |
| Local threats | ⚙️ → 🚨 Threats |
| Cache, logging | ⚙️ → ⚡ Advanced |

---

## Keyboard Shortcuts (Streamlit)

| Key | Action |
|-----|--------|
| `R` | Rerun app |
| `C` | Clear cache |
| `V` | Toggle theme |

---

## Common Issues

| Problem | Solution |
|---------|----------|
| "Cannot reach Ollama" | Start: `ollama serve`, Test in GUI |
| No articles | Go to 📡 Feeds → 🔄 Fetch All |
| Analysis slow | Reduce articles/days sliders |
| Config not saving | Click 💾 Save Configuration |
| Database error | Check `logs/app.log` |

---

## Tips

- Use 4+ hour lookback for trend analysis
- 10-15 articles good balance (speed vs. accuracy)
- Save config before major changes
- Check logs if anything fails
- Optimize DB monthly: ⚙️ → ⚡ Advanced → 🧹

---

## Folders Used

| Folder | Purpose |
|--------|---------|
| `data/` | Databases |
| `logs/` | Application logs |
| `config/` | Legacy configs (optional) |
| `src/` | Python modules |
| `scripts/` | Applications |

---

## Next Steps

1. ✅ Run `python setup.py`
2. ✅ Start Ollama
3. ✅ Launch app
4. ✅ Read `README_UNIFIED.md` for full guide
5. ✅ Try first analysis

**Done!** You have a working forecasting system.
