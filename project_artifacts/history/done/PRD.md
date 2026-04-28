# PantonicVideo — Product Requirements Document

**Version:** 1.1 (PRD, post-architecture pass)
**Status:** Draft for review
**Date:** April 2026
**Inputs:** `discovery-notes.md` (April 2026), `prd-decisions.md` (annotated), `architecture.md` (April 2026)

**Naming.** The product as a whole is **PantonicVideo** — the assembly of four layers (infracore, contracts, services, plugins). The name **infracore** refers specifically to the core layer; it is not the name of the platform. Earlier drafts of this PRD used "Infracore" as the product name; this version aligns with the architecture document.

---

## 1. Overview

PantonicVideo is a Windows desktop application written in Python that hosts independent plugins ("dockers") inside a single customizable window. Its purpose is to unify and partially automate the tasks involved in producing and editing videos for YouTube, with CapCut as the primary editing target.

The product is optimized for a single user: the author, a developer-tinkerer who builds most plugins with AI-assisted coding. Long-term value is extensibility and code health, not feature breadth at launch. The platform-first stance is deliberate: every requirement in this PRD is weighed against whether it preserves the architecture's ability to absorb new plugins without modification to the core.

PantonicVideo is composed of four layers — **infracore** (the core, with its components), **contracts** (the type-only seam), **services** (external-dependency wrappers and component expressions), and **plugins** (feature units). The four-layer split is normative; see §4 for its binding constraints.

---

## 2. Goals and non-goals

### 2.1 Goals (v1)

- Provide a stable, documented platform on which new plugins can be built without modifying infracore.
- Ship a working desktop application that demonstrates the platform with three built-in plugins covering real video-production tasks.
- Establish architectural boundaries (four-layer separation, service contracts, plugin manifests) that hold firm as the plugin set grows.
- Provide reliable diagnostics so the user can identify and recover from plugin failures without crashing the application.

### 2.2 Non-goals (v1)

- Pipelines / workflow chaining (deferred to v2).
- A CapCut JSON editing plugin (planned for v1.1+; requires `CapCutAdapterService`).
- Image enhancement plugins.
- Inter-plugin direct communication — explicitly forbidden by design, in v1 and beyond.
- Dark mode or theming.
- Multi-user support, profiles, SSO.
- System tray presence, autostart, or native OS notifications.
- Hot-reload of plugins (restart on plugin change is acceptable).
- A plugin marketplace or in-app plugin browser.
- Third-party plugin curation in the official repository.
- macOS support.

### 2.3 Success criteria

- All three built-in plugins load, render their dockers, and perform their stated function on a clean Windows install of the packaged PantonicVideo `.exe`.
- A new third-party plugin built by the author can be integrated by dropping its folder into the user-data plugins directory (`<pantonicvideo-root>/plugins`) and restarting, with zero changes to infracore's source.
- A deliberately broken plugin (malformed manifest, raised exception, missing service) does not crash PantonicVideo, and its failure surfaces under the alert icon with enough information to act on.

---

## 3. Users and personas

A single persona drives the PRD: the **developer-tinkerer**. This user is comfortable with Python, leans on AI coding assistants and agentic programming for most plugin work, and prefers tools that expose stable contracts over tools that hide behavior behind opinionated UX.

Implications:

- Plugin authors are expected to read service contracts but not infracore internals.
- The user is also the primary recipient of alerts; messaging can assume Python literacy.
- One user per machine. No multi-user concerns anywhere in this document.

---

## 4. Architecture (normative)

The layer separation is the binding constraint of this product. The architecture document specifies the layout, import rules, and startup sequence in detail; this section gives the normative summary that every requirement below is written to preserve.

### 4.1 The four layers

**Layer 1 — Infracore (the core).** Owns low-level operations: filesystem I/O primitives, application state store primitives, plugin lifecycle management, plugin registry, the logging sink, and the injector. Infracore is composed of *components* — infrastructural primitives that are wired in code at startup and that are not exposed to plugins directly. Infracore exposes generic, domain-agnostic capabilities. Contains no domain logic. Its only external dependencies are PySide6, `platformdirs`, and `pydantic`.

**Layer 2 — Contracts.** A type-only seam: `typing.Protocol` definitions, Pydantic models, and enums. No behavior, no I/O. The contracts layer **does not depend on infracore** — it is independently importable by services and plugins, and depends only on `pydantic` and stdlib `typing`. Distributed as the `contracts` package. (Earlier drafts called this `infracore-contracts`; the rename and the independence from infracore are architectural commitments — see architecture document §3.)

**Layer 3 — Services.** The only consumer of infracore's components and the home of every external library (Pillow, subtitle parsers, future CapCut JSON tooling, etc.). Services expose contract-shaped capabilities to plugins through dependency injection. Services come in four flavors (architecture §1.1):

