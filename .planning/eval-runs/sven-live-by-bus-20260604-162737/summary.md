# Sven live by-bus proof — 2026-06-04 16:27

## What this proves

Current source booted the live co-host bus and accepted a manual trigger without
inventing speech over silence.

- Session: `~/Library/Application Support/vibemix/recordings/20260604-162737`
- Launch: `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=1 VIBEMIX_DROP_DEBUG=1 .venv/bin/python -m vibemix`
- Bus: `ws://127.0.0.1:8765`
- Status tick: `livekit=ok`, `gemini=ok`, `midi=1`, `screen=unavailable`
- Voice path: startup selected `MOSS-TTS-Nano local only (provider=moss-local)`
- Brain path: startup selected `direct (GEMINI_API_KEY from .env)`, `gemini-3.5-flash`
- Manual trigger: sent by `.claude/skills/drive-vibemix/scripts/ws_probe.py --trigger`
- Result: `manual_silence_short_circuit`, reason `manual_no_live_evidence`
- LLM/TTS: skipped; `audio_tokens_est=0`, `avoided_audio_tokens_est=1536`
- User-heard line: none; `message=""`, `spoken_response_chars=0`
- Session ended cleanly: `crashed=false`, `duration_s=77.995`
- Socket cleanup: no process left listening on `127.0.0.1:8765` after stop

## Key event evidence

`events.jsonl` recorded:

- `event=MANUAL`, `audible=false`, `deck=none`, `track=null`, `phase=silent`
- `deck_audio_parts_skipped`, reason `deck_audio_silent`
- `mic_part_skipped`, reason `kaan_spoke_not_recent`
- `lookahead_part_skipped`, reason `no_lookahead`
- `manual_silence_short_circuit`, reason `manual_no_live_evidence`
- `ai_message`, `stop_reason=manual_no_live_evidence`, `suppression=manual_no_evidence`

## Limitation

This is not the keystone spoken-coaching proof. There was no live music evidence
in the capture (`music=0.000`, decks muted), so Sven correctly stayed silent
instead of hallucinating. The remaining live gate is still a driven set with
nonzero music RMS, nonzero voice RMS, and a grounded co-host line whose citation
resolves in `EvidenceRegistry`.
