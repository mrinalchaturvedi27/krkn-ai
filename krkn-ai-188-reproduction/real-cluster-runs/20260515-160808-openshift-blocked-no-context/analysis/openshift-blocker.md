# OpenShift Experiment Status

Run: `20260515-160808-openshift-blocked-no-context`

The OpenShift experiment did not run yet because no OpenShift kubeconfig/context is configured locally. `oc` is installed and the fixture/capture scripts are ready.

Observed blocker:

```text
error: Missing or incomplete configuration info.  Please point to an existing, complete config file:


  1. Via the command-line flag --kubeconfig
  2. Via the KUBECONFIG environment variable
  3. In your home directory as ~/.kube/config

To view or setup config directly use the 'config' command.

```

Next requirement: run `oc login <api-url> --token=<token>` or install/start OpenShift Local with a Red Hat pull secret, then run `_local/LFX/fixtures/bootstrap-openshift.sh` and `_local/LFX/fixtures/capture-openshift-cluster.sh`.
