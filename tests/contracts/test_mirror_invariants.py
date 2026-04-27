"""Tests for §3.3 structural-mirror invariants — SubscriptionHandle and plugin manifest."""

import inspect
import textwrap

import pytest


class TestSubscriptionHandleMirror:
    """§3.3, S3 — SubscriptionHandle is textually equivalent across infracore and contracts."""

    def _get_source_lines(self, module_path: str) -> str:
        """Read the SubscriptionHandle definition from a module file."""
        import importlib
        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod)
        lines = [
            line.strip()
            for line in source.splitlines()
            if "SubscriptionHandle" in line and not line.strip().startswith("#")
        ]
        return "\n".join(lines)

    def test_infracore_subscription_handle_defined(self):
        """§3.3: infracore.bootstrap_components.signal_component.handle defines SubscriptionHandle."""
        from infracore.bootstrap_components.signal_component.handle import SubscriptionHandle
        import uuid
        assert SubscriptionHandle.__supertype__ is uuid.UUID

    def test_contracts_subscription_handle_defined(self):
        """§3.3: contracts.signals defines SubscriptionHandle."""
        from contracts.signals import SubscriptionHandle
        import uuid
        assert SubscriptionHandle.__supertype__ is uuid.UUID

    def test_subscription_handle_structural_parity(self):
        """§3.3: SubscriptionHandle NewType is identical in infracore and contracts — drift fails the build."""
        from infracore.bootstrap_components.signal_component.handle import (
            SubscriptionHandle as InfracoreHandle,
        )
        from contracts.signals import SubscriptionHandle as ContractsHandle
        import uuid

        # Both must be NewType over uuid.UUID
        assert InfracoreHandle.__supertype__ is uuid.UUID, (
            "infracore SubscriptionHandle must be NewType over uuid.UUID"
        )
        assert ContractsHandle.__supertype__ is uuid.UUID, (
            "contracts SubscriptionHandle must be NewType over uuid.UUID"
        )

        # Both must share the same __qualname__ / __name__
        assert InfracoreHandle.__name__ == ContractsHandle.__name__ == "SubscriptionHandle", (
            "SubscriptionHandle __name__ drifted between infracore and contracts"
        )

    def test_subscription_handle_source_verbatim_match(self):
        """§3.3: the SubscriptionHandle source is verbatim (modulo whitespace) in both locations."""
        infracore_src = inspect.getsource(
            __import__(
                "infracore.bootstrap_components.signal_component.handle",
                fromlist=[""],
            )
        )
        contracts_src = inspect.getsource(
            __import__("contracts.signals", fromlist=[""])
        )

        def normalize(src: str) -> str:
            return " ".join(src.split())

        infracore_handle_line = next(
            (normalize(l) for l in infracore_src.splitlines() if "SubscriptionHandle" in l and "NewType" in l),
            None,
        )
        contracts_handle_line = next(
            (normalize(l) for l in contracts_src.splitlines() if "SubscriptionHandle" in l and "NewType" in l),
            None,
        )
        assert infracore_handle_line is not None, "No SubscriptionHandle NewType line found in infracore"
        assert contracts_handle_line is not None, "No SubscriptionHandle NewType line found in contracts"
        assert infracore_handle_line == contracts_handle_line, (
            f"SubscriptionHandle definition has drifted:\n"
            f"  infracore: {infracore_handle_line}\n"
            f"  contracts: {contracts_handle_line}"
        )


class TestPluginManifestMirror:
    """§3.3 — plugin manifest Pydantic model fields, types, and constraints match across layers."""

    def _collect_fields(self, model_class) -> dict:
        """Return {field_name: field_info} for a Pydantic v2 model."""
        return dict(model_class.model_fields)

    def test_infracore_plugin_manifest_exists(self):
        """§3.3: infracore.manifest.plugin_manifest defines PluginManifest."""
        from infracore.manifest.plugin_manifest import PluginManifest
        assert PluginManifest is not None

    def test_contracts_plugin_manifest_exists(self):
        """§3.3: contracts.manifest defines PluginManifest (mirror)."""
        from contracts.manifest import PluginManifest
        assert PluginManifest is not None

    def test_field_names_match(self):
        """§3.3: infracore and contracts PluginManifest have identical field names."""
        from infracore.manifest.plugin_manifest import PluginManifest as InfracoreManifest
        from contracts.manifest import PluginManifest as ContractsManifest

        infracore_fields = set(self._collect_fields(InfracoreManifest).keys())
        contracts_fields = set(self._collect_fields(ContractsManifest).keys())

        only_in_infracore = infracore_fields - contracts_fields
        only_in_contracts = contracts_fields - infracore_fields

        assert not only_in_infracore, (
            f"Fields present in infracore manifest but missing in contracts: {only_in_infracore}"
        )
        assert not only_in_contracts, (
            f"Fields present in contracts manifest but missing in infracore: {only_in_contracts}"
        )

    def test_field_types_match(self):
        """§3.3: infracore and contracts PluginManifest fields have identical annotation types."""
        from infracore.manifest.plugin_manifest import PluginManifest as InfracoreManifest
        from contracts.manifest import PluginManifest as ContractsManifest

        infracore_fields = self._collect_fields(InfracoreManifest)
        contracts_fields = self._collect_fields(ContractsManifest)

        for name in infracore_fields:
            if name not in contracts_fields:
                continue
            inf_type = str(infracore_fields[name].annotation)
            con_type = str(contracts_fields[name].annotation)
            assert inf_type == con_type, (
                f"Field '{name}' type drifted: infracore={inf_type}, contracts={con_type}"
            )

    def test_additional_properties_false_in_both(self):
        """§6.1, §3.3: both manifest schemas reject unknown fields (additionalProperties: false)."""
        from infracore.manifest.plugin_manifest import PluginManifest as InfracoreManifest
        from contracts.manifest import PluginManifest as ContractsManifest
        from pydantic import ValidationError

        common_valid = dict(
            name="test_plugin",
            version="1.0.0",
            contracts_min_version="1.0",
            author="auth",
            description="desc",
            entry_point="plugin:Cls",
            required_services=[],
            inputs=[],
            outputs=[],
            permissions=[],
        )
        for Model in (InfracoreManifest, ContractsManifest):
            with pytest.raises((ValidationError, TypeError)):
                Model(**common_valid, unknown_extra_field="oops")
