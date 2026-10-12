"""AetherOS Python SDK (`aetheros-sdk`). Sync + async typed clients."""

from aetheros_sdk.client import AsyncClient, Client, verify_webhook
from aetheros_sdk.errors import RetryPolicy, SDKError, TimeoutPolicy

__version__ = "1.0.0"
__all__ = ["AsyncClient", "Client", "RetryPolicy", "SDKError",
           "TimeoutPolicy", "verify_webhook"]
