# SPDX-License-Identifier: Apache-2.0
"""tests/dayzero/test_discord_provision_dryrun.py — LAUNCH-08 dry-run lock.

Plan 44-06 pins the Discord provisioning behaviour required by
LAUNCH-08:

  - `scripts/dayzero/discord_taxonomy.json` is the single source of
    truth for roles + channels + guild name. JSON is parseable, carries
    the canonical merged taxonomy (5 roles + 9 channels per CONTEXT
    §LAUNCH-08, MERGED with the existing Phase 36-era in-script set so
    nothing regresses).
  - `discord_provision.py` consumes the JSON at module load — there is
    no second source of truth for `TARGET_ROLES` / `TARGET_CHANNELS`.
  - Default CLI run is dry-run: no Discord SDK import, no network
    calls, prints the plan for the full taxonomy.
  - Bot-token env var is read with the new Bravoh-naming convention
    (`BRAVOH_DISCORD_BOT_TOKEN`) preferred over the legacy
    (`DISCORD_BOT_TOKEN`) for back-compat. Both rejected → exit 2.

The test deliberately overlaps a little with the existing
`test_discord_provision.py` so failures in either surface point at the
same root cause; the duplication is cheap and makes the LAUNCH-08
contract grep-discoverable on its own.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dayzero" / "discord_provision.py"
TAXONOMY = ROOT / "scripts" / "dayzero" / "discord_taxonomy.json"


# Canonical merged taxonomy (must match PLAN 44-06 must-have truths).
EXPECTED_ROLES = {"founder", "contributor", "DJ", "lurker", "moderator"}
EXPECTED_CHANNELS = {
    "announcements",
    "general",
    "help",
    "show-and-tell",
    "controllers",
    "ai-misbehavior",
    "dev",
    "bugs",
    "showcase",
}


def _load_module():
    """Fresh module load — avoids state bleed between tests that
    monkey-patch the import system."""
    spec = importlib.util.spec_from_file_location(
        "discord_provision_dryrun", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["discord_provision_dryrun"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------
# Taxonomy JSON contract
# ---------------------------------------------------------------------


def test_taxonomy_json_exists_and_is_parseable():
    """LAUNCH-08: single source of truth must ship as parseable JSON."""
    assert TAXONOMY.exists(), f"missing taxonomy file: {TAXONOMY}"
    data = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert set(data.keys()) >= {"roles", "channels", "guild_name"}


def test_taxonomy_json_carries_merged_canonical_set():
    """5 roles + 9 channels merged-canonical per Plan 44-06."""
    data = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    assert set(data["roles"]) == EXPECTED_ROLES, (
        f"roles drift: {sorted(data['roles'])} vs {sorted(EXPECTED_ROLES)}"
    )
    assert set(data["channels"]) == EXPECTED_CHANNELS, (
        f"channels drift: {sorted(data['channels'])} vs "
        f"{sorted(EXPECTED_CHANNELS)}"
    )
    assert len(data["roles"]) == 5
    assert len(data["channels"]) == 9
    assert data["guild_name"] == "vibemix"


# ---------------------------------------------------------------------
# Provision script consumes taxonomy.json
# ---------------------------------------------------------------------


def test_provision_script_loads_taxonomy_from_json():
    """`TARGET_ROLES` / `TARGET_CHANNELS` come from the JSON, not from
    hard-coded module-level tuples — single source of truth contract."""
    mod = _load_module()
    assert set(mod.TARGET_ROLES) == EXPECTED_ROLES
    assert set(mod.TARGET_CHANNELS) == EXPECTED_CHANNELS
    assert mod.GUILD_NAME == "vibemix"


def test_provision_script_taxonomy_path_is_relative_to_script():
    """The script must compute the taxonomy path from `__file__`, not
    from CWD — otherwise running from a different directory breaks."""
    mod = _load_module()
    # Must expose the resolved path for diagnostics.
    assert hasattr(mod, "TAXONOMY_PATH"), (
        "script must expose TAXONOMY_PATH for diagnostics"
    )
    assert pathlib.Path(mod.TAXONOMY_PATH).resolve() == TAXONOMY.resolve()


# ---------------------------------------------------------------------
# Dry-run is default + zero-network
# ---------------------------------------------------------------------


def test_dry_run_is_default_cli_path():
    """No CLI args → dry-run, exit 0, prints all 5 roles + 9 channels."""
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "[plan]" in out
    assert "DRY-RUN complete" in out
    # All roles present in the printed plan.
    for role in EXPECTED_ROLES:
        assert role in out, f"missing role in dry-run output: {role}"
    # All channels present in the printed plan.
    for channel in EXPECTED_CHANNELS:
        assert f"#{channel}" in out, (
            f"missing channel in dry-run output: #{channel}"
        )
    # Dry-run NEVER emits live "[done]" markers.
    assert "[done]" not in out


def test_dry_run_does_not_import_discord_sdk():
    """Dry-run path must not even attempt `import discord` — the SDK is
    an optional dep, dry-run on a fresh checkout (no `pip install
    discord.py`) must succeed.

    We assert by spawning a fresh Python process with `discord` blocked
    via a sitecustomize import hook injected into PYTHONPATH. If the
    script tries to import `discord` the spawn fails and we see the
    sentinel string in stderr.
    """
    blocker_dir = ROOT / "tests" / "dayzero" / "_discord_blocker"
    blocker_dir.mkdir(parents=True, exist_ok=True)
    (blocker_dir / "sitecustomize.py").write_text(
        "import sys\n"
        "class _Blocker:\n"
        "    def find_module(self, name, path=None):\n"
        "        if name == 'discord' or name.startswith('discord.'):\n"
        "            return self\n"
        "        return None\n"
        "    def load_module(self, name):\n"
        "        raise ImportError(\n"
        "            'DISCORD_SDK_IMPORT_BLOCKED_BY_DRYRUN_TEST'\n"
        "        )\n"
        "sys.meta_path.insert(0, _Blocker())\n",
        encoding="utf-8",
    )

    env = {
        **{k: v for k, v in os.environ.items() if k != "DISCORD_BOT_TOKEN"},
        "PYTHONPATH": f"{blocker_dir}{os.pathsep}{ROOT}",
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, (
        "dry-run must succeed without discord SDK\n"
        f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    )
    assert "DISCORD_SDK_IMPORT_BLOCKED_BY_DRYRUN_TEST" not in proc.stderr, (
        "dry-run attempted to import discord SDK — leaks live deps\n"
        f"stderr: {proc.stderr}"
    )


def test_dry_run_makes_zero_network_calls():
    """Mock-style: spawn dry-run with `http_proxy=invalid://` + `no_proxy=`
    cleared so any accidental HTTP attempt would surface (httpx, requests,
    aiohttp all respect these). The script must still exit 0 because
    dry-run is pure local computation."""
    env = {
        **{
            k: v
            for k, v in os.environ.items()
            if k
            not in ("DISCORD_BOT_TOKEN", "http_proxy", "https_proxy", "no_proxy")
        },
        "PYTHONPATH": str(ROOT),
        # Any network attempt routes through this invalid proxy and fails.
        # If the script were calling out to Discord, exit code would be
        # non-zero and stderr would carry the connection error.
        "http_proxy": "http://127.0.0.1:1",
        "https_proxy": "http://127.0.0.1:1",
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 0, (
        "dry-run failed under blocked-network env (network leak suspected)\n"
        f"stderr: {proc.stderr}"
    )
    # Surface marker for the LAUNCH-08 audit log.
    assert "DRY-RUN complete" in proc.stdout


# ---------------------------------------------------------------------
# Bot-token env var preference
# ---------------------------------------------------------------------


def test_live_prefers_bravoh_discord_bot_token():
    """When BOTH env vars set, BRAVOH_DISCORD_BOT_TOKEN wins."""
    env = {
        **{
            k: v
            for k, v in os.environ.items()
            if k not in ("DISCORD_BOT_TOKEN", "BRAVOH_DISCORD_BOT_TOKEN")
        },
        "PYTHONPATH": str(ROOT),
        "BRAVOH_DISCORD_BOT_TOKEN": "bravoh-token-sentinel",
        "DISCORD_BOT_TOKEN": "legacy-token-sentinel",
        # Diagnostic: the script in --live without a valid token will
        # still attempt discord.py import — we want it to print the
        # token-source diagnostic FIRST (before SDK import) so we can
        # assert which token was picked.
        "DISCORD_PROVISION_DIAG_TOKEN_SOURCE": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--live", "--guild-id", "1"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    # We don't care about exit code (no SDK / invalid token → 1 or 2);
    # we care that the diagnostic line names the BRAVOH var.
    combined = proc.stdout + proc.stderr
    assert "BRAVOH_DISCORD_BOT_TOKEN" in combined, (
        "live mode did not surface BRAVOH_DISCORD_BOT_TOKEN as the source\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


def test_live_falls_back_to_legacy_discord_bot_token():
    """BRAVOH var unset, DISCORD_BOT_TOKEN set → script still picks the
    legacy var (back-compat with prior Phase 36 deployment scripts)."""
    env = {
        **{
            k: v
            for k, v in os.environ.items()
            if k not in ("DISCORD_BOT_TOKEN", "BRAVOH_DISCORD_BOT_TOKEN")
        },
        "PYTHONPATH": str(ROOT),
        "DISCORD_BOT_TOKEN": "legacy-token-sentinel",
        "DISCORD_PROVISION_DIAG_TOKEN_SOURCE": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--live", "--guild-id", "1"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    combined = proc.stdout + proc.stderr
    assert "DISCORD_BOT_TOKEN" in combined, (
        "live mode did not surface DISCORD_BOT_TOKEN fallback\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


def test_live_rejects_when_no_token_in_either_var():
    """No tokens set → exit 2 + error message names the preferred var."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DISCORD_BOT_TOKEN", "BRAVOH_DISCORD_BOT_TOKEN")
    }
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--live", "--guild-id", "1"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2, (
        f"expected exit 2, got {proc.returncode}\nstderr: {proc.stderr}"
    )
    # Error message names BRAVOH var (the preferred one).
    assert "BRAVOH_DISCORD_BOT_TOKEN" in proc.stderr
