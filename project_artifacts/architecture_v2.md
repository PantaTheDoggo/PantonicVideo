# PantonicVideo — Architecture

**Version:** 1.1
**Status:** Updated with build-spec decisions S1–S17 (April 2026)
**Scope:** v1 architecture for PantonicVideo as specified in the PRD, plus the architectural decisions resolved out-of-band: source-tree layout, service catalog scope, packaging discipline, and the component/service distinction. Build-spec decisions S1–S17 (April 2026) have been folded back into this document; where the build spec (`spec.md`) is normative for implementation mechanics, this document defers to it.

PantonicVideo is the application as a whole — the assembly of four layers: **infracore** (the core, with its components), **contracts** (the type-only seam), **services** (external-dependency wrappers and component expressions), and **plugins** (feature units). The name "infracore" refers specifically to the core layer; "PantonicVideo" refers to the full platform.

This document is the architectural complement to the PRD. The PRD specifies *what* PantonicVideo does and *which contracts* it exposes; this document specifies *how the source is organized*, *how layers physically separate*, *how startup wires the pieces together*, and *which invariants hold across the boundary*. Where the PRD is normative, this document defers to it. Where the PRD is silent, this document fills the gap.

---

## 1. Architectural overview

PantonicVideo is a four-layer Windows desktop application. The layers, ordered from inside-out, are:

1. **infracore** — the core. Contains *components*: the platform's infrastructural primitives (signal, application state, filesystem, plugin registry, logging, lifecycle, UI shell, the injector). Components are infracore-internal; nothing outside infracore imports them directly.
2. **contracts** — the type-only seam. Defines `Protocol`s, Pydantic models, and enums that services implement and plugins consume. Has no behavior. Has no dependency on infracore.
3. **services** — external-dependency wrappers and component expressions. Two roles: domain services wrap third-party libraries (Pillow, subtitle parsers) into contract-shaped APIs; *expression* services expose infracore components to plugins through contracts. Services may import from infracore (to consume components) and from contracts (to declare what they expose).
4. **plugins** — feature units. Import only from contracts (for `Protocol` typing) and PySide6 (for UI). Receive services via dependency injection.

The directional rules are strict: each layer imports only from the layers below it on this list, and the contracts layer imports from nothing inside the project. External dependencies are concentrated in the services layer; infracore's external footprint is limited to PySide6, `platformdirs`, and `pydantic`; plugins have no external dependencies at all; contracts depends only on `pydantic` and `typing`.

The four-layer separation is enforced structurally (through source-tree placement and import rules) and procedurally (through the integration agent described in PRD §10). Both enforcement modes are necessary: structural rules prevent accidental violations during development, and the integration agent catches the residual cases — particularly transitive imports — before a plugin or service is admitted to the platform.

The application is single-process, single-user, and single-machine. There is no IPC, no sandbox, no multi-tenancy, no remote execution. Plugins run in-process with full Python capabilities; the security posture is "trusted developer using their own machine," exactly as PRD §14 specifies.

### 1.1 Components vs services — a vocabulary distinction

This document uses two distinct words for two distinct things, and the distinction is load-bearing.

A **component** is an infracore-coupled primitive. Components live under `infracore/bootstrap_components/` and are wired by the bootstrap code. They are not exposed to plugins directly. Their identities, types, and APIs are infracore's internal concern. The six v1 components (S1) are: `SignalComponent`, `AppStateComponent`, `FilesystemComponent`, `PluginRegistryComponent`, `LoggingComponent`, and `InjectorComponent`. The first five live under `infracore/bootstrap_components/`; `InjectorComponent` lives at `infracore/injector_component/` and is structurally distinct because it wires the others.

A **service** is a contract-shaped capability that plugins (and other services) consume through dependency injection. Services live under `services/` as folder-discovered modules. Four kinds of service exist:

