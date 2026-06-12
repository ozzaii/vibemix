# 2026-06-12 — Gig Check + Export Guard shipped; DO NOT drop these from the main push/PR

> For the session preparing the main push / PR: branch `ux-redesign-impeccable`
> carries four commits from the 2026-06-12 hand-of-god execution lane. They are
> green, smoke-tested on the real CLI, and must ride the push. This file exists
> so no model misses them while assembling the PR.

## The four commits (in order)

| Commit | What |
|---|---|
| `18e1df61` | `feat(library): gig-check` — read-only preflight verdict over a Rekordbox XML (`library/gig_check.py` + 18 tests + CLI) |
| `8815e18a` | `feat(library): export-guard` — read-only USB preflight vs a target rig (`library/export_guard.py` + 25 tests + CLI) |
| `7d0b0783` | `docs(planning)` — hand-of-god ingest closed at 8/8 files; queue updated |
| `d20494b5` | `feat(library): gig-check goes five-ecosystem + duplicate-winner ranking` (new `tests/library/test_gig_check_sources.py`; public `serato.iter_crates`) |

## What they are (one paragraph)

The 2026-06-11 Viber WA research pack ("hand of god", 8 files, digested at
`.planning/packets/2026-06-12/HAND-OF-GOD-DIGEST.md` — read THAT, not the raw
8.3M pack) concluded: own the pre-gig trust moment with read-only preflight
verdicts. Two CLIs now exist. `library gig-check <path>` audits ANY DJ catalog
(auto-sniffs Rekordbox collection.xml / Traktor collection.nml / VirtualDJ
database.xml / Engine m.db / `_Serato_` folder or its parent drive root) for
missing files, cue debt, duplicate suspects (with a g13/g14 "which copy has my
cues?" keeper call), crate bloat → `take_it / fix_first / do_not_take`, exit
code = verdict (0/1/2). `library export-guard <usb> --rig cdj-3000x` walks a
mounted USB and predicts "will it show up tonight": the OneLibrary
(`PIONEER/rekordbox/exportLibrary.db`) vs Device Library
(`PIONEER/rekordbox/export.pdb`) dual-format trap, filesystem rules, per-rig
audio-format support, missing USBANLZ. 9 rig profiles.

## Contracts the PR description should not misstate

- **Public noun is "Gig Check"** — NEVER "Library Doctor" in public copy
  (musiclibrarydoctor.com is a live competitor; `library doctor` internally is
  the env self-check). Avoid "AI DJ" language.
- Both tools are **read-only, deterministic, no network, no model calls**.
  V1 earns trust by refusing dangerous fixes (the pack's red line).
- `export_guard.RIG_PROFILES` hardware facts are **research-verified against
  official AlphaTheta notices/manuals** (workflow `wf_c61ce5aa-807`, 23/24
  claims survived adversarial verification; sources cited in the module
  docstring). Do not "fix" them from memory; unknowns are reported as
  unknown by design (e.g. engine-os format matrix deliberately not audited).
- Only `source == "dj"` cues count as prep in gig-check; anlz/auto cues never
  silence the naked-track signal (Invariant-#2-adjacent honesty rule).

## State at handoff

- Suite: `tests/library` + `tests/repo` = **1630 passed**; the only reds are
  the two INHERITED ones (curator persona-seam expectation vs HEAD's debrief
  persona, and the 2026-06-10 `debrief-mock-after.png` 1MB LFS scrub) — both
  pre-date this lane; do not attribute them to it.
- Real-CLI smokes performed: Rekordbox fixture (DO NOT TAKE / exit 2),
  Serato drive-root auto-detect (2 tracks parsed), Traktor NML (FIX FIRST /
  exit 1), export-guard 3 scenarios incl. unknown-rig actionable error.
- **Packaging: free.** Pure `vibemix.*` modules — PyInstaller
  `collect_submodules` bundles them automatically; NO new third-party dep
  (pyrekordbox already shipped). No spec edit needed. The current
  `dist/vibemix-0.0.1.dmg` (Jun 11 22:37, metallib rebuild) PRE-DATES all
  four commits — a fresh DMG is required for them to reach users.
- CLAUDE.md's Library CLI block documents both commands (committed alongside
  this handoff).

## Queue after these (pack priority)

1. Public `/dj/gig-check` panic-SEO utility (product/web decision — Kaan's call)
2. Crate Ark (backup-meaning manifest, pure code)
3. Migration preflight ("what dies in transit")
4. Recall trainer

Full map + final-pass golds: `.planning/packets/2026-06-12/HAND-OF-GOD-DIGEST.md`.
