## ING12 — DOCS / README honesty (partner-copy + CI-gate preservation)

**Read at HEAD `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04). The SHIP-MAP-MASTER maps were synthesized at `7ac35a84`; HEAD is several commits ahead (`d7d5337a` ← `322e8c44` ← `d67e6f81` ← `b40e81cd` ← `2337bc8d`). Where the maps are now stale on the voice/packaging gate, I correct inline and flag `[MOVED SINCE MAPS]`.

**Scope of this ingest:** public-facing docs honesty only — `README.md`, the launch docs, and the README-linked public docs (`SECURITY.md`, `PRIVACY.md`, `docs/code-signing-policy.md`, `docs/launch/github-meta.md`). NOT product code; NOT dev/contributor docs where naming a model is allowed by CLAUDE.md ("Internal docs/code may name Gemini").

**Proof tiers:** SRC (green test on source) ≠ PKG (in a signed DMG at HEAD) ≠ LIVE (a real user reaches it). README/docs are a SRC-tier artifact: their honesty is verified by the 4 CI gates + by-eye against the partner-copy policy. None of them are PKG/LIVE — a stranger reads them on the public GitHub repo, so the "policy violation" surface IS the user-facing surface.

---

### 0. Verdict headline

The README is **CLAIMED-shippable but DARK on partner-copy honesty**: all 4 CI gates are GREEN at HEAD (verified by running each), but the gates do NOT enforce the partner-copy policy, so every policy violation rides green. The README leaks model names (Gemini ×9, MOSS ×3), the internal proxy host (`api.altidus.world` ×3), a wrong security domain (`bravoh.com`), a wrong org slug (`ozzaii` ×1), a stale MOSS-voice claim that now contradicts source (Chatterbox-only landed), a djay-Pro-first claim that contradicts the Kaan-locked macOS-arm64 v1 shape, and a full dev feature-matrix dump (Phase numbers + 5 commit SHAs + "Kaan ear-passes daily" + KAAN-ACTION). **LANDED-but-DISHONEST**, not NOT-STARTED.

---

### 1. Partner-copy policy violations (file:line) — README.md

Policy: NO model names ("Gemini"/"MOSS" → "AI model"/"on-device voice"); NEVER expose `api.altidus.world` (→ "Bravoh's hosted service"); domain `bravoh.ai` NOT `bravoh.com`; org `bravoh-ai` NOT `ozzaii`.

**"Gemini" — 9 occurrences (PUBLIC marketing/FAQ surface, all violations):**
- `README.md:39` — "Live co-host calls go to Bravoh's **Gemini** proxy at `api.altidus.world`" (double violation: model + host)
- `README.md:61` — "live audio is streamed to Bravoh's **Gemini** proxy for analysis"
- `README.md:140` — feature-matrix Phase 96 cell: "AST gate lands BEFORE **Gemini** wiring" (this is dev-slop, see §3; also a model leak)
- `README.md:149` — feature-matrix Phase 80 cell: "**Gemini** as Secondary Ear" (dev-slop + model leak)
- `README.md:241` — "forwards to Google **Gemini** for grounded reaction planning"
- `README.md:259` — FAQ Q2: "forwards to Google **Gemini** for analysis"
- `README.md:269` — FAQ Q5 heading: "Why **Gemini** and not GPT / Claude / Llama?"
- `README.md:271` — FAQ Q5 body: "Sven uses Bravoh's **Gemini** path"
- `README.md:283` — FAQ Q8: "**Gemini** is Google's … point it at your own **Gemini** API key" (×2 on one line)
- `README.md:287` — FAQ Q9: "point vibemix at your own **Gemini** endpoint"

**"MOSS" — 3 occurrences (PUBLIC + STALE vs source, double violation):**
- `README.md:229` — Voice screenshot caption: "Sven speaks through the local **MOSS** voice path"
- `README.md:241` — "Speech is rendered locally through the **MOSS** voice path, not a cloud voice provider"
- `README.md:271` — FAQ Q5: "then speaks through the local **MOSS** voice path"
- NOTE `[MOVED SINCE MAPS]`: MOSS is NUKED in source — `src/vibemix/agent/local_tts.py` is DELETED, `config_store.py:65 DEFAULT_TTS_ENGINE="chatterbox"`, `_SUPPORTED_TTS_ENGINES = frozenset({"chatterbox"})`. The README MOSS claims are now both a policy violation AND a factual lie. De-slop rewrite must say "on-device voice", not just swap MOSS→Chatterbox.

**`api.altidus.world` — 3 occurrences (PUBLIC, leaks internal infra):**
- `README.md:39`, `README.md:241`, `README.md:259` — all expose the raw proxy host. Replace with "Bravoh's hosted service". (Out of ING12 marketing scope but noted: `SECURITY.md:58/75` and `PRIVACY.md:25` also carry it; SECURITY/PRIVACY are public-linked from the README footer/FAQ, so they leak too — see §2.)

**`bravoh.com` — 1 occurrence (PUBLIC, wrong domain):**
- `README.md:63` — "Please email **security@bravoh.com**". Domain is `bravoh.ai`. (Also in `SECURITY.md` ×4 — §2.)

**`ozzaii` — 1 occurrence (PUBLIC, wrong org slug):**
- `README.md:330` — "[GitHub Release notes](https://github.com/**ozzaii**/vibemix/releases)". Every OTHER repo URL in the README already correctly uses `bravoh-ai/vibemix` (lines 42-54 badges, 94 install, 210 issue template) — this is a single leftover. Org is `Bravoh-ai/vibemix` (main was pushed there 2026-06-04).

---

### 2. Partner-copy violations — README-linked PUBLIC docs (file:line)

These are linked directly from the README (footer / FAQ / Install), so a stranger reaches them — they are public-facing for ING12 purposes.

**`SECURITY.md` (linked README:63/315):**
- `:4` `:9` `:34` `:42` — `security@bravoh.com` ×4 (wrong domain → `bravoh.ai`)
- `:58` `:75` — `api.altidus.world/vibemix/latest.json` (updater endpoint host leak) — borderline: this is a security-disclosure egress table; the host is arguably load-bearing technical detail, but per policy it should read "Bravoh's hosted updater service". Owner-call.
- `:76` — already correct: `github.com/bravoh-ai/vibemix`.

**`PRIVACY.md` (linked README:109):**
- `:25` — "(`api.altidus.world`), which forwards them to Google's **Gemini** model" (host + model leak on the privacy page a privacy-conscious DJ WILL read).

**`docs/code-signing-policy.md` (linked README:107):**
- `:26` — "**Repository:** https://github.com/**ozzaii**/vibemix" (wrong org slug)
- `:44` — "Kaan Özkan (`github.com/**ozzaii**`)" (wrong org slug)

**`docs/launch/github-meta.md` (the canonical GitHub-side metadata, consumed by `sync_github_meta.sh`):**
- `:Real apply step 5` — "Cross-check at <https://github.com/**bravoh**/vibemix>" (should be `bravoh-ai`)
- "Repository transfer to `**bravoh**/vibemix` org" heading (should be `bravoh-ai`)
- The Description block + Homepage URL are CLEAN (no model names; uses `bravoh.ai`). Good.

