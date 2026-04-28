# PantonicVideo — Sprint Plan v2

**Source:** [spec_v3.md](spec_v3.md) (consolidated v1 + post-v1 extensions).
**Goal:** rebuild the project from scratch, applying the lessons learned during the v1 + Sprint 1/2 cycle.
**Total sprints:** 28 — S0 (governance + setup) + M1 (5) + M2 (7) + M3 (9) + M4 (4) + M5 (2).
**Universal sprint exit (rules.md):** target tests red → green; `integration-agent` stays green; `code-critic` ratifies. Milestone gates are binary.

---

## 1. Governance

**Decision:** v2 replaces the dual-location layout (`project_artifacts/{as-is.md, handoff.md, history/{done, *.md}}`) with a single `governance/` folder. One place for live state, one place for in-flight specs, one place for closed specs.

### 1.1 Folder layout (created by S0)

```
governance/
├── as-is.md                    # living source of truth — every agent reads this first
├── handoff.md                  # cross-sprint open items (the old "handoff.md" preserved)
├── rules.md                    # G1–G10 (mirrored from project root for proximity)
├── spec_v3.md                  # the authoritative architecture spec
├── sprint_plan_v2.md           # this file
├── work_in_progress/           # specs of sprints currently active
│   └── <spec_name>.md
└── done/                       # specs of closed sprints
    └── <spec_name>.md
```

### 1.2 Spec lifecycle (replaces the v1 ad-hoc flow)

| Phase | Action |
|---|---|
| Sprint planning | Author `governance/work_in_progress/<spec_name>.md` **before** any code or test is written. Append an OPEN entry to `governance/handoff.md`. |
| Sprint open | All agents read `governance/as-is.md` + the spec under `work_in_progress/`. |
| Sprint close | Move spec to `governance/done/`. Mark the handoff item DONE. **Update `governance/as-is.md`** (mandatory — sprint is not closed until as-is reflects the new state). |
| New cross-sprint dependency discovered mid-sprint | Append OPEN entry to `governance/handoff.md` before stopping. |

### 1.3 Universal pre-sprint checklist (every agent)

1. Read `governance/as-is.md` (primary truth).
2. Read `governance/rules.md` (G1–G10).
3. Read the sprint's spec from `governance/work_in_progress/`.
4. Read `governance/handoff.md`. For each OPEN item: in scope → resolve; out of scope → leave; in scope but no spec → **stop and request a spec** (universal refusal).

### 1.4 Refusal trigger (universal)

If the spec underspecifies a detail you would otherwise invent → stop and file a spec-clarification request under `governance/work_in_progress/`. Do not guess. (rules.md)

---

## 2. Lessons learned (encoded into the plan below)

| # | Lesson from v1 cycle | How v2 absorbs it |
|---|---|---|
| L1 | `filesystem_service` shipped at `1.0.0` and was extended to `1.1.0` mid-cycle to add `rename/move/copy` for `project_folder`. | M2.S2 + M3.S4 ship the v1.1 surface from day one. |
| L2 | `project_launcher` shipped with `on_enable: pass` (no UI), and was extended later to open `QFileDialog` and write `current_project` to app state. | M4.S1 ships the complete v1.1 surface from day one (4 services, real dialog, app-state write, re-entrancy guard). |
| L3 | `project_folder` was a post-v1 add. | Promoted to v1 plugin: M4 has **4 sprints**, one per plugin. |
| L4 | `pyinstaller.spec` had to be updated separately when `project_folder` arrived (still pending as Sprint D). | Each M4 sprint includes the `pyinstaller.spec` bundle update as part of its DoD. |
| L5 | `project_folder` publishes `state_set("open_file_request", path)` with no consumer; the signal is silently dropped. | Pub/sub gate added: any sprint that introduces a state-key publisher must either ship the consumer in the same milestone **or** open a tracked governance item before merging. M4.S2 opens the governance item for `open_file_request` (consumer is post-v1). |
| L6 | `project_launcher.on_enable` needed a re-entrancy guard (`_dialog_active`) because Docker-menu toggles can fire while the modal is open. | Pattern documented in `governance/as-is.md` §"Plugin patterns"; M4 plugins that open modal dialogs implement it from the first commit. |
| L7 | `as-is.md` and `handoff.md` lived in `project_artifacts/`; closed specs in `project_artifacts/history/done/`; open specs scattered. | New `governance/` layout (§1.1). |
| L8 | The `code-critic` G3 line-count budget surfaced as a warning only after the PR existed. | M2.S1+ enforce the ≤ 3× test-line budget at PR open time, not at review time. The `integration-agent`'s output template now blocks PRs that exceed the ratio without explicit human override. |

