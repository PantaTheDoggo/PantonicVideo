"""Tests for lifecycle hooks and excepthook — §6.2, §9.5, §9.10, §9.11, S11."""

import sys
import types
from pathlib import Path

import pytest
from infracore.lifecycle.hooks import call_on_load, call_on_enable, call_on_disable, call_on_unload
from infracore.lifecycle.excepthook import install_excepthook, _pantonicvideo_excepthook


class TestLifecycleHookOrdering:
    """§6.2 — on_load / on_enable / on_disable / on_unload called in order."""

    def test_on_load_called(self):
        """§6.2: call_on_load invokes plugin.on_load(services)."""
        order = []

        class FakePlugin:
            def on_load(self, services):
                order.append("load")
            def on_enable(self):
                pass
            def on_disable(self):
                pass
            def on_unload(self):
                pass

        plugin = FakePlugin()
        call_on_load(plugin, services={"svc": object()})
        assert "load" in order

    def test_on_enable_called_after_load(self):
        """§6.2: on_enable is called after on_load; order is preserved."""
        order = []

        class FakePlugin:
            def on_load(self, services):
                order.append("load")
            def on_enable(self):
                order.append("enable")
            def on_disable(self):
                pass
            def on_unload(self):
                pass

        plugin = FakePlugin()
        call_on_load(plugin, services={})
        call_on_enable(plugin)
        assert order == ["load", "enable"]

    def test_on_disable_before_on_unload(self):
        """§6.2: on_disable is called before on_unload during shutdown."""
        order = []

        class FakePlugin:
            def on_load(self, services):
                pass
            def on_enable(self):
                pass
            def on_disable(self):
                order.append("disable")
            def on_unload(self):
                order.append("unload")

        plugin = FakePlugin()
        call_on_disable(plugin)
        call_on_unload(plugin)
        assert order == ["disable", "unload"]


class TestHookExceptionCapture:
    """§6.2 — exceptions in lifecycle hooks are captured, not propagated."""

    def _make_plugin_that_raises(self, hook_name):
        class RaisingPlugin:
            def on_load(self, services):
                if hook_name == "on_load":
                    raise RuntimeError("load failed")
            def on_enable(self):
                if hook_name == "on_enable":
                    raise RuntimeError("enable failed")
            def on_disable(self):
                if hook_name == "on_disable":
                    raise RuntimeError("disable failed")
            def on_unload(self):
                if hook_name == "on_unload":
                    raise RuntimeError("unload failed")
        return RaisingPlugin()

    @pytest.mark.parametrize("hook", ["on_load", "on_enable", "on_disable", "on_unload"])
    def test_exception_does_not_propagate(self, hook):
        """§6.2: exceptions in lifecycle hooks do not propagate to the caller."""
        plugin = self._make_plugin_that_raises(hook)
        fn_map = {
            "on_load": lambda: call_on_load(plugin, services={}),
            "on_enable": lambda: call_on_enable(plugin),
            "on_disable": lambda: call_on_disable(plugin),
            "on_unload": lambda: call_on_unload(plugin),
        }
        fn_map[hook]()  # must not raise

    @pytest.mark.parametrize("hook", ["on_load", "on_enable", "on_disable", "on_unload"])
    def test_exception_marks_plugin_failed(self, hook):
        """§6.2: an exception during a lifecycle hook sets the plugin's status to failed."""
        from infracore.bootstrap_components.plugin_registry_component.plugin_registry import (
            PluginRegistryComponent,
            PluginRecord,
            PluginStatus,
        )
        plugin = self._make_plugin_that_raises(hook)
        # The hooks layer must accept a registry callback to record failures
        failed_names = []

        def on_fail(name, reason):
            failed_names.append(name)

        fn_map = {
            "on_load": lambda: call_on_load(plugin, services={}, plugin_name="test_p", on_failure=on_fail),
            "on_enable": lambda: call_on_enable(plugin, plugin_name="test_p", on_failure=on_fail),
            "on_disable": lambda: call_on_disable(plugin, plugin_name="test_p", on_failure=on_fail),
            "on_unload": lambda: call_on_unload(plugin, plugin_name="test_p", on_failure=on_fail),
        }
        fn_map[hook]()
        assert "test_p" in failed_names


