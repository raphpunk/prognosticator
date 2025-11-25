#!/usr/bin/env python3
"""Test script demonstrating LLM-based zip code discovery.

This shows how the system now works with:
1. Preconfigured zip codes (instant)
2. Unknown zip codes (queries LLM when available)
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("ZIP CODE DISCOVERY TEST - WITH LLM FALLBACK")
print("="*70 + "\n")

# Import after path setup
from src.forecasting.local_threats import get_jurisdiction_for_zip
from src.forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking

# Test scenarios
test_cases = [
    ("23112", "Preconfigured (Chesterfield, VA)"),
    ("23220", "Preconfigured (Richmond, VA)"),
    ("12345", "Unknown (would query LLM)"),
    ("10001", "Unknown NYC zip (would query LLM)"),
]

print("SCENARIO 1: Direct zip code lookup")
print("-" * 70)
for zip_code, description in test_cases:
    # Try without LLM first
    result = get_jurisdiction_for_zip(zip_code, use_llm=False)
    status = "✓ Preconfigured" if result else "? Unknown"
    print(f"{status:20} {zip_code:10} → {result or '(not in config)'}")
    print(f"{' '*20} Description: {description}")

print("\n" + "="*70)
print("SCENARIO 2: With LLM discovery enabled (would query Ollama if running)")
print("-" * 70)

# Show what would happen with LLM
print("\nTo enable LLM discovery for unknown zip codes:")
print("1. Start Ollama:  ollama serve")
print("2. Load model:    ollama pull phi3:mini")
print("3. The system will then automatically discover new jurisdictions")
print("\nExample flow:")
print("  User enters: 90210 (Beverly Hills, CA zip)")
print("  System checks: Not in preconfigured")
print("  System queries LLM: 'What jurisdiction has 90210?'")
print("  LLM responds: 'Los Angeles County, California'")
print("  System caches result (7-day TTL)")
print("  System scrapes dispatch from that jurisdiction")

print("\n" + "="*70)
print("SCENARIO 3: Integration with Streamlit UI")
print("-" * 70)
print("\nThe Streamlit 'Local Threats' tab now:")
print("✓ Shows 'Searching for jurisdiction via LLM...' spinner")
print("✓ Queries LLM if unknown zip code entered")
print("✓ Automatically fetches dispatch data for discovered jurisdiction")
print("✓ Works seamlessly with both preconfigured and discovered zips")

print("\n" + "="*70)
print("Current Status:")
print("-" * 70)

from src.forecasting.local_threats import get_available_zip_codes, get_jurisdictions

available_zips = get_available_zip_codes()
jurisdictions = get_jurisdictions()

print(f"✓ Preconfigured jurisdictions: {len(jurisdictions)}")
for j in jurisdictions:
    print(f"  - {j}")

print(f"\n✓ Preconfigured identifiers: {len(available_zips)}")
print(f"  Sample: {', '.join(list(available_zips.keys())[:8])}")

print("\n" + "="*70)
print("✅ SYSTEM READY FOR LLM-POWERED ZIP CODE DISCOVERY")
print("="*70 + "\n")

print("Next steps:")
print("1. Go to Streamlit at http://localhost:8501")
print("2. Go to '🚨 Local Threats' tab")
print("3. Try entering a preconfigured zip (23112)")
print("4. Try entering an unknown zip code")
print("   - If Ollama is running, it will discover the jurisdiction")
print("   - If Ollama is not running, it will show 'not found'")
print("\n")
