# SPDX-License-Identifier: Apache-2.0
"""Runtime jsonschema guard for inbound ipc.* messages.

Phase 11 Wave 0 — the Wave 4 WizardLoop will call ``parse_message(raw)`` on
every frame popped off the ws_bus. Drift between the Tauri shell and the
sidecar is caught here at the trust boundary (T-11-W0-04 mitigation).

``validate_message`` is the strict "raise on violation" entry point;
``parse_message`` is the convenience wrapper that accepts either a JSON
string or an already-parsed dict (the WizardLoop will hand us strings off the
WebSocket, but tests prefer dicts).
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from vibemix.ui_bus.messages import _SCHEMA, _VALIDATOR


def validate_message(raw: dict) -> None:
    """Raise ``jsonschema.ValidationError`` if ``raw`` violates the IPC schema.

    Use the module-level compiled ``_VALIDATOR`` (Draft-07) — ``.validate()``
    on a compiled validator is materially cheaper than top-level
    ``jsonschema.validate(d, schema)`` which re-builds the resolver every call.
    """
    _VALIDATOR.validate(raw)


def parse_message(raw: dict | str) -> dict:
    """Parse + validate an inbound IPC frame.

    Accepts a JSON string (typical for ws_bus reads) or an already-decoded
    dict (typical for tests). Returns the validated dict on success. Raises:

    * ``TypeError`` if ``raw`` is neither a dict nor a string.
    * ``json.JSONDecodeError`` if ``raw`` is a string that does not parse.
    * ``jsonschema.ValidationError`` if the decoded value violates the schema.
    """
    if isinstance(raw, str):
        decoded: Any = json.loads(raw)
    elif isinstance(raw, dict):
        decoded = raw
    else:
        raise TypeError(f"parse_message expected dict | str, got {type(raw).__name__}")
    if not isinstance(decoded, dict):
        raise jsonschema.ValidationError(
            f"top-level ipc payload must be a JSON object, got {type(decoded).__name__}"
        )
    _VALIDATOR.validate(decoded)
    return decoded


__all__ = ["_SCHEMA", "parse_message", "validate_message"]
