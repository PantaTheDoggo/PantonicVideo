# EdiVi — Sprint Plan

**Source:** `spec_v2.md` v1.1 (April 2026), §19 (Development plan, agents, and skills).
**Total sprints:** 26, distributed across 5 milestones per §19.6.
**Gate model:** every sprint exits with the same shape — its target test file goes red→green, the integration agent stays green, and `code-critic` ratifies the PR (§19.6). Milestone gates are binary: M*n+1* may not begin until M*n* is accepted (§19.2).

## Conventions used below

- **Skills column** lists the skill files (per §19.5 template) carried by the responsible agents. Every skill begins verbatim with G1–G10 (§19.1) — that is implicit in every row and is not repeated.
- **DoD** = Definition of Done. The universal exit criterion from §19.6 (target tests green, integration agent green, code-critic ratifies) applies to every task; the DoD column states only what is *additional or specific* to that task.
- **Agent** names match §19.4: `test-author`, `infracore-builder`, `service-builder`, `plugin-builder`, `integration-agent`, `code-critic`, `release-engineer`. The `integration-agent` and `code-critic` are gating/advisory on every sprint M2–M5 and are not relisted per task except where their work is the task itself.

---

## Milestone M1 — Functional-test corpus (5 sprints)

**Acceptance gate (§19.2):** the complete test suite under `tests/` exists and runs. Production code does not yet exist; the entire suite is **red**. Test shape reflects §16.1's per-layer discipline.

One sprint per layer, plus one for the integration-agent's own static checks. Sole executing agent: `test-author` (§19.4.1). `integration-agent` is not yet gating in M1 but is consulted for tests under `tests/integration/` to ensure they encode §13.1's checks.

### Sprint M1.S1 — Infracore test corpus

| Field | Value |
|---|---|
| **Task** | Author `tests/infracore/` |
| **Description** | Produce failing pytest modules covering every component in §4 (`SignalComponent`, `AppStateComponent`, `FilesystemComponent`, `PluginRegistryComponent`, `LoggingComponent`, `InjectorComponent`), the lifecycle module (§9.10–§9.11, §6.2), the wrapped excepthook (§9.5, S11), and the UI shell (§7). Tests use real component instances per §16.1 (no mocking inside infracore). Each test docstring names the spec section it derives from. Failure-mode parametrizations cover §11. |
| **DoD** | All test files exist, are collected by pytest, and fail (red) because the implementations they target do not exist. Spec-section docstrings are present on every test. No production code is touched. |
| **Skills** | `test-author` |
| **Agent** | `test-author` |

### Sprint M1.S2 — Contracts test corpus

| Field | Value |
|---|---|
| **Task** | Author `tests/contracts/` |
| **Description** | Tests verify Pydantic schema acceptance/rejection per §3, enum values, and the structural-mirror invariants of §3.3 (`SubscriptionHandle` parity between `infracore.bootstrap_components.signal_component.handle` and `contracts.signals`; plugin-manifest model parity between `infracore.manifest.plugin_manifest` and `contracts.manifest`). Caret-semver normalization helpers (§3.4) and `ContractVersionMismatch` / `ServiceNotAvailable` (§3) get coverage. |
| **DoD** | All contracts tests exist and fail because `contracts/` is empty. Mirror-invariant tests are written so they will fail loudly on drift, mirroring what `integration-agent` enforces statically. |
| **Skills** | `test-author` |
| **Agent** | `test-author` |

### Sprint M1.S3 — Services test corpus

| Field | Value |
|---|---|
| **Task** | Author `tests/services/` |
| **Description** | One test file per service (nine total per §1): six expression services (`signal_service`, `app_state_service`, `filesystem_service`, `plugin_registry_service`, `logging_service`, `injector_service`) and three domain services (`project_service`, `image_service`, `subtitle_service`). Per §16.1, components are mocked for expression-service tests; services are mocked for domain-service tests; Pillow and similar libraries are stubbed in unit tests, with one integration smoke test per domain service that exercises the real library. Manifest validation tests (§5.1) included per service. |
| **DoD** | Nine test files present and red. Stubs for Pillow / SRT-handling are in place under `tests/services/conftest.py`. |
| **Skills** | `test-author` |
| **Agent** | `test-author` |

### Sprint M1.S4 — Plugins test corpus

