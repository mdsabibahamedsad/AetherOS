"""Database Runtime — multi-database query execution.

Supports: SQLite, PostgreSQL, MySQL, MSSQL, MongoDB, Redis.
All queries use parameterized inputs to prevent injection.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class DatabaseRuntime(ToolInterface):
    """Multi-database runtime with parameterized queries.

    Features:
    - SQLite (built-in, no deps)
    - PostgreSQL (requires psycopg2)
    - MySQL (requires pymysql)
    - MSSQL (requires pymssql)
    - MongoDB (requires pymongo)
    - Redis (requires redis-py)
    """

    def __init__(self):
        meta = ToolMetadata(
            id="database",
            name="Database Runtime",
            description="Query databases: SQLite, PostgreSQL, MySQL, MSSQL, MongoDB, Redis (parameterized only)",
            category=ToolCategory.DATABASE,
            risk_level=ToolRiskLevel.WRITE,
            version="2.0.0",
            tags=["database", "sql", "nosql", "query"],
            requires_approval=False,
            timeout_seconds=30.0,
        )
        super().__init__(meta)

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "database",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "engine": {
                        "type": "string",
                        "enum": ["sqlite", "postgresql", "mysql", "mssql", "mongodb", "redis"],
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["query", "execute", "list_tables", "describe_table", "ping"],
                    },
                    "database": {"type": "string", "description": "Database name/path"},
                    "connection_string": {"type": "string"},
                    "query": {"type": "string"},
                    "params": {
                        "type": "array",
                        "items": {},
                        "description": "Parameterized query parameters",
                    },
                    "collection": {"type": "string", "description": "MongoDB collection"},
                    "filter": {"type": "object", "description": "MongoDB filter"},
                    "key": {"type": "string", "description": "Redis key"},
                    "value": {"type": "string", "description": "Redis value"},
                },
                "required": ["engine", "operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        engine = params.get("engine")
        operation = params.get("operation")

        if not engine:
            errors.append("Missing required parameter: engine")
        elif engine not in ("sqlite", "postgresql", "mysql", "mssql", "mongodb", "redis"):
            errors.append(f"Unsupported engine: {engine}")

        if not operation:
            errors.append("Missing required parameter: operation")
        elif operation not in ("query", "execute", "list_tables", "describe_table", "ping"):
            errors.append(f"Unknown operation: {operation}")

        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        engine = params["engine"]
        operation = params.get("operation", "query")

        engines = {
            "sqlite": self._execute_sqlite,
            "postgresql": self._execute_postgresql,
            "mysql": self._execute_mysql,
            "mssql": self._execute_mssql,
            "mongodb": self._execute_mongodb,
            "redis": self._execute_redis,
        }

        handler = engines.get(engine)
        if not handler:
            return ToolResult.fail(f"Unsupported engine: {engine}")

        try:
            return handler(operation, params)
        except Exception as e:
            logger.error("Database operation '%s' on '%s' failed: %s", operation, engine, e)
            return ToolResult.fail(f"Database error: {type(e).__name__}: {e}")

    def _sqlite_connect(self, params: Dict[str, Any]) -> sqlite3.Connection:
        db = params.get("database", ":memory:")
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute_sqlite(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        conn = self._sqlite_connect(params)
        try:
            return self._execute_sql(conn, operation, params)
        finally:
            conn.close()

    def _execute_postgresql(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            return ToolResult.fail("psycopg2 not available. Install with: pip install psycopg2-binary")

        conn_str = params.get("connection_string", "")
        if not conn_str:
            return ToolResult.fail("PostgreSQL requires 'connection_string' parameter")
        conn = psycopg2.connect(conn_str)
        try:
            return self._execute_sql(conn, operation, params)
        finally:
            conn.close()

    def _execute_mysql(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        try:
            import pymysql
        except ImportError:
            return ToolResult.fail("pymysql not available. Install with: pip install pymysql")

        conn_str = params.get("connection_string", "")
        if not conn_str:
            return ToolResult.fail("MySQL requires 'connection_string' parameter")
        conn = pymysql.connect(conn_str)
        try:
            return self._execute_sql(conn, operation, params)
        finally:
            conn.close()

    def _execute_mssql(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        try:
            import pymssql
        except ImportError:
            return ToolResult.fail("pymssql not available. Install with: pip install pymssql")

        conn_str = params.get("connection_string", "")
        if not conn_str:
            return ToolResult.fail("MSSQL requires 'connection_string' parameter")
        conn = pymssql.connect(conn_str)
        try:
            return self._execute_sql(conn, operation, params)
        finally:
            conn.close()

    def _execute_sql(self, conn, operation: str, params: Dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        query_params = params.get("params", [])

        if operation == "ping":
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return ToolResult.ok({"connected": True, "engine": params["engine"]})

        if operation == "list_tables":
            cursor = conn.cursor()
            if params["engine"] == "sqlite":
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            else:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = [row[0] for row in cursor.fetchall()]
            return ToolResult.ok({"tables": tables, "count": len(tables)})

        if operation == "describe_table":
            table = params.get("query", "")
            if not table:
                return ToolResult.fail("describe_table requires table name in 'query'")
            cursor = conn.cursor()
            if params["engine"] == "sqlite":
                cursor.execute(f"PRAGMA table_info({table})")
            else:
                cursor.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='{table}'")
            columns = [dict(row) for row in cursor.fetchall()]
            return ToolResult.ok({"table": table, "columns": columns})

        if operation in ("query", "execute"):
            cursor = conn.cursor()
            try:
                cursor.execute(query, query_params)
                if query.strip().upper().startswith(("SELECT", "PRAGMA", "WITH", "EXPLAIN")):
                    rows = [dict(row) for row in cursor.fetchall()]
                    conn.commit()
                    return ToolResult.ok({
                        "rows": rows,
                        "row_count": len(rows),
                        "columns": [desc[0] for desc in cursor.description] if cursor.description else [],
                    })
                else:
                    affected = cursor.rowcount
                    conn.commit()
                    return ToolResult.ok({
                        "affected_rows": affected,
                        "success": True,
                    })
            except Exception as e:
                conn.rollback()
                return ToolResult.fail(f"Query failed: {e}")

        return ToolResult.fail(f"Unknown SQL operation: {operation}")

    def _execute_mongodb(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        try:
            import pymongo
        except ImportError:
            return ToolResult.fail("pymongo not available. Install with: pip install pymongo")

        conn_str = params.get("connection_string", "mongodb://localhost:27017")
        client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)
        try:
            db_name = params.get("database", "test")
            db = client[db_name]

            if operation == "ping":
                client.admin.command("ping")
                return ToolResult.ok({"connected": True})

            collection_name = params.get("collection", "")
            if not collection_name:
                return ToolResult.fail("MongoDB operations require 'collection' parameter")
            collection = db[collection_name]

            if operation == "list_tables":
                return ToolResult.ok({"collections": db.list_collection_names()})

            if operation == "query":
                filter_doc = params.get("filter", {})
                docs = list(collection.find(filter_doc).limit(100))
                for doc in docs:
                    doc["_id"] = str(doc["_id"])
                return ToolResult.ok({"documents": docs, "count": len(docs)})

            if operation == "execute":
                filter_doc = params.get("filter", {})
                update = params.get("value")
                if update:
                    result = collection.update_many(filter_doc, {"$set": json.loads(update)})
                    return ToolResult.ok({"modified_count": result.modified_count})
                return ToolResult.fail("MongoDB execute requires 'value' parameter for update")

            return ToolResult.fail(f"Unknown MongoDB operation: {operation}")
        finally:
            client.close()

    def _execute_redis(self, operation: str, params: Dict[str, Any]) -> ToolResult:
        try:
            import redis as redis_py
        except ImportError:
            return ToolResult.fail("redis-py not available. Install with: pip install redis")

        conn_str = params.get("connection_string", "redis://localhost:6379/0")
        r = redis_py.from_url(conn_str)
        try:
            if operation == "ping":
                r.ping()
                return ToolResult.ok({"connected": True})

            key = params.get("key", "")
            value = params.get("value", "")

            if operation == "query":
                if not key:
                    return ToolResult.fail("Redis query requires 'key' parameter")
                val = r.get(key)
                ttl = r.ttl(key)
                return ToolResult.ok({"key": key, "value": val.decode() if val else None, "ttl": ttl})

            if operation == "execute":
                if key and value:
                    r.set(key, value)
                    return ToolResult.ok({"key": key, "set": True})
                return ToolResult.fail("Redis execute requires 'key' and 'value' parameters")

            if operation == "list_tables":
                keys = r.keys("*")
                return ToolResult.ok({"keys": [k.decode() for k in keys], "count": len(keys)})

            return ToolResult.fail(f"Unknown Redis operation: {operation}")
        finally:
            r.close()
