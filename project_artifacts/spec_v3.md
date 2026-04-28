# PantonicVideo — Build Specification

**Version:** 1.3
**Status:** Authoritative — supersedes spec_v2.md + spec_project_launcher_v1.1.md + spec_project_folder_v1.0.md
**Date:** 2026-04-28

PantonicVideo is a Windows desktop `.exe` built from Python, organized in four layers with a strict one-way import rule: **infracore → contracts → services → plugins**. v3 folds the post-v1 extensions (filesystem v1.1, project_launcher v1.1, project_folder v1.0) into the baseline.

---

## 1. Layers

| # | Layer | Folder | May import from | External deps |
|---|---|---|---|---|
| 1 | infracore | `infracore/` | stdlib + `PySide6`, `platformdirs`, `pydantic`; **only** the contracts data classes in §3.7 | PySide6, platformdirs, pydantic |
| 2 | contracts | `contracts/src/contracts/` | `pydantic`, `typing`, `uuid` | pydantic |
| 3 | services | `services/<name>/` | `infracore`, `contracts`, service's own extras | per-service |
| 4 | plugins | `plugins/<name>/` (built-in), `<root>/plugins/<name>/` (third-party) | `contracts`, `PySide6` | none |

Six components, nine services, four built-in plugins.

---

## 2. Source tree

```
infracore/
├── app.py                                  # bootstrap entry (§8)
├── _versions.py
├── bootstrap_components/
│   ├── signal_component/{signal.py, handle.py}
│   ├── app_state_component/app_state.py
│   ├── filesystem_component/filesystem.py
│   ├── plugin_registry_component/plugin_registry.py
│   └── logging_component/logging.py
├── injector_component/injector.py
├── lifecycle/{hooks.py, excepthook.py}
├── manifest/{plugin_manifest.py, service_manifest.py}
├── ui_shell/{window.py, docker_menu.py, alert_panel.py}
└── version_check.py
contracts/
├── pyproject.toml                          # version "1.0.0"
└── src/contracts/{signals, filesystem, state, plugin_registry, logging,
                  injector, project, image, subtitle, manifest, exceptions}.py
services/{injector, signal, app_state, filesystem, plugin_registry, logging,
          project, image, subtitle}_service/{manifest.json, service.py}
plugins/{project_launcher, project_folder, image_cropping, subtitle_text_tool}/
        {manifest.json, plugin.py}
tests/{infracore, contracts, services, plugins, integration}/
tools/integration_agent/
pyinstaller.spec, pyproject.toml
```

---

## 3. Contracts (type-only — G5)

### 3.1 Modules

| Module | Exposes |
|---|---|
| `signals` | `Signal[T]` Protocol, `Subscription` Protocol, `SubscriptionHandle = NewType(_, uuid.UUID)` (mirror) |
| `filesystem` | `FilesystemService` Protocol (v1.1 — see §5.4), `FilesystemEvent(path, kind, timestamp)` |
| `state` | `AppStateService` Protocol |
| `plugin_registry` | `PluginRegistryService` Protocol, `PluginRecord`, `PluginStatus` enum |
| `logging` | `LoggingService` Protocol, `LogLevel` enum, `AlertEntry` |
| `injector` | `InjectorService` Protocol — single `resolve(name, min_version)` |
| `project` | `ProjectService` Protocol, `Project(central_folder)`, `ProjectMetadata` |
| `image` | `ImageService` Protocol, `CropRect`, `Dimensions`, `ImageFormat(PNG, JPEG)` |
| `subtitle` | `SubtitleService` Protocol, `SrtOptions(cps, max_line_chars, min_duration_ms, gap_ms)` |
| `manifest` | `PluginManifest` (mirror), `RequiredService` |
| `exceptions` | `ServiceNotAvailable`, `ContractVersionMismatch` |

### 3.2 Mirrors (S3, G10 — drift fails the build)

- `SubscriptionHandle` — authoritative in `infracore/.../signal_component/handle.py`, mirrored verbatim in `contracts/signals.py`.
- `PluginManifest` — authoritative in `infracore/manifest/plugin_manifest.py`, mirrored field-for-field in `contracts/manifest.py`.

