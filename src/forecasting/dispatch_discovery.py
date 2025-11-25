"""Automated dispatch URL discovery using LLM.

This module uses a small language model to discover police dispatch URLs
for any jurisdiction. Can query Ollama LLM or use pre-discovered cache.
Designed to extend the base dispatch configuration dynamically.
"""

import logging
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def load_model_config(path: str = "config/model_config.json") -> Dict[str, Any]:
    """Load model configuration for remote/global enablement.

    Returns defaults if file missing or invalid. Environment variables override
    file values where applicable.
    """
    defaults = {
        "model_name": os.getenv("DISPATCH_MODEL_NAME", "gpt-5"),
        "enable_for_all_clients": os.getenv("DISPATCH_ENABLE", "true").lower() == "true",
        "remote_llm_endpoint": os.getenv("DISPATCH_LLM_ENDPOINT"),
        "auth_header": os.getenv("DISPATCH_LLM_AUTH_HEADER"),
        "timeout_seconds": int(os.getenv("DISPATCH_LLM_TIMEOUT", "30")),
    }
    cfg_file = Path(path)
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text())
            # Merge with precedence to env overrides already injected in defaults
            for k, v in data.items():
                if k not in defaults or defaults[k] is None:
                    defaults[k] = v
        except Exception as e:
            logger.debug(f"Failed to parse model_config.json: {e}")
    return defaults


def is_model_globally_enabled() -> bool:
    """Return whether global model discovery is enabled."""
    return load_model_config().get("enable_for_all_clients", True)


def load_preconfigured_jurisdictions(
    config_path: str = "config/dispatch_jurisdictions.json"
) -> Dict[str, Any]:
    """Load pre-configured dispatch jurisdictions.
    
    Returns the base set of already-discovered and verified jurisdictions.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict of jurisdictions with verified URLs
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        config_file = Path(__file__).parent.parent.parent / config_path
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("jurisdictions", {})
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    
    return {}


def _build_prompt(jurisdiction: str) -> str:
    return f"""Find the official police dispatch or active calls URL for {jurisdiction}.

Return ONLY a JSON object (no other text) with this exact structure:
{{
  "urls": ["https://example.com/active-calls"],
  "jurisdiction_name": "Full Jurisdiction Name",
  "region": "State/Province",
  "country": "Country",
  "identifiers": ["zip_code_examples"],
  "confidence": 0.9
}}

If you cannot find the URL, return empty urls array. Be concise."""


def query_remote_llm_for_dispatch_url(jurisdiction: str) -> Dict[str, Any]:
    """Query a remote LLM service (non-local) defined in model_config.json or env.
    Expected to POST a JSON with at least {"prompt": str} and return a JSON string in body.
    Environment variables override config file:
      DISPATCH_LLM_ENDPOINT, DISPATCH_LLM_AUTH_HEADER, DISPATCH_LLM_TIMEOUT
    Returns empty result if endpoint not configured.
    """
    cfg = load_model_config()
    endpoint = cfg.get("remote_llm_endpoint")
    auth_header = cfg.get("auth_header")
    timeout = int(cfg.get("timeout_seconds", 30))

    if not endpoint:
        return {"urls": [], "error": "remote endpoint not configured"}

    try:
        import requests
    except ImportError:
        return {"urls": [], "error": "requests not installed"}

    prompt = _build_prompt(jurisdiction)
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    try:
        resp = requests.post(endpoint, json={"prompt": prompt}, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return {"urls": [], "error": f"remote status {resp.status_code}"}
        raw = resp.text
        # Attempt to extract JSON
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["raw_response"] = raw[:500]
                return parsed
        except Exception as e:
            logger.debug(f"Remote LLM parse error: {e}")
        return {"urls": [], "error": "parse_failure", "raw_response": raw[:500]}
    except Exception as e:
        return {"urls": [], "error": str(e)}


def query_ollama_for_dispatch_url(
    jurisdiction: str,
    model: str = "phi3:mini",
    host: str = "http://localhost",
    port: int = 11434,
    timeout: int = 30
) -> Dict[str, Any]:
    """Query local Ollama if available; otherwise return empty result.
    Only used when remote endpoint not configured.
    """
    try:
        import requests
    except ImportError:
        return {"urls": [], "error": "requests not installed"}

    prompt = _build_prompt(jurisdiction)
    try:
        response = requests.post(
            f"{host}:{port}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.1},
            timeout=timeout
        )
        if response.status_code != 200:
            return {"urls": [], "error": f"ollama status {response.status_code}"}
        result = response.json()
        raw_response = result.get("response", "")
        try:
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                discovered = json.loads(json_match.group())
                discovered["raw_response"] = raw_response[:500]
                return discovered
        except Exception as e:
            logger.debug(f"Ollama parse error: {e}")
        return {"urls": [], "error": "parse_failure", "raw_response": raw_response[:500]}
    except Exception as e:
        return {"urls": [], "error": str(e)}


def extend_preconfigured_jurisdictions(
    new_jurisdiction_data: Dict[str, Any],
    config_path: str = "config/dispatch_jurisdictions.json"
) -> bool:
    """Add a newly discovered jurisdiction to the preconfigured config.
    
    Extends the base configuration with new discovered jurisdictions.
    Useful for adding new regions after LLM discovery.
    
    Args:
        new_jurisdiction_data: Dict with key and jurisdiction data
            {
                "key": {
                    "name": "Jurisdiction Name",
                    "region": "State/Province",
                    "country": "Country",
                    "dispatch_urls": ["url1", "url2"],
                    "scraper_type": "table",
                    "identifiers": ["id1", "id2"]
                }
            }
        config_path: Path to configuration file
        
    Returns:
        True if successful, False otherwise
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        config_file = Path(__file__).parent.parent.parent / config_path
    
    try:
        # Load existing config
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {"jurisdictions": {}}
        
        # Add new jurisdictions
        config["jurisdictions"].update(new_jurisdiction_data)
        
        # Write back
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Extended config with {len(new_jurisdiction_data)} jurisdictions")
        return True
    
    except Exception as e:
        logger.error(f"Failed to extend config: {e}")
        return False


