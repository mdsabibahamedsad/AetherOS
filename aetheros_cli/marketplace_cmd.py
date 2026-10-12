"""`aetheros agent-marketplace ...` — Agent Marketplace + Economy CLI (spec 57).

Named `agent-marketplace` (not `marketplace`: that name belongs to the
pre-existing Extension Marketplace). Every command operates on real
backend state (MarketplaceFlow). No fake listings, prices, reputation,
transactions, or availability. Simulation is available ONLY via
explicit `simulation` verbs and is always marked.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _flow():
    from aetheros_agent_market.flow import MarketplaceFlow
    return MarketplaceFlow()


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def build_parser(subparsers) -> Any:
    p = subparsers.add_parser("agent-marketplace",
                              aliases=["agent-market"],
                              help="Agent Marketplace: discover, evaluate, delegate, settle")
    sub = p.add_subparsers(dest="market_verb", required=True)

    s = sub.add_parser("search", help="Search services by need/capability (real index)")
    s.add_argument("query", help="What do you need? e.g. 'analyze financial spreadsheets'")
    s.add_argument("--capability", action="append", default=[], dest="capabilities",
                   help="Exact taxonomy capability (repeatable)")
    s.add_argument("--max-price", type=int, default=None, dest="max_price",
                   help="Max price in minor units (cents)")
    s.add_argument("--data-class", default="INTERNAL", dest="data_class",
                   help="Required data ceiling (PUBLIC|INTERNAL|CONFIDENTIAL|PRIVATE|HIGHLY_SENSITIVE)")
    s.add_argument("--limit", type=int, default=10)

    sub.add_parser("agents", help="List marketplace agents (real registry)").add_argument(
        "--org", default="", help="Filter by organization id")

    sv = sub.add_parser("services", help="List published services (real registry)")
    sv.add_argument("--agent", default="", help="Filter by agent id")

    i = sub.add_parser("inspect", help="Inspect an agent or service with provenance")
    i.add_argument("kind", choices=["agent", "service"])
    i.add_argument("id", help="Identity id or service id")

    c = sub.add_parser("compare", help="Compare 2-3 agents transparently")
    c.add_argument("ids", nargs="+", help="Agent ids (2-3)")
    c.add_argument("--query", default="", help="Task context for comparison")

    q = sub.add_parser("quote", help="Record + verify a provider quote")
    q.add_argument("--quote-file", required=True, help="Path to quote JSON")

    d = sub.add_parser("delegate", help="Run the full gated delegation pipeline")
    d.add_argument("--task-file", required=True, help="Path to task JSON")
    d.add_argument("--select-file", required=True, help="Path to selection JSON {service_id, agent_id, ...}")
    d.add_argument("--approve-as", default="", help="Approver identity (required for paid/human tier)")
    d.add_argument("--auto", action="store_true",
                   help="Autonomous purchase within user auto-purchase policy only")

    ct = sub.add_parser("contracts", help="List contracts (real state)")
    ct.add_argument("--status", default="")

    t = sub.add_parser("transactions", help="Show ledger entries + accounting")
    t.add_argument("--contract", default="")

    r = sub.add_parser("reputation", help="Show multidimensional reputation (real data)")
    r.add_argument("agent_id", help="Agent id")

    tr = sub.add_parser("trust", help="Show multidimensional trust profile")
    tr.add_argument("agent_id", help="Agent id")

    b = sub.add_parser("budget", help="Show budget usage for a scope")
    b.add_argument("--scope", default="user")
    b.add_argument("--scope-id", default="")

    dp = sub.add_parser("disputes", help="List disputes / open a dispute")
    dp.add_argument("--open-file", default="", help="Path to dispute JSON to open")
    dp.add_argument("--status", default="")

    pol = sub.add_parser("policy", help="Show effective marketplace policy")
    pol.add_argument("--set-file", default="", help="Path to preferences JSON to store (global)")

    sim = sub.add_parser("simulation", help="Dev-only SIMULATION fixtures (never production)")
    sim.add_argument("what", choices=["agents"], help="Fixture set")
    sim.add_argument("--n", type=int, default=5)

    adm = sub.add_parser("admin", help="Operator controls (audited)")
    adm.add_argument("action", choices=["stop-all", "kill", "flags"],
                     help="stop-all | kill <target> | flags")
    adm.add_argument("target", nargs="?", default="")
    return p


def dispatch_marketplace_command(args) -> int:
    flow = _flow()
    verb = args.market_verb

    if verb == "search":
        from aetheros_agent_market.taxonomy import MatchRequest
        from aetheros_agent_market.preferences import apply_preferences
        prefs = flow.preferences.effective()
        req = MatchRequest(query=args.query, exact_capabilities=args.capabilities,
                           data_class=args.data_class.upper(),
                           max_price_minor=args.max_price)
        req = apply_preferences(req, prefs)
        hits = flow.index.search(req, limit=args.limit)
        if not hits:
            print("(no matching services — constraints eliminated all candidates)")
            return 0
        for h in hits:
            print(f"{h.service.get('service_id')}  agent={h.agent_id}  "
                  f"src={h.source}  exact={h.exact}  score_kw={h.keyword_score:.2f}")
            for reason in h.reasons:
                print(f"    - {reason}")
        return 0

    if verb == "agents":
        agents = flow.registry.discover_agents(
            {"organization_id": args.org} if args.org else {})
        if not agents:
            print("(no agents registered)")
            return 0
        for a in agents:
            print(f"{a.get('identity_id')}  agent={a.get('agent_id')}  "
                  f"org={a.get('organization_id')}  verification={a.get('verification_status')}")
        return 0

    if verb == "services":
        services = flow.registry.discover_services(
            {"status": "published", **({"agent_id": args.agent} if args.agent else {})})
        if not services:
            print("(no published services)")
            return 0
        for s in services:
            print(f"{s.get('service_id')}  agent={s.get('agent_id')}  "
                  f"{s.get('name')}  pricing={s.get('pricing_model')}")
        return 0

    if verb == "inspect":
        from aetheros_agent_market.api import MarketplaceAPI
        api = MarketplaceAPI(flow)
        if args.kind == "agent":
            _print(api.get_agent(args.id))
        else:
            _print(api.get_service(args.id))
        return 0

    if verb == "compare":
        if not (2 <= len(args.ids) <= 3):
            raise SystemExit("compare requires 2-3 agent ids")
        from aetheros_agent_market.ipc import compare
        _print(compare({"agent_ids": args.ids, "query": args.query}))
        return 0

    if verb == "quote":
        with open(args.quote_file, encoding="utf-8") as f:
            body = json.load(f)
        from aetheros_agent_market import schemas as S
        quote = S.Quote.from_dict(body)
        check = flow.quotes.verify_quote(quote)
        recorded = flow.quotes.record_quote(quote)
        _print({"quote": recorded.to_dict(), "verification": check})
        return 0 if check["ok"] else 2

    if verb == "delegate":
        with open(args.task_file, encoding="utf-8") as f:
            task = json.load(f)
        with open(args.select_file, encoding="utf-8") as f:
            selection = json.load(f)
        try:
            result = flow.delegate(task, selection, approved_by=args.approve_as,
                                   auto=args.auto)
        except Exception as e:
            print(f"delegation refused/failed: {e}", file=sys.stderr)
            return 1
        _print(result)
        return 0

    if verb == "contracts":
        for c in flow.contracts.list(status=args.status):
            print(f"{c.contract_id} v{c.version}  {c.status}  "
                  f"agent={c.provider_agent_id}  price={c.price_minor}{c.currency}")
        return 0

    if verb == "transactions":
        from aetheros_agent_market.api import MarketplaceAPI
        _print(MarketplaceAPI(flow).get_transactions(args.contract))
        return 0

    if verb == "reputation":
        from aetheros_agent_market.api import MarketplaceAPI
        rep = MarketplaceAPI(flow).get_reputation(args.agent_id)
        metrics = rep["reputation"]["metrics"]
        for name, m in metrics.items():
            if m["sample_count"]:
                print(f"{name:22s} {m['value']:.2f}  conf={m['confidence']:.2f}  "
                      f"n={m['sample_count']}  via={m['provenance']}")
            else:
                print(f"{name:22s} insufficient evidence")
        flags = rep["reputation"]["flags"]
        if flags:
            print("flags: " + ", ".join(flags))
        return 0

    if verb == "trust":
        from aetheros_agent_market.api import MarketplaceAPI
        _print(MarketplaceAPI(flow).get_trust(args.agent_id))
        return 0

    if verb == "budget":
        _print(flow.budgets.usage(args.scope, args.scope_id))
        return 0

    if verb == "disputes":
        if args.open_file:
            with open(args.open_file, encoding="utf-8") as f:
                body = json.load(f)
            from aetheros_agent_market.ipc import dispute_create
            _print(dispute_create({"dispute": body}))
            return 0
        for d in flow.disputes.list(status=args.status):
            print(f"{d.dispute_id}  {d.status}  {d.reason}  agent={d.agent_id}")
        return 0

    if verb == "policy":
        if args.set_file:
            with open(args.set_file, encoding="utf-8") as f:
                body = json.load(f)
            from aetheros_agent_market.ipc import policy_update
            _print(policy_update({"preferences": body}))
            return 0
        from aetheros_agent_market.ipc import policy_get
        _print(policy_get({}))
        return 0

    if verb == "simulation":
        from aetheros_agent_market.simulation import MarketSimulator, SIMULATION_MARK
        sim = MarketSimulator()
        print(f"[{SIMULATION_MARK}] fixtures below are NOT production data")
        for a in sim.fixture_agents(args.n):
            print(f"{a['agent_id']}  {a['display_name']}  "
                  f"price={a['price_minor']}  reliability~{a['reliability']}")
        return 0

    if verb == "admin":
        if args.action == "flags":
            from aetheros_agent_market.ipc import policy_get
            _print(policy_get({})["flags"])
            return 0
        if args.action == "stop-all":
            rec = flow.kill.stop_all_marketplace_activity(by="cli")
            print(f"STOP ALL engaged: {rec}")
            return 0
        if args.action == "kill":
            rec = flow.kill.engage(args.target, by="cli")
            print(f"kill engaged: {rec}")
            return 0

    raise SystemExit(f"unknown marketplace verb: {verb}")
