# PantonicVideo — As-Is Reference

**Version:** post-Sprint-2 (April 2026)
**Status:** Living document — authoritative source of truth for all development.
**IMPORTANT:** Every agent must consult this document as its primary reference before implementing anything. At the end of every sprint, update this document to reflect the new application state before closing the sprint.

---

## Current Application State

| Metric | Value |
|---|---|
| Release | `dist/PantonicVideo.exe` (~63 MB) — v1 passes smoke checklist |
| Test count | **346 green** (M2 + M3 + M4 + M5 floors + Sprint 1 + Sprint 2 extensions) |
| Last sprint | plugin-extender Sprint 2 — `project_launcher` v1.1.0 + `project_folder` v1.0.0 |
| Pending sprint | release-engineer Sprint D — add `plugins/project_folder/` to `pyinstaller.spec` |
| Open handoff | `open_file_request` consumer — spec not yet written |

---

## 1. Architecture Overview

PantonicVideo is a four-layer Windows desktop application. Import direction is one-way and enforced by the integration agent.

| Layer | Folder | Imports allowed from | External deps |
|---|---|---|---|
| 1. infracore | `infracore/` | stdlib, `PySide6`, `platformdirs`, `pydantic`; §3.7 contracts data models only | PySide6, platformdirs, pydantic |
| 2. contracts | `contracts/src/contracts/` | `pydantic`, stdlib `typing`, `uuid` | pydantic |
| 3. services | `services/` | `infracore/`, `contracts/`, service's own declared extras | per service |
| 4. plugins (built-in) | `plugins/` | `contracts/`, `PySide6` | none |

The application is single-process, single-user, single-machine. No IPC, no sandboxing, no hot-reload.

---

## 2. Source Tree Layout (current)

```
<repo-root>/
├── infracore/
│   ├── app.py                              # bootstrap entry point (§9)
│   ├── _versions.py                        # infracore release version constant
│   ├── bootstrap_components/
│   │   ├── signal_component/
│   │   │   ├── signal.py                   # SignalComponent  __component_version__ = "1.0.0"
│   │   │   └── handle.py                   # SubscriptionHandle NewType(uuid.UUID)
│   │   ├── app_state_component/
│   │   │   └── app_state.py                # AppStateComponent  __component_version__ = "1.0.0"
│   │   ├── filesystem_component/
│   │   │   └── filesystem.py               # FilesystemComponent  __component_version__ = "1.0.0"
│   │   ├── plugin_registry_component/
│   │   │   └── plugin_registry.py          # PluginRegistryComponent  __component_version__ = "1.0.0"
│   │   └── logging_component/
│   │       └── logging.py                  # LoggingComponent  __component_version__ = "1.0.0"
│   ├── injector_component/
│   │   └── injector.py                     # InjectorComponent  __component_version__ = "1.0.0"
│   ├── lifecycle/
│   │   ├── hooks.py                        # on_load/on_enable/on_disable/on_unload orchestration
│   │   └── excepthook.py                   # wrapped sys.excepthook (S11)
│   ├── manifest/
│   │   ├── plugin_manifest.py              # authoritative PluginManifest (Pydantic v2)
│   │   └── service_manifest.py             # authoritative ServiceManifest (Pydantic v2)
│   ├── ui_shell/
│   │   ├── window.py                       # QMainWindow + menus + status bar
│   │   ├── docker_menu.py
│   │   └── alert_panel.py
│   └── version_check.py                    # normalize_version, caret_match (S4)
│
├── contracts/
│   ├── pyproject.toml                      # version: "1.0.0"
│   └── src/contracts/
│       ├── signals.py                      # Signal[T], Subscription, SubscriptionHandle mirror
│       ├── filesystem.py                   # FilesystemService Protocol, FilesystemEvent
│       ├── state.py                        # AppStateService Protocol
│       ├── plugin_registry.py              # PluginRegistryService Protocol, PluginRecord, PluginStatus
│       ├── logging.py                      # LoggingService Protocol, LogLevel, AlertEntry
│       ├── injector.py                     # InjectorService Protocol
│       ├── project.py                      # ProjectService Protocol, Project, ProjectMetadata
│       ├── image.py                        # ImageService Protocol, CropRect, Dimensions, ImageFormat
│       ├── subtitle.py                     # SubtitleService Protocol, SrtOptions
│       ├── manifest.py                     # PluginManifest mirror, RequiredService
│       └── exceptions.py                   # ServiceNotAvailable, ContractVersionMismatch
│
├── services/
│   ├── injector_service/
│   ├── signal_service/
│   ├── app_state_service/
│   ├── filesystem_service/                 # service_api_version: "1.1.0"  ← extended (Sprint 1)
│   ├── plugin_registry_service/
│   ├── logging_service/
│   ├── project_service/
│   ├── image_service/
│   └── subtitle_service/
│
├── plugins/
│   ├── project_launcher/                   # version: "1.1.0"  ← extended (Sprint 2)
│   ├── project_folder/                     # version: "1.0.0"  ← NEW (Sprint 2)
│   ├── image_cropping/                     # version: "1.0.0"
│   └── subtitle_text_tool/                 # version: "1.0.0"
│
├── tests/
│   ├── infracore/          # M2 floor (locked)
│   ├── contracts/          # M2 floor (locked)
│   ├── services/           # M3 floor (locked)
│   ├── plugins/            # M4 floor (locked) + Sprint 2 extensions
│   └── integration/        # M5 floor (locked)
│
├── tools/integration_agent/
├── pantonic_agents/                        # agent skill + claude.md files
├── project_artifacts/
│   ├── as-is.md                           ← THIS FILE (authoritative reference)
│   └── handoff.md                         # open/done cross-sprint items
│
├── pyproject.toml
├── pyinstaller.spec                        # NOTE: plugins/project_folder/ not yet added (Sprint D)
├── rules.md                                # G1–G10 guardrails (verbatim)
└── README.md
```

