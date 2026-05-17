# OpenShift Fixture For #188

This fixture captures the OpenShift-specific half of the #188 evidence:

- OpenShift `Route` metadata
- OpenShift monitoring / Thanos route metadata
- current `discover` behavior against a real OpenShift namespace

## Prerequisites

- `oc` installed
- logged in to a real OpenShift cluster with enough access to create a namespace
- optional access to `openshift-monitoring` for Prometheus / Thanos metadata

OpenShift Local / CRC also works, but it needs the CRC binary and a Red Hat pull secret.

## Run

```bash
oc login <api-url> --token=<token>
bash _local/LFX/fixtures/bootstrap-openshift.sh
RUN_ID="$(date +%Y%m%d-%H%M%S)-openshift-fixture"
bash _local/LFX/fixtures/capture-openshift-cluster.sh "$RUN_ID"
```

## Expected Evidence

The useful proof mirrors the kind run:

- `oc get route -n krkn-ps-fixture` shows a real Route host.
- `curl` against that Route returns a real HTTP response.
- `generated/current-discover.yaml` still has no active `health_checks`.
- OpenShift monitoring routes and/or Prometheus CRs are captured for Prometheus discovery design.
