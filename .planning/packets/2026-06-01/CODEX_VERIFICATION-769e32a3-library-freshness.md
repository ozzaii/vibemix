# CODEX VERIFICATION — HEAD `769e32a3` library freshness / user-file discovery

> Read-only verifier packet. Produced by Claude swarm (`wf_35794ea4`, 6 agents) + orchestrator cross-check + a LIVE read-only cache probe. Pinned **HEAD `769e32a329af8b63c35695becb06fa9f2280dc6a`** ("fix(library): reject fixture-backed user cache"), parent `32873bcb` ("detect sources for freshness nudges"). Date 2026-06-01.
> Raw evidence: `_verify-library-freshness-769e32a3-raw-wf_35794ea4.json`. Workflow script: `…/workflows/scripts/verify-library-freshness-769e32a3-wf_35794ea4-c7f.js`.
> ⚠️ Tree is shared/moving — re-pin + re-run the SRC anchors before routing if Codex has landed past `769e32a3`.

## Verdict summary

| # | Claim | Verdict | Tier |
|---|---|---|---|
| 1 | Production cache cannot load repo fixtures | **TRUE** | SRC |
| 2 | Backup `.v1bak` fallback matches `try_load_cache` | **TRUE (parity)** — but no *new* writer; see LIVE | SRC + LIVE |
| 3 | UI nudge stays honest for folder-backed sources | **TRUE on anti-slop axis**, wrong-remediation gap | SRC |
| 4 | Smallest next LAND package for folder re-index | **Scoped → `folder-reindex-from-nudge`** | — |
| ★ | LIVE: what the co-host actually loads on Kaan's rig | **1547 real tracks via `.v1bak`** (not empty) | LIVE |

**Bottom line for Codex A:** the two commits are SOUND and well-tested. Ship-safe at SRC. One real user-facing gap (folder DJs can't act on their own stale nudge) → one small follow-up package, **release-only, HOLD_WITH_GATE**. Two hygiene items (clean the poisoned primary; fix a misleading docstring) are SAFE_NOW. PKG tier is **unproven** (no `find dist/` check run).

---

## ★ LIVE finding (read-only cache probe — resolves a critic contradiction)

The swarm critic claimed the fix leaves Kaan's co-host loading an **empty** library. That is **FALSE**. Direct read-only inspection of `~/.cache/vibemix/` (vibemix's own cache, not an off-limits path):

```
library.pkl       1.6k  version=2  tracks=5     xml_path='tests/library/fixtures/synthetic_collection.xml' (RELATIVE)
                  → _is_user_library_cache_path=True, _is_repo_test_fixture_source_path=True → REJECT (fixture) ✓
library.pkl.v1bak 272k  version=1  tracks=1547  xml_path='/Users/ozai/Music' (dir, exists)
                  → not a fixture, source exists → LOAD
FINAL  try_load_cache() → True   loaded_tracks=1547   lib.xml_path='/Users/ozai/Music'
```

**Interpretation:**
- The poisoned primary (`library.pkl`, a 5-track v2 fixture cache from a dev probe at 16:45) is correctly **rejected** by HEAD's guard.
- `try_load_cache` then falls through to `library.pkl.v1bak` — a **real 1547-track v1 backup** (a `/Users/ozai/Music` folder-ingest from 2026-05-21 13:11) — and loads it. `xml_path` is a directory, so the mtime-staleness reject is intentionally bypassed (`_try_load_cache_path` rekordbox.py:325 `… and not os.path.isdir(blob.xml_path)`) — by design, so the live pill never loses its library on a folder mtime bump.
- **Net: the co-host loads a real library on Kaan's rig.** The `.v1bak` fallback the SRC verifiers called "dormant/dead code" is in fact **load-bearing here** — it is a v1→v2 schema-migration artifact that is doing exactly its job (survive primary poisoning → fall to known-good backup). "No *new* writer exists in current source" is TRUE; "the fallback is inert" is **falsified by disk**.

**Caveats that ARE real:**
- The backup is a **10-day-old snapshot** (2026-05-21) of `/Users/ozai/Music` — real, but possibly behind the current library. Freshness-status (dir path → `_catalog_tree_mtime`) would correctly report it `stale`; the *load* path tolerates it (correct).
- If `.v1bak` were ever **absent** (a fresh rig, or a user without the migration artifact), the same poisoning WOULD load empty. So the critic's "empty" outcome is the **no-backup** case, not the current rig.
- Nothing **cleans** the poisoned primary — every boot logs `library: ignoring user cache because it points at a repo test fixture: …` and falls through. Works, but it's log-spam + a latent trap if a future reader trusts `library.pkl` directly.

