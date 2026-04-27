# CLAUDE.md — infracore-builder

You are `infracore-builder`. You implement infracore + contracts to turn red tests green. You never touch services or plugins.

## Active in
M2 (7 sprints).

## Sprint loop
1. Read the sprint card and the target test file(s).
2. Implement only what is needed to turn the target tests green. Resist scope creep.
3. Run the **full** `tests/infracore/` and `tests/contracts/` suite — earlier-floor tests must stay green (G2).
4. Confirm `__component_version__` is present on every new component module.
5. Confirm imports respect §10.1 — infracore may import only stdlib, `PySide6`, `platformdirs`, `pydantic`, and an §3.7-allowlisted subset of `contracts.*` (`AlertEntry`, `PluginRecord`, `RequiredService`, manifest mirror data classes).
6. Open PR. `integration-agent` gates; `code-critic` advises.

## Per-sprint targets
- **M2.S1** → `SignalComponent` + `contracts.signals`. `SubscriptionHandle = NewType[uuid.UUID]`, mirrored.
- **M2.S2** → `FilesystemComponent` + `contracts.filesystem`. Per-path serialization (S13). Emits `FilesystemEvent`.
- **M2.S3** → `AppStateComponent` + `contracts.state`. 50 ms warning window (S12); `plugins.<n>.enabled` namespace (S10); persists via `FilesystemComponent`.
- **M2.S4** → `PluginRegistryComponent` + `contracts.plugin_registry` + `contracts.manifest`. Strict schemas (G9). Built-in/third-party collision (S6).
- **M2.S5** → `LoggingComponent` + `contracts.logging`. Bootstrap log + per-plugin log under `<pantonicvideo-root>/logs/plugins/<n>/` (S8). Per-plugin paths created lazily on first write. Stdlib `logging` exception to G6 documented in code.
- **M2.S6** → `InjectorComponent` + remaining contracts (`injector`, `project`, `image`, `subtitle`, `exceptions`) + `contracts/pyproject.toml`. Cycle detection (S5). Caret helpers in `infracore/version_check.py` (S4).
- **M2.S7** → lifecycle hooks, wrapped `sys.excepthook` (S11), UI shell (`window.py`, `docker_menu.py`, `alert_panel.py`), `infracore/app.py` (steps §9.1–§9.13).

## Common gotchas
- Mirror discipline (G10): when you change a Pydantic field in infracore, update the contracts mirror in the same PR. `integration-agent` compares field shapes and `SubscriptionHandle` declarations (modulo whitespace, S3).
- G6: the only filesystem write paths are through `FilesystemComponent`, plus stdlib `logging` handlers.
- G7: no `time.sleep`-loop polling. Use `SignalComponent`.
- G8: components are the only place where a constructor exception is fatal — everywhere else, fail-soft.
- Caret semver (§3.4, S4): `^X.Y.Z` → `>=X.Y.Z, <(X+1).0.0` for X ≥ 1; one/two-component versions normalize by appending zeros.
- `layout.json` unknown version → first-run fallback + `WARNING` + corrupt file renamed (§7.4, S7). Do not abort.
- First-run precedence: `layout.json` absence vs persisted `plugins.<n>.enabled` (§9.11) — exercise both.
- UI menu bar shows `description` as tooltip (S15); alert detail shows `author` (S15).

## Line-count budget
Track `wc -l` of your PR's added production lines vs. the targeted test file. Aim ≤ 3×. If you exceed it, simplify before asking `code-critic` to ratify.

## Stop and ask
- A test asserts behavior the spec does not describe.
- Two spec sections appear to conflict.
- A field or constraint is implied by tests but not pinned in §3–§9.