### 3.3 Caret semver (S4)

Versions normalize by appending zeros (`"1"` → `"1.0.0"`, `"1.2"` → `"1.2.0"`). `^X.Y.Z` matches `>=X.Y.Z, <(X+1).0.0` for X ≥ 1. No pre-release suffixes. Helpers: `infracore/version_check.py`.

### 3.4 Contracts package

Version `1.0.0`, declared in `contracts/pyproject.toml`, read at startup as a string (no contracts code imported by infracore). Distributed via the repo (`pip install -e ./contracts`); not on PyPI for v1.

### 3.5 Bump rules

Adding optional fields, new Protocol methods, new enum values → minor. Removing or changing existing → major.

### 3.6 Cross-layer Pydantic models (§3.7 of v2)

`AlertEntry`, `PluginRecord`, `RequiredService` live in `contracts/` and are the **only** runtime contracts imports made by infracore. Justified because they are pure data classes with no behavior. The integration agent enforces this allowlist.

---

## 4. Components (infracore)

Each module declares `__component_version__: str`. Construction order is fixed in code (§8.3); folder discovery is not used. Constructor failure is **fatal**.

### 4.1 SignalComponent (`v1.0.0`)

Reactive primitive. Builds `Signal[T]` over the callback registration primitives of other components. Caches latest value. **The only observation idiom in v1 — no polling (G7).**

```python
def make_signal(initial: T, register: Callable[[Callable[[T], None]], SubscriptionHandle]) -> Signal[T]: ...
def subscribe(signal: Signal[T], cb: Callable[[T], None]) -> Subscription: ...
def unsubscribe(sub: Subscription) -> None: ...
```

### 4.2 FilesystemComponent (`v1.0.0`)

Single point of write egress (G6). Per-path serialization via `dict[Path, threading.Lock]` with a meta-lock and 60 s lazy eviction. Watch backed by `QFileSystemWatcher` (fallback: `watchdog`); events normalized to `FilesystemEvent(path, kind ∈ {created, modified, deleted}, timestamp)`. **Documented exception:** stdlib `logging` handlers manage their own thread-safety.

```python
def read_file(path) -> bytes
def write_file(path, data) -> None        # serialized per path
def list_dir(path) -> list[Path]
def exists(path) -> bool
def delete(path) -> None                   # serialized per path
def make_dir(path, parents=True) -> None
def rename(src, dst) -> None               # ← v1.1
def move(src, dst) -> None                 # ← v1.1
def copy(src, dst) -> None                 # ← v1.1
def watch(path, cb) -> SubscriptionHandle
def unwatch(handle) -> None
```

### 4.3 AppStateComponent (`v1.0.0`)

In-memory KV store, JSON write-through to `<root>/state.json` via `FilesystemComponent`. Pydantic models accepted via `.model_dump()`.

```python
def state_get(key) -> Any | None
def state_set(key, value) -> None
def state_delete(key) -> None
def state_observe(key, cb) -> SubscriptionHandle
def state_unobserve(handle) -> None
```

**Last-write-wins (S12):** writes within `STATE_WRITE_WARNING_WINDOW_MS = 50` log a `WARNING` (key, both values, elapsed). **Corrupt/missing state.json:** start empty, log WARNING, rename existing file to `state.json.corrupt-<timestamp>`.

**State keys in use:**

| Key | Writer | Observer |
|---|---|---|
| `current_project` | `project_launcher` | `project_folder` |
| `open_file_request` | `project_folder` | (open — no consumer yet) |
| `plugins.<name>.enabled` (S10) | `PluginRegistryService.enable/disable` | startup §8.11 |
| `project.path` | `ProjectService` | `ProjectService` |

### 4.4 PluginRegistryComponent (`v1.0.0`)

```python
def list_plugins() -> list[PluginRecord]
def observe_plugins(cb) -> SubscriptionHandle
def unobserve_plugins(handle) -> None
def _record_loaded(record) -> None
def _record_failed(name, reason) -> None
def _set_enabled(name, enabled) -> None
```

