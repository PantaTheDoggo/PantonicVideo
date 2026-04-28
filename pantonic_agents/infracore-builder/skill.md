# Skill: infracore-builder

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

## Purpose
Implement components and contracts to turn `tests/infracore/` and `tests/contracts/` from red to green.

## Context (read access)
- Spec: §1, §2, §3, §4, §9, §10, §11, §13, §19.1.
- Tests: `tests/infracore/`, `tests/contracts/`.

## Tool access
- **Write:** `infracore/`, `contracts/`.
- **Read:** `tests/infracore/`, `tests/contracts/`, listed spec sections.
- **No-go:** `services/`, `plugins/`, `tests/services/`, `tests/plugins/`, `tests/integration/`.

## Inputs
- The sprint card (M2.S1–M2.S7) and the test files it points at.

## Outputs
- Component modules under `infracore/bootstrap_components/<n>/`.
- The injector under `infracore/injector_component/`.
- The lifecycle, excepthook, UI shell, and `app.py` (M2.S7).
- Mirrored `contracts/src/contracts/*.py` modules + `contracts/pyproject.toml` (M2.S6).
- Each component module declares `__component_version__` (§4.1, §13.1).

## Acceptance
- Target tests in `tests/infracore/` and `tests/contracts/` pass.
- All previously-green tests stay green (G2).
- §13.1 checks green: layer rules, manifest schemas, mirror invariants, `__component_version__` present.
- G3 line-count budget: ≤ 3× the corresponding test code's line count. Exceeding triggers a warning; `code-critic` adjudicates.
- M2 acceptance gate (M2.S7 end): `python -m infracore.app` boots to §9.8 with zero services/plugins and shuts down cleanly.

## Refusals
- Do not write services or plugins or their tests.
- Do not import from `services.*` or `plugins.*` (G4 — `integration-agent` veto).
- Do not introduce behavior into `contracts/*` (G5).
- If a test underspecifies behavior, file a spec-clarification request.
