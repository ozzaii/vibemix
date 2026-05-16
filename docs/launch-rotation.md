# vibemix v2.1 Launch — 24h Monitoring Rotation

**Phase 39 / SHIP-07 / P79**
**Supersedes:** `docs/day-zero-rota.md` (Phase 36 — 72h shift skeleton) for the v2.1 launch day specifically.

This document is the hourly hot-desk plan for the first 24 hours after the v2.1 RC binaries are public. Every hour is assigned to one of: **Kaan**, **Francesco**, **Bravoh-team** (Momo / Francis / on-call rotation).

## Owners

| Role | Person | Reach |
|------|--------|-------|
| Primary responder (RC bake) | Kaan | Discord DM, Telegram, +90 phone |
| Secondary + EU evening | Francesco | Discord DM, WhatsApp |
| Bravoh-team async | Momo / Francis | Bravoh Slack, Discord |
| Bravoh proxy on-call | Musa | api.altidus.world incidents |

## Per-hour shift (24h, all times CET)

Launch slot: **09:00 CET** (P78 — HN front-page sweet spot; Europe morning awake; US wake-up cohort).

| Hour (CET) | T-offset | Responder | Focus |
|---|---|---|---|
| 08:00 | T-1   | Kaan       | Final pre-flight check; cut_release.sh dry-run; KAAN-ACTION-LEGAL §SHIP review |
| 09:00 | T+0   | Kaan       | Flip release draft → published; trigger publish_social_posts NACK window |
| 10:00 | T+1   | Kaan       | Discord launch post + role ping; first hour Issues + comments triage |
| 11:00 | T+2   | Kaan       | HN front-page check; star velocity sample; Twitter replies |
| 12:00 | T+3   | Francesco  | EU lunch wave; IG IT engagement; quote-tweet amplification |
| 13:00 | T+4   | Francesco  | Reddit r/DJs comment triage; quote-tweet replies |
| 14:00 | T+5   | Bravoh-team | Async monitor (Momo): GitHub Issues triage + healthz pulse + Bravoh proxy load (Musa) |
| 15:00 | T+6   | Bravoh-team | Discord triage + community greeting flow |
| 16:00 | T+7   | Francesco  | EU afternoon peak; IG EN/IT replies; respond to Bravoh-funnel signups |
| 17:00 | T+8   | Francesco  | EU evening start; track star velocity; check for first install bugs |
| 18:00 | T+9   | Francesco  | EU evening DJ-set hour; expect controller-mapping reports |
| 19:00 | T+10  | Francesco  | EU evening; HN comments responses |
| 20:00 | T+11  | Kaan       | US evening wave begins; Twitter primary; HN comments |
| 21:00 | T+12  | Kaan       | US prime time; Discord live engagement; bug-report triage |
| 22:00 | T+13  | Kaan       | US prime; respond to Bravoh-funnel signups; promote standout community moments |
| 23:00 | T+14  | Kaan       | US late evening; HN drift down; Twitter wind-down |
| 00:00 | T+15  | Bravoh-team | Async monitor (overnight on-call); pager-only for showstoppers |
| 01:00 | T+16  | Bravoh-team | Async monitor |
| 02:00 | T+17  | Bravoh-team | Async monitor |
| 03:00 | T+18  | Bravoh-team | Async monitor |
| 04:00 | T+19  | Bravoh-team | Async monitor |
| 05:00 | T+20  | Bravoh-team | Async monitor |
| 06:00 | T+21  | Kaan       | TR morning wake; check overnight Issues + Discord backlog |
| 07:00 | T+22  | Kaan       | TR morning; star velocity snapshot; AU/NZ wave |
| 08:00 | T+23  | Francesco  | EU morning re-engage; day-2 plan with Kaan |
| 09:00 | T+24  | Kaan       | T+24h recap post; healthz snapshot; KPI review; hand off to async rota |

## Per-hour checklist (every responder, every hour)

1. **Discord triage** — open `#vibemix` server, scroll messages since last check, react ✅ to anything OK, escalate red flags.
2. **GitHub Issues** — `gh issue list --state open --label triage` — label + assign within the hour.
3. **healthz** — `bash scripts/dayzero/healthz_check.sh --max-iterations 1 --interval 0` — must return 200.
4. **Star velocity** — `gh api /repos/bravoh/vibemix --jq .stargazers_count` — log delta vs previous hour.
5. **Bravoh proxy** — check `api.altidus.world/healthz` returns 200; spot-check Gemini call latency.

## Escalation paths

| Scenario | Tier-1 (act now) | Tier-2 (escalate) | Tier-3 (war-room) |
|----------|-----------------|------------------|-------------------|
| **Showstopper bug** (install fails, app crashes on launch) | Kaan/Francesco posts an issue + pins it in Discord | Hotfix branch + emergency RC2 | Pull binaries from Releases; "downloads paused" banner in README |
| **Abuse / spam** (Discord flood, Issue spam) | Bravoh-team mute + delete | Francesco bans + reports | Kaan rotates webhook + revokes invite |
| **Traffic spike** (Bravoh proxy at >80% capacity) | Musa autoscales | Musa bumps rate limits | Kaan + Musa post "service stretched, queue active" Discord message |
| **Critical hallucination repro** (a DJ posts an AI-slop reaction video) | Kaan pulls events.jsonl from reporter | Kaan inspects evidence registry + prompt | Hotfix prompt template; RC2 if needed |
| **GitHub Actions failure** | Kaan re-runs | Kaan investigates + holds publish | Block release; post Discord delay note |
| **Apple/SignPath signing failure post-tag** | DIST-19 smoke validates | Re-run release.yml | Pause publish; document in §DIST KAAN-ACTION-LEGAL |
| **Mass controller-mapping bug** | Kaan pins thread | Kaan collects repro + dump_midi.py logs | Add controller to v2.2 sniff queue |
| **Legal/copyright issue** | Francesco triages | Francesco contacts Bravoh legal | Pause distribution; consult Bravoh SAGL |

## Handoff format (Discord `#vibemix-rota`)

End of each hour, the responder posts:

```
T+<hour> handoff | <responder> → <next>
Open issues:     <N> (link to triage list)
Open Discord:    <M> threads, <K> red flags
Stars delta:     +<X> since T+<hour-1>
healthz:         OK / WARN / FAIL
Notes:           <one-line summary>
Next watch:      <bullet points if any>
```

## Post-24h transition

At T+24, hand off to `docs/day-zero-rota.md` async cadence (4h-block primary checks for T+24→T+72, then normal cadence). Kaan drafts `docs/v2.1.0-launch-retro.md` at T+72 covering:

- What broke
- What surprised us
- HN / Reddit / Twitter momentum curves
- Star quality split (aligned-community vs cold)
- Anti-slop bug reports + how we triaged
- Decision: cut v1.0.0 from RC1, or cycle RC2?

## References

- `docs/day-zero-rota.md` — 72h post-launch cadence (Phase 36, predecessor)
- `scripts/dayzero/launch_trigger.sh` — T-30/T+0/T+5/T+24h stage sequence
- `KAAN-ACTION-LEGAL.md §SHIP` — all customer-facing publish actions
- `scripts/dayzero/seed_stars.md` — P59 aligned-community sourcing
- `docs/post-launch-playbook.md` — broader post-launch playbook
