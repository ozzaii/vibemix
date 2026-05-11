# SPDX-License-Identifier: Apache-2.0
"""Windows-only live screen smoke tests — Phase 20 fills the bodies.

Stubs collect on macOS (skipped via pytestmark) so the platform-selector
firewall test sees the file but doesn't execute any win32 code. Phase 20's
``windows-latest`` GitHub Actions matrix executes the bodies on a real
Windows VM.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


@pytest.mark.windows_only
def test_screen_windows_captures_real_window():
    """Live smoke — Phase 20 fills in. Skipped on macOS by the module-level
    pytestmark."""
    from vibemix.platform._screen_windows import ScreenWindows

    backend = ScreenWindows()
    assert backend.is_available()
    bounds = backend.find_dj_window()
    # If no DJ software running, bounds is None and we capture full monitor.
    frame = backend.capture(bounds)
    assert frame.jpeg.startswith(b"\xff\xd8")  # JPEG magic
    assert 100 < frame.width <= 1280
