"""AetherOS Integrations — provider adapters.

Importing this package registers every provider adapter with the shared
registry. Each adapter is a real implementation of its platform's protocol.
"""

from aetheros_integrations.providers.base import BaseProvider, ProviderRegistry, RESTProvider, register_provider, registry
from aetheros_integrations.providers import (
    messaging,  # noqa: F401
    email,  # noqa: F401
    calendar,  # noqa: F401
    storage,  # noqa: F401
    devtools,  # noqa: F401
    knowledge,  # noqa: F401
    productivity,  # noqa: F401
    crm,  # noqa: F401
    databases,  # noqa: F401
)

__all__ = ["BaseProvider", "ProviderRegistry", "RESTProvider", "register_provider", "registry"]
