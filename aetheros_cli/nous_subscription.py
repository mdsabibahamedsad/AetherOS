"""Backward-compatibility shim for :mod:`aetheros_cli.aetheros_subscription`.

The module was renamed from ``nous_subscription`` to ``aetheros_subscription``
as part of the AetherOS rebranding. This shim re-exports the full public API
so existing imports, plugins and scripts keep working unchanged. New code
should import from ``aetheros_cli.aetheros_subscription`` instead.
"""
# Re-export everything from the canonical module
from aetheros_cli.aetheros_subscription import *  # noqa: F401,F403
# Provide the specific imports that tests may patch
from aetheros_cli.config import get_env_value  # noqa: F401
from aetheros_cli.aetheros_account import (  # noqa: F401
    get_nous_portal_account_info as get_nous_portal_account_info,
)
# Explicitly expose the legacy aliases for backward compatibility
from aetheros_cli.aetheros_subscription import (  # noqa: F401
    NousFeatureState as NousFeatureState,
    NousSubscriptionFeatures as NousSubscriptionFeatures,
    apply_nous_managed_defaults as apply_nous_managed_defaults,
    ensure_nous_portal_access as ensure_nous_portal_access,
    get_nous_subscription_features as get_nous_subscription_features,
)
