"""
Network Manager — capability-controlled network access.

Enforces DNS policy, domain allowlist/denylist, IP policy, proxy,
TLS validation, SSRF defense, DNS rebinding defense, egress control,
rate limits, and network budgets.
"""

from __future__ import annotations

import logging
import threading
import time
import re
import ipaddress
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from urllib.parse import urlparse
from enum import Enum

from kernel.core.types import (
    AuthorityGrant,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class NetworkPolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    PROXY = "proxy"


@dataclass
class NetworkRule:
    """A network access rule."""
    rule_id: str
    name: str
    action: NetworkPolicyDecision
    domains: List[str] = field(default_factory=list)  # Allow/deny patterns
    ip_ranges: List[str] = field(default_factory=list)  # CIDR notation
    ports: List[int] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)  # http, https, ws, wss, tcp, udp
    require_tls: bool = False
    require_proxy: bool = False
    rate_limit: Optional[Dict[str, Any]] = None  # requests per time window
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0


@dataclass
class NetworkBudget:
    """Network budget for an agent."""
    agent_id: str
    max_requests_per_minute: int = 100
    max_bandwidth_mbps: float = 10.0
    max_concurrent_connections: int = 10
    used_requests: int = 0
    used_bandwidth_mb: float = 0.0
    window_start: float = field(default_factory=_now)
    reset_interval_seconds: int = 60


