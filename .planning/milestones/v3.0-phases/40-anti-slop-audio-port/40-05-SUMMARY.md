---
phase: 40-anti-slop-audio-port
plan: 05
subsystem: security
tags: [security, pgp, tauri-updater, kaan-action, pre-stage, gate-tests, audio-05, audio-06]
requirements: [AUDIO-05, AUDIO-06]
type: execute
wave: 1
dependency_graph:
  requires: []
  provides:
    - "AUDIO-05 engineering pre-stage (slot file + SECURITY.md retarget + runbook)"
    - "AUDIO-06 engineering pre-stage (rotation comment + runbook)"
  affects:
    - "tests/security/test_pgp_published.py — new dual-mode gate"
    - "tests/tauri/test_updater_key_rotated.py — new dual-mode gate"
    - "KAAN-ACTION-LEGAL.md — §AUDIO-05 + §AUDIO-06 runbooks"
    - "SECURITY.md — PGP link retargeted to docs/security/pgp-public-key.txt"
tech_stack:
  added: []
  patterns:
    - "Dual-mode gate test (sentinel flips pre-discharge → post-discharge automatically)"
    - "Slot file with PGP armor envelope + placeholder sentinel"
    - "Runbook in KAAN-ACTION-LEGAL.md mirrors gate-test invariants 1:1"
key_files:
  created:
    - "docs/security/pgp-public-key.txt"
    - "tests/security/test_pgp_published.py"
    - "tests/tauri/__init__.py"
    - "tests/tauri/test_updater_key_rotated.py"
  modified:
    - "SECURITY.md"
    - "tauri/src-tauri/tauri.conf.json5"
    - "KAAN-ACTION-LEGAL.md"
decisions:
  - "Slot file uses PGP armor envelope around the placeholder body — keeps the structure stable so consumers know where to look pre-discharge."
  - "AUDIO-05 + AUDIO-06 runbooks landed in a single KAAN-ACTION-LEGAL.md edit during Task 1 rather than splitting across the two task commits. Functionally identical; sequencing deviation documented below."
  - "tauri.conf.json5 pubkey value is UNCHANGED (the 2026-05-13 dev key stays). The Plan 40-05 comment block is the only addition — value rotation is Kaan's discharge step per autonomous-mode policy."
  - "Sentinel choice for AUDIO-06 pre-discharge detection: the dev-key fingerprint 94A8F6CE42E6487D (embedded in the base64-encoded minisign comment). Robust to non-meaningful whitespace edits in the comment block."
metrics:
  duration_seconds: 1320
  completed_date: "2026-05-16"
  tasks_completed: 2
  files_changed: 7
  tests_added: 13
  commits: 4
---

# Phase 40 Plan 05: PGP Slot File + Tauri Updater Key Pre-stage Scaffolding

**One-liner:** Pre-stage scaffolding for the two AUDIO-05 (PGP) + AUDIO-06 (Tauri updater key) KAAN-ACTION items — slot file, SECURITY.md retarget, two dual-mode gate tests, and copy-pasteable discharge runbooks in KAAN-ACTION-LEGAL.md.

## What shipped

### AUDIO-05 — PGP key slot

- **`docs/security/pgp-public-key.txt`** (new) — placeholder body inside a valid `-----BEGIN/END PGP PUBLIC KEY BLOCK-----` envelope. Carries the `PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED` sentinel that the gate test reads to decide pre- vs post-discharge mode.
- **`SECURITY.md`** — PGP section retargeted from `KAAN-PGP-PLACEHOLDER.asc` to `docs/security/pgp-public-key.txt`. Placeholder fingerprint `PLACEHOLDER-FINGERPRINT-NOT-REAL` preserved verbatim (Kaan replaces it atomically with the real fingerprint during discharge). `hkps://keys.openpgp.org` lookup hint added below the table.
- **`KAAN-ACTION-LEGAL.md §AUDIO-05`** — new section with the 5-step runbook (`gpg --quick-gen-key ed25519` → fingerprint → `gpg --armor --export` → `gpg --send-keys --keyserver hkps://keys.openpgp.org` → SECURITY.md fingerprint update + `git rm KAAN-PGP-PLACEHOLDER.asc`) and a discharge checklist that mirrors the gate-test invariants 1:1.

### AUDIO-06 — Tauri updater key rotation

