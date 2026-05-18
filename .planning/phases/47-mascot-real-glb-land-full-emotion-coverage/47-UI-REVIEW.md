---
phase: 47-mascot-real-glb-land-full-emotion-coverage
reviewed_at: 2026-05-18
overall_score: 22
max_score: 24
review_type: advisory
visual_surface_status: scaffold-only (real visual lands at §VIS-04 discharge)
---

# Phase 47 UI Review — 6-Pillar Visual Audit

**Overall: 22 / 24** (scaffold-grade — the visible character animation lands post-§VIS-04 discharge)

> Phase 47 ships **infrastructure for a visual surface**, not a new visual surface itself. The mascot panel chrome, layer indicators, persona-smoke harness frame, and README hero scaffold are all defined contract-wise in 47-UI-SPEC.md and instantiated as engineering scaffolds (placeholder 44 KB GLBs stand in for real Mixamo clips). This review audits the **contract quality** + the **engineering scaffold quality**, not the final visible rendering (which depends on §VIS-04 Kaan-discharge).

## Pillar Scores

| Pillar | Score | Notes |
|--------|-------|-------|
| Copywriting | 4 / 4 | Locked-vocab captions, anti-slop blocklist clean, error copy routed through existing crash-banner.ts |
| Visuals | 3 / 4 | Scaffold complete; visible quality pending §VIS-04 — react_hype_peak.glb 44 KB placeholder for README hero |
| Color | 4 / 4 | Zero new tokens; CDJ Whisper palette + 60/30/10 split + single amber accent enforced via `grep -rn '#[0-9a-fA-F]\{3,6\}'` ban |
| Typography | 4 / 4 | Zero new typographic roles; Saira + JetBrains Mono via `var(--type-*)` only |
| Spacing | 4 / 4 | All spacing tokens (xs/sm/md/lg/xl/2xl) sourced from existing tokens.css; no exceptions |
| Experience Design | 3 / 4 | Read-only canvas; no scope creep; reduced-motion fallback specified; -1 for the 23 placeholder GLBs not yet shipping the real motion-design intent |

## Top fixes (non-blocking)

1. **Post-§VIS-04: re-run UI review** once 28 real Mixamo retargets land. The Visuals + Experience Design pillars will likely jump to 4/4 (placeholder degenerate-output is the main delta).
2. **Consider rendering a placeholder-aware persona-smoke output** that overlays "PLACEHOLDER — pending VIS-04" text on the captured WebM, so an operator running `scripts/mascot/persona_smoke.sh` pre-discharge doesn't mistake the output for a release-ready demo.
3. **README hero size guards (50 KB PNG, 100 KB WebM)** may be too tight for real renders — review post-discharge; loosening these ceilings is acceptable if the real renders compress below ~120 KB combined.

## Pillar Detail

### Copywriting — 4/4

**Strengths:**
- Every shipped string in 47-UI-SPEC.md passes the 16-token anti-slop blocklist + `\bdeeply\s+\w+` regex (verified by `scripts/mascot/check_no_ai_slop_phase47.py`).
- Locked-vocab captions for the persona-smoke harness (`<clip_stem> / <N> of 15`) keep the harness output deterministic and machine-greppable.
- README hero alt text "vibemix mascot — Neon Rebel, hype peak reaction" matches the Phase 44 README hero verbatim-text contract.
- Mascot panel header lowercased ("mascot") matches CDJ Whisper restraint.
- Error state routes to existing `crash-banner.ts` — no new copy surfaces invented.

**Concerns:** None.

### Visuals — 3/4

**Strengths:**
- 23 placeholder GLB stubs at correct paths so the asset loader works in dev (no 404s).
- Three.js scene contract specified: OrthographicCamera framed on rig torso+head; void-2 #05070b clear color; no chrome 3D effects.
- 4-layer additive composition (Base 50 / Emotion 60 / Anticipation 70 / Reaction 80) lifted verbatim from the Phase 22-02 / Phase 31 v2.1 state machine.
- Mascot canvas read-only (no drag-rotate, no zoom) — matches `project_visual_direction_cdj_whisper` "restraint over flair".

