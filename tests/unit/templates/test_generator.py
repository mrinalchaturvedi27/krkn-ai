"""Tests for templates/generator.py scenario rendering."""

import yaml

from krkn_ai.templates.generator import (
    create_krkn_ai_template,
    STATIC_SCENARIO_ENABLES,
)

KUBECONFIG = "/tmp/kubeconfig"
DATA = {"namespaces": []}


def _scenario_block(rendered: str) -> dict:
    """Parse the rendered file and return the scenario mapping {key: enable}."""
    doc = yaml.safe_load(rendered)
    return {k: v["enable"] for k, v in doc["scenario"].items()}


class TestScenarioRendering:
    def test_none_falls_back_to_static_defaults(self):
        """dynamic=None renders the exact current static enables (byte-identical)."""
        rendered = create_krkn_ai_template(KUBECONFIG, DATA, None)
        enables = _scenario_block(rendered)
        expected = {k: (v == "true") for k, v in STATIC_SCENARIO_ENABLES.items()}
        assert enables == expected
        # Sanity: the 4 historically-enabled scenarios are on.
        assert enables["pod-scenarios"] is True
        assert enables["dns-outage"] is True
        assert enables["pvc-scenarios"] is False

    def test_no_dynamic_arg_matches_none(self):
        """Omitting dynamic behaves identically to dynamic=None (back-compat)."""
        assert create_krkn_ai_template(KUBECONFIG, DATA) == create_krkn_ai_template(
            KUBECONFIG, DATA, None
        )

    def test_set_enables_only_listed_scenarios(self):
        """A set turns on exactly the listed scenarios, all others off."""
        rendered = create_krkn_ai_template(
            KUBECONFIG, DATA, {"scenarios": {"pvc-scenarios", "node-cpu-hog"}}
        )
        enables = _scenario_block(rendered)
        assert enables["pvc-scenarios"] is True
        assert enables["node-cpu-hog"] is True
        assert enables["pod-scenarios"] is False
        assert sum(enables.values()) == 2

    def test_empty_set_disables_all(self):
        """An empty set disables every scenario."""
        rendered = create_krkn_ai_template(KUBECONFIG, DATA, {"scenarios": set()})
        enables = _scenario_block(rendered)
        assert not any(enables.values())

    def test_rendered_output_is_valid_yaml_and_lowercase(self):
        """Output parses as YAML and uses lowercase booleans (not Python True/False)."""
        rendered = create_krkn_ai_template(
            KUBECONFIG, DATA, {"scenarios": {"pod-scenarios"}}
        )
        assert "enable: true" in rendered
        assert "enable: True" not in rendered
        yaml.safe_load(rendered)  # does not raise