class TestMissingHooks:
    """§6.2 — a plugin missing any hook fails on_load."""

    def test_missing_on_enable_fails(self):
        """§6.2: a plugin missing on_enable is marked failed with reason 'lifecycle hook not implemented: on_enable'."""
        failed = {}

        class BadPlugin:
            def on_load(self, services):
                pass
            def on_disable(self):
                pass
            def on_unload(self):
                pass

        plugin = BadPlugin()
        call_on_load(
            plugin,
            services={},
            plugin_name="bad_plugin",
            on_failure=lambda name, reason: failed.update({name: reason}),
        )
        assert "bad_plugin" in failed
        assert "on_enable" in failed["bad_plugin"]


class TestExcepthook:
    """§9.5, S11 — wrapped sys.excepthook attributes exceptions to plugins."""

    def test_install_excepthook_replaces_sys_excepthook(self):
        """S11: install_excepthook replaces sys.excepthook with the PantonicVideo hook."""
        original = sys.excepthook
        try:
            install_excepthook(
                plugin_registry=None,
                logging_component=None,
            )
            assert sys.excepthook is not original
        finally:
            sys.excepthook = original

    def test_excepthook_calls_previous_hook(self):
        """S11: the wrapped excepthook always calls the previous hook (debugger-friendly)."""
        called = []
        prev = lambda t, v, tb: called.append(True)
        original = sys.excepthook
        sys.excepthook = prev
        try:
            install_excepthook(
                plugin_registry=None,
                logging_component=None,
            )
            try:
                raise ValueError("test exception")
            except ValueError:
                sys.excepthook(*sys.exc_info())
        finally:
            sys.excepthook = original
        assert called


class TestFirstRunPrecedence:
    """§9.11 — first-run vs layout.json precedence."""

    def test_project_launcher_enabled_on_first_run(self, tmp_path):
        """§9.11: on first run, project_launcher is always enabled regardless of persisted state."""
        from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
        from infracore.bootstrap_components.signal_component.signal import SignalComponent
        from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
        from infracore.bootstrap_components.logging_component.logging import LoggingComponent

        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        state = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        # Explicitly disable project_launcher in persisted state
        state.state_set("plugins.project_launcher.enabled", False)

        from infracore.lifecycle.hooks import resolve_enabled_on_first_run
        enabled = resolve_enabled_on_first_run(
            plugin_name="project_launcher",
            app_state=state,
            is_first_run=True,
        )
        assert enabled is True

    def test_non_launcher_plugin_honors_persisted_state_on_first_run(self, tmp_path):
        """§9.11: on first run, non-project_launcher plugins honor their persisted enabled state."""
        from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
        from infracore.bootstrap_components.signal_component.signal import SignalComponent
        from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
        from infracore.bootstrap_components.logging_component.logging import LoggingComponent
        from infracore.lifecycle.hooks import resolve_enabled_on_first_run

        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        state = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        state.state_set("plugins.image_cropping.enabled", True)

        enabled = resolve_enabled_on_first_run(
            plugin_name="image_cropping",
            app_state=state,
            is_first_run=True,
        )
        assert enabled is True

    def test_normal_run_honors_persisted_state(self, tmp_path):
        """§9.11: on a normal run (layout present), persisted enabled state is used."""
        from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
        from infracore.bootstrap_components.signal_component.signal import SignalComponent
        from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
        from infracore.bootstrap_components.logging_component.logging import LoggingComponent
        from infracore.lifecycle.hooks import resolve_enabled_on_first_run

        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        state = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        state.state_set("plugins.project_launcher.enabled", False)

        enabled = resolve_enabled_on_first_run(
            plugin_name="project_launcher",
            app_state=state,
            is_first_run=False,
        )
        assert enabled is False
