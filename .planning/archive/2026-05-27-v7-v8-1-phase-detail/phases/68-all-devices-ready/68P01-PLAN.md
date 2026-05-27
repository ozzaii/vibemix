---
phase: 68-all-devices-ready
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - src/vibemix/midi/controllers/ddj-200.json
  - src/vibemix/midi/controllers/ddj-400.json
  - src/vibemix/midi/controllers/ddj-flx4.json
  - src/vibemix/midi/controllers/ddj-rev1.json
  - src/vibemix/midi/controllers/kontrol-s2.json
  - src/vibemix/midi/controllers/kontrol-s4.json
  - src/vibemix/midi/controllers/mc-6000.json
  - src/vibemix/midi/controllers/mc-7000.json
  - src/vibemix/midi/controllers/mixtrack-platinum-fx.json
  - src/vibemix/midi/controllers/mixtrack-pro-fx.json
  - src/vibemix/midi/map_loader.py
  - src/vibemix/midi/schema.json
  - tests/midi/test_map_loader.py
  - tests/midi/test_live_binding_profiles_canonical.py
  - tests/repo/test_readme_shape.py
  - scripts/launch/check_readme_grids_a11y.py
  - README.md
  - docs/midi-mapping.md
  - KAAN-ACTION-LEGAL.md
  - docs/contributing/midi-catalog.md
  - docs/assets/controllers/ddj-200.svg
  - docs/assets/controllers/ddj-400.svg
  - docs/assets/controllers/ddj-rev1.svg
  - docs/assets/controllers/kontrol-s2.svg
  - docs/assets/controllers/kontrol-s4.svg
  - docs/assets/controllers/mc-6000.svg
  - docs/assets/controllers/mc-7000.svg
  - docs/assets/controllers/mixtrack-platinum-fx.svg
  - docs/assets/controllers/mixtrack-pro-fx.svg
  - docs/assets/controllers/hercules-inpulse-300.svg
  - docs/assets/controllers/hercules-inpulse-500.svg
  - docs/assets/controllers/numark-party-mix-live.svg
  - docs/assets/controllers/pioneer-ddj-1000.svg
  - docs/assets/controllers/pioneer-ddj-flx6.svg
  - docs/assets/controllers/pioneer-ddj-flx10.svg
  - docs/assets/controllers/pioneer-ddj-sx3.svg
  - docs/assets/controllers/pioneer-xdj-rx3.svg
  - .planning/PROJECT.md
autonomous: true
requirements:
  - DEV-02

must_haves:
  truths:
    - "find src/vibemix/midi -name '*.json' returns zero duplicate basenames"
    - "Running uv run pytest -q after the reconciliation exits 0 (4158 baseline + new tests still pending)"
    - "tests/repo/test_readme_shape.py passes against the rewritten 10-cell README controller grid"
    - "scripts/launch/check_readme_grids_a11y.py passes against the rewritten grid"
    - "docs/contributing/midi-catalog.md exists and documents which catalog won + why"
    - "Zero references to src/vibemix/midi/controllers/ remain in active (non-archive) repo paths"
  artifacts:
    - path: "docs/contributing/midi-catalog.md"
      provides: "Migration note explaining profiles/ wins, controllers/ deleted, schema incompatibility"
      min_lines: 30
    - path: "README.md"
      provides: "Updated 'Supported controllers' 10-cell grid matching src/vibemix/midi/profiles/ set"
      contains: "pioneer_ddj_flx4"
    - path: "tests/repo/test_readme_shape.py"
      provides: "REQUIRED_CONTROLLERS list updated to the 10 profiles/ IDs"
      contains: "hercules_inpulse_500"
  key_links:
    - from: "README.md"
      to: "src/vibemix/midi/profiles/"
      via: "Anti-drift comment + cell list"
      pattern: "src/vibemix/midi/profiles/"
    - from: "scripts/launch/check_readme_grids_a11y.py"
      to: "src/vibemix/midi/profiles/"
      via: "Glob reference in comment + CONTROLLERS_CELL_COUNT"
      pattern: "profiles/\\*\\.json"
    - from: "tests/repo/test_readme_shape.py"
      to: "src/vibemix/midi/profiles/"
      via: "REQUIRED_CONTROLLERS list"
      pattern: "REQUIRED_CONTROLLERS"
