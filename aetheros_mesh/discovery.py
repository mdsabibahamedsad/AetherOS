"""Mesh node discovery (Master 49 section 6).

Supports:
- Local discovery
- LAN discovery
- Manual discovery
- A2A discovery
- Organization registry
- Marketplace registry
- Trusted registry
- Direct Agent Card
- Cached discovery

Every discovery source has separate trust.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

from .models import MeshNode, MeshNodeState, create_mesh_node_from_agent_card

logger = logging.getLogger(__name__)


@dataclass
class DiscoverySource:
    """A discovery source with its trust level."""
    name: str
    trust_level: float = 0.5  # 0.0 - 1.0
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    last_refresh: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    """Result from a discovery operation."""
    node: MeshNode
    source: str
    raw_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)


class MeshDiscovery:
    """Dynamic mesh node discovery with multiple sources."""
    
    DEFAULT_SOURCES = {
        "local": DiscoverySource("local", trust_level=1.0, config={"paths": []}),
        "lan": DiscoverySource("lan", trust_level=0.6, config={"scan_interval_s": 60.0}),
        "manual": DiscoverySource("manual", trust_level=0.8),
        "a2a": DiscoverySource("a2a", trust_level=0.7, config={"registry_url": ""}),
        "org_registry": DiscoverySource("org_registry", trust_level=0.9, config={"registry_path": ""}),
        "marketplace": DiscoverySource("marketplace", trust_level=0.5, config={"api_endpoint": ""}),
        "trusted_registry": DiscoverySource("trusted_registry", trust_level=0.95, config={"registry_path": ""}),
        "direct_card": DiscoverySource("direct_card", trust_level=0.6),
    }
    
    def __init__(
        self,
        mesh_id: str,
        home: Path,
        organization_id: str = "default",
        sources: Optional[Dict[str, DiscoverySource]] = None,
    ):
        self.mesh_id = mesh_id
        self.home = Path(home)
        self.organization_id = organization_id
        self._sources = sources or self.DEFAULT_SOURCES.copy()
        self._nodes: Dict[str, MeshNode] = {}
        self._edges: Dict[str, Dict[str, List[str]]] = {}  # node_id -> edge_type -> target_ids
        self._discovery_callbacks: List[Callable[[MeshNode], None]] = []
        self._cache_file = self.home / "mesh_discovery_cache.json"
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cached discovery results."""
        if self._cache_file.exists():
            try:
                data = json.loads(self._cache_file.read_text(encoding="utf-8"))
                for node_data in data.get("nodes", []):
                    node = MeshNode.from_dict(node_data)
                    self._nodes[node.node_id] = node
                for edge_data in data.get("edges", []):
                    # Edges stored as simple mappings
                    pass
                logger.info(f"Loaded {len(self._nodes)} cached mesh nodes")
            except Exception as e:
                logger.warning(f"Failed to load discovery cache: {e}")
    
    def _save_cache(self) -> None:
        """Save discovery cache."""
        try:
            self.home.mkdir(parents=True, exist_ok=True)
            data = {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "saved_at": time.time(),
                "mesh_id": self.mesh_id,
            }
            tmp = self._cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self._cache_file)
        except Exception as e:
            logger.warning(f"Failed to save discovery cache: {e}")
    
    def register_source(self, source: DiscoverySource) -> None:
        """Register or update a discovery source."""
        self._sources[source.name] = source
    
    def enable_source(self, name: str, enabled: bool = True) -> bool:
        """Enable or disable a discovery source."""
        if name in self._sources:
            self._sources[name].enabled = enabled
            return True
        return False
    
    def add_discovery_callback(self, callback: Callable[[MeshNode], None]) -> None:
        """Add callback for new node discoveries."""
        self._discovery_callbacks.append(callback)
    
    def discover_all(self, force_refresh: bool = False) -> List[DiscoveryResult]:
        """Run discovery across all enabled sources."""
        results = []
        for name, source in self._sources.items():
            if not source.enabled:
                continue
            if not force_refresh and source.last_refresh > 0:
                # Skip if recently refreshed (within 5 minutes)
                if time.time() - source.last_refresh < 300:
                    continue
            
            try:
                source_results = self._discover_from_source(name, source)
                results.extend(source_results)
                source.last_refresh = time.time()
            except Exception as e:
                logger.error(f"Discovery from {name} failed: {e}")
        
        self._save_cache()
        return results
    
    def _discover_from_source(
        self, 
        name: str, 
        source: DiscoverySource
    ) -> List[DiscoveryResult]:
        """Discover nodes from a specific source."""
        results = []
        
        if name == "local":
            results = self._discover_local(source)
        elif name == "lan":
            results = self._discover_lan(source)
        elif name == "manual":
            results = self._discover_manual(source)
        elif name == "a2a":
            results = self._discover_a2a(source)
        elif name == "org_registry":
            results = self._discover_org_registry(source)
        elif name == "marketplace":
            results = self._discover_marketplace(source)
        elif name == "trusted_registry":
            results = self._discover_trusted_registry(source)
        elif name == "direct_card":
            results = self._discover_direct_card(source)
        
        # Apply source trust to nodes
        for result in results:
            result.node.metadata["discovery_source"] = name
            result.node.metadata["source_trust"] = source.trust_level
            self._add_or_update_node(result.node)
            for cb in self._discovery_callbacks:
                try:
                    cb(result.node)
                except Exception as e:
                    logger.debug(f"Discovery callback failed: {e}")
        
        return results
    
    def _discover_local(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover local agents from configured paths."""
        results = []
        paths = source.config.get("paths", [])
        
        # Add default local paths
        if not paths:
            paths = [
                str(self.home / "agents"),
                str(self.home / "plugins"),
            ]
        
        for path_str in paths:
            path = Path(path_str)
            if not path.exists():
                continue
            
            for agent_dir in path.iterdir():
                if not agent_dir.is_dir():
                    continue
                
                card_file = agent_dir / "agent-card.json"
                if card_file.exists():
                    try:
                        card_data = json.loads(card_file.read_text(encoding="utf-8"))
                        node = create_mesh_node_from_agent_card(
                            card_data,
                            organization_id=self.organization_id,
                            location="local",
                        )
                        results.append(DiscoveryResult(
                            node=node,
                            source="local",
                            raw_data=card_data,
                        ))
                    except Exception as e:
                        logger.debug(f"Failed to parse local agent card {card_file}: {e}")
        
        return results
    
    def _discover_lan(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """LAN discovery via mDNS/DNS-SD (placeholder - not fully implemented)."""
        # Master 46 documents this as a gap - discovery without verification enables spoofing
        # This is a stub for future implementation with proper verification
        logger.debug("LAN discovery not implemented (requires mDNS/DNS-SD with verification)")
        return []
    
    def _discover_manual(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Manual discovery from imported cards."""
        results = []
        manual_dir = self.home / "manual_agents"
        if not manual_dir.exists():
            return results
        
        for card_file in manual_dir.glob("*.json"):
            try:
                card_data = json.loads(card_file.read_text(encoding="utf-8"))
                node = create_mesh_node_from_agent_card(
                    card_data,
                    organization_id=self.organization_id,
                    location="manual",
                )
                results.append(DiscoveryResult(
                    node=node,
                    source="manual",
                    raw_data=card_data,
                ))
            except Exception as e:
                logger.debug(f"Failed to parse manual agent card {card_file}: {e}")
        
        return results
    
    def _discover_a2a(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover via A2A network gateway."""
        results = []
        registry_url = source.config.get("registry_url", "")
        
        if not registry_url:
            return results
        
        try:
            # Use existing A2A network discovery
            from aetheros_network.discovery import discover_from_registry_file
            from aetheros_network import A2A_AGENT_CARD_PATH
            
            # This would fetch from the registry URL
            # For now, return empty - integration with aetheros_network needed
            logger.debug(f"A2A discovery from {registry_url} not fully wired")
        except Exception as e:
            logger.debug(f"A2A discovery failed: {e}")
        
        return results
    
    def _discover_org_registry(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover from organization registry file."""
        results = []
        registry_path = source.config.get("registry_path", "")
        
        if not registry_path:
            registry_path = str(self.home / "org_registry.json")
        
        registry_file = Path(registry_path)
        if not registry_file.exists():
            return results
        
        try:
            from aetheros_network.discovery import discover_from_registry_file
            discoveries = discover_from_registry_file(
                registry_file,
                kind="org_registry",
                organization_id=self.organization_id,
            )
            
            for disc in discoveries:
                if disc.errors:
                    continue
                node = MeshNode.from_dict(disc.identity)
                node.capabilities = [s["id"] for s in disc.card.get("skills", [])]
                node.protocols = [f"A2A/{disc.card.get('protocol_version', '1.0')}"]
                node.endpoint = disc.card.get("url", "")
                node.metadata["discovery_source"] = "org_registry"
                results.append(DiscoveryResult(
                    node=node,
                    source="org_registry",
                    raw_data=disc.card,
                ))
        except Exception as e:
            logger.debug(f"Org registry discovery failed: {e}")
        
        return results
    
    def _discover_marketplace(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover from agent marketplace."""
        results = []
        api_endpoint = source.config.get("api_endpoint", "")
        
        if not api_endpoint:
            return results
        
        try:
            # Use existing marketplace discovery
            from aetheros_agent_market.discovery import CapabilityIndex, DiscoveryHit
            from aetheros_agent_market.discovery import local_services_provider, network_services_provider
            
            index = CapabilityIndex()
            # Add marketplace provider
            # This would need a marketplace API client
            logger.debug(f"Marketplace discovery from {api_endpoint} not fully wired")
        except Exception as e:
            logger.debug(f"Marketplace discovery failed: {e}")
        
        return results
    
    def _discover_trusted_registry(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover from trusted registry (curated, verified agents)."""
        results = []
        registry_path = source.config.get("registry_path", "")
        
        if not registry_path:
            registry_path = str(self.home / "trusted_registry.json")
        
        registry_file = Path(registry_path)
        if not registry_file.exists():
            return results
        
        try:
            from aetheros_network.discovery import discover_from_registry_file
            discoveries = discover_from_registry_file(
                registry_file,
                kind="trusted_registry",
                organization_id=self.organization_id,
            )
            
            for disc in discoveries:
                if disc.errors:
                    continue
                node = MeshNode.from_dict(disc.identity)
                node.capabilities = [s["id"] for s in disc.card.get("skills", [])]
                node.protocols = [f"A2A/{disc.card.get('protocol_version', '1.0')}"]
                node.endpoint = disc.card.get("url", "")
                node.metadata["discovery_source"] = "trusted_registry"
                node.update_state(MeshNodeState.TRUSTED)  # Trusted registry = pre-verified
                results.append(DiscoveryResult(
                    node=node,
                    source="trusted_registry",
                    raw_data=disc.card,
                ))
        except Exception as e:
            logger.debug(f"Trusted registry discovery failed: {e}")
        
        return results
    
    def _discover_direct_card(self, source: DiscoverySource) -> List[DiscoveryResult]:
        """Discover from direct Agent Card URLs."""
        # This would be triggered by explicit user action
        return []
    
    def add_direct_card(self, card_data: Dict[str, Any], url: str = "") -> DiscoveryResult:
        """Add a node from a direct Agent Card (user-initiated)."""
        from aetheros_network.agent_card import parse_agent_card, validate_agent_card
        
        try:
            card = parse_agent_card(card_data, source_url=url)
            errors, warnings = validate_agent_card(card)
            
            node = create_mesh_node_from_agent_card(
                card_data,
                organization_id=self.organization_id,
                endpoint=url or card.url,
                location="direct",
            )
            node.metadata["discovery_source"] = "direct_card"
            
            result = DiscoveryResult(
                node=node,
                source="direct_card",
                raw_data=card_data,
                errors=errors,
                warnings=warnings,
            )
            
            self._add_or_update_node(node)
            return result
        except Exception as e:
            return DiscoveryResult(
                node=MeshNode(),
                source="direct_card",
                errors=[str(e)],
            )
    
    def _add_or_update_node(self, node: MeshNode) -> bool:
        """Add or update a node in the mesh."""
        existing = self._nodes.get(node.node_id)
        if existing:
            # Update existing node
            existing.capabilities = list(set(existing.capabilities) | set(node.capabilities))
            existing.protocols = list(set(existing.protocols) | set(node.protocols))
            existing.endpoint = node.endpoint or existing.endpoint
            existing.last_seen = time.time()
            existing.metadata.update(node.metadata)
            return False
        else:
            self._nodes[node.node_id] = node
            return True
    
    def get_node(self, node_id: str) -> Optional[MeshNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_nodes_by_capability(self, capability: str) -> List[MeshNode]:
        """Get all nodes with a specific capability."""
        return [n for n in self._nodes.values() if capability in n.capabilities]
    
    def get_nodes_by_state(self, state: MeshNodeState) -> List[MeshNode]:
        """Get all nodes in a specific state."""
        return [n for n in self._nodes.values() if n.state == state]
    
    def get_available_nodes(
        self, 
        required_capabilities: List[str] = None,
        min_trust: float = 0.0
    ) -> List[MeshNode]:
        """Get nodes available for task assignment."""
        nodes = []
        for node in self._nodes.values():
            if not node.is_available_for_task(required_capabilities):
                continue
            if node.get_overall_trust() < min_trust:
                continue
            nodes.append(node)
        return nodes
    
    def add_edge(
        self, 
        source_id: str, 
        target_id: str, 
        edge_type: str,
        provenance: Dict[str, Any] = None
    ) -> None:
        """Add an edge between nodes."""
        from .models import EdgeType
        
        if source_id not in self._nodes or target_id not in self._nodes:
            return
        
        edge_key = edge_type if isinstance(edge_type, str) else edge_type.value
        
        if source_id not in self._edges:
            self._edges[source_id] = {}
        if edge_key not in self._edges[source_id]:
            self._edges[source_id][edge_key] = []
        if target_id not in self._edges[source_id][edge_key]:
            self._edges[source_id][edge_key].append(target_id)
        
        # Also add reverse for undirected edge types
        undirected = {EdgeType.TRUST, EdgeType.COLLABORATION, EdgeType.ORGANIZATION}
        if isinstance(edge_type, EdgeType) and edge_type in undirected:
            if target_id not in self._edges:
                self._edges[target_id] = {}
            if edge_key not in self._edges[target_id]:
                self._edges[target_id][edge_key] = []
            if source_id not in self._edges[target_id][edge_key]:
                self._edges[target_id][edge_key].append(source_id)
    
    def get_neighbors(self, node_id: str, edge_type: str = None) -> List[str]:
        """Get neighbor node IDs."""
        if node_id not in self._edges:
            return []
        if edge_type:
            return self._edges[node_id].get(edge_type, [])
        # Return all neighbors
        neighbors = []
        for targets in self._edges[node_id].values():
            neighbors.extend(targets)
        return list(set(neighbors))
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the mesh."""
        if node_id in self._nodes:
            self._nodes[node_id].update_state(MeshNodeState.REMOVED)
            del self._nodes[node_id]
            # Clean up edges
            if node_id in self._edges:
                del self._edges[node_id]
            for src_edges in self._edges.values():
                for targets in src_edges.values():
                    if node_id in targets:
                        targets.remove(node_id)
            return True
        return False
    
    def suspend_node(self, node_id: str, reason: str = "") -> bool:
        """Suspend a node."""
        node = self._nodes.get(node_id)
        if node:
            node.update_state(MeshNodeState.SUSPENDED)
            node.metadata["suspension_reason"] = reason
            node.metadata["suspended_at"] = time.time()
            return True
        return False
    
    def revoke_node(self, node_id: str, reason: str = "") -> bool:
        """Revoke a node (permanent)."""
        node = self._nodes.get(node_id)
        if node:
            node.update_state(MeshNodeState.REVOKED)
            node.metadata["revocation_reason"] = reason
            node.metadata["revoked_at"] = time.time()
            return True
        return False
    
    def get_topology_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current mesh topology."""
        return {
            "mesh_id": self.mesh_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": self._edges,
            "node_count": len(self._nodes),
            "edge_count": sum(len(t) for edges in self._edges.values() for t in edges.values()),
            "states": {s.value: len(self.get_nodes_by_state(s)) for s in MeshNodeState},
            "timestamp": time.time(),
        }
    
    def refresh_node(self, node_id: str) -> Optional[DiscoveryResult]:
        """Refresh a specific node (re-discover)."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        
        source_name = node.metadata.get("discovery_source", "direct_card")
        source = self._sources.get(source_name)
        if not source:
            return None
        
        # Re-discover based on source
        if source_name == "direct_card" and node.endpoint:
            from aetheros_network.discovery import discover_from_url
            try:
                disc = discover_from_url(node.endpoint, organization_id=self.organization_id)
                if not disc.errors:
                    new_node = MeshNode.from_dict(disc.identity)
                    new_node.capabilities = [s["id"] for s in disc.card.get("skills", [])]
                    new_node.last_seen = time.time()
                    self._nodes[node_id] = new_node
                    return DiscoveryResult(node=new_node, source=source_name)
            except Exception as e:
                logger.debug(f"Node refresh failed: {e}")
        
        return None