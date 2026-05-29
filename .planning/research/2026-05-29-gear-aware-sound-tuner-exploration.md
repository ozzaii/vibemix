# Gear-Aware Sound Tuner — Exploration → Spec-Prep (v2, vibemix-grounded)

> **STATUS: EXPLORATION → SPEC-PREP. Not a final spec, no code yet.** This is v2 of the
> 2026-05-29 brain-dump, now **reconciled against real vibemix code** (every integration
> anchor re-verified with `file:line`) and **research-verified** (AutoEq/eqMac/Equalizer APO/
> spinorama/CATap licensing + formats checked at source). Decisions Kaan locked this session
> are marked **[LOCKED]**. Everything still routes through GSD (`/gsd-spec-phase` or
> `/gsd-plan-phase`) before any implementation.
>
> Origin: Kaan tuned his **JBL Quantum 100M2** (cheap white wired gaming headset) into a
> near-studio listening can via an AutoEq-derived parametric EQ. That sparked: *vibemix asks
> what gear you use at first run, then an agent researches that gear on the web, derives a
> correction, and gives you the config for a system-wide optimizer — better listening AND
> more accurate DJ monitoring.*
>
> Working name: **"vibemix Tune"** (rename freely).

---

## 0. LOCKED decisions (this session, 2026-05-29)

1. **[LOCKED] Home = vibemix opt-in module, config-generator architecture.** Not Bravoh, not a
   sibling tool. NOT a real-time in-engine audio DSP in v1 — vibemix **emits a config** that an
   external system-wide EQ host applies. Reuse the existing Viber/Codex/MCP agent + onboarding +
   CLAP. (Standalone-tool option was rejected specifically because it would lose the
   music-aware differentiator — see §5.4.)
2. **[LOCKED] Spine = GEAR optimization, not live music-adaptation.** The headline is "vibemix
   knows your gear → agent researches it → emits correction." The music-aware tilt is an
   **optional bonus layer**, not the v1 spine. Live, continuous adaptation is explicitly **P2**.
3. **[LOCKED] Honest "better DJing" = accurate headphone monitoring.** Correction-to-flat makes a
   DJ's monitoring *truthful* (this is what Sonarworks sells to DJs). The **live performance master
   (ASIO/dedicated interface) is guaranteed untouched** — confirmed by construction (§5.5).

---

## 1. Codebase reality check (re-verified against the live tree)

