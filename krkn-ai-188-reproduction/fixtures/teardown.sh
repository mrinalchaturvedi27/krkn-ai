#!/usr/bin/env bash
# Delete the local kind cluster used by the reproduction.
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER:-krkn-ps-fixture}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$HOME/.kube/${CLUSTER_NAME}.kubeconfig}"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "[teardown] Deleting kind cluster '$CLUSTER_NAME'..."
  kind delete cluster --name "$CLUSTER_NAME"
else
  echo "[teardown] No kind cluster named '$CLUSTER_NAME' found."
fi

if [[ -f "$KUBECONFIG_PATH" ]]; then
  echo "[teardown] Removing kubeconfig at $KUBECONFIG_PATH"
  rm -f "$KUBECONFIG_PATH"
fi

cat <<EOF

[teardown] Done. To remove /etc/hosts entries you may have added:
  sudo sed -i.bak '/web.test.local\\|orphan.test.local/d' /etc/hosts

EOF