---

## 3. Sprint S0 — Setup & governance bootstrap

| Field | Value |
|---|---|
| **Task** | Bootstrap the repo: create `governance/` per §1.1, drop in `rules.md`, `spec_v3.md`, this file, an empty `handoff.md`, an initial `as-is.md`. Initialize `pyproject.toml`, `pyinstaller.spec` skeleton (empty bundle list), `tests/` skeleton folders, and the `pantonic_agents/` skill files (one per agent in §6). Configure `pytest` + `pytest-qt` + `uv` env. |
| **Description** | No production code, no tests yet. The `as-is.md` opens with: "Empty repo. M1 not yet started. 0 tests." Skill files reproduce verbatim G1–G10 + agent-specific addenda from spec §16/agent roles. |
| **DoD** | `governance/` populated; `pytest` collects 0 tests successfully; `uv sync` succeeds; `python -c "import infracore"` fails with `ModuleNotFoundError` (expected — no source yet). All nine skill files exist under `pantonic_agents/<agent>/skill.md`. |
| **Agent** | human + `code-critic` (advisory) |

---

## 4. Milestone M1 — Functional-test corpus (5 sprints)

**Acceptance gate (spec §M1):** complete suite under `tests/` exists, runs, and is **all red**. Test shape reflects per-layer discipline (spec §15). Active agent: `test-author`. Each test docstring names the spec_v3 section it derives from.

### M1.S1 — `tests/infracore/` (red)
Cover all six components (spec §4), lifecycle (spec §6.2), wrapped excepthook (spec §8.5), UI shell (spec §7). Real component instances — no mocks inside infracore. Failure-mode parametrizations cover spec §11.

### M1.S2 — `tests/contracts/` (red)
Pydantic schema accept/reject per spec §3, mirror invariants of §3.2 (`SubscriptionHandle` parity + `PluginManifest` parity), caret-semver normalization (spec §3.3), exception classes.

### M1.S3 — `tests/services/` (red)
Nine test files. Expression services with mocked components, domain services with mocked services. **filesystem_service tests cover the v1.1 surface (`rename`, `move`, `copy`) from the start (L1).** Stubs for Pillow / SRT under `tests/services/conftest.py`. One real-library smoke per domain service.

### M1.S4 — `tests/plugins/` (red)
**Four** test files (one per plugin per spec §6.4): `project_launcher`, `project_folder`, `image_cropping`, `subtitle_text_tool`. Plugins tested with mocked services; UI exercised via `pytest-qt`. `project_launcher` tests cover the v1.1 behaviors (`QFileDialog` opens, `state_set("current_project", folder)`, re-entrancy guard) from the first commit (L2, L6). `project_folder` tests cover the 23 cases listed in the spec_project_folder_v1.0 (manifest, lifecycle, reactivity, navigation, file ops, G8 alert capture).

### M1.S5 — `tests/integration/` (red, quarantined)
Encode the five §15 scenarios. Tests are skip-marked until M5 so M1's "everything red" coherence holds. Temp `<pantonicvideo-root>` fixtures reusable.

---

## 5. Milestone M2 — Infracore + contracts (7 sprints)

**Acceptance gate:** `tests/infracore/` + `tests/contracts/` green. Boot reaches spec §8.8 with zero services and zero plugins; clean shutdown. M1 floor stays red (still no production for services/plugins).

Active agent: `infracore-builder`. Gating: `integration-agent`. Advisory: `code-critic`. **G3 budget (≤ 3× test lines) enforced at PR-open time (L8).**

