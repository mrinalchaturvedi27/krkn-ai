#!/usr/bin/env bash
# Create the local kind cluster used for the krkn-ai discover reproduction.
#
# Usage:
#   bash fixtures/bootstrap.sh
#   bash fixtures/bootstrap.sh --with-monitoring
#
# Re-running the script reuses the cluster and reapplies the fixture.
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER:-krkn-ps-fixture}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$HOME/.kube/${CLUSTER_NAME}.kubeconfig}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WITH_MONITORING=0
for arg in "$@"; do
  case "$arg" in
    --with-monitoring) WITH_MONITORING=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

for tool in kind kubectl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: '$tool' is not installed or not in PATH."
    exit 1
  fi
done

mkdir -p "$(dirname "$KUBECONFIG_PATH")"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "[bootstrap] Reusing kind cluster '$CLUSTER_NAME'."
  kind export kubeconfig --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH"
else
  echo "[bootstrap] Creating kind cluster '$CLUSTER_NAME'."
  kind create cluster \
    --name "$CLUSTER_NAME" \
    --config "$SCRIPT_DIR/kind-config.yaml" \
    --kubeconfig "$KUBECONFIG_PATH"
fi

export KUBECONFIG="$KUBECONFIG_PATH"
kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null

echo "[bootstrap] Installing ingress-nginx."
bash "$SCRIPT_DIR/install-ingress.sh"

echo "[bootstrap] Applying fixture resources."
kubectl apply -f "$SCRIPT_DIR/krkn-ps-fixture.yaml"

echo "[bootstrap] Waiting for web-app pods to become Ready."
kubectl wait --namespace krkn-ps-fixture \
  --for=condition=ready pod \
  --selector=app=web \
  --timeout=120s || {
    echo "[bootstrap] Web pods did not become Ready in time. Useful checks:"
    echo "    kubectl get pods -n krkn-ps-fixture"
    echo "    kubectl describe pods -n krkn-ps-fixture -l app=web"
  }

if [[ "$WITH_MONITORING" -eq 1 ]]; then
  echo "[bootstrap] Installing kube-prometheus-stack. This can take a few minutes."
  bash "$SCRIPT_DIR/install-monitoring.sh"
fi

cat <<EOF

[bootstrap] Done.

Cluster:     kind-${CLUSTER_NAME}
Kubeconfig:  $KUBECONFIG_PATH

Next steps:

  export KUBECONFIG="$KUBECONFIG_PATH"
  kubectl get all -n krkn-ps-fixture

  # One-time host entry for the Ingress test:
  echo "127.0.0.1 web.test.local orphan.test.local" | sudo tee -a /etc/hosts

  # Confirm the reachable Ingress:
  curl -i http://web.test.local/

  # From a krkn-ai checkout, run the current discover command:
  conda run -n conda-krkn python -c "from krkn_ai.cli.cmd import main; main()" discover \\
    --kubeconfig "\$KUBECONFIG" \\
    --namespace "krkn-ps-fixture" \\
    --output /tmp/current-discover.yaml \\
    --verbose

Teardown:
  bash $SCRIPT_DIR/teardown.sh

EOF
