from __future__ import annotations

from contracts.plugin_registry import PluginRecord, PluginStatus
from PySide6.QtWidgets import QMenu


class DockerMenu(QMenu):
    def update_plugins(self, records: list[PluginRecord]) -> None:
        self.clear()
        for record in records:
            if record.status == PluginStatus.failed:
                continue
            action = self.addAction(record.name)
            action.setToolTip(record.description)
