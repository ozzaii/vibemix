# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-04 — post_discord_launch.py tests.

REQ-IDs: SHIP-04
Pitfall: P59 (no paid-star / favour-star language).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "launch" / "post_discord_launch.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "launch"))
import post_discord_launch as pdl  # noqa: E402


def test_script_exists():
    assert SCRIPT.exists()


def test_render_announcement_includes_release_url_and_role():
    body = pdl.render_announcement(
        release_url="https://github.com/bravoh/vibemix",
        role_mention="<@&12345>",
    )
    assert "https://github.com/bravoh/vibemix" in body
    assert "<@&12345>" in body
    assert "vibemix is live" in body.lower()


def test_render_announcement_omits_role_gracefully():
    """Empty role -> placeholder remains, not a malformed mention."""
    body = pdl.render_announcement(
        release_url="https://x.test/y",
        role_mention="[aligned-community]",
    )
    assert "[aligned-community]" in body
    assert "<@&" not in body


def test_dry_run_uses_preview_channel(monkeypatch):
    """Default --dry-run posts to DISCORD_PREVIEW_URL, never to DISCORD_WEBHOOK_URL."""
    monkeypatch.setenv("DISCORD_PREVIEW_URL", "https://discord.example/preview")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/real")
    monkeypatch.delenv("LAUNCH_REAL", raising=False)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, check=False,
        env={**os.environ},
    )
    assert result.returncode == 0
    assert "preview" in result.stdout
    # Real webhook URL MUST NOT appear in the dry-run output payload URL line.
    # (preview is True + url is the preview one.)
    assert "/preview" in result.stdout
    assert "/real" not in result.stdout


def test_real_requires_launch_real_env():
    """--real without LAUNCH_REAL=1 must exit 2."""
    env = os.environ.copy()
    env.pop("LAUNCH_REAL", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--real"],
        capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 2
    assert "LAUNCH_REAL" in (result.stdout + result.stderr)


def test_real_requires_real_webhook_set():
    """--real + LAUNCH_REAL=1 + missing DISCORD_WEBHOOK_URL must exit 3."""
    env = os.environ.copy()
    env["LAUNCH_REAL"] = "1"
    env.pop("DISCORD_WEBHOOK_URL", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--real"],
        capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 3
    assert "DISCORD_WEBHOOK_URL" in (result.stdout + result.stderr)


def test_announcement_pings_aligned_community_role(monkeypatch):
    """When role-id env is set, the announcement contains <@&ROLE_ID>."""
    monkeypatch.setenv(pdl.DEFAULT_ROLE_ID_ENV, "987654321098765432")
    body = pdl.render_announcement(
        release_url="https://x.test",
        role_mention=f"<@&{os.environ[pdl.DEFAULT_ROLE_ID_ENV]}>",
    )
    assert "<@&987654321098765432>" in body


def test_post_webhook_no_op_without_poster():
    """No poster injected -> synthetic dict, NO network."""
    resp = pdl.post_webhook(
        webhook_url="https://example.invalid/x",
        body="hi",
        poster=None,
    )
    assert resp["preview"] is True
    assert resp["payload"]["content"] == "hi"
    # Only roles may be parsed (not @everyone) — defensive default.
    assert resp["payload"]["allowed_mentions"]["parse"] == ["roles"]


def test_p59_no_paid_star_text_in_announcement():
    """P59 — no buy-stars / pay-for-review / star-favour language in
    the announcement body, ever."""
    body = pdl.render_announcement(
        release_url="https://x.test",
        role_mention="<@&1>",
    )
    banned = [
        "buy stars", "pay for review", "paid review",
        "star this as a favour", "star this as a favor",
        "boost stars", "purchase stars", "star-for-star",
    ]
    lower = body.lower()
    for term in banned:
        assert term not in lower, (
            f"announcement contains banned phrase {term!r} (P59)"
        )


def test_static_audit_no_external_api_calls_outside_webhook():
    """Hard rule: the script body must only use Discord webhook POSTs.
    No raw twitter / instagram / reddit / praw / tweepy."""
    body = SCRIPT.read_text(encoding="utf-8")
    forbidden = ["tweepy", "praw", "instagrapi", "facebook_graph"]
    for token in forbidden:
        assert token not in body, (
            f"post_discord_launch.py must not reference {token!r}"
        )


def test_announcement_references_aligned_community_protocol():
    """Per SHIP-04, the announcement copy must align with the
    `scripts/dayzero/seed_stars.md` protocol — value-first, opt-out
    friendly, no favour-language. Static lint here: no "as a favor" /
    "as a favour" phrasing."""
    body = pdl.render_announcement(
        release_url="https://x.test",
        role_mention="<@&1>",
    )
    lower = body.lower()
    assert "as a favor" not in lower
    assert "as a favour" not in lower
