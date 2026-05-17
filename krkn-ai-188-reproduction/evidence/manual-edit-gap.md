# Manual Edit Gap

**Run:** `20260512-124901-kind-fixture`  
**Cluster:** `kind-krkn-ps-fixture`  
**Namespace:** `krkn-ps-fixture`

## Live Cluster Facts

The sandbox cluster contains real Kubernetes resources that map directly to the #188 discovery goals:

- Two running application pods in `krkn-ps-fixture`, each with two containers: `nginx` and `sidecar`.
- Two Services in the fixture namespace:
  - `web-svc`, `ClusterIP`, port `80/TCP`.
  - `web-lb`, `LoadBalancer`, port `80/TCP`, with `EXTERNAL-IP <pending>` on kind.
- Two Ingresses:
  - `web-ing`, class `nginx`, host `web.test.local`, address `localhost`.
  - `orphan-ing`, class `nonexistent`, host `orphan.test.local`, no address.
- One bound PVC: `web-data`, `1Gi`.
- Three Ready nodes.
- No OpenShift Route API in this kind cluster.
- No Prometheus CRD/monitoring stack in this run.

Endpoint reachability was also real, not inferred:

- `curl -i -H 'Host: web.test.local' http://127.0.0.1/` returned `HTTP/1.1 200 OK`.
- `curl -i -H 'Host: web.test.local' http://127.0.0.1/healthz/notfound` returned `HTTP/1.1 404 Not Found`.

## Current Discover Output

The generated config is saved at `generated/current-discover.yaml`.

Parsed summary:

```text
has_health_checks: False
fitness_query: sum(kube_pod_container_status_restarts_total)
cluster_components_namespaces: ['krkn-ps-fixture']
namespace_summary: krkn-ps-fixture pods= 2 services= 2 pvcs= 1 vmis= 0
```

The generated YAML did discover pods, services, PVCs, and nodes, but it did not discover or render Ingresses, IngressClasses, LoadBalancer endpoint status, or health checks.

## Gap 1: Real Ingress Endpoint Exists, But No Health Check Is Generated

Live cluster metadata:

```text
krkn-ps-fixture   web-ing      nginx         web.test.local      localhost   80
krkn-ps-fixture   orphan-ing   nonexistent   orphan.test.local               80
```

Generated config:

```yaml
# health_checks:
#   stop_watcher_on_failure: false
#   applications:
#   - name: cart
#     url: "$HOST/cart/add/1/Watson/1"
```

Manual edit required today:

- User must inspect Ingress/Route/LB resources manually.
- User must decide that `http://web.test.local/` is the real application URL.
- User must uncomment/create `health_checks.applications`.
- User must avoid adding the deliberate `404` path as a passing health check unless `status_code: 404` is intentional.

Dynamic-discovery implication:

- `discover` should read `networking.k8s.io/v1` Ingresses.
- It should detect that `web-ing` references an installed `IngressClass` (`nginx`).
- It should warn on or comment out `orphan-ing` because `ingressClassName: nonexistent` has no matching IngressClass.

## Gap 2: LoadBalancer Service Is Present But Pending

Live cluster metadata:

```text
krkn-ps-fixture   web-lb   LoadBalancer   10.96.243.148   <pending>   80:30892/TCP
```

Manual edit required today:

- User must know that this is not an externally usable endpoint yet.

Dynamic-discovery implication:

- `discover` should inspect `status.loadBalancer.ingress`.
- If empty, it should skip or comment the endpoint rather than producing an active health check.

## Gap 3: Fitness Query Is Static

Generated config:

```yaml
fitness_function:
  query: 'sum(kube_pod_container_status_restarts_total)'
```

Manual edit required today:

- User must know whether this metric exists in their Prometheus.
- User must scope it to the namespace/workload manually.

Dynamic-discovery implication:

- This run did not install Prometheus, so it validates graceful fallback only.
- Follow-up run `20260512-164406-kind-with-monitoring` closes this gap: kube-prometheus-stack exposes `prometheus-operated`, `/api/v1/label/__name__/values` returns 1,372 metric names, Tier-1 SLO metrics are present, and `kube_pod_container_status_restarts_total{namespace="krkn-ps-fixture"}` narrows the static query from 27 total restart series to 4 workload series.

## Gap 4: Scenario Enables Are Static

Generated static scenario block enables only:

```text
pod-scenarios, application-outages, container-scenarios, dns-outage
```

Validator output using the generated config's current scenario block:

```text
['pod_scenarios', 'application_outages', 'container_scenarios', 'dns_outage']
```

Validator output with all scenario flags enabled against the same discovered `ClusterComponents`:

```text
['pod_scenarios', 'application_outages', 'container_scenarios', 'node_cpu_hog', 'node_memory_hog', 'node_io_hog', 'time_scenarios', 'dns_outage', 'syn_flood', 'pvc_scenarios']
```

Manual edit required today:

- User does not get an auto-eligible set in the generated YAML.
- Valid scenarios such as `time_scenarios`, `syn_flood`, and `pvc_scenarios` are not surfaced as eligible by `discover`.
- Destructive node scenarios are valid but should remain default-off with explicit comments or require `--enable-destructive`.

Dynamic-discovery implication:

- `ScenarioFactory.generate_valid_scenarios` can already compute the eligible set from discovered components.
- `discover` should delegate to it rather than duplicating scenario rules.

## Gap 5: Kubernetes Node Interface Discovery Fails OpenShift-Specific Path

Discover logs:

```text
Failed to list node interfaces for node krkn-ps-fixture-worker: [Errno 2] No such file or directory: 'oc'
```

Generated node entries have no `interfaces`, and `free_cpu/free_mem` are `-1.0` because Metrics Server is absent.

Dynamic-discovery implication:

- `network-scenarios` remain invalid on this vanilla kind cluster because interfaces are not populated.
- Generalizing `list_node_interfaces` from `oc debug` to `kubectl debug` remains a useful follow-up or scoped extension.

## Short Takeaway

This run proves the core #188 problem on a real Kubernetes cluster:

> The live cluster exposes a reachable Ingress endpoint, a pending LoadBalancer Service, a bound PVC, two labeled multi-container pods, and three Ready nodes. Current `discover` sees only the basic cluster components and emits no active health checks, a static unscoped fitness query, and static scenario enables. Running the existing scenario validator against the discovered components produces a richer eligible scenario set, proving the dynamic scenario-selection foundation already exists and is simply unused by `discover`.

Prometheus follow-up:

> A second live run with kube-prometheus-stack proves the Prometheus metadata needed for #188 is available: `prometheus-operated` is discoverable, the metric API enumerates 1,372 metric names, and namespace-scoped restart metrics isolate the fixture workload more cleanly than the current unscoped static template query.
