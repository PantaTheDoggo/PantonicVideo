# PantonicVideo — Build Specification

**Version:** 1.1
**Status:** Build-ready (sprint-planning input)
**Date:** April 2026
**Inputs:** `PRD.md` v1.1, `architecture.md` v1.0, pre-spec decisions S1–S17 (April 2026)
**Scope:** v1 of PantonicVideo. Where the PRD is normative, this document defers to it. Where the architecture document is normative, this document defers to it. This document fills the gaps and pins the unspecified mechanics so the implementation can proceed without further interpretation.

**Changes from v1.0:** Refined cross-layer Pydantic-model placement (§3.7) to remove an inconsistency where `AlertEntry` was used in a contracts-typed signal but defined in infracore; added `RequiredService` to `contracts.manifest` exports; tightened the import-direction table (§10.1) and the integration agent's checks (§13.1) to reflect the data-model exception explicitly; clarified first-run precedence between `layout.json` absence and persisted plugin-enabled state (§9.11); added §19 covering the development plan, milestones, agents, skills, and project-wide guardrails for sprint planning.

PantonicVideo is the assembly of four layers — **infracore**, **contracts**, **services**, and **plugins** — packaged as a single Windows desktop `.exe` produced from a Python source tree. The `infracore` layer hosts the platform's components; `contracts` is the type-only seam; `services` wraps external dependencies and exposes infracore's components to plugins; `plugins` are feature units with no direct knowledge of infracore.

This specification is organized as the codebase will be: infracore first, contracts second, services third, plugins fourth, then the cross-cutting concerns (startup, packaging, diagnostics, integration, testing). Decisions S1–S17 are inlined where they apply; the spec does not need to be read alongside the pre-spec report.

---

## 1. Layered overview

PantonicVideo has four layers and a strict import direction. The directional rule is the binding constraint of the platform:

| Layer | Folder | Imports allowed from | External dependencies |
|---|---|---|---|
| 1. infracore | `infracore/` | stdlib only | `PySide6`, `platformdirs`, `pydantic` |
| 2. contracts | `contracts/` | (none from project) | `pydantic`, stdlib `typing` |
| 3. services | `services/` | `infracore`, `contracts` | each service's own libs (e.g., `Pillow`) |
| 4. plugins | `plugins/` (built-in) and `<pantonicvideo-root>/plugins/` (third-party) | `contracts`, `PySide6` | none |

The contracts layer **does not** depend on infracore (architecture §3); infracore **does not** depend on contracts. Where a type would otherwise need to cross this boundary, it is duplicated structurally — see §3.3.

The v1 catalog has **six components** (S1) and **nine services**:

- **Components** (in infracore): `SignalComponent`, `AppStateComponent`, `FilesystemComponent`, `PluginRegistryComponent`, `LoggingComponent`, `InjectorComponent`. Five live under `infracore/bootstrap_components/`; `InjectorComponent` lives at `infracore/injector_component/` and is structurally distinct because it wires the others.
- **Expression services** (one per component): `SignalService`, `AppStateService`, `FilesystemService`, `PluginRegistryService`, `LoggingService`, `InjectorService`.
- **Domain services**: `ProjectService`, `ImageService`, `SubtitleService`.

The PRD's three v1 plugins — Project Launcher, Image Cropping, Subtitle Text Tool — consume these services exclusively through dependency injection. No plugin imports infracore; no plugin imports services by code path; no plugin imports an external library.

---

## 2. Source-tree layout

The development repository layout is fixed below. Every file path the rest of this spec references is rooted here.

```
<repo-root>/
├── infracore/
│   ├── __init__.py
│   ├── app.py                                  # bootstrap entry point (§9)
│   ├── _versions.py                            # infracore release version constant
│   ├── bootstrap_components/
│   │   ├── __init__.py
│   │   ├── signal_component/
│   │   │   ├── __init__.py
│   │   │   ├── signal.py                       # SignalComponent
│   │   │   └── handle.py                       # SubscriptionHandle NewType (S3)
│   │   ├── app_state_component/
│   │   │   ├── __init__.py
│   │   │   └── app_state.py                    # AppStateComponent
│   │   ├── filesystem_component/
│   │   │   ├── __init__.py
│   │   │   └── filesystem.py                   # FilesystemComponent
│   │   ├── plugin_registry_component/
│   │   │   ├── __init__.py
│   │   │   └── plugin_registry.py              # PluginRegistryComponent
│   │   └── logging_component/
│   │       ├── __init__.py
│   │       └── logging.py                      # LoggingComponent
│   ├── injector_component/
│   │   ├── __init__.py
│   │   └── injector.py                         # InjectorComponent
│   ├── lifecycle/
│   │   ├── __init__.py
│   │   ├── hooks.py                            # on_load/on_enable/on_disable/on_unload orchestration
│   │   └── excepthook.py                       # sys.excepthook wrapping (§9.5, S11)
│   ├── manifest/
│   │   ├── __init__.py
│   │   ├── plugin_manifest.py                  # authoritative Pydantic schema
│   │   └── service_manifest.py                 # authoritative Pydantic schema
│   ├── ui_shell/
│   │   ├── __init__.py
│   │   ├── window.py                           # QMainWindow + menus + status bar
│   │   ├── docker_menu.py
│   │   └── alert_panel.py
│   └── version_check.py                        # caret semver helpers (§3.4)
│
├── contracts/
│   ├── pyproject.toml                          # versions independently of infracore (§3.5)
│   └── src/contracts/
│       ├── __init__.py
│       ├── signals.py                          # Signal[T], SubscriptionHandle (mirror)
│       ├── filesystem.py                       # FilesystemService Protocol, FilesystemEvent
│       ├── state.py                            # AppStateService Protocol
│       ├── plugin_registry.py                  # PluginRegistryService Protocol, PluginRecord
│       ├── logging.py                          # LoggingService Protocol
│       ├── injector.py                         # InjectorService Protocol (S2, S17)
│       ├── project.py                          # ProjectService Protocol, Project, ProjectMetadata
│       ├── image.py                            # ImageService Protocol, CropRect, Dimensions, ImageFormat
│       ├── subtitle.py                         # SubtitleService Protocol, SrtOptions
│       ├── manifest.py                         # plugin-facing manifest mirror
│       └── exceptions.py                       # ServiceNotAvailable, ContractVersionMismatch
│
├── services/
│   ├── injector_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── signal_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── app_state_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── filesystem_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── plugin_registry_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── logging_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── project_service/
│   │   ├── manifest.json
│   │   └── service.py
│   ├── image_service/
│   │   ├── manifest.json
│   │   └── service.py
│   └── subtitle_service/
│       ├── manifest.json
│       └── service.py
│
├── plugins/                                    # built-in plugins only
│   ├── project_launcher/
│   │   ├── manifest.json
│   │   └── plugin.py
│   ├── image_cropping/
│   │   ├── manifest.json
│   │   └── plugin.py
│   └── subtitle_text_tool/
│       ├── manifest.json
│       └── plugin.py
│
├── tests/
│   ├── infracore/
│   ├── contracts/
│   ├── services/
│   ├── plugins/
│   └── integration/
│
├── tools/
│   └── integration_agent/                      # gatekeeper (§13)
│
├── pyproject.toml
├── pyinstaller.spec
└── README.md
```

The four top-level package directories (`infracore/`, `contracts/`, `services/`, `plugins/`) are siblings and the import direction follows the table in §1.

---

## 3. The contracts layer

### 3.1 Purpose

`contracts` is a type-only seam: `typing.Protocol` definitions, Pydantic v2 models, enums, and `NewType` aliases. It contains no behavior, no I/O, no logging, no constants other than version strings. It depends only on `pydantic` and stdlib `typing`.

### 3.2 Modules and responsibilities

| Module | Exposes |
|---|---|
| `contracts.signals` | `Signal[T]` Protocol, `Subscription` Protocol, `SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)` |
| `contracts.filesystem` | `FilesystemService` Protocol, `FilesystemEvent` Pydantic model |
| `contracts.state` | `AppStateService` Protocol |
| `contracts.plugin_registry` | `PluginRegistryService` Protocol, `PluginRecord` Pydantic model, `PluginStatus` enum |
| `contracts.logging` | `LoggingService` Protocol, `LogLevel` enum aliased to stdlib `logging` levels, `AlertEntry` Pydantic model |
| `contracts.injector` | `InjectorService` Protocol (S17) |
| `contracts.project` | `ProjectService` Protocol, `Project`, `ProjectMetadata` Pydantic models |
| `contracts.image` | `ImageService` Protocol, `CropRect`, `Dimensions`, `ImageFormat` enum (`PNG`, `JPEG`) |
| `contracts.subtitle` | `SubtitleService` Protocol, `SrtOptions` Pydantic model |
| `contracts.manifest` | Plugin-facing manifest model (mirror of `infracore.manifest.plugin_manifest`), `RequiredService` Pydantic model |
| `contracts.exceptions` | `ServiceNotAvailable`, `ContractVersionMismatch` |

### 3.3 The structural-mirror rule (S3)

Two types appear identically in both infracore and contracts and **never import across the boundary**:

- `SubscriptionHandle`. Defined in `infracore/bootstrap_components/signal_component/handle.py` as:
  ```python
  import uuid
  from typing import NewType
  SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)
  ```
  Mirrored verbatim in `contracts/src/contracts/signals.py`. The integration agent (§13) verifies textual equivalence modulo whitespace; a drift fails the build.

- The plugin manifest model. Authoritative Pydantic schema in `infracore/manifest/plugin_manifest.py`; mirror in `contracts/manifest.py`. The agent compares field names, types, and constraints; structural drift fails the build.

