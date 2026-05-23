"""Per-module conftest: adds usbea_ai's source dir to sys.path so tests can
import its pure-Python services without involving Odoo.

The addon's package __init__.py is NEVER imported here — we only point at
``addons/usbea_ai/`` as a sys.path root, so ``from services.cache import
PromptCache`` resolves to ``addons/usbea_ai/services/cache.py`` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_USBEA_AI_DIR = (
    Path(__file__).resolve().parent.parent.parent / "addons" / "usbea_ai"
)
if str(_USBEA_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_USBEA_AI_DIR))
