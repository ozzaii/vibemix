#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""PostToolUse guard — regenerate the IPC validator when the IPC schema changes.

Editing ``tauri/ui/src/ipc/messages.schema.json`` without re-running
``npm run codegen:ipc`` leaves the PRE-COMPILED ajv validator
(``validator.generated.mjs``) stale — it then silently rejects the new field at
runtime (the documented stale-validator class). This hook closes that gap: on
any Edit/Write whose file_path is the IPC schema, it regenerates the validator.

Fail-soft by contract: a PostToolUse hook runs AFTER the edit already landed, so
a failure here must NEVER block editing — every path returns 0 and swallows
errors to stderr only.

Wired in ``.claude/settings.json`` as a PostToolUse(Edit|Write|MultiEdit)
command. Set ``VIBEMIX_HOOK_DRYRUN=1`` to print the intended action without
running codegen (used by the hook's own standalone test).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # no/invalid hook payload → nothing to do
    fp = str((data.get("tool_input") or {}).get("file_path") or "")
    if not fp.endswith("messages.schema.json"):
        return 0  # not the IPC schema → no-op (the common case, kept fast)

    repo = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ui_dir = os.path.join(repo, "tauri", "ui")

    if os.environ.get("VIBEMIX_HOOK_DRYRUN") == "1":
        print(f"[post-edit] WOULD run codegen:ipc in {ui_dir} (IPC schema changed)", file=sys.stderr)
        return 0

    try:
        subprocess.run(
            ["npm", "run", "codegen:ipc"],
            cwd=ui_dir,
            capture_output=True,
            timeout=120,
        )
        print("[post-edit] regenerated IPC validator (codegen:ipc) — schema changed", file=sys.stderr)
    except Exception as exc:  # fail-soft: never wedge the editing flow
        print(f"[post-edit] codegen:ipc skipped ({exc!r})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