**Launch `.md` docs (`docs/launch/*.md`) — CLEAN.** Grep across `partner-brief.md`, `partner-brief-meturavers.md`, `partner-capabilities.md`, `partner-capabilities-short.md`, `nda-meturavers.md`, `github-meta.md` returns ZERO `Gemini|MOSS|api.altidus.world|bravoh.com|ozzaii` (except the github-meta `bravoh/vibemix` org-slug noted above). The partner-facing prose already honors the policy.

**Dev/contributor docs — IN POLICY, do NOT touch (CLAUDE.md allows model names internally):**
- `docs/byo-key.md` — titled "Bring Your Own Gemini API Key", names Gemini ~15× + `api.altidus.world` ×3. This is the BYO-key engineer recipe (`direct` mode); naming the provider is correct and necessary. LEAVE.
- `docs/audio-routing.md:126/151` — "Viber/Gemini" in a recipe; dev doc. LEAVE.
- `docs/windows-setup.md:37` (`github.com/ozzaii` clone URL) + `:58` (names Chatterbox/Gemini in a dev voice note). The `ozzaii` clone URL IS a slug bug worth fixing even in a dev doc, but it is not README-marketing. Flag, low priority.

---

### 3. Dev feature-matrix slop leak (the internal dump)

The README "Current shipped surface" table (`README.md:128-171`, between the `<!-- AUTO-GEN: feature-matrix START/END -->` markers) is a raw internal engineering log on the public landing page. Specific leaks:

