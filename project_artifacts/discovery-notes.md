# Infracore — Discovery Notes

**Document purpose:** Consolidated record of the discovery phase for the Infracore desktop application. This document is the authoritative input for the PRD (Product Requirements Document) stage.

**Status:** Discovery complete.
**Date:** April 2026.

---

## 1. Product summary

**Infracore** is a Windows desktop application, written in Python, that hosts independent plugins ("dockers") inside a single customizable window. Its purpose is to unify and partially automate the tasks involved in producing and editing videos for YouTube, with CapCut as the primary editing target.

The product is optimized for a single user: the author, a developer-tinkerer who will build most plugins with AI-assisted coding. The platform's long-term value is extensibility and code health, not feature breadth at launch.

---

## 2. Problem and motivation

### 2.1 Core pain

Producing videos in CapCut consumes disproportionate time on repetitive preparation tasks: resizing and cropping images, populating the timeline with assets, adjusting captions, and preparing animations. Ad-hoc standalone scripts partially address individual tasks, but:
- Each script lives in its own folder and must be invoked manually.
- There is no shared infrastructure, so each new script carries the same overhead as the last.
- There is no synergy — scripts cannot compose into larger workflows.

### 2.2 What Infracore solves

- **Unified workspace.** All artifacts of a video project (assets, scripts, configuration files) visible on one screen.
- **Shared infrastructure.** New tooling ideas reuse existing services instead of being rebuilt from zero.
- **Composable automation (v2).** Plugins can be chained into pipelines that execute sequentially.
- **Healthy extensibility.** A clean plugin contract means future AI-assisted development can add capabilities without touching the core.

### 2.3 Positioning

**Platform-first.** The discovery prioritizes robust infrastructure over feature count. End-user feature breadth is a downstream concern.

---

## 3. Users

### 3.1 Persona

A single persona: **Developer-tinkerer**, comfortable with Python, leveraging AI coding assistants and agentic programming for most plugin development.

### 3.2 User assumptions

- One user per machine. No multi-user, profile, or SSO concerns.
- Plugin authors do not need to understand infracore's internals. They only need knowledge of **service contracts** and **integration contracts**.
- No plugin development should require changes to infracore. At most, a plugin may propose new services or extensions to existing services.
- Distribution of third-party plugins is not a concern of the official repository. Forks are welcome; third-party plugin safety is the fork owner's responsibility.

### 3.3 Repository governance

- Public GitHub repository.
- Only the author merges PRs into the central repository.
- The central repository ships only the plugins the author considers essential.

---

## 4. References

- **Krita** — primary reference for the UI paradigm (dockable widgets, customizable layout, concise docker surfaces).
- **Blender** — known but rejected as a UI reference; its density is considered excessive for this product.

The Krita model is closer to the intended feel: concise dockers, low information density per panel, user-driven layout.

---

## 5. Architecture — non-negotiable premises

Infracore enforces a strict three-layer separation. This is the single most important architectural decision in the project and shapes every subsequent requirement.

### 5.1 The three layers

**Layer 1 — Infracore (the core).**
Owns all low-level operations: filesystem I/O, OS interactions, plugin lifecycle management, shared application state, logging sink, plugin registry. Exposes generic, domain-agnostic APIs. Contains no domain logic. Contains no external-library dependencies beyond the GUI framework and stdlib-adjacent tooling.

**Layer 2 — Service layer.**
The **only** consumer of infracore APIs. Services add domain semantics on top of generic infracore operations. All external dependencies (image libraries, subtitle parsers, CapCut JSON schema knowledge, etc.) are encapsulated here. Services expose public contracts that plugins consume. Services are injected into plugins via dependency injection.

**Layer 3 — Plugins.**
Pure orchestration and UI. Plugins consume service contracts only. Plugins never call infracore directly. Plugins never import external libraries. A plugin's job is to present a UI (a docker), collect user intent, and delegate work to services.

### 5.2 Implications of the three-layer rule

