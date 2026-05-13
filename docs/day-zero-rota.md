# Day-Zero Responder Rota

> Coverage plan for the first 72 hours after `git tag v0.1.0`.
> Phase 20 Plan 20 Task 2.

## Owners

| Role                  | Person     | Reach                          |
|-----------------------|------------|--------------------------------|
| Primary responder     | Kaan       | Discord DM, Telegram, +90 phone |
| Secondary responder   | Francesco  | Discord DM, WhatsApp           |
| Backend escalation    | Musa       | Discord DM, Slack (Bravoh)     |

Primary owns the first response. Secondary takes over when primary is
off-shift. Backend escalation handles anything that touches
`api.altidus.world` (proxy, signing, telemetry).

## First 72 hours — shift schedule (all times CET)

| Window         | Hours | Primary    | Notes                                  |
|----------------|-------|------------|----------------------------------------|
| T+0 → T+8      | 09–17 | **Kaan**       | Launch day. All-hands on deck.     |
| T+8 → T+16     | 17–01 | **Francesco**  | Evening EU → late-night US.        |
| T+16 → T+24    | 01–09 | **Kaan**       | Morning monitor + retro start.     |
| T+24 → T+48    | day 2 | Async       | Critical-only. 4h SLA on `triage`.    |
| T+48 → T+72    | day 3 | Async       | Daily standup at 10:00 CET.           |
| T+72 onwards   | —     | Async       | Normal cadence; retro doc drafted.    |

Day-1 is hot. Days 2–3 are async — primary checks issues + Discord at
the top of every 4h block.

## Alert classes + who responds

| Alert                                          | First responder      | Action                                                          |
|------------------------------------------------|----------------------|-----------------------------------------------------------------|
| GitHub Actions release matrix failed           | Kaan                 | Re-run; if 2nd run also fails, hold publish + post in Discord.  |
| `verify_binary_failed` count > 1% / 1h         | Musa                 | Pull artifact, run `verify_binary.py --report`, rotate API key. |
| Per-DAU Gemini cost > median + 3·MAD           | Musa                 | Check `/v1/telemetry/event` traffic for anomaly; consider rate-limit bump. |
| Notarization rejected by Apple                 | Francesco            | Inspect rejection email; common cause = missing hardened-runtime. |
| User reports installer doesn't open            | Kaan                 | Reproduce; if signed-cert issue, check cert validity, re-sign.  |
| Mass controller-mapping bug reports            | Kaan                 | Pin a Discord thread; collect repro details + dump_midi.py logs.|
| Critical hallucination repro                   | Kaan                 | Pull events.jsonl from reporter; check anti-slop config; hotfix prompt template if rule miss. |
| Discord moderation issue                       | Francesco            | Cool down; mute if needed; document in retro.                   |

## Async handoff format

End-of-shift Discord post in `#vibemix-rota`:

```
EOS: <name> | T+<hour>
Open: <N> issues, <M> Discord threads
Hot: <list any in-progress or watching>
Handover: <next responder>
```

## Retro

End of day 3 (T+72), Kaan drafts `docs/v0.1.0-launch-retro.md`:
- What broke
- What surprised us
- What the rota model needs to change for the next release
- Star count + Discord member growth as supporting data

## Pager-style escalation

If the primary responder is unreachable for >2h on day 1, secondary
takes over and pings Bravoh #engineering. Day 2+ uses 4h SLA — no
overnight wake-ups unless a critical alert fires.