### M2.S1 — SignalComponent + `contracts.signals`
Implements `infracore/.../signal_component/{signal.py, handle.py}` and `contracts/src/contracts/signals.py`. `SubscriptionHandle = NewType[uuid.UUID]` mirrored verbatim (G10). `__component_version__ = "1.0.0"`.

### M2.S2 — FilesystemComponent + `contracts.filesystem`
Implements the v1.1 surface from day one (L1): `read_file/write_file/list_dir/exists/delete/make_dir/watch/unwatch/**rename/move/copy**`. Per-path locking, `QFileSystemWatcher` watch backend, `FilesystemEvent` model. `__component_version__ = "1.1.0"` (drives the `service_api_version` of `filesystem_service` in M3.S4).

### M2.S3 — AppStateComponent + `contracts.state`
KV with write-through. `STATE_WRITE_WARNING_WINDOW_MS = 50` (S12). State-key namespace conventions documented (`current_project`, `open_file_request`, `plugins.<name>.enabled`, `project.path` — spec §4.3).

### M2.S4 — PluginRegistryComponent + `contracts.plugin_registry` + `contracts.manifest`
`PluginRecord`, `PluginStatus`, name-collision policy (S6). Authoritative `infracore/manifest/plugin_manifest.py` + mirror `contracts/manifest.py` with `RequiredService`. Strict schemas (G9).

### M2.S5 — LoggingComponent + `contracts.logging`
Dual-channel: rotating infracore log + per-plugin rotating logs (S8 path resolution by `is_builtin`). In-memory `AlertEntry` sink. `acknowledge` for click-through (S14). Stdlib-`logging`-bypass exception to G6 documented in code.

### M2.S6 — InjectorComponent + remaining contracts
`infracore/injector_component/injector.py` (topological sort, cycle rejection per S5). Finalize `contracts/{injector, project, image, subtitle, exceptions}.py`. `contracts/pyproject.toml` at version `1.0.0`. After this sprint the contracts package is complete and locally installable.

### M2.S7 — Lifecycle + excepthook + UI shell + `app.py`
`infracore/lifecycle/{hooks.py, excepthook.py}`, `infracore/ui_shell/{window.py, docker_menu.py, alert_panel.py}`, `infracore/app.py` implementing spec §8.1–§8.13. UI shell honors `description` tooltip (S15) and click-to-acknowledge alert detail with `author` (S15). First-run override for `project_launcher` (spec §8.11). `python -m infracore.app` boots to UI-visible against an empty tempdir and exits cleanly.

---

## 6. Milestone M3 — Services (9 sprints)

**Acceptance gate:** `tests/services/` green; M2 floor green. Boot reaches spec §8.8 with the injector reporting nine constructed services. No plugin code yet.

Active agent: `service-builder` (parameterized per service). Each instance sees only its target's spec subsection, its test file, and the contracts it implements. No infracore source. No other-service source.

### M3.S1 — `injector_service` (api `1.0.0`)
Single `resolve(name, min_version)` (S2/S17).

### M3.S2 — `signal_service` (api `1.0.0`)
Wraps SignalComponent.

### M3.S3 — `app_state_service` (api `1.0.0`)
Wraps AppStateComponent. Exposes `state_observe`/`state_unobserve` and the `plugins.<name>.enabled` namespace.

### M3.S4 — `filesystem_service` (api **`1.1.0`**)
Ships the v1.1 surface from day one (L1): `rename/move/copy` plus the v1.0 methods. `service_api_version = "1.1.0"` matches the wrapped component's `__component_version__` (integration-agent check 10).

### M3.S5 — `plugin_registry_service` (api `1.0.0`)
Wraps PluginRegistryComponent; `enable/disable` write `plugins.<name>.enabled` in app state and call lifecycle hooks (S10).

### M3.S6 — `logging_service` (api `1.0.0`)
Routes plugin log calls into per-plugin files (S8).

### M3.S7 — `project_service` (api `1.0.0`)
`set_current` loads/creates `pantonicvideo-project.json`; `update_metadata` is atomic via per-path lock in FilesystemComponent (S13). Real-FS smoke test included.