- When an external format (e.g., CapCut's JSON schema) changes, only one service updates. Plugins and infracore are unaffected.
- Infracore remains domain-free in perpetuity. It never learns what a "video project" or a "subtitle" is.
- Plugin authors work against a stable, versioned service contract surface and do not track infracore versions.
- The service layer is a genuine anti-corruption boundary between the platform and the outside world.

### 5.3 Application state store

Infracore maintains an in-memory key-value store (persisted to disk as JSON) for shared ecosystem state — for example, the current project folder. Plugins never read or write this store directly; they go through a service, which goes through infracore. OS environment variables are **not** used for this purpose.

---

## 6. Features — v1 scope

### 6.1 UI shell

- Standard Windows window chrome.
- A top menu bar including a **Docker** menu that lists all available dockers; the user enables or hides dockers from this menu.
- A **status bar** at the bottom hosting the **alert icon**.
- Light mode only. Other themes are out of scope for v1 and may be added later by plugins or services.

### 6.2 Dockers (plugin UI)

- Dockable, movable, resizable widgets following the Krita paradigm.
- Built on Qt's native `QDockWidget` via PySide6.
- Each docker is provided by exactly one plugin.

### 6.3 Layout persistence

- Docker positions, sizes, and visibility persist across restarts.
- Single layout only. No named layouts, no per-user layouts, no workspace concept.

### 6.4 Plugin lifecycle

Four lifecycle hooks, called by infracore in this order:

1. **`on_load`** — service contract verification. Plugin confirms all required services and versions are available. If not, plugin is not loaded and a failure entry appears under the alert icon.
2. **`on_enable`** — plugin loads its configuration and renders its docker on screen.
3. **`on_disable`** — plugin stops execution and hides its docker.
4. **`on_unload`** — plugin persists any changed configuration.

Plugin errors must never crash infracore. Errors are logged by the plugin (full log inside the plugin's own filesystem area for manual inspection) and a summarized entry is propagated to infracore's alert surface.

### 6.5 Plugin installation UX

- Plugins are installed by placing a plugin folder inside infracore's `/plugins` directory. Restart required.
- On launch, infracore scans `/plugins`, validates each manifest, and lists all passing plugins in the Docker menu as available dockers.
- Plugins with invalid manifests or unmet service requirements are **not** listed as available dockers; their failure reasons appear under the alert icon.

### 6.6 Plugin configuration

- Plugin configuration is the responsibility of the plugin itself. Infracore does not provide a standardized settings panel.

### 6.7 Alerts and diagnostics

- Alert icon in the status bar.
- Clicking the icon shows a brief summary of errors.
- Drilling in shows summarized plugin error messages.
- Full plugin error logs remain in the plugin's own filesystem area.
- Infracore itself uses stdlib `logging` with a rotating file handler under `<infracore-root>/logs`.

### 6.8 First-run experience

Infracore ships with three built-in plugins:

1. **Project Launcher** — prompts for a destination folder; the selection is passed through a service to infracore, which stores it in the application state store. Other plugins read the current project via the appropriate service's read API.
2. **Image Cropping** — resize and crop static images.
3. **Subtitle Text Tool** — convert text to `.srt` subtitle files.

### 6.9 Explicitly out of scope for v1

- Pipelines / workflows (deferred to v2, see §7).
- CapCut JSON editing plugin (planned but not v1; will require the `CapCutAdapterService` described in §8).
- Image enhancement plugin (planned, not v1).
- Inter-plugin direct communication (never — by design).
- Dark mode / theming.
- Multi-user support.
- System tray presence or autostart.
- Native notifications.
- Hot-reload of plugins (restart is acceptable for the product's lifetime).
- Plugin marketplace / in-app plugin browser.
- Third-party plugin support in the official repository.

---

## 7. Pipelines / workflows — v2 feature (scoped here for continuity)

Deferred to v2, but the shape is agreed:

- A pipeline is a stored, ordered list of plugin invocations executed sequentially when data preconditions are met. Conceptually similar to a cron job chained across plugins.
- Execution waits for one plugin to complete before triggering the next. No concurrent execution. No direct plugin-to-plugin communication.
- Each plugin declares an **input contract** and an **output contract** (Pydantic v2 models referenced by name in the manifest). The pipeline runner validates that adjacent plugins' output and input contracts are compatible; it refuses to start an inconsistent pipeline.
- Pipelines require infracore APIs (plugin management), mediated through the service layer. The UI and configuration of pipelines is implemented by a **native plugin**, not by infracore itself, preserving the three-layer rule.
- Pipeline definitions are configured through a UI and persisted as JSON documents.

---

## 8. Integration and services

### 8.1 Operating system

- Windows-only for v1.
- Linux support is allowed *if* it introduces no meaningful complexity. The practical rule: use `pathlib` everywhere, avoid Windows-specific APIs where Qt offers a portable equivalent. No macOS plans.

### 8.2 Filesystem conventions

- Default to platform conventions (e.g., `%APPDATA%\infracore` on Windows via `platformdirs`), but allow the user to override the root directory.

### 8.3 Dependency management

- A single Python environment, bundled inside the packaged `.exe` via PyInstaller. The user's system Python is untouched; the user never installs dependencies.
- All external dependencies live in the service layer.
- Plugin development proceeds in two stages:
  1. **PoC stage** (external to the platform): a standalone script proves the functional requirement, preferably in pure Python, using free external dependencies if necessary.
  2. **Integration stage**: external dependencies are moved into (or consumed via) the service layer. The plugin is rewritten against service contracts and integration contracts. Only after this onboarding is the plugin accepted by infracore.

### 8.4 Service contracts

- Defined as Python `typing.Protocol` classes.
- Each service carries a `service_api_version` string.
- Contracts are distributed in a small `infracore-contracts` package that plugins import. This package is the stable surface that plugin authors track.
- When a plugin's declared service requirements cannot be satisfied (missing service, incompatible version), the plugin is not loaded; a summarized reason appears under the alert icon.

### 8.5 Plugin input/output contracts

- Defined as **Pydantic v2 models**.
- Referenced by name in the plugin's JSON manifest.
- Used by the pipeline runner (v2) to validate plugin chaining.

### 8.6 Plugin manifest (JSON)

Schema fields:

- `name`
- `version`
- `infracore_min_version`
- `author`
- `description`
- `entry_point` — Python module path
- `required_services` — list of `{name, min_version}`
- `inputs` — list of Pydantic model references
- `outputs` — list of Pydantic model references
- `permissions` — deferred to v2; reserved field

### 8.7 CapCut integration approach (future plugin)

- Infracore exposes generic find, read, and write filesystem APIs.
- A `CapCutAdapterService` in the service layer understands CapCut's JSON schema, maps generic video-editing operations to specific key manipulations, and requests reads/writes through infracore.
- The CapCut plugin itself is thin: it surfaces a UI for domain-level video-editing intents and delegates to the adapter service.
- When CapCut changes its format, only the adapter service updates. The plugin and infracore are unaffected.
- Known risk: CapCut's format is proprietary and undocumented. The adapter service is best-effort and will be version-pinned to specific CapCut releases.

### 8.8 Versioning principles

- Semantic versioning on the `infracore-contracts` package and on each individual service's `service_api_version`.
- No infracore internal APIs are exposed to plugins, ever.
- Plugin authors track service contract versions only, not infracore versions.

### 8.9 Security posture

- Plugins run in-process and have full Python capabilities.
- For single-user home use, this is accepted. A permissions model is reserved in the manifest but not enforced in v1.

---

## 9. Stack

| Area | Choice |
|---|---|
| GUI framework | PySide6 (LGPL) |
| Language | Python 3.12 (fallback to 3.11 if PyInstaller issues arise) |
| Packaging | PyInstaller, **one-file `.exe`** mode |
| Dependency management | `uv` + `pyproject.toml` |
| Plugin manifest format | JSON |
| Plugin discovery | Filesystem scan of `/plugins` at launch |
| Service layer pattern | Simple service locator / registry |
| Service contracts | `typing.Protocol` + `service_api_version` string, distributed in `infracore-contracts` |
| Plugin I/O contracts | Pydantic v2 models, referenced by name in manifest |
| Application state store | In-memory key-value, persisted as JSON |
| Config storage | JSON |
| Logging | stdlib `logging` with a rotating file handler under `<infracore-root>/logs` |
| Testing | `pytest`, with `pytest-qt` for UI tests |
| Distribution | Public GitHub repository; `.exe` provided for fast usage |

**Packaging note:** One-file mode has a known cold-start cost because PyInstaller unpacks to a temporary directory on launch. The user has accepted this tradeoff in exchange for single-file distribution, combined with care to persist last-session settings and keep loading times low otherwise.

---

## 10. Open items for the PRD stage

These do not block discovery but should be resolved during PRD authoring:

1. **Exact infracore public API surface.** Minimally: filesystem operations, application state store, plugin registry, logging sink. Final list to be enumerated.
2. **Initial service catalog for v1.** Working names: `ProjectService`, `ImageService`, `SubtitleService`. `CapCutAdapterService` is v1.1+. Exact boundaries and method signatures to be finalized.
3. **Conflict resolution in the application state store** when multiple plugins request incompatible state changes. Likely a v2 concern but should be named in the PRD.
4. **Exact serialization format of the application state store.** Recommended: JSON for v1.
5. **Specific PyInstaller configuration** to minimize cold-start cost in one-file mode (e.g., UPX settings, excluded modules).

---

## 11. Decision summary

| # | Decision |
|---|---|
| 1 | Target user: single developer-tinkerer leveraging AI-assisted coding. |
| 2 | Core purpose: automate everyday video creation and editing tasks around CapCut. |
| 3 | GUI framework: PySide6. |
| 4 | Plugins use JSON manifests. Lifecycle hooks: `on_load`, `on_enable`, `on_disable`, `on_unload`. Plugins never communicate with each other directly. |
| 5 | Three-layer architecture (infracore → services → plugins) is non-negotiable. Plugins never reach infracore directly; services are the only consumer of infracore APIs; only services hold external dependencies. |
| 6 | Distribution: public GitHub repository, plus one-file `.exe` via PyInstaller. |
| 7 | v1 ships with three built-in plugins: Project Launcher, Image Cropping, Subtitle Text Tool. Pipelines and the CapCut plugin are deferred. |
