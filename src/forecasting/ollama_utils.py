#!/usr/bin/env python3
"""Shared Ollama utilities for HTTP API interaction with remote Ollama servers."""

import json
from typing import List, Optional, Tuple


def list_models_http(host: str, port: int, api_key: Optional[str] = None) -> List[str]:
    """List available models via HTTP API (common Ollama server endpoints)."""
    import requests
    
    candidates = ["/api/tags", "/v1/models", "/api/models", "/models"]
    for endpoint in candidates:
        url = f"{host.rstrip('/')}:{port}{endpoint}"
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    models = []
                    # Handle /api/tags response format
                    if isinstance(data, dict) and "models" in data:
                        models = [m.get("name") if isinstance(m, dict) else str(m) for m in (data.get("models") or []) if m]
                    # Handle /v1/models response format
                    elif isinstance(data, dict) and "data" in data:
                        data_list = data.get("data")
                        if data_list:
                            models = [m.get("id", m.get("name")) if isinstance(m, dict) else str(m) for m in data_list if m]
                    # Handle array response
                    elif isinstance(data, list):
                        models = [m.get("name", m.get("id")) if isinstance(m, dict) else str(m) for m in data if m]
                    
                    if models:
                        return [str(m) for m in models if m]
                except (json.JSONDecodeError, ValueError, AttributeError):
                    continue
        except (requests.RequestException, OSError):
            continue
    
    return []


def pull_model_http(host: str, port: int, model_name: str, api_key: Optional[str] = None, progress_callback=None) -> tuple[bool, str]:
    """Pull a model via HTTP API with optional progress tracking.
    
    Args:
        host: Ollama server host
        port: Ollama server port
        model_name: Name of model to pull
        api_key: Optional API key
        progress_callback: Optional callable(status_dict) for progress updates
                          status_dict contains: {'stage', 'digest', 'total', 'completed', 'percent'}
    
    Returns: (success, message)
    """
    import requests
    import re
    
    if not model_name or not model_name.strip():
        return False, "Model name cannot be empty."
    
    # Validate model name format (alphanumeric, dots, colons, hyphens, underscores only)
    model_name = model_name.strip()
    if not re.match(r'^[a-zA-Z0-9._:-]+$', model_name):
        return False, "Invalid model name format. Use only alphanumeric characters, dots, colons, hyphens."
    
    url = f"{host.rstrip('/')}:{port}/api/pull"
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model_name.strip()}
        
        # Use stream=True since Ollama returns streaming JSON
        resp = requests.post(url, json=payload, headers=headers, timeout=300, stream=True)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
        
        # Parse streaming response
        last_status = None
        max_completed = 0
        max_total = 0
        
        for line in resp.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    status = data.get("status", "")
                    digest = data.get("digest", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    
                    # Track progress
                    if total > 0:
                        max_total = max(max_total, total)
                        max_completed = max(max_completed, completed)
                        percent = min(100, int((completed / total) * 100))
                    else:
                        percent = 0
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback({
                            "stage": status,
                            "digest": digest[:12] if digest else "",
                            "total": total,
                            "completed": completed,
                            "percent": percent
                        })
                    
                    last_status = status
                    
                    # Check for completion
                    if status == "success":
                        return True, f"✅ Model '{model_name}' pulled successfully!"
                
                except json.JSONDecodeError:
                    continue
        
        # If we got here without success, still check if it completed
        if last_status:
            return True, f"Model pull completed: {last_status}"
        return False, "Pull request sent but no response received."
    
    except requests.exceptions.Timeout:
        return False, "Pull operation timed out (300s). Model may still be downloading in background."
    except requests.RequestException as e:
        return False, f"HTTP request failed: {str(e)[:200]}"
    except OSError as e:
        return False, f"OS error: {str(e)[:200]}"


def test_ollama_connection(host: str, port: int, api_key: Optional[str] = None) -> dict:
    """Test Ollama HTTP connection and return diagnostic details.
    
    Returns dict with keys: 'success' (bool), 'status' (str), 'models' (list), 'details' (str).
    """
    import requests
    
    # Normalize host
    host = host.strip()
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"http://{host}"
    host = host.rstrip("/")
    
    # Try multiple endpoints for compatibility
    test_endpoints = ["/api/tags", "/v1/models", "/api/models"]
    
    result = {
        "success": False,
        "status": "Unknown",
        "models": [],
        "details": "",
        "diagnostic_tips": []
    }
    
    last_error = None
    for endpoint in test_endpoints:
        test_url = f"{host}:{port}{endpoint}"
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            resp = requests.get(test_url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    models = []
                    
                    # Handle /api/tags response format
                    if isinstance(data, dict) and "models" in data:
                        models = [m.get("name") if isinstance(m, dict) else str(m) for m in data.get("models", []) if m]
                    # Handle /v1/models response format
                    elif isinstance(data, dict) and "data" in data:
                        models = [m.get("id", m.get("name")) if isinstance(m, dict) else str(m) for m in data.get("data", []) if m]
                    # Handle array response
                    elif isinstance(data, list):
                        models = [m.get("name") if isinstance(m, dict) else str(m) for m in data if m]
                    
                    result["success"] = True
                    result["status"] = "Connected ✓"
                    result["models"] = [str(m) for m in models if m]
                    result["details"] = f"Found {len(result['models'])} model(s)"
                    if result["models"]:
                        result["details"] += f": {', '.join(result['models'][:3])}"
                        if len(result["models"]) > 3:
                            result["details"] += f" (+{len(result['models']) - 3} more)"
                    return result
                except json.JSONDecodeError:
                    result["status"] = "Connected but invalid response"
                    result["details"] = f"Server responded but response was not valid JSON (endpoint: {endpoint})"
                    return result
            elif resp.status_code == 404:
                continue  # Try next endpoint
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection refused on {endpoint}"
        except requests.exceptions.Timeout:
            last_error = f"Timeout on {endpoint}"
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {str(e)[:100]}"
    
    # If we get here, no endpoint worked
    if last_error and "Connection refused" in last_error:
        result["status"] = "Connection Refused"
        result["details"] = f"Cannot connect to {host}:{port}"
        result["diagnostic_tips"] = [
            "🔍 Troubleshooting steps:",
            f"1. Check if Ollama is running on {host.split('://')[-1]}",
            f"   - On that computer: ps aux | grep ollama",
            f"2. Verify Ollama is listening on port {port}:",
            f"   - On that computer: netstat -tuln | grep {port}",
            f"3. Ensure Ollama listens on all network interfaces:",
            f"   - Start with: OLLAMA_HOST=0.0.0.0:{port} ollama serve",
            "4. Check firewall rules allow port 11434",
            f"5. Test manually: curl http://{host.split('://')[-1]}:{port}/api/tags",
            "6. Try 'ollama status' to see if service is running properly",
        ]
    else:
        result["status"] = "API Endpoint Not Found"
        result["details"] = f"Connected to {host}:{port} but Ollama API endpoints not found. Tried: {', '.join(test_endpoints)}"
        result["diagnostic_tips"] = [
            "⚠️ Server is reachable but API endpoints not responding:",
            "1. Verify Ollama is fully started (may still be initializing)",
            f"2. Check if running on different port: curl http://{host.split('://')[-1]}:11434/",
            "3. Review Ollama logs on the remote machine",
        ]
    
    return result