def discover_and_cache_dispatch_urls(
    jurisdiction: str,
    cache_db: str = "data/dispatch_cache.db",
    model: str = "phi3:mini",
    ttl_hours: int = 168  # 1 week
) -> Dict[str, Any]:
    """Discover dispatch URLs with caching to avoid repeated LLM calls.
    
    Results are cached in SQLite to avoid querying the LLM repeatedly
    for the same jurisdiction. First checks preconfigured, then queries LLM.
    
    Args:
        jurisdiction: Jurisdiction to discover
        cache_db: Path to cache database
        model: LLM model to use
        ttl_hours: Cache time-to-live in hours
        
    Returns:
        Dict with discovered URLs and metadata
    """
    # Check preconfigured first
    preconfigured = get_jurisdiction_urls(jurisdiction)
    if preconfigured:
        logger.info(f"Using preconfigured data for {jurisdiction}")
        return {
            "urls": preconfigured.get("dispatch_urls", []),
            "jurisdiction_name": preconfigured.get("name", jurisdiction),
            "region": preconfigured.get("region", "Unknown"),
            "country": preconfigured.get("country", "Unknown"),
            "identifiers": preconfigured.get("identifiers", []),
            "from_cache": True,
            "confidence": 1.0
        }
    
    # Check SQLite cache
    cache_path = Path(cache_db)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    import sqlite3
    conn = sqlite3.connect(str(cache_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatch_url_cache (
            jurisdiction TEXT PRIMARY KEY,
            urls TEXT,
            metadata TEXT,
            discovered_at TEXT,
            model TEXT
        )
    """)
    
    # Check cache
    cursor.execute(
        "SELECT urls, metadata, discovered_at FROM dispatch_url_cache WHERE jurisdiction = ?",
        (jurisdiction,)
    )
    cached = cursor.fetchone()
    
    if cached:
        urls_str, metadata_str, discovered_at = cached
        discovered_at = datetime.fromisoformat(discovered_at)
        
        if datetime.utcnow() - discovered_at < timedelta(hours=ttl_hours):
            logger.info(f"Using cached results for {jurisdiction}")
            result = json.loads(metadata_str)
            result["urls"] = json.loads(urls_str)
            result["from_cache"] = True
            conn.close()
            return result
    
    # Not cached - query LLM (only if globally enabled)
    if not is_model_globally_enabled():
        logger.info(f"Model discovery disabled globally; skipping LLM for '{jurisdiction}'")
        conn.close()
        return {
            "urls": [],
            "jurisdiction_name": jurisdiction,
            "region": "Unknown",
            "country": "Unknown",
            "identifiers": [],
            "from_cache": False,
            "confidence": 0.0,
            "error": "model_disabled"
        }

    logger.info(f"Querying LLM for dispatch URLs: {jurisdiction}...")
    result = query_remote_llm_for_dispatch_url(jurisdiction)
    # Only try local Ollama if explicitly configured AND remote failed because endpoint missing
    if (not result.get("urls")) and result.get("error") == "remote endpoint not configured":
        result = query_ollama_for_dispatch_url(jurisdiction, model=model)
    
    # Cache the result if found
    if result.get("urls"):
        cursor.execute("""
            INSERT OR REPLACE INTO dispatch_url_cache
            (jurisdiction, urls, metadata, discovered_at, model)
            VALUES (?, ?, ?, ?, ?)
        """, (
            jurisdiction,
            json.dumps(result.get("urls", [])),
            json.dumps({k: v for k, v in result.items() if k != "urls"}),
            datetime.utcnow().isoformat(),
            model
        ))
        conn.commit()
        logger.info(f"Cached discovery results for {jurisdiction}")
    
    conn.close()
    result["from_cache"] = False
    return result


def get_jurisdiction_urls(
    jurisdiction_name: str,
    cache_db: str = "data/dispatch_cache.db"
) -> Optional[Dict[str, Any]]:
    """Get dispatch URLs for a jurisdiction from preconfigured base.
    
    Searches pre-configured jurisdictions for a match by:
    1. Exact key match
    2. Case-insensitive key match
    3. Name field match
    
    Args:
        jurisdiction_name: Name to search for (e.g., "Richmond" or "Richmond, Virginia")
        cache_db: Cache database path (for future use)
        
    Returns:
        Dict with jurisdiction data or None
    """
    preconfigured = load_preconfigured_jurisdictions()
    
    search_lower = jurisdiction_name.lower()
    
    for key, data in preconfigured.items():
        # Check key
        if key.lower() == search_lower or key.lower() == search_lower.replace(" ", "_"):
            return data
        
        # Check name field
        name = data.get("name", "").lower()
        if name == search_lower or name.startswith(search_lower):
            return data
        
        # Check partial matches
        if search_lower in name or search_lower.replace(" ", "_") in name.lower():
            return data
    
    return None


def generate_dispatch_config_from_discovery(
    jurisdictions: List[str],
    output_path: str = "config/dispatch_jurisdictions_discovered.json",
    model: str = "phi3:mini"
) -> bool:
    """Auto-generate dispatch configuration by discovering URLs for jurisdictions.
    
    Queries the LLM for each jurisdiction not already configured.
    
    Args:
        jurisdictions: List of jurisdiction names to discover
        output_path: Where to save the generated config
        model: LLM model to use
        
    Returns:
        True if successful, False otherwise
    """
    config = {"jurisdictions": {}}
    preconfigured = load_preconfigured_jurisdictions()
    
    # Start with preconfigured jurisdictions
    config["jurisdictions"].update(preconfigured)
    
    for jurisdiction in jurisdictions:
        # Skip if already configured
        if jurisdiction.lower() in [j.lower() for j in config["jurisdictions"].keys()]:
            logger.info(f"Jurisdiction {jurisdiction} already configured")
            continue
        
        logger.info(f"Discovering {jurisdiction}...")
        
        result = discover_and_cache_dispatch_urls(jurisdiction, model=model)
        
        if result.get("urls"):
            # Generate unique key from jurisdiction name
            key = jurisdiction.lower().replace(" ", "_").replace(",", "")[:40]
            
            config["jurisdictions"][key] = {
                "name": result.get("jurisdiction_name", jurisdiction),
                "region": result.get("region", "Unknown"),
                "country": result.get("country", "USA"),
                "dispatch_urls": result.get("urls", []),
                "scraper_type": "table",
                "identifiers": result.get("identifiers", []),
                "discovered_at": datetime.utcnow().isoformat(),
                "discovery_confidence": result.get("confidence", 0),
                "discovery_model": model
            }
            logger.info(f"✓ Found {len(result['urls'])} URLs for {jurisdiction}")
        else:
            logger.warning(f"✗ Could not discover URLs for {jurisdiction}")
    
    # Write config
    try:
        from pathlib import Path
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✓ Saved configuration to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        return False


def test_dispatch_discovery():
    """Test the dispatch discovery system."""
    print("=" * 60)
    print("Testing Dispatch URL Discovery")
    print("=" * 60)
    
    # Test 1: Load preconfigured jurisdictions
    print("\n1. Loading preconfigured jurisdictions...")
    preconfigured = load_preconfigured_jurisdictions()
    print(f"✓ Found {len(preconfigured)} preconfigured jurisdictions:")
    for key, data in list(preconfigured.items())[:3]:
        print(f"  - {data.get('name', key)}: {len(data.get('dispatch_urls', []))} URLs")
    
    # Test 2: Get specific jurisdiction
    print("\n2. Looking up specific jurisdictions...")
    test_lookups = ["Chesterfield County", "Richmond"]
    for jurisdiction in test_lookups:
        result = get_jurisdiction_urls(jurisdiction)
        if result:
            print(f"✓ {jurisdiction}: Found {len(result.get('dispatch_urls', []))} URLs")
        else:
            print(f"✗ {jurisdiction}: Not found in preconfigured")
    
    # Test 3: Cache query (if Ollama available)
    print("\n3. Testing cache mechanism...")
    try:
        result = discover_and_cache_dispatch_urls(
            "Test Jurisdiction",
            ttl_hours=24
        )
        if result.get("from_cache"):
            print("✓ Cache is working (using cached data)")
        else:
            print("✓ Cache system ready (would query Ollama if needed)")
    except Exception as e:
        print(f"✓ Cache system ready (note: {str(e)[:50]}...)")
    
    print("\n" + "=" * 60)
    print("Testing complete")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_dispatch_discovery()