---

## 3. Component Catalog (infracore)

Components are wired in code at startup. Construction order is fixed: `InjectorComponent → SignalComponent → FilesystemComponent → AppStateComponent → LoggingComponent → PluginRegistryComponent`. Each module declares `__component_version__: str`.

### SignalComponent
- **Path:** `infracore/bootstrap_components/signal_component/signal.py`
- **Version:** `1.0.0`
- **Responsibility:** reactive primitive — manages `Signal[T]`, subscription registration, latest-value caching. All observation surfaces delegate here.
- **Key API:** `make_signal(initial, register)`, `subscribe(signal, callback) → Subscription`, `unsubscribe(subscription)`
- **No polling anywhere** — G7 enforced at this layer.

### FilesystemComponent
- **Path:** `infracore/bootstrap_components/filesystem_component/filesystem.py`
- **Version:** `1.0.0`
- **Responsibility:** single point of write egress; per-path serialization via `dict[Path, threading.Lock]`; raises `FilesystemEvent` signals.
- **Key API:** `read_file`, `write_file`, `list_dir`, `exists`, `delete`, `make_dir`, `watch(path, callback) → SubscriptionHandle`, `unwatch(handle)`, `rename(src, dst)`, `move(src, dst)`, `copy(src, dst)`
- **Exception:** stdlib `logging` handlers bypass this component (G6 documented exception).

### AppStateComponent
- **Path:** `infracore/bootstrap_components/app_state_component/app_state.py`
- **Version:** `1.0.0`
- **Responsibility:** in-memory KV store, write-through to `<pantonicvideo-root>/state.json` via `FilesystemComponent`.
- **Key API:** `state_get(key) → Any|None`, `state_set(key, value)`, `state_delete(key)`, `state_observe(key, callback) → SubscriptionHandle`, `state_unobserve(handle)`
- **State keys in use:**
  - `current_project` — current project folder path (set by `project_launcher`, observed by `project_folder`)
  - `open_file_request` — path emitted by `project_folder` on file open (no subscriber yet — open handoff)
  - `plugins.<name>.enabled` — persisted enable flag per plugin (S10)
  - `project.path` — project path key used by `ProjectService`
- **Collision warning:** 50 ms window (S12 — `STATE_WRITE_WARNING_WINDOW_MS = 50`).

