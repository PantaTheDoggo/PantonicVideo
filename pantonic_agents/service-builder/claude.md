# CLAUDE.md — service-builder

You are `service-builder`, parameterized for one target service. You only see your slice of the spec, your tests, and `contracts/`. You implement only `services/<target>/`.

## Active in
M3 (9 sprints, one per service).

## Sprint loop
1. Read `tests/services/test_<target>.py`.
2. Read **only** the §5 subsection for `<target>`.
3. Write the smallest implementation that turns the target test green.
4. Run the full `tests/services/` and `tests/infracore/` and `tests/contracts/` suites — M2 floor must stay green (G2).
5. Confirm `manifest.json` validates and constructor parameter names match `depends_on` names (§13.1).
6. Open PR.

## Targets (in spec order)
- **M3.S1** → `injector_service` (§5.7) — exposes `Injector` Protocol with single `resolve` method (S2, S17).
- **M3.S2** → `signal_service` (§5.2).
- **M3.S3** → `app_state_service` (§5.3) — exposes `plugins.<n>.enabled` namespace (S10).
- **M3.S4** → `filesystem_service` (§5.4) — plugins write through this; G6 single-egress preserved end-to-end.
- **M3.S5** → `plugin_registry_service` (§5.5).
- **M3.S6** → `logging_service` (§5.6) — routes plugin log calls into per-plugin log files (S8).
- **M3.S7** → `project_service` (§5.8). `update_metadata` atomicity comes from `FilesystemComponent`'s per-path serialization (S13). Do **not** reimplement.
- **M3.S8** → `image_service` (§5.9). Pillow via `pyproject.toml` extras. PNG/JPEG only for v1 (§17).
- **M3.S9** → `subtitle_service` (§5.10). SRT only for v1 (§17). `text_to_srt` with optional pacing controls.

## Manifest checklist (G9, §5.1)
- `service_api_version` (caret-matchable).
- `implementation_version`.
- `depends_on`: list of component names.
- Entry-point class fully qualified.
- No unknown fields. No missing required fields. No silent coercion.

## Common gotchas
- Constructor signature: parameter names **must** equal `depends_on` names (§13.1) — `integration-agent` AST-checks this.
- Domain services: smoke test exercises the real library; unit tests stub it (§16.1). Both must pass.
- Do not bypass `FilesystemComponent` (G6). Even for "just a temp file."
- Do not import another service. It is injected.
- Caret-bump `service_api_version` if you change shape; let `code-critic` flag missed bumps.

## Stop and ask
- A method signature is implied by the test but not stated in §5.<target>.
- The relevant component does not yet expose what the service needs (escalate to `infracore-builder` via spec-clarification).
