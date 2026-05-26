# SPDX-License-Identifier: Apache-2.0
"""Phase 81 BENCH — offline test package for the validation instrument.

The bench harness (``src/vibemix/bench/``) is built across Plans 02 (harness),
03 (eval), 04 (review). This package installs the Nyquist safety net BEFORE any
``bench/`` source lands: every BENCH-01/02/03 acceptance criterion is pinned by
an ``xfail(strict=True)`` test that flips to a real pass when its implementation
plan ships. A silent early-pass becomes an ``xpassed`` → HARD failure.

Honest green: ZERO API calls on this gate — the offline ``_FakeClient`` fixture
returns canned text + synthetic ``usage_metadata`` with no network, no
``genai.Client``, no ``GEMINI_API_KEY``.
"""
