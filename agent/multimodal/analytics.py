"""Advanced Analytics & Business Intelligence (Phase 67).

Enterprise analytics and BI capabilities:
- Data warehouse integration
- OLAP cube analysis
- Real-time streaming analytics
- Machine learning feature store
- Custom report builder
- Data lineage tracking
- Data quality monitoring
- Ad-hoc query engine
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

import numpy as np

from agent.multimodal.production import MetricsCollector, LRUCache

logger = logging.getLogger(__name__)


class DataType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"


class AggregationType(Enum):
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"
    PERCENTILE = "percentile"
    STDDEV = "stddev"
    VARIANCE = "variance"


class Granularity(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class Column:
    """Column definition for datasets."""
    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Schema:
    """Dataset schema."""
    schema_id: str
    name: str
    columns: List[Column] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    version: int = 1


@dataclass
class Dataset:
    """Dataset definition."""
    dataset_id: str
    name: str
    description: str
    schema: Schema
    source: str  # Source system
    location: str  # Storage location
    format: str = "parquet"  # parquet, csv, json, avro, orc
    partitioning: List[str] = field(default_factory=list)
    partitioning_granularity: Granularity = Granularity.DAY
    retention_days: int = 365
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Query:
    """Analytical query."""
    query_id: str
    name: str
    sql: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    cache_ttl_seconds: int = 300
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class QueryResult:
    """Query execution result."""
    result_id: str
    query_id: str
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    cached: bool = False
    error: Optional[str] = None


class DataWarehouse:
    """Data warehouse abstraction layer."""

    def __init__(self, connection_string: str = ""):
        self.connection_string = connection_string
        self._datasets: Dict[str, Dataset] = {}
        self._schemas: Dict[str, Schema] = {}
        self._queries: Dict[str, Query] = {}
        self._cache = LRUCache(maxsize=1000, ttl=300)
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("data_warehouse")

    def register_dataset(self, dataset: Dataset) -> bool:
        with self._lock:
            if dataset.dataset_id in self._datasets:
                return False
            self._datasets[dataset.dataset_id] = dataset
            self._schemas[dataset.schema.schema_id] = dataset.schema
            return True

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        with self._lock:
            return self._datasets.get(dataset_id)

    def list_datasets(self, tags: Optional[List[str]] = None) -> List[Dataset]:
        with self._lock:
            datasets = list(self._datasets.values())
            if tags:
                datasets = [d for d in datasets if any(t in d.tags for t in tags)]
            return datasets

    def execute_query(self, query: Query, params: Optional[Dict] = None) -> QueryResult:
        """Execute analytical query."""
        start = time.time()
        query_id = query.query_id

        # Check cache
        cache_key = f"{query_id}:{hash(str(params))}"
        cached = self._cache.get(cache_key)
        if cached:
            result = cached
            result.cached = True
            result.execution_time_ms = (time.time() - start) * 1000
            return result

        # Execute query (simplified - would use actual DB in production)
        try:
            # This would connect to actual warehouse (Snowflake, BigQuery, Redshift, etc.)
            # For now, return mock data
            columns = ["id", "timestamp", "value", "category"]
            rows = [
                [i, time.time() - i * 3600, np.random.rand() * 100, f"cat_{i % 5}"]
                for i in range(100)
            ]

            result = QueryResult(
                result_id=f"res_{uuid.uuid4().hex[:8]}",
                query_id=query_id,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=(time.time() - start) * 1000,
                cached=False,
            )

            # Cache result
            self._cache.set(cache_key, result)

            self.metrics.counter("queries_executed", labels={"query": query.name})
            self.metrics.histogram("query_latency_ms", (time.time() - start) * 1000)

            return result

        except Exception as e:
            return QueryResult(
                result_id=f"res_{uuid.uuid4().hex[:8]}",
                query_id=query_id,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    def register_query(self, query: Query) -> bool:
        with self._lock:
            if query.query_id in self._queries:
                return False
            self._queries[query.query_id] = query
            return True

    def get_query(self, query_id: str) -> Optional[Query]:
        with self._lock:
            return self._queries.get(query_id)


class OLAPCube:
    """OLAP cube for multi-dimensional analysis."""

    def __init__(self, name: str, dimensions: List[str], measures: List[str]):
        self.name = name
        self.dimensions = dimensions
        self.measures = measures
        self._data: Dict[str, Dict] = {}  # dimension key -> measure values
        self._lock = threading.Lock()

    def add_fact(self, dimensions: Dict[str, str], measures: Dict[str, float]) -> None:
        """Add a fact to the cube."""
        key = self._make_key(dimensions)
        with self._lock:
            if key not in self._data:
                self._data[key] = {m: 0.0 for m in self.measures}
            for m, v in measures.items():
                if m in self.measures:
                    self._data[key][m] += v

    def query(
        self,
        dimensions: List[str],
        measures: List[str],
        filters: Optional[Dict[str, str]] = None,
        aggregation: AggregationType = AggregationType.SUM,
    ) -> List[Dict]:
        """Query the cube."""
        with self._lock:
            results = []
            for dims, values in self._data.items():
                # Apply filters
                if filters:
                    match = True
                    for k, v in filters.items():
                        if k in dims and dims[k] != v:
                            match = False
                            break
                    if not match:
                        continue

                # Extract requested dimensions
                result = {d: dims.get(d) for d in dimensions if d in dims}
                for m in measures:
                    if m in values:
                        result[m] = values[m]
                results.append(result)

        return results

    def _make_key(self, dimensions: Dict[str, str]) -> str:
        return "|".join(f"{k}={v}" for k, v in sorted(dimensions.items()))

    def rollup(self, dimensions: List[str]) -> List[Dict]:
        """Roll up to higher granularity."""
        results = []
        with self._lock:
            for dims, values in self._data.items():
                reduced = {d: dims[d] for d in dimensions if d in dims}
                key = self._make_key(reduced)
                if key not in self._data:
                    self._data[key] = {m: 0.0 for m in self.measures}
                for m in self.measures:
                    if m in values:
                        self._data[key][m] += values[m]
        return self.query(dimensions, self.measures)


class StreamingAnalytics:
    """Real-time streaming analytics engine."""

    def __init__(self, window_size_seconds: int = 300):
        self.window_size = window_size_seconds
        self._windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("streaming_analytics")

    def ingest(self, stream_id: str, event: Dict[str, Any]) -> None:
        """Ingest event into stream."""
        timestamp = event.get("timestamp", time.time())
        with self._lock:
            self._windows[stream_id].append((timestamp, event))

    def windowed_aggregation(
        self,
        stream_id: str,
        field: str,
        aggregation: AggregationType,
        window_seconds: Optional[int] = None,
    ) -> float:
        """Compute windowed aggregation."""
        window = window_seconds or self.window_size
        cutoff = time.time() - window

        with self._lock:
            events = self._windows.get(stream_id, deque())
            values = [e[1].get(field) for _, e in events if e[0] >= cutoff and field in e[1]]

        if not values:
            return 0.0

        if aggregation == AggregationType.SUM:
            return sum(v for v in values if v is not None)
        elif aggregation == AggregationType.COUNT:
            return len([v for v in values if v is not None])
        elif aggregation == AggregationType.AVG:
            vals = [v for v in values if v is not None]
            return sum(vals) / len(vals) if vals else 0.0
        elif aggregation == AggregationType.MIN:
            return min(v for v in values if v is not None)
        elif aggregation == AggregationType.MAX:
            return max(v for v in values if v is not None)
        elif aggregation == AggregationType.COUNT_DISTINCT:
            return len(set(v for v in values if v is not None))

        return 0.0

    def get_window_stats(self, stream_id: str, window_seconds: Optional[int] = None) -> Dict:
        """Get statistics for a time window."""
        window = window_seconds or self.window_size
        cutoff = time.time() - window

        with self._lock:
            events = self._windows.get(stream_id, deque())
            recent = [e for t, e in events if t >= cutoff]

            if not recent:
                return {"count": 0}

            return {
                "count": len(recent),
                "time_range": [recent[0][0], recent[-1][0]] if recent else None,
                "fields": list(set().union(*[e.keys() for _, e in recent])),
            }


class FeatureStore:
    """Machine learning feature store."""

    def __init__(self, storage_backend: Any):
        self.storage = storage_backend
        self._features: Dict[str, Dict] = {}
        self._feature_groups: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("feature_store")

    def register_feature(
        self,
        feature_name: str,
        entity_type: str,
        feature_type: DataType,
        description: str = "",
        tags: List[str] = [],
        owner: str = "",
    ) -> bool:
        with self._lock:
            if feature_name in self._features:
                return False
            self._features[feature_name] = {
                "name": feature_name,
                "entity_type": entity_type,
                "type": feature_type,
                "description": description,
                "tags": tags,
                "owner": owner,
                "created_at": time.time(),
                "version": 1,
            }
            return True

    def get_feature(self, feature_name: str) -> Optional[Dict]:
        with self._lock:
            return self._features.get(feature_name)

    def put_features(
        self,
        entity_id: str,
        entity_type: str,
        features: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> bool:
        """Write feature values for an entity."""
        key = f"{entity_type}:{entity_id}"
        ts = timestamp or time.time()

        # Store in backend
        data = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "features": features,
            "timestamp": ts,
        }

        # In production, would write to feature store (Feast, Hopsworks, etc.)
        # For now, cache locally
        with self._lock:
            if key not in self._features:
                self._features[key] = {}
            self._features[key][str(ts)] = data

        self.metrics.counter("features_written", labels={"entity_type": entity_type})
        return True

    def get_features(
        self,
        entity_ids: List[str],
        entity_type: str,
        feature_names: List[str],
        timestamp: Optional[float] = None,
    ) -> Dict[str, Dict]:
        """Get feature values for entities."""
        ts = timestamp or time.time()
        results = {}

        with self._lock:
            for entity_id in entity_ids:
                key = f"{entity_type}:{entity_id}"
                if key in self._features:
                    # Find latest timestamp <= requested
                    timestamps = sorted(self._features[key].keys())
                    valid_ts = [t for t in timestamps if float(t) <= ts]
                    if valid_ts:
                        latest = self._features[key][valid_ts[-1]]
                        features = {f: latest["features"].get(f) for f in feature_names}
                        results[entity_id] = features

        self.metrics.counter("features_read", labels={"entity_type": entity_type})
        return results

    def create_feature_group(
        self,
        group_name: str,
        feature_names: List[str],
        entity_type: str,
        description: str = "",
    ) -> bool:
        with self._lock:
            if group_name in self._feature_groups:
                return False
            self._feature_groups[group_name] = feature_names
            return True

    def get_feature_group(self, group_name: str) -> Optional[List[str]]:
        with self._lock:
            return self._feature_groups.get(group_name)


class ReportBuilder:
    """Custom report builder with drag-and-drop style API."""

    def __init__(self, data_warehouse: DataWarehouse):
        self.warehouse = data_warehouse
        self._reports: Dict[str, Dict] = {}
        self._templates: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_report(
        self,
        report_id: str,
        name: str,
        description: str,
        layout: List[Dict],
        parameters: Optional[List[Dict]] = None,
    ) -> bool:
        with self._lock:
            if report_id in self._reports:
                return False
            self._reports[report_id] = {
                "report_id": report_id,
                "name": name,
                "description": description,
                "layout": layout,
                "parameters": parameters or [],
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            return True

    def generate_report(
        self,
        report_id: str,
        parameters: Dict[str, Any],
        format: str = "json",  # json, html, pdf, csv
    ) -> Dict[str, Any]:
        """Generate report with given parameters."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return {"error": "Report not found"}

        results = {
            "report_id": report_id,
            "name": report["name"],
            "generated_at": time.time(),
            "format": format,
            "sections": [],
        }

        # Execute queries for each layout element
        for element in report["layout"]:
            element_type = element.get("type")
            query_id = element.get("query_id")
            params = element.get("params", {})

            # Merge parameters
            merged_params = {**element.get("params", {}), **parameters}

            if query_id:
                query = self.warehouse.get_query(query_id)
                if query:
                    result = self.warehouse.execute_query(query, merged_params)
                    section = {
                        "type": element_type,
                        "title": element.get("title", ""),
                        "data": {
                            "columns": result.columns,
                            "rows": result.rows[:1000],  # Limit rows
                            "row_count": result.row_count,
                        },
                        "metadata": {
                            "query_id": query_id,
                            "execution_time_ms": result.execution_time_ms,
                        },
                    }
                    results["sections"].append(section)

        # Format output
        if format == "json":
            return results
        elif format == "csv":
            # Convert to CSV
            return {"content": "csv_data", "format": "csv"}
        elif format == "html":
            return {"content": "html_report", "format": "html"}

        return results

    def create_template(
        self,
        template_id: str,
        name: str,
        layout: List[Dict],
        parameters: List[Dict],
    ) -> bool:
        with self._lock:
            if template_id in self._templates:
                return False
            self._templates[template_id] = {
                "template_id": template_id,
                "name": name,
                "layout": layout,
                "parameters": parameters,
            }
            return True

    def instantiate_from_template(
        self,
        template_id: str,
        report_id: str,
        name: str,
        overrides: Optional[Dict] = None,
    ) -> bool:
        with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return False

            layout = template["layout"]
            params = template["parameters"]
            if overrides:
                for param in params:
                    if param["name"] in overrides:
                        param["default"] = overrides[param["name"]]

            return self.create_report(report_id, overrides.get("name", "Untitled"), "", layout, params)