The mirror is justified by the layer-independence rule (architecture §3, S2). Importing across the boundary would force infracore to depend on contracts (forbidden) or contracts to depend on infracore (forbidden). The duplication is small and gated by the agent.

### 3.4 Caret semver and version-string normalization (S4)

Every `min_version` and `service_api_version` string in PantonicVideo is parsed as semver. **Normalization rule**: if fewer than three numeric components are present, missing components are treated as `0`.

- `"1"` → `"1.0.0"`
- `"1.2"` → `"1.2.0"`
- `"1.2.3"` → unchanged

Anything that does not parse as numeric components separated by dots is rejected at manifest validation. Pre-release and build-metadata suffixes are not supported in v1.

**Caret matching**: `^X.Y.Z` matches `>=X.Y.Z, <(X+1).0.0` when `X >= 1`. The semver helpers live in `infracore/version_check.py` and are duplicated functionally in the integration agent — they have no contract-shaped surface, so no contract module is needed.

### 3.5 Versioning of the contracts package itself

The `contracts` package ships at `1.0.0` for v1 launch. Its version is declared in `contracts/pyproject.toml` and read at infracore startup (as a string from `pyproject.toml`; no contracts code is imported during the version check — see §9.4).

Bump rules (caret-style):

- Adding optional fields, new methods on a Protocol, new enum values: minor bump.
- Removing fields, changing method signatures, removing enum values: major bump.

### 3.6 Distribution (S16)

For v1, the `contracts` package is **not** published to PyPI. Plugin authors building outside the source tree clone the PantonicVideo repository and install `contracts` from the local path (`pip install -e ./contracts`). Publication to PyPI is deferred; the `pyproject.toml` is structured so the future publication is a release-engineering task only — no code changes will be required when it happens.

### 3.7 Shared Pydantic models — placement rules

Models that cross the plugin/infracore boundary live in `contracts/`:

- `AlertEntry` — exposed via `Signal[list[AlertEntry]]` from `SignalService.signal_for_alerts()`. Authoritative definition: `contracts.logging`. `LoggingComponent` imports it from contracts at runtime; it is the **only** runtime contracts import made by infracore, justified by the model being a pure data class with no behavior. The integration agent records this single allowed exception.
- `PluginRecord` — exposed via `PluginRegistryService.list_plugins()` and `Signal[list[PluginRecord]]`. Authoritative: `contracts.plugin_registry`. Same rule as `AlertEntry`.
- `RequiredService` — used by both the manifest schema and `InjectorComponent.services_for(...)`. Authoritative: `contracts.manifest`.

The structural-mirror rule (§3.3) applies only to `SubscriptionHandle` and the plugin-manifest model; the three pure-data models above are imported, not mirrored, because an import of a behaviorless data class does not create a structural dependency in the architectural sense (the contracts package would still build with infracore absent).

---

## 4. The infracore layer — components

This section specifies every component's interface and behavior. Components are infracore-internal: nothing outside infracore imports them, and the only consumers are other components and the expression services that wrap them.

### 4.1 Component versioning convention (S9)

Each component's main module declares a module-level constant:

```python
__component_version__: str = "1.0.0"
```

Format: semver under §3.4 rules. This constant is read by:

- The integration agent, when verifying that an expression service's `service_api_version` is consistent with the component it wraps (§13).
- Service compatibility checks at infracore-internal layers, where applicable.

Plugins do not see component versions. External configuration does not reference them.

### 4.2 `SignalComponent`

Location: `infracore/bootstrap_components/signal_component/signal.py`.

The reactive primitive. Builds `Signal[T]` on top of the callback primitives exposed by `FilesystemComponent`, `AppStateComponent`, and `PluginRegistryComponent`. Caches the latest emitted value so synchronous reads return immediately.

Internal API (consumed by other components and by `SignalService`):

```python
def make_signal(
    initial: T,
    register: Callable[[Callable[[T], None]], SubscriptionHandle],
) -> Signal[T]: ...

def subscribe(signal: Signal[T], callback: Callable[[T], None]) -> Subscription: ...
def unsubscribe(subscription: Subscription) -> None: ...
```

`Signal[T]` carries the current value, the registered callbacks, and the unregistration handle. `register` is the callback-registration primitive of the underlying component (e.g., `AppStateComponent.state_observe`); `SignalComponent` wires it once per signal.

The signal abstraction is the **only** observation idiom in v1. There is no polling anywhere.

### 4.3 `FilesystemComponent`

Location: `infracore/bootstrap_components/filesystem_component/filesystem.py`.

The single point of egress for all filesystem writes in PantonicVideo (architecture §8). Writes are serialized **per path**: writes to different paths proceed in parallel; writes to the same path queue. This invariant is the component's responsibility, not the service's.

API:

```python
def read_file(path: Path) -> bytes: ...
def write_file(path: Path, data: bytes) -> None: ...           # serialized per path
def list_dir(path: Path) -> list[Path]: ...
def exists(path: Path) -> bool: ...
def delete(path: Path) -> None: ...                            # serialized per path
def make_dir(path: Path, parents: bool = True) -> None: ...
def watch(path: Path, callback: Callable[[FilesystemEvent], None]) -> SubscriptionHandle: ...
def unwatch(handle: SubscriptionHandle) -> None: ...
```

**Serialization implementation.** A `dict[Path, threading.Lock]` (with a meta-lock to manage acquisition of new entries) provides per-path locks. Each write acquires the path's lock, writes, releases. Locks for paths that have not been touched in the last 60 seconds are evicted lazily by the next acquisition.

**Watch implementation.** `QFileSystemWatcher` is the v1 backing; `watchdog` is the documented fallback if QFileSystemWatcher proves unreliable. Watch events are normalized to `FilesystemEvent` (a Pydantic model with fields `path`, `kind ∈ {created, modified, deleted}`, `timestamp`).

**Log writes are the documented exception** (architecture §8): stdlib `logging` handlers manage their own thread-safety and do not route through `FilesystemComponent`.

### 4.4 `AppStateComponent`

Location: `infracore/bootstrap_components/app_state_component/app_state.py`.

In-memory key-value store, JSON-persisted write-through to `<pantonicvideo-root>/state.json` via `FilesystemComponent`. Values must be JSON-serializable; Pydantic models are accepted and serialized via `.model_dump()`.

API:

```python
def state_get(key: str) -> Any | None: ...
def state_set(key: str, value: Any) -> None: ...
def state_delete(key: str) -> None: ...
def state_observe(key: str, callback: Callable[[Any], None]) -> SubscriptionHandle: ...
def state_unobserve(handle: SubscriptionHandle) -> None: ...
```

**Persistence cadence.** Every `state_set` triggers a write of the full JSON store, routed through `FilesystemComponent.write_file("<pantonicvideo-root>/state.json", ...)`. Volume is small in v1; if measurements demand it, batching can be added without changing the surface.

**Concurrency / last-write-wins (S12).** Writes follow a last-write-wins policy. When two writes to the same key happen within `STATE_WRITE_WARNING_WINDOW_MS = 50` (a module-level constant; not user-configurable in v1), the component logs a `WARNING` via `LoggingComponent` indicating the key, the two values, and the elapsed milliseconds. The warning is diagnostic only; no user-facing effect.

**Corrupt or missing state file.** On startup, if `state.json` is missing or fails to parse as JSON, the store starts empty and a `WARNING` is logged. The corrupt file (if present) is renamed to `state.json.corrupt-<timestamp>` for post-mortem and the application proceeds.

**Observation primitives are callback-shaped, not signal-shaped.** `SignalComponent` constructs the signal abstraction on top.

### 4.5 `PluginRegistryComponent`

Location: `infracore/bootstrap_components/plugin_registry_component/plugin_registry.py`.

Tracks the running set of plugins. Read-only inspection plus a change-notification primitive.

API:

```python
def list_plugins() -> list[PluginRecord]: ...
def observe_plugins(callback: Callable[[list[PluginRecord]], None]) -> SubscriptionHandle: ...
def unobserve_plugins(handle: SubscriptionHandle) -> None: ...

# Internal (called by lifecycle, not by services directly):
def _record_loaded(record: PluginRecord) -> None: ...
def _record_failed(name: str, reason: str) -> None: ...
def _set_enabled(name: str, enabled: bool) -> None: ...
```

`PluginRecord` (Pydantic v2):

```python
class PluginRecord(BaseModel):
    name: str
    version: str
    description: str
    author: str
    status: PluginStatus     # loaded | enabled | disabled | failed
    failure_reason: str | None
    is_builtin: bool
```

Enable/disable transitions go through `PluginRegistryService.enable / disable` (§5.5). The component implements the transitions but does not surface them as a separate API to other components. The `is_builtin` flag is informational; per S6 it has no effect on resolution other than the collision rule (§9.3).

### 4.6 `LoggingComponent`

Location: `infracore/bootstrap_components/logging_component/logging.py`.

Three responsibilities: the infracore log, the per-plugin logs, and the alert sink.

**Infracore log.** Rotating file handler at `<pantonicvideo-root>/logs/infracore.log` — 10 MB per file, 5 backups, captures the `infracore.*` logger hierarchy at `INFO` and above. Installed on the stdlib `logging` root.

**Per-plugin logs.** Rotating file handlers, one per plugin, with the path resolved by `is_builtin`:

| Plugin kind | Log path |
|---|---|
| Built-in | `<pantonicvideo-root>/logs/plugins/<plugin-name>/plugin.log` (S8) |
| Third-party | `<pantonicvideo-root>/plugins/<plugin-name>/logs/plugin.log` |

