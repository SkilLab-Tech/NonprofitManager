"""Conftest: mount usbea_ai service files under unique module names.

Multiple tests/conftests across different addons would collide on the
``services`` and ``utils`` top-level names if they all share sys.path,
so we mount each file under a uniquely-prefixed module name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ADDON_DIR = _REPO_ROOT / "addons" / "usbea_ai"


def _mount(file_rel: str, module_name: str) -> None:
    spec = importlib.util.spec_from_file_location(module_name, _ADDON_DIR / file_rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


# Mount as flat top-level names so test files use ``from services.X import Y``.
# Use a unique synthetic ``services`` package shim that re-exports the three.
_services_pkg = sys.modules.get("services")
if _services_pkg is None:
    import types

    _services_pkg = types.ModuleType("services")
    sys.modules["services"] = _services_pkg

_mount("services/lgpd_redactor.py", "services.lgpd_redactor")
_mount("services/cache.py", "services.cache")
_mount("services/router.py", "services.router")

# Make submodules attribute-accessible (so ``services.cache`` works too).
_services_pkg.lgpd_redactor = sys.modules["services.lgpd_redactor"]
_services_pkg.cache = sys.modules["services.cache"]
_services_pkg.router = sys.modules["services.router"]
