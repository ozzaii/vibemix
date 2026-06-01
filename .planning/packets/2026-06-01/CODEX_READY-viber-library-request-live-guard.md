# CODEX_READY: Viber Library Request Live Guard

Date: 2026-06-01
Author: Codex
Status: LAND packet, Viber text-boundary slice
Package: Package 5B - Viber Library Request Live Guard

## Decision

LAND this slice as `fix(library): keep Viber library requests grounded`.

This package fixes the case where Viber receives live context as a safety rail
but the user's actual request is library/crate/set-prep help. In that mode,
unsupported live transition, deck, or sound-change fallback language should not
replace an honest library answer.

## Files

- `src/vibemix/library/codex_curate.py`
- `tests/library/test_codex_curate.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-viber-library-request-live-guard.md`

## What Changed

- `chat_with_codex()` classifies whether the user is asking about the active
  live moment or asking for library/crate/set-prep help while live context is
  merely attached.
- For library requests with live context, model replies that leak live-move,
  transition, or sound-change fallback language are replaced with grounded
  library result copy when there are tracks/tools, or an honest no-results
  library reply when there are none.
- The live verification record still preserves the raw guard violations,
  including `library_request_live_leak`, so the bad model shape remains visible
  to eval/reporting.
- Active live questions continue to use the live guard path. This package does
  not mute legitimate live-context answers; it prevents hidden live context from
  hijacking explicit library work.

## Evidence

Full Viber/Codex curate tests:

```text
uv run pytest -q tests/library/test_codex_curate.py
88 passed in 0.48s
```

Focused library/live guard:

```text
uv run pytest -q tests/library/test_codex_curate.py -k 'library_request or non_live_outcome or live_context or chat_with_codex'
37 passed, 51 deselected in 0.23s
```

CLI live reply checks:

```text
uv run pytest -q tests/library/test_live_context_cli.py -k 'chat or verify_live_reply'
8 passed, 32 deselected in 0.33s
```

Stop reason coverage:

```text
uv run pytest -q tests/library/test_codex_curate_stop_reason.py
16 passed in 0.38s
```

Lint:

```text
uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py
All checks passed!
```

Whitespace:

```text
git diff --check -- src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This package is about Viber text results. Package 8D separately governs Sven's
  spoken live-cohost path.
- It does not prove the installed Codex binary or Tauri chat surface with a real
  logged-in Codex session. Current proof is deterministic unit/CLI boundary
  coverage against current source.
- The source file is shared with AI-message observability work. Stage by hunk:
  this package owns library-request detection, live-leak suppression, and its
  regression tests.

## Next Required Proof

Run a real Viber/Codex CLI or Tauri chat turn with Codex logged in and a
live-context artifact attached:

- Ask for library/crate/set-prep help.
- Force or observe a model reply that tries to pivot into live-move language.
- Verify the user-visible reply stays a grounded library answer or honest
  no-results text.
- Verify `live_verification.guard_violations` still records the suppressed leak.
