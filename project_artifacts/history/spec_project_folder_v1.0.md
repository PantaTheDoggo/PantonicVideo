# Spec — `project_folder` v1.0 (Novo plugin pós-v1)

**Data:** 2026-04-27
**Agente responsável:** `plugin-extender`
**Guardrails:** G1–G10 (ver `rules.md`)
**Status:** Especificação fechada — aguarda Sprint do `service-extender` (pré-condição)

---

## Contexto

Novo built-in plugin que apresenta os arquivos da pasta do projeto corrente, determinada pela chave `"current_project"` no `AppStateService`. Permite operações triviais de gerenciamento de arquivos e pastas via teclado e mouse.

---

## Pré-condição obrigatória (Sprint `service-extender`)

`FilesystemService` precisa ser estendido com os seguintes métodos antes desta sprint:

```python
class FilesystemService(Protocol):
    # ... métodos existentes mantidos ...
    def rename(self, src: Path, dst: Path) -> None: ...
    def move(self,   src: Path, dst: Path) -> None: ...
    def copy(self,   src: Path, dst: Path) -> None: ...
```

- `service_api_version` do `filesystem_service`: `1.0.0` → `1.1.0`.
- Mirror G10 aplicado onde houver schema espelhado em `infracore/`.

---

## Manifesto

**Arquivo:** `plugins/project_folder/manifest.json` (novo)

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
  "inputs": [],
  "outputs": [],
  "permissions": []
}
```

---

## Estrutura de arquivos

```
plugins/project_folder/
├── manifest.json
└── plugin.py
```

---

## Lifecycle hooks

### `on_load(services)`
- Guarda referências dos 4 serviços.
- Não cria widget. Não lê estado.

### `on_enable()`
- Constrói `QWidget` raiz com `QListView` + `QStandardItemModel` + `QVBoxLayout`.
- Se `current_project` ausente: exibe `QLabel` placeholder ("Open a project to view its files"); atalhos ficam desabilitados.
- Registra atalhos via `QShortcut` (ver tabela de ações).
- Conecta `doubleClicked` do `QListView` a `_on_double_click`.
- Configura menu de contexto via `customContextMenuRequested`.
- Assina `app_state_service.state_observe("current_project", self._on_project_changed)` → armazena handle `_state_h`.
- Se `state_get("current_project")` já houver valor: chama `_render(root)` imediatamente.

### `on_disable()`
- `state_unobserve(_state_h)`.
- `filesystem_service.unwatch(_fs_h)` (se armado).
- `widget.hide()`.
- Libera modelo e clipboard interno.

### `on_unload()`
- Libera widget e referências de serviço.

---

## Reatividade (G7 — sem polling)

| Fonte de mudança | Mecanismo | Ação |
|---|---|---|
| `current_project` muda no estado | `state_observe` callback | re-arma `_cwd` para nova raiz; `unwatch` antigo; `_render(nova_raiz)` |
| Evento de filesystem no diretório atual | `filesystem_service.watch(cwd, cb)` callback | `_render(_cwd)` (sem re-assinar `state_observe`) |

`_render(path)`:
1. `list_dir(path)` → repopula modelo.
2. `unwatch(_fs_h)` se existia.
3. `_fs_h = filesystem_service.watch(path, self._on_fs_event)`.

---

## Ações e controles

| Gatilho teclado | Gatilho mouse | Ação | Serviço / PySide6 |
|---|---|---|---|
| `F5` | Menu "Refresh" | `_render(_cwd)` | `filesystem_service.list_dir` |
| `Backspace` | Menu "Up" | Sobe 1 nível; clampado em `current_project` (raiz inacessível) | — |
| `Enter` em pasta | Duplo-clique em pasta | Navega: `_cwd = path`; `_render(_cwd)` | — |
| `Enter` em arquivo | Duplo-clique em arquivo | `app_state_service.state_set("open_file_request", path)` | `app_state_service` |
| `Delete` | Menu "Delete" | `QMessageBox.question` Yes → `filesystem_service.delete(path)` | `filesystem_service` |
| `F2` | Menu "Rename" | `QInputDialog.getText` → `filesystem_service.rename(src, src.parent / novo)` | `filesystem_service` |
| `Ctrl+X` | Menu "Cut" | Guarda `(path, "cut")` em clipboard interno | — |
| `Ctrl+C` | Menu "Copy" | Guarda `(path, "copy")` em clipboard interno | — |
| `Ctrl+V` | Menu "Paste" | "cut": `move(src, cwd/src.name)` + limpa clipboard. "copy": `copy(src, cwd/src.name)` | `filesystem_service` |
| `Ctrl+N` | Menu "New folder" | `QInputDialog.getText` → `filesystem_service.make_dir(cwd / nome)` | `filesystem_service` |
| `Ctrl+Shift+N` | Menu "New file" | `QInputDialog.getText` → `filesystem_service.write_file(cwd / nome, b"")` | `filesystem_service` |
| Botão direito | — | Abre `QMenu` com todas as ações acima | `PySide6.QtWidgets.QMenu` |

### Semântica de "abrir arquivo"
Publicação de intenção via estado (Opção A — desacoplado, §4.3):
```python
app_state_service.state_set("open_file_request", path)
```
Outros plugins que quiserem reagir assinam esta chave em suas próprias sprints. `project_folder` não habilita nem chama outros plugins diretamente.

### Semântica de "abrir pasta"
Navegação interna: atualiza `_cwd`; **não** sobrescreve `"current_project"` no estado. `current_project` é sempre a raiz do projeto.

---

## Failure containment (G8)

Toda chamada a `filesystem_service.*` dentro de slots Qt é envolvida por:
```python
try:
    filesystem_service.<operação>(...)
