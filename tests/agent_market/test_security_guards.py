"""Unit: security guards, flags/kill/safe-mode, export/import, simulation."""

import json

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.export_import import (
    check_restore_integrity, export_bundle, import_bundle,
)
from aetheros_agent_market.flags import (
    DEFAULTS, FeatureFlags, KillSwitch, safe_mode_active,
)
from aetheros_agent_market.security import (
    EconomicAbuseGuard, ListingScanner, RecursionGuard,
)
from aetheros_agent_market.simulation import (
    SIMULATION_MARK, MarketSimulator, simulation_home,
)


def test_safe_defaults(home):
    flags = FeatureFlags(home)
    assert flags.is_enabled("marketplace") is True
    for name in ("remote_delegation", "paid_agents", "automatic_negotiation",
                 "automatic_payment", "external_registries",
                 "organization_marketplace"):
        assert flags.is_enabled(name) is False, name
    with pytest.raises(PermissionError):
        flags.require("paid_agents")
    with pytest.raises(ValueError):
        flags.is_enabled("nope")


def test_flag_changes_audited(home):
    flags = FeatureFlags(home)
    flags.set("remote_delegation", True, by="tester")
    assert flags.is_enabled("remote_delegation") is True
    log = flags.audit_log()
    assert log and log[-1]["flag"] == "remote_delegation"


def test_kill_switch_payments(home):
    flags = FeatureFlags(home)
    flags.set("paid_agents", True, by="t")
    flags.set("automatic_payment", True, by="t")
    kill = KillSwitch(home, flags)
    rec = kill.engage("payments", by="ops", reason="fraud wave")
    assert rec["engaged"] is True
    assert flags.is_enabled("paid_agents") is False
    assert flags.is_enabled("automatic_payment") is False
    assert kill.log()
    with pytest.raises(ValueError):
        kill.engage("everything")


def test_stop_all(home):
    flags = FeatureFlags(home)
    kill = KillSwitch(home, flags)
    kill.stop_all_marketplace_activity(by="ops")
    for name in ("remote_delegation", "paid_agents", "automatic_negotiation",
                 "automatic_payment"):
        assert flags.is_enabled(name) is False
    assert safe_mode_active(flags) is True


def test_listing_scan_levels(home):
    scanner = ListingScanner(home)
    # No card, no endpoint => partial, honest about coverage.
    r = scanner.scan({"service_id": "s1", "name": "X"})
    assert r["level"] == "partially_scanned"
    assert any("redirect" in n for n in r["not_covered"])
    # Risky scope flagged high.
    r2 = scanner.scan({"service_id": "s2", "name": "Y",
                       "security_requirements": ["unrestricted filesystem"]},
                      agent_card={"url": "https://agent.example.com/"})
    assert r2["high_count"] >= 1
    assert scanner.get("s2")["service_id"] == "s2"


def test_recursion_guard_ceilings(home):
    guard = RecursionGuard(home, max_depth=2, max_agents=2)
    assert guard.check("root", "a1", 1)["allowed"] is True
    assert guard.check("root", "a2", 2)["allowed"] is True
    over = guard.check("root", "a3", 3)
    assert over["allowed"] is False and "depth" in over["reason"]
    loop = guard.check("root", "a1", 2)
    assert loop["allowed"] is False and "chain" in loop["reason"]


def test_quote_flooding_blocked(home):
    guard = EconomicAbuseGuard(home)
    ok = True
    for _ in range(25):
        ok = guard.check_quote_rate("spam-agent", max_per_minute=20)["allowed"]
    assert ok is False


def test_spend_velocity_blocked(home):
    guard = EconomicAbuseGuard(home)
    assert guard.check_spend_velocity("u1", 60000)["allowed"] is True
    res = guard.check_spend_velocity("u1", 60000)
    assert res["allowed"] is False and "velocity" in res["reason"]


def test_export_import_roundtrip(home):
    from aetheros_agent_market.preferences import AgentPreferences, PreferenceStore
    from aetheros_agent_market.budgets import BudgetManager
    PreferenceStore(home).put(AgentPreferences(min_trust_rank=5))
    BudgetManager(home).set_budget(S.Budget(
        budget_id="b", scope="user", spent_minor=999,
        auto_approve_limit_minor=5000))
    bundle = export_bundle(home)
    assert bundle["export_version"] == "1"
    # Import into a fresh home: spend reset, auto-approve zeroed.
    dest = home / "restored"
    dest.mkdir()
    result = import_bundle(dest, bundle, by="test")
    assert result["applied"]["budgets"] == 1
    b = BudgetManager(dest).get_budget("user")
    assert b.spent_minor == 0 and b.auto_approve_limit_minor == 0
    assert PreferenceStore(dest).get().min_trust_rank == 5


def test_import_rejects_bad_bundle(home):
    with pytest.raises(ValueError):
        import_bundle(home, {"export_version": "99", "records": {}})


def test_restore_integrity_ok_and_tampered(home):
    from aetheros_agent_market.ledger import Ledger
    ledger = Ledger(home / "ledger.jsonl")
    ledger.append("QUOTE_CREATED", agent_id="a", idempotency_key="k1")
    assert check_restore_integrity(home)["safe_mode"] is False
    lines = (home / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("QUOTE_CREATED", "MINTED")
    (home / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = check_restore_integrity(home)
    assert result["safe_mode"] is True


def test_simulation_isolated_and_marked(tmp_path):
    sim = MarketSimulator()
    agents = sim.fixture_agents(3)
    assert len(agents) == 3
    assert all(a["simulation"] is True for a in agents)
    assert all(SIMULATION_MARK in a["agent_id"] for a in agents)
    assert (simulation_home() / "SIMULATION_MARKER").exists()
    # Production home refused.
    from aetheros_agent_market.store import market_home
    with pytest.raises(PermissionError):
        MarketSimulator(home=market_home())
    # Simulator exposes no production ledger.
    assert sim.ledger()[0]["simulation"] is True
