#!/usr/bin/env python3
"""Day-Zero Discord server provisioning for vibemix.

Idempotently scaffolds the `vibemix` Discord server with the agreed role
+ channel layout. By default runs in DRY-RUN: prints the planned actions
without touching Discord. `--live` actually performs the operations and
requires `DISCORD_BOT_TOKEN` in the environment.

The script is autonomous-safe — re-running against a partially or fully
provisioned server is a no-op for the entries that already exist.

Roles    : founder, contributor, DJ, lurker
Channels : #announcements, #help, #show-and-tell, #controllers,
           #ai-misbehavior, #dev

Usage (dry-run, default):
    python scripts/dayzero/discord_provision.py

Usage (live):
    export DISCORD_BOT_TOKEN=<bot-token>
    python scripts/dayzero/discord_provision.py --live --guild-id <id>

The `discord.py` dependency is imported lazily — dry-run mode does NOT
require it.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Target state
# ---------------------------------------------------------------------------

TARGET_ROLES: tuple[str, ...] = ("founder", "contributor", "DJ", "lurker")
TARGET_CHANNELS: tuple[str, ...] = (
    "announcements",
    "help",
    "show-and-tell",
    "controllers",
    "ai-misbehavior",
    "dev",
)
GUILD_NAME: str = "vibemix"


# ---------------------------------------------------------------------------
# Plan diffing
# ---------------------------------------------------------------------------

@dataclass
class ProvisionPlan:
    """The list of ops we would perform against a Guild snapshot."""

    roles_to_create: list[str]
    channels_to_create: list[str]
    roles_existing: list[str]
    channels_existing: list[str]

    def is_noop(self) -> bool:
        return not self.roles_to_create and not self.channels_to_create

    def as_lines(self) -> list[str]:
        lines: list[str] = []
        for r in self.roles_existing:
            lines.append(f"[skip] role exists: {r}")
        for c in self.channels_existing:
            lines.append(f"[skip] channel exists: #{c}")
        for r in self.roles_to_create:
            lines.append(f"[plan] create role {r}")
        for c in self.channels_to_create:
            lines.append(f"[plan] create channel #{c}")
        if self.is_noop():
            lines.append("[plan] no-op — server already fully provisioned")
        return lines


def diff_plan(
    existing_roles: Iterable[str],
    existing_channels: Iterable[str],
) -> ProvisionPlan:
    existing_role_set = {r for r in existing_roles}
    existing_channel_set = {c for c in existing_channels}

    return ProvisionPlan(
        roles_to_create=[r for r in TARGET_ROLES if r not in existing_role_set],
        channels_to_create=[
            c for c in TARGET_CHANNELS if c not in existing_channel_set
        ],
        roles_existing=[r for r in TARGET_ROLES if r in existing_role_set],
        channels_existing=[
            c for c in TARGET_CHANNELS if c in existing_channel_set
        ],
    )


# ---------------------------------------------------------------------------
# Live execution against discord.py (lazy import)
# ---------------------------------------------------------------------------

async def apply_plan_live(plan: ProvisionPlan, guild) -> list[str]:
    """Apply `plan` to a live `discord.Guild` instance.

    Returns the list of executed actions for logging.
    """
    actions: list[str] = []

    for role_name in plan.roles_to_create:
        await guild.create_role(name=role_name)
        actions.append(f"[done] created role {role_name}")

    for channel_name in plan.channels_to_create:
        await guild.create_text_channel(channel_name)
        actions.append(f"[done] created channel #{channel_name}")

    return actions


async def _run_live(token: str, guild_id: int) -> int:
    """Connect to Discord with `discord.py`, diff + apply plan against guild."""
    try:
        import discord  # type: ignore
    except ImportError:
        print(
            "ERROR: discord.py is required for --live mode. "
            "Install with: pip install discord.py",
            file=sys.stderr,
        )
        return 2

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    exit_code = {"code": 0}

    @client.event
    async def on_ready():  # pragma: no cover — network path
        try:
            guild = client.get_guild(guild_id)
            if guild is None:
                guild = await client.fetch_guild(guild_id)

            existing_roles = [r.name for r in guild.roles]
            existing_channels = [c.name for c in guild.channels]
            plan = diff_plan(existing_roles, existing_channels)

            for line in plan.as_lines():
                print(line)

            actions = await apply_plan_live(plan, guild)
            for action in actions:
                print(action)
        except Exception as exc:  # pragma: no cover — network path
            print(f"ERROR: live provision failed: {exc}", file=sys.stderr)
            exit_code["code"] = 1
        finally:
            await client.close()

    await client.start(token)
    return exit_code["code"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="discord_provision.py",
        description=(
            "Idempotently scaffold the vibemix Discord server. "
            "Defaults to dry-run; --live performs real operations."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Actually create roles/channels (requires DISCORD_BOT_TOKEN env)",
    )
    p.add_argument(
        "--guild-id",
        type=int,
        default=None,
        help="Numeric Discord guild ID (required with --live)",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)

    if not args.live:
        # Dry-run: print the plan assuming a fresh server.
        plan = diff_plan(existing_roles=[], existing_channels=[])
        print(f"[plan] guild name target: {GUILD_NAME}")
        for line in plan.as_lines():
            print(line)
        print(
            "[plan] DRY-RUN complete. Re-run with --live and "
            "DISCORD_BOT_TOKEN to apply.",
        )
        return 0

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print(
            "ERROR: DISCORD_BOT_TOKEN env var is required for --live.",
            file=sys.stderr,
        )
        return 2

    if args.guild_id is None:
        print(
            "ERROR: --guild-id is required for --live.",
            file=sys.stderr,
        )
        return 2

    return asyncio.run(_run_live(token, args.guild_id))


if __name__ == "__main__":
    sys.exit(main())
