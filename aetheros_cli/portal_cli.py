"""``aetheros portal`` — the human-readable entry point for AetherOS.

Running ``aetheros portal`` with no subcommand performs the one-shot AetherOS
onboarding: OAuth login, pick an AetherOS model, switch the inference provider
to AetherOS, and offer to enable the Tool Gateway. It is the friendly alias
for ``aetheros auth add aetheros --type oauth`` (which still works), is
identical to ``aetheros setup --portal``, and runs the same AetherOS flow as
the first-time quick setup.

Subcommands:
  (none)   Log in to AetherOS + set it up (one-shot onboarding).
  login    Explicit alias for the default one-shot onboarding.
  info     Show AetherOS auth state + which Tool Gateway tools are routed.
  open     Open the AetherOS subscription page in the user's default browser.
  tools    List Tool Gateway tools and which are active in the current config.

This command is intentionally minimal — it does not duplicate functionality
already in ``aetheros auth`` or ``aetheros tools``. It's the onboarding +
discovery surface for the AetherOS subscription itself.
"""
from __future__ import annotations

import sys
import webbrowser

from aetheros_cli.colors import Colors, color
from aetheros_cli.config import load_config

DEFAULT_PORTAL_URL = "https://portal.aetheros.com"
SUBSCRIPTION_URL = "https://portal.aetheros.com/manage-subscription"
DOCS_URL = "https://aetheros.aetheros.com/docs/user-guide/features/tool-gateway"


def _cmd_status(args) -> int:
    """Show AetherOS auth + Tool Gateway routing summary."""
    from aetheros_cli.auth import get_aetheros_auth_status
    from aetheros_cli.aetheros_subscription import get_aetheros_subscription_features

    config = load_config() or {}

    try:
        auth = get_aetheros_auth_status() or {}
    except Exception:
        auth = {}

    logged_in = bool(auth.get("logged_in"))

    print()
    print(color("  AetherOS", Colors.MAGENTA))
    print(color("  ────────", Colors.MAGENTA))
    if logged_in:
        portal = auth.get("portal_base_url") or DEFAULT_PORTAL_URL
        print(f"  Auth:    {color('✓ logged in', Colors.GREEN)}")
        print(f"  Portal:  {portal}")
        inference = auth.get("inference_base_url")
        if inference:
            print(f"  API:     {inference}")
    else:
        print(f"  Auth:    {color('not logged in', Colors.YELLOW)}")
        print(f"  Sign up: {SUBSCRIPTION_URL}")
        print(f"  Login:   aetheros portal")

    # Provider selection (independent of auth)
    model_cfg = config.get("model") if isinstance(config.get("model"), dict) else {}
    provider = str(model_cfg.get("provider") or "").strip().lower()
    if provider in ("aetheros", "nous"):
        print(f"  Model:   {color('✓ using AetherOS as inference provider', Colors.GREEN)}")
    elif provider:
        print(f"  Model:   currently {provider} (switch with `aetheros model`)")

    # Tool Gateway routing
    print()
    print(color("  Tool Gateway", Colors.MAGENTA))
    print(color("  ────────────", Colors.MAGENTA))
    try:
        features = get_aetheros_subscription_features(config)
    except Exception:
        features = None

    if features is None:
        print("  (could not resolve subscription state)")
        return 0

    rows = []
    for feat in features.items():
        if feat.managed_by_aetheros:
            state = color("via AetherOS", Colors.GREEN)
        elif feat.active and feat.current_provider:
            state = feat.current_provider
        elif feat.active:
            state = "active"
        else:
            state = color("not configured", Colors.DIM)
        rows.append((feat.label, state))

    width = max((len(r[0]) for r in rows), default=0)
    for label, state in rows:
        print(f"  {label:<{width}}   {state}")

    if not logged_in:
        print()
        print(color(f"  Docs: {DOCS_URL}", Colors.DIM))
    return 0


def _cmd_open(args) -> int:
    """Open the AetherOS subscription page in the default browser."""
    target = SUBSCRIPTION_URL
    print(f"Opening {target}")
    try:
        opened = webbrowser.open(target)
    except Exception:
        opened = False
    if not opened:
        print()
        print("Could not launch a browser. Visit the URL above manually.")
        return 1
    return 0


