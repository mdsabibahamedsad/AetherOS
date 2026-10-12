"""Backward-compatibility shim for :mod:`aetheros_cli.aetheros_account`.

The module was renamed from ``nous_account`` to ``aetheros_account`` as part
of the AetherOS rebranding. This shim re-exports the full public API so
existing imports, plugins and scripts keep working unchanged. New code
should import from ``aetheros_cli.aetheros_account`` instead.
"""
from aetheros_cli.aetheros_account import (  # noqa: F401
    AetherOSAccountInfo,
    AetherOSAccountInfoSource,
    AetherOSPaidServiceAccessInfo,
    AetherOSSubscriptionInfo,
    AetherOSToolAccessInfo,
    TOOL_COVERAGE_CATEGORIES,
    aetheros_billing_url,
    format_aetheros_entitlement_message,
    get_aetheros_account_info,
    reset_aetheros_account_info_cache,
)
from aetheros_cli.aetheros_account import (  # noqa: F401  (legacy aliases)
    NousAccountInfoSource,
    NousPortalAccountInfo,
    NousPortalSubscriptionInfo,
    NousPaidServiceAccessInfo,
    NousToolAccessInfo,
    format_nous_portal_entitlement_message,
    get_nous_portal_account_info,
    nous_portal_billing_url,
    reset_nous_portal_account_info_cache,
)
