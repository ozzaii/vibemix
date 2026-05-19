# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-02 — tauri-plugin-macos-permissions wire gate.

Pins three facts that together prove the plugin is wired correctly for
the one-click install wizard:

1. ``tauri/src-tauri/Cargo.toml`` pins ``tauri-plugin-macos-permissions =
   "2.3.0"`` under the macOS-only target dependency table.
2. ``tauri/src-tauri/src/main.rs`` registers the plugin behind a
   ``#[cfg(target_os = "macos")]`` guard so Windows builds stay green.
3. ``tauri/src-tauri/capabilities/default.json`` allowlists the plugin's
   namespace + the two commands the wizard invokes.

The gate is statically scoped — it never runs ``cargo check``. The
Phase 11 Tauri build pipeline + the existing capabilities-lint workflow
catch parse-level regressions; this test catches drift in *intent*.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CARGO_TOML = REPO_ROOT / "tauri" / "src-tauri" / "Cargo.toml"
MAIN_RS = REPO_ROOT / "tauri" / "src-tauri" / "src" / "main.rs"
CAPABILITIES = REPO_ROOT / "tauri" / "src-tauri" / "capabilities" / "default.json"


def test_cargo_toml_pins_plugin_version() -> None:
    """Plugin appears under [target.'cfg(target_os = "macos")'.dependencies]
    pinned to exactly 2.3.0 (33-RESEARCH tooling pin)."""
    body = CARGO_TOML.read_text(encoding="utf-8")
    assert "tauri-plugin-macos-permissions" in body, (
        "Cargo.toml missing tauri-plugin-macos-permissions dep"
    )
    # Pin must be exactly "2.3.0" (no caret / tilde — research lock).
    pattern = re.compile(
        r'tauri-plugin-macos-permissions\s*=\s*"2\.3\.0"'
    )
    assert pattern.search(body), (
        "Plugin pin missing or not '2.3.0'. Found: "
        + repr(body[body.find("tauri-plugin-macos-permissions"):][:80])
    )
    # Must live under the macOS target table (the only macOS-target block
    # in this file). We verify by finding the target header BEFORE the dep.
    target_block_start = body.find(
        '[target.\'cfg(target_os = "macos")\'.dependencies]'
    )
    plugin_pos = body.find("tauri-plugin-macos-permissions")
    assert target_block_start != -1, "macOS target dep table missing"
    assert target_block_start < plugin_pos, (
        "Plugin must be under [target.cfg(macos).dependencies] not [dependencies]"
    )


def test_lib_rs_registers_plugin_on_macos_only() -> None:
    """main.rs registers the plugin behind a cfg(target_os = "macos") guard."""
    body = MAIN_RS.read_text(encoding="utf-8")
    assert "tauri_plugin_macos_permissions::init" in body, (
        "main.rs missing tauri_plugin_macos_permissions::init() call"
    )
    # The cfg guard MUST precede the .plugin() call. We assert the two
    # tokens co-occur within a single window so a future refactor that
    # accidentally drops the guard fails the test.
    init_pos = body.find("tauri_plugin_macos_permissions::init")
    window_start = max(0, init_pos - 200)
    window = body[window_start:init_pos]
    assert '#[cfg(target_os = "macos")]' in window, (
        "tauri_plugin_macos_permissions::init() registered without a "
        "#[cfg(target_os = \"macos\")] guard — Windows builds will fail."
    )


def test_capabilities_allowlists_plugin_commands() -> None:
    """capabilities/default.json allowlists macos-permissions namespace
    plus the specific check_*_permission + request_*_permission
    identifiers used by the wizard.

    The plugin splits its check/request commands per system surface
    (accessibility / microphone / screen-recording) — there is no
    generic ``allow-check-permission`` identifier, so we assert the
    three surfaces the wizard actually drives.
    """
    raw = CAPABILITIES.read_text(encoding="utf-8")
    cfg = json.loads(raw)
    perms = cfg.get("permissions", [])
    flat = [p if isinstance(p, str) else p.get("identifier") for p in perms]
    assert "macos-permissions:default" in flat, (
        "capabilities/default.json missing macos-permissions:default"
    )
    for surface in ("accessibility", "microphone", "screen-recording"):
        check_id = f"macos-permissions:allow-check-{surface}-permission"
        request_id = f"macos-permissions:allow-request-{surface}-permission"
        assert check_id in flat, f"capabilities/default.json missing {check_id}"
        assert request_id in flat, f"capabilities/default.json missing {request_id}"
