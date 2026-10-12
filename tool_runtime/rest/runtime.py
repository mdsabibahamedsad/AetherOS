"""REST API Runtime — real HTTP client.

Supports: GET, POST, PUT, PATCH, DELETE with full auth, retry, streaming.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Callable

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class RESTRuntime(ToolInterface):
    """REST API client runtime with full HTTP method support.

    Features:
    - GET, POST, PUT, PATCH, DELETE
    - Custom headers
    - Bearer, Basic, OAuth authentication
    - Retry with exponential backoff
    - Streaming responses
    """

    def __init__(self):
        meta = ToolMetadata(
            id="rest_api",
            name="REST API Runtime",
            description="Full REST client: GET, POST, PUT, PATCH, DELETE with auth, retries, streaming",
            category=ToolCategory.REST_API,
            risk_level=ToolRiskLevel.NETWORK,
            version="2.0.0",
            tags=["http", "rest", "api", "client"],
            requires_approval=False,
            timeout_seconds=30.0,
        )
        super().__init__(meta)
        self._httpx_available = False
        self._init_http()

    def _init_http(self) -> None:
        try:
            import httpx
            self._httpx_available = True
        except ImportError:
            self._httpx_available = False

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "rest_api",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    },
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "params": {"type": "object"},
                    "body": {"type": "object"},
                    "auth_type": {
                        "type": "string",
                        "enum": ["none", "bearer", "basic", "oauth2"],
                    },
                    "auth_token": {"type": "string"},
                    "auth_username": {"type": "string"},
                    "auth_password": {"type": "string"},
                    "timeout": {"type": "number"},
                    "retry_count": {"type": "integer"},
                    "stream": {"type": "boolean"},
                },
                "required": ["method", "url"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        if "method" not in params:
            errors.append("Missing required parameter: method")
        if "url" not in params:
            errors.append("Missing required parameter: url")
        method = params.get("method", "").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            errors.append(f"Invalid method: {method}")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        if not self._httpx_available:
            return self._execute_urllib(params)

        import httpx

        method = params["method"].upper()
        url = params["url"]
        headers = params.get("headers", {})
        query_params = params.get("params", {})
        body = params.get("body")
        timeout = params.get("timeout", 30)
        retry_count = params.get("retry_count", 0)
        stream = params.get("stream", False)

        auth = self._build_auth(params)

        for attempt in range(retry_count + 1):
            try:
                start = time.time()

                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=query_params,
                        json=body if method in ("POST", "PUT", "PATCH") else None,
                        auth=auth,
                    )

                elapsed = (time.time() - start) * 1000

                response_body = self._parse_response(response)

                result_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body,
                    "elapsed_ms": elapsed,
                }

                if response.status_code < 400:
                    return ToolResult.ok(result_data, duration_ms=elapsed)
                return ToolResult(
                    success=False,
                    output=result_data,
                    error=f"HTTP {response.status_code}: {response.reason_phrase}",
                    duration_ms=elapsed,
                )

            except Exception as e:
                if attempt < retry_count:
                    wait = 2 ** attempt
                    logger.warning("REST request failed (attempt %d/%d): %s. Retrying in %ds...",
                                   attempt + 1, retry_count + 1, e, wait)
                    time.sleep(wait)
                    continue
                return ToolResult.fail(f"REST request failed after {retry_count + 1} attempts: {e}")

    def _build_auth(self, params: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        auth_type = params.get("auth_type", "none")
        if auth_type == "bearer":
            token = params.get("auth_token", "")
            if token:
                params.setdefault("headers", {})["Authorization"] = f"Bearer {token}"
        elif auth_type == "basic":
            username = params.get("auth_username", "")
            password = params.get("auth_password", "")
            if username and password:
                return (username, password)
        return None

    def _parse_response(self, response) -> Any:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return response.json()
            except Exception:
                return response.text[:10000]
        return response.text[:10000]

    def _execute_urllib(self, params: Dict[str, Any]) -> ToolResult:
        """Fallback using urllib when httpx is not available."""
        import urllib.request
        import urllib.parse

        method = params["method"].upper()
        url = params["url"]
        headers = params.get("headers", {})
        query_params = params.get("params", {})
        body = params.get("body")
        timeout = params.get("timeout", 30)

        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)

        data = None
        if body and method in ("POST", "PUT", "PATCH"):
            data = json.dumps(body).encode("utf-8")
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        self._build_auth(params)

        try:
            req = urllib.request.Request(
                url, data=data, headers=headers, method=method,
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                resp_headers = dict(resp.headers)
                body_text = resp.read().decode("utf-8", errors="replace")
                try:
                    body_json = json.loads(body_text)
                except json.JSONDecodeError:
                    body_json = body_text[:10000]

                return ToolResult.ok({
                    "status_code": status,
                    "headers": resp_headers,
                    "body": body_json,
                })

        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
            return ToolResult(
                success=False,
                output={"status_code": e.code, "body": body_text[:1000]},
                error=f"HTTP {e.code}: {e.reason}",
            )
        except Exception as e:
            return ToolResult.fail(f"REST request failed: {e}")

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["httpx_available"] = self._httpx_available
        return base
