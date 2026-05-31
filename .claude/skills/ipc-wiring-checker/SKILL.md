---
name: ipc-wiring-checker
description: Verifies BOTH ends of a vibemix IPC message type are wired — sender on one side, handler/consumer on the other — so a one-ended "dead" type never ships as a silent dead feature. Trigger BEFORE shipping any edit to tauri/ui/src/ipc/messages.schema.json, when adding/removing/renaming an ipc.* message type, when wiring a new control end-to-end (button → emitIpc → register_handler → response), or when hunting a control/panel that looks dead or unresponsive ("button does nothing", "panel stays blank", "no reaction on the wire"). Also trigger when a PR or plan touches the ws_bus, register_handler, emitIpc/sendIpcRequest/subscribeIpc, or the codegen:ipc pipeline.
metadata:
  trigger: Editing messages.schema.json, adding/removing/renaming an ipc.* type, wiring a control end-to-end, debugging a dead/unresponsive control
---

# vibemix — IPC Wiring Checker

The shell (TypeScript webview, `tauri/ui/src/`) and the Python sidecar
(`src/vibemix/`) talk over ONE ws_bus on `127.0.0.1:8765`. Every message type
is declared once in `tauri/ui/src/ipc/messages.schema.json` (72 `const` types
today). A type is a real feature only when BOTH ends touch it: a sender on one
side, a consumer/handler on the other.

A type wired on only ONE end is a **dead feature**. The sidecar emits a frame
nobody renders, or the shell sends a request nobody handles. It ships green —
schema parity holds, `tsc` passes, every test is happy — and does nothing
live. That is the exact bug behind every "button does nothing" / "panel stays
blank" report in this repo. This skill catches it deterministically.

## When to run this

- You edited `messages.schema.json` (added, removed, or renamed a type).
- You wired a new control: pill/button → `emitIpc("ipc.x.y", ...)` → Python
  `register_handler("ipc.x.y", ...)` → response the shell subscribes to.
- A control or panel looks dead and you suspect one end was never wired.
- A PR/plan touches `ws_bus.py`, `register_handler`, `emitIpc` /
  `sendIpcRequest` / `subscribeIpc`, or `codegen-ipc.mjs`.

## Run it

```bash
uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
```

Stdlib-only, no network, no app launch (it never binds 8765 — it reads
source). It infers the repo root from its own location; pass
`--repo-root <path>` to point at a different checkout. Exits nonzero when any
dead or stale type exists, so it drops straight into a pre-commit hook or CI
gate.

## How it decides (read the report this way)

For each `const` type in the schema it scans three trees for the type as a
**literal** string:

- **shell** — `tauri/ui/src/**/*.ts` (minus generated + tests). Both forms
  count: the dotted literal `"ipc.session.mute"` (what `emitIpc` /
  `sendIpcRequest` / `subscribeIpc` callers pass) and the dash-converted event
  name `ipc-session-mute` (what a raw `listenTauri` call-site uses — note
  `subscribeIpc` does the `.`→`-` swap internally, so ITS callers still pass
  the dotted form).
- **sidecar** — `src/vibemix/**/*.py`. Covers both
  `register_handler("ipc.x.y", ...)` (inbound handler) and the
  `ui_bus/messages.py` + `ui_bus/learn_messages.py` factory constants
  (outbound emit).
- **rust** — `tauri/src-tauri/src/**/*.rs`. Rust is mostly a generic
  `forward_ipc_to_sidecar` passthrough, so a missing Rust ref is **context
  only, not a fault**. A handful of types (`ipc.session.snapshot`,
  `ipc.session.mute`, `ipc.learn.ack`, `ipc.learn.tutor_speak`) have a
  dedicated Rust command — the report lists Rust refs when present.

A type is reported **DEAD / ONE-ENDED** when it is missing from the shell tree
OR the sidecar tree. The report names the side that IS wired and its file(s),
so you go straight to the missing end.

> The check is presence-of-literal, not full dataflow. It cannot prove the
> handler does the right thing — it proves a handler/sender *exists*. That is
> the cheap, high-signal half: a type with zero references on one end is dead
> with certainty; a type with references on both ends is worth a 30-second
> manual read. It deliberately does NOT chase types referenced only via a TS
> type-name (`subscribeIpc<SessionCitation>`) without the literal — in this
> codebase the literal is always present at a real call-site, so a literal-only
> scan has no false negatives and no false "it's fine" passes.

## Stale codegen (the second failure mode)

After you edit the schema you MUST regenerate the TS types + the pre-compiled
ajv validator:

```bash
cd tauri/ui && npm run codegen:ipc
```

`validator.generated.mjs` is **pre-compiled** (the production webview ships
under a Tauri CSP with no `unsafe-eval`, so ajv cannot `.compile()` at
runtime). A stale validator silently rejects your new field at runtime — the
frame never reaches the handler, and it looks exactly like a dead type. The
checker flags this: every schema `const` type must appear as a literal in the
generated `tauri/ui/src/ipc/messages.ts`. A type missing there means
`codegen:ipc` was not re-run. Fix it before anything else — a stale validator
poisons every downstream wiring read.

## What a clean vs. dirty run looks like

Dirty (example — a sidecar-only type is emitted but the shell never subscribes):

```
DEAD / ONE-ENDED — 1 type(s):
  - ipc.example.missing_shell: no SHELL ref (sidecar emits/handles a type the webview never sends or consumes)
      sidecar: src/vibemix/ui_bus/messages.py
```

Each line is a decision: either wire the missing end, or — if the type is
intentionally future-reserved — drop it from the schema until you wire it. Do
not leave it half-wired; that is the dead-feature trap.

Clean:

```
OK — every type has both a shell and a sidecar reference.
```

## After you fix wiring

1. Re-run the checker until the type you touched is no longer listed.
2. If you edited the schema: `cd tauri/ui && npm run codegen:ipc`, then
   `npm run build && npm test`.
3. The sister CI gate `scripts/check_ipc_schema.py` (count parity + per-wrapper
   roundtrip) catches "schema added without a Python wrapper" — run it too:
   `PYTHONPATH=src python3 scripts/check_ipc_schema.py`. This skill catches the
   layer that one misses: a wrapper exists on both ends of the *schema* but no
   call-site actually sends or consumes it.

## Why this exists

PROJECT.md's bar is "real DJ friend in your ear, no AI slop" — and half of
that promise is the UI doing what it claims. A control that emits a frame into
the void, or a sidecar that ships a panel nobody renders, breaks the promise
silently. Schema parity + green tests do not catch a one-ended type. This does.
