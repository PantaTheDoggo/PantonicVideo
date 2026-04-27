from __future__ import annotations

import sys
import traceback
import types
from typing import Any, Optional


def install_excepthook(
    plugin_registry: Optional[Any],
    logging_component: Optional[Any],
) -> None:
    """§9.5, S11: replace sys.excepthook with the PantonicVideo hook while chaining the previous one."""
    prev_hook = sys.excepthook

    def _pantonicvideo_excepthook(
        exc_type: type,
        exc_value: BaseException,
        exc_tb: types.TracebackType | None,
    ) -> None:
        prev_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _pantonicvideo_excepthook


# Exposed for testing
def _pantonicvideo_excepthook(
    exc_type: type,
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    sys.__excepthook__(exc_type, exc_value, exc_tb)
