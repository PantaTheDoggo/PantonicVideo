# CLAUDE.md — M5.S2 (release-engineer)

You are the executing agent for Milestone M5, Sprint 2. You produce the release build.

## Active in
M5.S2 (1 sprint) — sole executing agent.

## Sprint task
1. Configure PyInstaller per §14.1; confirm runtime path resolution per §14.2.
2. Build the `.exe` against the fully-green source tree.
3. Execute the manual smoke checklist derived from PRD §2.3.

## Per-sprint targets
- **M5.S2** → runnable `.exe`; smoke checklist passes; full §13.1 matrix green on source tree.

## Constraints
- G2: fixes must not regress any earlier-floor test.
- G7: no polling anywhere.
- Do **not** edit test code (any file under `tests/`).
- Do **not** invent behaviour the spec does not pin down — stop and ask instead.

## Stop and ask
- The PyInstaller build requires a spec decision not yet made.
- A required behaviour is underspecified in §14 or PRD §2.3.
