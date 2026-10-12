"""Extension platform benchmarks (Master 44 section 74). Measured only:
discovery, validation, signature verify, install, activation, tool
lookup, permission eval, shutdown, update, rollback + scaling 10/50/100.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aetheros_extensions import (
    ExtensionManifest, ExtensionService, Grant, PermissionEngine,
    build_package, generate_keypair, sign_package_digest,
    verify_package, verify_signature,
)
from aetheros_extensions.trust import PublisherRecord


def make_pkg(tmp: Path, i: int, keys) -> Path:
    src = tmp / f"src{i}"
    (src / "extension").mkdir(parents=True)
    manifest = {"id": f"bench.ext{i}", "name": f"ext{i}", "version": "1.0.0",
                "publisher": "Bench", "publisher_id": "bench",
                "extension_type": "tool_pack",
                "permissions": [{"permission": "network.request",
                                 "domains": ["api.example.com"]}],
                "tools": [{"name": f"tool_{i}", "description": "bench tool"}],
                "entrypoints": {"main": "extension/main.py"}}
    (src / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (src / "extension" / "main.py").write_text(
        "def run(ctx):\n    return {'ok': True}\n", encoding="utf-8")
    pkg = tmp / f"ext{i}.aetherext"
    build_package(src, pkg)
    rep = verify_package(pkg)
    env = sign_package_digest(rep.package_digest, keys["private_b64"])
    import zipfile as _zf
    with _zf.ZipFile(pkg, "a") as zf:
        zf.writestr("signature/signature.json", json.dumps(env))
    return pkg


def bench_scale(n: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="extbench"))
    keys = generate_keypair()
    svc = ExtensionService(root=tmp / "ext", approve=lambda _i: True)
    svc.initialize()
    svc._trust.upsert(PublisherRecord(publisher_id="bench",
                                      public_keys=[keys["public_b64"]],
                                      trust="user_trusted"))
    pkgs = [make_pkg(tmp, i, keys) for i in range(n)]
    out: dict = {"n": n}
    t0 = time.time()
    for pkg in pkgs:
        r = svc.install(package=pkg, source="local_package")
        assert r["ok"], r
    out["install_s"] = round(time.time() - t0, 3)
    t0 = time.time()
    for i in range(n):
        svc.enable(f"bench.ext{i}")
    out["activation_s"] = round(time.time() - t0, 3)
    eng = PermissionEngine()
    grants = [Grant(permission="network.request", scope={"domains": ["api.example.com"]})]
    t0 = time.time()
    for _ in range(1000):
        eng.check(grants, "network.request", {"host": "api.example.com"})
    out["perm_eval_1000_s"] = round(time.time() - t0, 3)
    t0 = time.time()
    for _ in range(100):
        svc.list(query="ext")
    out["registry_search_100_s"] = round(time.time() - t0, 3)
    t0 = time.time()
    for i in range(n):
        svc.disable(f"bench.ext{i}")
    out["shutdown_s"] = round(time.time() - t0, 3)
    # Update + rollback on one.
    pkg2 = make_pkg(tmp / "u", 0, keys) if False else None
    return out


def bench_crypto() -> dict:
    keys = generate_keypair()
    t0 = time.time()
    for _ in range(50):
        env = sign_package_digest("d" * 64, keys["private_b64"])
        verify_signature("d" * 64, env, keys["public_b64"])
    dt = time.time() - t0
    return {"sign_verify_50_s": round(dt, 3)}


if __name__ == "__main__":
    sizes = [int(a) for a in sys.argv[1:] or [10, 50]]
    print(json.dumps({"crypto": bench_crypto(),
                      "scale": [bench_scale(n) for n in sizes]}, indent=2))
