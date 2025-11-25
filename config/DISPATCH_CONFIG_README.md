# Dispatch Jurisdictions Configuration

This directory contains the configuration for local threat monitoring dispatch scrapers.

## Configuration Format

The `dispatch_jurisdictions.json` file uses the following structure:

```json
{
  "jurisdictions": {
    "unique_key": {
      "name": "Human-readable jurisdiction name",
      "region": "Region/State/Province",
      "country": "Country",
      "dispatch_urls": ["https://example.com/dispatch"],
      "scraper_type": "table",
      "identifiers": ["12345", "zip_codes_or_area_codes_etc"]
    }
  }
}
```

## Fields

- **unique_key**: Internal identifier (not exposed to users, can be anything)
- **name**: Display name shown in the Streamlit UI
- **region**: Geographic region for organization
- **country**: Country for organization
- **dispatch_urls**: List of URLs to scrape
- **scraper_type**: Type of scraper ("table" for HTML tables, extensible for other types)
- **identifiers**: List of location codes (zip codes, area codes, districts, postcodes, etc.)

## Adding New Jurisdictions

1. Choose identifiers for your jurisdiction (zip codes, postal codes, area codes, etc.)
2. Find the public dispatch feed URL
3. Add an entry to `dispatch_jurisdictions.json`:

```json
{
  "jurisdictions": {
    "my_city_state": {
      "name": "My City, My State",
      "region": "My State",
      "country": "My Country",
      "dispatch_urls": ["https://dispatch.example.gov/active-calls"],
      "scraper_type": "table",
      "identifiers": ["12345", "12346", "12347"]
    }
  }
}
```

4. If the dispatch site has a different structure, you may need to implement a custom scraper in `src/forecasting/local_threats.py`:

```python
def scrape_my_jurisdiction(self, url: str) -> List[DispatchCall]:
    """Scrape My Jurisdiction active calls."""
    # Implementation similar to scrape_chesterfield, scrape_richmond, etc.
```

5. Update `scrape_all_jurisdictions()` to route to your custom scraper:

```python
elif "my_domain" in url.lower():
    calls = self.scrape_my_jurisdiction(url)
    all_calls.extend(calls)
```

## Example Jurisdictions

See `dispatch_jurisdictions.EXAMPLE.json` for examples of how to configure jurisdictions from:
- Other US states (New York, California)
- International locations (London, UK)

## Privacy & Security Notes

- The configuration is public and should not contain any sensitive URLs
- Identifiers are shown in the UI - use publicly available codes (zip codes, postcodes, etc.)
- All dispatch data is publicly available from government sources
- The scraper respects robots.txt and rate limits

## Testing Configuration

```python
from forecasting.local_threats import get_jurisdictions, get_available_zip_codes

# View all configured jurisdictions
jurisdictions = get_jurisdictions()
print(jurisdictions)

# View all configured identifiers
identifiers = get_available_zip_codes()
print(identifiers)
```

## Scraping Different Site Structures

The system currently includes generic table scrapers that work for most government dispatch sites with HTML tables. If your jurisdiction uses:

- **JavaScript-rendered content**: Playwright handles this (already integrated)
- **Custom HTML structure**: May need custom parser (see existing scrapers)
- **API endpoints**: Can be extended to support JSON APIs
- **PDF/Other formats**: Custom implementation needed

Refer to existing scrapers in `src/forecasting/local_threats.py` for implementation patterns.
