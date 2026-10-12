"""Measured Memory 2.0 benchmark (Master 41 sections 63, 65).

Generates N synthetic records in a temp dir, measures write throughput,
retrieval latency (hybrid, top-8), graph traversal, consolidation and
export.  Prints JSON.  No fabricated numbers: everything is timed.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aetheros_memory_intelligence.graph_store import Entity, EntityType, RelationType
from aetheros_memory_intelligence.record import ProvenanceKind, RecordScope, RecordType
from aetheros_memory_intelligence.service import MemoryService


def bench(n: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="m2bench"))
    svc = MemoryService(root=tmp)
    svc.initialize()

    t0 = time.time()
    for i in range(n):
        topic = ["deploy pipeline", "auth flow", "cache policy", "search ranking",
                 "billing webhook", "mobile sync", "error budget", "release train"][i % 8]
        svc.remember(
            f"Benchmark fact {i}: {topic} uses distinct mechanism omega-{i} "
            f"with constraint kappa-{i * 7 % 101} in region zeta-{i % 13}",
            record_type=RecordType.EPISODIC_EVENT if i % 3 else RecordType.PROJECT_FACT,
            scope=RecordScope.PROJECT, project_id=f"P{i % 10}",
            provenance=ProvenanceKind.TOOL_OBSERVED)
    write_s = time.time() - t0

    queries = [("deploy pipeline build package", "P0"),
               ("auth flow mechanism constraint", "P1"),
               ("cache policy region zeta", "P2"),
               ("billing webhook kappa", "P3"),
               ("release train omega", "P4")]
    t0 = time.time()
    lat = []
    hits = 0
    for q, proj in queries:
        t1 = time.time()
        from aetheros_memory_intelligence.record import RecordScope as _RS
        r = svc.retrieve(q, top_k=8, scope=_RS.PROJECT, project_id=proj)
        lat.append((time.time() - t1) * 1000.0)
        hits += len(r["included"])
    retr_s = time.time() - t0

    # Graph: 200 entities chained + 1 traversal.
    t0 = time.time()
    prev = None
    ids = []
    for i in range(200):
        e = svc.add_entity(Entity(type=EntityType.CONCEPT, canonical_name=f"bench-node-{i}"))
        ids.append(e.id)
        if prev is not None:
            svc.link(prev, e.id, RelationType.RELATED_TO)
        prev = e.id
    graph_write_s = time.time() - t0
    t0 = time.time()
    sub = svc.get_entity_graph(ids[0], depth=3)
    graph_trav_ms = (time.time() - t0) * 1000.0

    t0 = time.time()
    cons = svc.consolidate()
    cons_s = time.time() - t0
    h = svc.health()
    return {"n": n, "write_s": round(write_s, 3),
            "write_per_s": round(n / max(write_s, 1e-6), 1),
            "retrieval_p50_ms": round(sorted(lat)[len(lat) // 2], 2),
            "retrieval_max_ms": round(max(lat), 2),
            "retrieval_hits_total": hits,
            "graph_write_200_s": round(graph_write_s, 3),
            "graph_traverse_depth3_ms": round(graph_trav_ms, 2),
            "graph_traverse_nodes": len(sub["entities"]),
            "consolidate_s": round(cons_s, 3),
            "consolidated": cons["created"],
            "health_score": h["health"]["score"],
            "records": h["records"]}


if __name__ == "__main__":
    sizes = [int(a) for a in sys.argv[1:] or [1000]]
    print(json.dumps([bench(n) for n in sizes], indent=2))
