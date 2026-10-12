"""WebSocket manager — upgrade handling, client registry, broadcast."""

from __future__ import annotations

import asyncio
import hashlib
import json
import base64
import struct
import logging
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WSClient:
    def __init__(self, client_id: str, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.id = client_id
        self.reader = reader
        self.writer = writer
        self.connected_at = datetime.utcnow()
        self._closed = False

    async def send(self, data: dict):
        if self._closed:
            return
        try:
            payload = json.dumps(data, default=str).encode("utf-8")
            frame = self._encode_frame(payload, 0x1)
            self.writer.write(frame)
            await self.writer.drain()
        except Exception as e:
            logger.debug("WS send error: %s", e)
            self._closed = True

    async def recv(self) -> Optional[dict]:
        if self._closed:
            return None
        try:
            frame = await self._read_frame()
            if frame is None:
                self._closed = True
                return None
            opcode, payload = frame
            if opcode == 0x8:
                self._closed = True
                return None
            if opcode == 0x9:
                await self._send_pong()
                return None
            return json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.debug("WS recv error: %s", e)
            self._closed = True
            return None

    async def close(self):
        self._closed = True
        try:
            frame = self._encode_frame(b"", 0x8)
            self.writer.write(frame)
            await self.writer.drain()
            self.writer.close()
        except Exception:
            pass

    def _encode_frame(self, payload: bytes, opcode: int) -> bytes:
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.extend([126, (length >> 8) & 0xFF, length & 0xFF])
        else:
            header.extend([127] + [(length >> (56 - i * 8)) & 0xFF for i in range(8)])
        return bytes(header) + payload

    async def _read_frame(self) -> Optional[tuple]:
        b1 = await self.reader.readexactly(1)
        opcode = b1[0] & 0x0F
        b2 = await self.reader.readexactly(1)
        masked = (b2[0] & 0x80) != 0
        length = b2[0] & 0x7F
        if length == 126:
            raw = await self.reader.readexactly(2)
            length = struct.unpack(">H", raw)[0]
        elif length == 127:
            raw = await self.reader.readexactly(8)
            length = struct.unpack(">Q", raw)[0]
        mask = b""
        if masked:
            mask = await self.reader.readexactly(4)
        payload = await self.reader.readexactly(length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    async def _send_pong(self):
        frame = self._encode_frame(b"", 0xA)
        self.writer.write(frame)
        await self.writer.drain()


class WebSocketManager:
    def __init__(self):
        self.clients: dict[str, WSClient] = {}
        self.channels: dict[str, set[str]] = {}
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)

    async def emit(self, event: str, client_id: str, data: dict):
        handlers = self._handlers.get(event, [])
        for h in handlers:
            try:
                await h(client_id, data)
            except Exception as e:
                logger.error("WS handler error: %s", e)

    async def handle_upgrade(self, reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter,
                              headers: dict, path: str):
        key = headers.get("sec-websocket-key", "")
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                         ).digest()).decode()
        resp = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        ).encode()
        writer.write(resp)
        await writer.drain()
        import uuid
        client_id = str(uuid.uuid4())[:8]
        client = WSClient(client_id, reader, writer)
        self.clients[client_id] = client
        logger.debug("WS client connected: %s", client_id)
        try:
            while not client._closed:
                msg = await client.recv()
                if msg is None:
                    break
                msg_type = msg.get("type", "")
                if msg_type == "subscribe":
                    channel = msg.get("channel", "default")
                    self.channels.setdefault(channel, set()).add(client_id)
                    await client.send({"type": "subscribed", "channel": channel})
                elif msg_type == "unsubscribe":
                    channel = msg.get("channel", "")
                    self.channels.get(channel, set()).discard(client_id)
                else:
                    await self.emit(msg_type, client_id, msg)
        except Exception as e:
            logger.debug("WS client error: %s", e)
        finally:
            self.clients.pop(client_id, None)
            for ch in self.channels.values():
                ch.discard(client_id)
            try:
                writer.close()
            except Exception:
                pass

    async def broadcast(self, channel: str, data: dict):
        client_ids = self.channels.get(channel, set())
        for cid in list(client_ids):
            client = self.clients.get(cid)
            if client:
                await client.send(data)

    async def broadcast_all(self, data: dict):
        for client in list(self.clients.values()):
            await client.send(data)

    async def send_to(self, client_id: str, data: dict):
        client = self.clients.get(client_id)
        if client:
            await client.send(data)

    async def shutdown(self):
        for client in list(self.clients.values()):
            await client.close()
        self.clients.clear()
        self.channels.clear()
