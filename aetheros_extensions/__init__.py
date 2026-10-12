"""AetherOS Universal Extension Platform."""

from aetheros_extensions.manifest import (
    ExtensionManifest, ExtensionType, LifecycleState, can_transition,
    EXTENSION_API_VERSION,
)
from aetheros_extensions.package import (
    build_package, verify_package, PackageReport,
)
from aetheros_extensions.trust import (
    PublisherRecord, PublisherTrust, TrustLevel, generate_keypair,
    sign_package_digest, verify_signature,
)
from aetheros_extensions.permissions import (
    CATALOG, Grant, PermissionEngine, Risk, normalize_requested,
)
from aetheros_extensions.registry import (
    ExtensionRecord, ExtensionRegistry, check_compat, satisfies,
)
from aetheros_extensions.scanner import (
    DynamicResult, ScanResult, run_dynamic, scan_static,
)
from aetheros_extensions.sandbox import (
    CapabilityFS, CapabilityNet, ExtensionContext, ExtensionHost,
    HealthSnapshot, SecretBroker, SANDBOX_BOUNDARY, redact_secrets,
)
from aetheros_extensions.sources import SourceManager, SourcePolicy
from aetheros_extensions import bridges
from aetheros_extensions.service import ExtensionService

__all__ = [
    "ExtensionManifest", "ExtensionType", "LifecycleState", "can_transition",
    "EXTENSION_API_VERSION",
    "build_package", "verify_package", "PackageReport",
    "PublisherRecord", "PublisherTrust", "TrustLevel", "generate_keypair",
    "sign_package_digest", "verify_signature",
    "CATALOG", "Grant", "PermissionEngine", "Risk", "normalize_requested",
    "ExtensionRecord", "ExtensionRegistry", "check_compat", "satisfies",
    "DynamicResult", "ScanResult", "run_dynamic", "scan_static",
    "CapabilityFS", "CapabilityNet", "ExtensionContext", "ExtensionHost",
    "HealthSnapshot", "SecretBroker", "SANDBOX_BOUNDARY", "redact_secrets",
    "SourceManager", "SourcePolicy",
    "bridges",
    "ExtensionService",
]
