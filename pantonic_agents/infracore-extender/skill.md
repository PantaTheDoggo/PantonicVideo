# Skill: infracore-extender

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
Extend `infracore/` and `contracts/` post-v1: add behavior to an existing component, introduce a new bootstrap component, tighten a contract, or grow a mirror — always behind a new failing test, never weakening the M2 floor.

## Context (read access)
- Embedded in `pantonic_agents/infracore-extender/claude.md`: component inventory, contracts inventory, construction order, M2 floor test list, common gotchas.
- **Fallback 1:** `infracore/`, `contracts/`, `tests/infracore/`, `tests/contracts/` source.
- **Fallback 2:** `project_artifacts/spec_v2.md` §3, §4, §9, §10, §11, §13, §19.1.

## Tool access
- **Write:** `infracore/`, `contracts/`, **new** test files under `tests/infracore/` and `tests/contracts/`.
- **Read:** all of the above; `services/`, `plugins/`, downstream tests, and `spec_v2.md` for fallback only.
- **No-go:** modifying `services/`, `plugins/`, or any pre-existing M1/M2-authored test in `tests/infracore/` and `tests/contracts/` (the locked floor).

## Inputs
- An extension demand (e.g., "add a `state_keys()` method to `AppStateComponent`", "add a new `MetricsComponent`", "tighten `LoggingComponent` to truncate alert summaries at 500 chars").
- The current state of `infracore/`, `contracts/`, and the existing test corpus.

## Outputs
- A new failing-then-green test under `tests/infracore/` or `tests/contracts/`.
- The minimal `infracore/` and/or `contracts/` change that turns it green.
- Mirror update in `contracts/` if a mirrored shape changed (G10).
- `__component_version__` declared on any new component module (§4.1, S9).
- A short note in the PR description if a downstream caret-bump is required (route to `service-extender`).

## Acceptance
- New test goes red → green.
- Full `tests/infracore/` and `tests/contracts/` suites green (M2 floor preserved, G2).
- `tests/services/`, `tests/plugins/`, `tests/integration/` stay green — or coordinated bump is documented and routed.
- §13.1 invariants green: layer rules (§10.1 allowlist), manifest schemas, mirror invariants, `__component_version__`, `SubscriptionHandle` parity (modulo whitespace, S3).
- G3 line-count budget honored (target ≤ 3× the new test code's line count).

## Refusals
- Do not modify `services/` or `plugins/` source.
- Do not modify pre-existing tests; only add new ones.
- Do not introduce behavior into `contracts/*` (G5). Mirrors are pure data classes / `Protocol` / enums / `NewType`.
- Do not grow the §10.1 import allowlist (`infracore.*` may import only stdlib, `PySide6`, `platformdirs`, `pydantic`, and §3.7 contracts data models).
- Do not bypass `FilesystemComponent` for writes (G6).
- Do not introduce polling (G7).
- If the demand is silent in this skill, in the code, and in the spec, **stop and file a clarification request** (Universal refusal trigger).
