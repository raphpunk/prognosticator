"""
Simple Ollama HTTP client for article pre-filtering
"""
import requests
import json
import logging

logger = logging.getLogger(__name__)


def call_ollama_simple(model: str, prompt: str, host: str = "192.168.1.140", 
                       port: int = 11434, timeout: int = 30) -> str:
    """
    Simple Ollama HTTP API call without dependencies
    
    Args:
        model: Model name (e.g., "gemma2:2b")
        prompt: The prompt text
        host: Ollama server host
        port: Ollama server port
        timeout: Request timeout in seconds
        
    Returns:
        Model response text
    """
    url = f"http://{host}:{port}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1  # Low temperature for consistent responses
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
        
    except requests.exceptions.Timeout:
        logger.error(f"Ollama request timed out after {timeout}s")
        raise RuntimeError(f"Model timeout after {timeout}s")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        raise RuntimeError(f"Cannot reach Ollama at http://{host}:{port}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