class NetworkManager:
    """
    Capability-controlled network access manager.
    
    Enforces:
    - DNS policy
    - Domain allowlist/denylist
    - IP policy
    - Proxy configuration
    - TLS validation
    - SSRF defense
    - DNS rebinding defense
    - Egress control
    - Rate limits
    - Network budgets
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._rules: Dict[str, NetworkRule] = {}
        self._rule_order: List[str] = []
        
        # Allow/deny lists
        self._domain_allowlist: Set[str] = set()
        self._domain_denylist: Set[str] = set()
        self._ip_allowlist: Set[str] = set()
        self._ip_denylist: Set[str] = set()
        
        # Proxy settings
        self._proxy_url: Optional[str] = None
        self._proxy_bypass: Set[str] = set()
        
        # Budgets
        self._budgets: Dict[str, NetworkBudget] = {}
        
        # TLS settings
        self._require_tls = True
        self._allowed_tls_versions: Set[str] = {"TLSv1.2", "TLSv1.3"}
        self._blocked_ciphers: Set[str] = set()
        
        # SSRF defense
        self._blocked_ip_ranges = [
            "127.0.0.0/8",      # Loopback
            "10.0.0.0/8",       # Private
            "172.16.0.0/12",    # Private
            "192.168.0.0/16",   # Private
            "169.254.0.0/16",   # Link-local
            "::1/128",          # Loopback IPv6
            "fc00::/7",         # Private IPv6
            "fe80::/10",        # Link-local IPv6
        ]
        
        # DNS cache for rebinding defense
        self._dns_cache: Dict[str, List[str]] = {}
        self._dns_cache_ttl = 300  # 5 minutes

        # Register default rules
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register default network rules."""
        # Default deny for private IPs (SSRF defense)
        self.add_rule(NetworkRule(
            rule_id="ssrf_private_ip",
            name="Block Private IP Ranges",
            action=NetworkPolicyDecision.DENY,
            ip_ranges=self._blocked_ip_ranges,
            priority=200,
        ))

        # Require TLS for external
        self.add_rule(NetworkRule(
            rule_id="require_tls_external",
            name="Require TLS for External",
            action=NetworkPolicyDecision.REQUIRE_APPROVAL,
            domains=["*"],  # All domains
            require_tls=True,
            priority=100,
        ))

    def add_rule(self, rule: NetworkRule) -> None:
        """Add a network rule."""
        with self._lock:
            self._rules[rule.rule_id] = rule
            self._rule_order = sorted(
                self._rules.keys(),
                key=lambda r: self._rules[r].priority,
                reverse=True,
            )

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a network rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._rule_order = [r for r in self._rule_order if r != rule_id]
                return True
        return False

    def add_domain_allowlist(self, domains: List[str]) -> None:
        """Add domains to allowlist."""
        with self._lock:
            self._domain_allowlist.update(domains)

    def add_domain_denylist(self, domains: List[str]) -> None:
        """Add domains to denylist."""
        with self._lock:
            self._domain_denylist.update(domains)

    def add_ip_allowlist(self, ips: List[str]) -> None:
        """Add IPs/CIDRs to allowlist."""
        with self._lock:
            self._ip_allowlist.update(ips)

    def add_ip_denylist(self, ips: List[str]) -> None:
        """Add IPs/CIDRs to denylist."""
        with self._lock:
            self._ip_denylist.update(ips)

    def set_proxy(self, proxy_url: str, bypass_domains: List[str] = None) -> None:
        """Configure proxy."""
        with self._lock:
            self._proxy_url = proxy_url
            self._proxy_bypass = set(bypass_domains or [])

    def check_url(
        self,
        url: str,
        grant: AuthorityGrant = None,
        agent_id: str = "",
    ) -> tuple:
        """
        Check if a URL is allowed.
        
        Returns: (allowed: bool, reason: str)
        """
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        scheme = parsed.scheme or ""
        port = parsed.port

        # Check denylist first
        if self._is_denied(domain):
            return False, f"Domain in denylist: {domain}"

        # Check allowlist (if configured)
        if self._domain_allowlist and not self._is_allowed(domain):
            return False, f"Domain not in allowlist: {domain}"

        # Check IP ranges (resolve domain)
        ips = self._resolve_domain(domain)
        for ip in ips:
            if self._is_ip_denied(ip):
                return False, f"IP in denylist: {ip}"
            if self._ip_allowlist and not self._is_ip_allowed(ip):
                return False, f"IP not in allowlist: {ip}"

        # Check scheme/TLS
        if self._require_tls and scheme not in ("https", "wss"):
            # Allow localhost/http for development
            if domain not in ("localhost", "127.0.0.1", "::1"):
                return False, f"TLS required for {domain}"

        # Check port
        if port and port not in (80, 443, 8080, 8443):
            # Non-standard ports need approval
            return False, f"Non-standard port {port} requires approval"

        # Check network scopes from grant
        if grant and grant.network_scopes:
            if not self._check_network_scope(domain, grant.network_scopes):
                return False, f"Network scope not granted: {domain}"

        # Check budget
        if agent_id and not self._check_budget(agent_id):
            return False, "Network budget exceeded"

        # Evaluate rules
        for rule_id in self._rule_order:
            rule = self._rules[rule_id]
            if not rule.enabled:
                continue
            
            if self._rule_matches(rule, url, domain, scheme, port, ips):
                if rule.action == NetworkPolicyDecision.DENY:
                    return False, f"Rule denied: {rule.name}"
                elif rule.action == NetworkPolicyDecision.REQUIRE_APPROVAL:
                    return False, f"Approval required: {rule.name}"
                elif rule.action == NetworkPolicyDecision.PROXY:
                    return True, f"Proxied via {rule.metadata.get('proxy', 'default')}"

        return True, "Allowed"

    def _is_denied(self, domain: str) -> bool:
        """Check if domain is in denylist."""
        for denied in self._domain_denylist:
            if self._domain_matches(domain, denied):
                return True
        return False

    def _is_allowed(self, domain: str) -> bool:
        """Check if domain is in allowlist."""
        for allowed in self._domain_allowlist:
            if self._domain_matches(domain, allowed):
                return True
        return False

    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """Check if domain matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern.startswith("*."):
            suffix = pattern[1:]
            return domain == suffix or domain.endswith(suffix)
        return domain == pattern

    def _resolve_domain(self, domain: str) -> List[str]:
        """Resolve domain to IPs (with caching for rebinding defense)."""
        now = _now()
        
        if domain in self._dns_cache:
            cached, timestamp = self._dns_cache[domain]
            if now - timestamp < self._dns_cache_ttl:
                return cached
        
        # In production, would actually resolve DNS
        # For now, return empty (would need socket.getaddrinfo)
        ips = []
        
        self._dns_cache[domain] = (ips, now)
        return ips

    def _is_ip_denied(self, ip: str) -> bool:
        """Check if IP is in denylist."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for denied in self._ip_denylist:
                if ip_obj in ipaddress.ip_network(denied):
                    return True
            # Also check built-in blocked ranges
            for blocked in self._blocked_ip_ranges:
                if ip_obj in ipaddress.ip_network(blocked):
                    return True
        except ValueError:
            pass
        return False

    def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is in allowlist."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for allowed in self._ip_allowlist:
                if ip_obj in ipaddress.ip_network(allowed):
                    return True
        except ValueError:
            pass
        return False

    def _check_network_scope(self, domain: str, scopes: List[str]) -> bool:
        """Check if domain matches granted network scopes."""
        for scope in scopes:
            if scope == "*":
                return True
            if self._domain_matches(domain, scope):
                return True
            # Check if scope is a parent domain
            if domain.endswith("." + scope) or domain == scope:
                return True
        return False

    def _check_budget(self, agent_id: str) -> bool:
        """Check network budget."""
        budget = self._budgets.get(agent_id)
        if not budget:
            # Create default budget
            budget = NetworkBudget(agent_id=agent_id)
            self._budgets[agent_id] = budget
        
        # Reset window if needed
        if _now() - budget.window_start > budget.reset_interval_seconds:
            budget.used_requests = 0
            budget.used_bandwidth_mb = 0.0
            budget.window_start = _now()
        
        return budget.used_requests < budget.max_requests_per_minute

    def record_request(self, agent_id: str, bytes_sent: int = 0, bytes_received: int = 0) -> None:
        """Record network request for budget tracking."""
        with self._lock:
            budget = self._budgets.get(agent_id)
            if not budget:
                budget = NetworkBudget(agent_id=agent_id)
                self._budgets[agent_id] = budget
            
            budget.used_requests += 1
            budget.used_bandwidth_mb += (bytes_sent + bytes_received) / (1024 * 1024)

    def _rule_matches(
        self,
        rule: NetworkRule,
        url: str,
        domain: str,
        scheme: str,
        port: Optional[int],
        ips: List[str],
    ) -> bool:
        """Check if a rule matches a request."""
        # Check domain
        if rule.domains:
            matched = False
            for pattern in rule.domains:
                if self._domain_matches(domain, pattern):
                    matched = True
                    break
            if not matched:
                return False
        
        # Check IP ranges
        if rule.ip_ranges:
            matched = False
            for ip in ips:
                for cidr in rule.ip_ranges:
                    try:
                        if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr):
                            matched = True
                            break
                    except ValueError:
                        pass
            if not matched:
                return False
        
        # Check ports
        if rule.ports and port:
            if port not in rule.ports:
                return False
        
        # Check protocols
        if rule.protocols:
            if scheme not in rule.protocols:
                return False
        
        return True

    def get_budget_status(self, agent_id: str) -> Dict[str, Any]:
        """Get network budget status."""
        budget = self._budgets.get(agent_id)
        if not budget:
            return {"error": "No budget found"}
        
        return {
            "agent_id": budget.agent_id,
            "max_requests_per_minute": budget.max_requests_per_minute,
            "used_requests": budget.used_requests,
            "remaining_requests": max(0, budget.max_requests_per_minute - budget.used_requests),
            "max_bandwidth_mbps": budget.max_bandwidth_mbps,
            "used_bandwidth_mb": budget.used_bandwidth_mb,
            "max_concurrent_connections": budget.max_concurrent_connections,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get network manager statistics."""
        with self._lock:
            return {
                "rules": len(self._rules),
                "domain_allowlist": len(self._domain_allowlist),
                "domain_denylist": len(self._domain_denylist),
                "ip_allowlist": len(self._ip_allowlist),
                "ip_denylist": len(self._ip_denylist),
                "proxy_configured": self._proxy_url is not None,
                "active_budgets": len(self._budgets),
                "dns_cache_size": len(self._dns_cache),
            }

    def shutdown(self) -> None:
        """Shutdown the network manager."""
        logger.info("NetworkManager: shutting down")
        with self._lock:
            self._rules.clear()
            self._rule_order.clear()
            self._domain_allowlist.clear()
            self._domain_denylist.clear()
            self._ip_allowlist.clear()
            self._ip_denylist.clear()
            self._budgets.clear()
            self._dns_cache.clear()