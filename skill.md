# Skill: test-author

**Authoritative reference:** `project_artifacts/as-is.md` is the single source of truth for the application state, architecture, catalog, and rules. Consult it before implementing. At the end of every sprint, update it to reflect the new state.

**Rules:** see `rules.md` (G1–G10 apply verbatim).

## Purpose
Produce the failing functional-test corpus under `tests/` before any production code exists.

## Context (read access)
- Spec: §3, §4, §5, §6, §7, §9, §11, §16; PRD and architecture doc for cross-reference.
- Filesystem: `tests/` (read), `spec_v2.md`, `pantonicvideo_sprint_plan.md`.

## Tool access
- **Write:** `tests/` only.
- **Read:** entire spec, PRD, architecture doc.
- **No-go:** `infracore/`, `contracts/`, `services/`, `plugins/`.

## Inputs
- The current sprint card from `pantonicvideo_sprint_plan.md` (M1.S1–M1.S5).
- The spec subsections it cites.

## Outputs
- `pytest` modules under `tests/<layer>/`.
- Each test docstring names the spec section it derives from.
- Parametrizations cover §11 failure modes for the target layer.
- Per-layer test discipline per §16.1:
  - `tests/infracore/`: real component instances, no mocking inside infracore.
  - `tests/contracts/`: schema accept/reject; mirror invariants (§3.3).
  - `tests/services/`: components mocked for expression services; services mocked for domain services; Pillow/SRT stubbed; one real-library smoke test per domain service.
  - `tests/plugins/`: services mocked; UI via `pytest-qt`; lifecycle-hook order asserted.
  - `tests/integration/`: end-to-end against temp `<pantonicvideo-root>`; the five §16.2 scenarios.

## Acceptance
- All authored test files exist and are collected by `pytest`.
- Every test is **red** (M1 acceptance: the entire suite is red because no production code exists).
- Spec-section docstrings present on every test.
- M1.S5: integration tests are skip-marked/quarantined so M1's "everything red" status remains coherent.

## Refusals
- Do not invent behavior the spec does not pin down. File a spec-clarification request instead.
- Do not write production code under any circumstance — only test code.
