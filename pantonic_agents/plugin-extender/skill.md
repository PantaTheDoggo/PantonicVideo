# Skill: plugin-extender

**Authoritative reference:** `project_artifacts/as-is.md` is the single source of truth for the application state, architecture, catalog, and rules. Consult it before implementing. At the end of every sprint, update it to reflect the new state.

**Rules:** see `rules.md` (G1–G10 apply verbatim).

## Pre-Sprint: Handoff Check

**Before any implementation, read `project_artifacts/handoff.md`.**
1. For each **open** item, decide: does it fall within this role and the current sprint?
2. If yes and a spec exists in `project_artifacts/history/`: include the item in this sprint.
3. If yes but no spec exists: **stop — all development requires a spec first.** Request one before proceeding.
4. If no: leave the item open and continue.

**Spec lifecycle rule:**  
Every development task requires a spec under `project_artifacts/history/<spec_name>.md` before coding starts.  
Specs in progress stay in `project_artifacts/history/`. When the sprint is complete, move the spec to `project_artifacts/history/done/` and mark the item **done** in `handoff.md`.

---

## Guardrails (verbatim from spec.md §19.1)
- G1. Test-Driven Development is mandatory.
- G2. Regression containment.
- G3. Less code, more quality.
- G4. Layer-direction rule (§10.1) is invariant.
- G5. The contracts package is type-only.
- G6. Single point of egress for filesystem writes.
- G7. Signals are the only observation idiom.
- G8. Failure containment over abort.
- G9. Strict manifests.
- G10. Mirror discipline.

## Purpose
Extend `plugins/` post-v1: add behavior to one of the three v1 plugins, or create a new built-in plugin — always behind a new failing test, never weakening the M4 floor. Import allowlist is `contracts.*` and `PySide6.*` only.

## Context (read access)
- Embedded in `pantonic_agents/plugin-extender/claude.md`: plugins inventory, plugin manifest schema, lifecycle hook order, failure containment, M4 floor test list, common gotchas.
- **Fallback 1:** `plugins/`, `contracts/`, `tests/plugins/` source. Read `services/<svc>/manifest.json` and the corresponding `contracts/<svc>.py` Protocol when you need a service's surface — never read `services/<svc>/service.py`.
- **Fallback 2:** `project_artifacts/spec_v2.md` §3, §6, §7 (UI conventions), §10, §11, §17, §19.1.

## Tool access
- **Write:** `plugins/<target>/` (entire folder for a new plugin), and **new** test files under `tests/plugins/`.
- **Read:** `plugins/`, `contracts/`, `tests/plugins/`; `services/<svc>/manifest.json` (not source); `infracore/`, `tests/integration/`, `spec_v2.md` for fallback only.
- **No-go:** modifying `infracore/`, `services/`, `contracts/` source; modifying any pre-existing test in `tests/plugins/` (locked floor); importing anything outside `contracts.*` and `PySide6.*` from plugin code.

## Inputs
- An extension demand (e.g., "add SRT preview to `subtitle_text_tool`", "add an aspect-ratio lock to `image_cropping`", "add a new `audio_trimmer` built-in plugin requiring a future `audio_service`").
- The current state of `plugins/`, `contracts/`, and the test corpus.

## Outputs
- A new failing-then-green test under `tests/plugins/test_<target>.py` (services mocked via `MagicMock`; UI driven by `pytest-qt`; lifecycle order asserted).
- New or updated `plugins/<target>/manifest.json` (strict, G9; all four lifecycle hooks accounted for).
- New or updated `plugins/<target>/plugin.py` and `__init__.py`.
- A short PR-description note if a service or contract change is required (route to `service-extender` first, then return to plug into the new surface).

## Acceptance
- New test goes red → green.
- `tests/plugins/` + M2 + M3 floors (`tests/infracore/`, `tests/contracts/`, `tests/services/`) green (G2).
- `tests/integration/` green — the five §16.2 scenarios still pass.
- Manifest validates strictly (G9): `name`, `version`, `contracts_min_version`, `author`, `description`, fully-qualified `entry_point`, `required_services` (each with `min_version`), `inputs`, `outputs`, `permissions` (lists, possibly empty).
- Lifecycle hooks (`on_load`, `on_enable`, `on_disable`, `on_unload`) all present and complete without exception on a clean fixture.
- Imports respect §10.1 strictly: **only** `contracts.*` and `PySide6.*` in `plugin.py`. Any other import (`os`, `pathlib`, `json`, `requests`, even type-only) is rejected by `integration-agent`.
- `description` is meaningful (it appears as the Docker-menu tooltip, S15); `author` is set (it appears in the alert detail, S15).
- G3 line-count budget honored (target ≤ 3× the new test code's line count).

## Refusals
- Do not modify `infracore/`, `services/`, or `contracts/` source. Route to the layer-appropriate extender.
- Do not modify pre-existing tests; only add new ones.
- Do not import anything outside `contracts.*` and `PySide6.*` from plugin code.
- Do not call another plugin (PRD §4.3 — promote to a service if needed).
- Do not bypass `filesystem_service` for I/O (G6).
- Do not poll (G7) — subscribe via `signal_service`.
- Do not handle the built-in/third-party name collision in plugin code (S6 — the registry handles it).
- If §6.<target>, the existing plugin code, and this skill are all silent on a UI control's behavior, **stop and file a clarification request** (Universal refusal trigger).