`PluginRecord = (name, version, description, author, status: PluginStatus, failure_reason: str|None, is_builtin: bool)`. `PluginStatus = loaded | enabled | disabled | failed`.

### 4.5 LoggingComponent (`v1.0.0`)

- **Infracore log** — rotating, `<root>/logs/infracore.log`, 10 MB × 5, INFO+, on stdlib root.
- **Per-plugin log** — rotating 10 MB × 5, INFO+, path resolved by `is_builtin`:
  - built-in: `<root>/logs/plugins/<name>/plugin.log` (S8)
  - third-party: `<root>/plugins/<name>/logs/plugin.log`
- **Alert sink** — in-memory `list[AlertEntry(plugin, level, summary, timestamp, acknowledged=False)]`. Resets on restart.

```python
def log(plugin, level, message, **extras) -> None
def raise_alert(plugin, level, summary) -> None
def acknowledge(timestamp, plugin) -> None
def list_alerts() -> list[AlertEntry]
def observe_alerts(cb) -> SubscriptionHandle
```

### 4.6 InjectorComponent (`v1.0.0`)

```python
def register_component(name, component) -> None
def register_service(name, manifest, factory) -> None
def construct_services() -> None
def resolve(name, min_version) -> object
def services_for(plugin_name, required) -> dict[str, object]
```

**Topological sort (S5):** cycles → reject every service in the cycle (log ERROR with edges); other services proceed. Plugins whose `required_services` cannot be satisfied are marked `failed`. **Construction does not abort the app.**

---

## 5. Services

Folder-discovered. Each folder has `manifest.json` + `service.py`. Constructor parameter names must equal `depends_on` names (AST-checked, §10.1). Components are injected by name and **not** declared in `depends_on`.

### 5.1 Service manifest (strict, G9)

```json
{
  "name": "<snake_case>",
  "service_api_version": "X.Y.Z",
  "implementation_version": "X.Y.Z",
  "entry_point": "service:ClassName",
  "depends_on": [{"name": "<svc>", "min_version": "X.Y"}]
}
```

Unknown fields, missing required fields, malformed JSON → reject. Rejected service → ERROR log, absent from injector, dependent plugins → `failed`.

### 5.2 Catalog

| Service | api_ver | Wraps / lib | depends_on |
|---|---|---|---|
| `signal_service` | `1.0.0` | SignalComponent | (none) |
| `app_state_service` | `1.0.0` | AppStateComponent | `signal_service ≥ 1.0` |
| `filesystem_service` | **`1.1.0`** | FilesystemComponent | `signal_service ≥ 1.0` |
| `plugin_registry_service` | `1.0.0` | PluginRegistryComponent | `signal_service ≥ 1.0`, `app_state_service ≥ 1.0` |
| `logging_service` | `1.0.0` | LoggingComponent | (none) |
| `injector_service` | `1.0.0` | InjectorComponent | (none) |
| `project_service` | `1.0.0` | (none) | `app_state_service ≥ 1.0`, `filesystem_service ≥ 1.0`, `signal_service ≥ 1.0` |
| `image_service` | `1.0.0` | Pillow (PNG/JPEG) | `filesystem_service ≥ 1.0` |
| `subtitle_service` | `1.0.0` | (manual SRT) | `filesystem_service ≥ 1.0` |

### 5.3 Expression-service Protocols (compact)

```python
class SignalService(Protocol):
    def signal_for_state(self, key) -> Signal[Any]
    def signal_for_path(self, path) -> Signal[FilesystemEvent]
    def signal_for_plugins(self) -> Signal[list[PluginRecord]]
    def signal_for_alerts(self) -> Signal[list[AlertEntry]]
    def subscribe(self, signal, cb) -> Subscription
    def unsubscribe(self, sub) -> None

class AppStateService(Protocol):
    def state_get(self, key) -> Any | None
    def state_set(self, key, value) -> None
    def state_delete(self, key) -> None
    def state_observe(self, key, cb) -> SubscriptionHandle
    def state_unobserve(self, handle) -> None

class PluginRegistryService(Protocol):
    def list_plugins(self) -> list[PluginRecord]
    def enable(self, name) -> None      # writes plugins.<name>.enabled=True, calls on_enable
    def disable(self, name) -> None
    def observe_plugins(self) -> Signal[list[PluginRecord]]

class LoggingService(Protocol):
    def log(self, plugin, level, message, **extras) -> None
    def raise_alert(self, plugin, level, summary) -> None

class InjectorService(Protocol):
    def resolve(self, name, min_version) -> object
```

