"""
Live Session Server — WebSocket bridge between the terminal agent and browser.

Runs on http://localhost:8080, serves the chat SPA, and exposes a WebSocket
endpoint that mirrors the agent conversation in real time.  Both terminal and
browser share one session — never two agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event bus — shared between the CLI thread and the WebSocket server
# ---------------------------------------------------------------------------

_event_loop: asyncio.AbstractEventLoop | None = None
_websocket_clients: set[WebSocket] = set()
_message_queue: asyncio.Queue[dict] = asyncio.Queue()
_browser_input_queue: list[str] = []
_input_lock = threading.Lock()
_server_started = threading.Event()


def broadcast(event: str, data: dict) -> None:
    """Enqueue an event to be sent to all connected WebSocket clients."""
    msg = json.dumps({"event": event, "data": data, "timestamp": time.time()})
    try:
        asyncio.run_coroutine_threadsafe(
            _send_to_all(msg), _event_loop
        )
    except RuntimeError:
        pass  # event loop not ready yet


def broadcast_sync(event: str, data: dict) -> None:
    """Synchronous version — call from any thread."""
    if _event_loop and _event_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            _send_to_all(json.dumps({
                "event": event, "data": data, "timestamp": time.time()
            })),
            _event_loop
        )


async def _send_to_all(msg: str) -> None:
    disconnected = set()
    for ws in _websocket_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.add(ws)
    _websocket_clients.difference_update(disconnected)


def get_browser_input() -> str | None:
    """Check for input submitted from the browser. Called from the CLI thread."""
    with _input_lock:
        if _browser_input_queue:
            return _browser_input_queue.pop(0)
    return None


def has_browser_input() -> bool:
    with _input_lock:
        return len(_browser_input_queue) > 0


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _event_loop
    _event_loop = asyncio.get_event_loop()
    _server_started.set()
    yield


app = FastAPI(lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
async def get_status():
    """Return server and agent status."""
    return JSONResponse({
        "status": "running",
        "clients": len(_websocket_clients),
        "uptime": time.time() - _start_time,
    })


@app.get("/api/session")
async def get_session():
    """Return current session info."""
    from aetheros_state import SessionDB
    try:
        db = SessionDB()
        sessions = db.list_sessions(limit=20)
        return JSONResponse({"sessions": sessions})
    except Exception as exc:
        return JSONResponse({"sessions": [], "error": str(exc)})


@app.get("/api/config")
async def get_config():
    """Return relevant config for the dashboard."""
    from aetheros_cli.config import load_config
    try:
        cfg = load_config()
        return JSONResponse({
            "model": cfg.get("model", ""),
            "provider": cfg.get("provider", ""),
            "language": cfg.get("language", "en"),
            "timezone": cfg.get("timezone", "UTC"),
            "terminal_backend": cfg.get("terminal", {}).get("backend", "local"),
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)})


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for live conversation sync."""
    await ws.accept()
    _websocket_clients.add(ws)
    logger.debug("WebSocket client connected (%d total)", len(_websocket_clients))

    # Send welcome
    await ws.send_text(json.dumps({
        "event": "connected",
        "data": {"message": "Connected to AetherOS live session"},
        "timestamp": time.time(),
    }))

    # Send current conversation state
    _send_conversation_history(ws)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            event = data.get("event", "")
            payload = data.get("data", {})

            if event == "user_message":
                # Inject message into the CLI agent loop
                text = payload.get("text", "")
                with _input_lock:
                    _browser_input_queue.append(text)
                broadcast("input_received", {"text": text, "source": "browser"})

            elif event == "ping":
                await ws.send_text(json.dumps({
                    "event": "pong", "data": {}, "timestamp": time.time()
                }))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket error: %s", exc)
    finally:
        _websocket_clients.discard(ws)
        logger.debug("WebSocket client disconnected (%d remaining)", len(_websocket_clients))


def _send_conversation_history(ws: WebSocket) -> None:
    """Send the current conversation history to a newly connected client."""
    try:
        from aetheros_state import SessionDB
        db = SessionDB()
        active = db.get_active_session()
        if active:
            history = db.get_session_messages(active.get("session_id", ""))
            import asyncio
            asyncio.ensure_future(
                ws.send_text(json.dumps({
                    "event": "conversation_history",
                    "data": {"messages": history or []},
                    "timestamp": time.time(),
                }))
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Server thread
# ---------------------------------------------------------------------------

_start_time: float = 0.0


def _run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the uvicorn server in a thread."""
    global _start_time
    _start_time = time.time()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server.run()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_session_thread: threading.Thread | None = None


def start_session_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the live session server in a background thread."""
    global _session_thread
    if _session_thread and _session_thread.is_alive():
        logger.debug("Session server already running")
        return

    _session_thread = threading.Thread(
        target=_run_server,
        args=(host, port),
        daemon=True,
        name="session-server",
    )
    _session_thread.start()
    _server_started.wait(timeout=5)

    logger.info("Live session server running on http://%s:%d", host, port)
    print(f"  Web Dashboard:  http://localhost:{port}")


def stop_session_server() -> None:
    """Stop the session server."""
    global _session_thread
    if _session_thread:
        _session_thread = None
    logger.debug("Session server stopped")


# ---------------------------------------------------------------------------
# Conversation event helpers — call these from cli.py agent loop
# ---------------------------------------------------------------------------

def notify_message_delta(delta: str, content_so_far: str) -> None:
    """Broadcast a streaming message delta."""
    broadcast_sync("message.delta", {
        "delta": delta,
        "content": content_so_far,
    })


def notify_message_complete(role: str, content: str) -> None:
    """Broadcast a completed message."""
    broadcast_sync("message.complete", {
        "role": role,
        "content": content,
    })


def notify_tool_start(tool_name: str, args: dict) -> None:
    """Broadcast that a tool is being called."""
    broadcast_sync("tool.start", {
        "name": tool_name,
        "args": args,
    })


def notify_tool_complete(tool_name: str, result: str, duration: float) -> None:
    """Broadcast that a tool call completed."""
    broadcast_sync("tool.complete", {
        "name": tool_name,
        "result": result[:500] if result else "",
        "duration": duration,
    })


def notify_status(status: str, **kwargs) -> None:
    """Broadcast a status update."""
    broadcast_sync("status", {"status": status, **kwargs})


def notify_user_message(text: str) -> None:
    """Broadcast that the user sent a message."""
    broadcast_sync("user_message", {"text": text})
