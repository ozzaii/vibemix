# LICENSE STRATEGY — Apache vs GPL for the vibemix client

**Synthesizer doc. HEAD ed081570. Read-only — no src/ or tauri/ edits, no commits.**
**Inputs synthesized:** MIXXX-ARSENAL (analyst 1), APACHE-COST/GPL-UNLOCK (analyst 2), THE ADVERSARY (analyst 3). Every claim is `file:line`, build-TOC, packet path, or explicit **NOT-FOUND**.

> This is a **Kaan business decision**, not an engineering one. The engineering verdict is already settled (clean-room works, the precedent is in tree). What's actually being decided is whether to trade Bravoh's frictionless reuse of its own warm-up project for a copyleft fence around it. This doc hands you the sharpest version of that trade.

---

## (1) THE QUESTION, IN ONE LINE

**Should the vibemix client stay Apache-2.0, or flip to GPL so we can vendor Mixxx's DJ-intelligence source directly — and what does that flip cost Bravoh's ability to reuse the code?**

---

## (2) MIXXX ARSENAL

What Mixxx actually offers, and whether a license flip is the lever that unlocks it. **Leverage** = how much it moves the core-value coach unlock or the growth wedge. **Port difficulty** is the *clean-room* cost (Apache-safe), since that is the real alternative to vendoring.

