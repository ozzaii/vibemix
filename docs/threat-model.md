# vibemix Threat Model — STRIDE-lite

**Scope:** vibemix v1 client + the Bravoh proxy boundary it talks to.
**Style:** STRIDE-lite. Four critical surfaces only. Not a full
enterprise-STRIDE matrix; we cover the attacks an OSS reviewer or
threat-modelling skeptic would actually raise. Each surface lists
**asset** + **threat actor** + **mitigation** + **residual risk**.

> Phase 34 / SEC-07. Maintained in lock-step with `SECURITY.md` and
> `src/vibemix/runtime/sec_check.py`. CI test
> `tests/security/test_sec_check.py` verifies the outbound endpoint
> list stays in sync.

---

## Surface 1 — Bravoh proxy rate-limit bypass

**Asset:** The pooled Gemini API quota and per-tenant token bucket on
`api.bravoh.altidus.world`. Cost: ~50 €/month at v1 user volume; an
amplification attack could blow this up by 100× quickly.

**Threat actor:** Adversarial vibemix user (or someone with a clone of the
binary) running a scripted load that pretends to be a live DJ session.

**Attack flow:**

1. Attacker extracts the proxy URL from the binary (trivial — it's not a
   secret).
2. Attacker mints fake "trigger" requests to the proxy at high rate.
3. Bravoh proxy passes traffic to Gemini → real users get rate-limited.

**Mitigations (in order of binding):**

- **M1** — Bravoh proxy issues per-install JWT (ed25519, 24h TTL,
  refreshed by signed install-id). Anonymous calls are rejected with
  `401`. See `KAAN-ACTION-LEGAL.md §5` — this is Bravoh-side work.
- **M2** — Bravoh proxy enforces per-install token bucket: 60 req/min
  default, 600 req/min for opt-in "power user" approvals. Bursts
  capped at 10. Hard ceiling at 1000 req/install/24h.
- **M3** — Anomaly detection on Bravoh side: tag installs that exceed
  3× baseline as suspect; rotate JWT-minting key + force re-auth.
- **M4** — Public-readme rate-limit policy makes the limits visible —
  prospective abusers see the ceiling and don't bother.

**Residual risk:** **MEDIUM.** Per-install JWT can still be extracted
from a single binary and used to amplify within that install's bucket.
Real protection comes from M3 (out-of-band detection) — which is a
Bravoh ops capability, not a client mitigation. Acceptable for v1; we
log every abuse event and have a hard kill-switch.

---

## Surface 2 — Key extraction from distributed binary

**Asset:** The auth token that lets vibemix talk to the Bravoh proxy. If
extracted and shareable, it would let a third party piggyback on our
Gemini quota indefinitely.

**Threat actor:** Anyone with a copy of `vibemix.dmg` / `vibemix.msi` +
`strings` + an hour. Especially: AI-tooling forums where extracted
keys get traded.

**Critical decision:** **There is NO raw `AIza` key in the distributed
binary.** Memory marker `[API key embedded in distributed binary is the
API-key-protection problem of the year]` — we solved this by routing
all Gemini calls through the Bravoh proxy.

**Mitigations:**

- **M1** — No `GEMINI_API_KEY` in the binary. The proxy holds the real
  key; vibemix never sees it. CI gate `scripts/dist/verify_binary.py`
  (Phase 18) scans bundles for AIza-pattern leaks; release blocks on hit.
- **M2** — Proxy auth is a per-install JWT (Surface 1). Even if
  extracted, it's bound to install-id and TTL'd. Revocation rotates
  the minting key.
- **M3** — `.gitleaks.toml` + `.secrets.baseline` (Phase 34 / SEC-01)
  catch any leaked secret in source. Surgical AIza-fixture allowlist
  prevents broad bypass.

**Residual risk:** **LOW.** Extraction of the JWT-minting key would be
catastrophic — that key lives only on Bravoh's KMS, never in the binary.
A JWT itself extracted gives the attacker the same quota as one user
for one day, which the rate-limit absorbs.

---

## Surface 3 — Telemetry exfiltration

**Asset:** Anything sensitive in the user's environment — track titles,
audio, MIDI device names, library contents. None of this should ever
leave the machine without explicit consent.

