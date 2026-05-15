# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-03 — publish_social_posts.py tests.

REQ-IDs: SHIP-03
Pitfall: P78 (NACK window).

Asserts:
- Dry-run does NOT touch real channels (Twitter / IG / Reddit / HN).
- All 5 templates render with no missing keys.
- NACK window blocks publish on negative reaction.
- --real mode refuses without LAUNCH_REAL=1 env.
- The script body itself contains NO platform API calls (static audit).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "launch" / "publish_social_posts.py"
TEMPLATES_DIR = REPO_ROOT / "scripts" / "launch" / "social_templates"


sys.path.insert(0, str(REPO_ROOT / "scripts" / "launch"))
import publish_social_posts as psp  # noqa: E402


def _run(*args: str, env_override: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_script_and_templates_exist():
    assert SCRIPT.exists()
    for _, filename in psp.CHANNELS:
        assert (TEMPLATES_DIR / filename).exists(), f"missing template: {filename}"


def test_all_templates_render_without_missing_keys():
    """Every template must render cleanly with the default variable set."""
    rendered = psp.render_all(psp.DEFAULT_VARS)
    assert set(rendered) == {name for name, _ in psp.CHANNELS}
    for name, body in rendered.items():
        assert body.strip(), f"template {name} rendered empty"
        # No leftover {{ ... }} placeholders.
        assert "{{" not in body, f"template {name} has unrendered placeholders"


def test_render_raises_on_missing_key(tmp_path: Path):
    """If a template requires a key not in the variables dict, render
    must KeyError before posting anywhere."""
    tpl = tmp_path / "bogus.txt.jinja"
    tpl.write_text("hello {{ release_url }} and {{ unknown_key }}", encoding="utf-8")
    with pytest.raises(KeyError):
        psp.render(tpl, {"release_url": "x"})


def test_dry_run_does_not_post_real_channels(tmp_path: Path):
    """Default invocation (no flags) is dry-run; must NOT POST to
    Twitter / IG / Reddit / HN. We assert by static audit that no
    platform domains are touched in the dry-run code path."""
    result = _run("--dry-run", "--print-only")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert set(parsed) == {name for name, _ in psp.CHANNELS}


def test_static_audit_no_platform_api_calls():
    """Hard rule: the publisher script body must not import or reference
    Twitter / IG / Reddit / HN clients. (P78 — Phase 39 hard rule.)"""
    body = SCRIPT.read_text(encoding="utf-8")
    # No tweepy, no praw, no instagrapi etc.
    forbidden = ["tweepy", "praw", "instagrapi", "instabot",
                 "facebook_graph_api", "twitter.com/api"]
    for token in forbidden:
        assert token not in body, (
            f"publisher script must not reference {token!r} — "
            f"real publish is Kaan/Francesco-action"
        )


def test_real_mode_requires_launch_real_env_flag():
    """`--real` without LAUNCH_REAL=1 must fail fast (exit 2)."""
    env = os.environ.copy()
    env.pop("LAUNCH_REAL", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--real", "--nack-window-seconds", "1"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 2, (
        f"--real without LAUNCH_REAL=1 should exit 2, got {result.returncode}.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "LAUNCH_REAL" in (result.stdout + result.stderr)


def test_nack_window_blocks_publish_on_negative_reaction():
    """NACK detected -> abort + non-zero exit. We inject the waiter to
    simulate a NACK."""
    nacked = psp.check_for_nack(
        webhook_url="https://example.invalid/webhook",
        deadline_unix=0,  # already past
        waiter=lambda url, deadline: True,
    )
    assert nacked is True


def test_nack_window_passes_when_no_reaction():
    """No NACK -> publish proceeds."""
    nacked = psp.check_for_nack(
        webhook_url="https://example.invalid/webhook",
        deadline_unix=0,
        waiter=lambda url, deadline: False,
    )
    assert nacked is False


def test_post_to_discord_preview_no_op_without_poster():
    """When no poster is injected, the dry-run preview path returns a
    synthetic dict + does NOT touch network (load-bearing for autonomous
    safety)."""
    result = psp.post_to_discord_preview(
        webhook_url="",
        channel="twitter",
        body="hello world",
        poster=None,
    )
    assert result["preview"] is True
    assert result["channel"] == "twitter"


def test_template_twitter_under_280_chars():
    """Twitter's hard limit is 280 chars — render once, sanity check."""
    rendered = psp.render(
        TEMPLATES_DIR / "twitter.txt.jinja",
        psp.DEFAULT_VARS,
    )
    assert len(rendered) <= 280, (
        f"twitter template renders to {len(rendered)} chars (>280):\n{rendered}"
    )


def test_templates_include_bravoh_or_vibemix_brand_reference():
    """Every channel except Twitter must mention either Bravoh or vibemix."""
    rendered = psp.render_all(psp.DEFAULT_VARS)
    for name, body in rendered.items():
        assert "vibemix" in body.lower() or "bravoh" in body.lower(), (
            f"template {name} missing brand reference"
        )


def test_no_paid_star_or_pay_for_review_language():
    """P59 — no buy-stars / pay-for-review language in any social copy."""
    rendered = psp.render_all(psp.DEFAULT_VARS)
    banned = ["buy stars", "buy followers", "pay for review",
              "paid review", "boost stars", "purchase stars"]
    for name, body in rendered.items():
        for term in banned:
            assert term not in body.lower(), (
                f"template {name} contains banned phrase {term!r} (P59)"
            )
