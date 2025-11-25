# Dispatch URL Discovery System

## Overview

The dispatch discovery system uses LLM technology to automatically discover police dispatch URLs for any jurisdiction worldwide. Instead of manually configuring dispatch URLs or limiting the system to hardcoded locations, users can add new jurisdictions dynamically.

## How It Works

### 1. Preconfigured Jurisdictions (No LLM Required)

The system starts with a set of pre-verified dispatch jurisdictions in `config/dispatch_jurisdictions.json`. These are production-tested and don't require LLM queries:

```json
{
  "jurisdictions": {
    "chesterfield_county_va": {
      "name": "Chesterfield County, Virginia",
      "region": "Virginia",
      "country": "USA",
      "dispatch_urls": ["https://www.chesterfield.gov/3999/Active-Police-Calls"],
      "identifiers": ["23112", "23235", ...],
      "scraper_type": "table"
    }
  }
}
```

### 2. Dynamic Discovery (LLM-Based)

When a user requests a jurisdiction not in preconfigured data:

1. **Query LLM**: Uses a small model (phi3:mini, ~2GB) to discover dispatch URLs
2. **Cache Results**: Saves discovered URLs in SQLite to avoid repeated queries
3. **Extend Config**: Optionally adds new jurisdictions to the config file

### 3. Discovery Flow

```
User Input (Jurisdiction Name)
    ↓
Check Preconfigured Jurisdictions
    ├─ Found? → Use immediately (no LLM)
    └─ Not Found? → Continue
    ↓
Check SQLite Cache (24h TTL)
    ├─ Found? → Use cached data
    └─ Expired/Missing? → Continue
    ↓
Query LLM (phi3:mini)
    ├─ Get JSON with URLs, identifiers, metadata
    └─ Cache result in SQLite
    ↓
Return discovered URLs to scraper
```

## Usage

### Adding a New Jurisdiction (Interactive)

```bash
python scripts/discover_new_jurisdiction.py "Los Angeles County California"
```

This will:
1. Query the LLM for dispatch URLs
2. Cache the results
3. Extend `config/dispatch_jurisdictions.json` with the new jurisdiction

### Programmatic Usage

```python
from src.forecasting.dispatch_discovery import discover_and_cache_dispatch_urls

# Discover URLs (checks cache, then LLM)
result = discover_and_cache_dispatch_urls("New York City")

if result.get("urls"):
    print(f"Found {len(result['urls'])} URLs:")
    for url in result["urls"]:
        print(f"  - {url}")
else:
    print(f"Not found (error: {result.get('error')})")
```

### In Streamlit UI

Users can enter any jurisdiction name in the "🚨 Local Threats" tab:

1. Enter jurisdiction name
2. System checks preconfigured and cache
3. If not found, queries LLM
4. Results cached for future use
5. Proceeds with scraping dispatch data

## API Reference

### `discover_and_cache_dispatch_urls(jurisdiction, cache_db, model, ttl_hours)`

Discovers dispatch URLs with intelligent caching.

**Args:**
- `jurisdiction` (str): Jurisdiction name (e.g., "Richmond Virginia")
- `cache_db` (str): Path to SQLite cache (default: "data/dispatch_cache.db")
- `model` (str): LLM model to use (default: "phi3:mini")
- `ttl_hours` (int): Cache validity (default: 168 hours = 1 week)

**Returns:** Dict with:
- `urls`: List of discovered dispatch URLs
- `jurisdiction_name`: Full jurisdiction name
- `region`: State/province
- `country`: Country
- `identifiers`: Sample location identifiers (zip codes, etc.)
- `confidence`: Confidence score (0-1)
- `from_cache`: Whether data came from preconfigured/SQLite

### `get_jurisdiction_urls(jurisdiction_name, cache_db)`

Lookup a jurisdiction from preconfigured data.

**Args:**
- `jurisdiction_name`: Name or partial name to find
- `cache_db`: Cache database path

**Returns:** Dict with jurisdiction data or None

### `extend_preconfigured_jurisdictions(new_jurisdiction_data, config_path)`

Add discovered jurisdictions to the preconfigured config.

**Args:**
- `new_jurisdiction_data`: Dict with jurisdiction key and full data
- `config_path`: Path to configuration file

**Returns:** True if successful, False otherwise

### `load_preconfigured_jurisdictions(config_path)`

Load all preconfigured jurisdictions.

**Args:**
- `config_path`: Path to configuration file (default: "config/dispatch_jurisdictions.json")

**Returns:** Dict of all configured jurisdictions

## Configuration

### preconfigured Jurisdictions Format

