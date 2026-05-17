#!/usr/bin/env bash
# Optional Prometheus setup for checking metric discovery.
#
# This installs kube-prometheus-stack into the `monitoring` namespace. It is
# slower than the base fixture, so only run it when checking PromQL evidence.
set -euo pipefail

NAMESPACE="${MONITORING_NAMESPACE:-monitoring}"
RELEASE_NAME="${MONITORING_RELEASE:-kps}"
CHART_VERSION="${KPS_CHART_VERSION:-}"

if ! command -v helm >/dev/null 2>&1; then
  echo "[install-monitoring] ERROR: helm not found. Install Helm 3 first: https://helm.sh/docs/intro/install/"
  exit 1
fi

echo "[install-monitoring] Adding prometheus-community Helm repo..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo update prometheus-community >/dev/null

echo "[install-monitoring] Installing kube-prometheus-stack into namespace '$NAMESPACE'..."
helm upgrade --install "$RELEASE_NAME" prometheus-community/kube-prometheus-stack \
  --namespace "$NAMESPACE" \
  --create-namespace \
  ${CHART_VERSION:+--version "$CHART_VERSION"} \
  --set grafana.enabled=false \
  --set alertmanager.enabled=false \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --wait --timeout 5m

echo "[install-monitoring] Done. Discoverable resources:"
kubectl get prometheus -n "$NAMESPACE"
kubectl get svc -n "$NAMESPACE" | grep -E "prometheus|operator" || true

cat <<EOF

To port-forward Prometheus from outside the cluster:
  kubectl port-forward -n $NAMESPACE svc/${RELEASE_NAME}-kube-prometheus-prometheus 9090:9090

Set PROMETHEUS_URL=http://localhost:9090 when running with --prometheus.
EOF
