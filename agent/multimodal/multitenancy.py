"""Multi-Tenancy & Federation (Phase 62).

Enterprise multi-tenancy with federation support:
- Tenant isolation (data, compute, network)
- Tenant onboarding and lifecycle
- Resource quotas and billing
- Cross-tenant collaboration (federation)
- Tenant customization and white-labeling
- Data residency and compliance
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
from pathlib import Path

from agent.multimodal.production import MetricsCollector, LRUCache
from agent.multimodal.security_advanced import EncryptionManager, RBACManager, User, Role, Permission, ResourceType

logger = logging.getLogger(__name__)


class TenantStatus(Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"
    DELETED = "deleted"


class TenantTier(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class FederationStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass
class ResourceQuota:
    """Resource quota for a tenant."""
    max_models: int = 10
    max_concurrent_streams: int = 5
    max_storage_gb: float = 10.0
    max_api_calls_per_day: int = 10000
    max_concurrent_agents: int = 5
    max_memory_entries: int = 10000
    max_cost_usd_per_day: float = 10.0
    custom_limits: Dict[str, float] = field(default_factory=dict)


@dataclass
class Tenant:
    """Tenant definition."""
    tenant_id: str
    name: str
    display_name: str
    status: TenantStatus = TenantStatus.PROVISIONING
    tier: TenantTier = TenantTier.FREE
    owner_id: str = ""  # User ID of tenant admin
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    quotas: ResourceQuota = field(default_factory=ResourceQuota)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # White-labeling
    branding: Dict[str, str] = field(default_factory=dict)  # logo_url, primary_color, etc.
    domain: Optional[str] = None  # Custom domain
    # Compliance
    data_residency: Optional[str] = None  # e.g., "us-east-1", "eu-west-1"
    compliance_tags: List[str] = field(default_factory=list)  # ["gdpr", "hipaa", "soc2"]
    # Billing
    billing_email: Optional[str] = None
    payment_method_id: Optional[str] = None
    subscription_id: Optional[str] = None
    trial_ends_at: Optional[float] = None


@dataclass
class ResourceUsage:
    """Current resource usage for a tenant."""
    tenant_id: str
    models: int = 0
    concurrent_streams: int = 0
    storage_gb: float = 0.0
    api_calls_today: int = 0
    concurrent_agents: int = 0
    memory_entries: int = 0
    cost_usd_today: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class FederationLink:
    """Federation link between tenants."""
    link_id: str
    source_tenant_id: str
    target_tenant_id: str
    status: FederationStatus = FederationStatus.PENDING
    permissions: List[str] = field(default_factory=list)  # What can be shared
    created_at: float = field(default_factory=time.time)
    established_at: Optional[float] = None
    revoked_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class SharedResource:
    """A resource shared across federation."""
    resource_id: str
    resource_type: str  # model, dataset, memory, agent, workflow
    owner_tenant_id: str
    shared_with: List[str] = field(default_factory=list)  # Tenant IDs
    permissions: List[str] = field(default_factory=list)  # read, write, execute
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)


class TenantManager:
    """Manages tenant lifecycle and operations."""

    def __init__(
        self,
        encryption: Optional[Any] = None,
        storage_path: Optional[str] = None,
    ):
        self._tenants: Dict[str, Tenant] = {}
        self._usage: Dict[str, ResourceUsage] = {}
        self._lock = threading.Lock()
        self._metrics = MetricsCollector("tenant_manager")
        self.encryption = encryption

    def create_tenant(
        self,
        name: str,
        display_name: str,
        owner_id: str,
        tier: TenantTier = TenantTier.FREE,
        owner_email: Optional[str] = None,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            display_name=display_name,
            owner_id=owner_id,
            tier=tier,
            billing_email=owner_email,
        )

        # Set tier-appropriate quotas
        tenant.quotas = self._get_tier_quotas(tier)

        with self._lock:
            self._tenants[tenant_id] = tenant
            self._usage[tenant_id] = ResourceUsage(tenant_id=tenant_id)

        self._metrics.counter("tenants_created", labels={"tier": tier.value})
        logger.info(f"Created tenant: {tenant_id} ({name})")

        # Initialize tenant resources
        self._initialize_tenant_resources(tenant)

        return tenant

    def _get_tier_quotas(self, tier: TenantTier) -> ResourceQuota:
        """Get default quotas for tier."""
        quotas = {
            TenantTier.FREE: ResourceQuota(
                max_models=2, max_concurrent_streams=1, max_storage_gb=1.0,
                max_api_calls_per_day=1000, max_concurrent_agents=1,
                max_memory_entries=1000, max_cost_usd_per_day=1.0,
            ),
            TenantTier.STARTER: ResourceQuota(
                max_models=5, max_concurrent_streams=3, max_storage_gb=5.0,
                max_api_calls_per_day=10000, max_concurrent_agents=3,
                max_memory_entries=5000, max_cost_usd_per_day=10.0,
            ),
            TenantTier.PROFESSIONAL: ResourceQuota(
                max_models=20, max_concurrent_streams=10, max_storage_gb=50.0,
                max_api_calls_per_day=100000, max_concurrent_agents=10,
                max_memory_entries=50000, max_cost_usd_per_day=100.0,
            ),
            TenantTier.ENTERPRISE: ResourceQuota(
                max_models=100, max_concurrent_streams=50, max_storage_gb=500.0,
                max_api_calls_per_day=1000000, max_concurrent_agents=50,
                max_memory_entries=500000, max_cost_usd_per_day=1000.0,
            ),
            TenantTier.CUSTOM: ResourceQuota(
                max_models=1000, max_concurrent_streams=200, max_storage_gb=5000.0,
                max_api_calls_per_day=10000000, max_concurrent_agents=200,
                max_memory_entries=5000000, max_cost_usd_per_day=10000.0,
            ),
        }
        return quotas.get(tier, quotas[TenantTier.FREE])

    def _initialize_tenant_resources(self, tenant: Tenant) -> None:
        """Initialize tenant-specific resources."""
        # Create tenant-specific directories, databases, etc.
        logger.info(f"Initialized resources for tenant {tenant.tenant_id}")

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        with self._lock:
            return self._tenants.get(tenant_id)

    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False

            for key, value in updates.items():
                if hasattr(tenant, key):
                    setattr(tenant, key, value)
            tenant.updated_at = time.time()
            return True

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.SUSPENDED
            tenant.metadata["suspension_reason"] = reason
            tenant.updated_at = time.time()
            return True

    def activate_tenant(self, tenant_id: str) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.ACTIVE
            tenant.updated_at = time.time()
            return True

    def delete_tenant(self, tenant_id: str, force: bool = False) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False

            if tenant.status == TenantStatus.ACTIVE and not force:
                return False  # Must suspend first

            tenant.status = TenantStatus.DEPROVISIONING
            # Cleanup resources
            self._cleanup_tenant_resources(tenant)
            tenant.status = TenantStatus.DELETED
            del self._tenants[tenant_id]
            if tenant_id in self._usage:
                del self._usage[tenant_id]
            return True

    def _cleanup_tenant_resources(self, tenant: Tenant) -> None:
        """Clean up tenant resources."""
        logger.info(f"Cleaning up resources for tenant {tenant.tenant_id}")

    def get_usage(self, tenant_id: str) -> Optional[ResourceUsage]:
        with self._lock:
            return self._usage.get(tenant_id)

    def update_usage(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        with self._lock:
            usage = self._usage.get(tenant_id)
            if not usage:
                return False
            for key, value in updates.items():
                if hasattr(usage, key):
                    setattr(usage, key, value)
            usage.last_updated = time.time()
            return True

    def check_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        """Check if tenant has quota for resource."""
        tenant = self.get_tenant(tenant_id)
        usage = self.get_usage(tenant_id)
        if not tenant or not usage:
            return False

        quota_value = getattr(tenant.quotas, f"max_{resource}", None)
        usage_value = getattr(usage, resource, 0)

        if quota_value is None:
            return True  # No limit

        return (usage_value + amount) <= quota_value

    def record_usage(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        """Record resource usage."""
        if not self.check_quota(tenant_id, resource, amount):
            return False
        return self.update_usage(tenant_id, {resource: getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), resource, 0) + amount})

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        tenant = self.get_tenant(tenant_id)
        usage = self.get_usage(tenant_id)
        if not tenant or not usage:
            return {}

        quota_dict = {
            "models": tenant.quotas.max_models,
            "concurrent_streams": tenant.quotas.max_concurrent_streams,
            "storage_gb": tenant.quotas.max_storage_gb,
            "api_calls_per_day": tenant.quotas.max_api_calls_per_day,
            "concurrent_agents": tenant.quotas.max_concurrent_agents,
            "memory_entries": tenant.quotas.max_memory_entries,
            "cost_usd_per_day": tenant.quotas.max_cost_usd_per_day,
        }

        usage_dict = {
            "models": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "models", 0),
            "concurrent_streams": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "concurrent_streams", 0),
            "storage_gb": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "storage_gb", 0.0),
            "api_calls_today": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "api_calls_today", 0),
            "concurrent_agents": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "concurrent_agents", 0),
            "memory_entries": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "memory_entries", 0),
            "cost_usd_today": getattr(self._usage.get(tenant_id, ResourceUsage(tenant_id)), "cost_usd_today", 0.0),
        }

        utilization = {}
        for key in quota_dict:
            quota = quota_dict[key]
            used = usage_dict.get(key, 0)
            utilization[key] = (used / quota * 100) if quota > 0 else 0

        return {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "status": tenant.status.value,
            "tier": tenant.tier.value,
            "quotas": quota_dict,
            "usage": usage_dict,
            "utilization_pct": utilization,
            "over_quota": any(u > q for u, q in zip(usage_dict.values(), quota_dict.values()) if q > 0),
        }

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        with self._lock:
            tenants = list(self._tenants.values())
            if status:
                tenants = [t for t in tenants if t.status == status]
            return tenants


class FederationManager:
    """Manages cross-tenant federation."""

    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self._links: Dict[str, FederationLink] = {}
        self._shared_resources: Dict[str, SharedResource] = {}
        self._lock = threading.Lock()
        self._metrics = MetricsCollector("federation_manager")

    def create_federation_link(
        self,
        source_tenant_id: str,
        target_tenant_id: str,
        permissions: List[str],
        metadata: Optional[Dict] = None,
    ) -> FederationLink:
        """Create a federation link between tenants."""
        # Verify both tenants exist
        source = self.tenant_manager.get_tenant(source_tenant_id)
        target = self.tenant_manager.get_tenant(target_tenant_id)
        if not source or not target:
            raise ValueError("Source or target tenant not found")

        if source.tenant_id == target.tenant_id:
            raise ValueError("Cannot create federation link to self")

        # Check for existing link
        for link in self._links.values():
            if (link.source_tenant_id == source_tenant_id and link.target_tenant_id == target_tenant_id) or \
               (link.source_tenant_id == target_tenant_id and link.target_tenant_id == source_tenant_id):
                raise ValueError("Federation link already exists")

        link = FederationLink(
            link_id=f"fed_{uuid.uuid4().hex[:12]}",
            source_tenant_id=source_tenant_id,
            target_tenant_id=target_tenant_id,
            permissions=permissions,
            metadata=metadata or {},
        )

        with self._lock:
            self._links[link.link_id] = link

        self._metrics.counter("federation_links_created")
        logger.info(f"Created federation link: {source_tenant_id} <-> {target_tenant_id}")
        return link

    def accept_federation_link(self, link_id: str, accepting_tenant_id: str) -> bool:
        with self._lock:
            link = self._links.get(link_id)
            if not link:
                return False
            if link.target_tenant_id != accepting_tenant_id:
                return False
            if link.status != FederationStatus.PENDING:
                return False

            link.status = FederationStatus.ACTIVE
            link.established_at = time.time()
            self._metrics.counter("federation_links_accepted")
            return True

    def revoke_federation_link(self, link_id: str, revoking_tenant_id: str) -> bool:
        with self._lock:
            link = self._links.get(link_id)
            if not link:
                return False
            if link.source_tenant_id != revoking_tenant_id and link.target_tenant_id != revoking_tenant_id:
                return False
            if link.status != FederationStatus.ACTIVE:
                return False

            link.status = FederationStatus.REVOKED
            link.revoked_at = time.time()
            self._metrics.counter("federation_links_revoked")
            return True

    def share_resource(
        self,
        owner_tenant_id: str,
        resource_type: str,
        resource_id: str,
        target_tenant_ids: List[str],
        permissions: List[str],
        expires_at: Optional[float] = None,
    ) -> SharedResource:
        """Share a resource with federated tenants."""
        # Verify federation links exist
        for target_id in target_tenant_ids:
            if not self._has_active_link(owner_tenant_id, target_id):
                raise ValueError(f"No active federation link with tenant {target_id}")

        resource = SharedResource(
            resource_id=f"shared_{uuid.uuid4().hex[:12]}",
            resource_type=resource_type,
            owner_tenant_id=owner_tenant_id,
            shared_with=target_tenant_ids,
            permissions=permissions,
            expires_at=expires_at,
        )

        with self._lock:
            self._shared_resources[resource.resource_id] = resource

        self._metrics.counter("resources_shared")
        return resource

    def _has_active_link(self, tenant_a: str, tenant_b: str) -> bool:
        for link in self._links.values():
            if ((link.source_tenant_id == tenant_a and link.target_tenant_id == tenant_b) or
                (link.source_tenant_id == tenant_b and link.target_tenant_id == tenant_a)):
                return link.status == FederationStatus.ACTIVE
        return False

    def get_shared_resources(self, tenant_id: str) -> List[SharedResource]:
        with self._lock:
            return [
                r for r in self._shared_resources.values()
                if tenant_id in r.shared_with
            ]

    def revoke_sharing(self, resource_id: str, revoking_tenant_id: str) -> bool:
        with self._lock:
            resource = self._shared_resources.get(resource_id)
            if not resource:
                return False
            if resource.owner_tenant_id != tenant_id:
                return False

            # Remove or update
            del self._shared_resources[resource_id]
            return True

    def get_federation_links(self, tenant_id: str) -> List[FederationLink]:
        with self._lock:
            return [
                link for link in self._links.values()
                if link.source_tenant_id == tenant_id or link.target_tenant_id == tenant_id
            ]


class MultiTenancyManager:
    """Unified multi-tenancy manager combining tenant and federation management."""

    def __init__(
        self,
        encryption: Optional[Any] = None,
        storage_path: Optional[str] = None,
    ):
        self.tenant_manager = TenantManager(encryption=encryption, storage_path=storage_path)
        self.federation_manager = FederationManager(self.tenant_manager)
        self._metrics = MetricsCollector("multitenancy")

    def create_tenant(self, *args, **kwargs) -> Tenant:
        return self.tenant_manager.create_tenant(*args, **kwargs)

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self.tenant_manager.get_tenant(tenant_id)

    def create_federation(self, *args, **kwargs) -> FederationLink:
        return self.federation_manager.create_federation_link(*args, **kwargs)

    def share_resource(self, *args, **kwargs) -> SharedResource:
        return self.federation_manager.share_resource(*args, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        with self.tenant_manager._lock:
            tenants = list(self.tenant_manager._tenants.values())
            total = len(tenants)
            active = sum(1 for t in self.tenant_manager._tenants.values() if t.status == TenantStatus.ACTIVE)
            suspended = sum(1 for t in self.tenant_manager._tenants.values() if t.status == TenantStatus.SUSPENDED)

            tier_counts = defaultdict(int)
            for t in self.tenant_manager._tenants.values():
                tier_counts[t.tier.value] += 1

            return {
                "total_tenants": total,
                "active": active,
                "suspended": suspended,
                "by_tier": dict(tier_counts),
                "federation_links": len(self.federation_manager._links),
                "shared_resources": len(self.federation_manager._shared_resources),
            }


# Convenience functions
def create_tenant(
    name: str,
    display_name: str,
    owner_id: str,
    tier: TenantTier = TenantTier.FREE,
) -> Tenant:
    manager = TenantManager()
    return manager.create_tenant(name, display_name, owner_id, tier)


def create_federation(
    source_tenant_id: str,
    target_tenant_id: str,
    permissions: List[str],
) -> FederationLink:
    manager = TenantManager()
    fed = FederationManager(manager)
    return fed.create_federation_link(source_tenant_id, target_tenant_id, [])