- **Phase numbers** — `README.md:132-169` every row is "| 102 |", "| 103 |", … "| 58 |" (Phase IDs 51-104). A user does not care that "Skill-Tree Engine" was "Phase 102".
- **Commit SHAs** — `README.md:139` (Phase 95): "commits `c740fd90 → 617b663b → d8f0f5f7 → 2a8e9bd9 → fd6e6981`". Five raw SHAs on the marketing surface.
- **Internal REQ-IDs / plan counts** — pervasive: "TEST-01..04", "DEV-01..05", "OSS-01..05", "RENDER-01..03, 05, 06, 07", "190/3 in tests/learn/", "(5/5 plans)".
- **"Kaan ear-passes daily"** — `README.md:69`: "rekordbox + DDJ-FLX4 is what **Kaan ear-passes daily**" — names the founder + an internal QA ritual in the public app-support copy.
- **"KAAN-ACTION" / "ear-pass"** — `README.md:11, 30, 86, 134, 135, 142, 148, 157, 198, 279, 295` — internal action-tracker tokens. Most are in HTML comments (11/30/86/198 — invisible to a reader but still committed slop); the load-bearing public ones are `:134/:142/:148` (visible feature-matrix cells naming KAAN-ACTION), `:135` ("Kaan ear-pass available the moment this lands"), `:69` (Kaan ear-passes daily), `:279` ("a Kaan ear-pass on a live DJ session"), `:295` (FAQ Q11 "Kaan + Francesco use daily").
- **Phase-process language in FAQ** — `README.md:279` FAQ Q7: "**Phase 16's** hallucination verification gate … **Phase 17**, ≥4.0 average". Internal phase IDs in a user FAQ.

**Constraint that makes this NOT a free edit:** the table body is AUTO-GENERATED by `scripts/launch/sync_feature_matrix.py` from `.planning/ROADMAP.md` (regex `^- \[x\] (?:\*\*)?Phase\s+(\d+):`). The Phase numbers + SHAs + REQ-IDs live in ROADMAP.md and are spliced verbatim into the README between the AUTO-GEN markers. You CANNOT hand-edit the cells to remove Phase numbers — the next `--check` run (CI gate `test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync`) re-detects drift and fails. To de-slop the matrix you must either (a) rewrite the ROADMAP source lines the syncer reads (so the generated cells stop carrying SHAs/REQ-IDs), or (b) change `sync_feature_matrix.py` to strip Phase IDs/SHAs at render time AND re-pin the two sync tests, or (c) replace the auto-gen feature-matrix entirely with a hand-written user-facing capability list AND retire the matrix-sync gate. This is a gate-coupled rewrite, not a copy edit — see §5.

---

### 4. Stale / wrong product claims (honesty failures independent of policy)

