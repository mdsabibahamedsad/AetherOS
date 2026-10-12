"""Provider SDK: build an AetherOS-compatible agent (spec section 68).

External developers subclass the pieces below; AetherOS discovers the
agent via its Agent Card, lists services via the registry API, and
settles via the PaymentProvider interface. See
docs/AETHEROS_PROVIDER_SDK.md for the full guide.
"""

from __future__ import annotations

from aetheros_agent_market import schemas as S
from aetheros_agent_market.payments import PaymentError, PaymentProvider
from aetheros_agent_market.registries import LocalRegistry
from aetheros_agent_market.taxonomy import ALL_CAPABILITIES
from aetheros_agent_market.verification import ResultVerificationEngine

__all__ = [
    "S",
    "PaymentProvider",
    "PaymentError",
    "LocalRegistry",
    "ALL_CAPABILITIES",
    "ResultVerificationEngine",
    "AgentProviderBase",
]


class AgentProviderBase(PaymentProvider):
    """Starter base for an external paid provider.

    Implement quote() pricing and settlement rails; idempotency,
    transaction persistence, and reconcile() come free from _BaseProvider
    if you subclass one of the built-ins' machinery — or implement
    PaymentProvider directly for full control.
    """

    name = "external:example"
    supports_escrow = False
