"""Conftest: mount usbea_impact utility under unique module name."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ADDON_DIR = _REPO_ROOT / "addons" / "usbea_impact"

_utils_pkg = sys.modules.setdefault("utils", types.ModuleType("utils"))


def _mount(file_rel: str, module_name: str) -> None:
    spec = importlib.util.spec_from_file_location(module_name, _ADDON_DIR / file_rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


_mount("utils/progress.py", "utils.progress")
_utils_pkg.progress = sys.modules["utils.progress"]