- **MOSS voice (3×, §1)** — STALE: source is Chatterbox-only `[MOVED SINCE MAPS]`. `config_store.py:65` + `agent/chatterbox_tts.py` present, `agent/local_tts.py` deleted.
- **"djay-Pro-first" — contradicts the Kaan-locked v1 shape.**
  - `README.md:267` FAQ Q4: "djay Pro is Mac/Win only and that's our **primary integration target**".
  - `README.md:295` FAQ Q11: "v1 ships **djay-Pro-first** because that's what Kaan + Francesco use daily … Mixxx OSC + rekordbox parsing are tracked in the v2 inventory."
  - This is WRONG twice: (1) Kaan-locked v1 = macOS Apple-Silicon (arm64) ONLY, with rekordbox + DDJ-FLX4 as the daily-verified path (README:69 itself says rekordbox is what's ear-passed daily — internally inconsistent with Q11's "djay-Pro-first"). (2) The screen-watch is in fact hardcoded djay-only on macOS (`_screen_macos.py` per SHIP-MAP §runtime-io W15), so "app-agnostic by design" (README:69/84) overclaims vision while Q11 underclaims rekordbox. The honest copy: app-agnostic audio+MIDI grounding; macOS-arm64 v1; rekordbox/DDJ-FLX4 the daily-verified target; screen-watch coverage expands per app.
- **Windows framing — "targets v0.1.0 stable".** `README.md:39, 84, 95, 103-104, 255, 275` all say "Windows … targets v0.1.0 stable" / "v0.1.0 stable swaps the placeholder". Per the Kaan-locked ship shape, Windows is v1.1 fast-follow (mlx-audio is Apple-only; Intel Macs are voiceless too), explicitly OFF the v1 critical path. "v0.1.0 stable" conflates the macOS GA tag with a Windows promise. The honest framing: v1 = macOS Apple-Silicon; Windows is a v1.1 milestone after macOS ships. ⚠ This also collides with the GA-TAG LANDMINE: `release.yml` + `companion-sign.yml` fire the full signed matrix (incl Windows + SignPath) on a `v*` tag — copy that promises "Windows with v0.1.0 stable" pressures a premature `v0.1.0` push.
- **Voice screenshot (`README.md:229`)** — caption + the asset `docs/assets/screenshots/voice-picker.png` describe a "local co-host voice setup" / MOSS path; a Chatterbox-only product has no voice-picker (single locked voice), so the screenshot itself may be stale. Asset re-shoot is a Kaan-action; flagged.
- **"~785 MB CLAP model" (README:39/241/259/271)** — factual, library-side, NOT a policy violation (no model NAME, just a size). Keep; verify the number still matches `library/model_assets.py` at ship.

`[MOVED SINCE MAPS — voice reachability]`: the SHIP-MAP-MASTER "#1 blocker = mlx_audio not a pyproject extra" is now STALE. `pyproject.toml:162/167` carries `mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'` in TWO extras, and the moss→chatterbox gate-swap has LANDED (`scripts/dist/pretag_check.sh:109/111/113` use `--require-chatterbox-ref --require-chatterbox-source`; `release.yml:355/399/426/541` likewise; ZERO `require-moss-source` remain repo-wide). So the README is now even FURTHER behind source on voice — fixing the MOSS copy is purely a doc lag now, the engineering moved.

---

### 5. The 4 CI gates — preservation contract (what a de-slop rewrite MUST keep vs may intentionally break)

All 4 gates VERIFIED GREEN at HEAD `d7d5337a` (ran each): `check_readme_hero_hash.py` exit 0 (PLACEHOLDER sentinel), `sync_feature_matrix.py --check` "in sync", `check_readme_grids_a11y.py` "PASS", `pytest tests/repo/test_readme_shape.py tests/repo/test_readme_feature_matrix_sync.py` 53 passed.