### LoggingComponent
- **Path:** `infracore/bootstrap_components/logging_component/logging.py`
- **Version:** `1.0.0`
- **Responsibility:** infracore rotating log (`<pantonicvideo-root>/logs/infracore.log`); per-plugin rotating logs; in-memory alert sink with signal emission.
- **Per-plugin log paths:** built-ins → `<pantonicvideo-root>/logs/plugins/<name>/plugin.log` (S8); third-party → `<pantonicvideo-root>/plugins/<name>/logs/plugin.log`.
- **Key API:** `log(plugin, level, message, **extras)`, `raise_alert(plugin, level, summary)`, `acknowledge(timestamp, plugin)`, `list_alerts()`, `observe_alerts(callback) → SubscriptionHandle`
- **AlertEntry model:** `plugin`, `level`, `summary`, `timestamp`, `acknowledged: bool = False`

### PluginRegistryComponent
- **Path:** `infracore/bootstrap_components/plugin_registry_component/plugin_registry.py`
- **Version:** `1.0.0`
- **Responsibility:** tracks loaded/enabled/failed plugins; emits `observe_plugins` signal.
- **Key API:** `list_plugins() → list[PluginRecord]`, `observe_plugins(callback) → SubscriptionHandle`, `unobserve_plugins(handle)`, `_record_loaded`, `_record_failed`, `_set_enabled`
- **PluginRecord:** `name`, `version`, `description`, `author`, `status: PluginStatus`, `failure_reason: str|None`, `is_builtin: bool`
- **PluginStatus enum:** `loaded | enabled | disabled | failed`

### InjectorComponent
- **Path:** `infracore/injector_component/injector.py`
- **Version:** `1.0.0`
- **Responsibility:** active constructor — topological sort of `depends_on`, service instantiation, resolution at `on_load`. Cycles rejected (S5), not fatal.
- **Key API:** `register_component(name, component)`, `register_service(name, manifest, factory)`, `construct_services()`, `resolve(name, min_version) → object`, `services_for(plugin_name, required) → dict[str, object]`

---

## 4. Contracts Catalog

`contracts` package version: **`1.0.0`** (declared in `contracts/pyproject.toml`). Type-only — no behavior, no I/O, no logging.

### Structural mirror rule (S3, G10)
Two types are mirrored verbatim between infracore and contracts — drift fails the build:
- `SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)` — in `infracore/bootstrap_components/signal_component/handle.py` and `contracts/signals.py`
- `PluginManifest` Pydantic model — authoritative in `infracore/manifest/plugin_manifest.py`, mirrored in `contracts/manifest.py`

### Contracts by module

| Module | Exposes |
|---|---|
| `contracts.signals` | `Signal[T]` Protocol, `Subscription` Protocol, `SubscriptionHandle` (mirror) |
| `contracts.filesystem` | `FilesystemService` Protocol, `FilesystemEvent(path, kind, timestamp)` |
| `contracts.state` | `AppStateService` Protocol |
| `contracts.plugin_registry` | `PluginRegistryService` Protocol, `PluginRecord`, `PluginStatus` |
| `contracts.logging` | `LoggingService` Protocol, `LogLevel` enum, `AlertEntry` |
| `contracts.injector` | `InjectorService` Protocol — single `resolve(name, min_version)` (S2, S17) |
| `contracts.project` | `ProjectService` Protocol, `Project(central_folder)`, `ProjectMetadata` |
| `contracts.image` | `ImageService` Protocol, `CropRect`, `Dimensions`, `ImageFormat(PNG/JPEG)` |
| `contracts.subtitle` | `SubtitleService` Protocol, `SrtOptions(cps, max_line_chars, min_duration_ms, gap_ms)` |
| `contracts.manifest` | `PluginManifest` mirror, `RequiredService` |
| `contracts.exceptions` | `ServiceNotAvailable`, `ContractVersionMismatch` |

### FilesystemService Protocol (current — v1.1.0 surface)
```python
class FilesystemService(Protocol):
    def write_file(self, path: Path, data: bytes) -> None: ...
    def read_file(self, path: Path) -> bytes: ...
    def exists(self, path: Path) -> bool: ...
    def delete(self, path: Path) -> None: ...
    def make_dir(self, path: Path, *, parents: bool = False) -> None: ...
    def list_dir(self, path: Path) -> list[Path]: ...
    def watch(self, path: Path, callback: Callable[[FilesystemEvent], None]) -> SubscriptionHandle: ...
    def unwatch(self, handle: SubscriptionHandle) -> None: ...
    def rename(self, src: Path, dst: Path) -> None: ...   # ← added Sprint 1
    def move(self, src: Path, dst: Path) -> None: ...     # ← added Sprint 1
    def copy(self, src: Path, dst: Path) -> None: ...     # ← added Sprint 1
```

