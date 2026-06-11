# SPDX-License-Identifier: Apache-2.0
"""Shared library-test isolation fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_viber_ground_ledger(tmp_path, monkeypatch):
    """Keep library tests away from the REAL ground ledger.

    ``chat_with_codex`` harvests ``~/.cache/vibemix/viber_working_set.json``
    on every successful turn (and a fresh-conversation turn OVERWRITES it), so
    an unisolated test run would clobber the user's live working set — the
    same foot-gun class as the ``RekordboxLibrary.CACHE_PATH`` gotcha. Tests
    that care about the ledger re-point this env var themselves; everyone
    else silently writes into their own tmp dir.
    """
    monkeypatch.setenv("VIBEMIX_VIBER_WORKING_SET_PATH", str(tmp_path / "viber_working_set.json"))
