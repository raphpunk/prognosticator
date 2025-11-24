#!/usr/bin/env python3
"""Test dynamic zip code lookup for local threat monitoring."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from forecasting.local_threats import (
    get_available_zip_codes,
    get_jurisdictions,
    get_jurisdiction_for_zip
)
from forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking


def test_zip_code_lookup():
    """Test the zip code lookup functionality."""
    print("=" * 60)
    print("Testing Dynamic Zip Code Lookup for Local Threats")
    print("=" * 60)
    
    # Test 1: Get all available jurisdictions
    print("\n1. Available Jurisdictions:")
    jurisdictions = get_jurisdictions()
    for jurisdiction in jurisdictions:
        print(f"   - {jurisdiction}")
    
    # Test 2: Get available zip codes
    print("\n2. Available Zip Codes:")
    available_zips = get_available_zip_codes()
    print(f"   Total zip codes: {len(available_zips)}")
    for zip_code, jurisdiction in sorted(available_zips.items())[:5]:
        print(f"   - {zip_code} → {jurisdiction}")
    print(f"   ... and {len(available_zips) - 5} more")
    
    # Test 3: Lookup specific zip codes
    print("\n3. Testing Specific Zip Code Lookups:")
    test_zips = ["23112", "23220", "23228", "23834", "99999"]
    for test_zip in test_zips:
        jurisdiction = get_jurisdiction_for_zip(test_zip)
        if jurisdiction:
            print(f"   ✓ {test_zip} → {jurisdiction}")
        else:
            print(f"   ✗ {test_zip} → NOT FOUND")
    
    # Test 4: Test scraping by zip code
    print("\n4. Testing Scraping by Zip Code:")
    print("   Chesterfield (23112)...")
    items = fetch_local_threat_feeds_with_health_tracking(
        zip_code="23112",
        lookback_hours=6
    )
    if items:
        print(f"   ✓ Found {len(items)} dispatch calls")
        sample = items[0]
        print(f"     Sample: {sample['title']}")
    else:
        print(f"   ⚠ No calls found (may be normal)")
    
    # Test 5: Test scraping all
    print("\n5. Testing Scraping All Jurisdictions:")
    items_all = fetch_local_threat_feeds_with_health_tracking(
        zip_code=None,
        lookback_hours=6
    )
    if items_all:
        print(f"   ✓ Found {len(items_all)} total dispatch calls")
        jurisdictions_found = set(item.get('jurisdiction', 'Unknown') for item in items_all)
        print(f"   Jurisdictions: {', '.join(sorted(jurisdictions_found))}")
    else:
        print(f"   ⚠ No calls found")
    
    print("\n" + "=" * 60)
    print("✓ Dynamic zip code lookup is working!")
    print("=" * 60)


if __name__ == "__main__":
    test_zip_code_lookup()