### AppStateService Protocol
```python
class AppStateService(Protocol):
    def state_get(self, key: str) -> Any | None: ...
    def state_set(self, key: str, value: Any) -> None: ...
    def state_delete(self, key: str) -> None: ...
    def state_observe(self, key: str, callback: Callable[[Any], None]) -> SubscriptionHandle: ...
    def state_unobserve(self, handle: SubscriptionHandle) -> None: ...
```

### Shared Pydantic data models (imported by infracore at runtime — §3.7)
`AlertEntry`, `PluginRecord`, `RequiredService` — authoritative in `contracts/`, imported by infracore. Only allowed runtime contracts imports by infracore.

---

## 5. Services Catalog (current versions)

Each service folder: `manifest.json` + `service.py`. Discovered at startup, validated by `ServiceManifest`, registered with `InjectorComponent`. Constructor parameter names must equal `depends_on` names (§13.1).

### Expression services (wrap a component)

| Service | `service_api_version` | Wraps | `depends_on` |
|---|---|---|---|
| `signal_service` | `1.0.0` | `SignalComponent` | (none) |
| `app_state_service` | `1.0.0` | `AppStateComponent` | `signal_service >= 1.0` |
| `filesystem_service` | **`1.1.0`** | `FilesystemComponent` | `signal_service >= 1.0` |
| `plugin_registry_service` | `1.0.0` | `PluginRegistryComponent` | `signal_service >= 1.0`, `app_state_service >= 1.0` |
| `logging_service` | `1.0.0` | `LoggingComponent` | (none) |
| `injector_service` | `1.0.0` | `InjectorComponent` | (none) |

### Domain services (wrap external libs)

| Service | `service_api_version` | External lib | `depends_on` |
|---|---|---|---|
| `project_service` | `1.0.0` | (none) | `app_state_service >= 1.0`, `filesystem_service >= 1.0`, `signal_service >= 1.0` |
| `image_service` | `1.0.0` | Pillow (PNG/JPEG only) | `filesystem_service >= 1.0` |
| `subtitle_service` | `1.0.0` | (manual SRT) | `filesystem_service >= 1.0` |

### filesystem_service v1.1.0 changes (Sprint 1)
Added `rename(src, dst)`, `move(src, dst)`, `copy(src, dst)` — required by `project_folder`. `service_api_version` bumped from `1.0.0` → `1.1.0`. `contracts/filesystem.py` updated accordingly.

---

## 6. Plugins Catalog (current versions)

Each plugin: `manifest.json` + `plugin.py` + `__init__.py`. Import allowlist: `contracts.*` and `PySide6.*` only. All four lifecycle hooks required.

### project_launcher — v1.1.0

| Field | Value |
|---|---|
| **Entry point** | `plugins.project_launcher.plugin:ProjectLauncherPlugin` |
| **required_services** | `project_service >= 1.0`, `filesystem_service >= 1.0`, `app_state_service >= 1.0`, `logging_service >= 1.0` |
| **Auto-enabled** | yes — first run (§9.11) |

**v1.1.0 changes (Sprint 2):** Added `app_state_service` to `on_load`. `on_enable` opens `QFileDialog.getExistingDirectory` (guard against re-entrant calls). `commit(folder)` now also calls `app_state_service.state_set("current_project", folder)` in addition to `project_service.set_current(folder)`. Cancel is no-op.

```python
# Current plugin skeleton
class ProjectLauncherPlugin:
    def on_load(self, services):
        self._project_service    = services["project_service"]
        self._filesystem_service = services["filesystem_service"]
        self._app_state_service  = services["app_state_service"]
        self._logging_service    = services["logging_service"]
        self._dialog_active      = False

    def on_enable(self):
        if self._dialog_active: return
        self._dialog_active = True
        try:
            selected = QFileDialog.getExistingDirectory(None, "Open Folder", "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if selected: self.commit(Path(selected))
        finally:
            self._dialog_active = False

    def commit(self, folder):
        self._project_service.set_current(folder)
        self._app_state_service.state_set("current_project", folder)
```