- **Expression services** wrap an infracore component and expose its capability through a contract (e.g., `FilesystemService` wraps `FilesystemComponent`). Plugins never see components directly; expression services are the controlled boundary.
- **Domain services** wrap external libraries into contract-shaped APIs (e.g., `ImageService` wraps Pillow). They have no component backing.
- **Auxiliary services** centralize generic recurring procedures (e.g., file renaming) that several plugins would otherwise duplicate.
- **Simplifying services** absorb procedures that would harm a plugin's cohesion (e.g., timestamp manipulation for the subtitle plugin).

The v1 catalog uses only expression and domain services; auxiliary and simplifying services are scaffolded for the integration agent's promotion path (§10).

**Layer 4 — Plugins.** Pure orchestration and UI. Plugins import only from `contracts` (for `Protocol` typing) and from PySide6 (for UI rendering). Plugins **never** call infracore directly. Plugins **never** import services by code path; services are received via dependency injection at `on_load`. Plugins **never** import external libraries. A plugin presents a docker, collects user intent, and delegates work to services. Beyond these constraints, plugins are autonomous. When duplication appears across plugins, the integration agent (see §10) may propose centralizing the duplicated logic into an auxiliary service.

### 4.2 Components vs services — vocabulary

The architecture document fixes a vocabulary distinction that this PRD adopts:

- A **component** is an infracore-coupled primitive (e.g., `SignalComponent`, `FilesystemComponent`). Components live inside infracore, are wired in code at startup, and have no manifest. Plugins do not see them. The v1 components are listed in §5.
- A **service** is a contract-shaped capability that plugins (and other services) consume through dependency injection. Services live under `services/`, are folder-discovered at startup, ship with a manifest, and are registered with the injector.

Where this PRD previously spoke of "the service layer" as the only consumer of "infracore APIs," the more precise statement is: services are the only consumer of infracore's components, and plugins are the only consumer of services. The contracts layer sits between them as the type-only seam.

### 4.3 Communication

- **Plugins → Services:** direct calls via injected service references against `Protocol`s defined in the `contracts` package.
- **Services → Components:** direct calls against infracore's component API. Expression services are thin facades; domain services may consume expression services (and through them, components) but never reach into a component directly.
- **Plugins → Plugins:** **forbidden.** Cross-plugin coordination happens via shared state, mediated by services, observed via signals.
- **Plugins → Components:** **forbidden.** Components are not exposed to plugins under any circumstance.
- **Infracore → Plugins:** only through the lifecycle hooks defined in §6.

### 4.4 Observation primitives and the signal abstraction

Infracore exposes generic, low-level **observation primitives** through its components: callback registration over filesystem changes (`FilesystemComponent`), callback registration over application-state-store changes (`AppStateComponent`), and callback registration over plugin-registry changes (`PluginRegistryComponent`). These primitives are intentionally minimal and carry no value semantics — they notify, they do not hold state.

The **signal abstraction** — value-holding, subscription-based, modeled on Angular and Godot — is constructed by `SignalComponent` inside infracore and exposed to plugins through `SignalService` (§8.1). Every other expression and domain service in v1 builds its observation contract surface on top of `SignalService`, so plugins consume signals everywhere even though only `SignalComponent` produces them.

This split keeps infracore's other components strictly callback-shaped and domain-agnostic. The same callback primitives could just as well back a different reactive abstraction (RxPy observables, plain pub/sub, etc.) without changing the components — only `SignalComponent` and the `SignalService` contract would move. The platform's commitment to signals is a service-layer commitment, surfaced through one component.

One binding consequence carries through every layer: there is no polling anywhere in the platform. If a plugin needs to react to a state change, it subscribes through a service.

---

## 5. Infracore — components and their capabilities

This section enumerates the components infracore is composed of and the capabilities each provides to the services that wrap it. Components are infracore-internal; only services see them. Plugins see services only. The component list below is the v1 catalog; per the architecture, components are wired in code at startup and have no manifest.

