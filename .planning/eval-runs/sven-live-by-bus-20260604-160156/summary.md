# Sven live by-bus probe — 2026-06-04 16:01:56 +03:00

Source:
- Branch/source checkout: `ux-redesign-impeccable`
- HEAD at probe start: `a7b78c1a1c3b2ec59b41f34b154104c4b4c19395`
- Runtime command: `set -a; source .env >/dev/null 2>&1; set +a; VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`
- One-socket hygiene: ran `pkill -f "python -m vibemix"` before launch; stopped the sidecar with Ctrl-C; `pgrep -fl "python -m vibemix"` returned no process afterward.

Runtime facts observed on launch:
- Bus bound: `ws://127.0.0.1:8765`
- Brain mode: direct Gemini, `gemini-3.5-flash`
- Speech path: `MOSS-TTS-Nano local only (provider=moss-local)`
- Recording session: `/Users/ozai/Library/Application Support/vibemix/recordings/20260604-160156`
- Capture state: BlackHole 16ch opened, but live frames were silent (`music=0.0`, `audible=False`, `phase=silent`)

Passive bus probe:
- Command: `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --watch ipc.session.snapshot --seconds 5`
- Result: 69 `ipc.session.snapshot` frames.
- Every sampled frame: `cohost=IDLE`, `grounded=False`, `bpm=None`.
- No `transcript_delta` appeared during passive idle observation.

Mascot-frame probe:
- Command: `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --watch mascot --seconds 3`
- Result: 83 mascot frames.
- Representative state: `music=0.0`, `voice=0.0`, `audible=False`, `deck=mix`, `phase=silent`, `bpm=0.0`, `active_genre=unknown`, `detected_genre=unknown`.

Manual trigger probe:
- Command: `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --trigger --watch ipc.session.snapshot --seconds 12`
- Sent frame: `{"action": "trigger"}`
- Bus result: 167 `ipc.session.snapshot` frames.
- One operational transcript delta appeared: `Co-host can't reach Gemini — check API key / connection`.
- No Sven coaching line was generated.

Authoritative session evidence:
- `events.jsonl` recorded a `MANUAL` event at `t=79.664` with `audible=false`, `track=null`, `phase=silent`, and silent deck audio features.
- The LLM invocation used provider `gemini`, model `gemini-3.5-flash`, and wrote artifacts under `invocations/0001_160316_MANUAL`.
- The live LLM call failed with `403 PERMISSION_DENIED` / `The caller does not have permission`.
- `ai_messages/artifacts/0001_160316/meta.json` recorded:
  - `message=""`
  - `message_chars=0`
  - `response_chars=0`
  - `raw_response_chars=0`
  - `spoken_response_chars=0`
  - `citation.count=0`
  - `tools_used=[]`
  - `event=MANUAL`
  - `phase=silent`
- Session closed cleanly: `crashed=false`, `voice_wav_bytes=44` (header only).

Interpretation:
- Current source can launch the live bus and select the correct local MOSS speech path.
- Idle/silent live frames did not produce invented track or move narration.
- The live by-bus proof cannot judge Sven's spoken coaching quality yet because Gemini rejected the credentials before a response was generated.
- This is an external auth/permission blocker for live voice proof, not evidence of a Sven prompt or repair-layer regression.