### project_folder — v1.0.0 (NEW, Sprint 2)

| Field | Value |
|---|---|
| **Entry point** | `plugins.project_folder.plugin:ProjectFolderPlugin` |
| **required_services** | `app_state_service >= 1.0`, `filesystem_service >= 1.1`, `signal_service >= 1.0`, `logging_service >= 1.0` |
| **Auto-enabled** | no |

**Behavior:**
- `on_enable`: builds `QWidget` with `QListView` + `QStandardItemModel`; shows placeholder label if no `current_project`; registers `QShortcut`s; subscribes `state_observe("current_project", _on_project_changed)`; renders immediately if `current_project` already set.
- `on_disable`: unobserves state, unwatches filesystem, hides widget, clears clipboard.
- **Reactivity (G7):** `state_observe` for project changes; `filesystem_service.watch(cwd, callback)` for directory changes.
- **Navigation:** `_cwd` tracks current directory; `Backspace`/Up clamps at `current_project` root; folder double-click/Enter navigates `_cwd` (does NOT write `current_project`).
- **File open:** double-click/Enter on file → `state_set("open_file_request", path)` (no consumer yet).
- **Filesystem ops (G8 — all in try/except → `raise_alert`):** Delete (with `QMessageBox.question`), Rename (`QInputDialog`), Cut/Copy/Paste (via `move`/`copy`), New folder (`make_dir`), New file (`write_file(..., b"")`).
- **Shortcuts:** F5 refresh, Backspace up, Enter open, Delete delete, F2 rename, Ctrl+X/C/V cut/copy/paste, Ctrl+N new folder, Ctrl+Shift+N new file. Context menu mirrors all actions.

### image_cropping — v1.0.0

| Field | Value |
|---|---|
| **required_services** | `image_service >= 1.0`, `filesystem_service >= 1.0`, `project_service >= 1.0`, `logging_service >= 1.0` |
| **UI** | image picker + Qt-rendered crop/resize preview + commit |
| **Calls** | `ImageService.apply_crop` or `ImageService.resize` |

### subtitle_text_tool — v1.0.0

| Field | Value |
|---|---|
| **required_services** | `subtitle_service >= 1.0`, `filesystem_service >= 1.0`, `project_service >= 1.0`, `logging_service >= 1.0` |
| **UI** | text input + optional SRT pacing + destination picker + commit |
| **Calls** | `SubtitleService.text_to_srt` |

---

## 7. Guardrails (G1–G10) — verbatim from rules.md

- **G1. TDD mandatory.** No production code before its failing test. A change is accepted only when (a) the motivating test existed and was failing before the change, and (b) every previously-green test stays green.
- **G2. Regression containment.** Every validated milestone is sealed. Subsequent sprints may not weaken floor tests; only extend them.
- **G3. Less code, more quality.** Fewer lines wins when two implementations satisfy the same tests. Verbose code is rejected by `integration-agent`.
- **G4. Layer-direction rule (§10.1) invariant.** No import may contradict the table in §1. `integration-agent` has veto authority. Transitive imports are checked.
- **G5. Contracts is type-only.** No behavior, no I/O, no logging, no non-version constants.
- **G6. Single filesystem egress.** All writes route through `FilesystemComponent`. Documented exception: stdlib `logging` handlers.
- **G7. Signals only.** No polling. `state_observe` + `filesystem_service.watch` are the only observation idioms.
- **G8. Failure containment over abort.** Non-fatal failures → alert icon + per-plugin log + `PluginRecord.status = failed`. Only component constructor exceptions are fatal.
- **G9. Strict manifests.** Unknown fields, missing required fields, malformed JSON → reject. No silent coercion.
- **G10. Mirror discipline.** `SubscriptionHandle` and `PluginManifest` are mirrored across infracore and contracts. Drift fails the build.

### Universal sprint exit (3 conditions, all required)
1. Target test file goes red → green.
2. `integration-agent` stays green (no §13.1 check regresses).
3. `code-critic` ratifies the PR.

### Universal refusal trigger
If the spec underspecifies a detail you would otherwise invent — **stop and file a spec-clarification request**. Do not guess.

---

## 8. Startup Sequence

`infracore/app.py` executes in order:

