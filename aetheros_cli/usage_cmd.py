"""Usage dashboard — reads session usage data from the state database.

``aetheros usage`` aggregates the token/cost columns that the runtime already
writes into ``sessions`` (input_tokens, output_tokens, cache_read/write_tokens,
reasoning_tokens, estimated_cost_usd, actual_cost_usd, api_call_count,
billing_provider/model). This is a read-only presentation layer — it never
mutates the DB.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _connect(db_path: Optional[str] = None):
    from aetheros_state import DEFAULT_DB_PATH

    path = db_path or os.environ.get("AETHEROS_STATE_DB") or str(DEFAULT_DB_PATH)
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _aggregate(conn, where: str = "", params: tuple = ()) -> dict:
    base = f"FROM sessions WHERE {where}" if where else "FROM sessions"
    q = f"""
        SELECT COUNT(*) AS session_count,
               COALESCE(SUM(COALESCE(message_count, 0)), 0) AS message_count,
               COALESCE(SUM(COALESCE(tool_call_count, 0)), 0) AS tool_call_count,
               COALESCE(SUM(COALESCE(api_call_count, 0)), 0) AS api_call_count,
               COALESCE(SUM(COALESCE(input_tokens, 0)), 0) AS input_tokens,
               COALESCE(SUM(COALESCE(output_tokens, 0)), 0) AS output_tokens,
               COALESCE(SUM(COALESCE(cache_read_tokens, 0)), 0) AS cache_read_tokens,
               COALESCE(SUM(COALESCE(cache_write_tokens, 0)), 0) AS cache_write_tokens,
               COALESCE(SUM(COALESCE(reasoning_tokens, 0)), 0) AS reasoning_tokens,
               COALESCE(SUM(COALESCE(estimated_cost_usd, 0)), 0) AS estimated_cost_usd,
               COALESCE(SUM(COALESCE(actual_cost_usd, 0)), 0) AS actual_cost_usd
        {base}
    """
    try:
        row = conn.execute(q, params).fetchone()
    except sqlite3.Error:
        return {}
    if row is None:
        return {}
    return {
        "session_count": int(row["session_count"]),
        "message_count": int(row["message_count"]),
        "tool_call_count": int(row["tool_call_count"]),
        "api_call_count": int(row["api_call_count"]),
        "input_tokens": int(row["input_tokens"]),
        "output_tokens": int(row["output_tokens"]),
        "cache_read_tokens": int(row["cache_read_tokens"]),
        "cache_write_tokens": int(row["cache_write_tokens"]),
        "reasoning_tokens": int(row["reasoning_tokens"]),
        "estimated_cost_usd": round(float(row["estimated_cost_usd"]), 4),
        "actual_cost_usd": round(float(row["actual_cost_usd"]), 4),
    }


def usage_summary(db_path: Optional[str] = None) -> dict:
    """Overall usage totals for the active profile."""
    conn = _connect(db_path)
    if conn is None:
        return {"available": False, "reason": "state database not found"}
    try:
        total = _aggregate(conn)
        if not total:
            return {"available": False, "reason": "no session data"}
        total["available"] = True
        return total
    finally:
        conn.close()


def usage_by_provider(db_path: Optional[str] = None) -> list[dict]:
    """Usage grouped by billing_provider (NULL/'' → 'unattributed')."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(billing_provider, ''), 'unattributed') AS provider,
                   COUNT(*) AS session_count,
                   SUM(COALESCE(message_count, 0)) AS message_count,
                   SUM(COALESCE(api_call_count, 0)) AS api_call_count,
                   SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                   SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                   SUM(COALESCE(estimated_cost_usd, 0)) AS estimated_cost_usd,
                   SUM(COALESCE(actual_cost_usd, 0)) AS actual_cost_usd
            FROM sessions
            GROUP BY provider
            ORDER BY estimated_cost_usd DESC
            """
        ).fetchall()
        return [
            {
                "provider": r["provider"],
                "session_count": int(r["session_count"]),
                "message_count": int(r["message_count"]),
                "api_call_count": int(r["api_call_count"]),
                "input_tokens": int(r["input_tokens"]),
                "output_tokens": int(r["output_tokens"]),
                "estimated_cost_usd": round(float(r["estimated_cost_usd"]), 4),
                "actual_cost_usd": round(float(r["actual_cost_usd"]), 4),
            }
            for r in rows
        ]
    finally:
        conn.close()


def usage_by_model(db_path: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Usage grouped by model (top `limit` by estimated cost)."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(model, ''), 'unknown') AS model,
                   COUNT(*) AS session_count,
                   SUM(COALESCE(api_call_count, 0)) AS api_call_count,
                   SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                   SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                   SUM(COALESCE(estimated_cost_usd, 0)) AS estimated_cost_usd,
                   SUM(COALESCE(actual_cost_usd, 0)) AS actual_cost_usd
            FROM sessions
            GROUP BY model
            ORDER BY estimated_cost_usd DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "model": r["model"],
                "session_count": int(r["session_count"]),
                "api_call_count": int(r["api_call_count"]),
                "input_tokens": int(r["input_tokens"]),
                "output_tokens": int(r["output_tokens"]),
                "estimated_cost_usd": round(float(r["estimated_cost_usd"]), 4),
                "actual_cost_usd": round(float(r["actual_cost_usd"]), 4),
            }
            for r in rows
        ]
    finally:
        conn.close()


def usage_recent_sessions(db_path: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Most recent sessions with their usage/cost."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            """
            SELECT id, COALESCE(NULLIF(title, ''), 'untitled') AS title,
                   COALESCE(NULLIF(model, ''), 'unknown') AS model,
                   started_at, message_count, tool_call_count, api_call_count,
                   input_tokens, output_tokens, estimated_cost_usd
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "model": r["model"],
                "started_at": r["started_at"],
                "message_count": int(r["message_count"] or 0),
                "tool_call_count": int(r["tool_call_count"] or 0),
                "api_call_count": int(r["api_call_count"] or 0),
                "input_tokens": int(r["input_tokens"] or 0),
                "output_tokens": int(r["output_tokens"] or 0),
                "estimated_cost_usd": round(float(r["estimated_cost_usd"] or 0), 4),
            }
            for r in rows
        ]
    finally:
        conn.close()


