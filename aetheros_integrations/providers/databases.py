"""AetherOS Integrations — database connector adapters.

SQLite (real, built-in), PostgreSQL, MySQL, MSSQL, MongoDB, Redis, Elastic.
Each runs a real query through its client library when available and reports
availability honestly. SQLite is fully functional with no external deps.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class SQLiteProvider(RESTProvider):
    definition = ProviderDefinition(
        key="sqlite",
        category=IntegrationCategory.DATABASE,
        display_name="SQLite",
        description="Query a local SQLite database.",
        auth_method=AuthMethod.NONE,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self) -> sqlite3.Connection:
        path = self.config.get("database", "")
        if not path:
            raise ValueError("sqlite database path not configured")
        import os

        if not os.path.exists(path):
            raise ValueError(f"sqlite database not found: {path}")
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def ping(self) -> HealthStatus:
        try:
            conn = self._connect()
            conn.execute("SELECT 1")
            conn.close()
            return HealthStatus.HEALTHY
        except (ValueError, sqlite3.Error, OSError):
            return HealthStatus.UNHEALTHY

    def run_query(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
        except (ValueError, sqlite3.Error, OSError) as exc:
            return [{"error": str(exc)}]
        try:
            cur = conn.execute(sql, params or [])
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        except sqlite3.Error as exc:
            return [{"error": str(exc)}]
        finally:
            conn.close()

    def run_statement(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> Dict[str, Any]:
        try:
            conn = self._connect()
        except (ValueError, sqlite3.Error, OSError) as exc:
            return {"success": False, "error": str(exc)}
        try:
            cur = conn.execute(sql, params or [])
            conn.commit()
            return {"success": True, "rowcount": cur.rowcount, "lastrowid": cur.lastrowid}
        except sqlite3.Error as exc:
            return {"success": False, "error": str(exc)}
        finally:
            conn.close()


class _DriverProvider(RESTProvider):
    """Base for client-driver databases. Requires the driver installed."""

    def _driver_name(self) -> str:
        raise NotImplementedError

    def _connect(self):
        raise NotImplementedError

    def ping(self) -> HealthStatus:
        try:
            conn = self._connect()
            try:
                if self._driver_name() == "redis":
                    conn.ping()
                else:
                    conn.cursor().execute("SELECT 1")
            finally:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
            return HealthStatus.HEALTHY
        except (ImportError, ModuleNotFoundError):
            return HealthStatus.UNAVAILABLE
        except Exception:  # noqa: BLE001
            return HealthStatus.UNHEALTHY

    def _import(self, name: str):
        try:
            return __import__(name, fromlist=["x"])
        except ImportError as exc:
            raise ModuleNotFoundError(f"Driver '{name}' not installed for {self.definition.key}") from exc


@register_provider
class PostgreSQLProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="postgresql",
        category=IntegrationCategory.DATABASE,
        display_name="PostgreSQL",
        description="Query PostgreSQL via psycopg2/psycopg (optional).",
        auth_method=AuthMethod.BASIC,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self):
        try:
            psycopg = self._import("psycopg")
            conn = psycopg.connect(host=self.config.get("host", ""), port=int(self.config.get("port", 5432)), dbname=self.config.get("database", ""), user=self.config.get("user", ""), password=self.config.get("password", ""))
        except ModuleNotFoundError:
            psycopg2 = self._import("psycopg2")
            conn = psycopg2.connect(host=self.config.get("host", ""), port=int(self.config.get("port", 5432)), dbname=self.config.get("database", ""), user=self.config.get("user", ""), password=self.config.get("password", ""))
        return conn

    def run_query(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
        except (ModuleNotFoundError, Exception) as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class MySQLProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="mysql",
        category=IntegrationCategory.DATABASE,
        display_name="MySQL",
        description="Query MySQL via PyMySQL/MySQLdb (optional).",
        auth_method=AuthMethod.BASIC,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self):
        try:
            pymysql = self._import("pymysql")
            conn = pymysql.connect(host=self.config.get("host", ""), port=int(self.config.get("port", 3306)), database=self.config.get("database", ""), user=self.config.get("user", ""), password=self.config.get("password", ""))
        except ModuleNotFoundError:
            MySQLdb = self._import("MySQLdb")
            conn = MySQLdb.connect(host=self.config.get("host", ""), port=int(self.config.get("port", 3306)), db=self.config.get("database", ""), user=self.config.get("user", ""), passwd=self.config.get("password", ""))
        return conn

    def run_query(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
        except (ModuleNotFoundError, Exception) as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class MSSQLProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="mssql",
        category=IntegrationCategory.DATABASE,
        display_name="Microsoft SQL Server",
        description="Query SQL Server via pyodbc (optional).",
        auth_method=AuthMethod.BASIC,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self):
        pyodbc = self._import("pyodbc")
        server = self.config.get("server", "")
        database = self.config.get("database", "")
        user = self.config.get("user", "")
        password = self.config.get("password", "")
        if user and password:
            connstr = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={user};PWD={password}"
        else:
            connstr = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes"
        return pyodbc.connect(connstr)

    def run_query(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
        except (ModuleNotFoundError, Exception) as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class MongoDBProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="mongodb",
        category=IntegrationCategory.DATABASE,
        display_name="MongoDB",
        description="Query MongoDB via pymongo (optional).",
        auth_method=AuthMethod.BASIC,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self):
        pymongo = self._import("pymongo")
        uri = self.config.get("uri", "")
        if not uri:
            uri = f"mongodb://{self.config.get('host', 'localhost')}:{self.config.get('port', 27017)}/"
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        return client

    def ping(self) -> HealthStatus:
        try:
            client = self._connect()
            client.admin.command("ping")
            client.close()
            return HealthStatus.HEALTHY
        except (ModuleNotFoundError, ImportError):
            return HealthStatus.UNAVAILABLE
        except Exception:  # noqa: BLE001
            return HealthStatus.UNHEALTHY

    def run_query(self, collection: str, filter_expr: Optional[Dict[str, Any]] = None, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        try:
            client = self._connect()
        except (ModuleNotFoundError, ImportError) as exc:
            return [{"error": str(exc)}]
        try:
            db = client[self.config.get("database", "default")]
            cursor = db[collection].find(filter_expr or {}, {"_id": 0})
            rows = []
            for doc in cursor.limit(limit):
                rows.append(_serializable(doc))
            return rows
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class RedisProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="redis",
        category=IntegrationCategory.DATABASE,
        display_name="Redis",
        description="Read/write Redis keys via redis-py (optional).",
        auth_method=AuthMethod.BASIC,
        capabilities=["run_query", "run_statement"],
    )

    def _connect(self):
        redis = self._import("redis")
        return redis.Redis(host=self.config.get("host", "localhost"), port=int(self.config.get("port", 6379)), password=self.config.get("password", "") or None, decode_responses=True)

    def run_query(self, key: str, **kwargs) -> List[Dict[str, Any]]:
        try:
            r = self._connect()
        except (ModuleNotFoundError, ImportError) as exc:
            return [{"error": str(exc)}]
        try:
            value = r.get(key)
            return [{"key": key, "value": value}]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                r.close()
            except Exception:  # noqa: BLE001
                pass

    def run_statement(self, op: str = "set", key: str = "", value: str = "", **kwargs) -> Dict[str, Any]:
        try:
            r = self._connect()
        except (ModuleNotFoundError, ImportError) as exc:
            return {"success": False, "error": str(exc)}
        try:
            if op == "set":
                r.set(key, value)
            elif op == "delete":
                r.delete(key)
            else:
                return {"success": False, "error": f"unsupported op {op}"}
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
        finally:
            try:
                r.close()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class ElasticProvider(_DriverProvider):
    definition = ProviderDefinition(
        key="elastic",
        category=IntegrationCategory.DATABASE,
        display_name="Elasticsearch",
        description="Query Elasticsearch via the elasticsearch client (optional).",
        auth_method=AuthMethod.BASIC,
        base_url="http://localhost:9200",
        capabilities=["run_query", "search"],
    )

    def _connect(self):
        elasticsearch = self._import("elasticsearch")
        return elasticsearch.Elasticsearch(self.config.get("base_url", self.definition.base_url), basic_auth=(self.config.get("user", ""), self.config.get("password", "")) or None)

    def run_query(self, index: str, query: Dict[str, Any], size: int = 50, **kwargs) -> List[Dict[str, Any]]:
        try:
            es = self._connect()
        except (ModuleNotFoundError, ImportError) as exc:
            return [{"error": str(exc)}]
        try:
            resp = es.search(index=index, body=query, size=size)
            return [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]
        finally:
            try:
                es.close()
            except Exception:  # noqa: BLE001
                pass


def _serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serializable(v) for v in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)
