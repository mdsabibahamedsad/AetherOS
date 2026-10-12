"""WS-E mounting contracts: control-plane security CLI + web API routes."""

import argparse

from aetheros_cli.security_integration import (
    register_security_api_routes,
    register_security_subcommands,
)

EXPECTED_COMMANDS = {"permissions", "secrets", "audit", "sandbox", "verify", "scan"}


def test_register_security_subcommands_attaches_six_commands():
    parser = argparse.ArgumentParser(prog="aetheros-test")
    subparsers = parser.add_subparsers(dest="top_command")
    register_security_subcommands(subparsers)

    registered = set(subparsers.choices)
    assert EXPECTED_COMMANDS <= registered

    # Each command follows the repo dispatch contract: set_defaults(func=...)
    for name in EXPECTED_COMMANDS:
        sub = subparsers.choices[name]
        ns, _ = sub.parse_known_args([])
        assert callable(getattr(ns, "func", None)), f"{name} missing func default"


class _FakeApp:
    def __init__(self):
        self.routes = []

    def get(self, path, **kw):
        def deco(fn):
            self.routes.append(("GET", path))
            return fn

        return deco

    post = get
    delete = get


def test_register_security_api_routes_mounts_prefix():
    app = _FakeApp()
    register_security_api_routes(app)
    paths = {p for _, p in app.routes}
    assert any(p.startswith("/api/security/") for p in paths)


def test_web_server_app_includes_security_routes():
    """The real dashboard backend mounts /api/security/* before the SPA."""
    from aetheros_cli import web_server as ws  # heavy but established pattern

    route_paths = set()
    for r in getattr(ws.app, "routes", []):
        path = getattr(r, "path", None)
        if path:
            route_paths.add(path)
    security_routes = [p for p in route_paths if p.startswith("/api/security/")]
    assert security_routes, "web_server must mount /api/security/* routes"
    assert "/api/security/status" in security_routes