| Field | Value |
|---|---|
| **Task** | Author `tests/plugins/` |
| **Description** | One test file per plugin (three total per §6.5): `project_launcher`, `image_cropping`, `subtitle_text_tool`. Each plugin is tested with mocked services per §16.1; UI is exercised via `pytest-qt`. Manifest-validation tests per §6.1 (strict, `additionalProperties: false`). Lifecycle-hook tests per §6.2 confirming `on_load`/`on_enable`/`on_disable`/`on_unload` are called in order on a clean fixture. |
| **DoD** | Three test files present and red. `pytest-qt` is configured. Mocked-service fixtures are reusable across plugins. |
| **Skills** | `test-author` |
| **Agent** | `test-author` |

### Sprint M1.S5 — Integration test corpus

| Field | Value |
|---|---|
| **Task** | Author `tests/integration/` |
| **Description** | Encode the five §16.2 scenarios as end-to-end tests that run `infracore/app.py` against a temporary `<edivi-root>`: clean startup with the three built-in plugins; broken-plugin tolerance; pre-seeded `state.json` enabling Image Cropping at launch; unrecognized `layout.json` version (S7) falling back to first-run; built-in/third-party name collision (S6). Tests also assert the `integration-agent`'s runtime-visible invariants (§13.1) where they manifest at runtime. |
| **DoD** | Five test files (one per §16.2 scenario, or grouped logically) present and red. Temporary `<edivi-root>` fixtures are reusable. Tests are skip-marked or quarantined so M1's "everything red" status remains coherent — they may not pass until M5. |
| **Skills** | `test-author` (consulting `integration-agent` for §13.1 alignment) |
| **Agent** | `test-author` |

---

## Milestone M2 — Infracore delivered and accepted (7 sprints)

**Acceptance gate (§19.2):** all tests under `tests/infracore/` and `tests/contracts/` pass. Components and contracts conform to §3, §4, §10. Static checks (§13.1) green. The application boots to step §9.8 (UI shell construction) with zero services and zero plugins discovered, and shuts down cleanly. No service or plugin code is written.

Sprint cadence (§19.6): one per component (6) + one combined for lifecycle/excepthook/UI shell. Contracts modules are written alongside the component that requires them so the component's tests can pass; this is consistent with G5 (contracts are type-only) because the contracts work is shape-only. By sprint M2.S6 the contracts package is fully populated.

Executing agent: `infracore-builder` (§19.4.2). G3 line-count budget (≤ 3× the corresponding test code) is enforced per PR; `code-critic` advises; `integration-agent` gates.

### Sprint M2.S1 — `SignalComponent` + `contracts.signals`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/bootstrap_components/signal_component/` (`signal.py`, `handle.py`) and the matching `contracts/src/contracts/signals.py` (`Signal[T]`, `SubscriptionHandle` mirror per S3). |
| **Description** | Typed signal mechanism per §4.2. `SubscriptionHandle` is `NewType[uuid.UUID]` and is structurally mirrored across both layers (§3.3). No polling anywhere (G7). |
| **DoD** | `tests/infracore/test_signal_component.py` and the relevant subset of `tests/contracts/` pass. Mirror invariant verified by `integration-agent` (§13.1, G10). Line-count ratio within budget. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder` (build); `integration-agent` (gate); `code-critic` (advise) |

### Sprint M2.S2 — `FilesystemComponent` + `contracts.filesystem`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/bootstrap_components/filesystem_component/filesystem.py` and `contracts/src/contracts/filesystem.py` (`FilesystemService` Protocol, `FilesystemEvent`). |
| **Description** | The single point of egress for filesystem writes (§4.3, G6). Per-path serialization underpins atomicity used later by `ProjectService.update_metadata` (§5.8, S13). Emits `FilesystemEvent` signals on writes. |
| **DoD** | `tests/infracore/test_filesystem_component.py` passes. Component depends on `SignalComponent` (built in S1) using a real instance per §16.1. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

### Sprint M2.S3 — `AppStateComponent` + `contracts.state`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/bootstrap_components/app_state_component/app_state.py` and `contracts/src/contracts/state.py`. |
| **Description** | Key-value app-state store per §4.4 with the 50 ms warning window (S12) and the namespaced `plugins.<name>.enabled` keys (S10). Persists via `FilesystemComponent`. |
| **DoD** | `tests/infracore/test_app_state_component.py` passes. The 50 ms warning window is asserted by parametrized tests; the warning surfaces via the alert channel. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

### Sprint M2.S4 — `PluginRegistryComponent` + `contracts.plugin_registry` + `contracts.manifest`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/bootstrap_components/plugin_registry_component/plugin_registry.py`, the authoritative `infracore/manifest/plugin_manifest.py`, and the mirrored `contracts/src/contracts/plugin_registry.py` and `contracts/src/contracts/manifest.py` (including `RequiredService` per the v1.1 changelog). |
| **Description** | Registry per §4.5 with `PluginRecord`. Strict manifest schemas (§5.1, §6.1, G9): unknown fields, missing required fields, malformed JSON all reject. Built-in vs third-party collision policy per S6. |
| **DoD** | `tests/infracore/test_plugin_registry_component.py` passes; manifest mirror invariant green (G10). Strict-rejection cases covered. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