class DataLineageTracker:
    """Tracks data lineage across transformations."""

    def __init__(self):
        self._nodes: Dict[str, Dict] = {}  # Dataset/process IDs
        self._edges: List[Dict] = []  # lineage edges
        self._lock = threading.Lock()

    def register_node(
        self,
        node_id: str,
        node_type: str,  # dataset, process, model, report
        name: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        with self._lock:
            if node_id in self._nodes:
                return False
            self._nodes[node_id] = {
                "node_id": node_id,
                "type": node_type,
                "name": name,
                "metadata": metadata or {},
                "created_at": time.time(),
            }
            return True

    def add_lineage(
        self,
        source_id: str,
        target_id: str,
        transformation: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        with self._lock:
            if source_id not in self._nodes or target_id not in self._nodes:
                return False

            edge = {
                "source": source_id,
                "target": target_id,
                "transformation": transformation,
                "metadata": metadata or {},
                "created_at": time.time(),
            }
            self._edges.append(edge)
            return True

    def get_upstream(self, node_id: str, max_depth: int = 10) -> List[Dict]:
        """Get upstream dependencies."""
        with self._lock:
            visited = set()
            result = []

            def traverse(node_id: str, depth: int):
                if depth > max_depth or node_id in visited:
                    return
                visited.add(node_id)
                for edge in self._edges:
                    if edge["target"] == node_id:
                        source = self._nodes.get(edge["source"])
                        if source:
                            result.append({
                                "node": source,
                                "transformation": edge["transformation"],
                                "depth": depth,
                            })
                            traverse(edge["source"], depth + 1)

            traverse(node_id, 0)
            return result

    def get_downstream(self, node_id: str, max_depth: int = 10) -> List[Dict]:
        """Get downstream dependents."""
        with self._lock:
            visited = set()
            result = []

            def traverse(node_id: str, depth: int):
                if depth > max_depth or node_id in visited:
                    return
                visited.add(node_id)
                for edge in self._edges:
                    if edge["source"] == node_id:
                        target = self._nodes.get(edge["target"])
                        if target:
                            result.append({
                                "node": target,
                                "transformation": edge["transformation"],
                                "depth": depth,
                            })
                            traverse(edge["target"], depth + 1)

            traverse(node_id, 0)
            return result

    def get_impact_analysis(self, node_id: str) -> Dict:
        """Analyze impact of changes to a node."""
        upstream = self.get_upstream(node_id)
        downstream = self.get_downstream(node_id)

        return {
            "node_id": node_id,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "upstream": upstream[:50],  # Limit
            "downstream": downstream[:50],
            "risk_level": "high" if len(downstream) > 10 else "medium" if len(downstream) > 5 else "low",
        }


class DataQualityMonitor:
    """Data quality monitoring and alerting."""

    def __init__(self, data_warehouse: DataWarehouse):
        self.warehouse = data_warehouse
        self._rules: Dict[str, Dict] = {}
        self._results: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("data_quality")

    def add_rule(
        self,
        rule_id: str,
        name: str,
        dataset_id: str,
        check_type: str,  # null_check, range_check, uniqueness, pattern, custom_sql
        config: Dict,
        severity: str = "warning",
        schedule: str = "0 * * * *",  # cron
    ) -> bool:
        with self._lock:
            if rule_id in self._rules:
                return False
            self._rules[rule_id] = {
                "rule_id": rule_id,
                "name": name,
                "dataset_id": dataset_id,
                "check_type": check_type,
                "config": config,
                "severity": severity,
                "schedule": schedule,
                "enabled": True,
                "created_at": time.time(),
            }
            return True

    def run_check(self, rule_id: str) -> Dict:
        """Run a data quality check."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if not rule:
                return {"error": "Rule not found"}

        dataset = self.warehouse.get_dataset(rule["dataset_id"])
        if not dataset:
            return {"error": "Dataset not found"}

        # Execute check based on type
        check_type = rule["check_type"]
        config = rule["config"]

        if check_type == "null_check":
            result = self._check_nulls(config)
        elif check_type == "range_check":
            result = self._check_range(config)
        elif check_type == "uniqueness":
            result = self._check_uniqueness(config)
        elif check_type == "pattern":
            result = self._check_pattern(config)
        elif check_type == "custom_sql":
            result = self._run_custom_sql(config)
        else:
            return {"error": f"Unknown check type: {check_type}"}

        result["rule_id"] = rule_id
        result["rule_name"] = name
        result["severity"] = rule["severity"]
        result["timestamp"] = time.time()

        # Store result
        with self._lock:
            self._results[rule_id].append(result)

        # Update metrics
        if not result.get("passed", True):
            self.metrics.counter("dq_failures", labels={"rule": rule_id})

        return result

    def _check_nulls(self, config: Dict) -> Dict:
        column = config.get("column")
        threshold = config.get("threshold", 0.0)  # Max null percentage
        # Would query actual data
        return {"passed": True, "null_percentage": 0.0, "details": "Mock result"}

    def _check_range(self, config: Dict) -> Dict:
        return {"passed": True, "details": "Mock result"}

    def _check_uniqueness(self, config: Dict) -> Dict:
        return {"passed": True, "details": "Mock result"}

    def _check_pattern(self, config: Dict) -> Dict:
        return {"passed": True, "details": "Mock result"}

    def _run_custom_sql(self, config: Dict) -> Dict:
        return {"passed": True, "details": "Mock result"}

    def get_recent_results(self, rule_id: str, limit: int = 100) -> List[Dict]:
        with self._lock:
            return self._results.get(rule_id, [])[-limit:]

    def get_failing_rules(self) -> List[Dict]:
        with self._lock:
            failing = []
            for rule_id, results in self._results.items():
                if results and not results[-1].get("passed", True):
                    rule = self._rules.get(rule_id)
                    if rule:
                        failing.append({
                            "rule_id": rule_id,
                            "name": rule["name"],
                            "severity": rule["severity"],
                            "last_result": results[-1],
                        })
            return failing


# Convenience functions
def create_dataset(
    name: str,
    description: str,
    columns: List[Dict],
    source: str,
    location: str,
) -> Dataset:
    columns_obj = [
        Column(
            name=c["name"],
            data_type=DataType(c["type"]),
            nullable=c.get("nullable", True),
            primary_key=c.get("primary_key", False),
            description=c.get("description", ""),
        )
        for c in columns
    ]

    schema = Schema(
        schema_id=f"schema_{uuid.uuid4().hex[:8]}",
        name=f"{name}_schema",
        columns=columns_obj,
    )

    return Dataset(
        dataset_id=f"ds_{uuid.uuid4().hex[:8]}",
        name=name,
        description=description,
        schema=schema,
        source=source,
        location=location,
    )


def create_query(name: str, sql: str, params: Optional[Dict] = None) -> Query:
    return Query(
        query_id=f"q_{uuid.uuid4().hex[:8]}",
        name=name,
        sql=sql,
        parameters=params or {},
    )


def create_olap_cube(name: str, dimensions: List[str], measures: List[str]) -> OLAPCube:
    return OLAPCube(name, dimensions, measures)


def create_feature_store(storage_backend: Any) -> FeatureStore:
    return FeatureStore(storage_backend)


def create_report_builder(warehouse: DataWarehouse) -> ReportBuilder:
    return ReportBuilder(warehouse)


def create_lineage_tracker() -> DataLineageTracker:
    return DataLineageTracker()


def create_quality_monitor(warehouse: DataWarehouse) -> DataQualityMonitor:
    return DataQualityMonitor(warehouse)