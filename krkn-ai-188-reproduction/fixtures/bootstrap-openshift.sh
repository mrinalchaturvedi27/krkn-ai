#!/usr/bin/env bash
# bootstrap-openshift.sh - apply the OpenShift fixture for #188 metadata capture.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v oc >/dev/null 2>&1; then
  echo "oc is required. Install openshift-cli first."
  exit 1
fi

oc whoami >/dev/null
oc apply -f _local/LFX/fixtures/openshift-ps-fixture.yaml
oc wait -n krkn-ps-fixture deployment/web-app --for=condition=available --timeout=180s

echo "OpenShift fixture is ready."
oc get pods,svc,route,pvc -n krkn-ps-fixture
