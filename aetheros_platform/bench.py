"""Performance benchmarks — measured, never invented (§66, §103).

`python -m aetheros_platform.bench` prints a JSON + markdown table with
p50/p95 over live in-process + loopback-HTTP measurements. Requires the
test-only echo tool pattern; gateway tests run over real HTTP.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time


def _pct(samples, p):
    if not samples:
        return 0.0
    s = sorted(samples)
    k = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return s[k]


def bench_sdk_import():
    t0 = time.perf_counter()
    subprocess.run([sys.executable, "-c", "import aetheros_sdk"],
                   capture_output=True, check=True)
    return (time.perf_counter() - t0) * 1000.0


def bench_cli_startup():
    t0 = time.perf_counter()
    subprocess.run([sys.executable, "-m", "aetheros_platform.cli", "schema",
                    "--name", "Agent"], capture_output=True, check=True)
    return (time.perf_counter() - t0) * 1000.0


def bench_schema_validation(n=2000):
    from aetheros_platform.schemas import validate
    payload = {"name": "bench", "version": "1.0.0",
               "capabilities": ["artifact.create"]}
    t0 = time.perf_counter()
    for _ in range(n):
        assert validate("Agent", payload) == []
    return (time.perf_counter() - t0) / n * 1000.0


def bench_tool_invoke(n=200):
    from aetheros_platform.tools import ToolRegistry
    tools = ToolRegistry()
    tools.register({"name": "echo", "version": "1.0.0",
                    "inputSchema": {"type": "object"},
                    "outputSchema": {"type": "object"},
                    "capabilities": ["artifact.create"], "riskLevel": "LOW",
                    "sideEffects": [], "idempotent": True,
                    "timeoutSeconds": 10}, lambda a: {"echo": a.get("t")})
    samples = []
    for i in range(n):
        t0 = time.perf_counter()
        # Distinct actor per call: rate limits are per-identity by design,
        # and the benchmark measures the invoke path, not the limiter.
        tools.invoke("echo", {"t": i}, actor=f"bench-{i}",
                     grants=["artifact.create"])
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def bench_package_build(tmp_dir="/tmp"):
    import tempfile
    from pathlib import Path
    from aetheros_platform import packages as _p
    with tempfile.TemporaryDirectory(prefix="bench-pkg-") as d:
        proj = Path(d) / "p"
        proj.mkdir()
        (proj / "manifest.json").write_text(
            '{"name": "bench", "version": "1.0.0", "kind": "tool", '
            '"aetherosVersion": ">=1.0.0"}')
        (proj / "tool.py").write_text("x = 1\n")
        t0 = time.perf_counter()
        _p.build_package(proj)
        return (time.perf_counter() - t0) * 1000.0


def bench_http(n_get=50, n_task=8, concurrency=4):
    """Loopback HTTP: health GET p50/p95, task-create p50, concurrent tasks.

    Sized under the enforced rate-limit bursts (tool-invoke burst=10) so the
    benchmark measures latency, not the limiter (which is proven separately
    by test_rate_limit_enforced)."""
    import os
    import tempfile
    os.environ["AETHEROS_HOME"] = tempfile.mkdtemp(prefix="bench-http-")
    import socket
    import threading
    import httpx
    import uvicorn
    from aetheros_platform.agents import AgentRegistry
    from aetheros_platform.auth import APIKeyManager
    from aetheros_platform.events import WebhookRegistry
    from aetheros_platform.gateway import create_app
    from aetheros_platform.skills import SkillRegistry
    from aetheros_platform.tools import ToolRegistry

    key = APIKeyManager().create(
        "bench", ["agents:read", "agents:write", "tasks:read", "tasks:write",
                  "tools:read", "tools:invoke"], owner="bench")["api_key"]
    tools = ToolRegistry()
    tools.register({"name": "echo", "version": "1.0.0",
                    "inputSchema": {"type": "object"},
                    "outputSchema": {"type": "object"},
                    "capabilities": ["artifact.create"], "riskLevel": "LOW",
                    "sideEffects": [], "idempotent": True,
                    "timeoutSeconds": 10}, lambda a: {"echo": a.get("t")})
    app = create_app(agents=AgentRegistry(), tools=tools,
                     skills=SkillRegistry(tools=tools),
                     webhooks=WebhookRegistry())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                           log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            if httpx.get(base + "/api/v1/health", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.05)
    out = {}
    try:
        h = {"X-API-Key": key}
        with httpx.Client(base_url=base, timeout=30) as c:
            gets = []
            for _ in range(n_get):
                t0 = time.perf_counter()
                assert c.get("/api/v1/health").status_code == 200
                gets.append((time.perf_counter() - t0) * 1000.0)
            out["http_health_ms_p50"] = round(_pct(gets, 50), 2)
            out["http_health_ms_p95"] = round(_pct(gets, 95), 2)
            agent = c.post("/api/v1/agents", headers=h,
                           json={"name": "bench-agent", "version": "1.0.0",
                                 "capabilities": ["artifact.create"]}).json()
            tasks = []
            for i in range(n_task):
                t0 = time.perf_counter()
                r = c.post("/api/v1/tasks", headers=h,
                           json={"agent": agent["agentId"],
                                 "input": {"capability": "artifact.create",
                                           "tool": "echo", "args": {"t": i}}})
                assert r.status_code == 200, r.text[:200]
                tasks.append((time.perf_counter() - t0) * 1000.0)
            out["http_task_create_ms_p50"] = round(_pct(tasks, 50), 2)
            out["http_task_create_ms_p95"] = round(_pct(tasks, 95), 2)
            # Concurrent tasks across threads (distinct agents to avoid
            # lifecycle contention on one agent record).
            import concurrent.futures as _cf
            aids = [c.post("/api/v1/agents", headers=h,
                           json={"name": f"bench-c-{i}", "version": "1.0.0",
                                 "capabilities": ["artifact.create"]}).json()["agentId"]
                    for i in range(concurrency)]

            def one(aid):
                with httpx.Client(base_url=base, timeout=30) as cc:
                    r = cc.post("/api/v1/tasks", headers=h,
                                json={"agent": aid,
                                      "input": {"capability": "artifact.create"}})
                    return r.status_code

            t0 = time.perf_counter()
            with _cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
                codes = list(pool.map(one, aids))
            out["concurrent_tasks"] = concurrency
            out["concurrent_tasks_ok"] = sum(1 for x in codes if x == 200)
            out["concurrent_tasks_wall_ms"] = round(
                (time.perf_counter() - t0) * 1000.0, 1)
    finally:
        server.should_exit = True
        th.join(timeout=15)
    return out


def main() -> int:
    import json
    import os
    rows = {}
    rows["sdk_import_ms"] = round(bench_sdk_import(), 1)
    rows["cli_startup_ms"] = round(bench_cli_startup(), 1)
    rows["schema_validate_ms_per_op"] = round(bench_schema_validation(), 4)
    tool = bench_tool_invoke()
    rows["tool_invoke_ms_p50"] = round(_pct(tool, 50), 3)
    rows["tool_invoke_ms_p95"] = round(_pct(tool, 95), 3)
    try:
        rows["package_build_ms"] = round(bench_package_build(), 1)
    except Exception as exc:
        rows["package_build_ms"] = f"BLOCKED: {exc}"[:120]
    try:
        rows.update(bench_http())
    except Exception as exc:
        rows["http_bench"] = f"BLOCKED: {exc}"[:200]
    rows["env"] = {"python": sys.version.split()[0],
                   "platform": os.name,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(json.dumps(rows, indent=2))
    print()
    print("| metric | value |")
    print("| --- | --- |")
    for k, v in rows.items():
        if k != "env":
            print(f"| {k} | {v} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
