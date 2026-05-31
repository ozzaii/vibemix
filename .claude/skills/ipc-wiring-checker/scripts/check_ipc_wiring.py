#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""check_ipc_wiring.py — both-ends IPC wiring checker for vibemix.

The vibemix shell (TypeScript webview, ``tauri/ui/src/``) and the Python
sidecar (``src/vibemix/``) talk over ONE ws_bus on 127.0.0.1:8765. Every
message type is declared once in ``tauri/ui/src/ipc/messages.schema.json``
(the source of truth, 72 ``const`` types as of this writing). A type is only
a real feature when BOTH ends touch it: a sender on one side and a
consumer/handler on the other. A type wired on only one end is a *dead*
feature — the sidecar emits a frame nobody renders, or the shell sends a
request nobody handles. It ships green (schema parity holds, tsc passes) and
silently does nothing. This script catches that class before it ships.

Detection model (deterministic, stdlib-only, no network, no app launch):

  * Enumerate every ``const`` type from the schema ``definitions``.
  * SHELL end  — scan ``tauri/ui/src/**/*.ts`` (minus generated + tests) for
    the type as a literal. Both forms count: the dotted literal
    (``"ipc.session.mute"``) used by ``emitIpc`` / ``sendIpcRequest`` /
    ``subscribeIpc``, AND the dash-converted event name
    (``ipc-session-mute``) some ``listenTauri`` call-sites use directly
    (``subscribeIpc`` does ``type.replace(/\\./g, "-")`` internally, so its
    callers pass the dotted form — but a raw ``listenTauri`` does not).
  * SIDECAR end — scan ``src/vibemix/**/*.py`` for the dotted literal. This
    covers both ``register_handler("ipc.x.y", ...)`` (inbound handler) and
    the ``ui_bus.messages`` factory constants (outbound emit).
  * RUST     — scan ``tauri/src-tauri/src/**/*.rs`` for the dotted literal.
    Rust is mostly a generic ``forward_ipc_to_sidecar`` passthrough, so a
    missing Rust ref is NOT a fault; it is reported as context only.

A type is DEAD when it is missing from the shell end OR missing from the
sidecar end. Those are the one-ended types; the script exits nonzero when any
exist so a CI gate / pre-commit hook can block the ship.

Staleness: every schema ``const`` type must also appear in the *generated*
``tauri/ui/src/ipc/messages.ts`` (json-schema-to-typescript emits the literal
per type). A schema type absent from ``messages.ts`` means ``npm run
codegen:ipc`` was not re-run after the schema edit — the pre-compiled ajv
validator (``validator.generated.mjs``) is stale and will reject the new
field at runtime. Reported as a hard failure too.

