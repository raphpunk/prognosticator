"""Centralized configuration, logging, and security management."""
import os
import logging
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class OllamaConfig:
    """Ollama connection configuration."""
    host: str = "http://localhost"
    port: int = 11434
    api_key: Optional[str] = None
    timeout: int = 120
    max_workers: int = 2
    
    def __post_init__(self):
        # Validate host
        if not self.host.startswith(("http://", "https://")):
            self.host = f"http://{self.host}"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    live_db: str = "data/live.db"
    cache_db: str = "data/agent_cache.db"
    pool_size: int = 5
    timeout: int = 30


@dataclass
class AppConfig:
    """Application configuration."""
    ollama: OllamaConfig
    database: DatabaseConfig
    log_level: str = "INFO"
    debug: bool = False
    max_articles: int = 500
    context_topk: int = 15
    cache_responses: bool = True


def load_config(config_file: str = "feeds.json") -> AppConfig:
    """Load configuration from feeds.json and environment variables."""
    # Load from feeds.json if it exists
    if Path(config_file).exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
                ollama_cfg = data.get("ollama", {})
        except (json.JSONDecodeError, IOError) as e:
            # Log warning but continue with defaults
            print(f"Warning: Could not load {config_file}: {e}")
            ollama_cfg = {}
    else:
        ollama_cfg = {}
    
    # Override with environment variables
    ollama_host = os.getenv("OLLAMA_HOST", ollama_cfg.get("host", "http://localhost"))
    ollama_port = int(os.getenv("OLLAMA_PORT", ollama_cfg.get("port", 11434)))
    ollama_key = os.getenv("OLLAMA_API_KEY", ollama_cfg.get("api_key"))
    
    ollama = OllamaConfig(
        host=ollama_host,
        port=ollama_port,
        api_key=ollama_key,
        timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
        max_workers=int(os.getenv("OLLAMA_MAX_WORKERS", "2"))
    )
    
    database = DatabaseConfig(
        live_db=os.getenv("DB_LIVE", "data/live.db"),
        cache_db=os.getenv("DB_CACHE", "data/agent_cache.db"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        timeout=int(os.getenv("DB_TIMEOUT", "30"))
    )
    
    return AppConfig(
        ollama=ollama,
        database=database,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        max_articles=int(os.getenv("MAX_ARTICLES", "500")),
        context_topk=int(os.getenv("CONTEXT_TOPK", "15")),
        cache_responses=os.getenv("CACHE_RESPONSES", "true").lower() == "true"
    )


def setup_logging(log_level: str = "INFO", debug: bool = False) -> logging.Logger:
    """Configure logging with appropriate handlers and formatters."""
    logger = logging.getLogger("forecasting")
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
        if not debug else
        "[%(asctime)s] %(levelname)s - %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Global config and logger
_config: Optional[AppConfig] = None
_logger: Optional[logging.Logger] = None


def get_config() -> AppConfig:
    """Get or initialize global configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_logger() -> logging.Logger:
    """Get or initialize global logger."""
    global _logger
    if _logger is None:
        cfg = get_config()
        _logger = setup_logging(cfg.log_level, cfg.debug)
    return _logger


__all__ = [
    "OllamaConfig",
    "DatabaseConfig", 
    "AppConfig",
    "load_config",
    "setup_logging",
    "get_config",
    "get_logger"
]
