# CUE-LAND-ENGINE

Synthesis of observations, design, and three adversarial verdicts (provenance/safety, feasibility, cross-engine fit). Only what survived verification is below. The single highest-leverage move endorsed by all three judges leads: ship the provenance stamp first, then Viber auto-cue-on-export, carrying the stamp with it.

## What this is

Auto-cues that vibemix detects (intro, build, breakdown, drop, outro) land directly in the DJ's software so a track or a built set arrives gridded and cued on pads A-H, ready to play. Rekordbox is the first target; Serato and Mixxx follow on the universal carrier already in the tree. Two guarantees are stated up front and are structurally enforced, not promised. **Non-destructive:** every write produces a fresh importable file (`collection.xml`) or opt-in audio file-tags. No path touches Rekordbox's private SQLCipher DB. The irreversible merge stays the DJ's own gesture inside their own app. **Provenance:** an auto cue can never be byte-indistinguishable from a DJ's hand-set cue. A single `source` field rides from producer to carrier and a `VM ` Name prefix survives the Rekordbox import, so a DJ scanning their pads always sees what vibemix authored versus what they did. The whole capability generalizes behind one core so every engine lands cues the same way.

## Current stack (what exists)

The deterministic spine already exists end-to-end. The work is mostly wiring tested carriers behind one consent seam, plus one tiny provenance fix and one shared UI.

**Producers (all real, all tag `source`):**
- CUE-DETR ONNX `library/cue_detr.py:detect_cue_positions` -> raw timestamps, deps lazy + guarded.
- Pipeline assembler `library/cue_engine.py:detect_cues_auto:164` -> ONNX, then `cue_refine` snap/dedup, then `build_cue_anchors:77`; falls back to dep-free `cue_detect.detect_cues:186` on `CueProducerUnavailable`. Emits `list[CueAnchor]`, `source="auto"` (`:151`).
- Rekordbox ANLZ ingest `library/anlz_ingest.py`: `anchors_from_anlz:208` (`source="anlz"` :238, from PSSI phrase) and `dj_cue_anchors_from_anlz:246` (`source="dj"` :280, from PCOB/PCO2 hand-set cues).
- `CueAnchor` (`library/cue_types.py:41`) = the frozen cross-session seam (label / start_s / end_s / confidence / source in {dj, anlz, auto}); no slot.
- `SmartCue` / `SmartCueProposal` (`library/smart_cues.py:78` / `:118`) = the richer producer that owns slot policy: A-H roles (`SLOT_ROLES:40`), genre priority (`GENRE_SLOT_PRIORITIES:62`), `SOURCE_RANK {dj:4, anlz:3, auto:2, fallback:1}` (`:38`), `human_slot_occupied` suppression (`:193`), `_is_human_authored_cue` (`:324`), per-cue `review_status`. `propose_smart_cues:151` does the merge/rank/suppress; `proposal_to_export_marks:253` produces export marks.

**Carriers (all non-DB, fresh-tree or opt-in tags):**
- `library/export_rekordbox.py:export_set:95` = the universal sink. Fresh `RekordboxXml` tree -> `collection.xml`; `_add_cues:267` writes POSITION_MARK. Non-destructive; the DJ imports it additively.
- `library/cue_export.py:export_cues:95` = a parallel CueAnchor->XML writer with colored pads (`_LABEL_COLORS:52`). Effectively dead in the product except as the source for the label->name/color maps that `cue_folder` and `export_serato` import.
- `library/cue_folder.py:96` = folder bridge -> `detect_cues_auto` per file -> `anchors_to_marks:74` -> export-set dicts; `export_cued_folder:178` routes rekordbox/m3u8/both; `tag_folder_serato:238` opt-in Serato tags.
- `library/export_serato.py:write_serato_cues:223` = the universal carrier (Serato Markers2 GEOB into the audio file, reaches Serato + Mixxx + Rekordbox on load). File-mutating, opt-in `allow_write:238`, `_merge_cues:166` preserves foreign-pad cues.
- CLI: `__main__.py:_cmd_library_export_set:7411` with `--allow-unvalidated` (logic :7458, a grounding gate, a different axis than write-permission); `_cmd_library_cue:7518`.
- Viber/MCP: `toolset.py:smart_hot_cues:531` and `export_smart_cues:1024` -> `proposal_to_export_marks` -> `export_rekordbox.export_set`; registered `mcp_server.py:246/259/369`.
- Learn: `learn/mastered_marker_writer.py:write_mastered_marker:207` -> `write_serato_cues(..., merge=True)`, six-way gated.

