# CODEX_READY: Library UI Live Read Context

Date: 2026-06-01
Author: Codex
Status: LAND packet, Viber live-read UI slice
Package: Package 5 - Library UI Live Read Context

## Decision

LAND this slice as `feat(library-ui): ground Viber live reads with deck-pair context`.

The library/Viber webview now treats live context as a proof-bearing object, not
as loose audio ambience. It normalizes deck identity, mixer posture, source
status, audio-window labels, deck-pair capture descriptors, move evidence, and
live-verification receipts before sending context to `library_chat`. The UI also
shows whether the live read is waiting, partial, or armed, so Viber does not
silently receive stale or unsupported live claims.

This packet proves the source/UI contract. A real running-app deck-pair read
with current FLX4/Rekordbox/BlackHole state remains a later live proof.

## Files

- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/api.test.ts`
- `tauri/ui/src/library/chat.test.ts`

Supporting proof only, not a Package 5 staging file:

- `tests/library/test_live_context_cli.py`

## What Changed

- `api.ts` expands `LibraryLiveContext` with schema/capability metadata,
  deck-source status, deck-pair audio descriptors, audio-window maps,
  structured live evidence, recent moves, and live-verification receipts.
- `api.ts` normalizes live context defensively: malformed or overclaiming
  deck/audio strings are dropped, untrusted deck fields are stripped, evidence
  tokens are bounded/deduplicated, and generated evidence is derived only from
  normalized deck state and mixer posture.
- `index.ts` merges live frames through `mergeLiveContext`, clears stale
  deck/audio fields when newer frames omit them, keeps recent controller moves
  on a short TTL, and sends only `liveContextForChat(latestLiveContext)` to
  `libraryChat`.
- `index.ts` renders a visible live-read proof row before and after chat turns,
  with waiting/partial/armed status instead of hiding the proof state.
- `chat.test.ts` exercises the real mounted chat path so Viber receives
  deck-pair audio part labels only when the live context is fresh enough, and
  stale deck/audio context is cleared before a later chat turn.

## Source Evidence

- `tauri/ui/src/library/api.ts:272` defines the current `LibraryLiveContext`
  contract, including deck-pair audio descriptors, `audio_window_map`,
  `live_evidence`, and `recent_moves`.
- `tauri/ui/src/library/api.ts:499` normalizes deck identity and allows only
  bounded, trusted deck fields/sources.
- `tauri/ui/src/library/api.ts:544` normalizes mixer posture into bounded A/B
  controls.
- `tauri/ui/src/library/api.ts:611` normalizes `live_evidence`, deduplicating
  and capping mix, midi, and reference tokens.
- `tauri/ui/src/library/api.ts:864` rejects malformed audio-window context and
  forbids claims like attached stems or isolated decks.
- `tauri/ui/src/library/api.ts:944` accepts audio part labels only when they
  declare the live global mix and follow the non-verdict rule.
- `tauri/ui/src/library/api.ts:1314` accepts deck-audio separation text only as
  global-mix-only or configured deck-pair capture, with outcome claims
  forbidden.
- `tauri/ui/src/library/api.ts:1346`, `:1366`, and `:1387` accept deck-pair
  features, deltas, and pre/current windows only when each carries the
  non-outcome/non-causal rule.
- `tauri/ui/src/library/api.ts:1467` builds the normalized live context, and
  `tauri/ui/src/library/api.ts:1593` merges derived evidence back into it.
- `tauri/ui/src/library/api.ts:1823` keeps backend `live_verification` receipts
  available to the UI.
- `tauri/ui/src/library/api.ts:2465` passes `liveContext` to the real Tauri
  `library_chat` command when the webview is running inside Tauri.
- `tauri/ui/src/library/index.ts:288` merges incoming live frames, and
  `tauri/ui/src/library/index.ts:337` through `:355` clears stale textual and
  audio-window fields when a newer frame omits them.
- `tauri/ui/src/library/index.ts:374` builds the final chat-bound live context,
  adding recent moves only when fresh.
- `tauri/ui/src/library/index.ts:1048` computes waiting/partial/armed live-read
  status from transport capabilities, deck identity/source, transition gates,
  deck-pair capture, and receipt tokens.
- `tauri/ui/src/library/index.ts:1766` passes the sanitized live context into
  `libraryChat` during a Viber chat turn.

## Test Evidence

- `tauri/ui/src/library/api.test.ts:306` proves live deck context normalization
  drops non-deck/noisy fields, strips private/path-like payloads, bounds mixer
  values, preserves citable evidence, and rejects malformed raw live-audio
  strings.
- `tauri/ui/src/library/api.test.ts:661` through `:732` prove configured
  deck-pair separation, feature, delta, window, and Gemini part descriptors are
  accepted only in the supported non-verdict shapes.
- `tauri/ui/src/library/chat.test.ts:475` proves the chat chrome shows a
  waiting live-read row before the user asks Viber.
- `tauri/ui/src/library/chat.test.ts:489`, `:503`, `:517`, `:535`, and `:636`
  prove the UI stays partial until deck-pair identity, source, capture, and
  receipt requirements are satisfied.
- `tauri/ui/src/library/chat.test.ts:584` proves deck-pair audio-window part
  labels reach Viber chat when the live read is armed.
- `tauri/ui/src/library/chat.test.ts:614` proves stale Deck A/B audio part
  context is cleared when a later frame omits it.
- `tauri/ui/src/library/chat.test.ts:701` proves live-verification receipts are
  rendered as user-facing live-read proof without leaking internal guard labels.
- `tests/library/test_live_context_cli.py:1806` proves the CLI can pass a
  proof-file live context into library chat; `tests/library/test_live_context_cli.py:1996`
  through `:2155` prove unsupported transition/audio claims are rejected or
  corrected before they can be treated as a grounded live read.

## Verification

Package UI tests:

```text
npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts
73 passed
```

Full webview build:

```text
npm --prefix tauri/ui run build
tsc --noEmit && vite build passed
```

Supporting live-context CLI contract proof:

```text
uv run pytest -q tests/library/test_live_context_cli.py
40 passed in 3.62s

uv run ruff check tests/library/test_live_context_cli.py
All checks passed!
```

Whitespace:

```text
git diff --check -- tauri/ui/src/library/api.ts tauri/ui/src/library/index.ts tauri/ui/src/library/api.test.ts tauri/ui/src/library/chat.test.ts tests/library/test_live_context_cli.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- Package 5 owns the UI library live-read files only. `test_live_context_cli.py`
  is supporting evidence from the live-context/release-gate lane and should not
  be absorbed into a Package 5 commit unless that lane is deliberately bundled.
- This package does not change core Viber search/tool semantics.
- This package does not prove that the current running app has a real armed
  deck-pair read. It proves the UI will not pass unsupported or stale context as
  if it were armed.

## Next Required Proof

Run a source-mode or packaged-app rehearsal while FLX4, Rekordbox, and
BlackHole 16ch are active. The proof should capture a library chat turn where
the UI shows `live read armed`, `library_chat` receives deck-pair context, and
the returned Viber text either stays within the proof or is corrected by
`live_verification` without leaking internal guard labels.