---

<objective>
Wave 0 — Atomic catalog reconciliation. Collapse the duplicate `src/vibemix/midi/controllers/` ↔ `src/vibemix/midi/profiles/` catalogs to a single canonical directory (`profiles/`) and update every cross-repo reference in ONE commit so CI never reds between deletion and rewrite. This unblocks Wave 1 (contract tests + smokes can parametrize cleanly over the canonical 10), and is the load-bearing dependency for Waves 2-4.

Purpose: Eliminate the "which one does the registry actually use?" ambiguity flagged in v4.0 P53 (`profiles/` is already canonical at runtime; `controllers/` + `map_loader.py` are orphan). Closes DEV-02. The two catalogs use INCOMPATIBLE schemas (different ontologies — `controllers/` has `{vendor, model, description, verified, controls{}}` with flat cc+note dict; `profiles/` has `{id, display_name, port_name_hints, decks, controls{}, buttons{}}` with typed `kind/axis/field`) — reconciliation is DELETE-AND-UPDATE-REFERENCES, NOT merge.

Output: Deletion of 10 `controllers/*.json` + `map_loader.py` + `schema.json` + 2 orphan tests; rewrite of README controller grid + a11y script + test_readme_shape REQUIRED_CONTROLLERS + KAAN-ACTION-LEGAL §LAUNCH-04 refs + docs/midi-mapping.md schema example + `.planning/PROJECT.md` refs; addition of `docs/contributing/midi-catalog.md` migration note; rename of 10 SVG placeholders to new slugs. All in one atomic commit.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/68-all-devices-ready/68-CONTEXT.md
@.planning/phases/68-all-devices-ready/68-RESEARCH.md

@src/vibemix/midi/profiles/pioneer_ddj_flx4.json
@src/vibemix/midi/profile.py
@src/vibemix/midi/map_loader.py
@src/vibemix/midi/schema.json
@tests/midi/test_live_binding_profiles_canonical.py
@tests/midi/test_map_loader.py
@tests/repo/test_readme_shape.py
@scripts/launch/check_readme_grids_a11y.py