#### Gate A — `tests/repo/test_readme_shape.py` (29 parametrized assertions)
**MUST PRESERVE (verbatim substrings the gate greps):**
- The 5 required asset refs: `docs/assets/hero.png`, `docs/assets/demo-poster.png`, `docs/assets/architecture.svg`, `docs/assets/controllers/`, `docs/assets/screenshots/` (`:31-44`).
- All 10 controller profile IDs verbatim, e.g. `pioneer_ddj_flx4` … `hercules_inpulse_500` (`:60-71`) — they live in the anti-drift HTML comment at `README.md:200-203`; do NOT delete that comment block.
- All 12 FAQ question substrings (`:79-92`) — and **`"Why Gemini"` is one of them (`:84`).** ⚠ **GATE-BREAK HAZARD:** de-slopping FAQ Q5's heading to remove "Gemini" (e.g. "Why this AI model and not GPT/Claude?") BREAKS `test_readme_has_faq_question` on `"Why Gemini"`. To remove the word "Gemini" from the FAQ you MUST re-pin `:84` to the new heading substring. Same coupling for any FAQ heading rename.
- `bravoh.ai/vibemix?utm_source=github` present AND `https://altidus.world/vibemix` ABSENT (`:100-102`). The footer link de-slop is already policy-compliant; keep it.
- Install section: `## Install` + `vibemix.dmg` + `v0.1.0 stable` (`:105-112`). ⚠ **GATE-COUPLING:** the gate hard-asserts the literal `v0.1.0 stable` exists. If you de-slop the Windows framing to drop "v0.1.0 stable" you BREAK `test_readme_has_install_section` — re-pin `:112` (e.g. to "v1.1" or remove the assertion). This gate ENFORCES the stale Windows framing; rewriting honestly requires re-pinning the test.
- Feature-matrix cell words: `Beginner`, `Intermediate`, `Pro`, `Hype-man`, `Coach` (`:115-117`) — keep the skill×mode grid.
- License: `LICENSE` + `Apache 2.0` (`:155-157`). Badges: ≥5 `shields.io` (`:160-162`).
- **Anti-slop blocklist (`:122-139`)** — README must NOT contain: `absolutely amazing`, `as an AI`, `leverage`, `delve into`, `incredibly powerful`, `groundbreaking`, `revolutionary`, `let's dive in`, `the room is electric`. A de-slop rewrite naturally stays clear of these; do not introduce any.
**MAY INTENTIONALLY BREAK (re-pin):** `"Why Gemini"` → new FAQ heading; `v0.1.0 stable` → honest Windows framing. Both are 1-line test edits.

#### Gate B — `tests/repo/test_readme_feature_matrix_sync.py` + `sync_feature_matrix.py --check` (the matrix-sync gate)
**MUST PRESERVE:**
- Both AUTO-GEN markers verbatim: `<!-- AUTO-GEN: feature-matrix START` and `<!-- AUTO-GEN: feature-matrix END -->` (`:31-38`).
- The README block between the markers must byte-match `sync_feature_matrix.py` output (`:41-53`) — i.e. it stays auto-generated from ROADMAP.md.
- Every ROADMAP `- [x] Phase NN:` with NN≥27 must appear as `| NN |` in the block (`:56-82`); phases <27 must NOT appear (`:85-95`).
- Bravoh footer with `utm_source=github` + `utm_campaign=vibemix_launch`, AFTER the matrix block (`:98-121`).
- **`test_video_tag_present_in_hero_block` (`:124-135`) — requires `<video` AND `docs/assets/demo.mp4` inside the hero block (`<!-- vibemix:hero-start … --> … <!-- vibemix:hero-end -->`).** ⚠ **LOAD-BEARING SUBTLETY (verified):** the README hero block has NO real `<video>` element — it is an `<img>` placeholder (`README.md:19-21`). This gate passes ONLY because the substrings `<video` and `docs/assets/demo.mp4` appear INSIDE the HTML comment at `README.md:11-15` ("The `<video>` tag below points at it", "lands at `docs/assets/demo.mp4`"). A de-slop rewrite that trims that hero comment (it reads as internal Phase-process prose: "Phase 35 ASSETS-07 + Phase 39 SHIP-02 + Phase 70 GH-01 …") will DELETE the only `<video` substring and BREAK this gate. **Preserve the `<video` + `docs/assets/demo.mp4` tokens** (keep a minimal comment, or add a real `<video>` tag) when cleaning the hero block.
**MAY / MUST INTENTIONALLY BREAK to de-slop the matrix (§3):** the Phase-numbered table is auto-gen from ROADMAP, so de-slopping the SHAs/REQ-IDs/Phase-IDs requires EITHER rewriting ROADMAP source lines OR modifying `sync_feature_matrix.py`'s render to strip them AND re-pinning `test_feature_matrix_includes_all_completed_phases` (it asserts `| NN |` per completed phase — strip Phase IDs and it fails) OR replacing the auto-gen matrix with a hand-written capability list and RETIRING this gate. This is the single biggest gate-coupled decision in the README de-slop; owner-call. Recommended minimal honest path: keep the auto-gen block (don't fight the gate) but move it BELOW the fold / into a `docs/CHANGELOG`-style "Engineering log" and present a hand-written user-facing capability section above — but note even that needs the markers + the per-phase assertions to still resolve, so the cleanest is rewriting the ROADMAP descriptions to drop SHAs/REQ-IDs (keeps Phase IDs, which the gate requires anyway). Phase IDs themselves CANNOT be removed without retiring the gate.

