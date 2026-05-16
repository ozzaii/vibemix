# Bravoh Ops Endpoint — `api.altidus.world/vibemix/*`

**Phase:** 36 (Day-Zero Operations Automation) — REQ-ID OPS-14.
**Owner:** Bravoh team owns server-side implementation. vibemix client + docs live in this repo.

This document specifies the HTTP contract between the vibemix client + CI + healthz watchdog, and the Bravoh-side proxy/ops endpoint. Server-side deployment is Kaan/Bravoh-action (see `.planning/KAAN-ACTION-LEGAL.md` OPS-14-SERVER).

---

## 1. Auto-updater upload (`POST /vibemix/updates/upload`)

Used by `release.yml` CI after Phase 38 signing succeeds.

**Auth:** `Authorization: Bearer <bravoh-update-token>` (rotated per release; lives in GitHub Secrets).

**Request:** multipart/form-data with fields:
- `binary` (file, required) — signed `.dmg` (macOS) or `.msi` (Windows) bundle.
- `signature` (file, required) — `.sig` notarization-ticket or Authenticode chain proof.
- `version` (string, required) — semver tag e.g. `v2.1.0`.
- `channel` (string, required) — `stable` | `beta` | `nightly`.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "sha256": "<sha256-of-binary>",
  "url": "https://api.altidus.world/vibemix/updates/binaries/<channel>/<version>/<filename>"
}
```

**Rate limits:** 1 upload per 5-minute window per token. CI retries with exponential backoff (cap 3 retries).

---

## 2. Updater feed (`GET /vibemix/updates/latest.json`)

Used by the Tauri updater client. Cross-link: `docs/updater.md` (Tauri-specific config).

**Auth:** none (public-read).

**Response:**
```json
{
  "channel": "stable",
  "version": "v2.1.0",
  "sha256": "<sha256>",
  "url": "https://api.altidus.world/vibemix/updates/binaries/stable/v2.1.0/vibemix.dmg",
  "released_at": "2026-06-XX",
  "release_notes_url": "https://github.com/bravoh-ai/vibemix/releases/tag/v2.1.0"
}
```

**Rate limits:** 60 req/min per IP (DDOS protection).

---

## 3. Healthz (`GET /vibemix/healthz`)

Used by `scripts/dayzero/healthz_check.sh` cron.

**Auth:** none.

**Response:** `200 OK` JSON body:
```json
{
  "status": "ok",
  "uptime_s": 12345,
  "version": "v2.1.0",
  "checked_at": "2026-06-XX T HH:MM:SSZ"
}
```

**Failure modes:** any non-200 triggers Discord webhook alert (vibemix-side). PagerDuty escalation happens Bravoh-side, not vibemix.

---

## 4. Discord webhook (vibemix → Discord, NOT Bravoh)

vibemix client + healthz cron post directly to a Discord channel webhook URL (`DISCORD_WEBHOOK_URL` env). NOT an api.altidus.world endpoint.

---

## 5. Retry / backoff guidance

- All client retries: exponential backoff, base 1s, factor 2, cap 30s.
- Max retries:
  - Upload (one-shot): 3 (CI fails after).
  - Updater feed (background): 5 (silent fail acceptable — user opts to retry next session).
  - Healthz cron: 1 (immediate Discord alert on any failure).

---

## 6. CI bash audit (Pitfall P46)

The vibemix repo's `scripts/dist/verify_signed.py` greps all workflow files + scripts for `POST` or `PUT` to `apple.com`/`signpath.io`/`notarytool` endpoints. The `api.altidus.world/vibemix/updates/upload` endpoint is NOT covered by P46 (it's a Bravoh-internal endpoint, not legal-capacity). The audit's allowlist explicitly includes the Bravoh endpoint.

---

## 7. Server-side ownership boundary

| Concern | Owner |
|---|---|
| `POST /vibemix/updates/upload` impl | Bravoh team |
| `GET /vibemix/updates/latest.json` impl | Bravoh team |
| `GET /vibemix/healthz` impl | Bravoh team |
| PagerDuty integration | Bravoh team |
| Token issuance + rotation | Bravoh team |
| Rate-limit enforcement | Bravoh team |
| vibemix client code that hits these | vibemix repo |
| Tauri auto-updater config | vibemix repo (`docs/updater.md`) |
| Healthz cron + Discord webhook integration | vibemix repo (`scripts/dayzero/`) |

Server-side deployment status tracked in `.planning/KAAN-ACTION-LEGAL.md` entry **OPS-14-SERVER**.
