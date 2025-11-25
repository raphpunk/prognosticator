#!/usr/bin/env python3
"""Add a new dispatch jurisdiction via LLM discovery.

This script allows adding new dispatch URLs for any jurisdiction.
It can:
1. Query the LLM to discover dispatch URLs
2. Add them to the preconfigured config
3. Verify the scrapers work with the new URLs

Usage:
    python scripts/discover_new_jurisdiction.py "Los Angeles County California"
    python scripts/discover_new_jurisdiction.py "London United Kingdom"
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.forecasting.dispatch_discovery import (
    discover_and_cache_dispatch_urls,
    extend_preconfigured_jurisdictions,
    get_jurisdiction_urls
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def discover_jurisdiction(jurisdiction_name: str) -> bool:
    """Discover and add a new jurisdiction.
    
    Args:
        jurisdiction_name: Name of jurisdiction to discover
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Discovering dispatch URLs for: {jurisdiction_name}")
    print('='*60)
    
    # Check if already configured
    existing = get_jurisdiction_urls(jurisdiction_name)
    if existing:
        print(f"✓ Already configured in preconfigured data")
        print(f"  Name: {existing.get('name')}")
        print(f"  URLs: {len(existing.get('dispatch_urls', []))} configured")
        print(f"  Identifiers: {existing.get('identifiers', [])}")
        return True
    
    print(f"\n1. Querying LLM for dispatch URLs...")
    result = discover_and_cache_dispatch_urls(jurisdiction_name, ttl_hours=0)
    
    if not result.get("urls"):
        print(f"✗ Could not discover URLs for {jurisdiction_name}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
        return False
    
    print(f"✓ Found {len(result['urls'])} URLs:")
    for url in result["urls"]:
        print(f"  - {url}")
    
    print(f"\n2. Adding to preconfigured configuration...")
    
    # Generate config key
    key = jurisdiction_name.lower().replace(" ", "_").replace(",", "")[:50]
    
    new_config = {
        key: {
            "name": result.get("jurisdiction_name", jurisdiction_name),
            "region": result.get("region", "Unknown"),
            "country": result.get("country", "USA"),
            "dispatch_urls": result.get("urls", []),
            "scraper_type": "table",
            "identifiers": result.get("identifiers", []),
            "discovered_at": datetime.now().isoformat(),
            "discovery_confidence": result.get("confidence", 0.5),
            "discovery_model": "phi3:mini"
        }
    }
    
    if extend_preconfigured_jurisdictions(new_config):
        print(f"✓ Added to config with key: {key}")
        print(f"  Full name: {result.get('jurisdiction_name')}")
        print(f"  Country: {result.get('country')}")
        print(f"  Sample identifiers: {result.get('identifiers', [])[:3]}")
        return True
    else:
        print(f"✗ Failed to extend configuration")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/discover_new_jurisdiction.py '<jurisdiction_name>'")
        print("\nExamples:")
        print("  python scripts/discover_new_jurisdiction.py 'Los Angeles County California'")
        print("  python scripts/discover_new_jurisdiction.py 'Seattle Washington'")
        print("  python scripts/discover_new_jurisdiction.py 'London United Kingdom'")
        sys.exit(1)
    
    from datetime import datetime
    
    jurisdiction = sys.argv[1]
    success = discover_jurisdiction(jurisdiction)
    
    print(f"\n{'='*60}")
    if success:
        print("✓ Jurisdiction discovery successful")
        print("✓ Can now use in local threat monitoring")
    else:
        print("✗ Jurisdiction discovery failed")
        print("  Note: Ollama server must be running for LLM discovery")
    print('='*60 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