This split exists because built-in plugins ship inside the `.exe` and have no writable folder of their own. The `LoggingComponent` resolves the path based on the `PluginRecord.is_builtin` flag at first use and caches the handler.

Each per-plugin log: 10 MB per file, 5 backups, captures messages addressed to that plugin name at `INFO` and above.

**Alert sink.** An in-memory list of alert entries, each:

```python
class AlertEntry(BaseModel):
    plugin: str                      # source plugin name (or "infracore")
    level: int                       # WARNING / ERROR / CRITICAL
    summary: str
    timestamp: datetime
    acknowledged: bool = False       # mutated when the user clicks into the entry
```

The alert sink also exposes a callback primitive:

```python
def observe_alerts(callback: Callable[[list[AlertEntry]], None]) -> SubscriptionHandle: ...
```

so `SignalComponent` can construct the signal that drives the status-bar icon's appearance (§7.3).

API surface for callers:

```python
def log(plugin: str, level: int, message: str, **extras: Any) -> None: ...
def raise_alert(plugin: str, level: int, summary: str) -> None: ...
def acknowledge(timestamp: datetime, plugin: str) -> None: ...   # called by the UI on click-through
def list_alerts() -> list[AlertEntry]: ...
def observe_alerts(callback: Callable[[list[AlertEntry]], None]) -> SubscriptionHandle: ...
```

The component holds no plugin-specific identity beyond the `plugin` argument; it does not maintain a registry of plugin loggers — handlers are created lazily on first `log` for a given name.

### 4.7 `InjectorComponent`

Location: `infracore/injector_component/injector.py`.

The injector. Active construction, not passive lookup.

API:

```python
def register_component(name: str, component: object) -> None: ...
def register_service(name: str, manifest: ServiceManifest, factory: Callable[..., object]) -> None: ...
def construct_services() -> None: ...                # topological sort + instantiation
def resolve(name: str, min_version: str) -> object: ...
def services_for(plugin_name: str, required: list[RequiredService]) -> dict[str, object]: ...
```

**Construction order (S5).** `construct_services` performs a topological sort of registered services using their `depends_on` declarations.