- **Domain services** wrap external libraries. `ImageService` wraps Pillow; `SubtitleService` wraps subtitle parsers; `ProjectService` is a thin domain object. They have no component backing; they exist to confine external dependencies to one layer.
- **Expression services** expose infracore components to plugins through a contract. If a plugin needs to observe filesystem changes, it does not get `FilesystemComponent` — it gets a `FilesystemService` that wraps the component and presents only the contract-defined surface. Expression services are the controlled boundary across which component capabilities reach plugins.
- **Auxiliary services** centralize generic and recurring procedures used across plugins. For example, renaming files is a procedure several plugins may need; rather than each plugin reimplementing it, an auxiliary service endorses the DRY premise and provides a single, reusable implementation that plugins consume through a contract.
- **Simplifying services** handle procedures that would otherwise harm the cohesion of a plugin. For example, the subtitle creation feature requires handling timestamps; rather than embedding timestamp manipulation inside the plugin (where it dilutes the plugin's purpose), a simplifying service is created to manage timestamps, and the plugin consumes the service rather than implementing the procedure itself.

Not every component has an expression service in v1, though most do. The PRD's plugin manifests reference services like `signal`, `state`, `filesystem`, `plugin_registry`, `logging`; these are expression services backed by the corresponding components. `InjectorService` (S2, S17) is the contract-shaped expression of `InjectorComponent`; it has no in-tree consumer in v1 but exists so service-to-service late binding can be added without bumping the contracts package. `ProjectService`, `ImageService`, and `SubtitleService` are domain services with no component.

This vocabulary lets us say precisely what "infracore" means: it is the components plus the bootstrap that wires them. It is not the platform; the platform is PantonicVideo as a whole.

---

## 2. The two filesystem hierarchies

PantonicVideo distinguishes two filesystem hierarchies that are easy to conflate but architecturally distinct:

The **source-tree root** is the development repository. It contains the code that gets compiled into the `.exe` by PyInstaller, plus the built-in plugins that ship inside the binary. The integration agent operates on this tree.

The **user-data root** is `%APPDATA%\PantonicVideo` (overridable, see PRD §13). It contains runtime state: configuration, layout, the JSON-persisted state store, infracore's logs, and any third-party plugins the user has dropped in. PyInstaller does not touch it; the user — and the application at runtime — does.

These two hierarchies have separate `plugins/` folders with separate roles. The source-tree `plugins/` holds the v1 built-ins (Project Launcher, Image Cropping, Subtitle Text Tool); they ship inside the `.exe`. The user-data `plugins/` is the public extension surface; third-party plugins live only there.

### 2.1 Source-tree layout

```
<repo-root>/
├── infracore/                          # Layer 1: the core (components live here)
│   ├── __init__.py
│   ├── app.py                          # bootstrap entry point
│   ├── _versions.py                    # infracore release version constant
│   ├── bootstrap_components/             # the components, wired at startup
│   │   ├── __init__.py
│   │   ├── signal_component/
│   │   │   ├── __init__.py
│   │   │   ├── signal.py               # SignalComponent
│   │   │   └── handle.py               # SubscriptionHandle NewType (S3)
│   │   ├── app_state_component/
│   │   │   ├── __init__.py
│   │   │   └── app_state.py            # AppStateComponent
│   │   ├── filesystem_component/
│   │   │   ├── __init__.py
│   │   │   └── filesystem.py           # FilesystemComponent
│   │   ├── plugin_registry_component/
│   │   │   ├── __init__.py
│   │   │   └── plugin_registry.py      # PluginRegistryComponent
│   │   └── logging_component/
│   │       ├── __init__.py
│   │       └── logging.py              # LoggingComponent
│   ├── injector_component/             # the injector (formerly "service locator")
│   │   ├── __init__.py
│   │   └── injector.py                 # InjectorComponent
│   ├── lifecycle/                      # PRD §5.5: hook orchestration, exception capture
│   │   ├── __init__.py
│   │   ├── hooks.py                    # on_load/on_enable/on_disable/on_unload orchestration
│   │   └── excepthook.py               # sys.excepthook wrapping (S11)
│   ├── manifest/                       # plugin & service manifest schemas (Pydantic)
│   │   ├── __init__.py
│   │   ├── plugin_manifest.py
│   │   └── service_manifest.py
│   ├── ui_shell/                       # PRD §7: window, menus, status bar
│   │   ├── __init__.py
│   │   ├── window.py                   # QMainWindow + menus + status bar
│   │   ├── docker_menu.py
│   │   └── alert_panel.py
│   └── version_check.py                # caret semver helpers (S4)
│
├── contracts/                          # Layer 2: type-only seam
│   ├── pyproject.toml
│   └── src/contracts/
│       ├── __init__.py
│       ├── signals.py                  # Signal[T], SubscriptionHandle (mirror of infracore's, S3)
│       ├── filesystem.py               # FilesystemService Protocol, FilesystemEvent
│       ├── state.py                    # AppStateService Protocol
│       ├── plugin_registry.py          # PluginRegistryService Protocol, PluginRecord
│       ├── logging.py                  # LoggingService Protocol
│       ├── injector.py                 # InjectorService Protocol (S2, S17)
│       ├── project.py                  # ProjectService Protocol, Project, ProjectMetadata
│       ├── image.py                    # ImageService Protocol, CropRect, Dimensions, ImageFormat
│       ├── subtitle.py                 # SubtitleService Protocol, SrtOptions
│       ├── manifest.py                 # plugin-facing manifest model (mirror of infracore's)
│       └── exceptions.py               # ServiceNotAvailable, ContractVersionMismatch
│
├── services/                           # Layer 3: services (folder-discovered)
│   ├── injector_service/               # the services-layer injector facade
│   │   ├── manifest.json
│   │   └── service.py                  # InjectorService
│   ├── signal_service/                 # expression service: wraps SignalComponent
│   │   ├── manifest.json
│   │   └── service.py
│   ├── app_state_service/              # expression service: wraps AppStateComponent
│   │   ├── manifest.json
│   │   └── service.py
│   ├── filesystem_service/             # expression service: wraps FilesystemComponent
│   │   ├── manifest.json
│   │   └── service.py
│   ├── plugin_registry_service/        # expression service: wraps PluginRegistryComponent
│   │   ├── manifest.json
│   │   └── service.py
│   ├── logging_service/                # expression service: wraps LoggingComponent
│   │   ├── manifest.json
│   │   └── service.py
│   ├── project_service/                # domain service
│   │   ├── manifest.json
│   │   └── service.py
│   ├── image_service/                  # domain service (Pillow)
│   │   ├── manifest.json
│   │   └── service.py
│   └── subtitle_service/               # domain service (subtitle parsers)
│       ├── manifest.json
│       └── service.py
│
├── plugins/                            # Layer 4: built-in plugins only
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
│   └── integration_agent/              # the gatekeeper from PRD §10
│
├── pyproject.toml
├── pyinstaller.spec
└── README.md
```

The four top-level package directories (`infracore/`, `contracts/`, `services/`, `plugins/`) are siblings. This is the structural expression of the four-layer rule: the directories are peers, but the import direction is one-way — plugins import from `contracts`, services import from `contracts` and `infracore`, contracts imports from neither, and `infracore` imports from neither contracts, services, nor plugins.

Components live inside `infracore/bootstrap_components/` and are not visible outside infracore. The injector inside infracore is `InjectorComponent`, located at `infracore/injector_component/`. The parallel injector inside the services layer (a thin facade for service-to-service injection scenarios) is `InjectorService`, located at `services/injector_service/`. The two never refer to each other by import; `InjectorService` consumes `InjectorComponent` only through its contract.

### 2.2 User-data root layout

The user-data root is unchanged from PRD §13 and is reproduced here only to make the contrast with the source-tree layout explicit:

```
<pantonicvideo-root>/                           # %APPDATA%\PantonicVideo by default
├── config.json                         # infracore's own configuration
├── layout.json                         # docker layout (PRD §7.4)
├── state.json                          # application state store snapshot
├── logs/
│   ├── infracore.log                   # rotating, 10 MB × 5
│   └── plugins/                        # built-in plugin logs (S8)
│       └── <plugin-name>/
│           └── plugin.log              # rotating, 10 MB × 5
└── plugins/                            # third-party plugins only
    └── <plugin-name>/
        ├── manifest.json
        ├── <entry_point>.py
        ├── config.json                 # plugin's own configuration
        └── logs/
            └── plugin.log              # rotating, per-plugin
```

Built-in plugins do not appear under `<pantonicvideo-root>/plugins/`. They are bundled into the `.exe` and discovered through a separate code path (see §6.2). However, their per-plugin log files are written to `<pantonicvideo-root>/logs/plugins/<plugin-name>/plugin.log` (S8) because built-in plugins ship inside the `.exe` and have no writable folder of their own; the user-data root is the only writable destination available.

---

## 3. The contracts layer

`contracts` is the type-only seam of the PantonicVideo platform. It contains `typing.Protocol` definitions, Pydantic models, and enums that services implement and plugins consume. It has no behavior, no runtime logic, no I/O. Its dependencies are limited to `pydantic` and stdlib `typing`.

The contracts layer **does not depend on infracore**. This is a deliberate constraint, not an accident of layering. Infracore's components are internal infrastructural concerns; their types should not leak into a layer designed for plugin authors to import. Conversely, infracore's manifest schemas — used to validate plugin and service manifests at discovery time — live inside infracore, not in contracts. This avoids the inverted-dependency hazard where infracore would import from a downstream layer.

There are two manifest-shaped schemas in the system, one in each direction:

- **infracore-side manifest schemas** (`infracore/manifest/plugin_manifest.py`, `infracore/manifest/service_manifest.py`) are the authoritative validators. Infracore uses them at startup to reject malformed manifests. They live inside infracore because infracore is the consumer; the integration agent is the gatekeeper.
- **plugin-facing manifest model** (`contracts/manifest.py`) is a mirror schema with the same field shape, exposed for plugin authors who want to introspect or generate manifests programmatically. It is a separate Pydantic model with no import from infracore. The two schemas must agree; the integration agent verifies this at build time and fails the build if they have drifted.

The duplication is small (a few dozen fields total) and the cost is justified by the cleaner layering: infracore can be developed, tested, and reasoned about without any reference to the contracts layer.

The contracts package contains the following modules:

| Module | Exposes |
|---|---|
| `contracts.signals` | `Signal[T]` Protocol, `Subscription` Protocol, `SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)` (mirror of infracore, S3) |
| `contracts.filesystem` | `FilesystemService` Protocol, `FilesystemEvent` Pydantic model |
| `contracts.state` | `AppStateService` Protocol |
| `contracts.plugin_registry` | `PluginRegistryService` Protocol, `PluginRecord` Pydantic model, `PluginStatus` enum |
| `contracts.logging` | `LoggingService` Protocol, `LogLevel` enum aliased to stdlib `logging` levels |
| `contracts.injector` | `InjectorService` Protocol (S2, S17) |
| `contracts.project` | `ProjectService` Protocol, `Project`, `ProjectMetadata` Pydantic models |
| `contracts.image` | `ImageService` Protocol, `CropRect`, `Dimensions`, `ImageFormat` enum (`PNG`, `JPEG`) |
| `contracts.subtitle` | `SubtitleService` Protocol, `SrtOptions` Pydantic model |
| `contracts.manifest` | Plugin-facing manifest model (mirror of `infracore.manifest.plugin_manifest`) |
| `contracts.exceptions` | `ServiceNotAvailable`, `ContractVersionMismatch` |

### 3.1 Who imports contracts

- **Plugins** import only from `contracts` and PySide6. A plugin that needs to type a parameter as `ImageService` imports the `Protocol` from `contracts.image`; the concrete `ImageService` implementation is injected at `on_load` and the plugin never sees its identity.
- **Services** import from `contracts` (for the Protocols they implement and the Protocols they consume from sibling services) and from `infracore` (to access the components they wrap or depend on). Services do not import from plugins, ever.
- **Infracore does not import contracts.** The components inside infracore are typed against their own internal interfaces. Where infracore needs a type that contracts also defines (e.g., `SubscriptionHandle`), infracore defines its own version under `infracore/bootstrap_components/signal_component/` and the contracts layer mirrors it. The mirror is structural, not nominal: the two definitions look identical but neither imports the other.

The structural-mirror rule (S3) applies to two specific types: `SubscriptionHandle` (defined identically in `infracore/bootstrap_components/signal_component/handle.py` and in `contracts/src/contracts/signals.py`) and the plugin manifest model (authoritative in `infracore/manifest/plugin_manifest.py`, mirrored in `contracts/manifest.py`). The integration agent verifies textual equivalence (for `SubscriptionHandle`, modulo whitespace) and structural equivalence (for the manifest model, comparing field names, types, and constraints). Drift fails the build.

### 3.2 Versioning

The contracts layer ships at `1.0.0` for v1 launch. Future bumps follow caret-style semver (PRD §11, D11). Adding optional fields, adding new methods on a `Protocol`, or adding new enum values is a minor bump. Breaking signatures is a major bump.

The contracts package version is declared in its `pyproject.toml` and read at runtime by the version-check code (which lives in infracore — see §10).

**Caret semver and version-string normalization (S4).** Every `min_version` and `service_api_version` string in PantonicVideo is parsed as semver. If fewer than three numeric components are present, missing components are treated as `0` (`"1"` → `"1.0.0"`, `"1.2"` → `"1.2.0"`). Anything that does not parse as numeric components separated by dots is rejected at manifest validation; pre-release and build-metadata suffixes are not supported in v1. Caret matching is `^X.Y.Z` ≡ `>=X.Y.Z, <(X+1).0.0` for `X >= 1`. The semver helpers live in `infracore/version_check.py` and are duplicated functionally in the integration agent.

### 3.3 Distribution (S16)

For v1, the `contracts` package is **not** published to PyPI. Plugin authors building outside the source tree clone the PantonicVideo repository and install `contracts` from the local path (`pip install -e ./contracts`). Publication to PyPI is deferred; the `pyproject.toml` is structured so the future publication is a release-engineering task only — no code changes will be required when it happens.

---

## 4. Components and services

This section is the architectural detail behind the vocabulary established in §1.1. Components are the infracore-coupled primitives; services are the contract-shaped capabilities plugins consume. They differ in how they ship, how they are wired, and how their absence is handled.

### 4.1 Components

The six v1 components (S1) live under `infracore/`. Five live under `infracore/bootstrap_components/`; the injector is structurally distinct and lives under `infracore/injector_component/`. Each has its own folder with an `__init__.py` and an implementation module.

| Component | Folder | Responsibility |
|---|---|---|
| `SignalComponent` | `bootstrap_components/signal_component/` | The reactive primitive: `Signal[T]`, subscription registration, value caching. Backbone of all observation surfaces. |
| `AppStateComponent` | `bootstrap_components/app_state_component/` | Application-wide state store; `get`/`set`/`observe`; persists to `state.json` through `FilesystemComponent`. |
| `FilesystemComponent` | `bootstrap_components/filesystem_component/` | The single point of write egress; serializes writes per-path; raises `FilesystemEvent` signals. |
| `PluginRegistryComponent` | `bootstrap_components/plugin_registry_component/` | Discovery, manifest validation, lifecycle bookkeeping; emits `observe_plugins` signal. |
| `LoggingComponent` | `bootstrap_components/logging_component/` | Two channels (per-plugin file logs and the user-visible alert path); rotating handlers. |
| `InjectorComponent` | `injector_component/` | The injector. Registers components and services by name; resolves dependencies during service construction; supplies services to plugins at `on_load` time. |

Components have three properties in common. First, every service in the catalog depends on at least one of them; in particular, every observation contract in v1 routes through `SignalComponent`. Second, infracore itself uses them during startup and shutdown; they exist before any plugin or service loads and after every plugin and service has unloaded. Third, their absence is not a meaningful runtime concept — without `SignalComponent` there is no signal abstraction; without `LoggingComponent` there is no diagnostics path; without `InjectorComponent` there is no way to construct anything.

Components have no manifest because they are not discovered; they are wired in code by `infracore/app.py`. Their version numbers are declared in code. Per S9, each component module declares a module-level constant `__component_version__: str = "1.0.0"` (semver under §3.2 normalization rules). This constant is read by the integration agent (to verify expression-service compatibility) and by infracore-internal compatibility checks where applicable. Plugins do not see component versions; external configuration does not reference them.

`InjectorComponent` is the renamed "service locator" from earlier drafts. The rename is more than cosmetic: a service locator is conventionally a passive registry where consumers ask for things by name; an injector actively constructs things and wires their dependencies based on declarations. PantonicVideo does the latter — services declare `depends_on` in their manifests; `InjectorComponent` reads those declarations, computes a construction order via topological sort, instantiates each service with its dependencies satisfied, and provides the constructed services to plugins at `on_load` according to each plugin's `required_services`. If the topological sort detects a cycle (S5), every service in the cycle is rejected (logged at `ERROR`); the remaining acyclic services proceed. The application does not abort; the cycle is treated like any other service-discovery failure.

### 4.2 Services

Services live under `services/` as folders, each with a `manifest.json` and an entry-point Python module. They are discovered at startup, validated against the service-manifest schema (defined in infracore), and registered with `InjectorComponent`.

There are two kinds of service:

**Expression services** wrap a component and expose its capability to plugins through a contract. The v1 expression services are:

| Service | Wraps | Contract |
|---|---|---|
| `SignalService` | `SignalComponent` | `contracts.signals` |
| `AppStateService` | `AppStateComponent` | `contracts.state` |
| `FilesystemService` | `FilesystemComponent` | `contracts.filesystem` |
| `PluginRegistryService` | `PluginRegistryComponent` | `contracts.plugin_registry` |
| `LoggingService` | `LoggingComponent` | `contracts.logging` |
| `InjectorService` | `InjectorComponent` | `contracts.injector` |

Expression services exist because plugins should not see component internals; they should see only the contract-defined surface. Adding an expression service in front of each component lets us tighten or evolve the component without touching the plugin-facing contract — and conversely, lets us evolve the contract without disturbing infracore.

**Domain services** wrap external libraries and have no component backing:

| Service | Wraps | Contract |
|---|---|---|
| `ProjectService` | (no external lib; thin domain object) | `contracts.project` |
| `ImageService` | Pillow | `contracts.image` |
| `SubtitleService` | subtitle parsers | `contracts.subtitle` |

Domain services exist to confine external dependencies to the services layer. The PRD's Article 4.1 ("plugins must not import external libraries") is enforceable only because every external dependency a plugin might want is wrapped in a domain service.

Domain services may consume expression services (and through them, components). `ImageService` consumes `FilesystemService` to read and write image files; `SubtitleService` consumes `FilesystemService` to read and write SRT files. They never consume components directly.

### 4.3 Why the split between components and services

This split has four benefits. It expresses the genuine semantic difference between infrastructural primitives (components — always present, infracore-internal) and contract-shaped capabilities (services — discovered, contract-bound, plugin-facing). It gives infracore a stable internal vocabulary independent of the contracts layer, so infracore can evolve without dragging the contracts package along. It gives the integration agent a concrete promotion path when it identifies a recurring external dependency: scaffold a folder under `services/`, write the manifest, drop in the implementation. And it confines the failure modes of folder discovery to the layer where folder discovery is meaningful — services and plugins — while keeping infracore's components wired in code where they cannot be absent.

### 4.4 Service manifest

The service manifest is a small JSON document at the root of each service folder, validated against `infracore/manifest/service_manifest.py`:

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

- `name` — the contract name plugins reference in their `required_services`.
- `service_api_version` — the version of the contract this service implements; matched caret-style against the plugin's declared `min_version`.
- `implementation_version` — the version of this implementation, independent of the contract version.
- `entry_point` — `<module>:<class>` resolvable from the service folder.
- `depends_on` — other services this service consumes, with `min_version` constraints. Used by `InjectorComponent` to order construction. Services do not declare component dependencies in the manifest; component dependencies are resolved by name within infracore at construction time.

A service whose dependencies cannot be resolved is rejected at startup with an `ERROR` log entry; plugins that required it become `failed`.

---

## 5. Startup sequence

Infracore's startup is deterministic and ordered. The sequence below is what `infracore/app.py` executes between process start and the Qt event loop running. The build spec (`spec.md` §9) gives the per-step failure modes; the summary below is the architectural shape.

1. **Resolve the user-data root.** Read the override from a startup setting if present; otherwise use `platformdirs` to derive `%APPDATA%\PantonicVideo`. Create the directory and its standard subfolders (`logs/`, `logs/plugins/`, `plugins/`) if missing. If the resolved root is unwritable, the application aborts with a fatal error to stderr (no log file is available yet).

2. **Configure infracore's bootstrap log handler.** Attach the rotating file handler at `<pantonicvideo-root>/logs/infracore.log`. This is a stdlib `logging` handler, configured before `LoggingComponent` exists so that startup itself can log. Once `LoggingComponent` is constructed (step 3), the bootstrap handler stays in place — `LoggingComponent` extends rather than replaces it.

3. **Initialize components.** Construct, in order: `InjectorComponent` (first; it will hold the rest), `SignalComponent`, `FilesystemComponent`, `AppStateComponent`, `LoggingComponent`, `PluginRegistryComponent`. Each is registered with `InjectorComponent` under its component name. The order is fixed in code because `AppStateComponent` and `FilesystemComponent` consume `SignalComponent` (via the callback primitives `SignalComponent` builds upon), `LoggingComponent` consumes `FilesystemComponent` for path resolution, and `PluginRegistryComponent` consumes all four of the others. Components are wired in code; they are not folder-discovered. A failure at any step (constructor raises) aborts startup with a fatal log entry — there is no graceful degradation when a component is broken (see §9, "Component failures are not a runtime concept"). At this point in startup, no service or plugin code has run yet.

4. **Verify the contracts package and load the application state store.** Read `contracts/pyproject.toml` (or its bundled equivalent inside the `.exe`) and cache the version string; no contracts code is imported. Then `AppStateComponent` reads `<pantonicvideo-root>/state.json` if it exists (through `FilesystemComponent`), populates the in-memory store, and is ready for `get`/`set`/`observe` calls. If the file is missing or corrupt, the store starts empty and a `WARNING` is logged; the corrupt file (if present) is renamed to `state.json.corrupt-<timestamp>` for post-mortem.

5. **Install the wrapped `sys.excepthook` (S11).** `infracore/lifecycle/excepthook.py` wraps the existing `sys.excepthook`. The wrapper attributes uncaught exceptions to a plugin by walking the traceback's frames and matching `__file__` against known plugin module roots maintained by `PluginRegistryComponent`. When attribution succeeds, the hook logs to the per-plugin log at `ERROR`, raises an alert at `ERROR`, and marks the `PluginRecord` as `failed`. The previous hook is always called afterward (debugger-friendly). When no frame matches, the hook treats the exception as infracore's and skips plugin-specific routing. The hook is installed *before* plugins load — earlier than earlier drafts of this document placed it — so that exceptions raised during plugin construction or `on_load` are captured.

6. **Discover services.** Scan `services/` (bundled into the `.exe`, resolved through `_MEIPASS` or the source folder in dev mode). For each subfolder, validate the manifest against `infracore/manifest/service_manifest.py`, resolve the entry point, and register the service with `InjectorComponent`. After all manifests are registered, `InjectorComponent.construct_services()` performs a topological sort of `depends_on` and instantiates services in order. **If the sort detects a cycle (S5), every service in the cycle is rejected** (logged at `ERROR` with the cycle's edges enumerated); the remaining acyclic services proceed. A service whose dependency is missing or whose declared dependency does not satisfy the version requirement under caret rules is rejected. Plugins that required a rejected service become `failed`. The application does not abort.

7. **Discover plugins.** Scan two locations in this order: the bundled built-in plugins (source-tree `plugins/`, packaged into the `.exe`) and the user-data plugins folder (`<pantonicvideo-root>/plugins`). For each subfolder, validate the manifest, verify the running `contracts` version satisfies `contracts_min_version` (using the cached version string from step 4), and verify each `required_services` entry resolves against `InjectorComponent` with a compatible `service_api_version`. Manifests that fail validation, plugins whose `contracts_min_version` is unsatisfied, and plugins whose `required_services` cannot be satisfied produce `failed` `PluginRecord`s with reason strings. Successfully validated plugins are recorded as `loaded`, not yet enabled. **Built-in vs third-party name collision (S6):** if a plugin in the user-data scan has a `name` already discovered in the bundled scan, the third-party plugin is recorded as `failed` with reason "name collides with built-in plugin `<n>`". Built-ins always win.

8. **Construct the UI shell.** Build the `QMainWindow`, attach the menu bar, build the Docker menu from the plugin registry's `loaded` and `enabled` plugins (excluding `failed`), attach the status bar with the alert icon subscribed to `SignalService.signal_for_alerts()`.

9. **Restore layout.** Read `<pantonicvideo-root>/layout.json` if present; apply the Qt state. **Recovery on mismatch (S7):** if the file is absent, malformed, or carries an unrecognized `version`, infracore proceeds as on first run (PRD §7.5) and logs a `WARNING` naming the cause. The malformed file (if parseable enough to read at all) is renamed to `layout.json.unrecognized-<timestamp>`. Startup does not fail. On first run, only the Project Launcher's docker is rendered in a default position; other built-in plugins remain `loaded` but not `enabled` and appear in the Docker menu.

10. **Call `on_load` on every loaded plugin.** `InjectorComponent.services_for(plugin_name, required)` resolves each plugin's `required_services` and constructs the plugin with those services injected. Plugins receive only services, never components. An exception in `on_load` marks the plugin `failed` and the application continues; the plugin's per-plugin log gets the `ERROR`, an alert is raised, and the `PluginRecord.failure_reason` is set.

11. **Call `on_enable` on every plugin whose persisted state says it should be enabled.** For each `loaded` plugin, read `AppStateService.get(f"plugins.{name}.enabled")`. If `True`, call `on_enable` and update the `PluginRecord.status` to `enabled`. The `plugins.<name>.enabled` key (S10) is written by `PluginRegistryService.enable / disable`; it is the persistence mechanism behind "remembered enable state". On first run (no layout file fallback), this returns `None` for every plugin except `project_launcher`, which is enabled unconditionally per PRD §7.5. If `on_enable` raises, the plugin is marked `failed`; the persisted `enabled` flag remains `True` so the user's intent is preserved across restarts.

12. **Start the Qt event loop.** `app.exec()`. Control returns when the event loop exits.

Shutdown reverses the relevant steps: `on_disable` is called on every enabled plugin, `on_unload` is called on every loaded plugin, the layout is saved via `QMainWindow.saveState()`, the state store is flushed (write-through means there is little to flush), and logging handlers are closed. Each step captures exceptions and logs at `ERROR`; shutdown does not abort on a single failure.

---

## 6. Layer boundaries and import rules

The four-layer rule is enforceable as a set of import constraints. The integration agent (PRD §10) verifies these constraints; the architecture document defines them.

### 6.1 Allowed import edges

| From → To | Allowed | Notes |
|---|---|---|
| `infracore` → stdlib, PySide6, `platformdirs`, `pydantic` | yes | infracore's only external deps |
| `infracore` → `contracts/` | **no** | infracore does not depend on contracts; manifest schemas live inside infracore |
| `infracore` → `services/` | **no** | infracore is unaware of services as code |
| `infracore` → `plugins/` | **no** | infracore is unaware of plugins entirely |
| `infracore.bootstrap_components.*` → other `infracore.bootstrap_components.*` | yes, ordered | components depend on each other; construction order resolves the DAG |
| `infracore.injector_component` → `infracore.bootstrap_components.*` | yes | the injector knows about all components |
| `contracts/*` → `pydantic`, `typing` | yes | contracts has no other dependencies |
| `contracts/*` → `infracore` | **no** | the layer-independence rule |
| `contracts/*` → `services/`, `plugins/` | **no** | obvious |
| `services/*` → `infracore` | yes | services consume components through infracore's public component API |
| `services/*` → `contracts` | yes | for the Protocols they implement and consume |
| `services/*` → other `services/*` | yes, via contract | concrete dependency declared in the service manifest's `depends_on` |
| `services/*` → external libraries | yes | services are the *only* layer that may |
| `services/*` → `plugins/` | **no** | services do not know plugins exist |
| `plugins/*` → `contracts` | yes | for service Protocols and shared models |
| `plugins/*` → PySide6 | yes | for docker UI rendering |
| `plugins/*` → `infracore` | **no** | strict; components are not for plugins |
| `plugins/*` → `services/*` | **no** | strict; plugins receive services injected, never imported |
| `plugins/*` → external libraries | **no** | strict; PRD §4.1 |
| `plugins/*` → other `plugins/*` | **no** | strict; PRD §4.2 forbids inter-plugin coordination |

### 6.2 Built-in vs third-party plugins

Built-in plugins (the three v1 plugins) live under the source-tree `plugins/` folder. PyInstaller bundles them into the `.exe` at a known internal path; at startup, infracore's plugin discovery code knows to scan that bundled path in addition to the user-data `<pantonicvideo-root>/plugins` folder.

The bundled and user-data plugin discovery paths produce the same kind of `PluginRecord`. There is no privileged status for built-in plugins at runtime: they go through the same manifest validation, the same service-version checks, and the same lifecycle hooks. The only built-in privilege is shipping inside the `.exe`. The Project Launcher's "auto-enabled on first run" property (PRD §9.1, §7.5) is keyed on its name, not on its built-in status, so the same behavior would apply to a third-party plugin named `project_launcher` — which is fine, because plugin names are unique within the running PantonicVideo instance (PRD §6.1).

Third-party plugins drop into `<pantonicvideo-root>/plugins/` and are discovered on the next launch. There is no hot-reload; PRD §2.2 deferred it explicitly.

### 6.3 Enforcement

Three enforcement mechanisms operate together:

The **integration agent** runs static import analysis on plugins and services before admitting them. It rejects any plugin that imports `infracore.*`, any service implementation, or any external library (PRD §10). It rejects any service that imports a plugin or imports a component that the service is not authorized to wrap. It rejects any contracts module that imports from `infracore`. The agent's strictness is the architectural premise — plugins and services that reach the platform have already been gated. The agent also verifies that infracore's manifest schemas and the contracts-layer mirror have not drifted; a mismatch fails the build.

The **InjectorComponent** enforces the runtime expression of the rule. Plugins receive services through constructor injection and never have a way to obtain a service or component by import; the only handle a plugin has on a service is the `Protocol`-typed reference passed at `on_load`. Components are never injected into plugins; only services are.

The **manifest validation** rejects malformed manifests at discovery (PRD §6.1). A plugin that declares an external library in its requirements does not exist; the plugin manifest schema (in `infracore/manifest/plugin_manifest.py`) has no field for that.

These mechanisms are layered: integration-time analysis catches most violations before they ship; injector-shaped construction prevents the runtime from offering an escape; manifest schemas constrain what a plugin or service can ask for in the first place.

---

## 7. The signal abstraction in practice

The signal abstraction (PRD §4.3, §8.1) is the most consequential architectural commitment in the platform. Every observation contract in v1 routes through `Signal[T]` because the platform standardizes on one reactive idiom.

The implementation responsibility is split between `SignalComponent` (inside infracore) and `SignalService` (in the services layer). `SignalComponent` is the engine: it manages subscription registration, holds the latest emitted value, and notifies subscribers on change. `SignalService` is the contract-shaped expression: it is what other services and plugins receive when they need to observe something. `SignalService` does no work `SignalComponent` does not already do — it is a thin facade that confines the component's identity to infracore.

Other expression services that surface observations (`AppStateService.observe`, `FilesystemService.watch`, `PluginRegistryService.observe_plugins`) and domain services that surface observations (`ProjectService.observe_current`) do not implement signals themselves. They delegate to `SignalService`, which delegates to `SignalComponent`. The concept of "a signal" is centralized: if the platform ever needs to swap the reactive idiom (RxPy observables, plain pub/sub, etc.), the swap happens in `SignalComponent` — and possibly the contract for `SignalService` — but not across every service.

There is one corollary worth stating explicitly: there is no polling anywhere in the platform (PRD §4.3). Plugins that need to react to a state change subscribe through a service; services that need to react to component changes subscribe through a component. The design admits no other mechanism.

---

## 8. The write-coordination invariant

`FilesystemComponent` is the single point of egress for filesystem writes (PRD §8.3). This is not a convention; it is an invariant. Every other component and service routes its writes through `FilesystemComponent`, including `AppStateComponent` (when it persists `state.json`), `ProjectService` (when it writes the project metadata file), and the domain services that touch user files (`ImageService`, `SubtitleService`).

The reason is operation collision. The application has three concurrent write sources: the application state store flushing on `state_set`, plugins committing operations through domain services (image crops, subtitle files), and infracore's own writes (layout persistence, log rotation). Without a single serialization point, two of those sources can collide on the same path or on related paths, and the failure mode is silent corruption of a file the user does not realize was being written.

`FilesystemComponent` serializes writes per-path: writes to different paths proceed in parallel; writes to the same path queue. This is a finer guarantee than "one global write lock" and a coarser guarantee than "no concurrency anywhere." It is the right grain for the v1 scale.

The expression service `FilesystemService` is a thin facade over `FilesystemComponent`. It does not add serialization of its own; the serialization is the component's responsibility. The service exists to give plugins a contract-typed handle without exposing the component's identity, and to allow the contract to evolve independently of the component's internals.

A subtle implication: log writes do not go through `FilesystemComponent`. Both infracore's bootstrap log handler (`<pantonicvideo-root>/logs/infracore.log`) and `LoggingComponent`'s plugin log files use stdlib `logging`'s own handlers, which have their own thread-safety. Routing them through `FilesystemComponent` would couple two independent serialization disciplines and gain nothing. Logs are the documented exception.

---

## 9. Diagnostics and failure containment

The PRD specifies the user-facing diagnostics surface — the alert icon (§7.3), the two `LoggingService` channels (§8.5), and the lifecycle exception capture (§5.5). The architecture adds the routing rules that connect them.

**Plugin runtime exceptions** are caught at three boundaries: the four lifecycle hooks (`on_load`, `on_enable`, `on_disable`, `on_unload`), the Qt event-loop `sys.excepthook`, and any explicit try/except a plugin author writes. The first two are infracore's responsibility; they translate an exception into a `failed` `PluginRecord` with a reason string and route the failure to `LoggingComponent`'s alert path. The third is the plugin author's responsibility.

**Service runtime exceptions** are not caught by infracore. A service that raises is a service-level bug; the exception propagates to the calling plugin, which catches it (or doesn't) and decides how to react. Plugins that wish to be resilient to service failures wrap their service calls in try/except; plugins that don't bubble the exception to the lifecycle boundary, where infracore's capture turns it into a `failed` status.

**Manifest validation failures** (plugin or service) are logged at `ERROR` to infracore's log and surface in the plugin registry as `failed` records. They do not propagate as exceptions; they are diagnostic data, not control flow.

**Service discovery failures** (a service that fails to construct) are logged at `ERROR`; the service is absent from `InjectorComponent`. Plugins that required it become `failed` because their `required_services` cannot be satisfied. The chain of consequences (service missing → plugin fails → docker absent) is visible end-to-end through the alert icon and the logs.

**Component failures** are not a runtime concept. A component that cannot be constructed at startup is an infracore bug; the application aborts startup with a fatal log entry. There is no graceful degradation when a component is broken — the platform has no contract for running without one.

The architectural goal is that no single non-fatal failure cascades. A bad plugin does not crash the application; a bad service does not break the rest of the catalog; a corrupt state file degrades to an empty store with a logged `WARNING` rather than a startup failure.

---

## 10. Versioning interactions

There are five version axes in the running system. Four are visible to plugin authors (contracts package, service API, service implementation, infracore release); the fifth (component version) is internal:

| Axis | Where declared | Read by | Caret-matched against |
|---|---|---|---|
| Contracts package | `contracts/pyproject.toml` | `infracore.version_check` at startup | Plugin's `contracts_min_version` |
| Service contract (`service_api_version`) | Each service's `manifest.json` | `InjectorComponent` | Plugin's `required_services[].min_version` |
| Service implementation (`implementation_version`) | Each service's `manifest.json` | Integration agent only | Diagnostic, not enforced at runtime |
| Infracore release | `infracore/_versions.py` | Release engineering | Not matched against anything at runtime (PRD D12) |
| Component (`__component_version__`, S9) | Each component module | Integration agent | Expression-service compatibility |

The plugin-load check is performed by infracore. A plugin's manifest declares `contracts_min_version` (one number) and a list of `required_services`, each with a `min_version` (one number per service). At `on_load`, infracore verifies:

First, that the running `contracts` package satisfies the plugin's `contracts_min_version` under caret semantics (D11). The `contracts` version is read from its `pyproject.toml` at startup; infracore caches the value as a string and compares it against the manifest's declared minimum without importing anything from the contracts package.

Second, that for each entry in `required_services`, a service of that name is registered with `InjectorComponent` and its `service_api_version` satisfies the plugin's `min_version` under caret semantics.

If either check fails, the plugin is not loaded; the failure surfaces with a reason string ("contracts version too old," "service `image_service` not available," "service `image_service` version 1.0.0 does not satisfy plugin requirement 1.2") through `LoggingComponent`'s alert path and as a `failed` `PluginRecord`.

Infracore's own release version is not checked against anything. Plugin authors do not declare an infracore version (D12). The discipline that an infracore release does not break a plugin is enforced by infracore's commitment to the contracts layer: an infracore release that changes a component's behavior in a way visible through its expression service must bump the corresponding `service_api_version`, and plugins with strict requirements will refuse to load against it.

Service-to-service version dependencies (declared in a service manifest's `depends_on`) follow the same caret rules. A service that requires `signal_service >= 1.0` and finds `signal_service 2.0` registered is not constructed; this surfaces as a service-discovery failure as described in §9.

---

## 11. Packaging and distribution

PyInstaller bundles the `.exe` from the source tree. The bundle includes:

- The `infracore/` package, including all components under `bootstrap_components/` and the injector under `injector_component/`, plus its dependencies (PySide6, `platformdirs`, `pydantic`).
- The `contracts/` package.
- Every service folder under `services/` (both expression services and domain services), including each manifest and entry-point module, plus each service's external dependencies (Pillow for `ImageService`, etc.).
- Every built-in plugin folder under `plugins/`, including its manifest and entry-point module.

PyInstaller is configured for one-file mode with a splash screen during unpack (PRD §12). The cold-start tuning levers — UPX compression, excluded modules, fallback to one-folder packaging — are not committed in v1; they are exercised empirically once measurements exist.

At runtime, infracore distinguishes "bundled paths" (services and built-in plugins, accessed through PyInstaller's `_MEIPASS` mechanism or equivalent) from "user-data paths" (third-party plugins under `<pantonicvideo-root>/plugins`). Both produce equivalent records in the registry; the distinction matters only for discovery, not for execution. There is one user-visible consequence of the bundled/user-data split: built-in plugins ship inside the `.exe` and have no writable folder of their own, so their per-plugin log files are written under `<pantonicvideo-root>/logs/plugins/<plugin-name>/plugin.log` rather than alongside the plugin code (S8). Third-party plugin logs remain at `<pantonicvideo-root>/plugins/<plugin-name>/logs/plugin.log`. `LoggingComponent` resolves the path from the `PluginRecord.is_builtin` flag at first use.

The `.exe` is the PantonicVideo distribution format. Source distribution is available through the public GitHub repository for plugin authors who want to read contracts, but the platform itself is consumed as a binary. **Contracts distribution (S16):** for v1, the `contracts` package is not published to PyPI. Plugin authors building outside the source tree clone the repository and install `contracts` from the local path (`pip install -e ./contracts`). Publication to PyPI is deferred; the `pyproject.toml` is structured so the future publication is a release-engineering task only.

---

## 12. Out-of-scope for v1, named for the architectural record

These items are deferred per the PRD; they are listed here because each has architectural implications that v1 design must not foreclose.

**Pipelines.** Cross-plugin orchestration is a v2 concern. The architectural prerequisite — that signals carry typed values, that services expose well-defined inputs and outputs, and that the plugin registry can enumerate `PluginRecord`s for runner consumption — is met in v1. The pipeline runner can be added as a service in v2 without infracore changes.

**`CapCutAdapterService`.** A future domain service. Will live under `services/capcut_adapter_service/`, follow the same manifest discipline, and likely depend on `FilesystemService` and `SignalService`. No infracore changes anticipated.

**Hot-reload.** Out of scope, possibly forever. The architectural cost is real: the lifecycle hook invariants assume a plugin loads once and is unloaded once per process. Hot-reload would require `PluginRegistryComponent` to support load-while-running and `InjectorComponent` to support re-injection, neither of which v1 builds toward.

**Permissions enforcement.** The manifest's `permissions` field is reserved (PRD §6.1) and parsed but ignored. The architecture preserves the field through validation; enforcement is a v2+ concern.

**Sandboxing or out-of-process plugins.** Not committed in any future PRD currently named. Plugins run in-process with full Python capabilities; this is the security posture the PRD accepted (§14). A future change to this stance would be invasive — it would add an IPC layer between plugins and services and is not the kind of thing the platform absorbs without modification to the core.

---

## 13. Traceability

### 13.1 Architecture sections to PRD sections

| Architecture section | PRD section | Resolution |
|---|---|---|
| §1 Architectural overview | §4 | reframed as four layers; component/service vocabulary introduced |
| §1.1 Components vs services | new | vocabulary distinction made explicit |
| §2.1 Source-tree layout | new | Q1 resolved: monorepo with runtime distinction; `bootstrap_components/` and `injector_component/` placement specified |
| §2.2 User-data root | §13 | path renamed to `%APPDATA%\PantonicVideo`; per-plugin log paths split for built-ins (S8) |
| §3 Contracts layer | §4.1, §11 | renamed to `contracts`; declared independent of infracore; module catalog enumerated |
| §4 Components and services | new | Q3 resolved: components static under `infracore/bootstrap_components/`, services folder-discovered under `services/` |
| §4.1 Components | new | six v1 components enumerated (S1); `__component_version__` constant convention (S9) |
| §4.2 Services | new | expression services (component facades) and domain services distinguished |
| §4.4 Service manifest | new | manifest schema lives in infracore, mirrored in contracts |
| §5 Startup sequence | §5.5, §6, §7.5, §8.9 | composed from PRD pieces; excepthook installed early (S11); cycle handling (S5); name collision (S6); layout recovery (S7); persisted-enable mechanism (S10) |
| §6 Layer boundaries | §4.1, §4.2, §6 | import rules updated for four layers and contracts/infracore independence |
| §6.2 Built-in vs third-party plugins | §2.3, §9, §12, §13 | runtime distinction unchanged |
| §7 Signal abstraction in practice | §4.3, §8.1 | split between `SignalComponent` and `SignalService` made explicit |
| §8 Write-coordination invariant | §8.3 | invariant moved to `FilesystemComponent`; service is a thin facade |
| §9 Diagnostics and failure containment | §5.5, §6.5, §7.3, §8.5 | component failure semantics added |
| §10 Versioning interactions | §11, §6.1, §8.9 | manifest field renamed to `contracts_min_version`; five-axis table including component version |
| §11 Packaging and distribution | §12, §13 | bundling specifics updated for components and services; contracts not on PyPI for v1 (S16) |
| §12 Out-of-scope for v1 | §2.2, §15 | references updated to use injector and component vocabulary |

### 13.2 Architecture sections to build-spec decisions

The build spec (`spec.md`) introduces seventeen pre-spec decisions (S1–S17) that pin mechanics this document had left open. The mapping below records where each landed in this revision; the spec is the normative source for the underlying detail.

| Decision | Subject | Folded into |
|---|---|---|
| S1 | Six v1 components | §1.1, §4.1 |
| S2 | `contracts/injector.py` added | §1.1, §2.1, §3 module table |
| S3 | `SubscriptionHandle` mirror, `NewType[uuid.UUID]` | §3.1, §3 module table |
| S4 | Caret semver normalization rule | §3.2 |
| S5 | Service `depends_on` cycles rejected, not fatal | §4.1, §5 step 6 |
| S6 | Built-ins win on name collision | §5 step 7 |
| S7 | Layout version mismatch falls back to first-run | §5 step 9 |
| S8 | Built-in plugin logs under `<pantonicvideo-root>/logs/plugins/<n>/` | §2.2, §11 |
| S9 | `__component_version__` constant | §4.1, §10 |
| S10 | `plugins.<n>.enabled` in app state | §5 step 11 |
| S11 | Wrapped `sys.excepthook` installed early | §5 step 5 |
| S12 | 50 ms warning window for state-write collisions | spec §4.4 (mechanic only) |
| S13 | `update_metadata` atomicity via per-path serialization | spec §5.8 (mechanic only) |
| S14 | Click-to-acknowledge alerts, in-memory only | spec §7.3 (mechanic only) |
| S15 | `description` in tooltip; `author` in alert detail | spec §7.2, §7.3 (UI mechanic only) |
| S16 | `contracts` not on PyPI for v1; install from local path | §3.3, §11 |
| S17 | `Injector` Protocol with single `resolve` method | §1.1, §3 module table |

S12, S13, S14, and S15 are implementation mechanics with no architectural-shape change; they are recorded here for traceability but live entirely in the build spec.

### 13.3 v1 catalog

The v1 catalog comprises:

- **Six components** (in infracore, S1): `SignalComponent`, `AppStateComponent`, `FilesystemComponent`, `PluginRegistryComponent`, `LoggingComponent`, `InjectorComponent`.
- **Nine services** (in the services layer): six expression services (`SignalService`, `AppStateService`, `FilesystemService`, `PluginRegistryService`, `LoggingService`, `InjectorService`) plus three domain services (`ProjectService`, `ImageService`, `SubtitleService`).

The PRD's catalog of eight services maps directly onto the eight non-injector services here; the addition is `InjectorService` as the contract-shaped expression of `InjectorComponent` (S2, S17). No additional domain services are introduced (Q2 resolution: dispense with extra services for now). Future services follow the integration-agent promotion path described in PRD §10 and §4 of this document.