```json
{
  "name": "Jurisdiction Full Name",
  "region": "State/Province",
  "country": "Country",
  "dispatch_urls": [
    "https://dispatch.example.com/active-calls"
  ],
  "scraper_type": "table",  // or "playwright" for JS-rendered
  "identifiers": [
    "12345",  // zip codes, postal codes, area codes, etc.
    "12346"
  ],
  "discovered_at": "2025-11-24T...",  // optional
  "discovery_confidence": 0.95,  // optional
  "discovery_model": "phi3:mini"  // optional
}
```

### Adding to Preconfigured Config

Edit `config/dispatch_jurisdictions.json` to add new jurisdictions:

```json
{
  "jurisdictions": {
    "los_angeles_county_ca": {
      "name": "Los Angeles County, California",
      "region": "California",
      "country": "USA",
      "dispatch_urls": [
        "https://www.lasdvcrss.org/do/querypatrolareas"
      ],
      "scraper_type": "table",
      "identifiers": [
        "90001", "90002", "90003", ...
      ]
    }
  }
}
```

## Privacy & Security

### No Hardcoding Location Hints

- System uses generic "identifier" input (not "zip code")
- Preconfigured data is loaded from file, not embedded in code
- Discovery results are cached locally
- No communication with external systems except Ollama

### Data Retention

- Preconfigured data: Permanent (in config file)
- Discovered data: Cached 7 days in SQLite, then re-queried
- Users can clear cache by removing `data/dispatch_cache.db`

### Model Size

- Uses phi3:mini (~2GB) for fast local processing
- No internet required after model download
- No data sent to external APIs

## Examples

### Adding Los Angeles

```bash
python scripts/discover_new_jurisdiction.py "Los Angeles County California"
```

### Adding International Jurisdiction

```bash
python scripts/discover_new_jurisdiction.py "London Metropolitan Police United Kingdom"
```

### Programmatic Bulk Discovery

```python
from src.forecasting.dispatch_discovery import (
    discover_and_cache_dispatch_urls,
    extend_preconfigured_jurisdictions
)

jurisdictions_to_add = [
    "New York County New York",
    "Cook County Illinois",
    "Los Angeles County California"
]

new_configs = {}
for jurisdiction in jurisdictions_to_add:
    result = discover_and_cache_dispatch_urls(jurisdiction)
    if result.get("urls"):
        key = jurisdiction.lower().replace(" ", "_")[:50]
        new_configs[key] = {
            "name": result.get("jurisdiction_name"),
            "region": result.get("region"),
            "country": result.get("country"),
            "dispatch_urls": result.get("urls"),
            "scraper_type": "table",
            "identifiers": result.get("identifiers", [])
        }

if new_configs:
    extend_preconfigured_jurisdictions(new_configs)
```

## Troubleshooting

### LLM Queries Return No Results

**Cause:** Ollama server not running or model not loaded

**Solution:**
```bash
# Start Ollama
ollama serve

# In another terminal, ensure model is loaded
ollama pull phi3:mini
```

### Cache Not Working

**Check SQLite cache exists:**
```bash
ls -la data/dispatch_cache.db
```

**Clear cache (forces re-query):**
```bash
rm data/dispatch_cache.db
```

### Discovered URLs Not Working

**Solution:**
1. URLs might be behind authentication
2. Dispatch system might have changed
3. Try verifying URL in browser first
4. Report issue for preconfiguration update

## Architecture

### Modules

- **`dispatch_discovery.py`**: Core discovery, caching, and config extension
- **`local_threats.py`**: Uses discovery to load jurisdictions and scrape dispatch
- **`local_threat_integration.py`**: Converts dispatch to feed format
- **`scripts/discover_new_jurisdiction.py`**: CLI for adding jurisdictions

### Database Tables

**`dispatch_cache.db`:**
- `dispatch_url_cache`: Caches discovered URLs with TTL
  - `jurisdiction`: Lookup key
  - `urls`: JSON array of discovered URLs
  - `metadata`: Full discovery result
  - `discovered_at`: Timestamp for TTL
  - `model`: Which model discovered it

## Future Enhancements

- [ ] Add multiple scraper type support (JSON API, webhook, etc.)
- [ ] Implement scraper templates for common dispatch systems
- [ ] Add scraper quality metrics (success rate, response time)
- [ ] Support for scraper validation before adding to config
- [ ] Distributed cache for multi-instance deployments
- [ ] Automatic periodic discovery for missing jurisdictions

## Related Documentation

- See `DISPATCH_CONFIG_README.md` for manual configuration guide
- See `local_threats.py` for scraper implementation
- See `local_threat_integration.py` for feed integration
