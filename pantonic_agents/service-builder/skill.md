# Skill: service-builder

**Rules:** see `_shared/rules.md` (G1–G10 apply verbatim).

## Purpose
Implement one service folder under `services/<target>/` to turn its tests green. Parameterized per service.

## Context (read access)
- Spec: §3, §5 (**only the subsection for the target service**), §10, §13, §14, §19.1.
- Tests: the target service's test file under `tests/services/`.
- The contracts module the service implements.
- **No** infracore source. **No** other service source.

## Tool access
- **Write:** `services/<target>/` only.
- **Read:** `contracts/`, `tests/services/test_<target>.py`, the §5 subsection for `<target>`, §10, §13, §14, §19.1.
- **No-go:** `infracore/` source, other `services/<X>/` source, `plugins/`, all other tests.

## Inputs
- Sprint card naming the target service (one of nine).
- The service's test file. Mocked components arrive via test fixtures.

## Outputs
- `services/<target>/manifest.json` (strict, validates).
- `services/<target>/service.py` (entry-point class).
- `services/<target>/pyproject.toml` declaring external dependencies as extras (§14).
- `__init__.py` and any internal helpers required.
- For domain services: real-library smoke test stays green when run.

## Acceptance
- Target test `tests/services/test_<target>.py` passes.
- M2 regression floor stays green (G2).
- `manifest.json` validates strictly (G9): `service_api_version`, `implementation_version`, `depends_on`, entry-point class. Service constructor parameter names match `depends_on` names (§13.1).
- All external imports declared in `pyproject.toml` extras. No `requirements.txt`. No hard-coded import outside declared extras.
- §10.1 imports respected: `services.<target>` may import `contracts.*`, `infracore.*`, and its declared extras. **Not** other services.

## Refusals
- Do not modify `infracore/`, other services, plugins, or any test.
- Do not import other services directly. They arrive via injection (§10.2).
- If the test or §5 subsection is silent on a behavior, file a spec-clarification request.