### 5.4 FilesystemService Protocol (v1.1.0 surface)

```python
class FilesystemService(Protocol):
    def read_file(self, path) -> bytes
    def write_file(self, path, data) -> None
    def list_dir(self, path) -> list[Path]
    def exists(self, path) -> bool
    def delete(self, path) -> None
    def make_dir(self, path, *, parents: bool = False) -> None
    def watch(self, path, cb) -> SubscriptionHandle
    def unwatch(self, handle) -> None
    def rename(self, src, dst) -> None     # v1.1
    def move(self, src, dst) -> None       # v1.1
    def copy(self, src, dst) -> None       # v1.1
```

### 5.5 Domain-service Protocols (compact)

```python
class ProjectService(Protocol):
    def get_current(self) -> Project | None
    def set_current(self, folder) -> None    # loads/creates pantonicvideo-project.json, sets project.path
    def get_metadata(self) -> ProjectMetadata
    def update_metadata(self, updater: Callable[[ProjectMetadata], ProjectMetadata]) -> None  # atomic via per-path lock (S13)
    def observe_current(self) -> Signal[Project | None]

class ImageService(Protocol):
    def apply_crop(self, source, rect: CropRect, output) -> None
    def resize(self, source, dimensions: Dimensions, output) -> None
    def supported_formats(self) -> list[ImageFormat]   # PNG, JPEG only

class SubtitleService(Protocol):
    def text_to_srt(self, text, output, options: SrtOptions) -> None
```

`Project = (central_folder: Path)`. `ProjectMetadata = (image_source_folders, audio_source_folders, config_folders, extra)`. SRT defaults: `cps=17, max_line_chars=42, min_duration_ms=1000, gap_ms=100`. All write paths route through `filesystem_service.write_file`.

---

## 6. Plugins

### 6.1 Plugin manifest (strict, G9)

```json
{
  "name": "<snake_case_unique>",
  "version": "X.Y.Z",
  "contracts_min_version": "X.Y",
  "author": "<string — alert detail, S15>",
  "description": "<string — Docker-menu tooltip, S15>",
  "entry_point": "<dotted.module>:<ClassName>",
  "required_services": [{"name": "<svc>", "min_version": "X.Y"}],
  "inputs": [], "outputs": [], "permissions": []
}
```

`permissions` parsed and ignored in v1. Unknown fields → reject. **Imports allowed:** `contracts.*`, `PySide6.*`, plus stdlib `pathlib`, `typing` for annotations. Anything else → integration agent rejects.

### 6.2 Lifecycle (all four required)

```python
def on_load(self, services: dict[str, object]) -> None    # store refs
def on_enable(self) -> None
def on_disable(self) -> None
def on_unload(self) -> None
```

Order on enable: `on_load → on_enable`. Order on disable: `on_disable → on_unload`. Missing hook → `failed` with reason "lifecycle hook not implemented: <name>". Hook exception → ERROR log + alert + `failed` (`failure_reason` = truncated message), does not propagate.

### 6.3 Configuration

Convention: built-in → `<root>/plugins-config/<name>.json`; third-party → `<plugin-folder>/config.json`. Read/write through `FilesystemService`.

### 6.4 Plugin catalog

