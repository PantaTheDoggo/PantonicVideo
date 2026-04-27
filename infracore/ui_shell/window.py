from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtWidgets import QMainWindow


_LAYOUT_VERSION = 1


class MainWindow(QMainWindow):
    def save_layout(self, root: Path) -> None:
        root = Path(root)
        qt_state = self.saveGeometry().toBase64().data().decode()
        data = {
            "version": _LAYOUT_VERSION,
            "qt_state": qt_state,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        root.mkdir(parents=True, exist_ok=True)
        (root / "layout.json").write_text(json.dumps(data), encoding="utf-8")

    def restore_layout(
        self,
        root: Path,
        on_warning: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Return True on first run (no layout file or version mismatch fallback)."""
        layout_file = Path(root) / "layout.json"
        if not layout_file.exists():
            return True

        try:
            data = json.loads(layout_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if on_warning:
                on_warning("layout.json could not be read; using first-run layout")
            return True

        version = data.get("version")
        if version != _LAYOUT_VERSION:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            renamed = layout_file.parent / f"layout.json.unrecognized-{ts}"
            layout_file.rename(renamed)
            if on_warning:
                on_warning(
                    f"Unrecognized layout.json version {version!r}; "
                    f"renamed to {renamed.name}, using first-run layout"
                )
            return True

        qt_state = data.get("qt_state", "")
        if qt_state:
            from PySide6.QtCore import QByteArray
            self.restoreGeometry(QByteArray.fromBase64(qt_state.encode()))

        return False