### Sprint M2.S5 — `LoggingComponent` + `contracts.logging`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/bootstrap_components/logging_component/logging.py` and `contracts/src/contracts/logging.py`. |
| **Description** | Dual-channel logging per §4.6 (PRD D4): bootstrap log + per-plugin log under `<edivi-root>/logs/plugins/<name>/` (S8). Alert severities per D9. The stdlib `logging` exception to G6 is documented in code comments. |
| **DoD** | `tests/infracore/test_logging_component.py` passes. Per-plugin log paths created lazily and only on first write. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

### Sprint M2.S6 — `InjectorComponent` + `contracts.injector` + remaining contracts

| Field | Value |
|---|---|
| **Task** | Implement `infracore/injector_component/injector.py` and finalize the remaining contracts modules: `contracts/src/contracts/injector.py` (S2, S17 — `Injector` Protocol with the single `resolve` method), `contracts.project`, `contracts.image`, `contracts.subtitle`, `contracts.exceptions`. Also `contracts/pyproject.toml` per §3.5 / S16. |
| **Description** | Wires the other components; structurally distinct per §1. Caret-semver helpers (§3.4 / S4) live in `infracore/version_check.py`. After this sprint the contracts package is complete and locally installable per S16; M3 services can begin against it. Cycle detection per S5 / §4.7 / §9.6. |
| **DoD** | All `tests/contracts/` tests pass. `tests/infracore/test_injector_component.py` passes. Contracts package installs locally; `__component_version__` constants (§4.1, S9) consumed correctly. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

### Sprint M2.S7 — Lifecycle, excepthook, UI shell, `app.py`

| Field | Value |
|---|---|
| **Task** | Implement `infracore/lifecycle/hooks.py`, `infracore/lifecycle/excepthook.py`, the UI shell under `infracore/ui_shell/` (`window.py`, `docker_menu.py`, `alert_panel.py`), and the bootstrap entry point `infracore/app.py`. |
| **Description** | Lifecycle hook orchestration per §6.2; `sys.excepthook` wrapping per §9.5 / S11. UI shell per §7: window, menu bar with `description` tooltip (S15), status bar with click-to-acknowledge alerts (S14, with `author` in the detail per S15), layout persistence with version-mismatch fallback (§7.4 / S7), first-run experience (§7.5). `app.py` implements steps §9.1–§9.13 sufficient to boot to §9.8 with zero services and zero plugins, then shut down cleanly. |
| **DoD** | All remaining `tests/infracore/` tests pass. Manual `python -m infracore.app` against a fresh tempdir boots to UI-shell-visible and exits cleanly. M2 acceptance gate met: zero services, zero plugins, healthy startup and shutdown. |
| **Skills** | `infracore-builder` |
| **Agents** | `infracore-builder`; `integration-agent`; `code-critic` |

---

## Milestone M3 — Service layer delivered and accepted (9 sprints)

**Acceptance gate (§19.2):** all tests under `tests/services/` pass; M2 tests stay green (regression floor per §19.3). Nine services present and registered through `InjectorComponent`. Boot reaches §9.8 with the injector reporting nine constructed services. No plugin code is written.

One sprint per service (§19.6). Executing agent: `service-builder` (§19.4.3), parameterized per service. Each service-builder instance receives only the §5 subsection for its target, the target's test file, and the contracts modules it implements — no infracore source, no other service source. Order below puts expression services first (they have minimal external deps) and domain services last (they pull in Pillow etc. and are exercised by the integration smoke tests defined in M1.S3).