#### project_launcher — v1.1.0
- **Required:** `project_service ≥ 1.0`, `filesystem_service ≥ 1.0`, `app_state_service ≥ 1.0`, `logging_service ≥ 1.0`
- **Auto-enabled** on first run (§8.11)
- `on_enable`: opens `QFileDialog.getExistingDirectory(None, "Open Folder", "", ShowDirsOnly | DontResolveSymlinks)` (re-entrancy-guarded via `_dialog_active`); on non-empty result calls `commit(Path(selected))`; cancel is no-op.
- `commit(folder)`: `project_service.set_current(folder)` **and** `app_state_service.state_set("current_project", folder)`.

#### project_folder — v1.0.0
- **Required:** `app_state_service ≥ 1.0`, `filesystem_service ≥ 1.1`, `signal_service ≥ 1.0`, `logging_service ≥ 1.0`
- **Not auto-enabled.**
- `on_enable`: builds `QWidget` with `QListView` + `QStandardItemModel` + `QVBoxLayout`. If `current_project` absent, shows `QLabel` "Open a project to view its files" (shortcuts disabled). Registers `QShortcut`s. Connects `doubleClicked` and `customContextMenuRequested`. Subscribes `state_observe("current_project", _on_project_changed)` (handle `_state_h`). If `state_get("current_project")` already set, calls `_render(root)` immediately.
- `on_disable`: `state_unobserve(_state_h)`; `unwatch(_fs_h)` if armed; `widget.hide()`; clear model + clipboard.
- **Reactivity (G7):** `state_observe` for project change → re-arm `_cwd`, `unwatch` old, `_render(new_root)`. `filesystem_service.watch(cwd, cb)` for directory changes → `_render(_cwd)`. `_render(path)`: `list_dir(path)` → repopulate; `unwatch` old `_fs_h`; `_fs_h = watch(path, _on_fs_event)`.
- **Navigation:** `_cwd` tracks current folder; folder open updates `_cwd` (does **not** rewrite `current_project`); Backspace clamped at the project root.
- **File open:** `state_set("open_file_request", path)` (intent-publication; §10.2).
- **Actions** (keyboard / mouse / call):

  | Keys | Mouse | Action | Calls |
  |---|---|---|---|
  | `F5` | Refresh | `_render(_cwd)` | `list_dir` |
  | `Backspace` | Up | up one level, clamped at root | — |
  | `Enter` (folder) | dbl-click | navigate `_cwd` | — |
  | `Enter` (file) | dbl-click | publish open intent | `state_set("open_file_request", path)` |
  | `Delete` | Delete | `QMessageBox.question` Yes → `delete(path)` | `delete` |
  | `F2` | Rename | `QInputDialog.getText` → `rename(src, src.parent / new)` | `rename` |
  | `Ctrl+X` | Cut | clipboard `(path, "cut")` | — |
  | `Ctrl+C` | Copy | clipboard `(path, "copy")` | — |
  | `Ctrl+V` | Paste | cut → `move(src, cwd/src.name)`+clear; copy → `copy(src, cwd/src.name)` | `move`/`copy` |
  | `Ctrl+N` | New folder | `QInputDialog` → `make_dir(cwd / name)` | `make_dir` |
  | `Ctrl+Shift+N` | New file | `QInputDialog` → `write_file(cwd / name, b"")` | `write_file` |

- **Failure containment (G8):** every `filesystem_service.*` call inside a Qt slot is wrapped:
  ```python
  try: filesystem_service.<op>(...)
  except Exception as e:
      logging_service.raise_alert("project_folder", LogLevel.ERROR, str(e))
  ```
  Operation fails, plugin stays `enabled`.

#### image_cropping — v1.0.0
- **Required:** `image_service ≥ 1.0`, `filesystem_service ≥ 1.0`, `project_service ≥ 1.0`, `logging_service ≥ 1.0`
- UI: image picker, Qt-rendered crop/resize preview, commit. Calls `ImageService.apply_crop` / `resize`.

#### subtitle_text_tool — v1.0.0
- **Required:** `subtitle_service ≥ 1.0`, `filesystem_service ≥ 1.0`, `project_service ≥ 1.0`, `logging_service ≥ 1.0`
- UI: text input, optional SRT pacing, destination picker, commit. Calls `SubtitleService.text_to_srt`.