#### Gate C — `scripts/launch/check_readme_grids_a11y.py`
**MUST PRESERVE:**
- An H2 heading containing `works alongside` (DJ-software grid) and one containing `supported controllers` (case-insensitive) (`:56-57`).
- DJ-software grid = EXACTLY 6 `<img>` cells, each with a non-empty `alt=` (`:68`, `:198-218`); controllers grid = EXACTLY 10 `<img>` cells, each with non-empty `alt=` (`:69`).
- Grid balance: 6 divisible by 2 or 3; 10 divisible by 2 or 5 (`:76-77`).
- Alt-text must contain NONE of the slop blocklist (`:86-103`): `leverage, synergize, revolutionize, game-changer, next-generation, cutting-edge, seamless, robust, powerful, intuitive, delightful experience, AI-powered, harness the power, unlock, transformative, paradigm`. Current alts are clean; keep them clean on rewrite.
**INTENTIONALLY BREAKS:** nothing in a partner-copy de-slop touches this gate — the grids carry no model names. If a rewrite changes a heading you must keep the `works alongside` / `supported controllers` fragments (or update `:56-57`). Editing alt-text is fine as long as it stays non-empty + slop-free.

#### Gate D — `scripts/check_readme_hero_hash.py`
**MUST PRESERVE:**
- The hero start comment `<!-- vibemix:hero-start sha256=… path=… -->` MUST exist (`:73-80` — absence is a loud FAIL).
- `sha256=PLACEHOLDER` (the sentinel) keeps it green while no real `docs/assets/demo.mp4` exists (`:90-94`; verified — `demo.mp4` does NOT exist on disk). Keep `sha256=PLACEHOLDER path=docs/assets/demo.mp4` until the real demo cut lands.
**INTENTIONALLY BREAKS:** if a de-slop rewrite strips the hero comment entirely (to remove the Phase-process prose), this gate FAILS ("README has no hero-start block"). You can shrink the comment's prose but must keep the `<!-- vibemix:hero-start sha256=PLACEHOLDER path=docs/assets/demo.mp4 -->` line. This gate and Gate B's video test BOTH depend on the hero comment surviving — coordinate them.

---

### 6. Precise fix-list (ordered, with gate impact)

Copy-edits (no gate break) unless flagged ⚠.

**README.md — partner-copy:**
1. `:39` — drop "Gemini" + `api.altidus.world`: "Live co-host calls go to **Bravoh's hosted service** — analyzed in flight, never stored." (no gate)
2. `:61` — "live audio is streamed to **Bravoh's hosted service** for analysis" (no gate)
3. `:63` — `security@bravoh.com` → `security@bravoh.ai` (no gate)
4. `:229` — caption: drop MOSS → "Sven speaks through the **on-device voice**" (asset may also be stale, §4)
5. `:241` — drop Gemini + host + MOSS: "streams audio + screen frames + MIDI events through **Bravoh's hosted service** for grounded reaction planning; nothing is stored. Speech is rendered **on-device**, not a cloud voice provider."
6. `:259` (FAQ Q2) — "streamed to **Bravoh's hosted service** … No raw audio is stored on Bravoh's servers."
7. `:269` (FAQ Q5 heading) — rewrite to drop "Gemini" ⚠ **re-pin Gate A `:84`** (`"Why Gemini"` → new substring).
8. `:271` (FAQ Q5 body) — drop Gemini + MOSS: "Sven uses **Bravoh's hosted AI model** for grounded live reaction planning, then speaks **on-device**."
9. `:283` (FAQ Q8) — "The **AI model** is the provider's. … point it at your **own provider key**." (drop both Gemini)
10. `:287` (FAQ Q9) — "point vibemix at your **own provider endpoint**" (drop Gemini)
11. `:330` — `github.com/ozzaii/vibemix` → `github.com/bravoh-ai/vibemix` (no gate)