def _cmd_tools(args) -> int:
    """List the Tool Gateway catalog + current routing."""
    from aetheros_cli.aetheros_subscription import get_aetheros_subscription_features

    config = load_config() or {}
    try:
        features = get_aetheros_subscription_features(config)
    except Exception:
        print("Could not resolve Tool Gateway state.", file=sys.stderr)
        return 1

    # Static catalog — the partners Tool Gateway routes to today.
    catalog = [
        ("web",       "Web search & extract",  "Firecrawl"),
        ("image_gen", "Image generation",      "FAL"),
        ("tts",       "Text-to-speech",        "OpenAI TTS"),
        ("browser",   "Browser automation",    "Browser Use"),
        ("modal",     "Cloud terminal",        "Modal"),
    ]

    print()
    print(color("  Tool Gateway catalog", Colors.MAGENTA))
    print(color("  ────────────────────", Colors.MAGENTA))

    if not features.aetheros_auth_present:
        print(color("  Not logged into AetherOS — sign in with `aetheros portal`.", Colors.YELLOW))
        print()

    label_width = max(len(label) for _, label, _ in catalog)
    for key, label, partner in catalog:
        feat = features.features.get(key)
        if feat is None:
            state = color("unknown", Colors.DIM)
        elif feat.managed_by_aetheros:
            state = color("✓ via AetherOS", Colors.GREEN)
        elif feat.active and feat.current_provider:
            state = feat.current_provider
        elif feat.active:
            state = "active"
        else:
            state = color("not configured", Colors.DIM)
        print(f"  {label:<{label_width}}  partner: {partner:<14} {state}")

    print()
    print(color(f"  Manage your subscription: {SUBSCRIPTION_URL}", Colors.DIM))
    print(color(f"  Docs: {DOCS_URL}", Colors.DIM))
    return 0


def _cmd_login(args) -> int:
    """Run the one-shot AetherOS onboarding (login + model + provider + tools).

    This is the human-readable front door for `aetheros auth add aetheros
    --type oauth`. It reuses the exact wiring behind `aetheros setup --portal`
    (which in turn runs the same AetherOS flow as the first-time quick setup),
    so the commands stay in lockstep: device-code login, pick an AetherOS
    model, switch the inference provider to AetherOS, then offer the Tool
    Gateway opt-in.
    """
    from aetheros_cli.setup import _run_portal_one_shot

    config = load_config() or {}
    try:
        _run_portal_one_shot(config)
    except (KeyboardInterrupt, EOFError):
        print()
        print("Portal setup cancelled.")
        return 1
    return 0


def portal_command(args) -> int:
    """Top-level dispatch for `aetheros portal <subcommand>`."""
    sub = getattr(args, "portal_command", None)
    if sub in {None, "", "login"}:
        # Default to the one-shot onboarding — `aetheros portal` is the
        # human-readable alias for `aetheros auth add aetheros --type oauth` /
        # `aetheros setup --portal`.
        return _cmd_login(args)
    if sub in {"info", "status"}:
        # `status` kept as a back-compat alias for the prior default.
        return _cmd_status(args)
    if sub == "open":
        return _cmd_open(args)
    if sub == "tools":
        return _cmd_tools(args)
    print(f"Unknown portal subcommand: {sub}", file=sys.stderr)
    print("Run `aetheros portal -h` for usage.", file=sys.stderr)
    return 1


def add_parser(subparsers) -> None:
    """Register `aetheros portal` on the given argparse subparsers object."""
    portal_parser = subparsers.add_parser(
        "portal",
        help="Set up AetherOS (login, model pick, Tool Gateway); see also `portal info`",
        description=(
            "Run `aetheros portal` with no subcommand to log in to AetherOS "
            "and set it up — pick a model, set AetherOS as your provider, and "
            "offer the Tool Gateway (the human-readable alias for `aetheros "
            "auth add aetheros --type oauth`, identical to `aetheros setup "
            "--portal`). Subcommands: login (default), info, open, tools."
        ),
    )
    portal_sub = portal_parser.add_subparsers(dest="portal_command")

    portal_sub.add_parser(
        "login",
        help="Log in to AetherOS + set it up (default; one-shot onboarding)",
    )
    portal_sub.add_parser(
        "info",
        help="Show AetherOS auth + Tool Gateway routing summary",
    )
    # `status` retained as a hidden back-compat alias for `info`.
    portal_sub.add_parser("status")
    portal_sub.add_parser(
        "open",
        help="Open the AetherOS subscription page in your default browser",
    )
    portal_sub.add_parser(
        "tools",
        help="List Tool Gateway tools and which are routed via AetherOS",
    )

    portal_parser.set_defaults(func=portal_command)
