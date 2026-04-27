# Skill: infracore-builder

**Rules:** see `_shared/rules.md` (G1–G10 apply verbatim).

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