The v1 components are: `SignalComponent`, `AppStateComponent`, `FilesystemComponent`, `PluginRegistryComponent`, `LoggingComponent`, and `InjectorComponent`. Each has a corresponding expression service in §8 (the injector's expression service is `InjectorService`). The capability shapes documented here are those exposed to services; plugin-facing shapes are documented per-service in §8.

### 5.1 `FilesystemComponent` — filesystem operations

A thin pass-through over the OS filesystem with one invariant added: all writes route through this single component to serialize them per-path (see §8.3 and architecture §8). Operates on `pathlib.Path`. All operations are synchronous.

- `read_file(path: Path) -> bytes`
- `write_file(path: Path, data: bytes) -> None` — serialized; concurrent writes to the same path queue.
- `list_dir(path: Path) -> list[Path]`
- `exists(path: Path) -> bool`
- `delete(path: Path) -> None`
- `make_dir(path: Path, parents: bool = True) -> None`

Infracore performs no sandboxing; services are trusted callers. The discipline of *who writes where* lives in the service layer (see §8.3). Path arguments are accepted as-is — services that wish to scope themselves to a base directory do so internally.

**Filesystem change notification.** The component additionally exposes a callback-registration primitive:

- `watch(path: Path, callback: Callable[[FilesystemEvent], None]) -> SubscriptionHandle`
- `unwatch(handle: SubscriptionHandle) -> None`

The callback is invoked when the contents of the watched path change. `SubscriptionHandle` is an opaque infracore-internal type used only to support unregistration. There is no value semantics here — the component does not remember "the latest event," it merely fires callbacks on change. Any value-holding behavior (e.g., "the most recent filesystem event for this path") is constructed by `SignalComponent` on top of this primitive and surfaced through `SignalService` / `FilesystemService`.

This is the mechanism by which the project folder's contents stay current across the application without polling. Implementation backing is `QFileSystemWatcher`; when it proves insufficient, `watchdog` is the documented fallback.

### 5.2 `AppStateComponent` — application state store

An in-memory key-value store, persisted to disk as JSON via `FilesystemComponent`. Values must be JSON-serializable; Pydantic models are accepted and serialized via their `.model_dump()`.

The component exposes the primitive operations:

- `state_get(key: str) -> Any | None`
- `state_set(key: str, value: Any) -> None`
- `state_delete(key: str) -> None`
- `state_observe(key: str, callback: Callable[[Any], None]) -> SubscriptionHandle` — registers a callback that fires whenever the value at `key` changes.
- `state_unobserve(handle: SubscriptionHandle) -> None`

The observation primitive is intentionally callback-shaped, not signal-shaped. The component stores values and notifies on change; it does not expose value-holding observation objects. `SignalComponent` constructs the signal abstraction on top of these primitives, and `AppStateService` / `SignalService` surface that abstraction to plugins.

**Persistence cadence.** Write-through. Every `state_set` triggers a JSON write of the full store, routed through `FilesystemComponent`. The volume of state in v1 is small enough that this is acceptable; if it becomes a problem, batching can be added without changing the surface.

**Concurrency.** Last-write-wins. When two writes to the same key happen within a short window (default 50 ms), the component logs a `WARNING` via `LoggingComponent`. This warning is for the maintainer's diagnostic benefit; it has no user-visible effect in v1. (Tier 4, D15.)

**Plugins do not see this component.** Per §4, plugins access state through `AppStateService` for read/write and through `SignalService` (or the `observe` shorthand on `AppStateService`) for value-holding observation.

### 5.3 `PluginRegistryComponent` — plugin registry

Read-only inspection surface plus a change-notification primitive for the running set of plugins.

- `list_plugins() -> list[PluginRecord]`
- `observe_plugins(callback: Callable[[list[PluginRecord]], None]) -> SubscriptionHandle` — registers a callback fired on any registry state change (load, enable, disable, fail).
- `unobserve_plugins(handle: SubscriptionHandle) -> None`

Where `PluginRecord` exposes name, version, status (`loaded` / `enabled` / `disabled` / `failed`), and — when status is `failed` — a short reason string. This surface is consumed publicly through `PluginRegistryService` (§8.4) so that the Docker menu and any future diagnostics docker can render the same data.

Enable/disable transitions happen through `PluginRegistryService`; the component implements them but does not expose them as a separate API to other components.

### 5.4 `LoggingComponent` — logging sink and alert path

Two channels (see architecture §9 and PRD §8.5):

- The **infracore log** at `<pantonicvideo-root>/logs/infracore.log` — a rotating file handler (10 MB per file, 5 backups) that captures infracore's own modules at `INFO` and above. The component installs this handler on the stdlib `logging` root.
- The **per-plugin log** at `<plugin-folder>/logs/plugin.log` — rotating handlers, one per plugin, addressed by plugin name. Plugins write to these via `LoggingService`.
- The **alert path** — an in-memory sink that drives the status-bar alert icon (§7.3). Plugins push entries via `LoggingService.raise_alert`.

Plugin logging and alerting are mediated through `LoggingService`; the component handles the routing, file management, and alert fan-out. Infracore is unaware of plugins as logging origins; the `plugin` argument is passed by the caller.

### 5.5 `SignalComponent` — the signal engine

The reactive primitive. `SignalComponent` builds the value-holding signal abstraction (`Signal[T]`, subscriptions, value caching) on top of the callback primitives exposed by `FilesystemComponent`, `AppStateComponent`, and `PluginRegistryComponent`. It is the single place in the platform where the signal idiom is implemented; every observation contract surfaced through services delegates here.

`SignalComponent` is infracore-internal. Plugins consume signals through `SignalService` (§8.1); other services that surface observations (`AppStateService.observe`, `FilesystemService.watch`, `PluginRegistryService.observe_plugins`, `ProjectService.observe_current`) delegate to `SignalService`, which delegates to `SignalComponent`.

### 5.6 `InjectorComponent` — dependency injection

The injector. (Earlier drafts of this document called it the "service locator"; the architecture renames it: the injector actively constructs services and resolves their declared dependencies, rather than passively serving lookups.) `InjectorComponent`:

- Registers components by name (during infracore startup).
- Registers services by name during service discovery, after validating each service manifest (§8.10).
- Reads each service's `depends_on` declarations, computes a construction order, and instantiates services with their dependencies satisfied.
- At each plugin's `on_load`, resolves the plugin's `required_services` and supplies the contracted services to the plugin constructor.

Plugins receive only services from the injector, never components. The plugin-facing expression of this component is `InjectorService` (§8.10), which is provided primarily so that services-layer code can request injection in the rare cases where it is needed; v1 plugins do not consume `InjectorService` directly.

### 5.7 Lifecycle hooks (called by infracore)

Infracore calls these on each plugin in this order. Each call is wrapped in a try/except boundary; an exception inside any hook is captured, the plugin is marked `failed` with a reason string, and the application continues.

1. **`on_load`** — service contract verification. The plugin confirms that all required services and versions are available. If verification fails, the plugin is not loaded; the failure surfaces via `LoggingService` at `ERROR` (see §8.5) and the plugin's status becomes `failed`.
2. **`on_enable`** — the plugin loads its configuration and renders its docker on screen.
3. **`on_disable`** — the plugin stops execution and hides its docker.
4. **`on_unload`** — the plugin persists any changed configuration.

A `sys.excepthook` is installed by infracore to catch exceptions raised in Qt event-loop handlers. When such an exception originates in plugin-attached code, infracore routes it to the same captured-error path as a lifecycle exception. This is a defensive measure; plugins are expected to handle their own runtime exceptions and report through `LoggingService`.

---

## 6. Plugin contract

### 6.1 Manifest

Every plugin ships a JSON manifest at the root of its folder. The manifest is validated against a Pydantic model on plugin discovery. The authoritative schema lives inside infracore (`infracore/manifest/plugin_manifest.py`); a mirror schema for plugin authors who want to introspect or generate manifests programmatically lives in the contracts package (`contracts/manifest.py`). The integration agent verifies the two have not drifted.

Required fields:

- `name` (string, unique within the running PantonicVideo instance)
- `version` (string, semver)
- `contracts_min_version` (string, semver) — the minimum version of the `contracts` package the plugin is built against. (D12: tracks contracts, not infracore.)
- `author` (string)
- `description` (string)
- `entry_point` (string, Python module path resolvable from the plugin folder)
- `required_services` (list of objects with `name` and `min_version`)
- `inputs` (list of Pydantic model references; may be empty)
- `outputs` (list of Pydantic model references; may be empty)

Reserved for v2:

- `permissions` (currently ignored; the field may be present and is preserved through validation)

**Contracts version matching.** At `on_load`, infracore verifies that the running `contracts` package satisfies the plugin's `contracts_min_version` under caret semantics (D11). The check reads `contracts`'s `pyproject.toml` at startup and compares as strings; no contracts code is imported by infracore.

**Service version matching.** Caret semantics (D11). `min_version: 1.2` matches `1.2.x` through `1.x.x` but not `2.0.0`. A plugin whose required service versions cannot be satisfied is not loaded.

**Validation strictness (D10).** Manifests are validated strictly. Any deviation — missing required field, wrong type, unknown extra field, malformed JSON — rejects the manifest. This rigor is intentional: the integration agent (§10) is the gatekeeper that prepares plugins for the platform, and it is expected to fix or reject anything short of perfect.

### 6.2 Lifecycle obligations

Each plugin must implement the four hooks in §5.7. A plugin that does not implement all four fails `on_load` and is marked `failed`.

### 6.3 Configuration

Plugin configuration is the responsibility of the plugin itself. Infracore provides no standardized settings panel. Plugins may persist configuration anywhere within their own folder; the convention is `<plugin-folder>/config.json`.

### 6.4 Internal autonomy

Beyond the rules in §4.1 and §4.3 (no infracore imports, no service imports — only injected service references — no external library imports), plugins have full autonomy over their internal structure. They may compute, transform, render, and orchestrate however they choose. They may not, however, reach into the filesystem, network, or external libraries — those go through services without exception.

### 6.5 Error handling

A plugin's runtime exceptions caught at the lifecycle boundary (§5.7) become a single `failed` status with one reason string. A plugin that wants finer-grained reporting calls `LoggingService` directly to log and to raise alerts (§8.5).

---

## 7. UI shell

### 7.1 Window

Standard Windows window chrome. Light mode only. The application opens with the user's last-saved layout; on first launch, see §7.5.

### 7.2 Menus

A top menu bar with at minimum:

- **Docker menu.** Lists every plugin whose manifest validates and whose required services are available, regardless of currently loaded/enabled state. Each entry is a toggle; toggling enables or disables the plugin (calling `on_enable` / `on_disable` accordingly). Plugins that failed manifest validation or service-version checks do **not** appear here; their failure surfaces only under the alert icon.

### 7.3 Status bar

A status bar at the bottom of the window. The status bar hosts the **alert icon**.

- The icon's appearance reflects the current alert population. When the highest unacknowledged alert is at `WARNING`, `ERROR`, or `CRITICAL`, the icon styling escalates accordingly. Implementation detail; the user-visible effect is "something needs attention." (D9.)
- Clicking the icon opens a brief summary of current alerts, grouped by source plugin.
- Drilling into an entry shows the alert's full summary text and a path to the originating plugin's log file. Full log contents are not embedded in the UI; the user opens the file manually.

The user-facing semantics are deliberately simple: *something is wrong; here is roughly what; here is where to read more*. Severity grading exists so the UI can prioritize, not so the user has to learn a taxonomy.

### 7.4 Layout persistence

Docker positions, sizes, and visibility persist across restarts. Single layout — no named layouts, no workspaces.

The layout is stored at `<pantonicvideo-root>/layout.json` with the following shape:

```json
{
  "version": 1,
  "saved_at": "<ISO 8601 timestamp>",
  "qt_state": "<base64-encoded QByteArray from QMainWindow.saveState()>"
}
```

The wrapper exists so that future infracore versions can migrate layouts when Qt's binary state format changes incompatibly. (D13.)

### 7.5 First-run experience

On first launch — i.e., when no layout file is found — infracore enables the **Project Launcher** plugin only and renders its docker in a default position. The other built-in plugins are listed in the Docker menu but not enabled. No welcome modal, no tutorial, no marketing surface. (D14.)

---

## 8. The v1 service catalog

Services are the only consumers of infracore's components and the only home for external dependencies. The v1 catalog below is the minimum needed to support the three built-in plugins; future services arrive through the integration process described in §10.

Each service exposes a contract (a `typing.Protocol` plus `service_api_version` string) distributed via the `contracts` package. Plugins import contracts; concrete implementations live under `services/` in PantonicVideo's source tree and are bundled into the `.exe`.

The v1 catalog comprises **nine services**: six expression services that wrap infracore components (`SignalService`, `AppStateService`, `FilesystemService`, `PluginRegistryService`, `LoggingService`, `InjectorService`) and three domain services that wrap external libraries or hold thin domain objects (`ProjectService`, `ImageService`, `SubtitleService`). The architecture document (§4) details the expression-vs-domain distinction.

### 8.1 `SignalService`

The contract-shaped expression of `SignalComponent` (§5.5) — the **expression service** through which plugins (and other services) consume the signal abstraction. The reactive engine itself lives in `SignalComponent`; `SignalService` is a thin facade that confines the component's identity to infracore. (Architecture §7.) Most other services in the catalog delegate their observation surfaces to `SignalService`, which delegates to `SignalComponent`.

A `Signal[T]` is a value-holding observation object: it carries the current value, supports synchronous reads, and emits to subscribers on change. Internally, each signal is backed by a callback registered with the appropriate component primitive (`AppStateComponent.state_observe`, `FilesystemComponent.watch`, `PluginRegistryComponent.observe_plugins`); `SignalComponent` caches the latest emitted value so that `Signal.get()` returns synchronously.

Contract surface (illustrative):

- `signal_for_state(key: str) -> Signal[Any]` — backed by `AppStateComponent.state_observe`
- `signal_for_path(path: Path) -> Signal[FilesystemEvent]` — backed by `FilesystemComponent.watch`
- `signal_for_plugins() -> Signal[list[PluginRecord]]` — backed by `PluginRegistryComponent.observe_plugins`
- `subscribe(signal: Signal[T], callback: Callable[[T], None]) -> Subscription`
- `unsubscribe(subscription: Subscription) -> None`

`Signal[T]` and `Subscription` types are defined in the `contracts` package. They are the most stability-sensitive surface in v1 because every other service's observation contract depends on them. The signal type follows the Angular/Godot pattern; alternative reactive abstractions (RxPy observables, etc.) could be built by replacing `SignalComponent` and adjusting this contract, but only one is supported in v1. (D2.)

### 8.2 `AppStateService`

The expression service for `AppStateComponent` (§5.2). Generic key-value access over the application state store. Domain-agnostic. (D5, option 3 — generic primitive plus domain layer above it.)

Contract surface:

- `get(key: str) -> Any | None`
- `set(key: str, value: Any) -> None`
- `delete(key: str) -> None`
- `observe(key: str) -> Signal[Any]` — returns a signal sourced from `SignalService`; equivalent to `SignalService.signal_for_state(key)`. Provided for ergonomic plugin code.

Conventions (not enforced): keys use dot-separated namespaces (`project.path`, `ui.theme`, etc.) so that `observe` consumers can reason about scope.

### 8.3 `FilesystemService`

The expression service for `FilesystemComponent`. A thin facade that exposes the component's filesystem capability to plugins through a contract. (Architecture §8.) The architectural invariant — that all writes in PantonicVideo route through a single point so that operations on related paths cannot collide — lives in `FilesystemComponent`, not in this service. `FilesystemService` does not add serialization of its own; serialization is the component's responsibility.

Contract surface (illustrative):

- `read(path: Path) -> bytes`
- `write(path: Path, data: bytes) -> None` — serialized in `FilesystemComponent`; concurrent writes to the same path queue.
- `list(path: Path) -> list[Path]`
- `exists(path: Path) -> bool`
- `delete(path: Path) -> None`
- `watch(path: Path) -> Signal[FilesystemEvent]` — returns a signal sourced from `SignalService`; equivalent to `SignalService.signal_for_path(path)`. Provided for ergonomic plugin code.

The serialization guarantee is per-path: writes to different paths may proceed in parallel; writes to the same path are queued. Implementation backs onto `FilesystemComponent`'s primitives (§5.1).

Other services that touch the filesystem (`ProjectService`, `ImageService`, `SubtitleService`, and `AppStateComponent`'s state-store persistence) route their writes through `FilesystemService` (or, for components, through `FilesystemComponent` directly). This is a deliberate convention that keeps the write-coordination point single and obvious.

Log writes are the documented exception: `LoggingComponent`'s rotating handlers use stdlib `logging`'s own thread-safety and do not route through `FilesystemComponent`. (Architecture §8.)

### 8.4 `PluginRegistryService`

The expression service for `PluginRegistryComponent` (§5.3). Wraps the plugin registry for plugin and UI consumption.

Contract surface:

- `list_plugins() -> list[PluginRecord]`
- `enable(name: str) -> None`
- `disable(name: str) -> None`
- `observe_plugins() -> Signal[list[PluginRecord]]` — returns a signal sourced from `SignalService`; equivalent to `SignalService.signal_for_plugins()`. Fires on any registry state change.

The Docker menu is the primary consumer in v1. The pipeline runner (v2) will be the second.

### 8.5 `LoggingService`

The expression service for `LoggingComponent` (§5.4). The plugin-facing interface for diagnostics. Two channels (D4):

- `log(plugin: str, level: int, message: str, **kwargs)` — writes to that plugin's log file at `<plugin-folder>/logs/plugin.log` with a rotating handler. Standard `logging` levels.
- `raise_alert(plugin: str, level: int, summary: str)` — pushes an entry to the alert sink that drives the status-bar icon. Level uses `WARNING` / `ERROR` / `CRITICAL` per D9.

The two channels are independent. A plugin may log without alerting (routine info) or alert without verbose logging (a recoverable user-facing notice). Most failures will use both.

This service holds no plugin-specific state; the `plugin` argument is provided by the plugin and used for routing through `LoggingComponent`. The component does not maintain a registry of plugin loggers — that is a property of its implementation. (Endorses the project premise that infracore is unaware of plugins as identities.)

### 8.6 `ProjectService`

Domain layer over `AppStateService` and `FilesystemService`. Encapsulates the notion of "the current project."

A project consists of:

- A **central folder** where artifacts generated by the application are stored.
- A **metadata file** (`pantonicvideo-project.json`) at the central folder's root, mapping external locations relevant to the project: image source folders, audio source folders, configuration folders for other systems, and so on. (D6.)

Contract surface (illustrative):

- `get_current() -> Project | None`
- `set_current(folder: Path) -> None` — creates the metadata file if missing; loads it if present.
- `observe_current() -> Signal[Project | None]` — derived from the project state observed via `AppStateService` / `SignalService`.
- `get_metadata() -> ProjectMetadata`
- `update_metadata(updater: Callable[[ProjectMetadata], ProjectMetadata]) -> None`

`Project` and `ProjectMetadata` are Pydantic v2 models defined in the contracts package. The metadata schema is intentionally extensible — adding fields is a minor version bump.

### 8.7 `ImageService`

Encapsulates Pillow. Exposes operations for image manipulation in formats the contracts declare.

Contract surface for v1:

- `apply_crop(source: Path, rect: CropRect, output: Path) -> None`
- `resize(source: Path, dimensions: Dimensions, output: Path) -> None`
- `supported_formats() -> list[ImageFormat]`

`ImageFormat` is an enum that in v1 contains `PNG` and `JPEG`. (D7.) The contract is shaped to accept additional formats in later versions without breaking existing callers — adding an enum value is a minor bump; the method signatures do not change.

Plugins are responsible for any preview rendering they need; previews use Qt's built-in image scaling and do not call this service. The service is for committed operations only. (D7, subsidiary.)

### 8.8 `SubtitleService`

Encapsulates subtitle file generation.

Contract surface for v1:

- `text_to_srt(text: str, output: Path, options: SrtOptions) -> None`

The contract is deliberately narrow: SRT only. (D8.) Adding `.vtt` or `.ass` in a later version is expected to introduce new methods (or a writer-strategy refactor) rather than breaking the SRT method. The platform's general principle — extension should not require destructive refactoring — applies here as a future obligation, not as v1 surface area.

### 8.9 Service injection

Services are registered with `InjectorComponent` (§5.6) at infracore startup, after manifest validation and dependency resolution. Plugins receive the services they declared in `required_services` via constructor injection at `on_load` time. A plugin that requests a service whose version requirement cannot be met under caret semantics is not loaded.

The injector is *active* — it reads each service's `depends_on` declarations, computes a construction order, and instantiates each service with its dependencies satisfied — rather than a passive service locator. This is the substantive change behind the rename from earlier drafts. (Architecture §4.1.)

### 8.10 `InjectorService`

The expression service for `InjectorComponent` (§5.6). Provides a contract-shaped handle to the injector for service-layer code that needs to request injection in scenarios not covered by the static `depends_on` mechanism. v1 plugins do not consume `InjectorService`; it exists primarily for forward-compatibility and for the rare service-to-service late-binding case.

This service brings the v1 catalog count to nine (six expression services plus three domain services). The PRD's earlier draft listed eight services; the addition of `InjectorService` is the one extension introduced by the architecture pass.

### 8.11 Service manifest

Each service folder contains a `manifest.json` validated against `infracore/manifest/service_manifest.py`. Required fields:

- `name` — the contract name plugins reference in their `required_services`.
- `service_api_version` — the version of the contract this service implements; matched caret-style against the plugin's `min_version`.
- `implementation_version` — the version of this implementation, independent of the contract version.
- `entry_point` — `<module>:<class>` resolvable from the service folder.
- `depends_on` — other services this service consumes, with `min_version` constraints. Used by `InjectorComponent` to order construction.

Services do not declare component dependencies in the manifest; component dependencies are resolved by name within infracore at construction time. A service whose dependencies cannot be resolved is rejected at startup with an `ERROR` log entry; plugins that required it become `failed`.

---

## 9. The v1 plugins

### 9.1 Project Launcher

Prompts the user for a destination folder. Calls `ProjectService.set_current(folder)`, which writes through `AppStateService` and `FilesystemService` and triggers the project-changed signal. Other plugins observe this signal to update their views.

Auto-enabled on first run.

### 9.2 Image Cropping

Resizes and crops static images. UI exposes an image picker, crop/resize controls, and a commit button. Crop geometry is computed inside the plugin from user input; on commit the plugin calls `ImageService.apply_crop` or `ImageService.resize`. No live preview through the service.

### 9.3 Subtitle Text Tool

Converts text to `.srt` subtitle files. UI accepts a text input, optional timing parameters, and a destination. On commit, calls `SubtitleService.text_to_srt`.

---

## 10. Plugin integration process

Plugin development proceeds in two stages, mirroring §8.3 of the discovery notes:

1. **PoC stage (external).** The author proves the functional requirement as a standalone script, preferably in pure Python with free dependencies.
2. **Integration stage (mediated by an integration agent).** A dedicated AI integration agent is responsible for bringing the script into the platform. The agent:
   - Validates the manifest against the Pydantic schema in `infracore/manifest/plugin_manifest.py`.
   - Verifies the four-layer rule via static import analysis (architecture §6.3): no infracore imports from plugins, no service imports by code path from plugins, no external library imports from plugins, no contracts imports from infracore. The agent checks transitive imports as well as direct ones — this catches the failure modes that runtime injection cannot.
   - Identifies external dependencies and either places them inside an existing service or proposes a new domain service.
   - Identifies duplication with existing plugins and may propose centralizing common logic into an auxiliary service.
   - Identifies procedures that dilute a plugin's cohesion and may propose extracting them into a simplifying service.
   - Verifies that infracore's manifest schemas and the contracts-layer mirror schema have not drifted.
   - Refuses to mark a plugin as integrated until every check passes. Strict validation; minor issues are fixed or sent back, never accepted as-is. (D10.)

This agent is a project-level concern, not part of the runtime application. The PRD names it because the strictness of manifest and structural validation only makes sense in the context of an upstream gatekeeper that prepares plugins to meet that bar.

---

## 11. Versioning

PantonicVideo's v1 has four independent version axes, plus a hidden fifth (architecture §10):

- The `contracts` package versions independently of infracore. (D17, option 1.) Contracts go to `1.0.0` at v1 launch; subsequent bumps reflect contract changes only. (Earlier drafts called this package `infracore-contracts`; the rename and the package's independence from infracore are architectural commitments.)
- Each service carries a `service_api_version` (the version of the contract it implements) and an `implementation_version` (the version of its own code), independent of each other and of the contracts package version.
- Plugins declare `contracts_min_version` and per-service `min_version` in their manifests. Plugins do not declare an infracore version. (D12.)
- Infracore itself versions for release engineering; plugin authors are not expected to track it.
- Components have version numbers declared in code (Python module-level constants), used by the integration agent and by service compatibility checks but never seen by plugins or external configuration.

All semver matching is caret-style. (D11.) An infracore release that changes a component's behavior in a way visible through its expression service must bump the corresponding `service_api_version`; this is the discipline that lets plugin authors ignore infracore's release version.

---

## 12. Stack and packaging

| Area | Choice |
|---|---|
| GUI framework | PySide6 (LGPL) |
| Language | Python 3.12 (fallback to 3.11 if PyInstaller issues arise) |
| Packaging | PyInstaller, one-file `.exe` mode, with a splash screen during unpack; built-in plugins and services bundled into the binary |
| Dependency management | `uv` + `pyproject.toml` |
| Plugin manifest format | JSON, validated by Pydantic v2 (authoritative schema in `infracore/manifest/`, mirror in `contracts/manifest.py`) |
| Service manifest format | JSON, validated by Pydantic v2 (`infracore/manifest/service_manifest.py`) |
| Plugin discovery | Filesystem scan of two locations at launch: bundled `plugins/` (built-ins) and `<pantonicvideo-root>/plugins` (third-party) |
| Service discovery | Filesystem scan of bundled `services/` at launch; folder-discovered, manifest-validated, registered with `InjectorComponent` |
| Service layer pattern | Active injector (`InjectorComponent`), constructor injection driven by `depends_on` declarations |
| Service contracts | `typing.Protocol` + `service_api_version`, distributed in the `contracts` package (independent of infracore) |
| Plugin I/O contracts | Pydantic v2 models, referenced by name in manifest |
| Application state store | In-memory key-value, JSON-persisted, write-through; persistence routed through `FilesystemComponent` |
| Layout storage | `<pantonicvideo-root>/layout.json` (versioned wrapper around base64 Qt state) |
| Logging | stdlib `logging`; infracore log under `<pantonicvideo-root>/logs`, plugin logs under each plugin's folder |
| Testing | `pytest`, with `pytest-qt` for UI tests |
| Distribution | Public GitHub repository; `.exe` for fast usage |

**Packaging discipline (D16).** A splash screen during PyInstaller unpack is committed as v1 scope — the cheapest perceived-performance win available. UPX compression, excluded-module lists, and a fallback to one-folder packaging are tuning levers to be exercised empirically once cold-start measurements exist; they are not committed in v1.

**Bundled vs user-data discovery.** The `.exe` carries the source-tree `plugins/` (built-in plugins) and `services/` (the v1 service catalog) inside it; PyInstaller's `_MEIPASS` mechanism (or equivalent) is used to locate them at runtime. Third-party plugins live exclusively in `<pantonicvideo-root>/plugins`, which PyInstaller does not touch. Both discovery paths produce equivalent records; the distinction matters only for where files are read from. (Architecture §11.)

---

## 13. Filesystem layout

PantonicVideo distinguishes two filesystem hierarchies (architecture §2): the **source-tree root** (the development repository, compiled into the `.exe` by PyInstaller; covered in the architecture document) and the **user-data root** (the runtime directory the application reads and writes on the user's machine). The PRD specifies the user-data root; the source-tree layout is an architectural concern.

### User-data root

```
<pantonicvideo-root>/                          # %APPDATA%\PantonicVideo by default; user-overridable
├── config.json                        # infracore's own configuration
├── layout.json                        # docker layout (§7.4)
├── state.json                         # application state store snapshot
├── logs/
│   └── infracore.log                  # rotating
└── plugins/                           # third-party plugins only
    └── <plugin-name>/
        ├── manifest.json
        ├── <entry_point>.py
        ├── config.json                # plugin's own configuration (convention)
        └── logs/
            └── plugin.log             # rotating, per-plugin
```

Path resolution uses `pathlib.Path`. The default root is determined via `platformdirs`; on Windows this is `%APPDATA%\PantonicVideo`. The user may override the root through a startup setting; the override is the single thing infracore reads before establishing the rest of its filesystem.

**Built-in plugins do not appear in `<pantonicvideo-root>/plugins`.** They are bundled into the `.exe` and discovered through the source-tree path at runtime. The user-data `plugins/` folder is the public extension surface for third-party plugins. Both discovery paths produce equivalent `PluginRecord`s; the distinction matters only for discovery, not for execution. (Architecture §6.2, §11.)

---

## 14. Security posture

Plugins run in-process and have full Python capabilities. For single-user home use, this is accepted. The manifest's `permissions` field is reserved for v2; in v1 it is parsed and ignored. No sandboxing, no IPC isolation. (Discovery §8.9; architecture §12.)

---

## 15. Open items deferred to later PRDs

These are named here so they are known not-forgotten, not because they block v1.

- Pipelines / workflows — full v2 PRD.
- `CapCutAdapterService` and the CapCut plugin — v1.1+; depends on reverse-engineering the current CapCut JSON format.
- State store conflict-resolution policy beyond the diagnostic warning (D15).
- Permissions enforcement for the manifest's `permissions` field.
- Additional image formats beyond PNG/JPEG; additional subtitle formats beyond SRT.
- Hot-reload of plugins. Out of scope, possibly forever.

---

## 16. Traceability — decisions to sections

For audit:

- **D1, D2** → §4.4, §5.1, §5.2, §5.5, §8.1, §8.3
- **D3** → §5.3, §8.4
- **D4** → §5.4, §8.5
- **D5** → §8.2, §8.6
- **D6** → §8.6, §9.1
- **D7** → §6.4, §8.7, §9.2
- **D8** → §8.8, §9.3
- **D9** → §7.3, §8.5
- **D10** → §6.1, §10
- **D11, D12** → §6.1, §11
- **D13** → §7.4
- **D14** → §7.5
- **D15** → §5.2
- **D16** → §12
- **D17** → §11
