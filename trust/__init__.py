"""AetherOS Trust Fabric 1.0 — runtime authority infrastructure.

INTEGRATION-FIRST: this package extends Master-50
:mod:`aetheros_control_plane` and :mod:`aetheros_security`. It does not
reimplement identity, crypto, delegation, base policy, approvals,
audit chaining, or network guards — it imports them and adds only
genuine gaps: R0-R8 risk, extended policy decisions, path governance,
capability tokens, quorum approvals, revocation propagation, layered
emergency control, incidents, signed receipts, boundaries, firewall
orchestration, trust scores with hard-deny supremacy, tool contracts,
health/doctor, compliance packs, benchmarks, and the facade.
"""

from .models import *  # noqa
from .fabric import TrustFabric  # noqa
from .risk import RiskEngine  # noqa
from .paths import ExecutionPathTracker  # noqa
from .capabilities import CapabilityAuthority  # noqa
from .approvals import ApprovalOrchestrator  # noqa
from .revocation import RevocationAuthority  # noqa
from .emergency import EmergencyController  # noqa
from .incidents import IncidentController  # noqa
from .provenance import ProvenanceEngine  # noqa
from .boundaries import (DataBoundaryController, NetworkBoundaryController,  # noqa
                         SecretBoundaryController)
from .firewall import ActionFirewall  # noqa
from .scores import TrustScoreEngine, PrivilegeGraph  # noqa
from .contracts import ToolContractValidator  # noqa
from .health import GovernanceHealthMonitor, trust_doctor  # noqa
from .compliance import ComplianceEngine  # noqa
from .policy_ext import (PolicySimulator, PolicyCanary, PolicyRegression,  # noqa
                         GovernanceReplay, ExtendedDecision)
from .benchmarks import TrustFabricBenchmark  # noqa
from .transport import create_app  # noqa
from .hsm import LocalCustody, Pkcs11Custody  # noqa
from .mtls import (bootstrap_local_pki, client_context,  # noqa
                   server_context)
from .rigs import LoopbackMCPServer, LoopbackMCPClient, LoopbackA2APeer  # noqa

__version__ = "1.0.0"
__all__ = ["TrustFabric", "__version__"]