except Exception as e:
    logging_service.raise_alert("project_folder", LogLevel.ERROR, str(e))
```
Nenhuma exceção propaga ao Qt event loop. `PluginRecord.status` permanece `enabled` — a operação falha, não o plugin.

---

## Imports permitidos (§10.1)

```python
from __future__            import annotations
from pathlib               import Path          # aritmética sobre valores recebidos de serviços
from typing                import Any
from contracts.signals     import SubscriptionHandle
from contracts.filesystem  import FilesystemEvent
from contracts.logging     import LogLevel
from PySide6.QtWidgets     import (
    QWidget, QListView, QLabel, QVBoxLayout,
    QMenu, QMessageBox, QInputDialog,
)
from PySide6.QtGui         import (
    QStandardItemModel, QStandardItem, QAction,
    QKeySequence, QShortcut,
)
from PySide6.QtCore        import Qt, QModelIndex
```

Zero imports de `os`, `shutil`, `json`, `time`, `requests`, `infracore.*`, `services.*`.

---

## Novos testes

**Arquivo:** `tests/plugins/test_project_folder.py` (novo)

Mocks via `unittest.mock.MagicMock`; UI via `pytest-qt`.

| # | Teste | Cláusula |
|---|---|---|
| 1 | `test_manifest_validates_strict` | manifesto válido; campo extra rejeitado |
| 2 | `test_manifest_required_services` | 4 serviços declarados; `filesystem_service.min_version == "1.1.0"` |
| 3 | `test_lifecycle_hooks_present` | 4 hooks calláveis |
| 4 | `test_lifecycle_order_clean` | load→enable→disable→unload sem exceção em fixture limpa |
| 5 | `test_empty_state_shows_placeholder` | `state_get` retorna `None` → `list_dir` não chamado; label visível |
| 6 | `test_initial_render_with_current_project` | popula modelo com N itens de `list_dir` |
| 7 | `test_state_observe_subscribed_on_enable` | `state_observe("current_project", ...)` chamado 1× |
| 8 | `test_state_change_re_renders` | callback de observe recebe novo path → `list_dir(novo)` chamado |
| 9 | `test_watch_armed_on_enable_and_unwatched_on_disable` | `watch`/`unwatch` simétricos |
| 10 | `test_fs_event_triggers_re_render` | `FilesystemEvent` entregue ao callback → `list_dir` chamado de novo |
| 11 | `test_double_click_folder_navigates` | `_cwd` muda; `state_set` **não** chamado |
| 12 | `test_double_click_file_emits_open_request` | `state_set("open_file_request", path)` chamado |
| 13 | `test_delete_shortcut_with_confirmation` | mock `QMessageBox.question` Yes → `delete(path)` |
| 14 | `test_delete_shortcut_cancel_no_op` | mock retorna No → `delete` não chamado |
| 15 | `test_rename_shortcut` | mock `QInputDialog` → `rename(src, src.parent / novo)` |
| 16 | `test_cut_paste_calls_move` | Cut+Paste → `move(src, cwd/src.name)` |
| 17 | `test_copy_paste_calls_copy` | Copy+Paste → `copy(src, cwd/src.name)` |
| 18 | `test_new_folder_shortcut` | Ctrl+N → `make_dir(cwd / nome)` |
| 19 | `test_new_file_shortcut` | Ctrl+Shift+N → `write_file(cwd / nome, b"")` |
| 20 | `test_refresh_F5_calls_list_dir` | F5 → nova chamada a `list_dir(_cwd)` |
| 21 | `test_backspace_clamped_at_root` | Backspace na raiz → no-op (sem `list_dir` extra) |
| 22 | `test_failure_in_delete_raises_alert` | `delete` lança `IOError` → `raise_alert("project_folder", ERROR, ...)` sem propagação (G8) |
| 23 | `test_imports_allowlist_only` | AST scan: zero imports de `infracore` ou `services.` |

---

## Critérios de aceitação (exit da sprint)

- Testes 1–23 vão de vermelho → verde.
- Pisos M2, M3, M4 permanecem verdes (G2): `tests/infracore/`, `tests/contracts/`, `tests/services/`, `tests/plugins/` (3 arquivos de piso).
- `tests/integration/` — os 5 cenários §16.2 passam.
- Manifesto valida via `PluginManifest.model_validate` (G9); 4 hooks presentes.
- Imports verificados: `grep -E "^(import|from)" plugins/project_folder/plugin.py`.
- G3: contagem de linhas do plugin ≤ 3× contagem de linhas dos testes novos.
- Plugin built-in novo: sinalizar ao `release-engineer` que `plugins/project_folder/` deve ser adicionado ao `pyinstaller.spec`.

---

## Dependências e sequência

```
service-extender (Sprint 1) → filesystem_service v1.1.0
      ↓
plugin-extender  (Sprint C) → project_folder v1.0.0
      ↓
release-engineer (Sprint D) → pyinstaller.spec + rebuild .exe + smoke checklist
```

Sprint B (`project_launcher` v1.1.0) é independente e pode rodar em paralelo à Sprint 1.
