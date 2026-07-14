"""
Fitness-function catalog: a curated library of reliability-oriented PromQL queries
that quantify the impact ("negative behavior") of chaos experiments.

This is the base scaffold. Each :class:`CatalogEntry` is a vetted query template
plus the metadata a future dynamic layer needs (category, required metrics, scope).
Entries emit the existing :class:`krkn_ai.models.config.FitnessFunctionItem` so the
catalog plugs straight into the current fitness pipeline without a parallel type.

The module-level ``BASE_CATALOG`` mirrors the ``scenario_specs`` registry shape in
``krkn_ai/models/scenario/factory.py``.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, field_validator

from krkn_ai.models.cluster_components import ClusterComponents
from krkn_ai.models.config import FitnessFunctionItem, FitnessFunctionType
from krkn_ai.utils.logger import get_logger

logger = get_logger(__name__)


class FitnessCategory(str, Enum):
    """High-level grouping of the failure signal a query measures."""

    availability = "availability"
    resource = "resource"
    node = "node"
    control_plane = "control_plane"


class Scope(str, Enum):
    """How a query is scoped against a discovered cluster."""

    namespace = "namespace"  # filtered by a discovered namespace via the $ns placeholder
    cluster = "cluster"  # cluster-wide, no scoping


class CatalogEntry(BaseModel):
    """A single vetted fitness query template plus discovery metadata.

    ``query_template`` may contain two placeholders:
      - ``$ns``   : substituted with a discovered namespace (namespace-scoped entries).
      - ``$range$``: substituted at runtime by ``FitnessCalculator`` with the run window.
    """

    key: str  # stable identifier, e.g. "pod-restarts"
    category: FitnessCategory
    name: str  # human-readable label for reports / config comments
    query_template: str  # PromQL, single-series (sum/max/avg), may contain $ns / $range$
    type: FitnessFunctionType = FitnessFunctionType.range
    requires: List[str]  # metric names to existence-check (dynamic layer, Week 7)
    scope: Scope = Scope.namespace
    # Per-entry suggested importance. Final weighting (equal split vs severity) is a
    # dynamic-layer policy; this is only a default, not a normalized weight.
    default_weight: float = 1.0

    @field_validator("default_weight")
    @classmethod
    def _weight_range(cls, value: float) -> float:
        # Match FitnessFunctionItem's [0.0, 1.0] constraint.
        if value < 0 or value > 1:
            raise ValueError(f"{value} is outside the range [0.0, 1.0]")
        return value

    def resolved_query(self, namespace: Optional[str] = None) -> str:
        """Fill the ``$ns`` placeholder. ``$range$`` is left for the runtime executor."""
        if namespace:
            return self.query_template.replace("$ns", namespace)
        return self.query_template

    def to_fitness_item(self, namespace: Optional[str] = None) -> FitnessFunctionItem:
        """Emit the existing config type consumed by the fitness pipeline."""
        return FitnessFunctionItem(
            query=self.resolved_query(namespace),
            type=self.type,
            weight=self.default_weight,
        )


# Base catalog — high-impact reliability signals prioritized in the Jul 7 sync
# (system failures, resource spikes, downtime, CPU, OOM). Verified metric names
# and queries: see _local/LFX/Workspace/week-6/prometheus-study.md.
BASE_CATALOG: List[CatalogEntry] = [
    CatalogEntry(
        key="pod-restarts",
        category=FitnessCategory.availability,
        name="Pod container restarts",
        query_template=(
            'sum(increase(kube_pod_container_status_restarts_total'
            '{namespace="$ns"}[$range$]))'
        ),
        requires=["kube_pod_container_status_restarts_total"],
        scope=Scope.namespace,
    ),
    CatalogEntry(
        key="pod-unavailable",
        category=FitnessCategory.availability,
        name="Non-running pods (Pending/Failed/Unknown)",
        query_template=(
            'sum(kube_pod_status_phase'
            '{namespace="$ns", phase=~"Pending|Failed|Unknown"})'
        ),
        requires=["kube_pod_status_phase"],
        scope=Scope.namespace,
    ),
    CatalogEntry(
        # Caveat: last-state gauge — has 0 series until a container's *last*
        # termination reason is OOMKilled (verified empirically on minikube: metric
        # present, but the reason filter yields 0 series when nothing has OOMed).
        key="oom-kills",
        category=FitnessCategory.resource,
        name="Containers last terminated by OOMKilled",
        query_template=(
            'sum(kube_pod_container_status_last_terminated_reason'
            '{namespace="$ns", reason="OOMKilled"})'
        ),
        requires=["kube_pod_container_status_last_terminated_reason"],
        scope=Scope.namespace,
    ),
    CatalogEntry(
        # Caveat: the CFS throttling counters are often dropped by scrape
        # metric-relabeling (verified absent on a minikube kube-prometheus-stack
        # install). The Week-7 metric-existence gate must comment this out when its
        # `requires` metrics are missing; a cpu-usage-rate fallback is a candidate.
        key="cpu-throttle",
        category=FitnessCategory.resource,
        name="Worst-container CPU throttling ratio",
        query_template=(
            "max("
            "rate(container_cpu_cfs_throttled_periods_total"
            '{namespace="$ns", container!=""}[$range$])'
            " / "
            "rate(container_cpu_cfs_periods_total"
            '{namespace="$ns", container!=""}[$range$])'
            ")"
        ),
        requires=[
            "container_cpu_cfs_throttled_periods_total",
            "container_cpu_cfs_periods_total",
        ],
        scope=Scope.namespace,
    ),
    CatalogEntry(
        key="node-pressure",
        category=FitnessCategory.node,
        name="Nodes reporting a pressure condition",
        query_template=(
            "sum(kube_node_status_condition"
            '{condition=~"MemoryPressure|DiskPressure|PIDPressure", status="true"})'
        ),
        requires=["kube_node_status_condition"],
        scope=Scope.cluster,
    ),
    CatalogEntry(
        key="apiserver-errors",
        category=FitnessCategory.control_plane,
        name="API server 5xx error fraction",
        query_template=(
            'sum(rate(apiserver_request_total{code=~"5.."}[$range$]))'
            " / sum(rate(apiserver_request_total[$range$]))"
        ),
        requires=["apiserver_request_total"],
        scope=Scope.cluster,
    ),
]


def get_base_catalog() -> List[CatalogEntry]:
    """Return the base fitness-function catalog."""
    return BASE_CATALOG


# --- Dynamic layer -----------------------------------------------------------
# Turns the static catalog above into cluster-aware fitness queries by probing
# the target's live Prometheus. Mirrors ClusterManager.recommend_health_checks:
# returns a plain list[dict] for the Jinja template (selectattr on "enabled"),
# and never raises so it can't break discovery.

# Concrete window used only to make range queries runnable for shape validation;
# the emitted query keeps $range$ for FitnessCalculator to substitute at runtime.
_VALIDATION_RANGE = "5m"


def _safe_query(query: str) -> str:
    """Guarantee the query always yields one series.

    A label filter that matches no series (e.g. reason="OOMKilled" before any OOM)
    makes the query return empty, which FitnessCalculator treats as a fatal "no
    data" error. `or vector(0)` falls back to a literal 0, so a present-but-empty
    metric reads as 0 at baseline and its real value once chaos triggers it.
    """
    return f"({query}) or vector(0)"


def _validate_shape(prom_client, query: str) -> tuple:
    """Run the query and classify the result. Returns (enabled, reason).

    Three states (learned from the minikube prototype):
      - >1 series  -> not a valid fitness query (needs aggregation).
      - 0 or 1 series -> keep. 0-series-but-present is valid: the metric exists
        but has no matching series yet (e.g. no OOM has happened); it lights up
        under chaos, so it must not be dropped.
    """
    runnable = query.replace("$range$", _VALIDATION_RANGE)
    try:
        result = prom_client.process_query(runnable) or []
    except Exception as error:  # bad syntax, transient failure, etc.
        return False, f"query failed to run: {error}"
    if len(result) > 1:
        return False, f"returns {len(result)} series, needs aggregation (sum/max/avg)"
    return True, ""


def recommend_fitness_queries(
    components: ClusterComponents, prom_client
) -> List[Dict[str, Union[str, bool, float]]]:
    """Suggest cluster-aware fitness queries from the catalog.

    For each catalog entry: gate on metric existence, scope namespace entries to
    each discovered namespace, and validate query shape against live Prometheus.
    Enabled entries are emitted as active fitness items; the rest are rendered as
    commented suggestions with a reason (the probe/active idiom of health checks).
    """
    try:
        available = set(prom_client.prom_cli.all_metrics())
    except Exception as error:
        logger.debug("Could not list Prometheus metrics: %s", error)
        return []

    active_namespaces = [
        ns.name for ns in components.get_active_components().namespaces
    ]

    results: List[Dict[str, Union[str, bool, float]]] = []
    for entry in get_base_catalog():
        missing = [m for m in entry.requires if m not in available]
        targets = active_namespaces if entry.scope is Scope.namespace else [None]

        for namespace in targets:
            # $ns filled, $range$ kept; wrapped so it never returns 0 series at runtime
            query = _safe_query(entry.resolved_query(namespace))
            name = f"{entry.key}:{namespace}" if namespace else entry.key

            if missing:
                enabled, reason = False, "metric(s) not scraped: " + ", ".join(missing)
            else:
                enabled, reason = _validate_shape(prom_client, query)

            results.append(
                {
                    "name": name,
                    "query": query,
                    "type": entry.type.value,
                    "weight": entry.default_weight,
                    "enabled": enabled,
                    "reason": reason,
                }
            )

    # Equal-split weighting across enabled items (weights sum to ~1). Severity-based
    # weighting is a later policy; equal split is the safe default.
    enabled_count = sum(1 for r in results if r["enabled"])
    if enabled_count:
        share = round(1.0 / enabled_count, 4)
        for r in results:
            if r["enabled"]:
                r["weight"] = share

    return results
