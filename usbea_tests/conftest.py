"""Top-level conftest for USBEA pure-Python unit tests.

These tests live OUTSIDE addons/ so pytest never imports the Odoo package
__init__.py chain. Each per-module subdirectory's conftest adds the
corresponding addon services dir to sys.path.

Layout:

    usbea_tests/
        conftest.py              <-- this file (shared fixtures)
        usbea_ai/
            conftest.py          <-- adds addons/usbea_ai to sys.path
            test_lgpd_redactor.py
            ...

Tests run with:

    python -m pytest usbea_tests/

or via Makefile:

    make -f Makefile.usbea test
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so cross-module test helpers (if any)
# can be imported as `usbea_tests.shared`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
