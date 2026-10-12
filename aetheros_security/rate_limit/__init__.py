"""
Rate Limiting for AetherOS
==========================

Rate limiting per:
    - Plugin
    - Agent
    - MCP Server
    - User
    - Workspace

Usage::

    from aetheros_security.rate_limit import RateLimiter

    limiter = RateLimiter()
    if limiter.check("plugin:my-plugin:api_call"):
        # Allow request
        pass
    else:
        # Rate limited
        pass
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_requests: int = 100
    window_seconds: int = 60
    burst_limit: int = 10


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""
    timestamps: List[float] = field(default_factory=list)
    blocked_until: float = 0.0


class RateLimiter:
    """Rate limiter for AetherOS.

    Usage::

        limiter = RateLimiter()

        # Check rate limit
        if limiter.check("plugin:my-plugin:api_call"):
            # Process request
            pass

        # Get usage stats
        stats = limiter.get_stats("plugin:my-plugin")
    """

    def __init__(self) -> None:
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._configs: Dict[str, RateLimitConfig] = {}
        self._default_config = RateLimitConfig()

        # Set default configs for different scopes
        self._configs["plugin"] = RateLimitConfig(max_requests=1000, window_seconds=3600)
        self._configs["agent"] = RateLimitConfig(max_requests=500, window_seconds=3600)
        self._configs["mcp"] = RateLimitConfig(max_requests=500, window_seconds=3600)
        self._configs["user"] = RateLimitConfig(max_requests=2000, window_seconds=3600)
        self._configs["workspace"] = RateLimitConfig(max_requests=10000, window_seconds=3600)

    def check(
        self,
        key: str,
        *,
        cost: int = 1,
        scope: Optional[str] = None,
    ) -> bool:
        """Check if a request is within rate limits.

        Args:
            key: Rate limit key (e.g., "plugin:my-plugin:api_call").
            cost: Cost of the request (default 1).
            scope: Scope for config lookup.

        Returns:
            True if request is allowed.
        """
        now = time.time()
        entry = self._entries[key]

        # Check if blocked
        if entry.blocked_until > now:
            return False

        # Get config
        config = self._get_config(scope)

        # Clean old timestamps
        cutoff = now - config.window_seconds
        entry.timestamps = [t for t in entry.timestamps if t > cutoff]

        # Check burst limit
        recent_count = len([t for t in entry.timestamps if t > now - 1])
        if recent_count + cost > config.burst_limit:
            entry.blocked_until = now + 60  # Block for 1 minute
            return False

        # Check rate limit
        if len(entry.timestamps) + cost > config.max_requests:
            entry.blocked_until = now + config.window_seconds
            return False

        # Allow and record
        for _ in range(cost):
            entry.timestamps.append(now)

        return True

    def _get_config(self, scope: Optional[str]) -> RateLimitConfig:
        """Get rate limit config for scope."""
        if scope and scope in self._configs:
            return self._configs[scope]
        return self._default_config

    def set_config(
        self,
        scope: str,
        max_requests: int,
        window_seconds: int,
        burst_limit: int = 10,
    ) -> None:
        """Set rate limit config for a scope."""
        self._configs[scope] = RateLimitConfig(
            max_requests=max_requests,
            window_seconds=window_seconds,
            burst_limit=burst_limit,
        )

    def get_usage(self, key: str) -> Dict[str, any]:
        """Get usage stats for a key."""
        entry = self._entries[key]
        now = time.time()

        # Count requests in different windows
        last_minute = len([t for t in entry.timestamps if t > now - 60])
        last_hour = len([t for t in entry.timestamps if t > now - 3600])

        return {
            "key": key,
            "last_minute": last_minute,
            "last_hour": last_hour,
            "total": len(entry.timestamps),
            "blocked": entry.blocked_until > now,
            "blocked_until": entry.blocked_until,
        }

    def get_stats(self, prefix: Optional[str] = None) -> Dict[str, any]:
        """Get rate limit statistics."""
        total_keys = len(self._entries)
        blocked_keys = sum(
            1 for e in self._entries.values()
            if e.blocked_until > time.time()
        )

        return {
            "total_keys": total_keys,
            "blocked_keys": blocked_keys,
            "active_keys": total_keys - blocked_keys,
        }

    def reset(self, key: Optional[str] = None) -> int:
        """Reset rate limits.

        Args:
            key: Specific key to reset, or None for all.

        Returns:
            Number of entries reset.
        """
        if key:
            if key in self._entries:
                del self._entries[key]
                return 1
            return 0
        else:
            count = len(self._entries)
            self._entries.clear()
            return count

    def get_remaining(self, key: str, scope: Optional[str] = None) -> int:
        """Get remaining requests for a key."""
        config = self._get_config(scope)
        entry = self._entries[key]
        now = time.time()

        cutoff = now - config.window_seconds
        current = len([t for t in entry.timestamps if t > cutoff])

        return max(0, config.max_requests - current)


# Global rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Return the global RateLimiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
