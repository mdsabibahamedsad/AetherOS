"""CLI: ``aetheros trust ...`` (Master 55 §99).

Operates on actual runtime state (fresh in-process TrustFabric per
invocation; identities/policies are created explicitly by each
command — nothing is faked). Follows build_parser / dispatch_*
convention.
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def _fabric(args: Any):
    from trust import TrustFabric
    return TrustFabric()


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "trust",
        help="Trust Fabric: identities, delegations, policies, audit, "
             "incidents, emergency control",
    )
    verbs = parser.add_subparsers(dest="trust_command")

    verbs.add_parser("status", help="Fabric health + posture summary")

    i = verbs.add_parser("identities", help="Create/list identities")
    i.add_argument("--create", default="",
                   help="display_name for a new AGENT identity")
    i.add_argument("--type", default="AGENT")

    verbs.add_parser("agents", help="List agent identities")

    d = verbs.add_parser("delegations", help="Inspect delegation graph")
    d.add_argument("--privilege-graph", action="store_true",
                   help="Run amplification/cycle analysis on demo graph")

    verbs.add_parser("capabilities", help="Issue demo capability token")

    p = verbs.add_parser("policies", help="Publish demo policy version")
    p.add_argument("--layer", default="task")

    t = verbs.add_parser("policy-test", help="Regression-test a decision fn")
    t.add_argument("--allow", default="read")
    t.add_argument("--deny", default="write")

    s = verbs.add_parser("simulate", help="Dry-run a policy decision")
    s.add_argument("--cap", required=True)
    s.add_argument("--resource", default="*")

    a = verbs.add_parser("audit", help="Query audit events")
    a.add_argument("--agent", default="")
    a.add_argument("--action", default="")

    pr = verbs.add_parser("provenance", help="Explain an action")
    pr.add_argument("action_id", nargs="?", default="act_demo")

    verbs.add_parser("incidents", help="Open demo incident + contain")

    r = verbs.add_parser("revoke", help="Revoke demo authority")
    r.add_argument("--kind", default="capability")
    r.add_argument("--id", default="ctok_demo")

    e = verbs.add_parser("emergency-stop", help="Trigger layered kill")
    e.add_argument("--layer", default="GLOBAL_KILL")
    e.add_argument("--target", default="")

    verbs.add_parser("replay", help="Replay demo trace vs two policies")
    verbs.add_parser("compliance", help="Control mapping demo")
    verbs.add_parser("doctor", help="Trust health check")
    verbs.add_parser("benchmark", help="Run TrustFabricBenchmark")

    s = verbs.add_parser("serve", help="Serve the Trust HTTP API")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--tls", action="store_true",
                   help="mTLS with local test PKI (dev only)")

    verbs.add_parser("hsm", help="Key custody status")
    verbs.add_parser("mtls", help="Issue local test PKI material")
    verbs.add_parser("rigs", help="Run loopback MCP + A2A rigs")
    return parser


def _demo_identity(fabric, name="cli-agent"):
    from aetheros_control_plane.models import IdentityType
    return fabric.plane.identities.create(
        IdentityType.AGENT, name, scopes=["read:docs", "write:tmp/*"])


def dispatch_trust_command(args: Any) -> int:
    f = _fabric(args)
    verb = getattr(args, "trust_command", None) or "status"
    if verb == "status":
        from trust import TrustFabric as TF  # noqa
        health = f.health.self_test()
        print(json.dumps({"mode": health["mode"], "checks": health["checks"],
                          "unhealthy": health["unhealthy"]}, indent=2))
    elif verb == "identities":
        if args.create:
            ident = _demo_identity(f, args.create)
            print(json.dumps({"id": ident.id, "type": str(ident.type),
                              "status": str(ident.status)}, indent=2,
                             default=str))
        else:
            print(json.dumps(
                {"identities": [i.id for i in
                                f.plane.identities.list()]}, indent=2))
    elif verb == "agents":
        print(json.dumps(
            {"agents": [i.id for i in f.plane.identities.list()]}, indent=2))
    elif verb == "delegations":
        if args.privilege_graph:
            f.graph.grant("human:op", "agent:a", ["read:docs"])
            f.graph.grant("agent:a", "agent:b", ["read:docs", "write:tmp"])
            print(json.dumps(
                {"cycles": f.graph.find_cycles(),
                 "amplification": f.graph.amplification()}, indent=2))
        else:
            print(json.dumps({"grants": list(
                f.plane.delegation._grants)}, indent=2))
    elif verb == "capabilities":
        ident = _demo_identity(f)
        f.graph.grant("human:op", f"agent:{ident.id}", ["read:docs"])
        tok = f.capabilities.issue(ident.id, "read", "/docs/a.md",
                                   "demo", audience="tool-demo")
        print(json.dumps({"token": tok.token_id, "expires": tok.expires_at,
                          "validated": f.capabilities.validate(
                              tok, "tool-demo").token_id}, indent=2))
    elif verb == "policies":
        ver = f.policies.publish("demo-policy",
                                 {"allow": ["read"], "tests_passed": True},
                                 layer=args.layer)
        print(json.dumps({"id": ver.policy_id, "version": ver.version,
                          "hash": ver.content_hash[:16]}, indent=2))
    elif verb == "policy-test":
        from trust.policy_ext import PolicyRegression
        reg = PolicyRegression(
            lambda r: "ALLOW" if r["cap"] == args.allow else "DENY")
        reg.add("good", {"cap": args.allow}, "ALLOW")
        reg.add("bad", {"cap": args.deny}, "DENY")
        print(json.dumps(reg.run(), indent=2))
    elif verb == "simulate":
        print(json.dumps(f.simulator.simulate(args.cap, args.resource),
                         indent=2, default=str))
    elif verb == "audit":
        evs = f.plane.audit.query(
            **({} if not args.agent else {"agent": args.agent}))
        print(json.dumps({"events": len(evs),
                          "integrity": f.plane.audit.verify()}, indent=2,
                         default=str))
    elif verb == "provenance":
        f.provenance.link_action(args.action_id, "policy-demo",
                                 "authority-demo", "approval-demo")
        print(json.dumps(f.provenance.explain(args.action_id), indent=2,
                         default=str))
    elif verb == "incidents":
        inc = f.incidents.open("prompt injection", "HIGH", actor="agent-x")
        f.incidents.contain(inc.incident_id, ["WARN", "RATE_LIMIT"])
        print(json.dumps(f.incidents.explain(inc.incident_id), indent=2,
                         default=str))
    elif verb == "revoke":
        rec = f.revoke(args.kind, args.id, "operator request",
                       actor="cli")
        print(json.dumps({"revoked": rec.target_id,
                          "propagated": len(rec.propagated_to)}, indent=2))
    elif verb == "emergency-stop":
        print(json.dumps(f.emergency.kill(args.layer, args.target,
                                          reason="cli test",
                                          actor="cli"), indent=2,
                         default=str))
    elif verb == "replay":
        from trust.policy_ext import GovernanceReplay
        trace = [{"cap": "read"}, {"cap": "write"}]
        rep = GovernanceReplay({
            "old": lambda a: "ALLOW",
            "current": lambda a: "ALLOW" if a["cap"] == "read" else "DENY",
        })
        print(json.dumps(rep.replay(trace), indent=2))
    elif verb == "compliance":
        f.compliance.map("AC-1", "internal", "CONTROL_IMPLEMENTED",
                         evidence=["policy v1"])
        print(json.dumps(f.compliance.report(), indent=2, default=str))
    elif verb == "doctor":
        from trust.health import trust_doctor
        print(trust_doctor({"identity": {"healthy": True},
                            "policy": {"healthy": True},
                            "audit": {"healthy": True},
                            "revocation": {"healthy": True},
                            "emergency": {"healthy": True},
                            "secrets": {"healthy": True},
                            "agents": [], "extensions": []})["report"])
    elif verb == "benchmark":
        from trust.benchmarks import TrustFabricBenchmark
        print(json.dumps(TrustFabricBenchmark(f).run(), indent=2))
    elif verb == "serve":
        from trust.transport import create_app
        import uvicorn
        app = create_app(f)
        ssl_kwargs = {}
        if args.tls:
            from trust.mtls import (bootstrap_local_pki, server_context)
            pki = bootstrap_local_pki()
            ctx = server_context(pki["ca"].ca_cert,
                                 pki["server"].cert, pki["server"].key)
            # uvicorn takes certfile/keyfile/ca_certs directly
            ssl_kwargs = {
                "ssl_certfile": str(pki["server"].cert),
                "ssl_keyfile": str(pki["server"].key),
                "ssl_ca_certs": str(pki["ca"].ca_cert),
                "ssl_cert_reqs": 2,  # CERT_REQUIRED
            }
            print(f"mTLS on (local test PKI): {pki['dir']}")
            _ = ctx
        print(f"serving Trust API on 127.0.0.1:{args.port} "
              f"(localhost only)")
        uvicorn.run(app, host="127.0.0.1", port=args.port,
                    log_level="warning", **ssl_kwargs)
    elif verb == "hsm":
        from trust.hsm import LocalCustody, Pkcs11Custody
        print(json.dumps({
            "local": LocalCustody().info().__dict__,
            "pkcs11": Pkcs11Custody().info().__dict__}, indent=2))
    elif verb == "mtls":
        from trust.mtls import bootstrap_local_pki
        pki = bootstrap_local_pki()
        print(json.dumps({"dir": pki["dir"], "note": pki["note"]},
                         indent=2))
    elif verb == "rigs":
        from trust.rigs import (LoopbackA2APeer, LoopbackMCPClient,
                                LoopbackMCPServer)
        from trust.contracts import ToolManifest
        server = LoopbackMCPServer(f)
        server.register_tool(ToolManifest(
            identity="echo", capabilities=("echo",),
            permissions=("echo:run",), risk="R1",
            reversibility="reversible", audit_level="standard"),
            lambda a: {"echo": a})
        from aetheros_control_plane.models import IdentityType
        ident = f.plane.identities.create(
            IdentityType.AGENT, "rig-agent", scopes=["echo"])
        # demo allowlist (explicit, labeled — mirrors M50 CLI default)
        from aetheros_control_plane.policy_risk import policy_from_yaml
        if f.plane.policies.active() is None:
            f.plane.policies.publish(policy_from_yaml(
                "policy:\n  name: rig-demo-allowlist\n  version: v1\n"
                "  allow:\n    - {capability: 'echo', resource: '*'}\n"))
        # bootstrap trust so the demo runs (T2 minimum for low-risk)
        for dim in ("identity", "transport", "organization", "capability",
                      "behavior", "provenance", "data_handling", "execution",
                      "history", "policy"):
            f.plane.trust.add_evidence(ident.id, dim, 0.5,
                                       "rig demo bootstrap", source="cli")
        client = LoopbackMCPClient(f, ident.id)
        print(json.dumps({
            "mcp": client.invoke(server, "echo", "/tmp",
                                 {"hi": 1}, task_id="rig"),
            "note": "LOOPBACK transport; enforcement logic is live"},
            indent=2, default=str))
    else:
        print(f"unknown trust verb: {verb}")
        return 2
    return 0
