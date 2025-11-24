"""Security hardening utilities: input validation, sanitization, rate limiting."""
import re
from urllib.parse import urlparse
from time import time
from collections import defaultdict


def validate_url(url: str) -> bool:
    """Validate URL format (basic check for http/https and well-formed domain)."""
    try:
        result = urlparse(url)
        if result.scheme not in ("http", "https"):
            return False
        if not result.netloc:
            return False
        # basic regex for domain
        if not re.match(r"^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", result.netloc):
            return False
        return True
    except Exception:
        return False


def sanitize_domain(domain: str) -> str:
    """Sanitize domain to prevent injection. Returns lowercase alphanumeric and dots/hyphens only."""
    domain = domain.lower().strip()
    domain = re.sub(r"[^a-z0-9.-]", "", domain)
    return domain


def sanitize_sql_param(param: str) -> str:
    """Sanitize string parameter for SQL (basic escaping). Use parameterized queries where possible."""
    if not isinstance(param, str):
        return ""
    return param.replace("'", "''")[:500]  # limit length


class SimpleRateLimiter:
    """Simple in-memory rate limiter per domain/key."""

    def __init__(self, max_requests: int = 10, window_sec: int = 60):
        self.max_requests = max_requests
        self.window_sec = window_sec
        self.requests = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time()
        # prune old requests outside window
        self.requests[key] = [ts for ts in self.requests[key] if now - ts < self.window_sec]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True


if __name__ == "__main__":
    # quick tests
    assert validate_url("https://example.com/feed")
    assert not validate_url("ftp://example.com")
    print("✓ validate_url works")
    assert sanitize_domain("EXAMPLE.COM") == "example.com"
    print("✓ sanitize_domain works")
    limiter = SimpleRateLimiter(max_requests=3, window_sec=1)
    assert limiter.is_allowed("test_domain")
    assert limiter.is_allowed("test_domain")
    assert limiter.is_allowed("test_domain")
    assert not limiter.is_allowed("test_domain")
    print("✓ SimpleRateLimiter works")
