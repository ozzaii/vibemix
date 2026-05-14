# SPDX-License-Identifier: Apache-2.0
"""Phase 17 detector test package marker.

Each detector under ``vibemix.state.detectors.*`` has a sibling test module here
exercising fire / no-fire / silence-gate / cooldown / baseline-rotation behavior.
The ``conftest.py`` provides the shared ``_state(...)`` fixture (copied verbatim
from ``tests/state/test_event_detector.py`` since pytest discovery treats each
test directory independently and the fixture is light enough to live in both
places).
"""