### M3.S8 — `image_service` (api `1.0.0`)
Pillow-backed; PNG/JPEG only. Pillow declared in `services/image_service/pyproject.toml` extras (G3 + spec §14).

### M3.S9 — `subtitle_service` (api `1.0.0`)
SRT-only; `text_to_srt` with `SrtOptions` defaults from spec §5.5.

**M3 acceptance:** boot reaches §8.8; injector reports nine services; M2 floor green.

---

## 7. Milestone M4 — Plugins (4 sprints)

**Acceptance gate:** `tests/plugins/` green; M2+M3 floors green. Four built-in plugins present, manifests validate, lifecycle hooks complete cleanly on a fresh fixture.

Active agent: `plugin-builder` (parameterized per plugin). Imports allowed: `contracts.*`, `PySide6.*`, plus `pathlib`/`typing` for annotations only (spec §6.1). **Every M4 sprint includes the `pyinstaller.spec` bundle update as part of its DoD (L4).**

### M4.S1 — `project_launcher` v1.1.0
- **Required services:** `project_service`, `filesystem_service`, `app_state_service`, `logging_service` (4 from day one, L2).
- **Behavior:** `on_enable` opens `QFileDialog.getExistingDirectory(None, "Open Folder", "", ShowDirsOnly | DontResolveSymlinks)` with re-entrancy guard `_dialog_active` (L6); on non-empty result calls `commit(Path(selected))`; cancel is no-op. `commit(folder)` calls **both** `project_service.set_current(folder)` **and** `app_state_service.state_set("current_project", folder)`.
- **Auto-enabled** on first run (spec §8.11).
- **DoD:** `tests/plugins/test_project_launcher.py` green; manifest validates; lifecycle clean; `pyinstaller.spec` includes `plugins/project_launcher/`.

### M4.S2 — `project_folder` v1.0.0
- **Required services:** `app_state_service`, `filesystem_service ≥ 1.1`, `signal_service`, `logging_service`.
- **Behavior:** `QListView` + `QStandardItemModel`; placeholder when `current_project` absent; `state_observe("current_project", _on_project_changed)`; `filesystem_service.watch(cwd, _on_fs_event)`; navigation via double-click/Enter/Backspace clamped at root; file open publishes `state_set("open_file_request", path)`; full keyboard + context-menu action set (F5/Backspace/Enter/Delete/F2/Ctrl+X/C/V/N/Shift+N) per spec §6.4. **G8:** every `filesystem_service.*` call inside a Qt slot wrapped in `try/except` → `logging_service.raise_alert("project_folder", LogLevel.ERROR, str(e))`. Plugin remains `enabled` on op failure.
- **Pub/sub gate (L5):** this sprint introduces the `open_file_request` publisher with no in-tree consumer. Before merge, append OPEN item `open_file_request consumer` to `governance/handoff.md` with status, owner, acceptance criteria. Out-of-scope for v1 release.
- **DoD:** `tests/plugins/test_project_folder.py` (23 tests) green; manifest validates; lifecycle clean; G8 wrapper verified by tests; `pyinstaller.spec` includes `plugins/project_folder/`; `governance/handoff.md` open item created.

### M4.S3 — `subtitle_text_tool` v1.0.0
- **Required services:** `subtitle_service`, `filesystem_service`, `project_service`, `logging_service`.
- **Behavior:** text input + optional SRT pacing controls + destination picker + commit; calls `SubtitleService.text_to_srt`.
- **DoD:** `tests/plugins/test_subtitle_text_tool.py` green; manifest validates; lifecycle clean; `pyinstaller.spec` includes `plugins/subtitle_text_tool/`.

### M4.S4 — `image_cropping` v1.0.0
- **Required services:** `image_service`, `filesystem_service`, `project_service`, `logging_service`.
- **Behavior:** image picker + Qt-rendered crop/resize preview computed inside the plugin (no Pillow import — G4) + commit; calls `ImageService.apply_crop` / `resize`.
- **DoD:** `tests/plugins/test_image_cropping.py` green; manifest validates; lifecycle clean; `pyinstaller.spec` includes `plugins/image_cropping/`. **M4 gate met:** four plugins, all green, all bundled.

