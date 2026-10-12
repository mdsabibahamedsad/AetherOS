"""REST API Runtime.

Full REST API client:
- GET, POST, PUT, PATCH, DELETE
- Headers and authentication (Basic, Bearer, OAuth)
- Retry with backoff
- Streaming response
"""

from __future__ import annotations

from tool_runtime.rest.runtime import RESTRuntime

__all__ = ["RESTRuntime"]
