# Skill: plugin-builder

**Rules:** see `_shared/rules.md` (G1–G10 apply verbatim).

## Purpose
Implement one plugin folder under `plugins/<target>/` to turn its tests green. Parameterized per plugin.

## Context (read access)
- Spec: §3, §6 (**only the subsection for the target plugin**), §10, §19.1.
- Tests: the target plugin's test file under `tests/plugins/`.
- Contracts modules for the services this plugin requires.
- **No** infracore source. **No** service source.

## Tool access
- **Write:** `plugins/<target>/` only.
- **Read:** `contracts/`, `tests/plugins/test_<target>.py`, the §6 subsection for `<target>`, §10, §19.1.
- **No-go:** `infracore/`, `services/`, all other plugins, all other tests.

## Inputs
- Sprint card naming the target plugin (one of three).
- The plugin's test file. Services arrive mocked via fixtures.

## Outputs
- `plugins/<target>/manifest.json` (strict, validates).
- `plugins/<target>/plugin.py` (entry-point class with lifecycle hooks).
- `__init__.py`.

## Acceptance
- Target test `tests/plugins/test_<target>.py` passes.
- M2 + M3 regression floors stay green (G2).
- `manifest.json` validates strictly (G9): `name`, `description`, `author`, `contracts_min_version`, `required_services` (each with `min_version`), entry-point class.
- Lifecycle hooks (`on_load`, `on_enable`, `on_disable`, `on_unload`) complete without exception on a clean fixture.
- Imports respect §10.1: **only** `contracts.*` and `PySide6.*`. Any other import (`os`, `pathlib`, `requests`, even type-annotation imports not sourced from contracts) is rejected by `integration-agent`.

## Refusals
- Do not import `infracore.*`, `services.*`, or any external library.
- Do not call another plugin (PRD §4.3 — cross-plugin direct calls forbidden).
- If a plugin needs filesystem access, route through `filesystem_service` (G6).
- If §6.<target> is silent on a UI detail, file a spec-clarification request.
