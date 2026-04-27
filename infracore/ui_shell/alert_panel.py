from __future__ import annotations

import logging as _logging
from typing import Optional

from contracts.logging import AlertEntry


class AlertPanel:
    def __init__(self) -> None:
        self._alerts: list[AlertEntry] = []
        self._plugin_authors: dict[str, str] = {}

    def update_alerts(
        self,
        alerts: list[AlertEntry],
        plugin_authors: Optional[dict[str, str]] = None,
    ) -> None:
        self._alerts = list(alerts)
        if plugin_authors:
            self._plugin_authors.update(plugin_authors)

    def current_state(self) -> str:
        unack = [a for a in self._alerts if not a.acknowledged]
        if not unack:
            return "quiescent"
        max_level = max(a.level for a in unack)
        if max_level >= _logging.CRITICAL:
            return "critical"
        if max_level >= _logging.ERROR:
            return "error"
        return "warning"

    def has_author_in_row(self, plugin: str, author: str) -> bool:
        return self._plugin_authors.get(plugin) == author