---

## 8. Milestone M5 — Integration + release (2 sprints)

**Acceptance gate:** `tests/integration/` green (five spec §15 scenarios); PyInstaller `.exe` runs on a clean Windows host and passes the manual smoke checklist (PRD §2.3).

### M5.S1 — Integration scenarios green
Un-quarantine the §15 scenarios authored in M1.S5 and bring them green: clean startup with **all four** built-in plugins (`project_launcher` enabled; the other three loaded but not enabled); broken third-party plugin tolerance; `state.json`-seeded `plugins.image_cropping.enabled=True`; unrecognized `layout.json` version → first-run + WARNING (S7); built-in/third-party name collision (S6). First-run precedence between `layout.json` absence and persisted `plugins.<name>.enabled` (spec §8.11) is exercised. Defects trace back to the layer that owns them; fixes obey G2.

**DoD:** five scenarios green; full integration-agent §13 matrix green; M2+M3+M4 floors green.

### M5.S2 — Release build
PyInstaller one-file `.exe` with splash. Bundle includes `infracore/`, `contracts/`, all nine `services/`, all **four** built-in `plugins/`, and per-service `pyproject.toml` extras (Pillow). Runtime path resolution via `sys._MEIPASS` confirmed against the binary. Manual smoke checklist from PRD §2.3 executed against the produced `.exe`.

**DoD:** `dist/PantonicVideo.exe` runs on a clean Windows host; smoke checklist passes; full §13 matrix green; **M5 gate met → v1 ready**.

---

## 9. Cross-cutting agents

| Agent | Active | Role |
|---|---|---|
| `test-author` | M1 (active); M2–M5 (consulted) | Authors tests in M1; later, files spec-clarification requests under `governance/work_in_progress/` rather than guessing. |
| `infracore-builder` | M2 | Components + contracts. |
| `service-builder` | M3 | One service per sprint. |
| `plugin-builder` | M4 | One plugin per sprint. Bundles plugin into `pyinstaller.spec` as part of DoD (L4). |
| `integration-agent` | M2–M5 (gating) | Static enforcement of spec §13. **L8: enforces ≤ 3× test-line budget at PR-open time.** No write access. |
| `code-critic` | M2–M5 (advisory) | G3 review. Read-only. Outputs simpler diff or "ratify". |
| `release-engineer` | M5 | PyInstaller build + smoke checklist. |

Post-v1 extender variants (`infracore-extender`, `service-extender`, `plugin-extender`) are **not** instantiated for the rebuild — extensions only exist post-M5.

---

## 10. Sprint count

| Phase | Sprints |
|---|---:|
| S0 (governance + setup) | 1 |
| M1 (test corpus) | 5 |
| M2 (infracore + contracts) | 7 |
| M3 (services) | 9 |
| M4 (plugins) | 4 |
| M5 (integration + release) | 2 |
| **Total** | **28** |

(+2 vs v1's 26: S0 governance bootstrap + the 4th plugin in M4.)

---

## 11. Initial `governance/as-is.md` template

Created in S0; mutated at every sprint close:

```markdown
# PantonicVideo — As-Is

| Field | Value |
|---|---|
| Release | (none yet) |
| Test count | 0 green |
| Last sprint | S0 — governance bootstrap |
| Active sprint | M1.S1 |
| Open handoff items | (none) |

## Layers
(reference: governance/spec_v3.md)

## Plugin patterns (lessons)
- Modal dialog from on_enable → guard with `_dialog_active` flag (L6).
- Filesystem ops from Qt slots → wrap in try/except → `raise_alert` (G8).
- Publishing a state-key without an in-tree consumer → append OPEN handoff item before merge (L5).
- Adding a built-in plugin → update `pyinstaller.spec` in the same sprint (L4).
```

Subsequent sprints expand this to the full structure of the v1 `as-is.md` (architecture overview, source-tree map, component/service/plugin catalogs, startup sequence, test floors, integration-agent checks, layer rules, versioning, manifest schemas, user-data root, packaging, agent system, open items, out-of-scope).
