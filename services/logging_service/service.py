from __future__ import annotations


class LoggingServiceImpl:
    def __init__(self, logging_component: object) -> None:
        self._comp = logging_component

    def log(self, channel: str, level: int, message: str) -> None:
        self._comp.log(channel, level, message)

    def raise_alert(self, plugin: str, level: int, summary: str) -> None:
        self._comp.raise_alert(plugin, level, summary)
