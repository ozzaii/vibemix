#!/usr/bin/env python3
"""Phase 47 / MASCOT-08 — Anti-slop blocklist scan for Phase 47 docs + manifests.

Sibling to scripts/launch/check_no_ai_slop.py (which scans launch-copy/).
Reuses the same AI_SLOP_BLOCKLIST and the `\\bdeeply\\s+\\w+` regex but
points at the Phase 47 artifact paths.

Targets:
  - docs/mascot/README.md
  - docs/mascot/BUNDLE-DECISION.md
  - scripts/mascot/MIXAMO-CLIP-SOURCES.md
  - assets/mascot/source/MANIFEST.yaml
  - tauri/ui/src/mascot/event-dispatcher.ts
  - tauri/ui/src/mascot/persona-smoke-harness.ts
  - tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md

Exit codes:
  0 — all targets pass the gate
  1 — at least one target hit the blocklist
"""
from __future__ import annotations
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_SCRIPT = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"

PHASE_47_TARGETS = [
    "docs/mascot/README.md",
    "docs/mascot/BUNDLE-DECISION.md",
    "scripts/mascot/MIXAMO-CLIP-SOURCES.md",
    "assets/mascot/source/MANIFEST.yaml",
    "tauri/ui/src/mascot/event-dispatcher.ts",
    "tauri/ui/src/mascot/persona-smoke-harness.ts",
    "tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md",
]

DEEPLY_REGEX = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _import_blocklist() -> tuple[str, ...]:
    """Pull AI_SLOP_BLOCKLIST from the canonical launch-side script."""
    if not LAUNCH_SCRIPT.is_file():
        # Fallback to literal copy if the canonical script is missing.
        return (
            "leverage",
            "synergize",
            "revolutionize",
            "game-changer",
            "next-generation",
            "cutting-edge",
            "seamless",
            "robust",
            "powerful",
            "intuitive",
            "delightful experience",
            "AI-powered",
            "harness the power",
            "unlock",
            "transformative",
            "paradigm",
        )
    spec = importlib.util.spec_from_file_location(
        "_launch_slop", LAUNCH_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {LAUNCH_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return tuple(mod.AI_SLOP_BLOCKLIST)


def main() -> int:
    blocklist = _import_blocklist()
    errors: list[str] = []

    for rel in PHASE_47_TARGETS:
        path = REPO_ROOT / rel
        if not path.is_file():
            # File missing isn't a slop violation; sibling tests check existence.
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text_lower = text.lower()
        for token in blocklist:
            if token.lower() in text_lower:
                errors.append(f"  {rel}: contains blocklisted token '{token}'")
        if DEEPLY_REGEX.search(text):
            errors.append(f"  {rel}: contains 'deeply <word>' adverb-slop pattern")

    if errors:
        print("Phase 47 anti-slop gate FAIL:")
        for e in errors:
            print(e)
        return 1

    print(
        f"OK: {len(PHASE_47_TARGETS)} Phase 47 targets, {len(blocklist)} blocklist tokens, all clean"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