| Mixxx module | License | vibemix gap it fills | Clean-room port difficulty | Leverage | GPL flip needed? |
|---|---|---|---|---|---|
| **Serato crate/DB/GEOB reader** | format on Mixxx wiki; `triseratops` ref is **MPL-2.0** | NO Serato reader exists (`library/sources/__init__.py:6-8` "Serato later") | ~2d `struct.unpack`; GEOB decoder = **inverse of code we already own** (`export_serato.py`) | HIGH (growth/onboarding) | **NO** — Apache-clean |
| **Rekordbox master.db reader** | format; `pyrekordbox` = **MIT, already a dep** (`pyproject.toml`) | We read XML only (`library/sources/rekordbox.py`, refuses master.db by design) | ~1d — **just flip the policy**, wire the MIT dep we ship | HIGH (kills #1 onboarding friction) | **NO** |
| **Traktor `.nml` reader** | format; `traktor-nml-utils` ref | NO Traktor reader (Francesco's techno/house base) | ~0.5d XML, mirror `RekordboxLibrary.load_xml` | MED-HIGH | **NO** |
| **Engine DJ `m.db` reader** | **plain unencrypted SQLite** (no libdjinterop) | NO Engine reader | ~1.5d stdlib `sqlite3`; only cue/grid blob is real work | MED | **NO** |
| **EQ/filter response (`intel/eq_move_model.py`)** | RBJ Audio-EQ-Cookbook = **public domain** | The R-SLOP narrator→coach keystone (`GOLD-WIRING-MAP.md:74,82`) | **DONE this session** — 219 lines, zero Mixxx code (`eq_move_model.py:1`) | KEYSTONE | **NO** — Mixxx delegates to external fidlib; coeffs were never Mixxx's to give |
| **Beatgrid producer** | grid is in the file; `BeatGrid.from_anlz()` | Live exact grid for all reader users | ~0.5d; readers ARE the producer for the tagged-library majority | HIGH | **NO** |
| **`beatutils.cpp` Stage-D grid fitter** | GPL-2.0+ in tree (the one readable thing GPL would unlock) | Grid fit for untagged audio | ~1-2d, 430 readable lines of math (`mixxx-goldmine-map.md` H1/H2) | MED | flip would skip ~1-2d only |
| **Crossfader curve / sync corrector / AutoDJ planner** | GPL-2.0+ in tree | Transition coaching math | mostly **DONE** (`xfade.py`, `transition_clock.py`, `beatmatch_judge.py`, all Apache per `THIRD_PARTY_LICENSES.md:23-26`) | LOW-MED | flip would skip hours each |
| **Controller-mapping catalog (`res/controllers/`)** | mapping JS is GPL; **the `.midi.xml` data is mineable** | We ship ~10 maps; Mixxx has hundreds | ~30 min/device — transcribe data, don't port the QJSEngine | MED (feeds `recent_moves` evidence) | **NO** — mine data, not code |
| **Beat tracker / key-detection DSP / keylock** | external **qm-dsp** (GPL), **RubberBand** (GPL/commercial dual), **SoundTouch** (LGPL) | Untagged beat/key/time-stretch | **NOT in Mixxx tree** — numpy-from-paper or **MIT Beat-This ONNX** | HIGH but deferred | **flip unlocks NOTHING here** — see crux below |

**The arsenal's verdict:** the library-format **readers** are the bigger prize than the DSP, they're mostly **Apache-clean (not even GPL)**, and a "Universal Ingest" milestone (Serato + Traktor + Engine + master.db ≈ **5 focused days, zero GPL, zero spike risk**) is the highest-ROI library move available. The DSP gold is either already clean-roomed, public-domain math, or **lives in external libs the Mixxx checkout doesn't even contain.**

---

## (3) WHAT APACHE COSTS US / WHAT GPL UNLOCKS (quantified)

**Apache's standing cost = the clean-room tax.** It's real, but it's measured in **single days**, and most of it is already paid:

| Clean-room job | Apache tax | Done? |
|---|---|---|
| EQ biquads (`eq_move_model.py`) | ~1d | **DONE this session** |
| AutoDJ planner (`transition_clock.py`) | ~1d | DONE (394 lines) |
| Crossfader curve (`xfade.py`) | ~2h | DONE (75 lines) |
| Beatmatch grader (`beatmatch_judge.py`) | ~1d | DONE (167 lines) |
| `beatutils.cpp` Stage-D grid fitter | ~1-2d | NOT YET |
| `calcSyncAdjustment` nudge coach | ~hours (~30 lines) | NOT YET |

**Total remaining clean-room work GPL would let us skip: ~3-6 engineer-days, several already spent.**

**What GPL unlocks — and the crux that nukes the premise:** the seductive pitch is "flip, then `git clone mixxx && cp` for instant beatgrid+key+sync." **It is fantasy.** The algorithms vibemix wants *most* — the onset detection function, tempo/beat tracker, key-detection core (`GetKeyMode`), WSOLA keylock — **are NOT in the Mixxx source tree**. They live in external GPL libs (qm-dsp, RubberBand) that Mixxx's own analyzer is a ~116-line wrapper around (`recovered/wf_c297207c-6ae__ALT1...md:0,85`; `mixxx-goldmine-map.md:114-117`). Flipping vibemix to GPL would let you vendor *qm-dsp separately* — pulling a Cython/C++ DSP lib into a **stated torch-free, librosa-free, ONNX numpy runtime** across macOS+Windows PyInstaller builds. That's a worse engineering position than the recommended path (numpy-from-paper, or the **MIT Beat-This ONNX** model that fits the existing `cue_detr.py` pattern).

**So GPL's entire copyable yield = the grid-fitter + EQ + curve + planner = ~3-6 days, mostly already done. The hard stuff GPL is sold on, GPL does not deliver.**

---

## (4) WHAT GENUINELY BREAKS IF WE FLIP — the Bravoh-reuse crux

This is the decision's center of gravity. Everything else is secondary.

**Apache exists for exactly one stated strategic reason:** CLAUDE.md — *"Apache 2.0 ... Permits Bravoh internal reuse."* The architecture treats vibemix as **Bravoh's OSS warm-up that feeds the commercial product** — `partner-capabilities.md:167`: *"Every DJ who installs vibemix is one who can experience Bravoh's quality bar before joining the wider product path."* Under Apache, Bravoh (closed, commercial) lifts `intel/`, `coach.py`, the citation-grounding gate, the CLAP engine — any of it — into the closed backend with an attribution notice and moves on.

**GPL slams that door — and the mechanism is brutal because of process topology:**
- vibemix is **one Python process**. There is no network boundary between "client" and intelligence — `eq_move_model.py` is `import`ed by `state/deck_context.py` in the same interpreter (`GOLD-WIRING-MAP.md:76`, call site `apply_live_claim_guard:2342`). GPL's combined-work test treats same-process import as a derivative work. If vibemix is GPL and Bravoh's closed backend imports any vibemix module, the conservative legal reading every commercial shop uses is that **the Bravoh code linking it becomes GPL-obligated.**
- The "arm's-length socket/subprocess boundary" escape is the discipline our memory already encodes for *inbound* third-party GPL deps (`project_vibemix_gpl_runtime_dep_ok`). But the polarity inverts and gets far more painful: it's no longer "vibemix imports one GPL pip package," it's "**Bravoh — the product you actually monetize — can no longer freely absorb vibemix's intelligence.**" You'd fence your own crown jewels in copyleft, then engineer around your own fence forever.

**What does NOT break (the genuinely-true half of the pitch):**
- **A GPL desktop binary is fine and common** — Mixxx itself ships exactly this. We already ship a signed `.dmg`; the repo is already public, so the GPL "provide source" obligation is essentially met in spirit.
- **The commercial proxy moat stays closed under ANY license.** The live brain is a network `genai.Client` with a `base_url` override (`agent/proxy_client.py:33-42`) pointed at `api.altidus.world`; the server lives in `/var/www/bravoh-clean-backend` (memory `project_vibemix_proxy_deployed_altidus`) and is **never distributed** — only contacted over the network. GPL-2.0/3.0 do not treat network interaction as distribution (the ASP loophole). The only license that closes that loophole is **AGPL — and AGPL is NOT-FOUND anywhere in this tree** (grep `agpl|affero` across `src/` + `pyproject.toml` = empty, verified). So a GPL client + proprietary proxy is a **clean, lawful split.** The hosted moat survives the flip.

**The one live compliance fact — and it cuts AGAINST the flip:** the GPL-2.0 `mutagen` package is **already in the last frozen macOS build**. Verified: `build/vibemix-core.macos/Analysis-00.toc` has **96 mutagen entries** (`mutagen`, `mutagen.id3`, …). It's pulled transitively — `collect_submodules("vibemix")` follows `library/export_serato.py`'s lazy `from mutagen.id3 import ID3` (`:182,195`), even though mutagen is **NOT** explicitly in `vibemix-core.macos.spec`'s datas/hiddenimports and is gated behind the opt-in `serato` extra (`pyproject.toml:182-183`). **Translation: our "Apache-licensed client" DMG already ships GPL code today.** PyInstaller erases the "separate pip package, lazy-imported" distinction the runtime-import rule leans on — in a frozen onedir bundle, the bytecode is in the DMG either way. This is a real compliance task **regardless of the flip**, and using a project-wide GPL flip to "fix" it would be paying for the disease to cure one optional cue-tag-writer symptom.

---

## (5) DECISION MATRIX

| | **A. STAY APACHE (clean-room only)** | **B. DUAL-LICENSE / MODULE-SPLIT** | **C. FLIP CLIENT TO GPL** |
|---|---|---|---|
| **Unlocks** | All readers (Apache-clean) + EQ keystone (public math) + all clean-room DSP. Universal Ingest in ~5d. **Everything of value.** | Same as A, plus the *option* to vendor a single isolated GPL/LGPL module behind a hard process boundary (e.g. a separate-process key/keylock binary) without copyleft-ing the core. | Direct vendoring of `beatutils.cpp` grid-fitter + EQ + curve + planner (~3-6d saved, most already spent). Auto-resolves the mutagen wrinkle (GPL whole may contain GPL parts). |
| **Costs** | The clean-room tax (~3-6d remaining, mostly done). Must clean up the mutagen-in-DMG wrinkle. | Engineering overhead of a maintained process boundary + a second license surface to reason about. Most complex to govern. | **Permanent loss of frictionless Bravoh reuse** (must process-isolate forever). Re-papers 6 README mentions + every launch doc + partner one-pagers + the framing in a **signed NDA** (`nda-meturavers.md:53`). Contributor-friction tax on the controller-mapping/DJ-hacker community you want upstreaming. Jeopardizes the lean torch-free runtime if qm-dsp gets vendored. **One-way door.** |
| **Client** | Stays Apache, forkable, BYO-key promise intact (`README.md`). | Core stays Apache; an isolated module may carry GPL/LGPL via boundary. | Becomes GPL; published Apache history stays forkable forever anyway, so the flip doesn't even *close* what's out — it only forks the future into a more restrictive track. |
| **Bravoh** | **Frictionless reuse** (the stated reason for Apache). | Reuse preserved for the Apache core; the isolated module is process-called, not linked. | **Reuse forbidden** without arm's-length isolation of Bravoh's own crown-jewel intelligence. The expensive break. |
| **Proxy** | Clean (network ≠ distribution). | Clean. | **Still clean** (no AGPL). The moat survives regardless. |
| **Reversibility** | Can always relicense *to* GPL later. | Reversible per-module. | **Irreversible** — cannot Apache a GPL project. |

**The killer asymmetry:** Apache→GPL is a one-way door. The unlock GPL buys = a handful of days of clean-room work you're *already doing competently*. The price = permanent loss of Bravoh-reuse freedom + re-papering a contractual commitment + runtime risk. **And the hard DSP it's romanticized on isn't in Mixxx to copy anyway.**

---

## (6) RECOMMENDATION — with the honest tradeoff stated

**Choose A: STAY APACHE-2.0. Do not flip. Kill the GPL romance — it solves a problem you do not have.**

The sharpest version of the trade, stated honestly: **you would be trading the single stated strategic purpose of the license (Bravoh frictionlessly eating its own warm-up project) for ~3-6 engineer-days you're already spending well — and for that price you do NOT even get the hard Mixxx DSP, because beat/key/keylock live in external libs the Mixxx tree doesn't contain.** You can build the *entire* narrator→coach unlock — EQ physics, beatmatch grader, transition scorer, every library reader — under Apache, today, clean-room, with the precedent already shipping in tree (`THIRD_PARTY_LICENSES.md:8-26`; `eq_move_model.py` written from the RBJ cookbook this session). **The license is not the bottleneck; the missing `BeatGrid` producer is — and Apache builds it just fine** (the readers ARE the beatgrid producer for the tagged-library majority).

**The honest caveat where STAY-APACHE is genuinely weaker (don't let me lie to you):** if a future feature has a *hard* dependency on **RubberBand-grade keylock/time-stretch** and the WSOLA-from-paper / ONNX substitute proves not good enough, GPL (or buying RubberBand's commercial license) becomes the only legitimate path. **But even then the right move is a commercial RubberBand license — option B's isolated-module boundary — not a project-wide copyleft flip.** Keylock is correctly deferred behind a spike and is not a v1 blocker. So this caveat is real but **not yet load-bearing**; keep **B (dual-license / module-split)** in your pocket as the escape hatch for exactly that one future module, and never as a reason to copyleft the core.

**Two concrete actions that fall out of A, independent of the license decision:**
1. **Clean up the mutagen-in-DMG fact** so the Apache claim is actually true: either exclude `vibemix.library.export_serato` from the frozen bundle, or write the ~1-afternoon clean-room ID3-GEOB tag writer and drop mutagen entirely, or at minimum ship a mutagen source-offer + NOTICE for that component. (`build/vibemix-core.macos/Analysis-00.toc` proves it ships today.)
2. **Build Universal Ingest in parallel with the EQ keystone** — disjoint trees (`library/sources/` vs `intel/`), ~5 Apache days, zero GPL, and every reader also delivers beatgrids + keys + cues, feeding three DSP gaps for free.

---

## RETURN SUMMARY (≤300 words)

**Recommended option: A — STAY APACHE-2.0 (clean-room only).** Keep B (dual-license / isolated module-split) in your pocket as the future escape hatch for one specific module, never the core.

The GPL flip is justified by wanting Mixxx's DJ intelligence — and that justification is a **category error your own packets already refute**. Every value-bearing Mixxx algorithm is either (a) public-domain math you can clean-room — RBJ EQ cookbook, Krumhansl key profiles, WSOLA — with the precedent already shipping in tree (`THIRD_PARTY_LICENSES.md:8-26`; `eq_move_model.py` written from spec this session, 219 lines, zero Mixxx code), or (b) external GPL libs (qm-dsp, RubberBand) that **are not in the Mixxx checkout**, so a flip unlocks nothing copyable there anyway. The library-format **readers** are the bigger prize and they're **Apache-clean, not even GPL** — Universal Ingest (Serato + Traktor + Engine + master.db) ≈ 5 days, zero GPL, zero spike risk.

**What the flip would cost:** GPL's same-process combined-work test would **fence Bravoh out of its own warm-up project** — the one stated reason Apache was chosen (CLAUDE.md). It re-papers six README mentions, every launch doc, and the framing in a **signed NDA** (`nda-meturavers.md:53`). It's a **one-way door**. And it buys only ~3-6 engineer-days, most already spent.

**What survives the flip — and so doesn't need it:** the commercial proxy moat is network-only (`proxy_client.py:33-42`), and **AGPL is NOT-FOUND** in the tree, so a GPL client + proprietary proxy is lawful regardless. The moat is the hosted brain, not the client code — so GPL protects nothing you need.

**The one live GPL fact — `mutagen` already in the frozen DMG** (`build/vibemix-core.macos/Analysis-00.toc`, 96 entries) — argues the *opposite* of the flip: clean up that one optional dep so the Apache claim is true, rather than copyleft-ing the whole stack to retroactively bless a cue-tag writer.
