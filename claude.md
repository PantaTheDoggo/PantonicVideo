# CLAUDE.md — plugin-extender, Sprint 2

You are the executing agent for the `plugin-extender` role, Sprint 2.
Your deliverables: extend `project_launcher` to v1.1.0 (Sprint B) and build the new `project_folder` plugin v1.0.0 (Sprint C).

## Active in
plugin-extender Sprint 2 — sole executing agent.

## Sprint tasks

### Sprint B — `project_launcher` v1.1.0
1. Add failing tests in `tests/plugins/test_project_launcher_open_folder.py` **before** any production code (G1).
2. Update `plugins/project_launcher/manifest.json`: bump `version` to `"1.1.0"`, add `app_state_service` to `required_services`.
3. Update `plugins/project_launcher/plugin.py`: store `app_state_service` in `on_load`; implement `on_enable` with `QFileDialog`; extend `commit` to call `state_set("current_project", folder)`.

### Sprint C — `project_folder` v1.0.0
1. Add failing tests in `tests/plugins/test_project_folder.py` **before** any production code (G1).
2. Create `plugins/project_folder/manifest.json` (new).
3. Create `plugins/project_folder/plugin.py` (new).

### Final
4. Run the full test matrix and confirm all suites green.
5. Signal to `release-engineer` that `plugins/project_folder/` must be added to `pyinstaller.spec`.

## Manifests (from spec)

### project_launcher v1.1.0
```json
{
  "name": "project_launcher",
  "version": "1.1.0",
  "contracts_min_version": "1.0.0",
  "author": "PantonicVideo",
  "description": "Folder picker for selecting and opening a project directory.",
  "entry_point": "plugins.project_launcher.plugin:ProjectLauncherPlugin",
  "required_services": [
    {"name": "project_service",    "min_version": "1.0.0"},
    {"name": "filesystem_service", "min_version": "1.0.0"},
    {"name": "app_state_service",  "min_version": "1.0.0"},
    {"name": "logging_service",    "min_version": "1.0.0"}
  ],
  "inputs": [], "outputs": [], "permissions": []
}
```

### project_folder v1.0.0
```json
{
  "name": "project_folder",
  "version": "1.0.0",
  "contracts_min_version": "1.0.0",
  "author": "PantonicVideo",
  "description": "Browse and manage files within the current project folder.",
  "entry_point": "plugins.project_folder.plugin:ProjectFolderPlugin",
  "required_services": [
    {"name": "app_state_service",  "min_version": "1.0.0"},
    {"name": "filesystem_service", "min_version": "1.1.0"},
    {"name": "signal_service",     "min_version": "1.0.0"},
    {"name": "logging_service",    "min_version": "1.0.0"}
  ],
  "inputs": [], "outputs": [], "permissions": []
}
```

## Method skeleton — project_launcher (from spec)
```python
from __future__ import annotations
from pathlib import Path
from typing import Any
from PySide6.QtWidgets import QFileDialog

class ProjectLauncherPlugin:
    def on_load(self, services: dict[str, Any]) -> None:
        self._project_service    = services["project_service"]
        self._filesystem_service = services["filesystem_service"]
        self._app_state_service  = services["app_state_service"]
        self._logging_service    = services["logging_service"]

    def on_enable(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            None, "Open Folder", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if selected:
            self.commit(Path(selected))

    def on_disable(self) -> None: pass
    def on_unload(self) -> None: pass

    def commit(self, folder: Path) -> None:
        self._project_service.set_current(folder)
        self._app_state_service.state_set("current_project", folder)
```

## Per-sprint targets
- **Sprint B** → `project_launcher` at `version` `1.1.0`; 6 new tests green; M4 floor (`test_project_launcher.py`) stays green.
- **Sprint C** → `project_folder` at `version` `1.0.0`; 23 new tests green; full §13.1 matrix green.

## Constraints
- G1: write the failing test **first**; production code only after.
- G2: all M2–M5 floor tests must remain green.
- G3: fewest lines that pass.
- G4: imports must respect layer direction (§10.1).
- G5: `contracts` package is type-only — no behavior.
- G7: no polling (use `state_observe` + `filesystem_service.watch`).
- G8: all `filesystem_service.*` calls in Qt slots wrapped in `try/except` → `logging_service.raise_alert`.
- G9: manifest changes must pass `model_validate`.
- G10: no new infracore mirrors needed for these plugin additions.

## Stop and ask
- Semantics of a method not pinned by the spec that you would have to invent.
- Ambiguity in a G8 containment boundary.
