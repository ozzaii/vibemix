"""Tests for `scripts/dayzero/discord_provision.py`.

Discord SDK is never imported by these tests — we exercise the plan-diff
function (which is the part that holds the idempotency contract) and the
CLI dry-run path (the autonomous-mode default).
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
from typing import Iterable

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dayzero" / "discord_provision.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "discord_provision", SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec is not None and spec.loader is not None
    # `dataclasses` resolves annotations via sys.modules; register module before exec.
    sys.modules["discord_provision"] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_target_state_matches_requirements():
    """LAUNCH-08 contract: 5 roles + 9 channels per discord_taxonomy.json
    (merged from CONTEXT §LAUNCH-08 + Phase 36 in-script set — see
    `tests/dayzero/test_discord_provision_dryrun.py` for the merge
    resolution and the canonical lock)."""
    mod = _load_module()
    assert set(mod.TARGET_ROLES) == {
        "founder",
        "contributor",
        "DJ",
        "lurker",
        "moderator",
    }
    assert set(mod.TARGET_CHANNELS) == {
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


def test_discord_provision_idempotent_when_all_exist():
    """Existing roles + channels => no-op plan, no create calls implied."""
    mod = _load_module()
    plan = mod.diff_plan(
        existing_roles=list(mod.TARGET_ROLES),
        existing_channels=list(mod.TARGET_CHANNELS),
    )
    assert plan.is_noop() is True
    assert plan.roles_to_create == []
    assert plan.channels_to_create == []


def test_discord_provision_idempotent_partial():
    """Partial existing state => only missing entries planned."""
    mod = _load_module()
    plan = mod.diff_plan(
        existing_roles=["founder"],
        existing_channels=["announcements"],
    )
    # founder skipped; rest planned (post-LAUNCH-08 merged taxonomy:
    # 5 roles total → 4 remaining after founder skip).
    assert "founder" not in plan.roles_to_create
    assert "founder" in plan.roles_existing
    assert set(plan.roles_to_create) == {
        "contributor",
        "DJ",
        "lurker",
        "moderator",
    }

    assert "announcements" not in plan.channels_to_create
    assert "announcements" in plan.channels_existing
    assert "help" in plan.channels_to_create


def test_discord_provision_plan_from_empty_creates_everything():
    """Cold-start: every role + channel planned."""
    mod = _load_module()
    plan = mod.diff_plan(existing_roles=[], existing_channels=[])
    assert set(plan.roles_to_create) == set(mod.TARGET_ROLES)
    assert set(plan.channels_to_create) == set(mod.TARGET_CHANNELS)
    assert plan.is_noop() is False


def test_discord_provision_dry_run_default_cli():
    """No args => dry-run path; never touches Discord SDK."""
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "[plan]" in proc.stdout
    assert "DRY-RUN complete" in proc.stdout
    # Sanity: dry-run does NOT emit any "[done]" lines (those are live-only).
    assert "[done]" not in proc.stdout


def test_discord_provision_token_env_required_for_live():
    """--live without BRAVOH_DISCORD_BOT_TOKEN (or legacy
    DISCORD_BOT_TOKEN) must exit 2."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DISCORD_BOT_TOKEN", "BRAVOH_DISCORD_BOT_TOKEN")
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--live", "--guild-id", "123"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2
    # New error message names BRAVOH var first (preferred), legacy second.
    assert "BRAVOH_DISCORD_BOT_TOKEN" in proc.stderr
    assert "DISCORD_BOT_TOKEN" in proc.stderr


def test_apply_plan_live_calls_only_missing_entries(monkeypatch):
    """Mock guild that already has founder + #announcements;
    assert create_role / create_text_channel called only for the rest."""
    mod = _load_module()

    create_role_calls: list[str] = []
    create_channel_calls: list[str] = []

    class FakeGuild:
        async def create_role(self, name):
            create_role_calls.append(name)

        async def create_text_channel(self, name):
            create_channel_calls.append(name)

    plan = mod.diff_plan(
        existing_roles=["founder"],
        existing_channels=["announcements"],
    )

    import asyncio
    actions = asyncio.run(mod.apply_plan_live(plan, FakeGuild()))

    assert "founder" not in create_role_calls
    assert set(create_role_calls) == {
        "contributor",
        "DJ",
        "lurker",
        "moderator",
    }

    assert "announcements" not in create_channel_calls
    assert set(create_channel_calls) == {
        "general",
        "help",
        "show-and-tell",
        "controllers",
        "ai-misbehavior",
        "dev",
        "bugs",
        "showcase",
    }
    assert any("[done]" in a for a in actions)
