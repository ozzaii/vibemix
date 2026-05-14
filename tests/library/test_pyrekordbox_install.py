# SPDX-License-Identifier: Apache-2.0
"""Phase 25 Plan 25-01 — pyrekordbox install smoke tests.

Three import-only assertions wire the WAVE-0-DEPS-SPIKE.md verdict into CI:

1. ``import pyrekordbox`` succeeds (the package landed under the
   ``--no-deps + manual transitives`` recipe encoded in ``pyproject.toml``).
2. ``from pyrekordbox import RekordboxXml`` succeeds (XML import path live —
   ``rbxml.RekordboxXml`` is the class we consume in Plan 25-02).
3. SQLCipher path stays dormant — running a fresh Python interpreter that
   imports ``pyrekordbox`` (top-level) loads zero modules matching
   ``*sqlcipher*`` into ``sys.modules``. The dormancy gate prevents a
   regression where someone accidentally re-introduces ``sqlcipher3-wheels``
   into the dep graph (it would bloat the PyInstaller bundle by ~3.2 MB and
   ship a C-extension we never execute).

The third test uses ``subprocess.run`` to force a clean interpreter state —
``sys.modules`` in the running pytest worker carries hits from other tests
that may legitimately import other things.
"""

from __future__ import annotations

import subprocess
import sys


def test_pyrekordbox_imports_clean() -> None:
    """``import pyrekordbox`` succeeds without raising."""
    import pyrekordbox  # noqa: F401 — import-only smoke

    # Spike-locked version: 0.4.4 (WAVE-0-DEPS-SPIKE.md).
    assert pyrekordbox.__version__ == "0.4.4", (
        f"expected pyrekordbox 0.4.4 (spike-locked), got {pyrekordbox.__version__}"
    )


def test_rekordbox_xml_import_live() -> None:
    """``from pyrekordbox import RekordboxXml`` succeeds — XML path live."""
    from pyrekordbox import RekordboxXml

    # The class is re-exported from pyrekordbox.rbxml; verify the canonical
    # module path so Plan 25-02 can rely on the import surface.
    assert RekordboxXml.__module__ == "pyrekordbox.rbxml", (
        f"RekordboxXml expected to live in pyrekordbox.rbxml; got {RekordboxXml.__module__}"
    )


def test_sqlcipher_path_dormant_in_fresh_interpreter() -> None:
    """SQLCipher binary is never loaded — Pitfall gate.

    Spawns a fresh ``python -c`` subprocess so ``sys.modules`` reflects only
    the import chain triggered by ``import pyrekordbox``. The expected output
    is a single line ``DORMANT`` printed to stdout; any module matching
    ``*sqlcipher*`` flips the line to ``LEAKED:<mod-list>`` and the assertion
    fails (CI red).
    """
    script = (
        "import sys\n"
        "import pyrekordbox  # noqa\n"
        "from pyrekordbox import RekordboxXml  # noqa\n"
        "leaks = sorted(m for m in sys.modules if 'sqlcipher' in m.lower())\n"
        "print('LEAKED:' + ','.join(leaks) if leaks else 'DORMANT')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "DORMANT", (
        f"SQLCipher path is NOT dormant — child stdout: {result.stdout!r}; "
        f"stderr: {result.stderr!r}"
    )
