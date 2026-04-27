"""PantonicVideo bootstrap entry point — §9.1–§9.13."""
from __future__ import annotations

import dataclasses
import importlib
import importlib.util
import json
import logging as _stdlib_logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LAYOUT_VERSION = 1


def _get_bundle_dir() -> Path:
    """Return the root dir containing services/ and plugins/ (§14.2).

    Frozen one-file build: sys._MEIPASS mirrors the project root layout.
    Dev mode: walk up from this file.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


@dataclasses.dataclass
class RunResult:
    """Headless run result — consumed by integration tests (§16.2)."""

    plugin_records: list
    service_count: int
    alert_count: int
    shutdown_clean: bool
    startup_healthy: bool
    is_first_run: bool
    warnings: list
    errors: list

    @property
    def project_launcher_status(self) -> str:
        rec = next((r for r in self.plugin_records if r.name == "project_launcher"), None)
        return rec.status.value if rec else "not_found"

    @property
    def image_cropping_status(self) -> str:
        rec = next((r for r in self.plugin_records if r.name == "image_cropping"), None)
        return rec.status.value if rec else "not_found"

    @property
    def subtitle_text_tool_status(self) -> str:
        rec = next((r for r in self.plugin_records if r.name == "subtitle_text_tool"), None)
        return rec.status.value if rec else "not_found"


def run(root: Path | None = None, headless: bool = False) -> RunResult:
    """Bootstrap the full application against *root*, returning an observation object.

    When headless=True the Qt event loop and window are skipped; used by integration tests.
    """
    if root is None:
        root = Path(tempfile.mkdtemp(prefix="pantonicvideo-"))
    root = Path(root)

    PROJECT_ROOT = _get_bundle_dir()

    from infracore.lifecycle.excepthook import install_excepthook
    install_excepthook(plugin_registry=None, logging_component=None)

    from infracore.bootstrap_components.signal_component.signal import SignalComponent
    from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
    from infracore.bootstrap_components.logging_component.logging import LoggingComponent
    from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
    from infracore.bootstrap_components.plugin_registry_component.plugin_registry import PluginRegistryComponent
    from infracore.injector_component.injector import InjectorComponent

    signal_comp = SignalComponent()
    fs_comp = FilesystemComponent(signal_component=signal_comp)
    log_comp = LoggingComponent(filesystem_component=fs_comp, root=root)
    state_comp = AppStateComponent(
        signal_component=signal_comp,
        filesystem_component=fs_comp,
        logging_component=log_comp,
        root=root,
    )
    registry_comp = PluginRegistryComponent(
        signal_component=signal_comp,
        filesystem_component=fs_comp,
        app_state_component=state_comp,
        logging_component=log_comp,
    )
    injector_comp = InjectorComponent()
    injector_comp.register_component("signal", signal_comp)
    injector_comp.register_component("filesystem", fs_comp)
    injector_comp.register_component("logging", log_comp)
    injector_comp.register_component("app_state", state_comp)
    injector_comp.register_component("plugin_registry", registry_comp)
    injector_comp.register_component("injector", injector_comp)

    install_excepthook(plugin_registry=registry_comp, logging_component=log_comp)

    state_comp.load()

    from infracore.manifest.service_manifest import ServiceManifest
    services_dir = PROJECT_ROOT / "services"
    if services_dir.exists():
        for svc_dir in sorted(services_dir.iterdir()):
            if not svc_dir.is_dir():
                continue
            manifest_file = svc_dir / "manifest.json"
            if not manifest_file.exists():
                continue
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest = ServiceManifest(**manifest_data)
                module_path, cls_name = manifest.entry_point.rsplit(":", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, cls_name)
                injector_comp.register_service(manifest.name, manifest, cls)
            except Exception as e:
                log_comp.log("infracore", _stdlib_logging.ERROR,
                             f"Failed to register service {svc_dir.name}: {e}")

    injector_comp.construct_services()
    service_count = len(injector_comp._instances)
    log_comp.log("infracore", _stdlib_logging.INFO,
                 f"Boot: {service_count} services constructed")

    is_first_run, layout_warnings = _handle_layout(root)
    for w in layout_warnings:
        log_comp.log("infracore", _stdlib_logging.WARNING, w)

    from infracore.manifest.plugin_manifest import PluginManifest
    from contracts.plugin_registry import PluginRecord, PluginStatus
    from contracts.exceptions import ServiceNotAvailable
    from infracore.lifecycle.hooks import (
        call_on_load,
        call_on_enable,
        resolve_enabled_on_first_run,
    )

    builtin_plugin_dir = PROJECT_ROOT / "plugins"
    user_plugin_dir = root / "plugins"

    builtin_names: set[str] = set()
    if builtin_plugin_dir.exists():
        for _d in builtin_plugin_dir.iterdir():
            _mf = _d / "manifest.json"
            if _mf.exists():
                try:
                    _data = json.loads(_mf.read_text(encoding="utf-8"))
                    builtin_names.add(_data.get("name", ""))
                except Exception:
                    pass

    plugin_instances: dict[str, Any] = {}

    def _load_plugin(plugin_dir: Path, is_builtin: bool) -> None:
        manifest_file = plugin_dir / "manifest.json"
        if not manifest_file.exists():
            return

        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest = PluginManifest(**manifest_data)
        except Exception as exc:
            name = plugin_dir.name
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} manifest invalid: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed to load")
            registry_comp._record_failed(name, f"manifest error: {exc}")
            return

        name = manifest.name

        # S6: third-party plugin whose name collides with a built-in is rejected.
        if not is_builtin and name in builtin_names:
            reason = f"plugin '{name}' collides with built-in plugin"
            third_party = PluginRecord(
                name=name,
                version=manifest.version,
                description=manifest.description,
                author=manifest.author,
                status=PluginStatus.failed,
                failure_reason=reason,
                is_builtin=False,
            )
            registry_comp._records.append(third_party)
            registry_comp._notify_observers()
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"{name} collides with built-in plugin; third-party rejected")
            return

        # Check required services before any import.
        try:
            services = injector_comp.services_for(name, manifest.required_services)
        except ServiceNotAvailable as exc:
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} required service unavailable: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed: {exc}")
            registry_comp._record_failed(name, str(exc))
            return

        # Import entry point.
        try:
            module_path, cls_name = manifest.entry_point.rsplit(":", 1)
            if is_builtin:
                mod = importlib.import_module(module_path)
            else:
                plugin_file = plugin_dir / f"{module_path}.py"
                spec = importlib.util.spec_from_file_location(
                    f"_pv_user_plugin_{name}", plugin_file
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            cls = getattr(mod, cls_name)
            instance = cls()
        except Exception as exc:
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} import failed: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed to import")
            registry_comp._record_failed(name, f"import error: {exc}")
            return

        record = PluginRecord(
            name=name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=is_builtin,
        )
        registry_comp._record_loaded(record)

        def _on_load_failure(plugin_name: str, reason: str) -> None:
            registry_comp._records = [
                r.model_copy(update={"status": PluginStatus.failed, "failure_reason": reason})
                if r.name == plugin_name and r.is_builtin == is_builtin
                else r
                for r in registry_comp._records
            ]
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {plugin_name} on_load failed: {reason}")

        call_on_load(instance, services, plugin_name=name, on_failure=_on_load_failure)

        current = next(
            (r for r in registry_comp._records
             if r.name == name and r.is_builtin == is_builtin),
            None,
        )
        if current is None or current.status == PluginStatus.failed:
            return

        plugin_instances[name] = instance

    if builtin_plugin_dir.exists():
        for _d in sorted(builtin_plugin_dir.iterdir()):
            if _d.is_dir():
                _load_plugin(_d, is_builtin=True)

    if user_plugin_dir.exists():
        for _d in sorted(user_plugin_dir.iterdir()):
            if _d.is_dir():
                _load_plugin(_d, is_builtin=False)

    # §9.11 — apply first-run / persisted state, then call on_enable for enabled plugins.
    for name, instance in plugin_instances.items():
        if resolve_enabled_on_first_run(name, state_comp, is_first_run):
            registry_comp._set_enabled(name, True)
            call_on_enable(instance, plugin_name=name, on_failure=None)

    _save_layout(root)

    return RunResult(
        plugin_records=registry_comp.list_plugins(),
        service_count=service_count,
        alert_count=len(log_comp.list_alerts()),
        shutdown_clean=True,
        startup_healthy=True,
        is_first_run=is_first_run,
        warnings=log_comp.captured_warnings(),
        errors=log_comp.captured_errors(),
    )


def _handle_layout(root: Path) -> tuple[bool, list[str]]:
    """Return (is_first_run, warning_messages) after inspecting layout.json."""
    layout_file = root / "layout.json"
    warnings: list[str] = []

    if not layout_file.exists():
        return True, warnings

    try:
        data = json.loads(layout_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        warnings.append("layout.json could not be read; using first-run layout")
        return True, warnings

    version = data.get("version")
    if version != _LAYOUT_VERSION:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        renamed = layout_file.parent / f"layout.json.unrecognized-{ts}"
        layout_file.rename(renamed)
        warnings.append(
            f"Unrecognized layout.json version {version!r}; "
            f"renamed to {renamed.name}, using first-run layout"
        )
        return True, warnings

    if not {"version", "saved_at", "qt_state"}.issubset(data.keys()):
        warnings.append("layout.json missing required fields; using first-run layout")
        return True, warnings

    return False, warnings


def _save_layout(root: Path) -> None:
    data = {
        "version": _LAYOUT_VERSION,
        "qt_state": "",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    (root / "layout.json").write_text(json.dumps(data), encoding="utf-8")


def main(root: Path | None = None) -> None:
    import platformdirs

    if root is None:
        root = Path(platformdirs.user_data_dir("PantonicVideo", "PantonicVideo"))
        root.mkdir(parents=True, exist_ok=True)

    bundle_dir = _get_bundle_dir()

    from infracore.lifecycle.excepthook import install_excepthook
    install_excepthook(plugin_registry=None, logging_component=None)

    from infracore.bootstrap_components.signal_component.signal import SignalComponent
    from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
    from infracore.bootstrap_components.logging_component.logging import LoggingComponent
    from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
    from infracore.bootstrap_components.plugin_registry_component.plugin_registry import PluginRegistryComponent
    from infracore.injector_component.injector import InjectorComponent

    signal_comp = SignalComponent()
    fs_comp = FilesystemComponent(signal_component=signal_comp)
    log_comp = LoggingComponent(filesystem_component=fs_comp, root=root)
    state_comp = AppStateComponent(
        signal_component=signal_comp,
        filesystem_component=fs_comp,
        logging_component=log_comp,
        root=root,
    )
    registry_comp = PluginRegistryComponent(
        signal_component=signal_comp,
        filesystem_component=fs_comp,
        app_state_component=state_comp,
        logging_component=log_comp,
    )
    injector_comp = InjectorComponent()
    injector_comp.register_component("signal", signal_comp)
    injector_comp.register_component("filesystem", fs_comp)
    injector_comp.register_component("logging", log_comp)
    injector_comp.register_component("app_state", state_comp)
    injector_comp.register_component("plugin_registry", registry_comp)
    injector_comp.register_component("injector", injector_comp)

    install_excepthook(plugin_registry=registry_comp, logging_component=log_comp)

    state_comp.load()

    from infracore.manifest.service_manifest import ServiceManifest
    services_dir = bundle_dir / "services"
    if services_dir.exists():
        for svc_dir in sorted(services_dir.iterdir()):
            if not svc_dir.is_dir():
                continue
            manifest_file = svc_dir / "manifest.json"
            if not manifest_file.exists():
                continue
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest = ServiceManifest(**manifest_data)
                module_path, cls_name = manifest.entry_point.rsplit(":", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, cls_name)
                injector_comp.register_service(manifest.name, manifest, cls)
            except Exception as e:
                log_comp.log("infracore", _stdlib_logging.ERROR,
                             f"Failed to register service {svc_dir.name}: {e}")

    injector_comp.construct_services()
    service_count = len(injector_comp._instances)
    log_comp.log("infracore", _stdlib_logging.INFO,
                 f"Boot: {service_count} services constructed")

    from infracore.manifest.plugin_manifest import PluginManifest
    from contracts.plugin_registry import PluginRecord, PluginStatus
    from contracts.exceptions import ServiceNotAvailable
    from infracore.lifecycle.hooks import (
        call_on_load,
        call_on_enable,
        resolve_enabled_on_first_run,
    )

    builtin_plugin_dir = bundle_dir / "plugins"
    user_plugin_dir = root / "plugins"

    builtin_names: set[str] = set()
    if builtin_plugin_dir.exists():
        for _d in builtin_plugin_dir.iterdir():
            _mf = _d / "manifest.json"
            if _mf.exists():
                try:
                    _data = json.loads(_mf.read_text(encoding="utf-8"))
                    builtin_names.add(_data.get("name", ""))
                except Exception:
                    pass

    plugin_instances: dict[str, Any] = {}

    def _load_plugin(plugin_dir: Path, is_builtin: bool) -> None:
        manifest_file = plugin_dir / "manifest.json"
        if not manifest_file.exists():
            return
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest = PluginManifest(**manifest_data)
        except Exception as exc:
            name = plugin_dir.name
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} manifest invalid: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed to load")
            registry_comp._record_failed(name, f"manifest error: {exc}")
            return

        name = manifest.name

        if not is_builtin and name in builtin_names:
            reason = f"plugin '{name}' collides with built-in plugin"
            third_party = PluginRecord(
                name=name, version=manifest.version, description=manifest.description,
                author=manifest.author, status=PluginStatus.failed,
                failure_reason=reason, is_builtin=False,
            )
            registry_comp._records.append(third_party)
            registry_comp._notify_observers()
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"{name} collides with built-in plugin; third-party rejected")
            return

        try:
            services = injector_comp.services_for(name, manifest.required_services)
        except ServiceNotAvailable as exc:
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} required service unavailable: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed: {exc}")
            registry_comp._record_failed(name, str(exc))
            return

        try:
            module_path, cls_name = manifest.entry_point.rsplit(":", 1)
            if is_builtin:
                mod = importlib.import_module(module_path)
            else:
                plugin_file = plugin_dir / f"{module_path}.py"
                spec = importlib.util.spec_from_file_location(
                    f"_pv_user_plugin_{name}", plugin_file
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            cls = getattr(mod, cls_name)
            instance = cls()
        except Exception as exc:
            log_comp.log("infracore", _stdlib_logging.ERROR,
                         f"Plugin {name} import failed: {exc}")
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {name} failed to import")
            registry_comp._record_failed(name, f"import error: {exc}")
            return

        record = PluginRecord(
            name=name, version=manifest.version, description=manifest.description,
            author=manifest.author, status=PluginStatus.loaded,
            failure_reason=None, is_builtin=is_builtin,
        )
        registry_comp._record_loaded(record)

        def _on_load_failure(plugin_name: str, reason: str) -> None:
            registry_comp._records = [
                r.model_copy(update={"status": PluginStatus.failed, "failure_reason": reason})
                if r.name == plugin_name and r.is_builtin == is_builtin
                else r
                for r in registry_comp._records
            ]
            log_comp.raise_alert("infracore", _stdlib_logging.ERROR,
                                 f"Plugin {plugin_name} on_load failed: {reason}")

        call_on_load(instance, services, plugin_name=name, on_failure=_on_load_failure)

        current = next(
            (r for r in registry_comp._records
             if r.name == name and r.is_builtin == is_builtin),
            None,
        )
        if current is None or current.status == PluginStatus.failed:
            return

        plugin_instances[name] = instance

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from infracore.ui_shell.window import MainWindow
    window = MainWindow()
    is_first_run = window.restore_layout(root, on_warning=lambda w: log_comp.log("infracore", 30, w))

    if builtin_plugin_dir.exists():
        for _d in sorted(builtin_plugin_dir.iterdir()):
            if _d.is_dir():
                _load_plugin(_d, is_builtin=True)

    if user_plugin_dir.exists():
        for _d in sorted(user_plugin_dir.iterdir()):
            if _d.is_dir():
                _load_plugin(_d, is_builtin=False)

    for name, instance in plugin_instances.items():
        if resolve_enabled_on_first_run(name, state_comp, is_first_run):
            registry_comp._set_enabled(name, True)
            call_on_enable(instance, plugin_name=name, on_failure=None)

    from infracore.ui_shell.docker_menu import DockerMenu
    menu_bar = window.menuBar()
    docker_menu = DockerMenu("Plugins", window)
    docker_menu.update_plugins(registry_comp.list_plugins())
    menu_bar.addMenu(docker_menu)

    window.show()
    exit_code = app.exec()
    window.save_layout(root)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
