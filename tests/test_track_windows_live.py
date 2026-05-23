# SPDX-License-Identifier: Apache-2.0
"""Windows-only live SMTC smoke tests — Phase 20 fills the bodies.

Stub collected on macOS but skipped via the module-level pytestmark. Phase 20's
``windows-latest`` GitHub Actions matrix executes the body on a real Windows VM
with a media player reporting to SMTC.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


# reason: SMTC (System Media Transport Controls) is a Win 10/11 desktop API —
# Server 2022 hosts lack the SMTC surface. Live discharge rides
# KAAN-ACTION-LEGAL.md §V7-LIVE-02.
@pytest.mark.windows_only
@pytest.mark.xfail(
    strict=False,
    reason="Win 11 desktop SMTC API — see §V7-LIVE-02",
)
def test_track_windows_reads_real_smtc():
    """Live smoke — Phase 20 fills in. Expects either a real Now-Playing
    surface (Spotify / djay / Serato Stream / etc.) returning a title, or
    None if no media app is active. Skipped on macOS."""
    from vibemix.platform._track_windows import TrackWindows

    backend = TrackWindows()
    assert backend.is_available()
    snap = backend.poll()
    # snap may be None if no media is playing on the test machine.
    if snap is not None:
        assert isinstance(snap.title, str)
        assert len(snap.title) > 0
