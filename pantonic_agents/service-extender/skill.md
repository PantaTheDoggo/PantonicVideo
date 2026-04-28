# Skill: service-extender

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
Extend `services/` and the `contracts/` Protocol surface post-v1: add a new service (expression, domain, auxiliary, simplifying), extend an existing service's contract with a caret-safe bump, or introduce a new contract module — always behind a new failing test, never weakening the M3 floor.

## Context (read access)
- Embedded in `pantonic_agents/service-extender/claude.md`: services inventory, contracts inventory, manifest schema, constructor-naming rule, M3 floor test list, common gotchas.
- **Fallback 1:** `services/`, `contracts/`, `tests/services/` source; `infracore/manifest/service_manifest.py`; `infracore/injector_component/injector.py`.
- **Fallback 2:** `project_artifacts/spec_v2.md` §3, §5, §10, §13, §14, §17, §19.1.

## Tool access
- **Write:** `services/<target>/` (for new services or extensions), `contracts/src/contracts/<new>.py` for new Protocol/model/enum modules (G5 — type-only), and **new** test files under `tests/services/`.
- **Read:** all of the above; `infracore/`, `tests/infracore/`, `plugins/`, `tests/plugins/`, `tests/integration/`, `spec_v2.md` for fallback only.
- **No-go:** modifying `infracore/` source; modifying `plugins/` source; modifying any pre-existing test in `tests/services/` (locked floor); importing one service from another inside service code.

## Inputs
- An extension demand (e.g., "add `.vtt` support to `subtitle_service`", "add a new `archive_service` that wraps `zipfile`", "add a new `metrics_service` auxiliary that captures duplicated timing code from plugins").
- The current state of `services/`, `contracts/`, and the test corpus.

## Outputs
- A new failing-then-green test under `tests/services/test_<target>.py` (mocked components for expression services; mocked services + stubbed external libs for domain services; one real-library smoke per domain service).
- New or updated `services/<target>/manifest.json` (strict, G9; constructor parameter names match `depends_on`, §13.1).
- New or updated `services/<target>/service.py` and `pyproject.toml` (external deps in extras, §14).
- New `contracts/src/contracts/<name>.py` if a new contract is introduced (Protocol + Pydantic models + enums only — G5).
- A short PR-description note if the change cascades to plugins (route to `plugin-extender` after caret-bump).

## Acceptance
- New test goes red → green.
- `tests/services/` + M2 floor (`tests/infracore/`, `tests/contracts/`) green (G2).
- `tests/plugins/` + `tests/integration/` green — or coordinated bump documented.
- Manifest validates strictly (G9): `service_api_version`, `implementation_version`, `depends_on`, fully-qualified entry-point class.
- Constructor parameter names equal `depends_on` names (§13.1).
- All external imports declared in the service's `pyproject.toml` extras. No `requirements.txt`, no hidden imports.
- §10.1 import rules respected: `services.<target>` may import `contracts.*`, `infracore.*` (components), and its declared extras. **Not** other services.
- For domain services: real-library smoke test green when the actual dep is installed.
- G3 line-count budget honored (target ≤ 3× the new test code's line count).

## Refusals
- Do not modify `infracore/` (route to `infracore-extender`).
- Do not modify `plugins/` (route to `plugin-extender`).
- Do not modify pre-existing tests; only add new ones.
- Do not introduce behavior into `contracts/*` (G5). Mirrors stay pure data classes / Protocol / enums / NewType.
- Do not import another service from a service (§10.1, §10.2 — injection only).
- Do not bypass `FilesystemService` for writes (G6).
- Do not introduce polling (G7).
- If §5.<target>, the existing code, and this skill are all silent on a signature or behavior, **stop and file a clarification request** (Universal refusal trigger).
