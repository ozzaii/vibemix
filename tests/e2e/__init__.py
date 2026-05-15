# SPDX-License-Identifier: Apache-2.0
"""End-to-end test package for Phase 29 (and future end-to-end work).

Tests in this package exercise REAL subprocesses + REAL websocket
connections against the production sidecar code paths. Marked
``@pytest.mark.e2e`` so fast-lane CI can opt out via
``pytest -m 'not e2e'``.
"""
