# Spec — `project_launcher` v1.1 (Extensão pós-v1)

**Data:** 2026-04-27
**Agente responsável:** `plugin-extender`
**Guardrails:** G1–G10 (ver `rules.md`)
**Status:** Especificação fechada — aguarda execução (Sprint B)

---

## Contexto

O plugin `project_launcher` foi entregue na v1 com `on_enable: pass` — sem UI funcional. A única ação implementada era `commit(folder)`, que delegava ao `project_service.set_current(folder)`. Esta extensão:

1. Adiciona a abertura real do diálogo nativo "Open Folder" em `on_enable`.
2. Persiste o caminho selecionado em `app_state_service` sob a chave `"current_project"`, além de manter a chamada a `project_service.set_current` (G2 — não regride o piso M4).

---

## Mudanças de manifesto

**Arquivo:** `plugins/project_launcher/manifest.json`

| Campo | Antes | Depois |
|---|---|---|
| `version` | `"1.0.0"` | `"1.1.0"` |
| `required_services` | `project_service`, `filesystem_service`, `logging_service` | + `app_state_service` (min `1.0.0`) |

Manifesto completo resultante:

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
  "inputs": [],
  "outputs": [],
  "permissions": []
}
```

---

## Mudanças no plugin

**Arquivo:** `plugins/project_launcher/plugin.py`

### Imports adicionados
```python
from PySide6.QtWidgets import QFileDialog
```
Nenhum import fora de `contracts.*` / `PySide6.*` (tolerância existente para `pathlib.Path` e `typing.Any` já presentes no piso M4).

### Comportamento de `on_load`
Armazena referência adicional de `app_state_service` recebida via `services["app_state_service"]`.

### Comportamento de `on_enable` (novo)
Abre `QFileDialog.getExistingDirectory` com `None` como parent (sem janela-pai explícita — hospedagem é do Docker menu, S15). Flags: `ShowDirsOnly | DontResolveSymlinks`. Se o usuário confirmar (string não-vazia), invoca `self.commit(Path(selected))`. Se cancelar (string vazia), é **no-op** — sem alerta, sem mudança de estado.

### Comportamento de `commit(folder)` (estendido)
Mantém chamada v1: `project_service.set_current(folder)`.
Adiciona: `app_state_service.state_set("current_project", folder)`.

### Esqueleto resultante
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

---

## Novos testes

**Arquivo:** `tests/plugins/test_project_launcher_open_folder.py` (novo — não toca piso M4)

| # | Teste | Cláusula |
|---|---|---|
| 1 | `test_required_services_includes_app_state` | manifesto declara `app_state_service` |
| 2 | `test_commit_writes_state_current_project` | `state_set("current_project", folder)` chamado |
| 3 | `test_commit_still_calls_set_current` | `project_service.set_current(folder)` ainda chamado (G2) |
| 4 | `test_on_enable_opens_dialog_and_commits` | monkeypatch `QFileDialog.getExistingDirectory` → string → `commit` invocado |
| 5 | `test_on_enable_dialog_cancel_is_noop` | retorno `""` → `set_current` e `state_set` não chamados |
| 6 | `test_imports_only_contracts_and_pyside6` | AST scan: zero imports de `infracore` ou `services.` |

---

## Critérios de aceitação (exit da sprint)

- Testes 1–6 vão de vermelho → verde.
- Piso M4 travado (`tests/plugins/test_project_launcher.py`) permanece verde (G2).
- Suítes completas verdes: `tests/plugins/`, `tests/services/`, `tests/infracore/`, `tests/contracts/`.
- `tests/integration/` — os 5 cenários §16.2 passam.
- Manifesto valida via `PluginManifest.model_validate` (G9).
- Lifecycle hooks completos sem exceção em fixture limpa.
- Imports: `grep -E "^(import|from)" plugins/project_launcher/plugin.py` — somente `contracts.*` e `PySide6.*` (mais tolerâncias existentes).

---

## Dependências

Nenhuma. Esta sprint é independente e pode rodar em paralelo à Sprint do `service-extender`.
