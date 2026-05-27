# SPDX-License-Identifier: Apache-2.0
"""Library/Vibe Engine desktop capability contract.

The Library window is the packaged app's path into local CLAP model setup and
the Codex-backed Viber agent. Pin the pieces that make the verified UI/CLI path
reachable from the desktop shell: the window label, registered Tauri commands,
frontend invoke names, and dev-source command entries.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = REPO_ROOT / "tauri/src-tauri/capabilities/default.json"
MAIN_RS = REPO_ROOT / "tauri/src-tauri/src/main.rs"
LIBRARY_CMDS_RS = REPO_ROOT / "tauri/src-tauri/src/library_cmds.rs"
LIBRARY_API = REPO_ROOT / "tauri/ui/src/library/api.ts"

LIBRARY_COMMANDS = (
    "library_search",
    "library_similar",
    "library_curate",
    "library_build_set",
    "library_chat",
    "library_stats",
    "library_models",
    "library_embed_folder",
    "open_library_window",
)


def _load_capability() -> dict:
    return json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))


def _shell_execute_allows(cap: dict) -> list[dict]:
    for perm in cap.get("permissions", []):
        if isinstance(perm, dict) and perm.get("identifier") == "shell:allow-execute":
            allows = perm.get("allow")
            assert isinstance(allows, list), "shell:allow-execute allow must be a list"
            return allows
    raise AssertionError("shell:allow-execute permission not found")


def test_library_window_label_is_capability_scoped() -> None:
    cap = _load_capability()
    assert "library" in cap.get("windows", []), (
        "open_library_window loads library.html into a 'library' WebviewWindow; "
        "dropping this label strands the Vibe Engine in packaged builds"
    )


def test_library_commands_are_registered_in_tauri_invoke_handler() -> None:
    body = MAIN_RS.read_text(encoding="utf-8")
    for command in LIBRARY_COMMANDS:
        assert f"library_cmds::{command}" in body


def test_library_frontend_invokes_registered_command_names() -> None:
    body = LIBRARY_API.read_text(encoding="utf-8")
    for command in LIBRARY_COMMANDS:
        if command == "open_library_window":
            continue
        assert f'"{command}"' in body


def test_library_dev_source_shell_entries_remain_available() -> None:
    cap = _load_capability()
    allows = {entry.get("name"): entry for entry in _shell_execute_allows(cap)}
    assert allows["vibemix-library-uv"] == {
        "name": "vibemix-library-uv",
        "cmd": "uv",
        "args": True,
    }
    assert allows["vibemix-library-python"] == {
        "name": "vibemix-library-python",
        "cmd": "python3",
        "args": True,
    }


def test_library_desktop_bridge_pins_codex_agent_path() -> None:
    body = LIBRARY_CMDS_RS.read_text(encoding="utf-8")

    assert 'LIBRARY_AGENT_BACKEND: &str = "codex"' in body
    assert 'cmd.env("VIBEMIX_LIBRARY_AGENT_BACKEND", LIBRARY_AGENT_BACKEND)' in body
    assert 'cmd.env("VIBEMIX_CODEX_ALLOW_SHELL", "1")' in body
    assert '"library", "chat", "hello", "--backend", "codex", "--json"' in body
