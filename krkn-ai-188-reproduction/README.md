# krkn-ai #188 Reproduction Notes

This folder contains the small local setup I used while studying `krkn_ai discover` for issue #188.

The goal was simple: create a real Kubernetes cluster, run the current `discover` command, and check whether the generated `krkn-ai.yaml` already includes useful health checks, scenario choices, and Prometheus-backed fitness queries.

## What is included

- `fixtures/`: kind cluster setup and Kubernetes resources used for the test.
- `evidence/parsed-summary.txt`: small summary of the generated YAML.
- `evidence/manual-edit-gap.md`: notes from the base cluster run.
- `evidence/scenario-validator-all-enabled-output.txt`: validator output when all scenarios are enabled against the discovered components.
- `evidence/prometheus-evidence.md`: Prometheus run with kube-prometheus-stack installed.
- `evidence/openshift-blocker.md`: OpenShift test status. This was prepared but not run because no OpenShift context was available.

## Quick start

From this folder:

```bash
bash fixtures/bootstrap.sh
```

For the Prometheus check:

```bash
bash fixtures/bootstrap.sh --with-monitoring
```

After bootstrap, the script prints the kubeconfig path and the `discover` command I used. Run that command from a `krkn-ai` checkout or any environment where `krkn_ai` is installed.

## Main result

The current `discover` command finds pods, services, PVCs, and nodes, but the generated config still has no active `health_checks`, keeps the static fitness query, and uses static scenario enable flags. The fixture also had a reachable Ingress endpoint, which made the health-check gap easy to confirm.
