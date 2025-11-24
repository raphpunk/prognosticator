"""Circuit breaker and resilience patterns for Ollama API calls."""
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import logging

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        RetryError
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Fallback decorator
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    stop_after_attempt = wait_exponential = retry_if_exception_type = lambda x: None
    RetryError = Exception


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


class OllamaCircuitBreaker:
    """Circuit breaker for Ollama API calls."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                logger.warning("Circuit breaker OPEN - request blocked")
                return {
                    "status": "degraded",
                    "response": None,
                    "error": "Circuit breaker open - service unavailable"
                }
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return {"status": "success", "response": result, "error": None}
        
        except Exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker caught exception: {e}")
            return {
                "status": "degraded",
                "response": None,
                "error": str(e)
            }
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout_seconds
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN - recovery failed")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPEN - {self.failure_count} consecutive failures")


# Global circuit breaker instance
_circuit_breaker = OllamaCircuitBreaker()


def with_circuit_breaker(func: Callable) -> Callable:
    """Decorator to protect functions with circuit breaker."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return _circuit_breaker.call(func, *args, **kwargs)
    return wrapper


def with_retry_and_timeout(timeout: int = 30, max_attempts: int = 3):
    """Decorator combining retry logic and timeout protection."""
    if not TENACITY_AVAILABLE:
        logger.warning("tenacity not available - retry logic disabled")
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, timeout=timeout, **kwargs)
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed: {e}")
                    return None
            return wrapper
        return decorator
    
    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=2, min=1, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=False
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject timeout
            kwargs['timeout'] = timeout
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Retry attempt failed for {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get current circuit breaker status for monitoring."""
    return {
        "state": _circuit_breaker.state.value,
        "failure_count": _circuit_breaker.failure_count,
        "last_failure_time": _circuit_breaker.last_failure_time,
        "config": {
            "failure_threshold": _circuit_breaker.config.failure_threshold,
            "timeout_seconds": _circuit_breaker.config.timeout_seconds
        }
    }