---

## 7. UI shell

- **Window:** light-mode `QMainWindow`. First run → `project_launcher` docker only.
- **Docker menu:** one toggle per non-`failed` plugin; reflects current `enabled` state; click → `enable`/`disable`. Tooltip = manifest `description` (S15).
- **Status bar:** alert icon styled by highest unacknowledged level (`WARNING/ERROR/CRITICAL`). Subscribes to `signal_for_alerts()`. Click → dropdown of alerts grouped by plugin, newest first (each row: level, summary, timestamp, plugin author S15). Drill-in opens detail view with link to log file and "open log folder" button — calls `LoggingComponent.acknowledge(timestamp, plugin)` (S14, in-memory only, resets on restart). No "clear all".
- **Layout persistence:** `<root>/layout.json` = `{version, saved_at, qt_state(base64)}`. Absent / malformed / unknown version → first-run + WARNING; existing file renamed `layout.json.unrecognized-<timestamp>`. **First-run trigger = absence of layout.json**, not state.

---

## 8. Startup sequence (`infracore/app.py`)

1. **Resolve user-data root.** Read override from prior `config.json` else `platformdirs.user_data_dir("PantonicVideo")`. Create `<root>/{logs, logs/plugins, plugins}/`. Unwritable → fatal stderr.
2. **Bootstrap log handler.** Rotating handler on stdlib root → `<root>/logs/infracore.log`. Stays attached after LoggingComponent.
3. **Construct components** (fixed order, fatal on exception): `Injector → Signal → Filesystem → AppState → Logging → PluginRegistry`.
4. **Verify contracts version + load state.** Read `contracts/pyproject.toml` (string only). `AppStateComponent.load()` from `state.json`.
5. **Install wrapped `sys.excepthook` (S11).** Walks frames, attributes to plugin if `__file__` ∈ plugin folder → per-plugin log + alert + `_record_failed`. Always calls previous hook.
6. **Discover services.** Scan bundled `services/`. For each: validate manifest → resolve entry point → `register_service`. Then `construct_services()` (topological sort; cycles → reject members; constructor failure → reject; dependents of rejected → rejected).
7. **Discover plugins.** Two scans: bundled `plugins/` (built-in), then `<root>/plugins/` (third-party). For each: validate manifest, check `contracts_min_version`, check `required_services`. **Name collision (S6):** built-in wins; third-party → `failed`. Successful → `loaded`.
8. **Construct UI shell.** QMainWindow + Docker menu + alert icon.
9. **Restore layout.** Read `layout.json` per §7; fall back to first-run on any failure.
10. **Call `on_load`** on every `loaded` plugin via `services_for(name, required)`. Exception → `failed`.
11. **Call `on_enable`** for every `loaded` plugin where `state_get("plugins.<name>.enabled") == True`. **First-run override:** if §9 fell back to first-run, `project_launcher` is enabled unconditionally and the persisted flag is overwritten to `True` for that single launch; other plugins honor their persisted state.
12. **`app.exec()`.**
13. **Shutdown** (reverse, exception-tolerant): `on_disable` enabled → `on_unload` loaded → save `layout.json` → flush state → close handlers.

---

## 9. User-data root

```
<pantonicvideo-root>/    (default %APPDATA%\PantonicVideo)
├── config.json
├── layout.json
├── state.json
├── logs/
│   ├── infracore.log
│   └── plugins/<name>/plugin.log         # built-ins (S8)
└── plugins/<name>/                        # third-party only
    ├── manifest.json
    ├── <entry>.py
    ├── config.json
    └── logs/plugin.log
```

Bundled paths via `sys._MEIPASS`; user-data via `<root>`.

---

## 10. Layer rules and runtime expression

### 10.1 Import edges