1. **Resolve user-data root.** `%APPDATA%\PantonicVideo` (overridable). Create subfolders.
2. **Bootstrap log handler.** Attach rotating handler to `<root>/logs/infracore.log`.
3. **Construct components** (fixed order, fatal on exception): `InjectorComponent → SignalComponent → FilesystemComponent → AppStateComponent → LoggingComponent → PluginRegistryComponent`.
4. **Verify contracts version + load state.** Read `contracts/pyproject.toml`; load `state.json` (empty + WARNING if missing/corrupt; corrupt file renamed `state.json.corrupt-<timestamp>`).
5. **Install wrapped `sys.excepthook` (S11).** Attributes uncaught exceptions to plugins by frame-walking; routes to per-plugin log + alert.
6. **Discover services.** Scan bundled `services/`; validate manifests; topological sort + instantiate. Cycles → reject cycle members (logged ERROR), not abort.
7. **Discover plugins.** Scan built-in `plugins/` then user-data `<root>/plugins/`. For each: validate manifest, check `contracts_min_version`, check `required_services` satisfaction. Name collision: built-in wins (S6). Successful → `loaded`.
8. **Construct UI shell.** `QMainWindow`, Docker menu (all non-`failed` plugins), status bar (alert icon subscribed to `signal_for_alerts()`).
9. **Restore layout.** Read `<root>/layout.json`. On absent/malformed/unknown version: first-run + WARNING + file renamed `.unrecognized-<timestamp>`.
10. **Call `on_load` on every `loaded` plugin.** Exception → `failed`.
11. **Call `on_enable` on every plugin whose `plugins.<name>.enabled` = True.** First-run exception: `project_launcher` is enabled unconditionally regardless of persisted state; other plugins honor persisted state.
12. **Start Qt event loop.** `app.exec()`.
13. **Shutdown** (reverse): `on_disable` all enabled → `on_unload` all loaded → save layout → flush state → close handlers.

---

## 9. Test Matrix (floors — never weaken, only extend)

| Floor | Directory | Tests | Status |
|---|---|---|---|
| M2 | `tests/infracore/`, `tests/contracts/` | signal, filesystem, app_state, logging, plugin_registry, injector, lifecycle, ui_shell, schemas, mirror_invariants, exceptions, version | 🟢 locked |
| M3 | `tests/services/` | signal_service, app_state_service, filesystem_service, plugin_registry_service, logging_service, injector_service, project_service, image_service, subtitle_service | 🟢 locked |
| M4 | `tests/plugins/` (original 3 files) | test_project_launcher.py, test_image_cropping.py, test_subtitle_text_tool.py | 🟢 locked |
| M5 | `tests/integration/` | 5 scenarios: clean startup, broken plugin, state-seeded enable, unrecognized layout, name collision | 🟢 locked |
| Sprint 1 | `tests/infracore/test_filesystem_component.py` (extension), `tests/services/test_filesystem_service.py` (extension) | rename/move/copy coverage | 🟢 |
| Sprint 2 | `tests/plugins/test_project_launcher_open_folder.py` (6 tests), `tests/plugins/test_project_folder.py` (23 tests) | project_launcher v1.1 + project_folder v1.0 | 🟢 |
| **Total** | | | **346 green** |

### Integration scenarios (§16.2) — all must stay green
1. Clean startup with 4 built-in plugins. `project_launcher` enabled; others loaded.
2. Startup with deliberately broken user-data plugin — broken plugin under alert icon; app healthy.
3. Startup with `state.json` containing `plugins.image_cropping.enabled: True` — Image Cropping enabled at launch.
4. Startup with unrecognized `layout.json` version — first-run layout; WARNING logged; app healthy.
5. Built-in/third-party name collision — third-party `failed`; built-in enabled per persisted state.

---

## 10. Layer Rules — Import Constraints (§10.1)

| From → To | Allowed |
|---|---|
| `infracore.*` → stdlib, PySide6, platformdirs, pydantic | yes |
| `infracore.*` → `contracts.*` | **data models only**: `AlertEntry`, `PluginRecord`, `RequiredService`, manifest mirror data classes |
| `infracore.*` → `services.*` or `plugins.*` | **no** |
| `contracts.*` → pydantic, typing, uuid | yes |
| `contracts.*` → `infracore.*`, `services.*`, `plugins.*` | **no** |
| `services.<X>` → `infracore.*`, `contracts.*` | yes |
| `services.<X>` → `services.<Y>` (direct import) | **no** — inject only |
| `services.<X>` → `plugins.*` | **no** |
| `plugins.<X>` → `contracts.*`, `PySide6.*` | yes |
| `plugins.<X>` → `infracore.*`, `services.*`, external libs, other `plugins.*` | **no** |

