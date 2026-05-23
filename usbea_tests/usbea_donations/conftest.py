"""Conftest: mount usbea_donations utilities under unique module names."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ADDON_DIR = _REPO_ROOT / "addons" / "usbea_donations"

_utils_pkg = sys.modules.setdefault("utils", types.ModuleType("utils"))


def _mount(file_rel: str, module_name: str) -> None:
    spec = importlib.util.spec_from_file_location(module_name, _ADDON_DIR / file_rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


_mount("utils/cpf_formatter.py", "utils.cpf_formatter")
_mount("utils/receipt_validator.py", "utils.receipt_validator")
_mount("utils/webhook_signature.py", "utils.webhook_signature")
_utils_pkg.cpf_formatter = sys.modules["utils.cpf_formatter"]
_utils_pkg.receipt_validator = sys.modules["utils.receipt_validator"]
_utils_pkg.webhook_signature = sys.modules["utils.webhook_signature"]