| From → To | Allowed |
|---|---|
| `infracore.*` → stdlib + PySide6/platformdirs/pydantic | yes |
| `infracore.*` → `contracts.*` | **data classes only** (`AlertEntry`, `PluginRecord`, `RequiredService`, manifest-mirror data classes); **no Protocols** |
| `infracore.*` → `services.*`, `plugins.*` | **no** |
| `infracore.bootstrap_components.*` ↔ each other | yes (ordered) |
| `infracore.injector_component` → bootstrap components | yes |
| `contracts.*` → `pydantic`, `typing`, `uuid` | yes |
| `contracts.*` → `infracore`, `services`, `plugins` | **no** |
| `services.<X>` → `infracore`, `contracts`, declared extras | yes |
| `services.<X>` → `services.<Y>` (direct) | **no** (inject only) |
| `services.<X>` → `plugins.*` | **no** |
| `plugins.<X>` → `contracts.*`, `PySide6.*` | yes |
| `plugins.<X>` → `infracore`, `services`, other `plugins`, external libs | **no** |

Transitive imports are checked.

### 10.2 Runtime expression

`InjectorComponent` is the runtime enforcement: plugins receive only Protocol-typed services at `on_load`. Cross-plugin coupling — when desired — happens via `AppStateService` keys (e.g., `open_file_request` is published by `project_folder` and may be consumed by a future plugin via `state_observe`).

---

## 11. Failure containment

