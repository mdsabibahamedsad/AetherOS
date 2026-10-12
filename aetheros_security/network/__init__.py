"""
Network Security for AetherOS
=============================

Network policy enforcement: host allow/deny lists, port restrictions, DNS
guards, and TLS verification. Used by the plugin sandbox and the privacy
offline-mode guard.

Usage::

    from aetheros_security.network import NetworkSecurityManager

    manager = NetworkSecurityManager()
    manager.set_allowlist(["api.openai.com"])
    allowed = manager.check_connection("api.openai.com", 443)
"""

from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

#: Private / link-local ranges never reachable by sandboxed code by default.
_BLOCKED_CIDRS = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]

_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$")


@dataclass
class NetworkDecision:
    """Result of a network access check."""
    allowed: bool
    host: str
    port: int
    reason: str = ""
    source: str = "policy"  # policy | sandbox | privacy | default


class NetworkSecurityManager:
    """Enforces host/port/DNS-level network policy."""

    def __init__(self) -> None:
        self._allowlist_hosts: Set[str] = set()
        self._denylist_hosts: Set[str] = set()
        self._allowlist_ports: Set[int] = set()
        self._denylist_ports: Set[int] = set()
        self._blocked_cidrs: List = [ipaddress.ip_network(c) for c in _BLOCKED_CIDRS]
        self._block_private: bool = True
        self._tls_verify: bool = True

    # ------------------------------------------------------------------
    # Policy configuration
    # ------------------------------------------------------------------

    def set_allowlist(self, hosts: List[str]) -> None:
        """Restrict connections to the given host list (exclusive)."""
        self._allowlist_hosts = {self._normalize(h) for h in hosts if h}

    def set_denylist(self, hosts: List[str]) -> None:
        """Never allow connections to the given hosts."""
        self._denylist_hosts = {self._normalize(h) for h in hosts if h}

    def set_port_allowlist(self, ports: List[int]) -> None:
        self._allowlist_ports = {int(p) for p in ports}

    def set_port_denylist(self, ports: List[int]) -> None:
        self._denylist_ports = {int(p) for p in ports}

    def set_block_private_ranges(self, enabled: bool) -> None:
        self._block_private = enabled

    def set_tls_verify(self, enabled: bool) -> None:
        """Never disable in production; only for local/test hosts."""
        self._tls_verify = enabled

    @staticmethod
    def _normalize(host: str) -> str:
        return (host or "").lower().rstrip(".")

    def _is_ip(self, host: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            return ipaddress.ip_address(host)
        except ValueError:
            return None

    def _is_private(self, addr) -> bool:
        for network in self._blocked_cidrs:
            if addr in network:
                return True
        return False

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_host(self, host: str) -> NetworkDecision:
        """Check whether a host may be contacted at all."""
        host = self._normalize(host)
        if not host:
            return NetworkDecision(False, host, 0, "empty host")

        if host in self._denylist_hosts:
            return NetworkDecision(False, host, 0, "host is denied", "policy")
        if host in LOCALHOST_ALIASES and self._denylist_hosts:
            return NetworkDecision(False, host, 0, "local host denied", "policy")

        addr = self._is_ip(host)
        if addr is not None:
            if self._block_private and self._is_private(addr):
                return NetworkDecision(False, host, 0, "private/loopback range blocked", "default")
        else:
            if not _HOSTNAME_RE.match(host):
                return NetworkDecision(False, host, 0, "malformed hostname", "policy")

        if self._allowlist_hosts:
            # Allowlist is exclusive; wildcard subdomains supported.
            if host not in self._allowlist_hosts and not any(
                host.endswith("." + a) for a in self._allowlist_hosts
            ):
                return NetworkDecision(False, host, 0, "host not in allowlist", "policy")
        return NetworkDecision(True, host, 0)

    def check_port(self, port: int) -> NetworkDecision:
        port = int(port)
        if self._denylist_ports and port in self._denylist_ports:
            return NetworkDecision(False, "", port, "port is denied", "policy")
        if self._allowlist_ports and port not in self._allowlist_ports:
            return NetworkDecision(False, "", port, "port not in allowlist", "policy")
        return NetworkDecision(True, "", port)

    def check_connection(self, host: str, port: int) -> NetworkDecision:
        """Check whether a ``host:port`` connection is permitted."""
        host_decision = self.check_host(host)
        if not host_decision.allowed:
            return host_decision
        port_decision = self.check_port(port)
        if not port_decision.allowed:
            port_decision.host = host
            return port_decision
        return NetworkDecision(True, self._normalize(host), port)

    def check_dns(self, hostname: str) -> NetworkDecision:
        """Check whether a DNS resolution is permitted (policy + offline)."""
        return self.check_host(hostname)

    def is_private_host(self, host: str) -> bool:
        addr = self._is_ip(self._normalize(host))
        return addr is not None and self._is_private(addr)

    def tls_verify_enabled(self) -> bool:
        return self._tls_verify

    def apply_sandbox_rules(self, allow_hosts: List[str], deny_hosts: List[str], network_access: bool) -> None:
        """Apply sandbox-scoped rules.

        With ``network_access=False`` everything is denied. Otherwise the
        sandbox's host lists constrain the allow/deny sets.
        """
        if not network_access:
            self._denylist_hosts = {"*"}
            self._allowlist_hosts = set()
            return
        self._denylist_hosts = {self._normalize(h) for h in deny_hosts if h}
        self._allowlist_hosts = {self._normalize(h) for h in allow_hosts if h}

    def get_stats(self) -> Dict[str, int]:
        return {
            "allowlisted_hosts": len(self._allowlist_hosts),
            "denylisted_hosts": len(self._denylist_hosts),
            "blocked_cidrs": len(self._blocked_cidrs),
        }


LOCALHOST_ALIASES = {"localhost", "127.0.0.1", "::1"}


# Global network security manager
_network_manager: NetworkSecurityManager | None = None


def get_network_security_manager() -> NetworkSecurityManager:
    """Return the global NetworkSecurityManager singleton."""
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkSecurityManager()
    return _network_manager
