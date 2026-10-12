"""CLI (§84): governance/identity/trust/policy/permissions/delegation/
approvals/audit/provenance/security/quarantine/emergency-stop.

Operates against real backend state (in-process control plane with
optional JSON persistence for identities/policies). Usage:

    python -m aetheros_control_plane.cli policy check --cap filesystem.read ...
    python -m aetheros_control_plane.cli health
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .control_plane import UniversalControlPlane
from .models import ActionManifest, IdentityType, TrustLevel
from .policy_risk import policy_from_yaml

_STATE = Path.home() / ".aetheros" / "control-plane.json"


def _plane(persist: bool = True) -> UniversalControlPlane:
    cp = UniversalControlPlane()
    if persist and _STATE.exists():
        try:
            doc = json.loads(_STATE.read_text("utf-8"))
            pol = doc.get("policy_yaml")
            if pol:
                cp.policies.publish(policy_from_yaml(pol))
        except Exception:
            pass
    if cp.policies.active() is None:
        cp.policies.publish(policy_from_yaml(
            "policy:\n  name: default-allowlist\n  version: v1\n"
            "  allow:\n    - {capability: '*.read', resource: '*'}\n"))
    return cp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aetheros-control-plane")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("policy")
    p.add_argument("verb", choices=["check", "simulate", "publish", "history"])
    p.add_argument("--cap", default="*.read")
    p.add_argument("--resource", default="*")
    p.add_argument("--tenant", default="default")
    p.add_argument("--file")

    h = sub.add_parser("health")
    t = sub.add_parser("trust")
    t.add_argument("verb", choices=["assess"])
    t.add_argument("--identity", required=True)
    e = sub.add_parser("emergency-stop")
    e.add_argument("--scope", default="global")
    e.add_argument("--target", default="")
    e.add_argument("--reason", default="manual")
    e.add_argument("--resume", action="store_true")
    q = sub.add_parser("quarantine")
    q.add_argument("verb", choices=["hold", "release", "list"])
    q.add_argument("--identity", default="")
    q.add_argument("--reason", default="")
    a = sub.add_parser("audit")
    a.add_argument("verb", choices=["verify", "count"])
    w = sub.add_parser("permissions")
    w.add_argument("--identity", required=True)
    w.add_argument("--probe", nargs="+",
                   default=["filesystem.read", "terminal.execute"])

    args = ap.parse_args(argv)
    cp = _plane()

    if args.cmd == "policy":
        if args.verb == "publish" and args.file:
            cp.policies.publish(policy_from_yaml(
                Path(args.file).read_text("utf-8")))
            print(json.dumps({"active": cp.policies.active().version}))
        elif args.verb == "history":
            print(json.dumps({"history": cp.policies.history()}))
        else:
            ident = cp.identities.create(IdentityType.AGENT, "cli-probe")
            m = ActionManifest(identity_id=ident.id,
                               capabilities=[args.cap],
                               scopes=[args.cap],
                               resources=[args.resource])
            ident.tenant = args.tenant
            print(json.dumps(cp.why(m), indent=2))
    elif args.cmd == "health":
        print(json.dumps(cp.health(), indent=2))
    elif args.cmd == "trust":
        print(json.dumps(cp.trust.assess(args.identity).__dict__,
                         indent=2, default=str))
    elif args.cmd == "emergency-stop":
        from .emergency import StopScope
        scope = StopScope(args.scope)
        if args.resume:
            print(json.dumps(
                {"resumed": cp.emergency.resume(scope, args.target)}))
        else:
            st = cp.emergency.stop(scope, args.target, args.reason, "cli")
            print(json.dumps({"stopped": st.scope.value, "at": st.at}))
    elif args.cmd == "quarantine":
        if args.verb == "hold":
            cp.quarantine.hold(args.identity, args.reason or "manual")
            print(json.dumps({"held": args.identity}))
        elif args.verb == "release":
            print(json.dumps({"released": cp.quarantine.release(
                args.identity)}))
        else:
            print(json.dumps({"held": cp.quarantine.list()}, indent=2,
                             default=str))
    elif args.cmd == "audit":
        if args.verb == "verify":
            ok, msg = cp.audit.verify()
            print(json.dumps({"ok": ok, "message": msg}))
        else:
            print(json.dumps({"events": len(cp.audit)}))
    elif args.cmd == "permissions":
        print(json.dumps(cp.what_can_do(args.identity, args.probe),
                         indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
