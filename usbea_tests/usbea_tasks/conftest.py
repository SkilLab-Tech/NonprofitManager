"""Per-module conftest: makes the (lightweight) usbea_tasks helpers importable
without involving Odoo. Only the parser helpers in project_task have pure
Python logic; we test those in isolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

_USBEA_TASKS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "addons" / "usbea_tasks"
)
if str(_USBEA_TASKS_DIR) not in sys.path:
    sys.path.insert(0, str(_USBEA_TASKS_DIR))