The integration agent checks **transitive** imports.

---

## 11. Integration Agent Checks (§13.1)

| # | Check | Failure mode |
|---|---|---|
| 1 | Plugin manifest validates via `PluginManifest.model_validate` | Reject |
| 2 | Service manifest validates via `ServiceManifest.model_validate` | Reject |
| 3 | Plugin imports respect §10.1 (transitive) | Reject |
| 4 | Service imports respect §10.1 (transitive) | Reject |
| 5 | Infracore imports from contracts restricted to §3.7 allowlist | Fail build |
| 6 | Service constructor parameter names match `depends_on` names | Reject |
| 7 | Contracts mirror schemas not drifted from infracore authoritative | Fail build |
| 8 | `SubscriptionHandle` declarations match (textual, modulo whitespace) | Fail build |
| 9 | Each component module declares `__component_version__` | Fail build |
| 10 | Expression service `service_api_version` caret-compatible with component `__component_version__` | **Warn** |
| + | Production lines added ≤ 3× corresponding test lines (G3) | Warn |

---

## 12. Versioning Rules

**Caret semver (S4):** `^X.Y.Z` ≡ `>=X.Y.Z, <(X+1).0.0` for X ≥ 1. Missing components filled with zeros (`"1"` → `"1.0.0"`).

**Bump rules for `service_api_version`:** adding optional fields, new Protocol methods, new enum values → minor bump. Removing or changing existing → major bump.

| Axis | Declared in | Checked against |
|---|---|---|
| Contracts package | `contracts/pyproject.toml` | Plugin's `contracts_min_version` |
| `service_api_version` | `services/<X>/manifest.json` | Plugin's `required_services[].min_version` |
| `implementation_version` | `services/<X>/manifest.json` | Integration agent (diagnostic only) |
| Infracore release | `infracore/_versions.py` | Not checked at runtime (D12) |
| `__component_version__` | Each component module | Integration agent vs expression service |

---

## 13. Plugin Manifest Schema (strict, G9)

```json
{
  "name": "<snake_case_unique>",
  "version": "X.Y.Z",
  "contracts_min_version": "X.Y",
  "author": "<string — shown in alert detail, S15>",
  "description": "<string — shown as Docker-menu tooltip, S15>",
  "entry_point": "<dotted.module>:<ClassName>",
  "required_services": [{"name": "<svc>", "min_version": "X.Y"}],
  "inputs": [],
  "outputs": [],
  "permissions": []
}
```
`permissions` is parsed and ignored in v1. Unknown fields → reject.

### Lifecycle hooks (all four required)
```python
def on_load(self, services: dict[str, object]) -> None: ...   # store service refs
def on_enable(self) -> None: ...                               # show UI / start work
def on_disable(self) -> None: ...                              # hide UI / stop work
def on_unload(self) -> None: ...                               # release resources
```
Order: `on_load → on_enable` on enable; `on_disable → on_unload` on disable. Exception at any hook → `failed` + alert + per-plugin log ERROR.

---

## 14. Service Manifest Schema (strict, G9)

```json
{
  "name": "<snake_case>",
  "service_api_version": "X.Y.Z",
  "implementation_version": "X.Y.Z",
  "entry_point": "<dotted.module>:<ClassName>",
  "depends_on": [{"name": "<service_name>", "min_version": "X.Y"}]
}
```
Constructor parameter names must equal `depends_on` names (§13.1, AST-checked). Components injected by name without being listed in `depends_on`.

---

## 15. User-Data Root Layout

```
<pantonicvideo-root>/    (%APPDATA%\PantonicVideo by default)
├── config.json          # infracore configuration
├── layout.json          # docker layout (versioned wrapper around base64 Qt state)
├── state.json           # KV store snapshot (write-through)
├── logs/
│   ├── infracore.log    # rotating 10 MB × 5
│   └── plugins/         # built-in plugin logs (S8)
│       └── <plugin>/plugin.log
└── plugins/             # third-party plugins only
    └── <plugin>/
        ├── manifest.json
        ├── <entry>.py
        └── logs/plugin.log
```

