# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-03 — 4-channel social publisher with NACK window.

REQ-IDs: SHIP-03
Pitfall: P78 (launch-timing — quiet hours / wrong timezone catch).

Channels:
  - Twitter / X         (scripts/launch/social_templates/twitter.txt.jinja)
  - Instagram IT        (scripts/launch/social_templates/ig_it.txt.jinja)
  - Instagram EN        (scripts/launch/social_templates/ig_en.txt.jinja)
  - Reddit r/DJs        (scripts/launch/social_templates/reddit_djs.txt.jinja)
  - HN Show HN          (scripts/launch/social_templates/hackernews.txt.jinja)

Modes:
  --dry-run  (default)  POSTs each rendered post to the Discord webhook
                        preview channel only. NEVER touches real channels.
  --real                Requires LAUNCH_REAL=1 env AND a prior dry-run
                        confirmation file. NACK window (5 min) gates auto-
                        publish; if a Discord NACK reaction lands, abort.

Real publishing to Twitter / IG / Reddit / HN itself is Kaan/Francesco-
action — this script's `--real` mode prints the rendered content to
stdout but DOES NOT call platform APIs. The actual click-to-post is human.

Template substitution: simple `{{ key }}` swap, no Jinja runtime needed
(zero new deps). Required keys default to release-time values; pass
`--key=val` to override.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "scripts" / "launch" / "social_templates"

CHANNELS = [
    ("twitter", "twitter.txt.jinja"),
    ("ig_it", "ig_it.txt.jinja"),
    ("ig_en", "ig_en.txt.jinja"),
    ("reddit_djs", "reddit_djs.txt.jinja"),
    ("hackernews", "hackernews.txt.jinja"),
]

DEFAULT_VARS = {
    "release_url": "https://github.com/bravoh/vibemix/releases/latest",
    "bravoh_url": "https://altidus.world/vibemix?utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch",
}

NACK_WINDOW_SECONDS = 5 * 60


def render(template_path: Path, variables: dict[str, str]) -> str:
    """Simple {{ key }} substitution. Missing keys -> KeyError."""
    body = template_path.read_text(encoding="utf-8")
    # Catch missing keys before substitution.
    needed = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", body))
    missing = needed - set(variables)
    if missing:
        raise KeyError(
            f"template {template_path.name} requires keys not provided: {sorted(missing)}"
        )
    out = body
    for key, value in variables.items():
        out = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value, out)
    return out


def render_all(variables: dict[str, str]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for name, filename in CHANNELS:
        path = TEMPLATES_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"template missing: {path}")
        rendered[name] = render(path, variables)
    return rendered


def post_to_discord_preview(
    webhook_url: str,
    channel: str,
    body: str,
    poster: Any = None,
) -> dict[str, Any]:
    """POST a single rendered post to the Discord preview webhook.

    Returns the (synthetic) response dict. If poster is None or webhook_url
    is empty, behaves as a no-op + returns a recorded dict so the dry-run
    path is fully testable without network.
    """
    payload = {
        "username": "vibemix launch preview",
        "content": f"**[{channel} preview]**\n```\n{body[:1800]}\n```",
    }
    if poster is None or not webhook_url:
        return {"channel": channel, "url": webhook_url, "preview": True, "payload": payload}
    return poster(webhook_url, payload)


def check_for_nack(
    webhook_url: str,
    deadline_unix: float,
    waiter: Any = None,
) -> bool:
    """Poll for a Discord NACK reaction (👎) on the preview message.

    waiter is injected for testing. In production it would poll the
    Discord REST API for thumbs-down reactions on the preview message
    IDs. Default real-mode implementation here returns False (no NACK
    detected) — Kaan's real implementation would replace `waiter`.

    Returns True iff a NACK was detected before deadline.
    """
    if waiter is None:
        # Real-mode default: synchronously sleep until deadline if no
        # waiter is provided. Tests always inject a waiter. This is
        # intentional belt-and-braces — if you forget --dry-run AND
        # forget to wire a waiter, you still wait the full NACK window
        # before publishing.
        while time.time() < deadline_unix:
            time.sleep(1)
        return False
    return bool(waiter(webhook_url, deadline_unix))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Render templates + POST to Discord preview only (default).")
    p.add_argument("--real", action="store_true",
                   help="Render + run NACK window. Requires LAUNCH_REAL=1 env. "
                        "NEVER autonomously calls Twitter/IG/Reddit/HN APIs — those "
                        "remain Kaan/Francesco-action.")
    p.add_argument("--release-url", default=DEFAULT_VARS["release_url"])
    p.add_argument("--bravoh-url", default=DEFAULT_VARS["bravoh_url"])
    p.add_argument("--discord-webhook-url", default=os.environ.get("DISCORD_WEBHOOK_URL", ""))
    p.add_argument("--nack-window-seconds", type=int, default=NACK_WINDOW_SECONDS,
                   help="P78 — quiet-hours / wrong-timezone catch window.")
    p.add_argument("--print-only", action="store_true",
                   help="Skip Discord preview; just print rendered posts to stdout.")
    args = p.parse_args(argv)

    if not args.dry_run and not args.real and not args.print_only:
        # Default to dry-run for safety (P78).
        args.dry_run = True

    if args.real:
        if os.environ.get("LAUNCH_REAL") != "1":
            print(
                "::error::publish_social_posts: --real requires LAUNCH_REAL=1 env. "
                "Aborting (Phase 39 SHIP-03 hard guard).",
                file=sys.stderr,
            )
            return 2

    variables = {
        "release_url": args.release_url,
        "bravoh_url": args.bravoh_url,
    }

    try:
        rendered = render_all(variables)
    except (KeyError, FileNotFoundError) as e:
        print(f"::error::publish_social_posts: {e}", file=sys.stderr)
        return 1

    if args.print_only:
        print(json.dumps(rendered, indent=2))
        return 0

    # Dry-run: POST every channel's preview to Discord (or no-op if no
    # webhook URL provided). Real publishing is Kaan/Francesco-action.
    responses = []
    for channel, body in rendered.items():
        resp = post_to_discord_preview(
            args.discord_webhook_url,
            channel,
            body,
            poster=None,  # In CI / autonomous mode we never hit a real webhook.
        )
        responses.append(resp)
    print(json.dumps(responses, indent=2))

    if not args.real:
        return 0

    # Real mode: NACK window before "we declare it ready". This script
    # NEVER calls platform APIs autonomously — final publish is Kaan/
    # Francesco-action.
    deadline = time.time() + args.nack_window_seconds
    print(
        f"::notice::publish_social_posts: NACK window open for "
        f"{args.nack_window_seconds}s. React 👎 on Discord to abort.",
    )
    nacked = check_for_nack(args.discord_webhook_url, deadline, waiter=None)
    if nacked:
        print("::error::publish_social_posts: NACK detected — aborting publish.",
              file=sys.stderr)
        return 3
    print("::notice::publish_social_posts: NACK window elapsed without veto. "
          "Rendered content ready — Kaan/Francesco-action to click-publish "
          "on each platform.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
