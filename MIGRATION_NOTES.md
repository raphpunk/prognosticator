# Migration Notes

## Feed System Consolidation (November 2025)

### What Changed
The legacy `scripts/ingest_rss_feeds.py` has been **removed** in favor of the more capable trending feeds system.

### Old Way (Removed)
```bash
# ❌ This no longer works
python scripts/ingest_rss_feeds.py
```

**Limitations:**
- Only supported RSS feeds
- Required manual `feeds.json` editing
- Basic feedparser only
- No Google Trends or web scraping
- No signal normalization

### New Way (Use This)
```bash
# ✅ Production integration
python src/forecasting/trending_feeds_integration.py

# ✅ View statistics
python src/forecasting/trending_feeds_integration.py --stats

# ✅ Demo/test the module
python scripts/demo_trending_feeds.py
```

**Advantages:**
- Supports **RSS + Google Trends + Exploding Topics + Web Scraping**
- Unified `Signal` schema for all sources
- YAML configuration (`config/feeds.yaml`)
- Better error handling and logging
- Metadata preservation
- Compatible with existing `feeds.json` via admin UI

### Configuration
The new system uses `config/feeds.yaml` but the admin UI (`scripts/app.py`) still manages `feeds.json` for backward compatibility. Both work together seamlessly.

### Migration Path
1. **No action needed** - your existing `feeds.json` still works
2. *(Optional)* Create `config/feeds.yaml` to enable advanced sources:
   ```yaml
   scrapers:
     google_trends:
       enabled: true
       geo: US
   ```
3. Run the new integration: `python src/forecasting/trending_feeds_integration.py`

### Documentation
- **Full Guide**: `docs/TRENDING_FEEDS.md`
- **Quick Reference**: `docs/TRENDING_FEEDS_QUICKREF.md`
- **Summary**: `docs/TRENDING_FEEDS_SUMMARY.md`

---

**No breaking changes** - everything continues to work. The new system is simply more capable.
