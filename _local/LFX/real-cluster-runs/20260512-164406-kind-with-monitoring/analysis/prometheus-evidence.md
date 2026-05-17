# Prometheus / PromQL Evidence

**Run:** `20260512-164406-kind-with-monitoring`
**Cluster:** `kind` cluster `krkn-ps-fixture` + `kube-prometheus-stack`

This run closes the remaining Prometheus / PromQL metadata gap from the first real-cluster run. The same fixture cluster was kept alive, `kube-prometheus-stack` was installed into namespace `monitoring`, Prometheus was port-forwarded on `localhost:9090`, and the Prometheus HTTP API was queried directly.

## Prometheus Is Discoverable

Captured Kubernetes resources show a real Prometheus instance and stable Services:

```text
NAMESPACE    NAME                                   VERSION              DESIRED   READY   RECONCILED   AVAILABLE
monitoring   kps-kube-prometheus-stack-prometheus   v3.11.3-distroless   1         1       True         True
```

Relevant Services from `cluster/services-wide.txt`:

```text
monitoring  kps-kube-prometheus-stack-prometheus  ClusterIP  10.96.191.114  <none>  9090/TCP,8080/TCP
monitoring  prometheus-operated                   ClusterIP  None           <none>  9090/TCP
```

`prometheus-operated` gives the proposal a concrete well-known Service fallback for vanilla kube-prometheus-stack clusters.

## Available Metrics

The metric-name enumeration endpoint returned successfully:

```text
GET /api/v1/label/__name__/values
status: success
metric_count: 1372
```

Tier-1 Kubernetes SLO candidates are present:

```text
kube_pod_container_status_restarts_total        true
kube_deployment_status_replicas_unavailable     true
kube_pod_status_phase                           true
container_cpu_usage_seconds_total               true
container_memory_working_set_bytes              true
```

HTTP-specific application metrics are absent on this simple nginx fixture:

```text
http_requests_total                     false
nginx_ingress_controller_requests       false
```

That absence is useful negative evidence: a PromQL suggestion engine should rank Kubernetes-native SLO metrics first here, not invent HTTP queries that the cluster cannot answer.

## Namespace-Scoped Series

The fixture namespace has real restart metric series:

```text
GET /api/v1/series
match[]=kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"}

status: success
series_count: 4
```

The four series are exactly the expected shape: 2 pods x 2 containers (`nginx`, `sidecar`) from the `web-app` Deployment.

## Static Query Versus Scoped Query

Current generated config still emits:

```yaml
fitness_function:
  query: sum(kube_pod_container_status_restarts_total)
```

Prometheus confirms that query is valid, but broad:

```text
sum(kube_pod_container_status_restarts_total)                                  -> 44
count(kube_pod_container_status_restarts_total)                                -> 27 series
sum(kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"})     -> 8
count(kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"})   -> 4 series
```

The unscoped default includes kube-system / monitoring / fixture data together. The namespace-scoped variant isolates the workload that `discover --namespace krkn-ps-fixture` was asked to target.

For the short-window chaos SLO variant proposed in the blueprint:

```text
sum(increase(kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"}[5m])) -> 0
```

This is the expected steady-state value: the metric exists, series exist, and no new restarts occurred during the 5-minute window.

## Current Discover Output Still Does Not Use This Metadata

Even with Prometheus installed and reachable, the current generated config remains static:

```text
has_health_checks: False
fitness_query: sum(kube_pod_container_status_restarts_total)
```

So Gap 3 is now empirically demonstrated both ways:

- The data needed for a better suggestion is available from the live cluster.
- Current `discover` does not inspect or use it.

## Conclusion

The proposal's Prometheus path is grounded in real metadata now: kube-prometheus-stack exposes a discoverable `prometheus-operated` Service, Prometheus enumerates 1,372 metric names, Tier-1 Kubernetes SLO metrics are present, and a namespace-scoped query produces cleaner workload-specific signal than the current unscoped static template query.