**README.md — stale claims:**
12. `:267` (FAQ Q4) + `:295` (FAQ Q11) — replace "djay-Pro-first / primary integration target" with the honest macOS-arm64-v1 + rekordbox/DDJ-FLX4-daily-verified framing; align with `:69`. ⚠ Q11 heading "What about Mixxx? Rekordbox?" is gate-pinned (`"What about Mixxx"` Gate A `:90`) — keep that substring in the heading.
13. Windows framing `:39, 84, 95, 103-104, 255, 275` — reframe to "Windows = v1.1 fast-follow" instead of "v0.1.0 stable". ⚠ **re-pin Gate A `:112`** (asserts literal `v0.1.0 stable`).
14. `:279` (FAQ Q7) — drop internal "Phase 16 / Phase 17" IDs; describe the hallucination-grounding gate in user terms. Keep "Can it hallucinate?" heading (Gate A `:87` pins `"Can it hallucinate?"`... actually it pins the substring — verify; the gate list is the 12 FAQ strings).

**README.md — dev-matrix slop (§3, gate-coupled):**
15. `:69` — remove "Kaan ear-passes daily" → "the daily-verified target". (no gate)
16. `:134/:142/:148` visible KAAN-ACTION cells + `:135` "Kaan ear-pass" + `:139` 5 SHAs + `:140/:149` "Gemini wiring"/"Gemini as Secondary Ear" — these are INSIDE the AUTO-GEN block; ⚠ **CANNOT be hand-edited** (Gate B re-syncs from ROADMAP). De-slop requires rewriting `.planning/ROADMAP.md` source lines OR the syncer render OR retiring the matrix gate (§5 Gate B). Owner-decision.
17. HTML-comment KAAN-ACTION/Phase prose `:10-18, 24-31, 86, 198` — invisible to readers but committed slop; trim BUT preserve the load-bearing tokens: `<video`, `docs/assets/demo.mp4`, `vibemix:hero-start sha256=PLACEHOLDER` (Gates B+D), the 10 controller profile IDs at `:200-203` (Gate A).

**Linked public docs:**
18. `SECURITY.md:4/9/34/42` — `security@bravoh.com` → `security@bravoh.ai` (×4). `:58/75` — `api.altidus.world` updater host → "Bravoh's hosted updater" (owner-call; egress table may want the host).
19. `PRIVACY.md:25` — drop "Gemini" + `api.altidus.world`: "(**Bravoh's hosted service**), which forwards them to an **AI model** for analysis".
20. `docs/code-signing-policy.md:26/44` — `github.com/ozzaii` → `github.com/bravoh-ai` (×2).
21. `docs/launch/github-meta.md` — "Real apply step 5" + transfer heading: `bravoh/vibemix` → `bravoh-ai/vibemix` (×2).

**Lower priority (dev docs, allowed to name models but slug is wrong):**
22. `docs/windows-setup.md:37` — clone URL `github.com/ozzaii/vibemix` → `bravoh-ai`. (Gemini mention at `:58` is dev-allowed, leave.)

**Do NOT touch (in policy):** `docs/byo-key.md` (BYO engineer recipe, Gemini-by-design); `docs/audio-routing.md` (dev recipe); `docs/launch/*.md` partner prose (already clean).

