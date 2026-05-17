#!/usr/bin/env bash
# Install ingress-nginx into the kind cluster and wait for the controller to be ready.
# Uses the kind-recommended manifest, which sets a nodeSelector requiring
# ingress-ready=true on the target node (provided by kind-config.yaml).
set -euo pipefail

INGRESS_NGINX_MANIFEST="${INGRESS_NGINX_MANIFEST:-https://kind.sigs.k8s.io/examples/ingress/deploy-ingress-nginx.yaml}"

echo "[install-ingress] Applying ingress-nginx manifest: $INGRESS_NGINX_MANIFEST"
kubectl apply -f "$INGRESS_NGINX_MANIFEST"

echo "[install-ingress] Waiting for ingress-nginx controller to be Ready (up to 180s)..."
# Give the Deployment a moment to appear before waiting on it.
sleep 5
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s

echo "[install-ingress] ingress-nginx is ready."
echo "[install-ingress] Available IngressClasses:"
kubectl get ingressclass