- If the sort succeeds, services are instantiated in order. A service whose dependency is missing or whose declared dependency does not satisfy the version requirement under caret rules is **rejected** (logged at `ERROR`); plugins that required it become `failed`.
- **If the sort detects a cycle, every service in the cycle is rejected** (logged at `ERROR` with the cycle's edges enumerated). The remaining acyclic services proceed. Plugins whose `required_services` cannot be satisfied as a result become `failed`. The application does not abort; the cycle is treated like any other service-discovery failure.

**Plugin construction.** `services_for(plugin_name, required)` returns a `dict[str, object]` mapping each `RequiredService.name` to the resolved service instance, raising `ServiceNotAvailable` if any cannot be satisfied. The lifecycle layer catches and translates this into a `failed` `PluginRecord`.


---

## 5. The services layer

Services are folder-discovered at startup, validated against `infracore.manifest.service_manifest`, and registered with `InjectorComponent`. Each service folder contains a `manifest.json` and an entry-point Python module whose name is referenced by the manifest.

### 5.1 Service manifest schema

`infracore/manifest/service_manifest.py` defines the authoritative Pydantic model. The JSON shape:

```json
{
  "name": "image_service",
  "service_api_version": "1.0.0",
  "implementation_version": "1.0.0",
  "entry_point": "service:ImageServiceImpl",
  "depends_on": [
    {"name": "filesystem_service", "min_version": "1.0"},
    {"name": "signal_service", "min_version": "1.0"}
  ]
}
```

Fields:

- `name` (string, lowercase snake_case, unique within the running PantonicVideo instance) — the contract name plugins reference in their `required_services`.
- `service_api_version` (string, semver per §3.4) — the version of the contract this service implements.
- `implementation_version` (string, semver) — the version of this implementation, independent of the contract version.
- `entry_point` (string, `<module>:<class>`) — resolvable from the service folder.
- `depends_on` (list, may be empty) — other services this service consumes, with `name` and `min_version`. Components are not declared here; they are resolved by name within infracore.

Validation is strict (PRD §6.1, D10): unknown fields, missing required fields, malformed JSON all reject the manifest. A rejected manifest produces an `ERROR` log entry; the service is absent from the injector; plugins that required it become `failed`.

### 5.2 `SignalService` (expression service for `SignalComponent`)

Contract: `contracts.signals`. Wraps `SignalComponent`.

```python
class SignalService(Protocol):
    def signal_for_state(self, key: str) -> Signal[Any]: ...
    def signal_for_path(self, path: Path) -> Signal[FilesystemEvent]: ...
    def signal_for_plugins(self) -> Signal[list[PluginRecord]]: ...
    def signal_for_alerts(self) -> Signal[list[AlertEntry]]: ...
    def subscribe(self, signal: Signal[T], callback: Callable[[T], None]) -> Subscription: ...
    def unsubscribe(self, subscription: Subscription) -> None: ...
```

Every other expression service that surfaces an observation (`AppStateService.observe`, `FilesystemService.watch`, `PluginRegistryService.observe_plugins`) and every domain service that surfaces an observation (`ProjectService.observe_current`) delegates to `SignalService`, which delegates to `SignalComponent`.

`service_api_version`: `1.0.0`. `implementation_version`: `1.0.0`. `depends_on`: none (it directly wraps a component; component dependencies are not declared in `depends_on`).

### 5.3 `AppStateService` (expression service for `AppStateComponent`)

Contract: `contracts.state`.

```python
class AppStateService(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...
    def delete(self, key: str) -> None: ...
    def observe(self, key: str) -> Signal[Any]: ...     # delegates to SignalService.signal_for_state
```

**Key conventions** (not enforced; documented for plugin authors):

- `project.path` — the current project's central folder.
- `plugins.<plugin-name>.enabled` (S10) — a boolean indicating whether the plugin should be enabled at startup. Written by `PluginRegistryService.enable / disable`.
- `ui.layout-version` — reserved for future layout-migration use.

`depends_on`: `signal_service >= 1.0`.

### 5.4 `FilesystemService` (expression service for `FilesystemComponent`)

Contract: `contracts.filesystem`. Thin facade over `FilesystemComponent` — adds no serialization of its own.

```python
class FilesystemService(Protocol):
    def read(self, path: Path) -> bytes: ...
    def write(self, path: Path, data: bytes) -> None: ...     # serialized in the component
    def list(self, path: Path) -> list[Path]: ...
    def exists(self, path: Path) -> bool: ...
    def delete(self, path: Path) -> None: ...
    def make_dir(self, path: Path, parents: bool = True) -> None: ...
    def watch(self, path: Path) -> Signal[FilesystemEvent]: ...   # delegates to SignalService
```

Other services that touch the filesystem (`ProjectService`, `ImageService`, `SubtitleService`) route their writes through `FilesystemService`. State-store persistence in `AppStateComponent` routes through `FilesystemComponent` directly (component-to-component; the service does not exist yet at the moment `AppStateComponent` is wired).

`depends_on`: `signal_service >= 1.0`.

### 5.5 `PluginRegistryService` (expression service for `PluginRegistryComponent`)

Contract: `contracts.plugin_registry`.

```python
class PluginRegistryService(Protocol):
    def list_plugins(self) -> list[PluginRecord]: ...
    def enable(self, name: str) -> None: ...
    def disable(self, name: str) -> None: ...
    def observe_plugins(self) -> Signal[list[PluginRecord]]: ...
```

**Enable / disable behavior (S10).** `enable(name)`:

1. Calls `AppStateService.set("plugins.<name>.enabled", True)`.
2. Invokes the lifecycle layer's `on_enable` for that plugin.
3. Updates the `PluginRecord.status` to `enabled`.

`disable(name)` mirrors this with `False` and `on_disable`.

If `on_enable` raises, the plugin is marked `failed` (lifecycle capture, §9.5); the persisted `enabled` flag remains `True` so the user's intent is preserved across restarts. The next launch will attempt to enable again.

`depends_on`: `signal_service >= 1.0`, `app_state_service >= 1.0`.

### 5.6 `LoggingService` (expression service for `LoggingComponent`)

Contract: `contracts.logging`.

```python
class LoggingService(Protocol):
    def log(self, plugin: str, level: int, message: str, **extras: Any) -> None: ...
    def raise_alert(self, plugin: str, level: int, summary: str) -> None: ...
```

The two channels are independent. Both accept the `plugin` argument; the component handles routing. Plugin authors pass their own plugin name; the convention is to read it from a `self._plugin_name` attribute set by the plugin base class on construction.

`depends_on`: none.

### 5.7 `InjectorService` (expression service for `InjectorComponent`)

Contract: `contracts.injector` (S2, S17). The contract surface is intentionally narrow:

```python
class InjectorService(Protocol):
    def resolve(self, name: str, min_version: str) -> object: ...
    # raises ServiceNotAvailable if no service named `name` satisfies `min_version`
```

v1 has no in-tree consumer. The contract exists so service-to-service late binding (a future need) can be added without bumping the contracts package.

`depends_on`: none.

### 5.8 `ProjectService` (domain service)

Contract: `contracts.project`.

```python
class Project(BaseModel):
    central_folder: Path

class ProjectMetadata(BaseModel):
    image_source_folders: list[Path] = []
    audio_source_folders: list[Path] = []
    config_folders: dict[str, Path] = {}    # external system name -> folder
    extra: dict[str, Any] = {}              # extensible by minor bump

class ProjectService(Protocol):
    def get_current(self) -> Project | None: ...
    def set_current(self, folder: Path) -> None: ...
    def get_metadata(self) -> ProjectMetadata: ...
    def update_metadata(self, updater: Callable[[ProjectMetadata], ProjectMetadata]) -> None: ...
    def observe_current(self) -> Signal[Project | None]: ...
```

**Persistence layout.** Each project's central folder contains `pantonicvideo-project.json` at its root. The current project is stored in `AppStateService` under `project.path`.

**`set_current(folder)` behavior:**

1. If `folder/pantonicvideo-project.json` exists: load and validate via Pydantic.
2. If absent: create with default-empty `ProjectMetadata`.
3. Write `project.path = str(folder)` to app state. The state set fires `observe_current`.

**`update_metadata(updater)` atomicity (S13).** Read-modify-write through `FilesystemService`:

1. `current = read_metadata_file()` (via `FilesystemService.read`).
2. `new = updater(current)`.
3. `FilesystemService.write(metadata_path, new.model_dump_json().encode())`.

The per-path serialization in `FilesystemComponent` ensures that two concurrent `update_metadata` calls do not interleave: the second call's read sees the first call's write. The component's lock for the metadata path queues the second call until the first completes.

`depends_on`: `app_state_service >= 1.0`, `filesystem_service >= 1.0`, `signal_service >= 1.0`.

### 5.9 `ImageService` (domain service)

Contract: `contracts.image`. Wraps Pillow.

```python
class CropRect(BaseModel):
    left: int
    top: int
    width: int
    height: int

class Dimensions(BaseModel):
    width: int
    height: int

class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"

class ImageService(Protocol):
    def apply_crop(self, source: Path, rect: CropRect, output: Path) -> None: ...
    def resize(self, source: Path, dimensions: Dimensions, output: Path) -> None: ...
    def supported_formats(self) -> list[ImageFormat]: ...
```

Both write operations route their output through `FilesystemService.write`. Plugins handle preview rendering with Qt's built-in scaling and do not call this service for previews — the service is for committed operations only (PRD §8.7, D7).

`depends_on`: `filesystem_service >= 1.0`.

### 5.10 `SubtitleService` (domain service)

Contract: `contracts.subtitle`. v1 supports SRT only.

```python
class SrtOptions(BaseModel):
    cps: int = 17                      # characters per second pacing
    max_line_chars: int = 42
    min_duration_ms: int = 1000
    gap_ms: int = 100

class SubtitleService(Protocol):
    def text_to_srt(self, text: str, output: Path, options: SrtOptions) -> None: ...
```

Adding `.vtt` / `.ass` later is expected to add new methods rather than changing this signature — extension without destructive refactoring (PRD §8.8, D8).

The output write routes through `FilesystemService.write`.

`depends_on`: `filesystem_service >= 1.0`.

### 5.11 Service entry-point pattern

Each service's `service.py` exposes the implementation class named in `entry_point`. The class accepts its declared dependencies as constructor arguments, named by the service `name` from the manifest's `depends_on`:

```python
# services/image_service/service.py
from contracts.image import ImageService, CropRect, Dimensions, ImageFormat
from contracts.filesystem import FilesystemService

class ImageServiceImpl:                      # implements ImageService Protocol structurally
    def __init__(self, filesystem_service: FilesystemService) -> None:
        self._fs = filesystem_service

    def apply_crop(self, source, rect, output):
        ...

    def resize(self, source, dimensions, output):
        ...

    def supported_formats(self):
        return [ImageFormat.PNG, ImageFormat.JPEG]
```

`InjectorComponent` reads the manifest's `depends_on`, resolves each by name, and passes them to the constructor in declared order. Constructor parameter names must match the dependency `name` values; the integration agent verifies this at build time (§13).

---

## 6. The plugins layer

### 6.1 Plugin manifest schema

`infracore/manifest/plugin_manifest.py` defines the authoritative model. The JSON shape:

```json
{
  "name": "image_cropping",
  "version": "1.0.0",
  "contracts_min_version": "1.0",
  "author": "PantonicVideo",
  "description": "Crop and resize static images.",
  "entry_point": "plugin:ImageCroppingPlugin",
  "required_services": [
    {"name": "image_service", "min_version": "1.0"},
    {"name": "filesystem_service", "min_version": "1.0"},
    {"name": "logging_service", "min_version": "1.0"},
    {"name": "project_service", "min_version": "1.0"}
  ],
  "inputs": [],
  "outputs": [],
  "permissions": []
}
```

Fields:

- `name` (string, snake_case, unique).
- `version` (semver).
- `contracts_min_version` (semver) — minimum version of the `contracts` package (PRD D12; tracks contracts, not infracore).
- `author` (string).
- `description` (string).
- `entry_point` (`<module>:<class>`).
- `required_services` (list of `{name, min_version}`).
- `inputs`, `outputs` (lists of Pydantic model references; may be empty).
- `permissions` (reserved for v2; parsed and ignored — PRD §14, architecture §12).

Validation is strict; same regime as service manifests.

### 6.2 Lifecycle hooks

A plugin must implement four hooks (PRD §5.7):

```python
class Plugin(Protocol):
    def on_load(self, services: dict[str, object]) -> None: ...
    def on_enable(self) -> None: ...
    def on_disable(self) -> None: ...
    def on_unload(self) -> None: ...
```

`on_load` receives the dict of resolved services, keyed by the manifest's `required_services[].name`. The plugin stores the references it needs as instance attributes; the dict is not retained.

A plugin missing any hook fails `on_load` with reason "lifecycle hook not implemented: `<name>`" and is marked `failed`.

**Exception capture.** Each hook call is wrapped in try/except by `infracore/lifecycle/hooks.py`. An exception during any hook:

1. Is logged at `ERROR` to the per-plugin log.
2. Is raised as an alert at `ERROR` with summary "plugin `<name>` raised in `on_<hook>`: `<exception class>: <truncated message>`".
3. Marks the plugin `failed` with the truncated message as `failure_reason`.
4. Does not propagate; the application continues.

### 6.3 Configuration

Plugin configuration is the plugin's own concern. Convention: `<plugin-folder>/config.json`. For built-in plugins (no writable folder), the convention is `<pantonicvideo-root>/plugins-config/<plugin-name>.json`; plugins are responsible for reading/writing through `FilesystemService`.

### 6.4 Internal autonomy

Beyond the import constraints (no infracore, no service code paths, no external libraries) plugins have full autonomy. They may compute, transform, render Qt widgets, and orchestrate however they choose. They may not reach the filesystem, network, or external libraries except through services.

### 6.5 The v1 plugins

#### Project Launcher

`plugins/project_launcher/`. Required services: `project_service`, `filesystem_service`, `logging_service`. UI: a folder picker and a confirmation button. On commit, calls `ProjectService.set_current(folder)`.

Auto-enabled on first run (PRD §7.5; the lifecycle layer keys this behavior on the plugin name `project_launcher`).

#### Image Cropping

`plugins/image_cropping/`. Required services: `image_service`, `filesystem_service`, `project_service`, `logging_service`. UI: image picker, crop/resize controls (Qt-rendered preview computed inside the plugin), commit button. On commit, calls `ImageService.apply_crop` or `ImageService.resize`.

#### Subtitle Text Tool

`plugins/subtitle_text_tool/`. Required services: `subtitle_service`, `filesystem_service`, `project_service`, `logging_service`. UI: text input, optional SRT pacing controls, destination picker, commit button. On commit, calls `SubtitleService.text_to_srt`.

---

## 7. The UI shell

### 7.1 Window

A standard Windows `QMainWindow` with light-mode styling. The window opens with the user's last-saved layout (§7.4) or, on first run, with the Project Launcher docker only.

### 7.2 Menu bar

A top menu bar with at least:

- **Docker menu.** One toggle entry per plugin whose manifest validated and whose `required_services` are satisfied — i.e., every plugin whose `PluginRecord.status` is `loaded`, `enabled`, or `disabled`. Plugins with status `failed` are not listed; their failure surfaces only under the alert icon.

  Each toggle reflects the current `enabled` state and, when clicked, calls `PluginRegistryService.enable` or `disable` accordingly.

  The plugin's `description` (S15) is shown as a tooltip on the menu entry.

### 7.3 Status bar

A status bar at the bottom of the window with one element: the **alert icon**.

The icon is a button styled by the highest unacknowledged alert level present in `LoggingComponent`'s alert sink:

| State | Trigger |
|---|---|
| Quiescent | No unacknowledged alerts |
| `WARNING` styling | Highest unacknowledged is `WARNING` |
| `ERROR` styling | Highest unacknowledged is `ERROR` |
| `CRITICAL` styling | Highest unacknowledged is `CRITICAL` |

The icon subscribes to `SignalService.signal_for_alerts()` and recomputes its state on each emission.

**Click behavior.** Clicking opens a dropdown panel listing alerts grouped by source plugin, newest first. Each row shows `level`, `summary`, `timestamp`, and the plugin's `author` (S15).

**Drill-in.** Clicking a row opens a detail view showing the full summary, the path to the originating plugin's log file (resolved per the table in §4.6), and an "open log folder" button that invokes the OS file explorer at the log's directory. The detail view does not embed log contents.

**Acknowledgement (S14).** Drilling into an alert calls `LoggingComponent.acknowledge(timestamp, plugin)`, which sets `acknowledged=True` on the entry and re-emits the alert signal. There is no explicit "clear all" control. Acknowledgement state is in-memory only and resets on restart — at startup the alert sink is empty.

### 7.4 Layout persistence

Docker positions, sizes, and visibility persist across restarts. Single layout — no named layouts, no workspaces.

Layout file: `<pantonicvideo-root>/layout.json`:

```json
{
  "version": 1,
  "saved_at": "<ISO 8601 timestamp>",
  "qt_state": "<base64-encoded QByteArray from QMainWindow.saveState()>"
}
```

**Recovery on mismatch (S7).** The layout file's `version` is checked at startup. If:

- the file is absent, **or**
- the file is malformed (invalid JSON, missing fields), **or**
- the file's `version` is unrecognized by the running infracore (any value the current code does not know how to read),

then infracore proceeds as on first run (§7.5) and logs a `WARNING` to the infracore log naming the cause. The malformed file (if present and parseable enough to read at all) is renamed to `layout.json.unrecognized-<timestamp>` for post-mortem. Startup does not fail.

A successful layout load applies the Qt state and brings up exactly the dockers the previous session had visible.

### 7.5 First-run experience

When `<pantonicvideo-root>/layout.json` is absent (or falls back per §7.4), infracore enables the Project Launcher only and renders its docker in a default position. Other built-in plugins remain `loaded`, appear in the Docker menu, and are not enabled. No welcome modal, no tutorial.

The first-run condition is keyed on the absence of the layout file, not on app-state. This means that resetting the application by deleting `<pantonicvideo-root>/layout.json` produces a first-run experience even if `state.json` retains data.

---

## 8. Filesystem hierarchies

### 8.1 Source-tree root

The development repository (§2). Contains code that gets compiled into the `.exe`, plus the built-in plugins and the v1 service catalog. The integration agent operates on this tree.

### 8.2 User-data root

`<pantonicvideo-root>` — `%APPDATA%\PantonicVideo` by default, overridable via a startup setting. Resolved at startup using `platformdirs` and the optional override. The override is the only thing infracore reads before establishing the rest of its filesystem.

```
<pantonicvideo-root>/
├── config.json                              # infracore's own configuration; the override lives here on second launch
├── layout.json                              # docker layout (§7.4)
├── state.json                               # application state store (§4.4)
├── logs/
│   ├── infracore.log                        # rotating, 10 MB × 5
│   └── plugins/                             # built-in plugin logs (S8)
│       └── <plugin-name>/
│           └── plugin.log                   # rotating, 10 MB × 5
└── plugins/                                 # third-party plugins only
    └── <plugin-name>/
        ├── manifest.json
        ├── <entry_point>.py
        ├── config.json                      # plugin's own configuration (convention)
        └── logs/
            └── plugin.log                   # rotating, 10 MB × 5
```

Path resolution uses `pathlib.Path` throughout. Built-in plugins do not appear under `<pantonicvideo-root>/plugins`; they are bundled into the `.exe` and discovered through PyInstaller's `_MEIPASS` mechanism.


---

## 9. Startup sequence

`infracore/app.py` executes the steps below, in order, between process start and the Qt event loop running. Each step's failure mode is specified.

### 9.1 Resolve the user-data root

Read the override from a previously-written `config.json` if present (in a well-known platform-specific location); otherwise use `platformdirs.user_data_dir("PantonicVideo")`. Create `<pantonicvideo-root>` and its standard subfolders (`logs/`, `logs/plugins/`, `plugins/`) if missing.

Failure: if the resolved root is unwritable, the application aborts with a fatal error written to stderr (no log file is available yet).

### 9.2 Configure the bootstrap log handler

Attach a `RotatingFileHandler` to the stdlib `logging` root, writing to `<pantonicvideo-root>/logs/infracore.log`. This is the pre-component logging facility so that startup itself can log. Once `LoggingComponent` is constructed (§9.3), this handler stays in place — `LoggingComponent` extends rather than replaces it.

### 9.3 Construct components

In order, with each registered with `InjectorComponent` under its name:

1. `InjectorComponent` (constructed first; it will hold the rest).
2. `SignalComponent`.
3. `FilesystemComponent`.
4. `AppStateComponent` (consumes `SignalComponent`, `FilesystemComponent`).
5. `LoggingComponent` (consumes `FilesystemComponent` for path resolution; the bootstrap log handler stays attached to the root).
6. `PluginRegistryComponent` (consumes the four above).

The order is fixed in code; component construction is not folder-discovered. A failure at any step (constructor raises) aborts startup with a fatal log entry — there is no graceful degradation when a component is broken (architecture §9, "Component failures are not a runtime concept").

### 9.4 Verify the contracts package and load app state

Read `contracts/pyproject.toml` (or its bundled equivalent inside the `.exe`) and cache the version string. No contracts code is imported by infracore.

Then `AppStateComponent.load()` reads `<pantonicvideo-root>/state.json` through `FilesystemComponent`. If missing or corrupt, the store starts empty (per §4.4).

### 9.5 Install the wrapped `sys.excepthook` (S11)

`infracore/lifecycle/excepthook.py` wraps the existing `sys.excepthook`:

```python
_previous_hook = sys.excepthook

def _pantonicvideo_excepthook(exc_type, exc_value, traceback):
    plugin_name = _attribute_to_plugin(traceback)   # walks frames, matches against PluginRegistryComponent
    if plugin_name is not None:
        LoggingComponent.log(plugin_name, ERROR, format_exception(exc_type, exc_value, traceback))
        LoggingComponent.raise_alert(plugin_name, ERROR, f"{exc_type.__name__}: {exc_value}")
        PluginRegistryComponent._record_failed(plugin_name, f"{exc_type.__name__}: {str(exc_value)[:200]}")
    _previous_hook(exc_type, exc_value, traceback)   # always called, debugger-friendly
```

`_attribute_to_plugin` walks the traceback's frames, comparing `__file__` against the known plugin module roots maintained by `PluginRegistryComponent`. The first frame whose file lies inside a plugin's discovery folder (bundled or user-data) attributes the exception to that plugin. If no frame matches, the hook treats the exception as infracore's and skips the plugin-specific routing — only the previous hook is called.

### 9.6 Discover services

Scan the bundled `services/` folder (resolved via `_MEIPASS` inside the `.exe`, or directly in dev mode). For each subfolder:

1. Validate `manifest.json` against `infracore.manifest.service_manifest`. Failure → log `ERROR`, skip this service.
2. Resolve the entry point (`<module>:<class>`). Failure → log `ERROR`, skip.
3. Register with `InjectorComponent.register_service(name, manifest, factory)` where `factory` is a callable that constructs the entry-point class with its dependencies.

After all manifests are registered, call `InjectorComponent.construct_services()`:

- Topological sort of `depends_on` (S5). Cycles → log `ERROR` enumerating the cycle's edges; reject every service in the cycle.
- For each service in topological order: resolve dependencies, instantiate the factory. Constructor failure → log `ERROR`, mark the service rejected. Dependents of a rejected service are also rejected.

Discovery proceeds with the remaining services. The application does not abort.

### 9.7 Discover plugins

Two scan locations, in this order:

1. The bundled built-in `plugins/` folder (via `_MEIPASS`).
2. The user-data `<pantonicvideo-root>/plugins/` folder.

For each subfolder:

1. Validate `manifest.json` against `infracore.manifest.plugin_manifest`. Failure → record as `failed` with reason "manifest validation: `<details>`".
2. **Built-in vs. third-party name collision (S6).** If a plugin in scan location 2 has a `name` already discovered in scan location 1, the third-party plugin is recorded as `failed` with reason "name collides with built-in plugin `<n>`" and logged at `ERROR`. Built-ins always win.
3. Verify the running `contracts` version satisfies `contracts_min_version` (caret semver per §3.4) using the cached version string from §9.4. Failure → record as `failed` with reason "contracts version `<actual>` does not satisfy `<required>`".
4. Verify each `required_services` entry resolves against `InjectorComponent` with a `service_api_version` satisfying the plugin's `min_version`. Failure → record as `failed` with reason "service `<n>` not available" or "service `<n>` version `<actual>` does not satisfy `<required>`".
5. Successful → record as `loaded` (not yet enabled), with `is_builtin` set per scan location.

### 9.8 Construct the UI shell

Build the `QMainWindow`. Attach the menu bar; populate the Docker menu from `PluginRegistryComponent.list_plugins()` (excluding `failed`). Attach the status bar with the alert icon subscribed to `SignalService.signal_for_alerts()`.

### 9.9 Restore layout

Read `<pantonicvideo-root>/layout.json`. On any of the failure modes in §7.4, fall back to first-run per §7.5 and log `WARNING`. On success, apply the Qt state.

### 9.10 Call `on_load` on every loaded plugin

For each `PluginRecord` with status `loaded`, `InjectorComponent.services_for(plugin_name, required)` resolves the services dict, the plugin class is instantiated (no arguments), and `on_load(services)` is called. Exception capture is per §6.2.

A plugin that successfully completes `on_load` remains `loaded`.

### 9.11 Call `on_enable` on every plugin whose persisted state says it should be enabled

For each `loaded` plugin, read `AppStateService.get(f"plugins.{name}.enabled")`. If `True`, call `on_enable` and update the `PluginRecord.status` to `enabled`.

**First-run precedence.** If §9.9 fell back to first-run (layout absent or unrecognized), `project_launcher` is enabled unconditionally — **the persisted `plugins.project_launcher.enabled` value is ignored for this single launch and overwritten to `True`**. This guarantees the user always has a way back into the application after a layout reset, even if a previous session had explicitly disabled the launcher. For all other plugins on a first-run, the persisted state is honored.

### 9.12 Start the Qt event loop

`app.exec()`. Control returns when the event loop exits.

### 9.13 Shutdown

Reverse the relevant steps:

1. Call `on_disable` on every `enabled` plugin.
2. Call `on_unload` on every `loaded` plugin.
3. Save the layout via `QMainWindow.saveState()` to `<pantonicvideo-root>/layout.json`.
4. Flush the state store (write-through means there is little to flush).
5. Close logging handlers.

Each step captures exceptions and logs at `ERROR`; shutdown does not abort on a single failure.

---

## 10. Layer boundaries and import rules

The four-layer rule is enforced as import constraints. The integration agent verifies them; this section defines them.

### 10.1 Allowed import edges

| From → To | Allowed | Notes |
|---|---|---|
| `infracore.*` → stdlib, `PySide6`, `platformdirs`, `pydantic` | yes | infracore's only external deps |
| `infracore.*` → `contracts.*` | **data models only** | `AlertEntry`, `PluginRecord`, `RequiredService` (§3.7); no Protocol imports, no behavior |
| `infracore.*` → `services.*` | **no** | infracore is unaware of services as code |
| `infracore.*` → `plugins.*` | **no** | infracore is unaware of plugins entirely |
| `infracore.bootstrap_components.*` → other `infracore.bootstrap_components.*` | yes, ordered | construction order resolves the DAG |
| `infracore.injector_component` → `infracore.bootstrap_components.*` | yes | the injector knows about all components |
| `contracts.*` → `pydantic`, `typing`, `uuid` | yes | contracts has no other dependencies |
| `contracts.*` → `infracore.*` | **no** | layer-independence rule |
| `contracts.*` → `services.*`, `plugins.*` | **no** | trivially forbidden |
| `services.<X>` → `infracore.*` | yes | services consume components |
| `services.<X>` → `contracts.*` | yes | for Protocols implemented and consumed |
| `services.<X>` → `services.<Y>` (other service) | **no** | services consume each other only via injection |
| `services.<X>` → `plugins.*` | **no** | trivially forbidden |
| `services.<X>` → service's declared external libs | yes | listed in `pyproject.toml` extras |
| `plugins.<X>` → `contracts.*` | yes | for Protocol typing |
| `plugins.<X>` → `PySide6` | yes | UI rendering |
| `plugins.<X>` → `infracore.*` | **no** | strict |
| `plugins.<X>` → `services.*` | **no** | services arrive via injection only |
| `plugins.<X>` → `plugins.<Y>` (other plugin) | **no** | cross-plugin direct calls forbidden (PRD §4.3) |
| `plugins.<X>` → any external library | **no** | strict |

The agent checks **transitive** imports as well as direct ones (architecture §6.3) — this catches the failure modes that runtime injection does not surface.

### 10.2 Runtime expression of the rules

`InjectorComponent` is the runtime expression: plugins receive only services through constructor injection, never components, never other plugins, never external libraries. The plugin's only handle on a service is the `Protocol`-typed reference passed at `on_load`.

Manifest schemas constrain what a plugin or service can ask for in the first place — there is no manifest field for "external library dependency from a plugin," for instance.

These three mechanisms (integration-time analysis, injector-shaped construction, manifest schemas) layer on top of each other.

---

## 11. Diagnostics and failure containment

The architectural goal is that no single non-fatal failure cascades.

| Failure | Surface | Routing |
|---|---|---|
| Plugin lifecycle hook raises | Per-plugin log (`ERROR`) + alert (`ERROR`) + `PluginRecord.status = failed` | Lifecycle layer captures (§6.2, §9.10) |
| Plugin Qt slot raises | Per-plugin log (`ERROR`) + alert (`ERROR`) + `PluginRecord.status = failed` | Wrapped excepthook (§9.5) |
| Plugin manifest invalid | `PluginRecord.status = failed` with reason | Discovery (§9.7) |
| Plugin's `required_services` unsatisfied | `PluginRecord.status = failed` with reason | Discovery (§9.7) |
| Service raises during call | Propagates to plugin caller; if uncaught, hits lifecycle boundary | Plugin's responsibility unless it bubbles |
| Service manifest invalid | Service rejected; log `ERROR`; absent from injector | Discovery (§9.6) |
| Service constructor raises | Service rejected; log `ERROR`; absent from injector | Construction (§9.6) |
| Service `depends_on` cycle | Every service in the cycle rejected; log `ERROR` | Construction (§9.6, S5) |
| Component constructor raises | **Fatal**; abort startup with fatal log | §9.3 |
| `state.json` corrupt | Empty store + `WARNING`; corrupt file renamed | §4.4, §9.4 |
| `layout.json` malformed/unknown version | First-run layout + `WARNING`; corrupt file renamed | §7.4, §9.9 (S7) |

The **alert icon** is the one user-visible diagnostic surface (§7.3); the **logs** are the secondary surface for detail. The Docker menu hides `failed` plugins so the user is not invited to enable something that cannot run.

---

## 12. Versioning interactions

Five version axes (PRD §11, plus the hidden component axis):

| Axis | Where declared | Read by | Caret-matched |
|---|---|---|---|
| Contracts package | `contracts/pyproject.toml` | `infracore.version_check` at startup | Against plugin's `contracts_min_version` |
| Service contract (`service_api_version`) | Each service's `manifest.json` | `InjectorComponent` | Against plugin's `required_services[].min_version` |
| Service implementation (`implementation_version`) | Each service's `manifest.json` | Integration agent only | Diagnostic, not enforced at runtime |
| Infracore release | `infracore/_versions.py` | Release engineering | Not matched against anything at runtime (PRD D12) |
| Component (`__component_version__`) | Each component module | Integration agent | Against expression service compatibility (S9) |

**Compatibility discipline.** An infracore release that changes a component's behavior in a way visible through its expression service must bump the corresponding `service_api_version`. This is the discipline that lets plugin authors ignore infracore's release version: they pin contracts and services, never infracore.

**Caret rules** (§3.4): `^X.Y.Z` matches `>=X.Y.Z, <(X+1).0.0` for `X >= 1`. One- and two-component versions are normalized by appending zeros.

---

## 13. The integration agent

The integration agent is a project-level tool, not part of the runtime application. It lives at `tools/integration_agent/` and runs in two contexts:

- **Plugin/service promotion.** When a developer proposes a new plugin or a new service, the agent verifies it before it is admitted to the platform.
- **Build-time invariants.** As part of CI on the source tree, the agent verifies that no existing code has drifted out of compliance.

### 13.1 Agent responsibilities

| Check | Mechanism | Failure mode |
|---|---|---|
| Plugin manifest validates | Run `infracore.manifest.plugin_manifest.PluginManifest.model_validate` | Reject |
| Service manifest validates | Run `infracore.manifest.service_manifest.ServiceManifest.model_validate` | Reject |
| Plugin imports respect §10.1 | Static AST analysis, transitive | Reject |
| Service imports respect §10.1 | Static AST analysis, transitive | Reject |
| Infracore imports from `contracts` are restricted to the §3.7 allowlist | Static AST analysis (allowlist: `AlertEntry`, `PluginRecord`, `RequiredService`, plus the manifest mirror's data classes) | Fail build |
| Service constructor parameter names match `depends_on` names | AST inspection of the entry-point class's `__init__` | Reject |
| Contracts mirror schemas have not drifted from infracore's authoritative schemas | Compare Pydantic field shapes (name, type, constraints) | Fail build |
| `SubscriptionHandle` declarations match across infracore and contracts | Textual comparison modulo whitespace (S3) | Fail build |
| Each component module declares `__component_version__` | AST inspection | Fail build |
| Expression service `service_api_version` is compatible with the wrapped component's `__component_version__` | Compare under caret rules | Warn (not fail; the discipline is human-enforced, the agent surfaces drift) |

### 13.2 Agent strictness

Per PRD D10, the agent is strict: minor issues are fixed or sent back, never accepted as-is. The runtime's loose error handling (failed plugins surface but do not abort) is the user-side counterweight; the agent is the developer-side counterweight.

### 13.3 Agent extensions for future services

When the agent identifies a recurring external dependency in PoC scripts, it may propose scaffolding a new domain service. When it identifies duplication across plugins, it may propose an auxiliary service. When it identifies cohesion-diluting procedures, it may propose a simplifying service. v1 ships only domain and expression services; the agent's promotion path is the intended route for the other two flavors.

---

## 14. Stack and packaging

| Area | Choice |
|---|---|
| GUI framework | PySide6 (LGPL) |
| Language | Python 3.12 (fallback to 3.11 if PyInstaller issues arise) |
| Packaging | PyInstaller, one-file `.exe` mode, splash screen during unpack |
| Dependency management | `uv` + `pyproject.toml` |
| Plugin manifest format | JSON, validated by Pydantic v2 (authoritative in `infracore/manifest/`, mirror in `contracts/manifest.py`) |
| Service manifest format | JSON, validated by Pydantic v2 (`infracore/manifest/service_manifest.py`) |
| Plugin discovery | Filesystem scan: bundled `plugins/` (built-ins) and `<pantonicvideo-root>/plugins` (third-party) |
| Service discovery | Filesystem scan of bundled `services/` |
| Service injection | `InjectorComponent` (active injector with topological sort) |
| Service contracts | `typing.Protocol` + `service_api_version`, distributed in the `contracts` package |
| Plugin I/O contracts | Pydantic v2 models, referenced by name in manifest |
| Application state store | In-memory key-value, JSON-persisted, write-through |
| Layout storage | `<pantonicvideo-root>/layout.json` (versioned wrapper around base64 Qt state) |
| Logging | stdlib `logging`; rotating handlers (10 MB × 5) |
| Testing | `pytest`, `pytest-qt` for UI tests |
| Distribution | Public GitHub repository; `.exe` for fast usage; `contracts` package distributed via the repo for v1 (S16) |

### 14.1 PyInstaller configuration

`pyinstaller.spec` produces a one-file `.exe` with a splash screen. The bundle includes:

- The `infracore/` package and its dependencies (PySide6, `platformdirs`, `pydantic`).
- The `contracts/` package.
- Every service folder under `services/`, including each `manifest.json` and entry-point module, plus each service's external dependencies (e.g., Pillow for `ImageService`).
- Every built-in plugin folder under `plugins/`, including each `manifest.json` and entry-point module.

UPX compression, excluded-module lists, and a fallback to one-folder packaging are not committed in v1 (PRD D16); they are tuning levers exercised once cold-start measurements exist.

### 14.2 Runtime path resolution

At runtime, infracore distinguishes:

- **Bundled paths** (services and built-in plugins) — resolved through `sys._MEIPASS` (or `Path(__file__).parent` in dev mode).
- **User-data paths** (third-party plugins, logs, state, layout, config) — resolved relative to `<pantonicvideo-root>`.

Both produce equivalent records in the registry; the distinction matters only for discovery.

---

## 15. Security posture

Plugins run in-process with full Python capabilities. For single-user home use, this is accepted (PRD §14, architecture §12). The manifest's `permissions` field is reserved for v2; in v1 it is parsed and ignored.

No sandboxing, no IPC isolation, no out-of-process plugins. A future change to this stance would be invasive — it would add an IPC layer between plugins and services and is not absorbable without modification to infracore.

---

## 16. Testing

Test directory layout mirrors the source tree:

```
tests/
├── infracore/              # unit tests per component
├── contracts/              # mirror-drift tests, type-shape tests
├── services/               # unit tests per service (with mocked components)
├── plugins/                # unit tests per plugin (with mocked services)
└── integration/            # end-to-end startup/shutdown, three-plugin smoke tests
```

### 16.1 Unit-test discipline per layer

- **infracore.** Each component is tested in isolation. Components that consume other components use real instances (the components are small and fast); no mocking inside infracore.
- **contracts.** No behavior to test; tests verify Pydantic schemas, enum values, and the structural-mirror invariants (`SubscriptionHandle` parity, manifest mirror parity). The latter overlaps with what the integration agent checks; the test suite is the runtime-facing version of that check.
- **services.** Each service is tested with mocked dependencies (mocked components for expression services, mocked services for domain services). Pillow and similar libraries are stubbed in unit tests; one integration smoke test per domain service exercises the real library.
- **plugins.** Each plugin is tested with mocked services. UI is exercised via `pytest-qt`.

### 16.2 Integration tests

End-to-end startup tests run `infracore/app.py` against a temporary `<pantonicvideo-root>` and verify:

- Clean startup with the three built-in plugins. Project Launcher is enabled; the others are loaded but not enabled.
- Startup with a deliberately broken plugin in user-data (malformed manifest, raised exception, missing service) — the broken plugin appears under the alert icon; the application is otherwise healthy. (PRD §2.3, third success criterion.)
- Startup with a `state.json` containing `plugins.image_cropping.enabled: True` — Image Cropping is enabled at launch.
- Startup with an unrecognized `layout.json` version — falls back to first-run, logs `WARNING`, application is healthy.
- A built-in/third-party name collision — third-party is `failed`, built-in is `enabled` per persisted state.

### 16.3 Coverage targets

No hard coverage threshold for v1. The integration suite is the meaningful guarantee; unit-test coverage is a tool the developer uses, not a gate.

---

## 17. Out of scope (named for the record)

These are deferred per PRD §15 and architecture §12. The architecture must not foreclose them.

- **Pipelines / workflows.** v2 PRD. Architectural prerequisites met in v1: typed signals, well-defined service inputs/outputs, registry enumeration.
- **`CapCutAdapterService` and the CapCut plugin.** v1.1+. Will live under `services/capcut_adapter_service/`; depends on reverse-engineering CapCut's JSON format.
- **Permissions enforcement** for the manifest's `permissions` field. v2+.
- **Hot-reload of plugins.** Possibly forever out. The lifecycle hook invariants assume a plugin loads once and unloads once per process.
- **Plugin marketplace, in-app plugin browser, third-party plugin curation.** Not committed.
- **macOS support.** Not committed.
- **Dark mode, theming, named layouts, workspaces.** Not committed.
- **System tray, autostart, native OS notifications.** Not committed.
- **Sandboxing or out-of-process plugins.** Not committed.
- **Image formats beyond PNG/JPEG; subtitle formats beyond SRT.** Adding them is a minor bump, not a rewrite.
- **State store conflict-resolution policy** beyond the `WARNING` log.

---

## 18. Traceability

### 18.1 Pre-spec decisions to spec sections

| Decision | Resolution | Spec section |
|---|---|---|
| S1 | Six v1 components | §1, §4 |
| S2 | `contracts/injector.py` added | §2, §3.2, §5.7 |
| S3 | `SubscriptionHandle` mirror, `NewType[uuid.UUID]` | §3.3, §13.1 |
| S4 | Caret semver normalization rule | §3.4 |
| S5 | Service `depends_on` cycles rejected, not fatal | §4.7, §9.6 |
| S6 | Built-ins win on name collision | §9.7 |
| S7 | Layout version mismatch falls back to first-run | §7.4, §9.9 |
| S8 | Built-in plugin logs under `<pantonicvideo-root>/logs/plugins/<n>/` | §4.6, §8.2 |
| S9 | `__component_version__` constant | §4.1, §13.1 |
| S10 | `plugins.<n>.enabled` in app state | §4.5, §5.3, §5.5, §9.11 |
| S11 | Wrapped `sys.excepthook` | §9.5 |
| S12 | 50 ms warning window hard-coded | §4.4 |
| S13 | `update_metadata` atomicity via per-path serialization | §5.8 |
| S14 | Click-to-acknowledge, in-memory only | §7.3 |
| S15 | `description` in tooltip; `author` in alert detail | §7.2, §7.3 |
| S16 | `contracts` not on PyPI for v1; install from local path | §3.6 |
| S17 | `Injector` Protocol with single `resolve` method | §5.7 |

### 18.2 PRD decisions to spec sections

For continuity with the PRD's decision register:

- **D1, D2** (signal abstraction): §3.2, §4.2, §5.2
- **D3** (plugin registry): §4.5, §5.5
- **D4** (logging dual channel): §4.6, §5.6
- **D5** (state store API shape): §4.4, §5.3
- **D6** (project metadata): §5.8
- **D7** (image service scope): §5.9
- **D8** (subtitle service scope): §5.10
- **D9** (alert severity): §4.6, §7.3
- **D10** (manifest strictness): §5.1, §6.1, §13
- **D11, D12** (caret semver, contracts version): §3.4, §3.5, §6.1
- **D13** (layout wrapper): §7.4
- **D14** (first-run): §7.5
- **D15** (state-store warning): §4.4
- **D16** (packaging discipline): §14
- **D17** (contracts as package): §3, §14

### 18.3 Architecture sections to spec sections

- Architecture §1, §1.1 (overview, vocabulary): §1, §4, §5
- Architecture §2 (filesystem hierarchies): §2, §8
- Architecture §3 (contracts layer): §3
- Architecture §4 (components and services): §4, §5
- Architecture §5 (startup): §9
- Architecture §6 (layer boundaries): §10
- Architecture §7 (signal in practice): §4.2, §5.2
- Architecture §8 (write coordination): §4.3, §5.4
- Architecture §9 (diagnostics): §11
- Architecture §10 (versioning): §12
- Architecture §11 (packaging): §14
- Architecture §12 (out-of-scope): §17

---

## 19. Development plan, agents, and skills (sprint-planning input)

This section is the build-process companion to the architectural spec. Where §1–§18 describe **what** is being built, §19 prescribes **how** the work is sequenced, which automation handles which sprint, and which guardrails every agent must respect. It is the input the next phase (sprint planning) consumes.

### 19.1 Fundamental principles (project-wide guardrails)

These principles are non-negotiable and are restated verbatim in every skill defined in §19.4 so that no agent can act without them in context:

- **G1. Test-Driven Development is mandatory.** No production code is written before its failing functional test exists. A code change is accepted only when (a) the test that motivates it existed and was failing before the change, and (b) every previously-green test remains green.
- **G2. Regression containment.** Every validated milestone is sealed by adding regression tests that lock in the behavior just delivered. Subsequent sprints may not weaken those tests; they may only extend them.
- **G3. Less code, more quality.** When two implementations satisfy the same tests, the one with fewer lines wins. Agents that produce verbose code have their output rejected by the integration agent. This is not stylistic preference — it is enforced.
- **G4. Layer-direction rule (§10.1) is invariant.** No agent — human or automated — may write an import that contradicts §10.1. The integration agent has veto authority.
- **G5. The `contracts` package is type-only.** Agents working on contracts must not introduce behavior, I/O, logging, or non-version constants. (§3.1)
- **G6. Single point of egress for filesystem writes.** All writes route through `FilesystemComponent` (§4.3); the documented exception is stdlib `logging` handlers. Agents that bypass this rule have their PRs rejected.
- **G7. Signals are the only observation idiom.** No polling. (§4.2)
- **G8. Failure containment over abort.** Non-fatal failures surface at the alert icon and the per-plugin log; they never abort startup. (§11) The only fatal failures are component constructor exceptions.
- **G9. Strict manifests.** Unknown fields, missing required fields, and malformed JSON reject the manifest. No silent coercion. (§5.1, §6.1)
- **G10. Mirror discipline.** `SubscriptionHandle` and the plugin-manifest model are mirrored across infracore and contracts (§3.3). Drift fails the build. The integration agent is the enforcer.

### 19.2 Milestone plan

Five milestones, executed in order. Each milestone has an explicit acceptance gate; the gate is the integration agent's verdict, not a human review.

| # | Milestone | Definition of done |
|---|---|---|
| M1 | **Functional-test corpus** | The complete test suite under `tests/` exists and runs. Every test asserts behavior described in §3–§9. The infracore code under test does not yet exist; the entire suite is **red**. The shape of the tests (file paths, fixtures, parametrizations) reflects §16.1's per-layer discipline. |
| M2 | **Infracore delivered and accepted** | All tests under `tests/infracore/` and `tests/contracts/` pass. Components and contracts conform to §3, §4, §10. The integration agent's static checks (§13.1, §19.5) are green. No service or plugin code is written. The application can boot to step §9.8 (UI shell construction) with zero services and zero plugins discovered, and shut down cleanly. |
| M3 | **Service layer delivered and accepted** | All tests under `tests/services/` pass; M2's tests stay green (regression). The nine services in §1 are present and registered through `InjectorComponent`. The application boots to step §9.8 and the injector reports nine constructed services. No plugin code is written. |
| M4 | **Plugins delivered and accepted** | All tests under `tests/plugins/` pass; M2 and M3 stay green. The three v1 plugins (Project Launcher, Image Cropping, Subtitle Text Tool) are present, manifests validate, lifecycle hooks complete without exceptions on a clean fixture. |
| M5 | **Integration validated** | All tests under `tests/integration/` pass — the §16.2 scenarios exhaustively. The PyInstaller build (§14) produces a runnable `.exe` that passes a manual smoke checklist derived from PRD §2.3 success criteria. The integration agent's full check matrix (§13.1) is green. |

The gate between consecutive milestones is binary: M*n+1* may not begin until M*n* is accepted.

### 19.3 Regression discipline across milestones

At the close of each accepted milestone, the test suite is **frozen as the regression floor**: every test green at that moment must remain green at every subsequent milestone. New sprints add tests; they do not weaken existing ones. A sprint that needs to change a previously-green test is treated as a contract change — it requires the integration agent to confirm that the change is consistent with §3.4 (caret semver) and the affected `service_api_version` / contracts package version is bumped accordingly.

The `tests/` tree is structured so each milestone's regression floor is self-evident:

```
tests/
├── infracore/         # M2 floor
├── contracts/         # M2 floor
├── services/          # M3 floor
├── plugins/           # M4 floor
└── integration/       # M5 floor
```

CI runs the full tree on every commit after M1; commits that turn a previously-floor-green test red are rejected.

### 19.4 Agents and skills

Each milestone is executed by a small set of agents, each carrying a focused skill (system prompt + tool access + context selection). The principle is **minimum sufficient context**: an agent receives only the spec sections, source folders, and tests it needs. This keeps the agent fast, keeps reasoning grounded, and keeps the cost of error contained.

Every skill begins with the verbatim list of guardrails G1–G10 (§19.1). The sections below specify only what is *additional* to that.

#### 19.4.1 `test-author` (active in M1; consulted in M2–M5)

- **Purpose.** Produces the functional-test corpus before any production code exists.
- **Context.** §3, §4, §5, §6, §7, §9, §11, §16. Read-only access to PRD and architecture document if cross-referencing is needed.
- **Tool access.** Filesystem write under `tests/`. No write access elsewhere.
- **Outputs.** `pytest` modules. Each test names the spec section it derives from in its docstring. Parametrizations cover the failure modes in §11.
- **Guardrail addendum.** The agent does not invent behavior the spec does not pin down. If a test would require an underspecified detail, the agent files a spec-clarification request rather than guessing.

#### 19.4.2 `infracore-builder` (active in M2)

- **Purpose.** Implements components and contracts to turn `tests/infracore/` and `tests/contracts/` green.
- **Context.** §1, §2, §3, §4, §9, §10, §11, §13, §19.1. The corresponding test files. **No** access to `services/`, `plugins/`, or the service/plugin tests.
- **Tool access.** Filesystem write under `infracore/` and `contracts/`. Read-only on `tests/infracore/` and `tests/contracts/`.
- **Guardrail addendum.** G3 is enforced by a per-PR line-count budget computed from the test corpus (heuristic: target ≤ 3× the test code's line count). The integration agent surfaces the ratio as a warning when exceeded; reviewer (human or `code-critic` agent §19.4.6) decides.

#### 19.4.3 `service-builder` (active in M3, parameterized per service)

- **Purpose.** Implements one service folder under `services/` to turn its tests green.
- **Context.** §3, §5 (only the subsection for the target service), §10, §13, §19.1. The target service's test file. The contracts module the service implements. **No** infracore source. **No** other service source. Components are accessed only via the injector — but in tests the agent sees the test fixtures, which provide mocked components.
- **Tool access.** Filesystem write under `services/<target>/`. Read-only on `contracts/` and the target service's tests.
- **Guardrail addendum.** The service must declare its external dependencies in its `pyproject.toml` extras (§14). The agent's PR is rejected if a `requirements.txt` or hard-coded import outside the declared extras is introduced.

#### 19.4.4 `plugin-builder` (active in M4, parameterized per plugin)

- **Purpose.** Implements one plugin folder under `plugins/` to turn its tests green.
- **Context.** §3, §6 (only the subsection for the target plugin), §10, §19.1. The target plugin's test file. The contracts modules the plugin's required services expose. **No** infracore source. **No** service source.
- **Tool access.** Filesystem write under `plugins/<target>/`. Read-only on `contracts/` and the target plugin's tests.
- **Guardrail addendum.** The agent may import only `contracts.*` and `PySide6.*`. Any other import in the plugin code (`os`, `pathlib`, `requests`, etc., except as type annotations sourced from contracts) is rejected by the integration agent.

#### 19.4.5 `integration-agent` (active throughout, gating M2–M5)

- **Purpose.** §13. Static enforcement of layer rules, manifest schemas, mirror invariants, dependency naming, line-count discipline (§19.4.2).
- **Context.** Whole source tree (read-only). Whole test tree (read-only). §3–§13, §19.1.
- **Tool access.** No write access. Emits accept/reject verdicts and surfaces drift warnings.
- **Activation.** Runs on every PR. Its verdict is the milestone gate.

#### 19.4.6 `code-critic` (active throughout, advisory)

- **Purpose.** Reviews PRs for the G3 (less code, more quality) principle. Flags duplication, indirection that pays no rent, and verbose patterns where a less verbose Python idiom exists.
- **Context.** The PR diff. The corresponding spec subsection. §19.1.
- **Tool access.** Read-only.
- **Output.** Suggested simpler diff, or "ratify" if the PR is already minimal.

#### 19.4.7 `release-engineer` (active in M5)

- **Purpose.** Produces the PyInstaller build (§14). Runs the manual smoke checklist (PRD §2.3).
- **Context.** §14, §16.2, §19.2.
- **Tool access.** Build environment, signing keys (out of scope here).

### 19.5 Skill template

Every skill file (consumed by the corresponding agent at invocation time) follows this fixed structure. This template is itself a guardrail: an agent whose skill omits any section is not deployable.

```
# Skill: <name>

## Guardrails (verbatim from spec.md §19.1)
G1. Test-Driven Development is mandatory.
G2. Regression containment.
G3. Less code, more quality.
G4. Layer-direction rule (§10.1) is invariant.
G5. The contracts package is type-only.
G6. Single point of egress for filesystem writes.
G7. Signals are the only observation idiom.
G8. Failure containment over abort.
G9. Strict manifests.
G10. Mirror discipline.

## Purpose
<one-sentence purpose statement>

## Context (read access)
<bullet list of spec sections + source folders + test folders>

## Tool access
<allowed write paths, allowed read paths, no-go list>

## Inputs
<what the agent receives at invocation>

## Outputs
<what the agent produces, where it writes>

## Acceptance
<how the agent's output is judged: which tests must pass,
 which integration-agent checks must be green>

## Refusals
<situations in which the agent stops and asks for clarification
 instead of inventing behavior>
```

### 19.6 Sprint cadence

Sprints inside a milestone are short: one component or one service or one plugin per sprint. The exit criterion of every sprint is the same shape — the relevant test file goes from red to green, the integration agent stays green, and `code-critic` ratifies the PR.

The expected sprint count per milestone is approximate, not contractual:

| Milestone | Sprints | Sprint subjects |
|---|---|---|
| M1 | 5 | One per layer (`infracore`, `contracts`, `services`, `plugins`, `integration`) |
| M2 | 7 | One per component (6) + lifecycle/excepthook/UI shell (1 combined) |
| M3 | 9 | One per service |
| M4 | 3 | One per plugin |
| M5 | 2 | Integration scenarios + release build |

Total: ~26 sprints. The plan is intentionally over-decomposed — small sprints fail fast and recover cheaply.

### 19.7 Cross-references

- §13 (integration agent) — the runtime expression of G4, G5, G9, G10.
- §16 (testing) — defines what "test" means at each layer; §19 defines when the tests are written and who writes them.
- PRD §2.3 (success criteria) — informs the M5 manual smoke checklist.