def format_ts(epoch: Optional[float]) -> str:
    if not epoch:
        return ""
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return ""


def print_usage_dashboard(db_path: Optional[str] = None, *, json_out: bool = False) -> str:
    """Render the usage dashboard; returns the rendered string."""
    summary = usage_summary(db_path)
    if not summary.get("available"):
        return f"usage: {summary.get('reason', 'no data')}"
    if json_out:
        return json_dumps(
            {
                "summary": summary,
                "by_provider": usage_by_provider(db_path),
                "by_model": usage_by_model(db_path),
                "recent": usage_recent_sessions(db_path),
            }
        )

    lines = ["Usage dashboard"]
    lines.append(f"  Sessions: {summary['session_count']}")
    lines.append(f"  Messages: {summary['message_count']}")
    lines.append(f"  Tool calls: {summary['tool_call_count']}")
    lines.append(f"  API calls: {summary['api_call_count']}")
    lines.append(f"  Tokens in: {summary['input_tokens']:,}")
    lines.append(f"  Tokens out: {summary['output_tokens']:,}")
    if summary["cache_read_tokens"] or summary["cache_write_tokens"]:
        lines.append(f"  Cache read: {summary['cache_read_tokens']:,}  cache write: {summary['cache_write_tokens']:,}")
    if summary["reasoning_tokens"]:
        lines.append(f"  Reasoning tokens: {summary['reasoning_tokens']:,}")
    lines.append(f"  Estimated cost: ${summary['estimated_cost_usd']:.4f}")
    if summary["actual_cost_usd"]:
        lines.append(f"  Actual cost: ${summary['actual_cost_usd']:.4f}")

    by_provider = usage_by_provider(db_path)
    if by_provider:
        lines.append("\nBy provider:")
        for r in by_provider:
            lines.append(
                f"  {r['provider']:<18} sessions={r['session_count']:>4}  "
                f"api_calls={r['api_call_count']:>5}  "
                f"in={r['input_tokens']:>9,}  out={r['output_tokens']:>9,}  "
                f"est=${r['estimated_cost_usd']:.4f}"
            )

    by_model = usage_by_model(db_path, limit=10)
    if by_model:
        lines.append("\nBy model (top 10):")
        for r in by_model:
            lines.append(
                f"  {r['model']:<36} sessions={r['session_count']:>3}  "
                f"est=${r['estimated_cost_usd']:.4f}"
            )

    recent = usage_recent_sessions(db_path, limit=8)
    if recent:
        lines.append("\nRecent sessions:")
        for r in recent:
            lines.append(
                f"  {format_ts(r['started_at']):<17} {r['title'][:34]:<34} "
                f"{r['model'][:24]:<24} est=${r['estimated_cost_usd']:.4f}"
            )
    return "\n".join(lines)


def json_dumps(obj: Any) -> str:
    import json

    def _default(o):
        return str(o)

    return json.dumps(obj, indent=2, default=_default)
