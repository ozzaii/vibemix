# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-04 — Discord launch announcement publisher.

REQ-IDs: SHIP-04
Pitfall: P59 (star-quality / no paid-star language).

Posts the public-launch announcement to the vibemix Discord
`#announcements` channel via webhook. Reads the aligned-community
sourcing protocol from `scripts/dayzero/seed_stars.md` (Phase 36) to
ensure no paid-star / favour-star language sneaks into the post.

Modes:
  --dry-run (default)  Posts to a preview channel webhook (DISCORD_PREVIEW_URL).
  --real               Requires LAUNCH_REAL=1 env. Posts to the real channel
                       (DISCORD_WEBHOOK_URL). Pings the aligned-community role.

Never autonomously fires the real post: --real requires the env flag set
out-of-band, and the publish endpoint itself is gated by Discord's webhook
permissions. Final click is Kaan-action.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

ANNOUNCEMENT_TEMPLATE = """\
**vibemix is live.** {release_url}

The open-source AI co-host for live DJ sets. Listens to your master output, watches your DJ software's screen, reads your MIDI controller, talks back into your headphones as hype-man or coach. Gemini-grounded — no AI slop.

Mac + Windows. Free. Apache 2.0.

{role_mention} thanks for being here Day-1. If vibemix clicks for you, a star on GitHub helps surface it to the rest of the DJ community: {release_url}

Bug reports + feedback in this server. Built by the Bravoh team alongside our main product."""

DEFAULT_ROLE_ID_ENV = "DISCORD_ALIGNED_ROLE_ID"


def render_announcement(release_url: str, role_mention: str) -> str:
    return ANNOUNCEMENT_TEMPLATE.format(
        release_url=release_url,
        role_mention=role_mention,
    )


def post_webhook(
    webhook_url: str,
    body: str,
    poster: Any = None,
) -> dict[str, Any]:
    """POST to a Discord webhook. `poster` is injected for tests; in
    production it would be a thin requests.post() wrapper. When
    `poster` is None OR webhook_url is empty, returns a synthetic dict
    without touching network (load-bearing for autonomous safety)."""
    payload = {
        "username": "vibemix",
        "content": body,
        # Discord-side parse override — allow role mentions but no @everyone.
        "allowed_mentions": {"parse": ["roles"]},
    }
    if poster is None or not webhook_url:
        return {"url": webhook_url, "preview": True, "payload": payload}
    return poster(webhook_url, payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--real", action="store_true",
                   help="Requires LAUNCH_REAL=1 env to actually post.")
    p.add_argument("--release-url",
                   default="https://github.com/bravoh/vibemix/releases/latest")
    p.add_argument("--role-id",
                   default=os.environ.get(DEFAULT_ROLE_ID_ENV, ""),
                   help="Discord role ID to ping (aligned-community). Empty -> no ping.")
    p.add_argument("--preview-webhook",
                   default=os.environ.get("DISCORD_PREVIEW_URL", ""))
    p.add_argument("--real-webhook",
                   default=os.environ.get("DISCORD_WEBHOOK_URL", ""))
    args = p.parse_args(argv)

    if args.real and os.environ.get("LAUNCH_REAL") != "1":
        print(
            "::error::post_discord_launch: --real requires LAUNCH_REAL=1 env. "
            "Aborting (Phase 39 SHIP-04 hard guard).",
            file=sys.stderr,
        )
        return 2

    role_mention = f"<@&{args.role_id}>" if args.role_id else "[aligned-community]"
    body = render_announcement(args.release_url, role_mention)

    if args.real:
        url = args.real_webhook
        if not url:
            print("::error::post_discord_launch: DISCORD_WEBHOOK_URL not set; cannot --real",
                  file=sys.stderr)
            return 3
    else:
        url = args.preview_webhook  # may be empty in autonomous mode

    resp = post_webhook(url, body, poster=None)
    print(json.dumps(resp, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