**Concerns (-1):**
- The placeholder GLBs are all 44 KB copies of `prep_settle.glb` — `react_hype_peak.glb` rendering produces a degenerate static pose, not the peak-energy headbob the README hero needs. The Visuals pillar lands at 3/4 until §VIS-04 discharge.
- Bundle gate exits 2 (Tier 2 placeholder fail) — documented expected-fail UX, but worth flagging as a visible blocker on the path to full 4/4.

### Color — 4/4

**Strengths:**
- Zero new tokens introduced — `tokens.css` v5 CDJ Whisper cascade preserved byte-identical.
- 60/30/10 split locked: 60% void-2 dominant (canvas + panel), 30% glass-1 secondary (chrome + pills), 10% amber accent (reaction-pulse + indicator borders + caption underline).
- Single amber accent enforced — no secondary accent invented.
- Anti-pattern guard: `grep -rn '#[0-9a-fA-F]\{3,6\}' tauri/ui/src/mascot/` returns 0 violations.
- Destructive token NOT used (mascot panel has no destructive actions) — matches information-architecture honesty.

**Concerns:** None.

### Typography — 4/4

**Strengths:**
- Zero new typographic roles invented.
- All sizes sourced from existing `var(--type-body|label|mono|heading|display)` tokens.
- Body 14px Saira 400, Label 11px Saira 500, Mono 11px JetBrains Mono 400, Heading 18px Saira 600 — full ladder reused.
- Vendored WOFF2 (no Google Fonts runtime fetch) — privacy + offline-first preserved.
- Anti-pattern guard: no inline `font-family` declarations in Phase 47 components.

**Concerns:** None.

### Spacing — 4/4

**Strengths:**
- All spacing tokens (xs 4px → 2xl 48px) sourced from existing `tokens.css` spacing block.
- 4-multiple discipline preserved.
- No exceptions / one-offs.
- Spacing ladder applied consistently:
  - xs 4px → canvas inner padding
  - sm 8px → reaction-trigger gap
  - md 16px → mascot panel internal padding
  - lg 24px → mascot panel margin to deck siblings
  - xl 32px → persona-smoke caption-to-canvas separation
  - 2xl 48px → README hero figure → adjacent paragraph

**Concerns:** None.

### Experience Design — 3/4

**Strengths:**
- Read-only mascot canvas — no scope creep into draggable / zoom / pose-toy directions.
- `prefers-reduced-motion: reduce` fallback specified: chrome animations defer; mascot 3D animation itself still plays (visual signal load-bearing per `project_mascot_as_vtuber_personality_surface`).
- Layer-indicator pills' click-to-cycle-recent-clips behavior gated behind `data-debug="true"` Settings → Developer pill — does not leak to default UX.
- Error states routed through existing crash-banner.ts — no new error chrome invented.
- Persona-smoke harness is headless (no user-facing surface) — operator runs it via shell, not via app UI.

**Concerns (-1):**
- The 23 placeholder GLBs render as degenerate static poses pre-§VIS-04 — the "live experience" of watching the mascot react to events is the entire UX value of the phase, and that experience is currently scaffolded but not delivered until Kaan walks the Mixamo flow. The Experience Design pillar lands at 3/4 until full discharge.
- No "discharge progress" indicator surface for an operator to track which of the 28 slots are still placeholders. Would not block release, but a `scripts/mascot/check_discharge_progress.py` summary would help during the multi-session Mixamo walk.

## Cross-Pillar Notes

- **CDJ Whisper visual language preserved** — Phase 47 introduces zero new tokens, zero new typographic roles, zero new spacing values. The contract is purely additive (new clip slots in the existing surface).
- **POC immutability preserved** — `mascot.html` byte-identical to v2.0 tag per `tests/repo/test_g5_poc_files_untouched.py`.
- **Pitfall 4 closure verified** — CI grep gate at `.github/workflows/mascot-tauri-only.yml` with 6-file POC-immutability allowlist returns 0 violations.
- **Bravoh-side proxy + privacy rule** — Phase 47 changes zero IPC handlers / network endpoints / credential paths. Pure-asset / pure-build / pure-test surface.

## Recommendation

Phase 47 cleared at 22/24 (scaffold-grade). Re-run UI review post-§VIS-04 discharge to confirm Visuals + Experience Design jump to 4/4 with real Mixamo clips driving the visible mascot animation.

Phase 48 (OPP) dispatch is unblocked — Phase 48 depends on Phase 46 schema, not Phase 47's UI surface.
