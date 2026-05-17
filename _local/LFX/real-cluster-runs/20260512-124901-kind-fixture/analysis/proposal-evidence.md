# Proposal Evidence Snippet

Use this as concise evidence in the proposal, issue comment, or mentor email.

## Real-Cluster Reproduction

I built a reproducible `kind` fixture cluster for #188 with:

- 2 running labeled app pods, each with 2 containers.
- 1 ClusterIP Service.
- 1 pending LoadBalancer Service.
- 1 valid Ingress (`web-ing`, class `nginx`, host `web.test.local`, address `localhost`).
- 1 orphan Ingress (`orphan-ing`, class `nonexistent`) to test IngressClass gating.
- 1 bound PVC.
- 3 Ready nodes.

The valid Ingress endpoint is reachable:

```text
curl -i -H 'Host: web.test.local' http://127.0.0.1/
HTTP/1.1 200 OK
```

Current `discover` output from that same cluster:

```text
has_health_checks: False
fitness_query: sum(kube_pod_container_status_restarts_total)
namespace_summary: krkn-ps-fixture pods= 2 services= 2 pvcs= 1 vmis= 0
```

Scenario validator proof:

```text
Generated static config validates:
['pod_scenarios', 'application_outages', 'container_scenarios', 'dns_outage']

All-enabled validator against the same discovered components returns:
['pod_scenarios', 'application_outages', 'container_scenarios',
 'node_cpu_hog', 'node_memory_hog', 'node_io_hog',
 'time_scenarios', 'dns_outage', 'syn_flood', 'pvc_scenarios']
```

Claim:

> The current `discover` command can discover basic components, but it ignores real reachable Ingress endpoints, emits no active health checks, keeps a static unscoped fitness query, and does not use the existing runtime validator to surface eligible scenarios.

## Prometheus Follow-Up

Second captured run: `20260512-164406-kind-with-monitoring`.

Evidence:

```text
Prometheus Service: monitoring/prometheus-operated, port 9090
Metric names enumerated from /api/v1/label/__name__/values: 1372
Tier-1 metrics present:
  kube_pod_container_status_restarts_total
  kube_deployment_status_replicas_unavailable
  kube_pod_status_phase

count(kube_pod_container_status_restarts_total): 27 series
count(kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"}): 4 series
```

Prometheus claim:

> A live kube-prometheus-stack cluster exposes the metadata needed for smarter PromQL suggestions. The current static query is valid but unscoped; a namespace-scoped suggestion isolates the discovered workload and avoids mixing monitoring/kube-system noise into the fitness signal.
