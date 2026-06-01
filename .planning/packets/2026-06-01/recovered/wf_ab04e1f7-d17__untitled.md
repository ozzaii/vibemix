I have completed the read-only scout of the public-claims-vs-monetized-posture dimension. Here is my summary.

## Core finding

The accepted CODEX ground says vibemix is **now a monetized product** (Free + paid Pro/Studio per the final-acceptance-contract), but **every public-facing surface in the repo still says the product is "free."** There is **no Free/Pro/Studio tier copy anywhere** — the only "Pro"/"Studio" strings in the repo are the Beginner/Intermediate/Pro skill-level labels. So the narrow-to-Free+Pro/Studio edits are net-new reconciliations the public copy still needs, not tweaks to already-monetized text.

A second surprise: `docs/pricing/live-stack-economics.en.md` is **not** a pricing/business-model doc — it is an internal cost model that explicitly states (line 8-9) "This document measures cost. It does not choose the business model." It defines no tiers.

## SUPERSEDED — narrow (keep Apache-2.0, narrow the "free" marketing)

- **README.md:260-262** FAQ #3 "Is this free? Yes for v1… absorbed by Bravoh" — the highest-priority fix. (Also conflicts numerically: "~50 €/month" vs the cost model's €9.74/DJ.)
- **README.md:59, 304** + **PRODUCT.md:15, 17** — "free, open-source warm-up / waitlist funnel" framing.
- **docs/landing/index.html** — unqualified "free" in 5 places (lines 7, 13, 622, 629, 666) + "open-source warm-up" footer (690).
- **docs/launch/.vibemix-pitch-en.html:217** "Free. Open source." CTA and **.vibemix-pitch-tr.html:217** "Ücretsiz. Açık kaynak." CTA.
- **All partner decks** (partner-capabilities.md/-short.md, partner-brief.md/-meturavers.md and their .html/TR twins) — "open-source warm-up → Bravoh waitlist," no pricing.

## LIVE / OK — keep (legit license statements, not marketing overclaims)

- **README.md:39, 282, 325** + **LICENSE:190** Apache-2.0 statements (client open, proxy + main product closed) — accurate, keep.
- **docs/launch/github-meta.md:11, 29** "open-source" repo description/topics — true of the client, no "free product" implication.
- **docs/launch/nda-meturavers.md:15, 49** open-source carve-out — legal/license description.

## OVERCLAIM probes — all OK (no overclaim found on read surfaces)

- **Live drop speech** — every surface disclaims it (README:35, 123; pitch:139).
- **Deck/track identity from audio** — identity comes from screen capture (README:240); audio-naming is treated as a hallucination risk to suppress.
- **Mastered beatmatch** — "Mastered" is only a Learn skill-tree stage label (README:132-133), not an audio capability.
- **Signed == latest** — signing is hedged everywhere (README:95, 102; landing:676; decks "Windows in flight").

## Verification gaps to re-scan

- `vibemix-capabilities.pdf` + `vibemix-yetenekler-tr.pdf` (partner PDFs, likely mirror the stale "free warm-up" framing) and `live-stack-economics.it.md`.
- For the "signed==latest" overclaim specifically: `codesign0/1/2` (repo root), `docs/signing-macos.md` (modified per git status), `docs/release-process.md` — out of this dimension's scope but where such a claim would live.

Note: an intermittent tool-transport flakiness produced empty returns on several calls early and mid-session (trivial `printf` probes also returned empty during those windows), which is why some files were re-read multiple times; all classified files above were successfully read.