- **`tauri/src-tauri/tauri.conf.json5`** — new `// Plan 40-05 — production key rotation` comment block immediately above the existing pubkey line at 153. Pubkey VALUE unchanged (the 2026-05-13 dev key stays until Kaan rotates). Comment documents: runbook location, `gh secret set TAURI_UPDATER_PRIVATE_KEY` step, `placeholder-pubkey-gate` semantics (tagged pushes only), and the dual-mode gate test cross-reference.
- **`KAAN-ACTION-LEGAL.md §AUDIO-06`** — new section with the 4-step runbook (`npx @tauri-apps/cli signer generate --no-password` → paste pubkey into `tauri.conf.json5` → `base64 -i …key | gh secret set TAURI_UPDATER_PRIVATE_KEY` → `gh workflow run release.yml` rehearsal) and a discharge checklist.

### Gate tests

- **`tests/security/test_pgp_published.py`** — 7 assertions, dual-mode. Pre-discharge today: 4 passed, 1 skipped (post-discharge mode is a single `pytest.skip()` until Kaan replaces the placeholder sentinel).
- **`tests/tauri/test_updater_key_rotated.py`** — 8 assertions, dual-mode. Pre-discharge today: 7 passed, 1 skipped (post-discharge mode skipped until Kaan rotates the keypair).
- Both tests use a sentinel check on the slot file content as their mode discriminator — they flip from pre-discharge to post-discharge automatically when Kaan completes the runbook. **No code change needed.**

## The pre-/post-discharge invariants encoded in each gate test

### `tests/security/test_pgp_published.py`

| Invariant | Pre-discharge | Post-discharge |
|-----------|---------------|----------------|
| Slot file exists | ✓ | ✓ |
| Slot file has PGP armor envelope | ✓ | ✓ |
| SECURITY.md references `docs/security/pgp-public-key.txt` | ✓ | ✓ |
| KAAN-ACTION-LEGAL.md has AUDIO-05 runbook | ✓ | ✓ |
| Slot file has `PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED` | ✓ | ✗ (sentinel gone) |
| SECURITY.md has `PLACEHOLDER-FINGERPRINT-NOT-REAL` | ✓ | ✗ (real fingerprint) |
| Slot file body ≥200 chars + valid base64 armor | n/a | ✓ |
| Slot file has NO `BEGIN PGP PRIVATE KEY BLOCK` | n/a | ✓ (defense-in-depth) |
| SECURITY.md no longer references `KAAN-PGP-PLACEHOLDER.asc` | n/a | ✓ |
| `KAAN-PGP-PLACEHOLDER.asc` file no longer exists at repo root | n/a | ✓ |

**Partial-discharge failure mode:** if SECURITY.md fingerprint is updated but the slot file still has the placeholder sentinel (or vice versa), the test fails with a clear message pointing at the runbook.

### `tests/tauri/test_updater_key_rotated.py`

| Invariant | Pre-discharge | Post-discharge |
|-----------|---------------|----------------|
| `tauri.conf.json5` exists | ✓ | ✓ |
| `plugins.updater.pubkey` field non-empty | ✓ | ✓ |
| Pubkey is not the Phase 18 `TAURI_UPDATER_PLACEHOLDER` sentinel | ✓ | ✓ |
| `Plan 40-05` comment block present in `tauri.conf.json5` | ✓ | ✓ (audit trail) |
| `release.yml::placeholder-pubkey-gate` job preserved | ✓ | ✓ (Pitfall 6) |
| KAAN-ACTION-LEGAL.md has AUDIO-06 runbook | ✓ | ✓ |
| Decoded pubkey contains `94A8F6CE42E6487D` (dev-key fingerprint) | ✓ | ✗ (rotated) |
| Decoded pubkey starts with `untrusted comment: minisign public key:` | ✓ | ✓ |

**Partial-discharge failure mode:** if the pubkey is rotated but the `Plan 40-05` comment block disappears, or `release.yml::placeholder-pubkey-gate` was accidentally removed during rotation (Pitfall 6 regression), the test fails with a clear message.

## Kaan-action: how to discharge

**Run the runbooks in `KAAN-ACTION-LEGAL.md §AUDIO-05` + `§AUDIO-06` to discharge. The gate tests flip from pre-discharge to post-discharge mode automatically — no code change needed when Kaan completes.**

Quick reference:

