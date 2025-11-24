"""Circuit breaker and resilience patterns for fault tolerance."""
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import functools


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Timeout: {self.config.timeout_seconds}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._reset()
        else:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open state."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.timeout_seconds
    
    def _reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CacheLayer:
    """TTL-based caching layer for RSS feeds and API responses."""
    
    def __init__(self, db_path: str = "data/resilience_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize cache database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                cache_type TEXT NOT NULL,
                data TEXT NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)
        """)
        
        conn.commit()
        conn.close()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached value if not expired."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT data FROM cache_entries
            WHERE cache_key = ? AND expires_at > ?
        """, (key, datetime.utcnow().isoformat()))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def set(self, key: str, value: str, ttl_seconds: int = 300, cache_type: str = "general") -> None:
        """Set cached value with TTL."""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO cache_entries
            (cache_key, cache_type, data, ttl_seconds, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, cache_type, value, ttl_seconds, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
    
    def delete(self, key: str) -> None:
        """Delete cached entry."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM cache_entries WHERE expires_at <= ?
        """, (datetime.utcnow().isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cache_type,
                COUNT(*) as total,
                SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END) as valid
            FROM cache_entries
            GROUP BY cache_type
        """, (datetime.utcnow().isoformat(),))
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {"total": row[1], "valid": row[2]}
        
        conn.close()
        return stats


def cached(ttl_seconds: int = 300, cache_type: str = "general"):
    """Decorator for caching function results with TTL."""
    def decorator(func: Callable) -> Callable:
        cache = CacheLayer()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.sha256("|".join(key_parts).encode()).hexdigest()
            
            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                import json
                return json.loads(cached_value)
            
            # Call function and cache result
            result = func(*args, **kwargs)
            import json
            cache.set(cache_key, json.dumps(result), ttl_seconds, cache_type)
            return result
        
        return wrapper
    return decorator


def with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """Decorator for exponential backoff retry logic."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)
                    else:
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


class FallbackRouter:
    """Route requests to fallback handlers when primary fails."""
    
    def __init__(self):
        self.handlers = {}
    
    def register(self, name: str, primary: Callable, fallbacks: list[Callable]) -> None:
        """Register primary handler with fallback chain."""
        self.handlers[name] = {
            "primary": primary,
            "fallbacks": fallbacks
        }
    
    def call(self, name: str, *args, **kwargs) -> Any:
        """Call handler with fallback chain."""
        if name not in self.handlers:
            raise ValueError(f"No handler registered for '{name}'")
        
        handler_config = self.handlers[name]
        
        # Try primary
        try:
            return handler_config["primary"](*args, **kwargs)
        except Exception as primary_error:
            # Try fallbacks in order
            for i, fallback in enumerate(handler_config["fallbacks"]):
                try:
                    return fallback(*args, **kwargs)
                except Exception as fallback_error:
                    if i == len(handler_config["fallbacks"]) - 1:
                        # Last fallback failed, re-raise
                        raise fallback_error
            
            # No fallbacks succeeded
            raise primary_error


# Global circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker instance."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def protected_call(service_name: str, func: Callable, *args, **kwargs) -> Any:
    """Execute function with circuit breaker protection."""
    breaker = get_circuit_breaker(service_name)
    return breaker.call(func, *args, **kwargs)
