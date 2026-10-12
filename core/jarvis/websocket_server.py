from __future__ import annotations

import os
import sys
import json
import time
import uuid
import logging
import asyncio
import threading
from typing import Any, Optional

from core.jarvis.engine import JarvisEngine, EnginePhase
from core.jarvis.startup import get_engine, boot_sequence
from core.jarvis.observer import ObserverEvent, EventType
from core.jarvis.notifications import NotificationLevel, NotificationSource

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class JarvisWebSocketServer:
    def __init__(self, engine: JarvisEngine, host: str = "127.0.0.1", port: int = 9789):
        self.engine = engine
        self.host = host
        self.port = port
        self._clients: set[WebSocket] = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        if HAS_FASTAPI:
            self.app = FastAPI(title="Jarvis Engine Bridge")
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            self._register_routes()
        else:
            self.app = None

    def _register_routes(self):
        if not HAS_FASTAPI:
            return

        engine = self.engine

        @self.app.get("/api/jarvis/status")
        async def get_status():
            return {
                "engine": engine.get_state(),
                "autonomy": engine.autonomy.state,
                "stats": engine.get_stats(),
                "context": engine.context.to_dict(),
            }

        @self.app.get("/api/jarvis/stats")
        async def get_stats():
            return engine.get_stats()

        @self.app.get("/api/jarvis/memory")
        async def get_memory(query: str = "", type: str = "", limit: int = 20):
            entries = engine.memory.search(query, type=type or None, limit=limit)
            return {
                "entries": [
                    {"id": e.id, "type": e.type, "key": e.key,
                     "content": e.content, "timestamp": e.timestamp,
                     "tags": e.tags}
                    for e in entries
                ],
                "stats": engine.memory.get_stats(),
            }

        @self.app.post("/api/jarvis/memory")
        async def add_memory(data: dict):
            entry = engine.memory.remember(
                key=data.get("key", ""),
                content=data.get("content", ""),
                type=data.get("type", "fact"),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
            )
            return {"id": entry.id, "success": True}

        @self.app.get("/api/jarvis/notifications")
        async def get_notifications():
            return {
                "notifications": [
                    {"id": n.id, "title": n.title, "message": n.message,
                     "level": n.level.value, "source": n.source.value,
                     "timestamp": n.timestamp, "read": n.read}
                    for n in engine.notifications.notifications
                ],
                "stats": engine.notifications.get_stats(),
            }

        @self.app.post("/api/jarvis/command")
        async def execute_command(data: dict):
            command = data.get("command", "")
            if command:
                engine.execute_command(command)
                return {"success": True, "message": f"Command queued: {command[:60]}"}
            return {"success": False, "message": "No command provided"}

        @self.app.post("/api/jarvis/engine/start")
        async def start_engine():
            engine.start()
            return {"success": True, "state": engine.get_state()}

        @self.app.post("/api/jarvis/engine/stop")
        async def stop_engine():
            engine.stop()
            return {"success": True, "state": engine.get_state()}

        @self.app.post("/api/jarvis/engine/pause")
        async def pause_engine():
            engine.pause()
            return {"success": True}

        @self.app.post("/api/jarvis/engine/resume")
        async def resume_engine():
            engine.resume()
            return {"success": True}

        @self.app.post("/api/jarvis/autonomy")
        async def set_autonomy(data: dict):
            enabled = data.get("enabled", False)
            level = data.get("level", "suggestions")
            if enabled:
                engine.autonomy.enabled = True
                engine.autonomy.level = level
            else:
                engine.autonomy.enabled = False
            return {"success": True, "state": engine.autonomy.state}

        @self.app.get("/api/jarvis/autonomy/pending")
        async def get_pending():
            suggestions = engine.autonomy.get_pending()
            return {
                "suggestions": [
                    {
                        "timestamp": s.timestamp,
                        "event_type": s.result.event_type,
                        "summary": s.result.summary,
                        "suggestions": [
                            {"title": sug.title, "description": sug.description,
                             "priority": sug.priority, "category": sug.category}
                            for sug in s.result.suggestions
                        ],
                    }
                    for s in suggestions
                ]
            }

        @self.app.post("/api/jarvis/autonomy/accept")
        async def accept_suggestion(data: dict):
            index = data.get("index", 0)
            result = engine.autonomy.accept(index)
            if result:
                return {"success": True, "suggestion": result.summary}
            return {"success": False, "error": "No suggestion at index"}

        @self.app.post("/api/jarvis/autonomy/reject")
        async def reject_suggestion(data: dict):
            index = data.get("index", 0)
            engine.autonomy.reject(index)
            return {"success": True}

        @self.app.get("/api/jarvis/planner/graphs")
        async def get_graphs():
            graphs = engine.planner.get_all_graphs()
            return {
                "graphs": [
                    {
                        "id": g.id, "goal": g.goal, "status": g.status.value,
                        "created_at": g.created_at, "started_at": g.started_at,
                        "completed_at": g.completed_at, "priority": g.priority,
                        "nodes": [
                            {"id": n.id, "label": n.label, "status": n.status.value,
                             "progress": n.progress, "priority": n.priority}
                            for n in g.nodes
                        ],
                        "status_summary": engine.planner.get_graph_status(g.id),
                    }
                    for g in graphs
                ]
            }

        @self.app.get("/api/jarvis/scheduler/jobs")
        async def get_jobs():
            jobs = engine.scheduler.get_all_jobs()
            return {
                "jobs": [
                    {"id": j.id, "name": j.name, "type": j.type.value,
                     "enabled": j.enabled, "last_run": j.last_run,
                     "next_run": j.next_run, "run_count": j.run_count}
                    for j in jobs
                ]
            }

        @self.app.get("/api/jarvis/context")
        async def get_context():
            return engine.context.to_dict()

        @self.app.get("/api/jarvis/executor/tasks")
        async def get_tasks():
            tasks = engine.executor.get_all_tasks()
            return {
                "tasks": [
                    {"id": t.id, "type": t.type, "description": t.description,
                     "status": t.status, "progress": t.progress,
                     "started_at": t.started_at, "completed_at": t.completed_at,
                     "error": t.error}
                    for t in tasks[-50:]
                ]
            }

        @self.app.get("/api/jarvis/observer/events")
        async def get_events(limit: int = 20):
            events = engine.observer.recent_events[:limit]
            return {
                "events": [
                    {"type": e.type.value if isinstance(e.type, EventType) else e.type,
                     "data": e.data, "timestamp": e.timestamp, "source": e.source}
                    for e in events
                ]
            }

        @self.app.get("/api/jarvis/health")
        async def health_check():
            return {
                "status": "healthy",
                "engine_running": engine.is_running,
                "engine_phase": engine.phase,
                "observer_running": engine.observer._running if hasattr(engine.observer, '_running') else False,
                "scheduler_running": engine.scheduler._running if hasattr(engine.scheduler, '_running') else False,
                "memory_entries": len(engine.memory._entries) if hasattr(engine.memory, '_entries') else 0,
                "notifications_unread": engine.notifications.unread_count,
            }

        @self.app.websocket("/api/jarvis/ws")
        async def jarvis_websocket(ws: WebSocket):
            await ws.accept()
            self._clients.add(ws)
            client_id = uuid.uuid4().hex[:8]
            logger.info(f"Jarvis WS client connected: {client_id}")

            def on_engine_state(state: dict):
                try:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(
                        ws.send_json({"type": "engine:state", "data": state}),
                        asyncio.get_event_loop(),
                    )
                except Exception:
                    pass

            def on_notification(notif):
                try:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(
                        ws.send_json({
                            "type": "notification",
                            "data": {
                                "id": notif.id, "title": notif.title,
                                "message": notif.message, "level": notif.level.value,
                                "source": notif.source.value, "timestamp": notif.timestamp,
                                "read": notif.read,
                            },
                        }),
                        asyncio.get_event_loop(),
                    )
                except Exception:
                    pass

            def on_observer_event(event: ObserverEvent):
                try:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(
                        ws.send_json({
                            "type": "observer:event",
                            "data": {
                                "type": event.type.value if isinstance(event.type, EventType) else event.type,
                                "data": event.data,
                                "timestamp": event.timestamp,
                            },
                        }),
                        asyncio.get_event_loop(),
                    )
                except Exception:
                    pass

            unsub_state = engine.on_state_change(on_engine_state)
            unsub_notif = engine.notifications.on_notification(on_notification)
            unsub_event = engine.observer.on("*", on_observer_event)

            try:
                await ws.send_json({"type": "connected", "data": {"client_id": client_id, "engine_state": engine.get_state()}})

                while True:
                    try:
                        raw = await ws.receive_text()
                    except WebSocketDisconnect:
                        break

                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg_type = msg.get("type", "")
                    payload = msg.get("data", {})

                    if msg_type == "command":
                        engine.execute_command(payload.get("command", ""))
                        await ws.send_json({"type": "command:ack", "data": {"success": True}})
                    elif msg_type == "engine:start":
                        engine.start()
                        await ws.send_json({"type": "engine:state", "data": engine.get_state()})
                    elif msg_type == "engine:stop":
                        engine.stop()
                        await ws.send_json({"type": "engine:state", "data": engine.get_state()})
                    elif msg_type == "engine:pause":
                        engine.pause()
                        await ws.send_json({"type": "engine:state", "data": engine.get_state()})
                    elif msg_type == "engine:resume":
                        engine.resume()
                        await ws.send_json({"type": "engine:state", "data": engine.get_state()})
                    elif msg_type == "autonomy:set":
                        engine.autonomy.enabled = payload.get("enabled", False)
                        if payload.get("level"):
                            engine.autonomy.level = payload.get("level")
                        await ws.send_json({"type": "autonomy:state", "data": engine.autonomy.state})
                    elif msg_type == "ping":
                        await ws.send_json({"type": "pong", "data": {"timestamp": time.time()}})

            except Exception as e:
                logger.error(f"WS error: {e}")
            finally:
                unsub_state()
                unsub_notif()
                unsub_event()
                self._clients.discard(ws)
                try:
                    await ws.close()
                except Exception:
                    pass
                logger.info(f"Jarvis WS client disconnected: {client_id}")

    def _run_server(self):
        if not HAS_FASTAPI:
            logger.error("FastAPI not available - cannot start WebSocket server")
            return
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True, name="jarvis-ws-server")
        self._thread.start()
        logger.info(f"Jarvis WebSocket server starting on {self.host}:{self.port}")

    def stop(self):
        self._running = False
        logger.info("Jarvis WebSocket server stopped")

    def broadcast(self, message: dict):
        if not HAS_FASTAPI:
            return
        import asyncio
        for client in self._clients.copy():
            try:
                asyncio.run_coroutine_threadsafe(
                    client.send_json(message),
                    asyncio.get_event_loop(),
                )
            except Exception:
                pass


def run_jarvis_server(host: str = "127.0.0.1", port: int = 9789,
                      storage_dir: Optional[str] = None) -> JarvisWebSocketServer:
    if storage_dir:
        from pathlib import Path
        storage_path = Path(storage_dir)
    else:
        storage_path = None

    engine = boot_sequence(storage_dir=storage_path)
    server = JarvisWebSocketServer(engine, host=host, port=port)
    server.start()
    return server