```bash
# AUDIO-05 — PGP key
gpg --quick-gen-key 'Bravoh Security <security@bravoh.com>' ed25519 default 0
gpg --list-keys security@bravoh.com   # → copy fingerprint
gpg --armor --export security@bravoh.com > docs/security/pgp-public-key.txt
gpg --send-keys --keyserver hkps://keys.openpgp.org <FINGERPRINT>
# (click email-verify link from keys.openpgp.org)
# Edit SECURITY.md fingerprint cell + status; git rm KAAN-PGP-PLACEHOLDER.asc

# AUDIO-06 — Tauri updater key
npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater_prod.key --no-password
cat ~/.tauri/vibemix_updater_prod.key.pub   # → paste into tauri.conf.json5 plugins.updater.pubkey
base64 -i ~/.tauri/vibemix_updater_prod.key | gh secret set TAURI_UPDATER_PRIVATE_KEY
gh workflow run release.yml --ref main   # rehearsal
```

## Deviations from Plan

### Sequencing

**1. [Rule 1 - Convenience] AUDIO-06 runbook added during Task 1 commit**
- **Found during:** Task 1 GREEN edit of KAAN-ACTION-LEGAL.md
- **Issue:** Plan structure says Task 1 covers AUDIO-05 (PGP) and Task 2 covers AUDIO-06 (Tauri). I added both AUDIO-05 and AUDIO-06 runbook sections in a single KAAN-ACTION-LEGAL.md edit because they sit adjacently in the file and the test for AUDIO-06 expects the runbook to exist.
- **Fix:** None needed — functionally identical to the plan's intent. The Task 2 RED gate test still failed correctly (on the `Plan 40-05` comment block missing from `tauri.conf.json5`), and Task 2 GREEN added that block as planned.
- **Impact:** Task 2 RED only ran with 1 failing assertion (the comment block check) instead of 2 (would have also been the AUDIO-06 runbook check), but the GREEN gate covers both correctly.

### Worktree state

**2. [Rule 3 - Blocker] Stale LFS pointer state in worktree**
- **Found during:** pre-commit `git status`
- **Issue:** The worktree was spawned from commit `d7accba` (older than the Phase 40 plan commit `5cdba68`). Plan 40-05 files lived only on `main`. Multiple LFS-tracked GLB files showed as modified due to a smudge-pointer mismatch (LFS content size 20MB → pointer 133B).
- **Fix:** Stashed LFS-affected GLB modifications (`git stash`), merged `main` into the worktree branch to bring Phase 40 plans + research into scope, then proceeded. The stashed GLB pointer mismatches re-emerged after merge (LFS smudge artifact unrelated to my task) and were left as-is — not part of this plan's surface.
- **Impact:** None — the GLB pointer state is a pre-existing artifact of the worktree spawn and is not committed by this plan. Verification block `git status` filter on POC files only confirms cohost*.py + mascot.html are clean.

## Self-Check

### Files created (4)

```text
docs/security/pgp-public-key.txt         FOUND
tests/security/test_pgp_published.py     FOUND
tests/tauri/__init__.py                  FOUND
tests/tauri/test_updater_key_rotated.py  FOUND
```

### Files modified (3)

```text
SECURITY.md                              MODIFIED — references docs/security/pgp-public-key.txt
tauri/src-tauri/tauri.conf.json5         MODIFIED — Plan 40-05 comment block added; pubkey unchanged
KAAN-ACTION-LEGAL.md                     MODIFIED — §AUDIO-05 + §AUDIO-06 runbook sections added
```

### Commits (4)

```text
8e73bc8 test(40-05): add failing dual-mode gate test for AUDIO-05 PGP slot
b2501ec feat(40-05): scaffold AUDIO-05 PGP slot file + SECURITY.md retarget + runbook
f07dd16 test(40-05): add failing dual-mode gate test for AUDIO-06 Tauri updater key
3574cbb feat(40-05): scaffold AUDIO-06 Tauri updater key rotation comment block
```

### Verification block results

```text
Gate tests:                       11 passed, 2 skipped (post-discharge mode)
SECURITY.md slot ref:             2 mentions (≥1 required) — PASS
AUDIO-05/06 in legal:             15 mentions (≥2 required) — PASS
placeholder-pubkey-gate in CI:    7 mentions (≥2 required) — PASS
POC files clean:                  PASS (cohost*.py, mascot.html unmodified)
No PRIVATE KEY surface:           0 (only pubkey ever lives in repo) — PASS
```

## Self-Check: PASSED
