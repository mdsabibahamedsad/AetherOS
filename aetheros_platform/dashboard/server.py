"""Dashboard web server — lightweight async HTTP + WebSocket server."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import traceback
from typing import Any, Callable, Optional
from urllib.parse import urlparse, parse_qs
from aetheros_platform.dashboard.websocket import WebSocketManager
from aetheros_platform.dashboard.routes import RouteRegistry

logger = logging.getLogger(__name__)


class DashboardServer:
    def __init__(self, host: str = "127.0.0.1",
                 port: int = 8756,
                 static_dir: Optional[str] = None):
        self.host = host
        self.port = port
        self.static_dir = static_dir
        self.routes = RouteRegistry()
        self.ws_manager = WebSocketManager()
        self._server: Optional[asyncio.AbstractServer] = None
        self._running = False
        self._middleware: list[Callable] = []

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def add_middleware(self, fn: Callable):
        self._middleware.append(fn)

    async def start(self):
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_connection, self.host, self.port)
        logger.info("Dashboard server started at %s", self.url)

    async def stop(self):
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        await self.ws_manager.shutdown()
        logger.info("Dashboard server stopped")

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter):
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return
            method, path, version = request_line.decode().strip().split(" ", 2)
            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                key, _, value = line.decode().strip().partition(":")
                headers[key.strip().lower()] = value.strip()
            content_length = int(headers.get("content-length", 0))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)
            if headers.get("upgrade", "").lower() == "websocket":
                await self.ws_manager.handle_upgrade(
                    reader, writer, headers, path)
                return
            await self._handle_http(method, path, headers, body, writer)
        except Exception as e:
            logger.debug("Connection error: %s", e)
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_http(self, method: str, path: str,
                            headers: dict, body: bytes,
                            writer: asyncio.StreamWriter):
        parsed = urlparse(path)
        clean_path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        for mw in self._middleware:
            result = mw(method, clean_path, headers, params)
            if result:
                await self._send_response(writer, result["status"],
                                           result.get("body", ""),
                                           result.get("content_type", "text/plain"))
                writer.close()
                return
        handler = self.routes.match(method, clean_path)
        if handler:
            try:
                body_str = body.decode("utf-8") if body else "{}"
                body_json = json.loads(body_str) if body else {}
                result = await handler(body_json, params, headers, writer)
                if isinstance(result, tuple) and len(result) >= 2:
                    status, data = result[0], result[1]
                    ct = result[2] if len(result) > 2 else "application/json"
                elif isinstance(result, dict):
                    status, data, ct = 200, result, "application/json"
                else:
                    status, data, ct = 200, {"result": str(result)}, "application/json"
                if isinstance(data, (dict, list)):
                    body_out = json.dumps(data, default=str)
                elif isinstance(data, bytes):
                    body_out = data
                    ct = ct or "application/octet-stream"
                else:
                    body_out = str(data)
                if isinstance(body_out, str):
                    body_out = body_out.encode("utf-8")
                await self._send_response(writer, status, body_out, ct)
            except Exception as e:
                logger.error("Handler error: %s\n%s", e, traceback.format_exc())
                await self._send_response(writer, 500,
                                           json.dumps({"error": str(e)}).encode(),
                                           "application/json")
        else:
            if self.static_dir and not clean_path.startswith("/api/"):
                await self._serve_static(clean_path, writer)
            else:
                await self._send_response(writer, 404,
                                           json.dumps({"error": "Not found"}).encode(),
                                           "application/json")
        writer.close()

    async def _serve_static(self, path: str, writer: asyncio.StreamWriter):
        file_path = os.path.join(self.static_dir, path.lstrip("/") or "index.html")
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            ct, _ = mimetypes.guess_type(file_path)
            await self._send_response(writer, 200, data,
                                       ct or "application/octet-stream")
        else:
            index = os.path.join(self.static_dir, "index.html")
            if os.path.isfile(index):
                with open(index, "rb") as f:
                    data = f.read()
                await self._send_response(writer, 200, data, "text/html")
            else:
                await self._send_response(writer, 404,
                                           b"Not found", "text/plain")

    async def _send_response(self, writer: asyncio.StreamWriter,
                              status: int, body: bytes,
                              content_type: str = "text/plain"):
        status_text = {200: "OK", 201: "Created", 204: "No Content",
                       301: "Moved", 400: "Bad Request", 401: "Unauthorized",
                       403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
        resp = (
            f"HTTP/1.1 {status} {status_text.get(status, 'Unknown')}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Access-Control-Allow-Headers: *\r\n"
            f"Cache-Control: no-cache\r\n"
            f"\r\n"
        ).encode() + body
        writer.write(resp)
        await writer.drain()
