"""TypeScript type generator — single source of truth (Master 62 §47).

`schema -> validation -> type generation -> SDK -> contract tests`.
Run: `python -m aetheros_platform.tsgen > sdks/typescript/src/generated.ts`.
"""

from __future__ import annotations

from aetheros_platform.schemas import SCHEMAS, SCHEMA_VERSION

_HEADER = """// GENERATED from aetheros_platform/schemas.py — do not hand-edit.
// Schema version: %s

export type AgentState = %s;
export type TaskState = %s;
export type RiskLevel = %s;
export type Stability = %s;
""" % (SCHEMA_VERSION,
       " | ".join(f'"{s}"' for s in
                  ("REGISTERED", "CREATED", "READY", "RUNNING", "WAITING",
                   "PAUSED", "COMPLETED", "FAILED", "CANCELLED",
                   "QUARANTINED", "TERMINATED")),
       " | ".join(f'"{s}"' for s in
                  ("PENDING", "RUNNING", "WAITING_APPROVAL", "PAUSED",
                   "COMPLETED", "FAILED", "CANCELLED")),
       '"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"',
       '"PUBLIC" | "INTERNAL" | "EXPERIMENTAL" | "DEPRECATED" | "PRIVATE" | "UNSTABLE"')

_TS_TYPES = {
    "string": "string", "integer": "number", "number": "number",
    "boolean": "boolean", "object": "Record<string, unknown>",
    "array": "unknown[]",
}


def _ts(schema: dict, name: str = "") -> str:
    t = schema.get("type", "unknown")
    if t == "object":
        props = schema.get("properties", {})
        if not props:
            return "Record<string, unknown>"
        req = set(schema.get("required", []))
        lines = ["{"]
        for k, v in props.items():
            opt = "" if k in req else "?"
            lines.append(f"  {k}{opt}: {_ts(v, k)};")
        lines.append("}")
        return "\n".join(lines)
    if t == "array":
        return f"{_ts(schema.get('items', {}), name)}[]"
    if "enum" in schema:
        return " | ".join(f'"{v}"' for v in schema["enum"])
    return _TS_TYPES.get(t, "unknown")


def generate() -> str:
    parts = [_HEADER]
    first = ("Agent", "AgentTask", "AgentResult", "Tool", "Skill",
             "AgentCard", "MCPServer", "Automation", "MemoryRecord",
             "Artifact", "APIKey", "Webhook", "Package")
    rest = sorted(n for n in SCHEMAS if n not in first)
    for name in (*first, *rest):
        parts.append(f"export interface {name} {_ts(SCHEMAS[name])}")
    parts.append("""
export interface AetherError {
  code: string; message: string; category: string; retryable: boolean;
  severity: string; requestId: string; traceId: string; taskId: string;
  capability: string; policyDecision: string; remediation: string;
  metadata: Record<string, unknown>;
}
export interface Page<T> { items: T[]; nextCursor: string; limit: number }
""")
    return "\n\n".join(parts) + "\n"


if __name__ == "__main__":
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument("--out", default=None)
    _a = _p.parse_args()
    text = generate()
    if _a.out:
        from pathlib import Path as _Path
        _Path(_a.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