---

## Claim 1 — Production cache cannot load repo fixtures → **TRUE (SRC)**

Guard at `rekordbox.py:307-314` (helpers `_is_user_library_cache_path` :72-85, `_is_repo_test_fixture_source_path` :88-99). Rejects a blob when the cache path is the production shape **AND** the recorded source resolves into the repo's `tests/…/fixtures/…`. Returns `None` → `try_load_cache()` continues to `.v1bak`, else `False` → caller re-parses via `load_xml` → never serves fixture tracks.

Verified (swarm, with probes):
- **Both names covered:** `library.pkl` and `library.pkl.v1bak` match the allow-list (`rekordbox.py:81-85`); `try_load_cache` iterates both (`:277-280`).
- **Absolute fixture rejected; real user XML NOT rejected** (`~/Library/Pioneer/rekordbox/collection.xml` → False; `/etc/hosts` → False).
- **Symlinked fixtures CAUGHT** via `resolve(strict=False)` (`:93`).
- **Relative source → fail-closed** (`load_xml` stores `str(path)` verbatim `:230,235`; the `ValueError` branch `:94-97` substring-matches `tests`+`fixtures`). This is how the LIVE poisoned primary (a *relative* `tests/library/fixtures/…` path) gets caught.
- **Frozen build:** guard is a benign no-op (`parents[3]` ≠ repo → `ValueError` → absolute user path returns False). Acceptable **iff** no `tests/fixtures` ship in the bundle — **PKG-unproven**, see risks.

SRC proof: `tests/library/test_rekordbox.py::test_user_cache_ignores_repo_fixture_source` (added in `769e32a3`, L181-191) monkeypatches `CACHE_PATH` to a production-**shaped** tmp path, loads the FIXTURE, asserts `try_load_cache() is False` and `len()==0`. **1 passed.** Plus `test_staleness.py::test_freshness_status_rejects_user_cache_pointing_at_test_fixture` and `…_payload_never_refreshes_test_fixture_source`.

---

## Claim 2 — `.v1bak` backup fallback matches `try_load_cache` → **TRUE parity; no new writer (LIVE-populated by migration)**

- **Suffix construction byte-identical:** `rekordbox.try_load_cache` `:279` `CACHE_PATH.with_suffix(CACHE_PATH.suffix + ".v1bak")` vs `staleness._legacy_cache_path` `:132` `pkl.with_suffix(pkl.suffix + ".v1bak")`. Both → `library.pkl.v1bak`. Same base path object (`RekordboxLibrary.CACHE_PATH` ≡ `DEFAULT_LIBRARY_PKL`). Proven empirically.
- **Fallback fires in both freshness branches** — pkl-missing (`staleness.py:174-176`) and fixture-reject (`:244-248`); the `reason != "cache_points_to_test_fixture"` check (`:247`) prevents returning a backup that's *also* poisoned.
- **Recursion guard sound:** `_legacy_cache_path` returns `None` when name ends `.v1bak` (`:130-131`) → exactly one level, no infinite loop / no `.v1bak.v1bak`.
- SRC pin: `test_staleness.py::test_freshness_status_uses_real_backup_when_primary_cache_is_fixture` (L172-193) asserts `cache_path == str(backup_cache)`.

