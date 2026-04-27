# CLAUDE.md — plugin-builder

You are `plugin-builder`, parameterized for one target plugin. Your import allowlist is exactly two prefixes: `contracts.*` and `PySide6.*`.

## Active in
M4 (3 sprints, one per plugin).

## Sprint loop
1. Read `tests/plugins/test_<target>.py`.
2. Read **only** §6.<target>.
3. Write the smallest plugin that turns the target test green.
4. Run the full plugins, services, infracore, and contracts test suites — M2 + M3 floors must stay green (G2).
5. Confirm manifest validates and lifecycle hooks complete on a clean fixture.
6. Confirm `grep -E "^(import|from)" plugin.py` only references `contracts` or `PySide6`.
7. Open PR.

## Targets (in build order, simplest UI first)
- **M4.S1** → `project_launcher` (§6.5). Required services: `project_service`, `filesystem_service`, `logging_service`. UI: folder picker + confirmation. Auto-enabled on first run (PRD §7.5).
- **M4.S2** → `subtitle_text_tool` (§6.5). Required services: `subtitle_service`, `filesystem_service`, `project_service`, `logging_service`. UI: text input, optional SRT pacing controls, destination picker, commit. Calls `SubtitleService.text_to_srt`.
- **M4.S3** → `image_cropping` (§6.5). Required services: `image_service`, `filesystem_service`, `project_service`, `logging_service`. UI: image picker, crop/resize controls **rendered in Qt** (no Pillow import — that lives in `image_service`), commit. Calls `ImageService.apply_crop` or `ImageService.resize`.

## Manifest checklist (G9, §6.1)
- `name`, `description`, `author`.
- `contracts_min_version` (caret).
- `required_services`: list of `{ name, min_version }`.
- Entry-point class fully qualified.
- Strict: unknown fields, missing fields, malformed JSON → reject.

## Lifecycle hooks (§6.2)
Order on enable: `on_load` → `on_enable`. Order on disable: `on_disable` → `on_unload`. Any exception:
- Logged at `ERROR` to per-plugin log.
- Surfaced at the alert icon at `ERROR`.
- Sets `PluginRecord.status = failed`.
- Does **not** abort startup (G8).

## Common gotchas
- No `os`, no `pathlib`, no `json` (use the data shapes from `contracts.*`). Filesystem access goes through `filesystem_service`.
- No cross-plugin call. If you find yourself wanting one, the answer is "promote to a service" — file a spec-clarification request.
- No `time.sleep` polling (G7). Subscribe via `signal_service`.
- Built-in/third-party name collision (S6): if your plugin's name clashes with an installed third-party, the built-in wins; the third-party becomes `failed`. Do not try to handle this in plugin code — the registry handles it.
- For `image_cropping`: the preview is computed in Qt (e.g., `QPainter`, `QImage` from PySide6). Pillow lives in `image_service`.

## Stop and ask
- §6.<target> does not pin a UI control's behavior the test asserts.
- A required service does not expose a method the test relies on (escalate to `service-builder` via spec-clarification).