**Verdict: scattered, not unified.** Two cue shapes that do not share a slot model (`CueAnchor` has no slot; `SmartCue` does, and the bridge `smart_cue_to_anchor:241` downgrades and loses slot/review/provenance). Three Rekordbox writers (the real sink, the dead colored-pad one, the folder orchestrator). Permission handled per-module on different axes (`allow_write` for tags, `--allow-unvalidated` for grounding, nothing for plain XML). The only app-wired cue path is `library_cue_folder` (Rust `library_cmds.rs:866`, registered `main.rs:111`, called `tauri/ui/src/library/api.ts:2637`), which is the GUI-safe portable-only subset and skips the SmartCue slot/provenance policy entirely. The correct provenance-aware path (`smart_hot_cues`/`export_smart_cues`/`export_set`) has no Tauri command and no frontend caller; it is reachable only via MCP and CLI.

**The confirmed leak.** `source` dies at the export-mark dict boundary. `export_rekordbox._add_cues` reads only `name/type/start_s/end_s/num` and calls `track.add_mark(Name, Type, Start, End, Num)`; no `source` arg exists. `toolset._export_cues_and_grid:1805` (the #1 call site) emits only `entry.cues` with no `source`. On the folder/anchor path (`cue_folder.anchors_to_marks`, `cue_export.cue_anchor_to_mark_kwargs`) auto cues land as bare `INTRO`/`DROP` with no `VM ` prefix, so they ARE byte-indistinguishable from DJ cues today. Important correction confirmed in source: `proposal_to_export_marks` ALREADY carries `"source"` (`smart_cues.py:283-285`) and `_add_cues` already writes the `VM `-prefixed `Name` from `SLOT_EXPORT_LABELS` into the POSITION_MARK. So the SmartCue path is clean; the leak is only on the folder/cue_export paths and at the `_export_cues_and_grid` seam.

## The reusable cue-landing engine

One new module, `library/cue_landing.py`, sits ABOVE the working carriers and never reimplements XML/tag writing. Two records and one verb. This is the only new product code of size, and it is glue.

**`CueSet`** = unified, slot-native and provenance-native. **`LandedCue`** = a `SmartCue` projected at the moment slots are already assigned (slot / role / start_s / end_s / start_beat / confidence / source / review_status / provenance_ref). Verified 1:1: `SmartCue` (`smart_cues.py:77-94`) already carries every one of these fields, so `propose_smart_cues` output maps onto `LandedCue` with zero loss. `CueAnchor` stays the producer shape; the seam converts `CueAnchor -> SmartCue -> LandedCue` exactly once.

**`land(cueset, target, *, granted) -> LandReceipt`** = the single permissioned verb. `target` in {RekordboxXml, SeratoTags, MixxxTags, M3u8}, each an `ExportTarget` declaring `destructive: bool` + `requires_permission: bool`. `land()` does three things only: (1) refuses unless `granted` is True (per-call bool, no module-level remembered consent), (2) stamps provenance so an auto/anlz/fallback cue never lands naked, (3) delegates to the existing carrier and returns `LandReceipt {path, written_count, kept_dj_count, skipped_count, target, import_instruction}`.

**WIRE vs BUILD per piece** (feasibility judge's corrected effort, no inflation):

| Piece | Verdict | Effort | Proof |
|---|---|---|---|
| `cue_landing.py` core (CueSet/LandedCue/land) | BUILD glue | ~1.5d | unit: propose_smart_cues -> CueSet -> marks lossless vs proposal_to_export_marks |
| Producers -> CueSet | WIRE | in the above | each `source` preserved into the CueSet |
| Provenance stamp (`source` key + `VM ` Name) | BUILD tiny, do FIRST | ~0.5d | pyrekordbox re-parse biconditional (below) |
| `library_land_cues` Tauri cmd + IPC | BUILD | ~0.5d | ipc-wiring-checker both ends; codegen:ipc |
| Cue Tray UI + primitives | BUILD | ~4-5d | render CueSet fixtures; badge hollow/filled |

Two corrections to the design's optimism that survived feasibility review and are baked in here:
- **The merge is not free.** `propose_smart_cues` consumes *sections*, not raw `CueAnchor`s, and no `CueAnchor -> section` adapter exists. That shim is the load-bearing part of the ~1.5d core. True retirement of the three independent merges (`smart_cues._near_stronger_cue`, `export_serato._merge_cues:166`, `ingest._materialized_cue_number:388`) is a follow-up, not day one.
- **Verify the one unverified producer tag:** confirm `cue_detect.detect_cues` actually sets `source="fallback"` (it is returned verbatim by `detect_cues_auto`, one line to check).

**The provenance fix (highest-value, smallest, do FIRST).** Close the leak in two cheap places inside the seam: (1) carry the `source` key through the export-mark dict on the folder/anchor path so the readers (`_add_cues`, `export_serato`) can act on it; (2) deterministically guarantee the `VM ` Name prefix for every `auto`/`anlz`/`fallback` cue and never for a `dj` cue. The anti-masquerade contract is a TEST, not a convention: re-parse the written `collection.xml` with pyrekordbox and assert the biconditional — (a) every POSITION_MARK named `VM ...` has `source != dj`, (b) every `source != dj` mark has the `VM ` prefix, (c) every DJ-named mark is byte-preserved verbatim, (d) zero DB files touched. Make `VM ` unspoofable: reject an incoming DJ cue whose name already starts `VM ` so a real cue can't masquerade by name. Pure file round-trip, never a DB write. The provenance verdict flagged this as the single most valuable item; the feasibility verdict named it the smallest real first step that de-risks every downstream caller.

## Sexy permissioned UX

One surface, the **Cue Tray**, three states and never more: **Detecting** (honest progress) -> **Review** (the preview) -> **Landed** (the receipt). No prelisten, no audio playback, no second window. Dark and textured, one amber accent line that ignites only on grounded things. It is a pure render of `CueSet`, so zero new model work. It is the reusable shell every other engine inherits.

**Preview = the A-H slot ladder.** Eight fixed rows A->H; the pad slot IS the identity (a DJ reads "D is my drop" by muscle memory). Per row: pad letter + role word, `m:ss` time (bar tooltip from `start_beat`, grounded-only), a 5-segment **ConfidenceMeter** banded to the policy floors (`export_ready >= 0.78` -> 4-5 segments, pre-checked; `review 0.55-0.78` -> 2-3 segments, checked-but-flagged; below `review_floor` never reaches the tray, surfaced only behind a collapsed "N candidates the engine wasn't sure of"), and the load-bearing **ProvenanceBadge**: `◇ AUTO` hollow vs `● DJ` filled. DJ rows render locked, no checkbox, shown `· kept` (the upstream `human_slot_occupied` guard made visible). Empty slots shown empty (honest-null made visible; the engine declined to guess). Top honesty line from `SmartCueProposalSummary`: "6 cues ready, 1 to review, C/E/H left empty — techno priority." Folder mode collapses to a track list with `6 ✓ · 1 ?` per row. Accept/reject is at the slot grain: AUTO rows have checkboxes, `export_ready` checked by default, `review` checked-but-flagged; DJ rows untouchable.

**Permission = one explicit consent gesture, then their hand.** `[ Rekordbox ▾ ]  Land 6 cues →`. Pressing the primary button IS the authorization (`granted=True`); before it, nothing has touched the machine beyond an in-memory proposal. The target picker defaults to the on-screen detected app (`djay/rekordbox/serato/traktor/virtualdj`). Land does three automatic jobs then stops at the door: writes the fresh importable `collection.xml` to `~/Music/vibemix/cues/<name>.xml`, reveals it in Finder + copies the path, and swaps to the Landed receipt. The receipt carries the copy-exact handoff (confirmed against Rekordbox 7): "Preferences -> Bridge -> 'Imported Library' -> choose this file. Drag its Playlists into your collection." (Rekordbox 6: Preferences -> Advanced -> 'rekordbox xml'.) The final irreversible merge happens in Rekordbox, by the DJ's hand, where Rekordbox stages it in a separate `rekordbox xml` quarantine view before the drag-in.

**Multi-ecosystem = same consent, target picker.** Rekordbox -> importable XML. Serato -> the universal Markers2 carrier (writes into a copy of the audio files), so the button reads `Land 6 cues to Serato (writes file tags) →`, gated by the same `allow_write` the backend already enforces, with the receipt line "Your hand-set cues on other pads are kept." Mixxx -> same Markers2 carrier plus neutral `.m3u8` ordering. The picker changes only the carrier and the receipt; the ladder, provenance contract, accept/reject grain, and one-consent model are identical. A DJ learns the gesture once.

**Auto-vs-user boundary, stated on the box.** vibemix automates up to the door of the DJ's software and stops: it detects structure, bands confidence, picks the carrier, writes the non-destructive file, reveals it, preserves DJ cues, and stamps everything `AUTO` / `VM `. The DJ always does: accept/reject each AUTO slot, press Land (the one consent), and the final import/drag-in inside their own app. **Silent direct-DB write is off the happy path entirely** — no checkbox, no toggle, no env flag on this screen. No DB-write path exists in the tree today and this design must not introduce one; keep direct-DB out of `cue_landing.py`'s `ExportTarget` set for v1.

**Reusable primitives** (build once, inherit everywhere): `ProvenanceBadge`, `ConfidenceMeter`, `LandConsent` (picker + single action + carrier-aware receipt), and the `Tray` state machine. A new engine feeds the ladder `{slot|rank, role, value, confidence, source}` rows + a carrier and gets the look, the honesty, and the permission model for free. The Cue Tray surfaces the backend guards as UX: locked DJ rows, empty-as-empty, hollow-vs-filled badge. Guards from the safety verdict: the badge must read the carrier-bound `source` that will actually be written (if it shows `● DJ` it is byte-true in the XML); the meter bands come from the policy floors so it can't show "ready" for a `review` cue; the file-mutating Serato/Mixxx label appears before the press.

## Cross-engine: ship order

**THE ONE FIRST INTEGRATION: Viber auto-cue-on-export, carrying the provenance stamp with it.** All three judges converged here. A DJ asks Viber to build a peak-time set and today gets back an importable XML with bare pads on every track, because `export_set` (`toolset.py:990`) spreads `_export_cues_and_grid(entry)` which reads only `entry.cues` (`:1810`) with no fallback to detection. The set-builder did the hard part (sequencing) and handed back tracks the DJ still has to cue by hand. This is the moment a DJ most wants cues (prepping an unfamiliar set) and permission is already implied by "build me a set."

**Call site:** `library/toolset.py:990`, inside `export_set`'s per-track loop. When `entry.cues` is empty (or below the `export_ready` floor), fall through to `propose_smart_cues(entry, sections_for_entry(entry), genre=...)` (the pattern proven at `smart_hot_cues:560`) -> `proposal_to_export_marks(include_preserved=False)`, merged so auto cues fill empty slots and DJ cues are never clobbered (enforced by `human_slot_occupied` suppression). Make it a deterministic default step (today it is agent discretion — `codex_curate.py:1119` only suggests `smart_hot_cues`, so most built sets export bare) with a `--cue/--no-cue` flag at `__main__.py:3624` (build-set) and an honest report line sourced from `SmartCueProposalSummary`, not a hand-written string: "auto-cued N of M tracks, K skipped (low confidence / not techno-house-psy)."

**Effort, corrected:** ~75% WIRE (not 90%). The engine, proposal layer, provenance, and both carriers exist; the merge-on-empty-slot at the seam is new logic, plus the flag and count. ~1.5-2d. **Proof:** `library build-set "..." --cue --export rekordbox`, re-parse the XML, assert empty-slot tracks gained `VM `-named auto marks and DJ-cued tracks are unchanged. The default must be fill-empty-only (`include_preserved=False`), and default-on is acceptable ONLY because the `VM ` stamp makes every auto cue self-identifying — if the stamp guard is not enforced, this element flips to KILL.

**Deferred, with why:**
- **#2 Debrief "land the cues from tracks you just played"** — KEEP, defer to second. High emotional pull (the DJ just heard the drop). But it is NOT ~70% wire as first claimed: the load-bearing input does not exist. `debrief/session_loader.py:115` returns `(events, evidence_snapshot, voice_meta)`, and there is no played-track -> library-entry resolution anywhere in `src/vibemix/debrief/`. That resolution must be built from scratch (parse titles from events, fuzzy-resolve to entries, fall back to file-path CueSets), plus a chapter/CTA and new 8766 IPC. ~30% wire, ~3-4d. It depends on #1's seam existing first. Guard: unresolved tracks fail to honest-null (never silently matched to a wrong entry).
- **#3 Semantic / next-suggestion** — REFRAME, not an integration. The pill is a consumer, not a `land()` caller, and must stay that way (Invariant #3 + latency; `next_suggestion.py:33` forbids realtime detection). It already reads `candidate.cue_slot/cue_source/cue_confidence` (`:800`) and `_cue_hint` (`:856`), which `ingest._materialize_*` already populates. Landing cues upstream via #1/ingest enriches the pill for free. This is the strong argument FOR #1, not a separate build. Guard: structural test that `next_suggestion` imports no landing/detection symbol.
- **#4 Learn mastered-moment -> hot cue** — KILL for v1, later 1-line wire. Lowest landing leverage, partially invariant-blocked (practice cues must never reach `land()`). The only legitimate landing is the single earned in-set moment, where `source="dj"` is honest (the student did it live). The honest move is to re-point `mastered_marker_writer.write_mastered_marker:207` at `land()` so it inherits the consent + receipt — a small wire, not an integration. Its existing six-way gates (position/deck/confidence/library-row) ARE the live-credit proof; `land()` must receive that same evidence, never a bare "trust me it's DJ." The judge<->auto-cue grading link (`cue_placement_judge.grade_cue_placement` `target_frame` fed by an auto anchor) is separate and unrelated to landing.

**Ship #1 + provenance stamp + the shared Cue Tray together.** The Cue Tray you build for #1 is the reusable surface #2 and the offline library nudge plug straight into.

## Owner-gates

These are Kaan's calls, not the build's:

1. **Default target ecosystem.** Recommend Rekordbox (the universal sink everything funnels into, fresh-XML non-destructive by construction, and the import UX is confirmed). The picker auto-defaults to the on-screen detected app at runtime regardless.
2. **Direct-DB-write appetite.** Recommend NO. No DB-write path exists in the tree today; keep it that way for v1. Both the safety and fit verdicts pin "writes Rekordbox's private SQLite DB by default or behind an in-screen toggle" as a hard red line. If it ever ships, it lives behind a separate typed-confirmation Advanced lane with its own warnings, never reachable from the happy path, and never inside `cue_landing.py`'s `ExportTarget` set.
3. **Tier.** Where does auto-cue-on-export sit across Free / Pro (€4.99) / Studio (€9.99)? This is set-prep value at the moment of highest DJ desire; Kaan decides whether it gates Pro or rides along.

## Next /goal — Cue-landing engine

```
/goal Cue-landing engine — provenance stamp first, then Viber auto-cue-on-export.

ISLAND (Library/Engine lane): src/vibemix/library/** (new cue_landing.py + the
provenance stamp in export_rekordbox.py / cue_folder.py / cue_export.py), the
Viber call site at src/vibemix/library/toolset.py:990 (export_set per-track loop)
+ the --cue/--no-cue flag at src/vibemix/__main__.py:3624. Any UI preview (the
Cue Tray) is the FRONTEND lane and the IPC schema add (library_land_cues) is
FRONTEND-owned — do not touch tauri/ui/src/ipc/messages.schema.json from this lane.

DO, in this order:
1. Provenance stamp FIRST (~0.5d): thread the `source` key through the export-mark
   dict on the folder/anchor path, and guarantee the `VM ` Name prefix for every
   auto/anlz/fallback cue and never for a dj cue. Reject incoming dj cues whose
   name already starts `VM ` (unspoofable).
2. cue_landing.py core (~1.5d): CueSet / LandedCue (= SmartCue projected at slots)
   + land(cueset, target, *, granted) -> LandReceipt. granted is a per-call bool,
   no remembered consent. Build the CueAnchor->section shim; route all producers
   through propose_smart_cues. land() refuses any cue with empty/unknown source.
3. Verify the cue_detect.detect_cues fallback sets source="fallback" (one line).
4. #1 Viber auto-cue-on-export (~1.5-2d): empty-slot fallback in export_set's
   per-track loop via propose_smart_cues + proposal_to_export_marks(include_preserved
   =False), default fill-empty-only, --cue/--no-cue flag, honest count from
   SmartCueProposalSummary.

PROOF (test-passing alone is not done):
- pyrekordbox re-parse biconditional on a mixed DJ+auto set: every `VM `-named
  POSITION_MARK has source != dj; every source != dj mark is `VM `-prefixed;
  every DJ-named mark byte-preserved verbatim; zero DB files touched.
- By-eye import: run `library build-set "..." --cue --export rekordbox`, open the
  XML in Rekordbox via Preferences -> Bridge -> Imported Library, confirm empty
  slots gained auto pads and DJ-cued tracks are unchanged.
- No co-host line changes here; if any reaction/persona text is touched, run
  grounding-review.

DEFER: Debrief land-your-cues (depends on #1; needs played-track->library-entry
resolution that does not exist yet). DROP for v1: Learn mastered->cue (later
1-line land() re-point). Semantic pill is a consumer, no new code.
```

```
SHARED LAW - one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, Kaan Ozkan <rahipdotaci@gmail.com>.
```