**Nuance (was the swarm's "critical hole", now corrected by LIVE):** grep finds **no writer** of `.v1bak` in current `src/` — both `rekordbox._write_cache` (`:354,365,369`) and `folder_ingest._write_library_cache` (`:309,312`) write only `library.pkl`. SRC conclusion "dormant" is right for *new* writes. **But disk shows a populated 272k v1 `.v1bak`** — a leftover from an older app version's v1→v2 migration (version field is the tell). So: the parity is real AND the fallback is currently live-functional on rigs that carry the migration artifact; it is NOT guaranteed for fresh installs. If real resilience is wanted going forward, add a rotation in `_write_cache` (rename prior `library.pkl` → `library.pkl.v1bak` before `os.replace`). Until then it's forward-compat scaffolding that happens to be filled here.

---

## Claim 3 — UI nudge honesty for folder-backed sources → **TRUE on the anti-slop axis; wrong-remediation gap**

End-to-end trace (swarm ran the real functions, not asserts):

| Stage | Folder source, changed (stale) |
|---|---|
| `library_freshness_status` | `status=stale, reason=source_newer_than_cache, source_path=/…/Music` |
| `_refreshable_source_path` (`:67-75`) | **`None`** — folder path fails `suffix == ".xml"` |
| `freshness_nudge_payload` (`:328`) | `source_path: None`, `reason: source_newer_than_cache` |
| `staleness-banner.ts::show(0, null, …)` (`:79-86`) | copy **"Drop the Rekordbox XML below."**, refresh button **hidden** |

- **Anti-slop gate PASSES:** a changed folder is reported `stale` and a nudge fires; status is **never** falsely `fresh`. Nested-crate edits are caught (`_catalog_tree_mtime` `:97-119`; `test_freshness_status_stale_when_nested_folder_file_newer`).
- **Remediation is wrong-action:** a folder DJ (no XML) is told "Drop the Rekordbox XML below" with no re-index button. Honest about *staleness*, mis-prescribes the *cure*. This is the seam for the package below.
- **Consent intact:** `_detect_library_source_path` (`:78-94`) only detects `collection.xml` via `.is_file()` — folders are **never** auto-detected/indexed; the "Import library" affordance only ever fires for XML.

SRC proof: `tests/library/test_staleness.py` 31/31; UI `staleness-banner.spec.ts` 10/10 (pins the no-source → "Drop the Rekordbox XML" branch at L162-180).

---

## SRC proof tier (test runs at HEAD `769e32a3`)

| Command | Result |
|---|---|
| `pytest -q tests/library/test_staleness.py tests/library/test_rekordbox.py` | **50 passed, 0.57s** |
| 5 targeted new tests (`-v`) | **5 passed, 0.20s** |
| `vitest run tests/settings/staleness-banner.spec.ts` (local bin, no install) | **10 passed** |

No NOT-RUN. **SRC only** — no PKG (signed build) or LIVE-rig (FLX4/Rekordbox) evidence beyond the cache probe above.

---

## ★ NEXT LAND PACKAGE — `folder-reindex-from-nudge`

**Why:** A folder-backed DJ (used `embed-folder` / `ingest_folder`, the no-Rekordbox path) whose tracks changed gets a correct stale nudge but the only affordance is "Drop the Rekordbox XML" — which they don't have. The freshness work in `32873bcb`+`769e32a3` made folder sources *detectable* + *stale-aware*; this makes the folder nudge *actionable*. Closes the half-wire for the no-Rekordbox DJ.

**The live trap (mapped, must avoid):** you **cannot** reuse `ipc.library.import` for folders — its handler `_on_library_import` (`__main__.py:1971`) → `importer.import_library` → `RekordboxLibrary.load_xml` → `pyrekordbox.RekordboxXml(path)`, which **raises** on a directory. A folder must route to `ingest_folder`, a distinct action.

**Files (smallest-first):**
1. `staleness.py:67-75` — broaden `_refreshable_source_path` (or add `_reindexable_source_path`) to also accept `Path(source_path).is_dir()`. ~4 lines; this alone flows the folder path through the nudge.
2. `staleness.py:325-331` — `freshness_nudge_payload` passes it through for free once (1) lands; add a `source_kind` ("xml"|"folder") field so the UI/handler branch deterministically. Mirror in `watcher.py` emit.
3. `ui_bus/messages.py` (`LibraryStalenessNudgePayload` + action payload) **and** `tauri/ui/src/ipc/messages.schema.json` — add `source_kind` + a `reindex` action. **REQUIRES `npm run codegen:ipc`** (pre-compiled ajv — memory `feedback_schema_edit_needs_codegen_ipc`).
4. `staleness-banner.ts:71-110` — `source_kind === "folder"` → button "Re-index folder", copy "Re-index to keep Viber grounded."; click emits the folder action.
5. `__main__.py:2057-2064` — `_on_library_staleness_action`: keep `dismiss`/`snooze_7d` → `apply_snooze_action`; add `reindex` → build embedder+store (mirror `_on_library_import` :1985-1998), call `ingest_folder(Path(recorded_path), …)`, refresh `evidence_registry.register_library`. **Recorded path must come from `library_freshness_status().source_path`, NOT renderer input** (un-spoofable).

**Smallest-possible cut:** steps 1+4+5 only — reuse the existing `staleness_action` enum with a literal `"reindex"`, sniff `is_dir()` in the handler, UI re-sniffs suffix for button copy. Drops the schema edit + `codegen:ipc` gate, ~10 fewer lines, one fewer gated surface.

**Tests that pin current behavior (update):** `staleness-banner.spec.ts:162-180` (add a folder `source_kind` case; the true-no-source case stays valid); re-grep `test_staleness.py` for any `_refreshable_source_path → None for dir` pin; `mock-transfer-contract.spec.ts` if the action enum changes.

**Blast radius:** Localized. `_refreshable_source_path` is consumed only by `freshness_nudge_payload` + `_should_emit_nudge`. **No `MusicState`/coach/reaction-loop surface** (Invariants #1/#2/#3 untouched). The XML `_on_library_import` path is untouched.

- **Blocks:** **release-only** (user-facing completeness; not A/B/C-blocking).
- **Gate:** **HOLD_WITH_GATE** → `vibemix-grounding-review` (it changes what the UI tells the user about library state + triggers a re-embed feeding EvidenceRegistry — confirm a folder re-index can't leave the registry on stale embeddings) **+** `ipc-wiring-checker` + `npm run codegen:ipc` (new IPC action, both-ends-wired).
- **Tiers achievable:** SRC + PKG. **LIVE** (real folder going stale → re-index on Kaan's rig) = post-merge KAAN-VERIFY (`drive-vibemix`).

---

## Secondary findings — ranked (for the board)

| Sev | Finding | Evidence | Disposition |
|---|---|---|---|
| HIGH | Poisoned `library.pkl` still on disk; never cleaned — boot log-spam + latent trap (a future reader trusting the primary gets 5 fixture tracks) | LIVE probe; `rekordbox.py:310` warns to stderr only | **SAFE_NOW** hygiene: on fixture-reject, quarantine/rename the poisoned primary (or surface the warning to UI). Tiny. |
| MED | Relative-path fixture guard can reject a *legitimate* user library whose relative import path contains `tests`+`fixtures` (substring, no repo-root gate) | `rekordbox.py:94-97`; reject logs to stderr, not UI → user sees empty co-host, no error | **HOLD_WITH_GATE**: dev-only in practice (app passes absolute paths), but if surfaced, gate `vibemix-grounding-review`. Critic rated HIGH; orchestrator down-rates to MED (real-user trigger is narrow). |
| MED | PKG tier unproven — fixture-reject is a no-op in the signed build; relies on "no `tests/fixtures` ship" | nobody ran `find dist/ -path '*tests/fixtures*'` | **SAFE_NOW** one-liner: run that find against `dist/` + the build TOC to close PKG. |
| LOW | `folder_ingest._write_library_cache` docstring says `xml_path = 'folder:<root>' marker`; code writes a **plain** resolved path | docstring `folder_ingest.py:288` vs code `:298`; `folder:` prefix only on `track_id` `:214` | **SAFE_NOW** doc fix. Latent trap: "fixing" code to match the docstring would break `Path(source_path).is_dir()` staleness detection. Leave code; fix the comment. |
| LOW | Second cache-load entry `RekordboxSource.iter_tracks` (`sources/rekordbox.py:120`) uses a weaker `xml_path == resolved_path` guard; safe today (rejected primary → empty `xml_path` → fresh parse) but never traced by tests | swarm critic | **RESEARCH_ONLY** — add a coverage test for the curate/build-set read path. |

---

## Codex A routing recommendation

1. **Accept `769e32a3` + `32873bcb`** — sound, SRC-proven, anti-slop gate holds. No changes required to land.
2. **SAFE_NOW (no gate):** quarantine the poisoned primary on reject (HIGH hygiene); `find dist/` PKG check; folder-ingest docstring fix.
3. **HOLD_WITH_GATE (release-only):** `folder-reindex-from-nudge` — the natural close-out of the freshness feature; gate `vibemix-grounding-review` + `ipc-wiring-checker`.
4. **KAAN-VERIFY (LIVE):** the dev cache is self-healing via a 10-day-old `.v1bak`. Recommend a fresh `uv run python -m vibemix library ingest` (or `embed-folder ~/Music`) so LIVE proofs run against a *current* real library, not a stale-but-real backup — and so the poisoned primary gets overwritten by a clean v2 cache.