First-run: layout.json absent → Project Launcher enabled; others loaded (in Docker menu, not enabled).

---

## 16. Packaging

- **Tool:** PyInstaller, one-file `.exe`, splash screen during unpack.
- **Bundle includes:** `infracore/`, `contracts/`, all `services/` folders, all built-in `plugins/` folders, all per-service `pyproject.toml` extras.
- **`pyinstaller.spec` status:** `plugins/project_launcher/`, `plugins/image_cropping/`, `plugins/subtitle_text_tool/` bundled. **`plugins/project_folder/` NOT YET ADDED — pending Sprint D.**
- **Runtime path resolution:** bundled paths via `sys._MEIPASS`; user-data paths via `<pantonicvideo-root>`.

---

## 17. Agent System

### Agent roles

| Agent | Active in | Purpose |
|---|---|---|
| `test-author` | M1 | Author failing tests before production code |
| `infracore-builder` | M2 | Implement components + contracts |
| `service-builder` | M3 | Implement one service per sprint |
| `plugin-builder` | M4 | Implement one plugin per sprint |
| `integration-agent` | M2–M5+ | Static gate on every PR — read-only, veto authority |
| `code-critic` | M2–M5+ | G3 review — advisory, read-only |
| `release-engineer` | M5 | PyInstaller build + smoke checklist |
| `infracore-extender` | post-v1 | Extend components/contracts on locked M2 floor |
| `service-extender` | post-v1 | Extend services/contracts on locked M3 floor |
| `plugin-extender` | post-v1 | Extend plugins on locked M4 floor |

### Agent skill files
Each agent's `skill.md` is in `pantonic_agents/<agent>/skill.md`. Each agent's full `CLAUDE.md` (inventory, gotchas, context fallback chain) is in `pantonic_agents/<agent>/claude.md` (system-reminder injected at activation).

### Context fallback chain (all extender agents)
1. **Primary:** this `as-is.md` + `rules.md`
2. **Fallback 1:** actual source code in the relevant layer
3. **Fallback 2:** `project_artifacts/history/done/` for closed sprint specs
4. **Refusal:** if all three are silent on the demand, stop and ask

### Pre-sprint checklist (all agents)
Before implementing: read `project_artifacts/handoff.md`. For each **open** item: if in scope and spec exists → resolve; if in scope and no spec → stop (spec first); if out of scope → leave open.

**Spec lifecycle:** every task needs a spec under `project_artifacts/history/<spec_name>.md` before coding. On sprint close: move spec to `project_artifacts/history/done/`; mark item done in `handoff.md`; **update this `as-is.md`**.

---

## 18. Open Items (from handoff.md)

### OPEN — `open_file_request` consumer

| Field | Value |
|---|---|
| **Status** | open |
| **Opened** | 2026-04-28 |
| **Owner** | plugin-extender (next sprint) |
| **Spec** | not yet written |

`project_folder` publishes `state_set("open_file_request", path)` when the user opens a file. No plugin currently subscribes. Until a subscriber exists, the signal is silently dropped.

**Acceptance for closure:** a new plugin (or extension) observes `"open_file_request"` via `state_observe`; spec exists before coding; all floor tests stay green.

### OPEN — Sprint D: pyinstaller.spec update

| Field | Value |
|---|---|
| **Status** | open |
| **Owner** | release-engineer |
| **Action** | Add `plugins/project_folder/` to `pyinstaller.spec` bundle; rebuild `.exe`; run smoke checklist |

---

## 19. Out of Scope (v1 + current extensions)

- Pipelines / cross-plugin workflows (v2)
- `CapCutAdapterService` (v1.1+)
- Permissions enforcement (v2+)
- Hot-reload of plugins
- Plugin marketplace / in-app browser
- macOS support
- Dark mode, theming, named layouts
- System tray, autostart, OS notifications
- Sandboxing / out-of-process plugins
- Image formats beyond PNG/JPEG; subtitle formats beyond SRT (minor bumps when needed, not rewrites)
- `contracts` on PyPI (deferred; `pyproject.toml` is ready)