Path roots default relative to the repo root (two levels up from this
script's skill dir); override with ``--repo-root`` for a different checkout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults (relative to repo root). Keep these in sync with the real tree —
# they are verified by the skill's grounding pass, not guessed.
# ---------------------------------------------------------------------------
SCHEMA_REL = "tauri/ui/src/ipc/messages.schema.json"
GENERATED_TS_REL = "tauri/ui/src/ipc/messages.ts"
TS_ROOT_REL = "tauri/ui/src"
PY_ROOT_REL = "src/vibemix"
RUST_ROOT_REL = "tauri/src-tauri/src"

# Substrings that mark a TS path as NOT a real call-site (generated artifacts
# + tests). A type that appears only in a test is not wired in production.
TS_EXCLUDE = (
    "validator.generated",
    "/ipc/messages.ts",  # generated TS types — checked separately for staleness
    ".test.ts",
    ".spec.ts",
    "/__tests__/",
    "/tests/",
)
PY_EXCLUDE = ("__pycache__",)

# Types intentionally declared ahead of their feature. Keep this empty unless a
# reservation has an explicit product owner and package plan; schema-only IPC
# ghosts should be pruned instead.
RESERVED: frozenset[str] = frozenset()


def _repo_root_default() -> Path:
    # scripts/check_ipc_wiring.py -> scripts -> ipc-wiring-checker -> skills
    # -> .claude -> <repo root>
    return Path(__file__).resolve().parents[4]


def enumerate_types(schema_path: Path) -> list[str]:
    """Return every ``const`` message-type string from the schema definitions.

    Two of the ~81 definitions (LevelPair, …) are shared sub-objects with no
    ``type`` const — they are correctly skipped (they are not wire messages).
    """
    schema = json.loads(schema_path.read_text())
    out: list[str] = []
    for d in schema.get("definitions", {}).values():
        const = d.get("properties", {}).get("type", {}).get("const")
        if isinstance(const, str):
            out.append(const)
    return out


def _type_forms(t: str) -> tuple[str, ...]:
    """Literal forms a real call-site may use for a type.

    Dotted-in-quotes (the JSON wire ``type`` field + emitIpc/sendIpcRequest/
    subscribeIpc args) and the dash-converted event name used by raw
    listenTauri call-sites.
    """
    return (f'"{t}"', f"'{t}'", t.replace(".", "-"))


def scan_tree(root: Path, suffix: str, types: list[str], excludes: tuple[str, ...]) -> dict[str, list[str]]:
    """Map type -> list of files under ``root`` matching ``suffix`` that
    reference it as a literal. Skips paths containing any ``excludes``
    substring. Read errors are skipped, never fatal (mirrors the embed-folder
    resilience contract)."""
    forms = {t: _type_forms(t) for t in types}
    hits: dict[str, list[str]] = {}
    if not root.exists():
        return hits
    for p in sorted(root.rglob(f"*{suffix}")):
        sp = str(p)
        if any(x in sp for x in excludes):
            continue
        try:
            txt = p.read_text(errors="ignore")
        except OSError:
            continue
        for t in types:
            if any(f in txt for f in forms[t]):
                hits.setdefault(t, []).append(sp)
    return hits


def scan_generated_ts(generated_ts: Path, types: list[str]) -> set[str]:
    """Return the set of schema types present as a literal in the generated
    messages.ts. A type missing here means codegen:ipc is stale."""
    if not generated_ts.exists():
        return set()
    txt = generated_ts.read_text(errors="ignore")
    return {t for t in types if f'"{t}"' in txt}


def _rel(paths: list[str], repo_root: Path) -> str:
    rels = []
    for p in paths:
        try:
            rels.append(str(Path(p).resolve().relative_to(repo_root)))
        except ValueError:
            rels.append(p)
    return ", ".join(sorted(set(rels)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root_default(),
        help="Repo root (default: inferred from this script's location).",
    )
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()

    schema_path = repo / SCHEMA_REL
    if not schema_path.exists():
        print(f"[ipc-wiring] schema not found: {schema_path}", file=sys.stderr)
        print("  (pass --repo-root <path> if running outside the vibemix tree)", file=sys.stderr)
        return 2

    types = enumerate_types(schema_path)
    ts_hits = scan_tree(repo / TS_ROOT_REL, ".ts", types, TS_EXCLUDE)
    py_hits = scan_tree(repo / PY_ROOT_REL, ".py", types, PY_EXCLUDE)
    rust_hits = scan_tree(repo / RUST_ROOT_REL, ".rs", types, ())
    generated = scan_generated_ts(repo / GENERATED_TS_REL, types)

    # --- One-ended types (missing shell OR sidecar reference). RESERVED types
    # are partitioned out as informational; the rest are real dead features. ---
    dead: list[tuple[str, str]] = []
    reserved: list[tuple[str, str]] = []
    for t in types:
        in_ts = t in ts_hits
        in_py = t in py_hits
        if in_ts and in_py:
            continue
        if not in_ts and not in_py:
            why = "ORPHANED — no shell ref AND no sidecar ref (schema-only)"
        elif not in_ts:
            why = "no SHELL ref (sidecar emits/handles a type the webview never sends or consumes)"
        else:
            why = "no SIDECAR ref (shell sends/subscribes a type the sidecar never emits or handles)"
        (reserved if t in RESERVED else dead).append((t, why))

    stale = [t for t in types if t not in generated]

    # --- Report --------------------------------------------------------------
    print(f"IPC wiring check — {len(types)} message types declared in {SCHEMA_REL}")
    print(f"  shell (tauri/ui/src):   {len(ts_hits)} wired")
    print(f"  sidecar (src/vibemix):  {len(py_hits)} wired")
    print(f"  rust (passthrough ctx): {len(rust_hits)} referenced")
    print()

    if stale:
        print(f"STALE CODEGEN — {len(stale)} type(s) missing from generated {GENERATED_TS_REL}:")
        for t in stale:
            print(f"  - {t}")
        print("  -> run `cd tauri/ui && npm run codegen:ipc` (pre-compiled ajv validator is stale).")
        print()

    if reserved:
        print(f"RESERVED — {len(reserved)} type(s) declared ahead of feature (informational, not a failure):")
        for t, why in reserved:
            print(f"  - {t}: {why}")
        print()

    if dead:
        print(f"DEAD / ONE-ENDED — {len(dead)} type(s):")
        for t, why in dead:
            print(f"  - {t}: {why}")
            if t in ts_hits:
                print(f"      shell:   {_rel(ts_hits[t], repo)}")
            if t in py_hits:
                print(f"      sidecar: {_rel(py_hits[t], repo)}")
            if t in rust_hits:
                print(f"      rust:    {_rel(rust_hits[t], repo)}")
        print()
        print("  A one-ended type is a silent dead feature: it passes schema parity + tsc but")
        print("  does nothing live. Wire the missing end, or drop the type from the schema if")
        print("  it is intentionally future-reserved.")
    else:
        print("OK — every type has both a shell and a sidecar reference.")

    return 1 if (dead or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