### Sprint M3.S1 — `injector_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/injector_service/` (`manifest.json`, `service.py`). |
| **Description** | Expression service for `InjectorComponent` per §5.7, exposing the `Injector` Protocol with the single `resolve` method (S2, S17). Manifest declares `service_api_version` and the component dependency. |
| **DoD** | `tests/services/test_injector_service.py` passes. Manifest validates strictly. M2 regression floor stays green. |
| **Skills** | `service-builder` (parameterized: target = `injector_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S2 — `signal_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/signal_service/`. |
| **Description** | Expression service for `SignalComponent` per §5.2 (PRD D1, D2). |
| **DoD** | `tests/services/test_signal_service.py` passes. M2 floor green. |
| **Skills** | `service-builder` (target = `signal_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S3 — `app_state_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/app_state_service/`. |
| **Description** | Expression service for `AppStateComponent` per §5.3 (PRD D5). Exposes the `plugins.<name>.enabled` namespace per S10. |
| **DoD** | `tests/services/test_app_state_service.py` passes. |
| **Skills** | `service-builder` (target = `app_state_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S4 — `filesystem_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/filesystem_service/`. |
| **Description** | Expression service for `FilesystemComponent` per §5.4. Plugins write through this — G6 single-egress is preserved end-to-end. |
| **DoD** | `tests/services/test_filesystem_service.py` passes. |
| **Skills** | `service-builder` (target = `filesystem_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S5 — `plugin_registry_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/plugin_registry_service/`. |
| **Description** | Expression service for `PluginRegistryComponent` per §5.5 (PRD D3). Exposes registry enumeration to plugins. |
| **DoD** | `tests/services/test_plugin_registry_service.py` passes. |
| **Skills** | `service-builder` (target = `plugin_registry_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S6 — `logging_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/logging_service/`. |
| **Description** | Expression service for `LoggingComponent` per §5.6 (PRD D4, D9). Routes plugin log calls into per-plugin log files (S8). |
| **DoD** | `tests/services/test_logging_service.py` passes. |
| **Skills** | `service-builder` (target = `logging_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S7 — `project_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/project_service/`. |
| **Description** | Domain service per §5.8 (PRD D6). `update_metadata` atomicity is provided by `FilesystemComponent`'s per-path serialization (S13) — `ProjectService` does not reimplement it. Required dependencies declared in `pyproject.toml` extras (§14). |
| **DoD** | `tests/services/test_project_service.py` passes; the integration smoke test in this file (per §16.1) exercises real filesystem writes via the component. |
| **Skills** | `service-builder` (target = `project_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S8 — `image_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/image_service/`. |
| **Description** | Domain service per §5.9 (PRD D7). Uses Pillow; declared via extras in `services/image_service/pyproject.toml` per §14. PNG/JPEG only for v1 (§17). |
| **DoD** | `tests/services/test_image_service.py` passes; the per-service Pillow smoke test passes. |
| **Skills** | `service-builder` (target = `image_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

### Sprint M3.S9 — `subtitle_service`

| Field | Value |
|---|---|
| **Task** | Implement `services/subtitle_service/`. |
| **Description** | Domain service per §5.10 (PRD D8). SRT only for v1 (§17). `text_to_srt` with optional pacing controls. |
| **DoD** | `tests/services/test_subtitle_service.py` passes. M3 acceptance gate met: nine services constructed, boot reaches §9.8 with injector reporting nine. |
| **Skills** | `service-builder` (target = `subtitle_service`) |
| **Agents** | `service-builder`; `integration-agent`; `code-critic` |

---

## Milestone M4 — Plugins delivered and accepted (3 sprints)

**Acceptance gate (§19.2):** all tests under `tests/plugins/` pass; M2 and M3 stay green. The three v1 plugins are present, manifests validate, lifecycle hooks complete without exceptions on a clean fixture.

One sprint per plugin (§19.6). Executing agent: `plugin-builder` (§19.4.4), parameterized per plugin. The plugin-builder may import only `contracts.*` and `PySide6.*` — the integration agent rejects any other import (G4 enforced by §19.4.4 addendum). Plugin order below builds the simplest UI first (Project Launcher) and the most service-coupled last (Image Cropping).

### Sprint M4.S1 — `project_launcher`

| Field | Value |
|---|---|
| **Task** | Implement `plugins/project_launcher/` (`manifest.json`, `plugin.py`). |
| **Description** | Per §6.5. Required services: `project_service`, `filesystem_service`, `logging_service`. UI: folder picker + confirmation button. On commit, calls `ProjectService.set_current(folder)`. Auto-enabled on first run (PRD §7.5; lifecycle keys this on the plugin name). |
| **DoD** | `tests/plugins/test_project_launcher.py` passes. Manifest validates. Lifecycle hooks complete without exceptions on a clean fixture. M2 + M3 floors green. |
| **Skills** | `plugin-builder` (target = `project_launcher`) |
| **Agents** | `plugin-builder`; `integration-agent`; `code-critic` |

### Sprint M4.S2 — `subtitle_text_tool`

| Field | Value |
|---|---|
| **Task** | Implement `plugins/subtitle_text_tool/`. |
| **Description** | Per §6.5. Required services: `subtitle_service`, `filesystem_service`, `project_service`, `logging_service`. UI: text input, optional SRT pacing controls, destination picker, commit button. On commit, calls `SubtitleService.text_to_srt`. |
| **DoD** | `tests/plugins/test_subtitle_text_tool.py` passes. Manifest validates. Lifecycle clean on fixture. |
| **Skills** | `plugin-builder` (target = `subtitle_text_tool`) |
| **Agents** | `plugin-builder`; `integration-agent`; `code-critic` |

### Sprint M4.S3 — `image_cropping`

| Field | Value |
|---|---|
| **Task** | Implement `plugins/image_cropping/`. |
| **Description** | Per §6.5. Required services: `image_service`, `filesystem_service`, `project_service`, `logging_service`. UI: image picker, crop/resize controls (Qt-rendered preview computed inside the plugin — no Pillow import), commit button. On commit, calls `ImageService.apply_crop` or `ImageService.resize`. |
| **DoD** | `tests/plugins/test_image_cropping.py` passes. Manifest validates. Lifecycle clean on fixture. M4 acceptance gate met. |
| **Skills** | `plugin-builder` (target = `image_cropping`) |
| **Agents** | `plugin-builder`; `integration-agent`; `code-critic` |

---

## Milestone M5 — Integration validated (2 sprints)

**Acceptance gate (§19.2):** all `tests/integration/` tests pass — the §16.2 scenarios exhaustively. PyInstaller build (§14) produces a runnable `.exe` passing the manual smoke checklist derived from PRD §2.3. Full §13.1 check matrix green.

Sprint cadence (§19.6): integration scenarios + release build.

### Sprint M5.S1 — Integration scenarios green

| Field | Value |
|---|---|
| **Task** | Bring `tests/integration/` from red to green. |
| **Description** | Un-quarantine the §16.2 scenario tests authored in M1.S5 and make them pass against the assembled system: clean startup with the three built-in plugins (Project Launcher enabled, others loaded but not enabled); broken-plugin tolerance (broken plugin appears under the alert icon, app otherwise healthy — PRD §2.3 third success criterion); pre-seeded `state.json` enabling Image Cropping at launch; unrecognized `layout.json` version → first-run fallback with `WARNING` log (S7); built-in/third-party name collision (built-in `enabled`, third-party `failed` — S6). Any defects surface and are fixed in the appropriate layer; per G2 such fixes may not regress any earlier-floor test. The first-run precedence between `layout.json` absence and persisted plugin-enabled state (§9.11, v1.1 changelog item) is exercised. |
| **DoD** | All five §16.2 scenarios green. Full integration-agent §13.1 check matrix green. M2, M3, M4 floors all green (full regression suite). |
| **Skills** | `infracore-builder` and/or `service-builder` and/or `plugin-builder` (whichever layer the defect lives in — gated by `integration-agent`'s assignment of the failure to a layer) |
| **Agents** | Layer-appropriate builder; `integration-agent` (gate); `code-critic` (advise) |

### Sprint M5.S2 — Release build

| Field | Value |
|---|---|
| **Task** | Produce the PyInstaller `.exe` per §14 and execute the manual smoke checklist. |
| **Description** | Build configuration per §14.1; runtime path resolution per §14.2 confirmed against the packaged binary. Per-service `pyproject.toml` extras (§14) drive the bundled dependency set. Manual smoke checklist derived from PRD §2.3 success criteria is executed against the produced `.exe`. |
| **DoD** | `.exe` runs on a clean Windows host. Manual smoke checklist passes. Full integration-agent §13.1 matrix green on the source tree the build was produced from. M5 acceptance gate met → v1 ready. |
| **Skills** | `release-engineer` |
| **Agent** | `release-engineer` (with `integration-agent` providing the final source-tree verdict) |

---

## Cross-cutting agents (active across multiple milestones)

| Agent | Active in | Role |
|---|---|---|
| `integration-agent` (§19.4.5) | M2–M5 (gating) | Static enforcement of §13.1: layer rules (G4), manifest schemas (G9), mirror invariants (G10), dependency naming, line-count discipline (§19.4.2). No write access. Its verdict is the milestone gate. |
| `code-critic` (§19.4.6) | M2–M5 (advisory) | Reviews PRs for G3 (less code, more quality). Flags duplication, indirection without rent, verbose patterns. Outputs a simpler diff or "ratify". Read-only. |
| `test-author` (§19.4.1) | M1 (active); M2–M5 (consulted) | Authors tests in M1; consulted later when a sprint needs an additional regression test or clarifies an underspecified detail (in which case the agent files a spec-clarification request rather than guessing — §19.4.1 addendum). |

---

## Sprint count check

| Milestone | Sprints |
|---|---:|
| M1 | 5 |
| M2 | 7 |
| M3 | 9 |
| M4 | 3 |
| M5 | 2 |
| **Total** | **26** |

Matches the §19.6 cadence table exactly.