| Failure | Surface | Routing |
|---|---|---|
| Plugin lifecycle hook raises | per-plugin log ERROR + alert ERROR + `failed` | §6.2, §8.10 |
| Plugin Qt slot raises | per-plugin log ERROR + alert ERROR + `failed` | wrapped excepthook §8.5 |
| Plugin manifest invalid | `failed` with reason | §8.7 |
| `required_services` unsatisfied | `failed` with reason | §8.7 |
| Service raises during call | propagates to caller (plugin's responsibility) | — |
| Service manifest invalid | rejected, ERROR log, absent from injector | §8.6 |
| Service constructor raises | rejected, ERROR log, dependents rejected | §8.6 |
| Service `depends_on` cycle | every member rejected, ERROR with cycle edges | §8.6 (S5) |
| **Component constructor raises** | **fatal** — abort startup | §8.3 |
| `state.json` corrupt | empty store + WARNING; corrupt file renamed | §4.3, §8.4 |
| `layout.json` malformed/unknown | first-run + WARNING; file renamed | §7, §8.9 |

The Docker menu hides `failed` plugins.

---

## 12. Versioning axes

| Axis | Declared | Read by | Caret-matched |
|---|---|---|---|
| Contracts package | `contracts/pyproject.toml` | `version_check` at startup | plugin `contracts_min_version` |
| `service_api_version` | `services/<X>/manifest.json` | InjectorComponent | plugin `required_services[].min_version` |
| `implementation_version` | `services/<X>/manifest.json` | integration agent | diagnostic only |
| Infracore release | `infracore/_versions.py` | release engineering | not matched |
| `__component_version__` | each component module | integration agent | wrapping `service_api_version` (warn) |

**Bump discipline:** an infracore change visible through an expression service must bump the corresponding `service_api_version`.

---

## 13. Integration agent (`tools/integration_agent/`)

Project-level tool, not runtime. Runs in CI and on plugin/service promotion.

| # | Check | Failure |
|---|---|---|
| 1 | Plugin manifest validates | reject |
| 2 | Service manifest validates | reject |
| 3 | Plugin imports respect §10.1 (transitive) | reject |
| 4 | Service imports respect §10.1 (transitive) | reject |
| 5 | infracore→contracts imports restricted to §3.6 allowlist | fail build |
| 6 | Service constructor param names == `depends_on` names | reject |
| 7 | Mirror schemas (PluginManifest) not drifted | fail build |
| 8 | `SubscriptionHandle` declarations match (textual modulo whitespace) | fail build |
| 9 | Each component declares `__component_version__` | fail build |
| 10 | `service_api_version` caret-compatible with wrapped component | warn |
| 11 | Production lines added ≤ 3× test lines added (G3) | warn |

Strict (PRD D10): minor issues are fixed or sent back, never accepted.

---

## 14. Stack and packaging

| Area | Choice |
|---|---|
| GUI | PySide6 (LGPL) |
| Language | Python 3.12 (3.11 fallback) |
| Packaging | PyInstaller, one-file `.exe`, splash on unpack |
| Deps | `uv` + `pyproject.toml` |
| Manifests | JSON, Pydantic v2 strict |
| Discovery | filesystem scan (bundled + user-data) |
| Injection | `InjectorComponent` (active, topological) |
| State store | in-memory KV, JSON write-through |
| Layout | versioned wrapper around base64 Qt state |
| Logging | stdlib `logging`, rotating 10 MB × 5 |
| Testing | `pytest`, `pytest-qt` |
| Distribution | GitHub repo + `.exe`; `contracts` from local path (S16) |

`pyinstaller.spec` bundles: `infracore/`, `contracts/`, every service folder + extras, every built-in plugin folder. **`plugins/project_folder/` must be added** (Sprint D).

---

## 15. Testing

```
tests/{infracore, contracts, services, plugins, integration}/
```

- **infracore** — components in isolation; real (not mocked) inner components.
- **contracts** — schema and mirror-drift tests.
- **services** — mocked components for expression services; mocked services for domain services.
- **plugins** — mocked services; UI via `pytest-qt`.
- **integration (§16.2 of v2):** (1) clean startup with all built-ins; (2) deliberately broken third-party plugin; (3) `state.json` seeded with `plugins.image_cropping.enabled=True`; (4) unrecognized `layout.json` version; (5) built-in/third-party name collision.

**Floor discipline (G2):** every test green at milestone close becomes a regression floor; subsequent sprints may extend, never weaken. Current floor: 346 green (M2+M3+M4+M5+Sprint 1+Sprint 2).

---

## 16. Guardrails (verbatim — every skill restates these)

- **G1.** TDD mandatory. No production code before its failing test.
- **G2.** Regression containment. Floor tests may be extended, never weakened.
- **G3.** Less code, more quality. Fewer lines wins.
- **G4.** Layer-direction rule (§10.1) is invariant.
- **G5.** `contracts` is type-only — no behavior, no I/O, no logging, no non-version constants.
- **G6.** Single point of egress for filesystem writes (exception: stdlib `logging`).
- **G7.** Signals are the only observation idiom. No polling.
- **G8.** Failure containment over abort. Only component constructor exceptions are fatal.
- **G9.** Strict manifests. No silent coercion.
- **G10.** Mirror discipline. Drift fails the build.

**Universal sprint exit:** target test red → green; integration agent stays green; `code-critic` ratifies.
**Universal refusal:** if the spec underspecifies a detail you would otherwise invent → stop and file a spec-clarification request.

---

## 17. Out of scope (v1 + current extensions)

Pipelines/workflows (v2); `CapCutAdapterService` (v1.1+); permissions enforcement (v2+); hot-reload; plugin marketplace; macOS; dark mode/theming/named layouts; system tray/autostart/OS notifications; sandboxing/out-of-process plugins; image formats beyond PNG/JPEG; subtitle formats beyond SRT (extensions are minor bumps); `contracts` on PyPI.

---

## 18. Pre-spec decision index (v2 carry-over)

S1 six components (§1, §4) · S2 `InjectorService` Protocol (§3.1, §5.3) · S3 `SubscriptionHandle` mirror (§3.2) · S4 caret semver (§3.3) · S5 cycles rejected, not fatal (§4.6, §8.6) · S6 built-ins win on name collision (§8.7) · S7 layout-version mismatch → first-run (§7) · S8 built-in plugin logs under `<root>/logs/plugins/<n>/` (§4.5, §9) · S9 `__component_version__` (§4, §13) · S10 `plugins.<n>.enabled` in app state (§4.3, §8.11) · S11 wrapped `sys.excepthook` (§8.5) · S12 50 ms warning window (§4.3) · S13 `update_metadata` atomicity via per-path lock (§5.5) · S14 click-to-acknowledge, in-memory (§7) · S15 description in tooltip, author in alert (§7) · S16 contracts not on PyPI (§3.4) · S17 `Injector` single `resolve` (§5.3).
