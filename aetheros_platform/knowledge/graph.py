"""Knowledge graph — SQLite-backed property graph for entities and relations."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT DEFAULT '{}',
                    source TEXT DEFAULT '',
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT DEFAULT '{}',
                    weight REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES kg_entities(id),
                    FOREIGN KEY (target_id) REFERENCES kg_entities(id)
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_entity_type
                ON kg_entities(type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_entity_name
                ON kg_entities(name)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_relation_source
                ON kg_relations(source_id)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_relation_target
                ON kg_relations(target_id)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_relation_type
                ON kg_relations(type)
            """)
            self._conn.commit()

    def add_entity(self, entity_id: str, entity_type: str, name: str,
                    properties: dict = None, source: str = "",
                    confidence: float = 1.0) -> bool:
        now = datetime.utcnow().isoformat() + "Z"
        props = json.dumps(properties or {})
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT OR REPLACE INTO kg_entities
                       (id, type, name, properties, source, confidence, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, COALESCE(
                           (SELECT created_at FROM kg_entities WHERE id=?), ?), ?)""",
                    (entity_id, entity_type, name, props, source, confidence,
                     entity_id, now, now))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("add_entity error: %s", e)
            return False

    def update_entity(self, entity_id: str, properties: dict = None,
                       name: str = None, confidence: float = None) -> bool:
        now = datetime.utcnow().isoformat() + "Z"
        updates = []
        params = []
        if properties is not None:
            updates.append("properties = ?")
            params.append(json.dumps(properties))
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        updates.append("updated_at = ?")
        params.append(now)
        params.append(entity_id)
        try:
            with self._lock:
                self._conn.execute(
                    f"UPDATE kg_entities SET {', '.join(updates)} WHERE id=?",
                    params)
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("update_entity error: %s", e)
            return False

    def get_entity(self, entity_id: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM kg_entities WHERE id=?", (entity_id,))
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_entity(row)

    def get_entity_by_name(self, name: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM kg_entities WHERE name=?", (name,))
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_entity(row)

    def search_entities(self, query: str, limit: int = 20) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM kg_entities WHERE name LIKE ? OR properties LIKE ? "
                "ORDER BY confidence DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", limit))
            return [self._row_to_entity(r) for r in cur.fetchall()]

    def list_entities(self, entity_type: str = None, limit: int = 100) -> list[dict]:
        with self._lock:
            if entity_type:
                cur = self._conn.execute(
                    "SELECT * FROM kg_entities WHERE type=? ORDER BY updated_at DESC LIMIT ?",
                    (entity_type, limit))
            else:
                cur = self._conn.execute(
                    "SELECT * FROM kg_entities ORDER BY updated_at DESC LIMIT ?",
                    (limit,))
            return [self._row_to_entity(r) for r in cur.fetchall()]

    def delete_entity(self, entity_id: str) -> bool:
        try:
            with self._lock:
                self._conn.execute("DELETE FROM kg_relations WHERE source_id=? OR target_id=?",
                                    (entity_id, entity_id))
                self._conn.execute("DELETE FROM kg_entities WHERE id=?", (entity_id,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("delete_entity error: %s", e)
            return False

    def add_relation(self, relation_id: str, source_id: str, target_id: str,
                      relation_type: str, properties: dict = None,
                      weight: float = 1.0) -> bool:
        now = datetime.utcnow().isoformat() + "Z"
        props = json.dumps(properties or {})
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT OR REPLACE INTO kg_relations
                       (id, source_id, target_id, type, properties, weight, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (relation_id, source_id, target_id, relation_type,
                     props, weight, now))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("add_relation error: %s", e)
            return False

    def get_relations(self, entity_id: str,
                       direction: str = "both") -> list[dict]:
        with self._lock:
            if direction == "outgoing":
                cur = self._conn.execute(
                    "SELECT r.*, e.name as target_name, e.type as target_type "
                    "FROM kg_relations r JOIN kg_entities e ON r.target_id=e.id "
                    "WHERE r.source_id=? ORDER BY r.weight DESC",
                    (entity_id,))
            elif direction == "incoming":
                cur = self._conn.execute(
                    "SELECT r.*, e.name as source_name, e.type as source_type "
                    "FROM kg_relations r JOIN kg_entities e ON r.source_id=e.id "
                    "WHERE r.target_id=? ORDER BY r.weight DESC",
                    (entity_id,))
            else:
                cur = self._conn.execute(
                    """SELECT r.*, e1.name as source_name, e1.type as source_type,
                              e2.name as target_name, e2.type as target_type
                       FROM kg_relations r
                       JOIN kg_entities e1 ON r.source_id=e1.id
                       JOIN kg_entities e2 ON r.target_id=e2.id
                       WHERE r.source_id=? OR r.target_id=?
                       ORDER BY r.weight DESC""",
                    (entity_id, entity_id))
            return [self._row_to_relation(r) for r in cur.fetchall()]

    def get_subgraph(self, entity_id: str, depth: int = 1) -> dict:
        entities = {}
        relations = []
        def _traverse(eid: str, remaining: int, visited: set):
            if remaining < 0 or eid in visited:
                return
            visited.add(eid)
            entity = self.get_entity(eid)
            if entity:
                entities[eid] = entity
            for rel in self.get_relations(eid):
                rel_key = rel["id"]
                if rel_key not in {r["id"] for r in relations}:
                    relations.append(rel)
                other = rel["target_id"] if rel["source_id"] == eid else rel["source_id"]
                if other != eid:
                    _traverse(other, remaining - 1, visited)
        _traverse(entity_id, depth, set())
        return {"entities": list(entities.values()), "relations": relations}

    def get_stats(self) -> dict:
        with self._lock:
            ent_count = self._conn.execute(
                "SELECT COUNT(*) FROM kg_entities").fetchone()[0]
            rel_count = self._conn.execute(
                "SELECT COUNT(*) FROM kg_relations").fetchone()[0]
            type_counts = self._conn.execute(
                "SELECT type, COUNT(*) as c FROM kg_entities "
                "GROUP BY type ORDER BY c DESC").fetchall()
            rel_type_counts = self._conn.execute(
                "SELECT type, COUNT(*) as c FROM kg_relations "
                "GROUP BY type ORDER BY c DESC").fetchall()
        return {
            "entities": ent_count,
            "relations": rel_count,
            "entity_types": dict(type_counts),
            "relation_types": dict(rel_type_counts),
        }

    def clear(self):
        with self._lock:
            self._conn.execute("DELETE FROM kg_relations")
            self._conn.execute("DELETE FROM kg_entities")
            self._conn.commit()

    def close(self):
        self._conn.close()

    @staticmethod
    def _row_to_entity(row: sqlite3.Row) -> dict:
        return {
            "id": row[0], "type": row[1], "name": row[2],
            "properties": json.loads(row[3]) if isinstance(row[3], str) else row[3],
            "source": row[4], "confidence": row[5],
            "created_at": row[6], "updated_at": row[7],
        }

    @staticmethod
    def _row_to_relation(row: sqlite3.Row) -> dict:
        result = {
            "id": row[0], "source_id": row[1], "target_id": row[2],
            "type": row[3],
            "properties": json.loads(row[4]) if isinstance(row[4], str) else row[4],
            "weight": row[5], "created_at": row[6],
        }
        names = ["source_name", "source_type", "target_name", "target_type"]
        for i, n in enumerate(names):
            idx = 7 + i
            if idx < len(row):
                result[n] = row[idx]
        return result