<interfaces>
Canonical 10 profile IDs (from src/vibemix/midi/profiles/, exactly the success-criterion set per
ROADMAP P68 SC#1):

```python
_BUNDLED_IDS = [
    "hercules_inpulse_300",
    "hercules_inpulse_500",
    "numark_party_mix_live",
    "pioneer_ddj_1000",
    "pioneer_ddj_400",
    "pioneer_ddj_flx10",
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
]
```

ControllerProfile fields validated by `src/vibemix/midi/profile.py::_parse_profile`:
- `id: str`, `display_name: str`, `port_name_hints: tuple[str, ...]` (non-empty), `decks: tuple[str, ...]`,
  `controls: dict[str, ControlBinding]`, `buttons: dict[str, ControlBinding]`, optional `notes: str`.

References to delete or rewrite (load-bearing per 68-RESEARCH.md §Runtime State Inventory):
- README.md:133-156 — 10-cell `<img src="docs/assets/controllers/...svg">` grid + anti-drift comment line 156
- README.md:135 — "sourced verbatim from `src/vibemix/midi/controllers/`" → `src/vibemix/midi/profiles/`
- tests/repo/test_readme_shape.py:51-62 — REQUIRED_CONTROLLERS list (10 IDs)
- scripts/launch/check_readme_grids_a11y.py:18-20, 62 — `controllers/*.json` comment + CONTROLLERS_CELL_COUNT
- KAAN-ACTION-LEGAL.md §LAUNCH-04 (4 refs) — `controllers/*.json` → `profiles/*.json`
- docs/midi-mapping.md:1-77 — schema example uses stale `slug/port_name_substr/deck_a` shape
- .planning/PROJECT.md:18, :233, :372 — 3 refs to `midi/controllers/`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete orphan catalog + add migration note (single commit prep)</name>
  <files>
    src/vibemix/midi/controllers/ (entire directory — 10 files),
    src/vibemix/midi/map_loader.py,
    src/vibemix/midi/schema.json,
    tests/midi/test_map_loader.py,
    tests/midi/test_live_binding_profiles_canonical.py,
    docs/contributing/midi-catalog.md (NEW)
  </files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Common Pitfalls #1 + #6 + §Runtime State Inventory + §Sources primary)
    @src/vibemix/midi/map_loader.py (166 lines — confirms CONTROLLERS_DIR = Path(__file__).parent / "controllers")
    @src/vibemix/midi/schema.json (validates LEGACY controllers/ schema only)
    @tests/midi/test_map_loader.py (gates the deleted module)
    @tests/midi/test_live_binding_profiles_canonical.py (anti-drift gate — vacuous after deletion)
    @src/vibemix/midi/__init__.py (verify no `MidiMapLoader` in `__all__` — confirm safe to delete)
    @src/vibemix/midi/generic.py (verify it does NOT import from map_loader or controllers/)
  </read_first>
  <action>
    Run `git rm` on the following load-bearing-but-orphan paths (research 68-RESEARCH.md §Common Pitfalls #6 confirms these gates target code being deleted; no behavioral coverage is lost):
    1. `git rm -r src/vibemix/midi/controllers/` (deletes all 10: ddj-200.json, ddj-400.json, ddj-flx4.json, ddj-rev1.json, kontrol-s2.json, kontrol-s4.json, mc-6000.json, mc-7000.json, mixtrack-platinum-fx.json, mixtrack-pro-fx.json).
    2. `git rm src/vibemix/midi/map_loader.py` (the orphan MidiMapLoader — never wired into runtime per `test_live_binding_profiles_canonical.py`).
    3. `git rm src/vibemix/midi/schema.json` (validates the deleted controllers/ schema; not consumed by profile.py).
    4. `git rm tests/midi/test_map_loader.py` (gates the deleted map_loader.py module).
    5. `git rm tests/midi/test_live_binding_profiles_canonical.py` (anti-drift gate becomes vacuous when its targets are gone).

    Before staging, verify `grep -rn "from vibemix.midi.map_loader\|from vibemix.midi import.*MidiMapLoader" src/ tests/` returns zero hits in active code (archives under `.planning/milestones/` are documentation, not imports).

    Create `docs/contributing/midi-catalog.md` (NEW, ≤80 lines) explaining the migration. Sections:
    - **Why `profiles/` won** (already canonical at runtime per v4.0 P53; ControllerProfile dataclass; 10 bundled match success criterion verbatim)
    - **What was deleted** (10 controllers/*.json files, map_loader.py, schema.json, 2 orphan tests — list the 10 controllers/ filenames so audit-archaeology in git history is trivial)
    - **Why DELETE-AND-UPDATE rather than MERGE** (incompatible schemas — show 4-line `controllers/ddj-flx4.json` excerpt vs `profiles/pioneer_ddj_flx4.json` excerpt to make the ontology gap concrete)
    - **For contributors adding controllers** (one-liner pointer to `docs/contributing/add-a-controller.md` — landing in Wave 3 — flag as "coming in P68 Wave 3" if not yet present at commit time, OR omit the pointer and add it in Wave 3's commit)
    - **Git archaeology** (the 10 deleted controller JSONs survive in git history at SHA preceding this commit; `git log --diff-filter=D -- src/vibemix/midi/controllers/` finds the deletion)

    DO NOT stage yet — Tasks 2 and 3 must land in the same commit (atomic reconciliation per 68-RESEARCH.md Pitfall #2).
  </action>
  <verify>
    <automated>test ! -d src/vibemix/midi/controllers/ &amp;&amp; test ! -f src/vibemix/midi/map_loader.py &amp;&amp; test ! -f src/vibemix/midi/schema.json &amp;&amp; test ! -f tests/midi/test_map_loader.py &amp;&amp; test ! -f tests/midi/test_live_binding_profiles_canonical.py &amp;&amp; test -f docs/contributing/midi-catalog.md &amp;&amp; [ $(wc -l &lt; docs/contributing/midi-catalog.md) -ge 30 ] &amp;&amp; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - `find src/vibemix/midi -name "*.json" | xargs -I{} basename {} .json | sort | uniq -c | awk '$1 &gt; 1'` returns empty (no duplicate basenames anywhere in the midi subsystem).
    - `git ls-files src/vibemix/midi/controllers/` returns empty.
    - `git diff --cached --stat -- src/vibemix/midi/controllers/` shows only D entries (pure deletion; no Ms or As).
    - `docs/contributing/midi-catalog.md` is ≥ 30 lines and contains the strings "profiles/" + "deleted" + "incompatible".
    - `grep -rn "from vibemix.midi.map_loader\|MidiMapLoader" src/ tests/` (excluding `.planning/milestones/`) returns zero hits.
  </acceptance_criteria>
  <done>
    The 5 paths are git-rm'd (staged), the migration note exists with the four required sections, no active-code reference to `map_loader` / `MidiMapLoader` / `controllers/` survives in `src/` or `tests/`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite README + a11y + test_readme_shape + KAAN-ACTION + docs/midi-mapping + PROJECT.md (the cross-repo find-and-replace surface)</name>
  <files>
    README.md,
    tests/repo/test_readme_shape.py,
    scripts/launch/check_readme_grids_a11y.py,
    KAAN-ACTION-LEGAL.md,
    docs/midi-mapping.md,
    .planning/PROJECT.md
  </files>
  <read_first>
    @README.md (lines 130-170 — current 10-cell controller grid + anti-drift comment + sniff invocation reference)
    @tests/repo/test_readme_shape.py (full file — note REQUIRED_CONTROLLERS list at ~lines 51-62 + asset path refs at ~33-39)
    @scripts/launch/check_readme_grids_a11y.py (full file — note CONTROLLERS_CELL_COUNT=10 + the inline `controllers/*.json` reference comment at lines 18-20, 62)
    @docs/midi-mapping.md (full ~77 lines — entire schema example at lines 34-52 is stale and must be replaced)
    @docs/midi-controllers.md (reference — its table already matches profiles/ verbatim; use it as the truth for slug naming convention)
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Runtime State Inventory cross-repo refs table — the load-bearing list)
    @KAAN-ACTION-LEGAL.md (grep for `§LAUNCH-04` then read full section — there are 4 refs to `controllers/*.json` that need rekey)
    @.planning/PROJECT.md (grep `controllers/` — 3 refs at :18, :233, :372)
    @src/vibemix/midi/profiles/pioneer_ddj_flx4.json (the canonical schema example for docs/midi-mapping.md rewrite)
  </read_first>
  <action>
    1. **README.md rewrite** (`controllers/` → `profiles/` swap + grid rotation):
       - Lines 133-156 region: rewrite the 10-cell "Supported controllers" grid. NEW cell list (canonical 10 per ROADMAP P68 SC#1 + 68-RESEARCH.md §Example 5):
         `hercules_inpulse_300` · `hercules_inpulse_500` · `numark_party_mix_live` · `pioneer_ddj_400` · `pioneer_ddj_1000` · `pioneer_ddj_flx4` · `pioneer_ddj_flx6` · `pioneer_ddj_flx10` · `pioneer_ddj_sx3` · `pioneer_xdj_rx3`.
       - Each `<img>` src points at `docs/assets/controllers/<slug>.svg` where `<slug>` uses the dashed lowercase form: `hercules-inpulse-300`, `hercules-inpulse-500`, `numark-party-mix-live`, `pioneer-ddj-400`, `pioneer-ddj-1000`, `pioneer-ddj-flx4`, `pioneer-ddj-flx6`, `pioneer-ddj-flx10`, `pioneer-ddj-sx3`, `pioneer-xdj-rx3` (slug convention mirrors existing `ddj-flx4.svg` → `pioneer-ddj-flx4.svg`).
       - Line 135: change "sourced verbatim from `src/vibemix/midi/controllers/`" to "sourced verbatim from `src/vibemix/midi/profiles/`".
       - Line 156: update the anti-drift comment to pin against `src/vibemix/midi/profiles/*.json`.
       - Line 164 (`scripts/sniff_controller.py` invocation reference): leave unchanged — that script stays.
       - Use `<alt>` text matching the friendly display name (e.g., `alt="Pioneer DDJ-FLX4"`) — pull from each profile JSON's `display_name` field.

    2. **`tests/repo/test_readme_shape.py::REQUIRED_CONTROLLERS`** rewrite (around lines 51-62):
       - Replace the 10-element list with the new 10 profile IDs (snake_case form: `hercules_inpulse_300`, `hercules_inpulse_500`, `numark_party_mix_live`, `pioneer_ddj_400`, `pioneer_ddj_1000`, `pioneer_ddj_flx4`, `pioneer_ddj_flx6`, `pioneer_ddj_flx10`, `pioneer_ddj_sx3`, `pioneer_xdj_rx3`).
       - If the gate compares against image slug vs. profile ID, mirror the dashed-slug convention used in the rewritten README (the test should match whichever shape the README cells emit — verify by reading the test's grep regex).
       - Update any comment that says "locked against `src/vibemix/midi/controllers/*.json`" → `src/vibemix/midi/profiles/*.json`.

    3. **`scripts/launch/check_readme_grids_a11y.py`** (lines 18-20 + 62):
       - Change the inline comment + glob reference from `src/vibemix/midi/controllers/*.json` to `src/vibemix/midi/profiles/*.json`.
       - `CONTROLLERS_CELL_COUNT = 10` stays unchanged.
       - Anything else that hardcodes a `controllers/` slug list updates to the profiles/ slug list.

    4. **`KAAN-ACTION-LEGAL.md §LAUNCH-04`** (4 refs per 68-RESEARCH §Runtime State Inventory):
       - Find each `controllers/*.json` mention; rekey to `profiles/*.json`. The canonical-10 list inside §LAUNCH-04 also updates to the new 10.
       - Do NOT touch any other §-section.

    5. **`docs/midi-mapping.md`** rewrite (lines 1-77):
       - Current schema example at lines 34-52 uses stale `{slug, port_name_substr, deck_a, deck_b, controls{}}` shape (which matches the deleted `controllers/` ontology, NOT `profile.py::_parse_profile`).
       - Replace the example with an excerpt from `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` covering the canonical fields: `id`, `display_name`, `port_name_hints` (plural list), `decks`, `controls` (with one example binding showing `kind/channel/cc/axis/deck/field`), `buttons` (with one example binding showing `kind/channel/note/deck/field`), `notes`.
       - Prefix the section with one sentence: "Profile JSONs validate against `src/vibemix/midi/profile.py::_parse_profile` (hand-rolled validator; no jsonschema in the live decode path)."

    6. **`.planning/PROJECT.md`** (3 refs at :18, :233, :372):
       - Each `midi/controllers/` reference → `midi/profiles/`.
       - Do not invent new content — these are pure rekey edits.

    Stage all six file edits. Do NOT commit yet (Task 3 stages the SVG rename + final commit).
  </action>
  <verify>
    <automated>grep -rn 'src/vibemix/midi/controllers' README.md tests/repo/test_readme_shape.py scripts/launch/check_readme_grids_a11y.py KAAN-ACTION-LEGAL.md docs/midi-mapping.md .planning/PROJECT.md 2&gt;/dev/null | grep -v '^#' | grep -v 'git log\|git history\|archaeology\|deleted' | wc -l | awk '{exit ($1 == 0 ? 0 : 1)}' &amp;&amp; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "src/vibemix/midi/controllers" README.md tests/repo/test_readme_shape.py scripts/launch/check_readme_grids_a11y.py docs/midi-mapping.md .planning/PROJECT.md` returns zero non-historical hits (mentions inside `docs/contributing/midi-catalog.md`'s migration narrative or `KAAN-ACTION-LEGAL.md §LAUNCH-04`'s history block are NOT counted — the gate is on the active-reference set above).
    - `grep -c "pioneer_ddj_flx4" tests/repo/test_readme_shape.py` ≥ 1 (REQUIRED_CONTROLLERS contains the new ID).
    - `grep -c "hercules_inpulse_500" tests/repo/test_readme_shape.py` ≥ 1 (the most-likely-missed Hercules entry is present).
    - `grep -E "kontrol[-_]s2|mc-7000|mixtrack" tests/repo/test_readme_shape.py` returns zero (old non-bundled controllers removed from the test gate).
    - `grep -c "pioneer_ddj_flx4\.json\|display_name\|port_name_hints" docs/midi-mapping.md` ≥ 1 (the new schema example references the live shape).
    - All six files are staged via `git add` (verify via `git diff --cached --stat`).
  </acceptance_criteria>
  <done>
    Every active reference to `src/vibemix/midi/controllers/` is rewritten to `profiles/` or removed; README grid + test gate + a11y script + KAAN-ACTION §LAUNCH-04 + docs/midi-mapping.md schema example + .planning/PROJECT.md all aligned with the canonical `profiles/` set; all six edits staged.
  </done>
</task>

<task type="auto">
  <name>Task 3: Rotate SVG placeholders to new slugs + commit atomically + run gate suite</name>
  <files>
    docs/assets/controllers/ (rename + create — 10 old SVGs → 10 new SVGs),
    (this task creates the final atomic commit; no new source code)
  </files>
  <read_first>
    @docs/assets/controllers/ddj-flx4.svg (read 1 existing SVG to understand the placeholder shape — they are wordmark placeholders per KAAN-ACTION §LAUNCH-04; do NOT change visual style, only filename slug)
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Open Questions #1 + Assumption A4 — SVG rotation is engineering-side placeholders in P68; real trademark logos still ride §LAUNCH-04)
    @README.md (the rewritten grid from Task 2 — confirm the 10 `<img src="docs/assets/controllers/<slug>.svg">` paths and rename SVGs to match)
  </read_first>
  <action>
    1. **Determine survivors vs. renames vs. new files** — compare current `docs/assets/controllers/*.svg` (ddj-200, ddj-400, ddj-flx4, ddj-rev1, kontrol-s2, kontrol-s4, mc-6000, mc-7000, mixtrack-platinum-fx, mixtrack-pro-fx — 10 files) against the new slug set from Task 2's README rewrite (hercules-inpulse-300, hercules-inpulse-500, numark-party-mix-live, pioneer-ddj-400, pioneer-ddj-1000, pioneer-ddj-flx4, pioneer-ddj-flx6, pioneer-ddj-flx10, pioneer-ddj-sx3, pioneer-xdj-rx3 — 10 slugs).
       - Survivors (rename existing): `ddj-400.svg` → `pioneer-ddj-400.svg`; `ddj-flx4.svg` → `pioneer-ddj-flx4.svg`. Use `git mv` to preserve history.
       - Deletions: `ddj-200.svg`, `ddj-rev1.svg`, `kontrol-s2.svg`, `kontrol-s4.svg`, `mc-6000.svg`, `mc-7000.svg`, `mixtrack-platinum-fx.svg`, `mixtrack-pro-fx.svg` → `git rm` (these controllers are no longer in the bundle).
       - New placeholders (create — 8 new): `hercules-inpulse-300.svg`, `hercules-inpulse-500.svg`, `numark-party-mix-live.svg`, `pioneer-ddj-1000.svg`, `pioneer-ddj-flx6.svg`, `pioneer-ddj-flx10.svg`, `pioneer-ddj-sx3.svg`, `pioneer-xdj-rx3.svg`. Copy the existing `pioneer-ddj-flx4.svg` (formerly `ddj-flx4.svg`) as a template and update only the inline wordmark text to the new controller's `display_name`. Same dimensions, same fill, same accessibility metadata — the placeholder rotation is documented as engineering-side in 68-RESEARCH.md Assumption A4; real trademark-compliant logos ride §LAUNCH-04 separately.

    2. **Pre-commit gate dry-run** — before staging the commit, run the test gate set that 68-RESEARCH.md §Runtime State Inventory flags as load-bearing:
       - `uv run pytest tests/repo/test_readme_shape.py -v` — must be GREEN against the rewritten README grid.
       - `uv run python3 scripts/launch/check_readme_grids_a11y.py` — must exit 0.
       If either fails, diagnose against Task 2's edits — DO NOT proceed to commit. Common failure (per 68-RESEARCH Pitfall #2): the test enforces a specific slug shape (dashed vs underscore) different from what was written into README.

    3. **Atomic commit** — stage all changes from Tasks 1 + 2 + this task:
       ```
       git add -A src/vibemix/midi/ tests/midi/ tests/repo/test_readme_shape.py \
                  scripts/launch/check_readme_grids_a11y.py README.md docs/midi-mapping.md \
                  docs/contributing/midi-catalog.md KAAN-ACTION-LEGAL.md \
                  .planning/PROJECT.md docs/assets/controllers/
       git commit -m "$(cat &lt;&lt;'EOF'
       refactor(68P01): reconcile MIDI catalog — delete orphan controllers/, canonicalize profiles/

       Atomic reconciliation per DEV-02:
       - Delete src/vibemix/midi/controllers/ (10 orphan JSONs — incompatible ontology)
       - Delete src/vibemix/midi/map_loader.py + schema.json (orphan MidiMapLoader path)
       - Delete tests/midi/test_map_loader.py + test_live_binding_profiles_canonical.py
         (gate code that no longer exists)
       - Rewrite README.md 'Supported controllers' grid to the canonical 10 profiles/ IDs
       - Update tests/repo/test_readme_shape.py::REQUIRED_CONTROLLERS to new 10
       - Update scripts/launch/check_readme_grids_a11y.py reference to profiles/*.json
       - Update KAAN-ACTION-LEGAL.md §LAUNCH-04 (4 refs)
       - Rewrite docs/midi-mapping.md schema example to match profile.py::_parse_profile shape
       - Update .planning/PROJECT.md (3 refs)
       - Rotate 10 SVG placeholders to new slugs (hercules-inpulse-{300,500},
         numark-party-mix-live, pioneer-ddj-{400,1000,flx4,flx6,flx10,sx3}, pioneer-xdj-rx3)
       - Add docs/contributing/midi-catalog.md migration note

       Per 68-RESEARCH.md Pitfall #2: this MUST land atomically — partial commits
       red CI between deletion and grid rewrite.
       EOF
       )"
       ```

    4. **Post-commit full-suite verification** — run `uv run pytest -q` and assert it stays at the 67P04 baseline (4158 passed / 26 skipped / 4 xpassed / 0 failed) MINUS the 2 deleted tests (so expect ~4156 passed / 26 skipped / 4 xpassed; the exact delta depends on how many parametrize rows the deleted tests contributed — verify it matches what `pytest --collect-only` predicted). Zero new failures permitted.
  </action>
  <verify>
    <automated>uv run pytest tests/repo/test_readme_shape.py tests/repo/test_repo_scrub.py -q 2&gt;&amp;1 | tail -5 &amp;&amp; uv run python3 scripts/launch/check_readme_grids_a11y.py &amp;&amp; find src/vibemix/midi -name '*.json' | xargs -I{} basename {} .json | sort | uniq -c | awk '$1 &gt; 1' | wc -l | awk '{exit ($1 == 0 ? 0 : 1)}' &amp;&amp; uv run pytest -q 2&gt;&amp;1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `find src/vibemix/midi -name '*.json' | xargs -I{} basename {} .json | sort | uniq -c | awk '$1 &gt; 1'` returns empty (DEV-02 SC verified).
    - `uv run pytest tests/repo/test_readme_shape.py -v` exits 0 with all parametrize rows GREEN.
    - `uv run python3 scripts/launch/check_readme_grids_a11y.py` exits 0.
    - `uv run pytest -q` exits 0; non-failure count is within ±3 of the pre-commit baseline (the 2 deleted test files contribute a small known delta — record the new baseline in the SUMMARY).
    - `git log -1 --stat` shows a single commit touching the expected files; no partial-state commit lurks between deletion and rewrite.
    - `git diff HEAD~ HEAD -- src/vibemix/midi/controllers/` shows only D entries (10 deletes, no As or Ms).
    - `ls docs/assets/controllers/` lists exactly the 10 new slugs (no leftover ddj-200 / kontrol / mc-6000 / mixtrack files).
  </acceptance_criteria>
  <done>
    Catalog reconciled atomically in one commit; CI gates (test_readme_shape + a11y script) GREEN; default pytest suite within ±3 of baseline; zero residual `controllers/` references in active code; migration note + SVG rotation complete; Wave 0 fully closes DEV-02 and unblocks Waves 1-4.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo CI gate | tests/repo/test_readme_shape + a11y script enforce README ↔ catalog parity; any rewrite that breaks this gate reds main on next push |
| contributor JSON | future contributor profile JSONs will validate against `profile.py::_parse_profile` — deletion of `schema.json` removes a parallel (dead) validator, NOT the live one |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-68P01-01 | Tampering | Atomic-commit assumption | mitigate | Pre-commit dry-run of `test_readme_shape` + a11y script in Task 3 step 2; refuse to commit on failure (per 68-RESEARCH.md Pitfall #2). |
| T-68P01-02 | Disclosure | docs/contributing/midi-catalog.md migration note | accept | Note documents the incompatible-schema rationale openly; the deleted controllers/ schemas survive in git history (no secret data). |
| T-68P01-03 | Repudiation | Cross-repo reference sweep | mitigate | Task 2's acceptance grep gate enumerates every reference site (README + test + a11y + KAAN-ACTION + docs/midi-mapping.md + .planning/PROJECT.md) per 68-RESEARCH.md §Runtime State Inventory load-bearing list. |
| T-68P01-04 | DoS | uv run pytest -q regression | mitigate | Task 3 step 4 explicitly re-runs the full default suite post-commit and asserts the baseline holds; any new red is a regression to roll back. |
| T-68P01-SC | Tampering | npm/pip/cargo installs | accept | This plan installs NO packages. `pyproject.toml` and `uv.lock` are untouched (verified via `git diff` in acceptance). |
</threat_model>

<verification>
- `find src/vibemix/midi -name '*.json' | xargs -I{} basename {} .json | sort | uniq -c | awk '$1 > 1'` returns empty.
- `uv run pytest tests/repo/test_readme_shape.py -v` GREEN against the rewritten 10-cell README grid.
- `uv run python3 scripts/launch/check_readme_grids_a11y.py` exits 0.
- `uv run pytest -q` exits 0 (full default suite; baseline within ±3 of 67P04's 4158-passed).
- `grep -rn "from vibemix.midi.map_loader\|MidiMapLoader\|src/vibemix/midi/controllers" src/ tests/ scripts/ docs/ README.md` (excluding `.planning/milestones/` archives and `docs/contributing/midi-catalog.md` migration narrative) returns zero hits.
- `git log -1 --stat` shows the reconciliation as a single atomic commit.
</verification>

<success_criteria>
DEV-02 closed (SC #2 from ROADMAP P68): the duplicated `controllers/` ↔ `profiles/` catalogs collapse to a single canonical directory (`profiles/`); the loser is deleted; a one-paragraph migration note exists at `docs/contributing/midi-catalog.md`; no broken imports; the README grid + test_readme_shape + a11y script + KAAN-ACTION + docs/midi-mapping.md + .planning/PROJECT.md all align with the canonical `profiles/` set; the entire reconciliation lands atomically in one commit; the default pytest suite stays GREEN.
</success_criteria>

<output>
Create `.planning/phases/68-all-devices-ready/68-01-SUMMARY.md` when done. Summary MUST record:
- New default-pytest baseline (passed/skipped/xpassed counts post-deletion of 2 tests).
- Exact commit SHA of the atomic reconciliation.
- The 10 SVG slug renames (with file size + sha256 of each new placeholder for the next plan to reference).
- Whether `docs/contributing/midi-catalog.md` was finalized in this commit or left a pointer to Wave 3 for `add-a-controller.md` (note the decision; the audit-trail matters when Wave 3 lands).
</output>