Each anchor below was checked by reading the actual source. **Two doc assumptions were wrong** —
flagged ❌.

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1 | Onboarding asks "Beginner/Int/Pro" + picks controller | ❌ **PARTIAL/WRONG** | `runtime/wizard.py` + `tauri/ui/src/wizard/onboarding-flow.ts:68` — steps are `tcc-grants`, `audio-device`, `controller-probe`, `ai-test-reaction`, + `step-profile-consent.ts` (yes/no learning). **No skill-level selector exists.** Controller IS picked. Adding gear = **new wizard step(s)** = a real (modular) surface extension, not "extend an existing question." |
| 2 | `profile.json` is a locked 5-field privacy contract | ✅ VERIFIED | `profile/schema.py:67` — `PROFILE_SCHEMA` `additionalProperties:false`, 5 required fields, `validate_profile()` rejects extras. **Gear must NOT be written here.** |
| 3 | Viber/Codex/MCP agent runtime + grounding pattern | ✅ VERIFIED | `library/toolset.py` (`seen:set` Gate#1 + library re-validate Gate#2), `mcp_server.py` (FastMCP STDIO), `codex_curate.py` (`codex exec` + timeout + re-validate), `telegram_bridge.py`. Codex is the product backend, no Gemini fallback. A new "gear lookup" tool follows this exact `def handler(self, args)->dict` pattern. |
| 4 | CLAP engine, 512-dim, lazy | ✅ VERIFIED | `library/clap_engine.py` — `CLAP_DIM=512`, ONNX default, deterministic 10s-chunk mean-pool, heavy imports lazy. Entry point for the music-aware tilt. |
| 5 | Evidence registry + citation/trust invariants, test-enforced | ✅ VERIFIED | `state/evidence_registry.py` (`parse_citations`), grounding linter, citation-schema-mirror tests. The new agent must **cite the measurement source or refuse** — maps 1:1 to invariants #2/#3. |
| 6 | Platform audio has an output-processing path | ❌ **CAPTURE-ONLY** | `platform/_audio_macos.py` + `_audio_windows.py` are **loopback capture only**. `find_output_device()` is UI-selection, not signal processing. **No in-engine output DSP exists today** → fine for config-gen (external host applies), but confirms P2 in-engine DSP is a genuinely new backend. |
| 7 | `model_router`, no hardcoded model literals | ✅ VERIFIED | `llm/model_router.py` `resolve(path)`, CI grep gate. If the gear agent ever calls a model, add a route — never inline. |
| 8 | Anti-creep CI gates (ports, IPC) | ✅ VERIFIED | ws ports locked `127.0.0.1:8765` (wizard/bus) + `8766` (debrief); `scripts/check_ipc_schema.py` enforces schema↔wrapper count-parity (new IPC msg ⇒ schema entry **and** Python wrapper, or CI fails). |
| 9 | `~/.cache/vibemix/` is the local store home | ✅ VERIFIED | `library/cache_paths.py:9`. Already holds `clap_embeddings.db`, `library.pkl`, `learn-progress.json`, `knowledge/`, etc. A new `gear.json` fits the precedent with **zero collision** *iff* it adds no new port/IPC. |

**Bottom line:** the grounding machinery, agent runtime, CLAP, model_router, store, and anti-creep
gates are all real and reusable. The only structural surprises: (a) gear capture means **adding a
wizard step or a settings-side opt-in surface** (no skill-level question to piggyback on), and
(b) there is **no output-audio path** today, which is exactly why config-generator (not in-engine)
is the right v1.

---

## 2. Research-verified findings (with the honest boundaries)

### 2a. Headphones — SOLVED, but data is per-source-licensed
- **AutoEq**: code is **MIT** (Apache-compatible). The **measurement DATA is per-source** —
  oratory1990 / Crinacle / RTINGS / Innerfidelity each have their own terms, and **at least one
  source is non-commercial**. Results are stored per-source (`results/<source>/.../<Model> ParametricEQ.txt`),
  so **per-source attribution is trivial**. ⇒ **Do NOT bundle the whole DB.** Use a
  commercial-safe subset (e.g. oratory1990) with attribution, or runtime-fetch against
  user-obtained data, and credit the measurer.
- **`autoeq` PyPI lib is too heavy** (pulls matplotlib/scipy/pandas/Pillow/soundfile) → breaks
  vibemix's torch-free/minimal-dep posture. ⇒ **Reimplement the FR→biquad math in-house**
  (RBJ shelf/peak biquads from Fc/Q/gain + a small PEQ fit, ~100 lines, standard DSP).
- **`autoeq-mcp` is immature** (single-author, ~0–3 stars, no releases) → **build our own thin
  grounded tool**, don't take the dependency.
- **Model-name resolution is the real UX problem.** ~8,800 models, named by the source's exact
  product string. Fuzzy "white JBL gaming headset" → exact model is non-trivial. For the
  **100M2-not-in-DB-but-100-is** case (which is Kaan's actual headset): using a sibling curve is
  **defensible ONLY if disclosed** — "no exact match; using JBL Quantum 100 (Rtings) as the
  closest sibling." Silent substitution = slop. This is the agent's job and maps to grounding.

### 2b. Speakers — voicing yes (license-gated), room no
- **spinorama.org**: real pre-computed anechoic PEQs at `datas/eq/<Model>/iir-*.txt` (plain REW/APO
  text). Covers common DJ monitors (**KRK RoKit, JBL LSR/308P, Yamaha HS** confirmed present).
  **BUT the whole repo is GPL-3.0 (code + data, no separate data license).** ⇒ **Do NOT vacuum it
  into the Apache tree.** Defensible path: **runtime-fetch the individual PEQ text by model name +
  attribute spinorama + zero GPL code in tree.** GPL-on-data is a legal gray area → **needs
  Francesco/lawyer sign-off before redistributing the files inside the binary**; runtime-fetch is
  the safer posture.
- **Honesty boundary (anti-slop, non-negotiable):** web data corrects the speaker's **own
  anechoic voicing**, NOT the user's **room**. Room correction provably needs a mic (Sonarworks
  averages **37 mic measurements**). ⇒ Label: **"Speaker voicing correction — adjusts your
  monitors toward their measured anechoic ideal; it does not measure or correct your room (that
  needs a microphone)."**
- IIR/PEQ correction degrades phase near crossovers (FIR would be needed for phase accuracy) —
  fine for tonal/voicing, note it for any accuracy claim.

### 2c. Delivery hosts (this resolves the v1 "emit vs bundle" fork)
| Host | OS | License | Config format | Apply mechanism | Verdict |
|---|---|---|---|---|---|
| **Equalizer APO** | Win | **GPLv2** | plain `config.txt`: `Filter: ON PK Fc 50 Hz Gain -10 dB Q 2.5` + `Preamp:` | **hot-reloads on save** (write file → instant) | **Primary Win target.** Strongest path: plain-text, live-applying. Install via Configurator (per-device, wants GUI). |
| **eqMac** | mac | **Apache-2.0** (🔑 not GPL — verified raw LICENSE) | **JSON preset (undocumented, version-fragile, import buggy)** | manual Finder "Open"; no CLI/URL-scheme | **Lead mac target but INSTRUCT, don't bundle** — bundleable legally, but the unstable schema + user-space driver make it fragile. |
| **SoundSource** | mac | paid, closed | no on-disk format; hosts AUNBandEQ | **Shortcuts "Set Effect Preset" + `shortcuts run` CLI** | **Optional premium target** (cleanest automation, but can't bundle, user must own it). |

- **Licensing rule (FSF/SFLC-backed):** *generating a config file for*, *CLI-invoking*, or
  *shipping an installer that downloads* a GPL tool = **mere aggregation, NOT derivation** → no
  copyleft reaches the Apache code. The only forbidden move is **embedding a GPL binary inside the
  distributed Apache bundle.**
- **DJ-safety holds by construction:** Equalizer APO is **WASAPI-shared only — ASIO/WASAPI-exclusive
  bypass it**; the macOS hosts act on the chosen *default* device, not a dedicated DJ interface. So
  a DJ's live master is outside all processed paths. ✅

### 2d. P2 in-engine path (validated, not for v1)
- **macOS = CoreAudio Taps (CATap)**: floor **macOS 14.2**, no virtual driver, low (not zero)
  latency. Reference impl **iQualize (MIT)** = CATap → lock-free ring buffer → `AVAudioSourceNode`
  → `AVAudioUnitEQ` → limiter; safe to study/adapt for an Apache tree.
- **Windows = a system APO pipeline** (Equalizer APO is the proof). Same ASIO bypass property.
- ⇒ P2 is real on both platforms; macOS floor is the main constraint.

### 2e. Competitor bar — Sonarworks SoundID Reference
Standalone + DAW plugin; **headphones via 500+ per-model presets (no mic)**; **speakers via
calibrated mic + multi-measurement**. **Differentiation gap:** it has **zero awareness of musical
content.** A CLAP-library-aware vibemix can tune *contextually* (per-genre/energy voicing, "this
track's low end will overload this monitor") and ship a free, gear-aware, no-mic "good-enough"
correction — turf Sonarworks doesn't touch. **This is why it belongs in vibemix, not as a
standalone AutoEq frontend.**

---

## 3. Recommended integration architecture ("the hot way")

**One sentence:** *vibemix asks your gear (opt-in), a grounded Codex tool looks up the measurement
and derives a parametric correction it can cite, and vibemix writes a system-EQ config + walks you
through installing the free host — correction-to-flat by default, an optional CLAP-driven musical
tilt on top, your live DJ master always untouched.*

**3.1 Gear capture (new opt-in surface — NOT profile.json)**
- Store gear in a **new `~/.cache/vibemix/gear.json`** (separate store, precedent §1.9). Never the
  5-field `profile.json`.
- Surface options (a real decision — see §6): (a) a **new optional wizard step**, or (b) a
  **settings-side "Tune my sound" opt-in** reachable any time. (b) is lower-friction and avoids
  bloating first-run; lean (b) with a one-line nudge in onboarding.
- Capture: headphone model + master output (monitor model | **"audio interface — don't touch"**).
  Manual pick from a bundled, attribution-tagged model list is the safe default; **auto-detect is
  impossible for analog** (3.5mm carries no model ID — proven on Kaan's Mac), partial for USB/BT.

**3.2 Tuner Agent (new grounded MCP tool, reuses the Viber/Codex pattern)**
- New tool(s) in the `toolset.py` style, exposed via `mcp_server.py`, run through Codex
  (`codex_curate.py`). E.g. `resolve_gear(description)→model+provenance`,
  `get_correction(model, kind)→{preamp, bands[], source_url, exact|sibling}`.
- The agent's *real* value (vs a static DB lookup): **fuzzy name resolution** ("white JBL gaming"
  → Quantum 100M2 — literally what worked this session), **sibling-curve disclosure** when no exact
  match, **scraping a measurement + running our biquad fit** when not pre-computed, and
  **explaining the correction**.
- **Grounding contract:** cite the measurement source (model + rig + URL) or **refuse** — no
  invented curves. Extends invariants #2/#3 to gear. Errors return dicts, never raise; wall-clock
  timeout like the existing tools.
- Math is **in-house biquad** (§2a), no `autoeq`/`autoeq-mcp` dependency.

**3.3 Delivery = HYBRID (emit always, guided-install, never bundle GPL)**
- **Always** generate the correct config for the user's OS/host.
- **Windows (primary):** write `config.txt` (hot-reloads instantly); guide the official Equalizer
  APO install (link/download + Configurator), never bundle the binary.
- **macOS:** lead with **eqMac** (instruct-and-link, despite Apache-2.0, because of fragile import);
  optional **SoundSource** premium target via the `shortcuts run` automation for users who own it.
- This is exactly Kaan's "give the code / system optimizers." Zero added latency liability,
  minimal new surface, GPL-clean by mere-aggregation.

**3.4 Music-aware tilt (the differentiator, opt-in, P1-optional)**
- Correction-to-flat = honest base. The Viber curator proposes an **optional** genre/energy tilt
  from **CLAP** analysis of what you play (techno → controlled sub + tamed harsh treble). Labeled
  **"flavor," default OFF**, never used for performance monitoring.
- This is the answer to "why vibemix and not a generic AutoEq frontend" (§2e).

**3.5 Consent + guarantee (state explicitly in UI)**
- Single opt-in toggle. System-wide affects **general listening only**; **live DJ master
  (ASIO/interface) guaranteed untouched** (§2c). Speaker tuning labeled "voicing, not room" (§2b).

---

## 4. Anti-creep reconciliation

| Locked constraint | This feature | Verdict |
|---|---|---|
| No new AI provider | Reuses Codex/MCP; no new provider | ✅ clean |
| No new ws port | Uses none / existing 8765 | ✅ clean if no new port |
| No new IPC family | Gear capture + "apply" likely need **1 new IPC msg** (`ipc.gear.*`) | ⚠️ allowed but must add schema entry **+** wrapper (CI parity), or run codegen |
| No heavy dep | In-house biquad; no `autoeq`/torch; data fetched not bundled | ✅ clean |
| No new surface | Gear capture is a **new opt-in surface** (no skill-level question to extend) | ⚠️ the one genuine creep — minimize via settings-side opt-in (§3.1) |
| Single-user local | All local; web fetch is read-only measurement lookup | ✅ clean |

**Net:** lowest-creep path is settings-side opt-in + 1 IPC message + in-house math + runtime-fetched
data. The "new surface" point is the only real tension and is a deliberate, bounded addition.

---

## 5. Dependency / licensing decisions (resolved)

- **Biquad math:** reimplement in-house (RBJ). **Do not** add `autoeq` PyPI (heavy) or `autoeq-mcp`
  (immature).
- **AutoEq data:** ship a **commercial-safe, attribution-tagged subset** (oratory1990-class) or
  runtime-fetch; credit each measurer; respect non-commercial sources. Never bundle the full DB.
- **spinorama data (GPL-3.0 whole repo):** **runtime-fetch by model + attribute + zero GPL code in
  tree.** **Redistributing the files inside the binary needs legal sign-off** (GPL-on-data is gray).
- **eqMac (Apache-2.0):** bundleable in principle, but **instruct-and-link** for engineering
  reasons (unstable JSON import, user-space driver).
- **Equalizer APO (GPLv2):** emit `config.txt` + guided install = mere aggregation, **clean**.
- **SoundSource (paid/closed):** optional, user-owned only, never bundled.

---

## 6. Phasing (proposal — GSD decides)

- **P1 — Config-generator.** Gear capture (opt-in surface + `gear.json`) → Tuner Agent (grounded,
  in-house biquad) → emit config + guided install (EAPO/eqMac). Honest, low-creep, immediate value.
  Optional CLAP tilt as a labeled flavor.
- **P2 — In-engine real-time correction.** CATap (mac 14.2+) / APO pipeline (Win), consent-gated.
  This is where "live adapt to what you play" can actually become continuous.
- **P3 — Mic measurement** for true speaker+room correction (the Sonarworks-Measure equivalent).

---

## 7. Open decisions for Kaan / Francesco (the genuine forks left)

1. **Legal sign-off (Francesco/lawyer):** redistributing spinorama (GPL-3.0) PEQ files + the
   non-commercial AutoEq source subset inside the shipped binary, vs runtime-fetch + attribution.
   This gates whether speaker correction ships "offline" or "fetch-on-demand."
2. **Gear-capture surface:** new optional **wizard step** vs **settings-side opt-in** (lean
   settings-side for lowest friction/creep). Kaan's call — it's the one real new-surface point.
3. **SoundSource premium target:** support the paid host's Shortcuts automation in v1, or skip?
4. **macOS floor for P2:** CATap needs **14.2+** — acceptable, or keep a BlackHole/eqMac fallback?
5. **Tilt in P1 or P2:** ship the optional CLAP flavor in P1 (more "vibemix-y") or hold for P2?

---

## 8. Sources

**Codebase:** verified in-tree — `runtime/wizard.py`, `tauri/ui/src/wizard/onboarding-flow.ts`,
`profile/schema.py`, `library/{toolset,mcp_server,codex_curate,telegram_bridge,clap_engine,cache_paths}.py`,
`state/evidence_registry.py`, `llm/model_router.py`, `platform/_audio_{macos,windows}.py`,
`scripts/check_ipc_schema.py`.

**AutoEq:** [github jaakkopasanen/AutoEq (MIT code)](https://github.com/jaakkopasanen/AutoEq) · [LICENSE](https://github.com/jaakkopasanen/AutoEq/blob/master/LICENSE) · [PyPI autoeq 4.1.2](https://pypi.org/project/autoeq/) · [results INDEX](https://github.com/jaakkopasanen/AutoEq/blob/master/results/INDEX.md) · [verIdyia/autoeq-mcp (immature)](https://github.com/verIdyia/autoeq-mcp)

**EQ hosts:** [eqMac (Apache-2.0)](https://github.com/bitgapp/eqMac) + [raw LICENSE](https://raw.githubusercontent.com/bitgapp/eqMac/master/LICENSE) · [Equalizer APO (GPLv2)](https://sourceforge.net/projects/equalizerapo/) + [config reference](https://sourceforge.net/p/equalizerapo/wiki/Configuration%20reference/) + [ASIO bypass thread](https://sourceforge.net/p/equalizerapo/discussion/general/thread/219a3df5f3/) · [SoundSource Shortcuts](https://rogueamoeba.com/support/manuals/legacy/soundsource5/?page=shortcuts) · [GPLv2 FAQ (mere aggregation)](https://www.gnu.org/licenses/old-licenses/gpl-2.0-faq.html)

**Speakers / honesty:** [spinorama (GPL-3.0)](https://github.com/pierreaubert/spinorama) + [eqs.html](https://www.spinorama.org/eqs.html) · [Sonarworks: room measurement techniques](https://www.sonarworks.com/blog/learn/what-are-the-measurement-techniques-used-by-soundid-reference-for-room-analysis) · [do I need a mic](https://www.sonarworks.com/blog/learn/do-i-really-need-a-measurement-microphone) · [miniDSP FIR vs IIR](https://www.minidsp.com/applications/dsp-basics/429-staging-fir-vs-iir)

**P2 engine:** [Apple CoreAudio Taps](https://developer.apple.com/documentation/CoreAudio/capturing-system-audio-with-core-audio-taps) · [iQualize (MIT, CATap ref)](https://github.com/DariusCorvus/iqualize) · [dechamps/APO notes](https://github.com/dechamps/APO)

**Competitor:** [Sonarworks SoundID Reference](https://www.sonarworks.com/soundid-reference)
