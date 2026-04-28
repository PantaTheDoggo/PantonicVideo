from __future__ import annotations

from pathlib import Path
from typing import Any

from contracts.filesystem import FilesystemEvent
from contracts.logging import LogLevel
from contracts.signals import SubscriptionHandle
from PySide6.QtWidgets import (
    QWidget, QListView, QLabel, QVBoxLayout,
    QMenu, QMessageBox, QInputDialog,
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem,
    QKeySequence, QShortcut,
)
from PySide6.QtCore import Qt, QModelIndex


class ProjectFolderPlugin:
    def on_load(self, services: dict[str, Any]) -> None:
        self._app_state = services["app_state_service"]
        self._fs        = services["filesystem_service"]
        self._log       = services["logging_service"]

    def on_enable(self) -> None:
        self._cwd:       Path | None               = None
        self._fs_h:      SubscriptionHandle | None = None
        self._clipboard: tuple[Path, str] | None   = None

        self._widget = QWidget()
        layout = QVBoxLayout(self._widget)

        self._placeholder = QLabel("Open a project to view its files")
        self._model = QStandardItemModel()
        self._view  = QListView()
        self._view.setModel(self._model)

        layout.addWidget(self._placeholder)
        layout.addWidget(self._view)

        self._view.doubleClicked.connect(self._on_double_click)
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._on_context_menu)
        self._register_shortcuts()

        self._state_h = self._app_state.state_observe("current_project", self._on_project_changed)

        root = self._app_state.state_get("current_project")
        if root is None:
            self._placeholder.setVisible(True)
        else:
            self._placeholder.setVisible(False)
            self._render(Path(root))

    def on_disable(self) -> None:
        self._app_state.state_unobserve(self._state_h)
        if self._fs_h is not None:
            self._fs.unwatch(self._fs_h)
            self._fs_h = None
        self._widget.hide()
        self._clipboard = None

    def on_unload(self) -> None:
        self._widget = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _render(self, path: Path) -> None:
        self._cwd = path
        self._model.clear()
        for p in self._fs.list_dir(path):
            item = QStandardItem(p.name)
            item.setData(p,          Qt.UserRole)
            item.setData(p.is_dir(), Qt.UserRole + 1)
            self._model.appendRow(item)
        if self._fs_h is not None:
            self._fs.unwatch(self._fs_h)
        self._fs_h = self._fs.watch(path, self._on_fs_event)

    def _on_project_changed(self, new_root: Any) -> None:
        if self._fs_h is not None:
            self._fs.unwatch(self._fs_h)
            self._fs_h = None
        if new_root is not None:
            self._placeholder.setVisible(False)
            self._render(Path(new_root))
        else:
            self._cwd = None
            self._model.clear()
            self._placeholder.setVisible(True)

    def _on_fs_event(self, _event: FilesystemEvent) -> None:
        if self._cwd is not None:
            self._render(self._cwd)

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------

    def _on_double_click(self, index: QModelIndex) -> None:
        item = self._model.itemFromIndex(index)
        if item is None:
            return
        path: Path = item.data(Qt.UserRole)
        if item.data(Qt.UserRole + 1):
            self._render(path)
        else:
            self._app_state.state_set("open_file_request", path)

    def _on_context_menu(self, pos: Any) -> None:
        menu = QMenu(self._view)
        menu.addAction("Refresh",    self._do_refresh)
        menu.addAction("Up",         self._do_up)
        if self._selected_path() is not None:
            menu.addAction("Delete", self._do_delete)
            menu.addAction("Rename", self._do_rename)
            menu.addAction("Cut",    self._do_cut)
            menu.addAction("Copy",   self._do_copy)
        menu.addAction("Paste",      self._do_paste)
        menu.addAction("New folder", self._do_new_folder)
        menu.addAction("New file",   self._do_new_file)
        menu.exec(self._view.viewport().mapToGlobal(pos))

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("F5"),           self._widget, self._do_refresh)
        QShortcut(QKeySequence("Backspace"),     self._widget, self._do_up)
        QShortcut(QKeySequence("Return"),        self._widget, self._do_enter)
        QShortcut(QKeySequence("Delete"),        self._widget, self._do_delete)
        QShortcut(QKeySequence("F2"),            self._widget, self._do_rename)
        QShortcut(QKeySequence("Ctrl+X"),        self._widget, self._do_cut)
        QShortcut(QKeySequence("Ctrl+C"),        self._widget, self._do_copy)
        QShortcut(QKeySequence("Ctrl+V"),        self._widget, self._do_paste)
        QShortcut(QKeySequence("Ctrl+N"),        self._widget, self._do_new_folder)
        QShortcut(QKeySequence("Ctrl+Shift+N"),  self._widget, self._do_new_file)

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    def _selected_path(self) -> Path | None:
        indexes = self._view.selectedIndexes()
        if not indexes:
            return None
        item = self._model.itemFromIndex(indexes[0])
        return item.data(Qt.UserRole) if item else None

    def _do_refresh(self) -> None:
        if self._cwd is not None:
            self._render(self._cwd)

    def _do_up(self) -> None:
        root = self._app_state.state_get("current_project")
        if self._cwd is None or root is None or self._cwd == Path(root):
            return
        self._render(self._cwd.parent)

    def _do_enter(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        item = self._model.itemFromIndex(self._view.selectedIndexes()[0])
        if item.data(Qt.UserRole + 1):
            self._render(path)
        else:
            self._app_state.state_set("open_file_request", path)

    def _do_delete(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        reply = QMessageBox.question(self._widget, "Delete", f"Delete {path.name}?")
        if reply == QMessageBox.Yes:
            try:
                self._fs.delete(path)
            except Exception as e:
                self._log.raise_alert("project_folder", LogLevel.ERROR, str(e))

    def _do_rename(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        new_name, ok = QInputDialog.getText(self._widget, "Rename", "New name:", text=path.name)
        if ok and new_name:
            try:
                self._fs.rename(path, path.parent / new_name)
            except Exception as e:
                self._log.raise_alert("project_folder", LogLevel.ERROR, str(e))

    def _do_cut(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._clipboard = (path, "cut")

    def _do_copy(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._clipboard = (path, "copy")

    def _do_paste(self) -> None:
        if self._clipboard is None or self._cwd is None:
            return
        src, op = self._clipboard
        dst = self._cwd / src.name
        try:
            if op == "cut":
                self._fs.move(src, dst)
                self._clipboard = None
            else:
                self._fs.copy(src, dst)
        except Exception as e:
            self._log.raise_alert("project_folder", LogLevel.ERROR, str(e))

    def _do_new_folder(self) -> None:
        if self._cwd is None:
            return
        name, ok = QInputDialog.getText(self._widget, "New folder", "Folder name:")
        if ok and name:
            try:
                self._fs.make_dir(self._cwd / name)
            except Exception as e:
                self._log.raise_alert("project_folder", LogLevel.ERROR, str(e))

    def _do_new_file(self) -> None:
        if self._cwd is None:
            return
        name, ok = QInputDialog.getText(self._widget, "New file", "File name:")
        if ok and name:
            try:
                self._fs.write_file(self._cwd / name, b"")
            except Exception as e:
                self._log.raise_alert("project_folder", LogLevel.ERROR, str(e))