---

### 7. Open owner-decisions this ingest surfaces

- **D-DOC1 — feature-matrix slop:** retire the auto-gen matrix gate and hand-write a user capability list, OR rewrite ROADMAP.md descriptions to drop SHAs/REQ-IDs (keeps Phase IDs the gate requires)? The Phase IDs CANNOT leave the README while `test_readme_feature_matrix_sync.py` lives. (§5 Gate B)
- **D-DOC2 — SECURITY/PRIVACY updater-host leak:** `api.altidus.world/vibemix/latest.json` in the egress table — replace with prose or keep the host as load-bearing security disclosure?
- **D-DOC3 — Voice screenshot re-shoot:** `docs/assets/screenshots/voice-picker.png` likely shows a stale MOSS/voice-picker UI a Chatterbox-only build no longer has. Kaan-action asset cut.
- **D-DOC4 — FAQ Q5/Install gate re-pins:** the two test re-pins (`"Why Gemini"`, `v0.1.0 stable`) are the only test edits required for the partner-copy + Windows-framing rewrite. Confirm they ship in the same commit as the README rewrite (else CI RED). Per CLAUDE.md "Do NOT edit product behavior to satisfy a test — fix the test policy": these ARE policy re-pins (the gate was pinning stale copy), legitimate.

---

### 8. Summary table (status per surface)

| Surface | Violation kind | Count | CI-gate state | Flag |
|---|---|---|---|---|
| README Gemini leaks | model name | 9 | GREEN (gates don't enforce) | LANDED-but-DISHONEST |
| README MOSS leaks | model name + STALE vs source | 3 | GREEN | LANDED-but-DISHONEST |
| README api.altidus.world | infra leak | 3 | GREEN | LANDED-but-DISHONEST |
| README bravoh.com | wrong domain | 1 (`:63`) | GREEN | LANDED-but-DISHONEST |
| README ozzaii | wrong slug | 1 (`:330`) | GREEN | LANDED-but-DISHONEST |
| README dev-matrix dump | internal slop (Phase/SHA/KAAN) | matrix block + ~8 prose | GREEN, gate-coupled | LANDED-but-DISHONEST |
| README djay-Pro-first | stale vs macOS-arm64 v1 | 2 (Q4/Q11) | GREEN, Q11 heading gate-pinned | LANDED-but-DISHONEST |
| README Windows framing | stale vs v1.1-fast-follow | ~6 | GREEN, `v0.1.0 stable` gate-pinned | LANDED-but-DISHONEST |
| SECURITY.md | bravoh.com ×4 + host ×2 | 6 | not README-gated | LANDED-but-DISHONEST |
| PRIVACY.md | Gemini + host | 1 (`:25`) | not README-gated | LANDED-but-DISHONEST |
| code-signing-policy.md | ozzaii slug | 2 | not README-gated | LANDED-but-DISHONEST |
| github-meta.md | bravoh/ org slug | 2 | greps own values | LANDED-but-DISHONEST |
| launch/*.md partner prose | none | 0 | clean | CLEAN |
| byo-key / audio-routing (dev) | model names (allowed) | many | n/a | IN-POLICY, leave |
| 4 README CI gates | all pass | — | GREEN at `d7d5337a` | gates DO NOT enforce partner-copy |

**The one-line thesis for the organizer:** the README is green and shippable to CI but lies to the user — the 4 gates pin shape/assets/sync, not honesty, so every model name, the proxy host, the wrong domain/slug, the stale MOSS+djay+Windows claims, and the dev feature-matrix dump all ride green. The de-slop rewrite is mostly free copy edits; the ONLY gate breaks are 2 re-pins (`"Why Gemini"` FAQ heading + `v0.1.0 stable` Install string) plus the matrix-slop decision, which is gate-coupled to the ROADMAP-driven auto-gen syncer and is the single owner-call (D-DOC1). Preserve the hero-comment `<video`/`demo.mp4`/`PLACEHOLDER` tokens and the 10 controller profile IDs through any comment trimming.