**Threat actor:** Three sub-cases:

- **3a.** Future vibemix maintainer (Bravoh or a fork) silently adding
  collected fields.
- **3b.** Compromised dep stealing telemetry payload at transit.
- **3c.** Misconfigured logging that incidentally captures sensitive
  context.

**Mitigations:**

- **M1** — Telemetry default-OFF (Phase 34 / SEC-08, Pitfall P67).
  First-run wizard surfaces two equally-prominent radio options;
  default selected is `Don't share`. No skip-equals-off dark pattern.
- **M2** — Field-set disclosure in the consent wizard explicitly
  enumerates every datum collected on opt-in. The wizard renders a
  visible NOT-COLLECTED list (track titles, audio, library, MIDI
  device names, window titles).
- **M3** — Outbound endpoint list in `SECURITY.md` is the *source of
  truth*. The `src/vibemix/runtime/sec_check.py` boot banner mirrors
  it byte-for-byte. CI test
  `tests/security/test_sec_check.py` fails on
  drift. Adding a new endpoint requires updating both files in the
  same PR.
- **M4** — `runtime/sec_check.py` prints the current telemetry
  posture on every launch (`Telemetry: OFF` / `ON`). Users see the
  ground truth, not the marketing copy.

**Residual risk:** **LOW.** Sub-case 3b (compromised dep) is the
hardest to mitigate — pip-audit + osv-scanner severity gate (Phase 34
/ SEC-02) and SBOM publishing (SEC-04) raise the bar but don't
eliminate it.

---

## Surface 4 — Supply-chain compromise

**Asset:** The build pipeline that produces the signed Mac DMG and
Windows MSI. Compromise here = arbitrary code execution on every
user's machine.

**Threat actor:** Compromised dep (typo-squat, malicious update),
compromised GitHub Action, compromised CI runner, compromised
Apple/SignPath chain.

**Mitigations:**

- **M1** — Python deps locked via `uv.lock`. Rust crates locked via
  `Cargo.lock`. Pinning is enforced by `pip-audit --strict` against
  the lockfile.
- **M2** — Severity gate (Pitfall P65) on every CI run. HIGH+ on
  direct deps fails the build; CRITICAL anywhere fails. LOW/MEDIUM
  warn only.
- **M3** — SBOM (`sbom.spdx.json`) attached to every release. Users
  and security researchers can diff the SBOM across versions and
  audit the supply chain themselves.
- **M4** — Tauri capability snapshot lint (Phase 34 / SEC-09). Any
  change to `tauri/src-tauri/capabilities/default.json` requires a
  matching `SNAPSHOT.json` update in the same PR with a
  `SECURITY_CAPABILITY_DELTA:` block in the PR description.
- **M5** — GitHub Actions are pinned to versioned tags (`@v4`,
  `@v0.17.0`, etc.) — never `@main`. Phase 34 follows this convention.
- **M6** — Code-signing (deferred to Phase 38) closes the chain.
  Apple notarytool + SignPath Authenticode + Tauri updater signature
  (ed25519). The verifier (`scripts/dist/verify_signed.py`) catches
  unsigned artifacts pre-publish.

**Residual risk:** **MEDIUM.** Build-time compromise of Tauri or Vite
toolchain is the bug class hardest to mitigate without reproducible
builds (deferred to v2.2 per `.planning/research/SUMMARY.md`).

---

## What's intentionally NOT covered

- **Repudiation** (the "R" in STRIDE) — vibemix has no auditable
  multi-user surface. Single-user desktop app.
- **Denial of service against client** — if you have local access to
  the user's machine you can kill the app. Not interesting.
- **Information disclosure to the user themselves** — that's the
  product, not an attack.
- **At-rest encryption of recordings** — local-only files with 0o600
  perms. v2.2 will add optional encryption.
- **HSM / TPM integration** — explicitly out of scope (v1 is desktop
  Python; not a context for HSM keying).

## Sign-off

- **Threat-model owner:** Kaan Özkan
- **Last reviewed:** 2026-05-15 (Phase 34)
- **Next review:** v1.1 release (re-evaluate per-install JWT rotation
  cadence and abuse-log retention policy).
