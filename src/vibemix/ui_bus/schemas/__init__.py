# SPDX-License-Identifier: Apache-2.0
"""Subpackage for per-message payload structs introduced after Phase 11 — keeps
messages.py wrappers thin while colocating future payload types by domain.
"""

from __future__ import annotations

from vibemix.ui_bus.schemas.citation import SessionCitationPayload

__all__ = ["SessionCitationPayload"]
