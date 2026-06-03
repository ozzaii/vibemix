# CODEX VERDICT - B2

Item: B2 - route the Learn tutor through MOSS.

SHA: `24895730bc2716e05547834b2019a92153ad4db6`

Verdict: shipped.

User value: a Pro Learn user now hears the authored tutor line through the same local MOSS Sven voice used by the live co-host, instead of only seeing a silent subtitle.

By-ear / by-eye artifact:

- Ran the real source app with `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`.
- Boot confirmed the safe output route: `AI voice -> Multi-Output Device @ 24000Hz` and `djay passthrough -> Multi-Output Device @ 48000Hz`.
- Live Tauri shell was running against the source sidecar.
- Fired `ipc.learn.start_lesson` + `ipc.learn.ack` for `L1.03` (`eq_hi:A`, MIDI source). The bus emitted `ipc.learn.lesson_loaded`, `ipc.learn.highlight`, two `ipc.learn.tutor_speak` frames, `ipc.learn.advance`, and `ipc.learn.complete_lesson`.
- UI log showed the tutor speech while voice meters moved: pill frames reached `voice=0.086`, `voice=0.07`; snapshots showed `cohost_status="TALKING"`, `bpm:null`, and `grounded:false`.
- UI pill BPM stayed suppressed during Sven loopback: frames showed `bpm:0`, not the previous stale `101.7` / voice-derived BPM.
- Events ledger recorded `learn_tutor_speak` and `ai_message`. The second line carried `citations=["[screen:eq_hi:A]"]` with `citation.count=1`, `valid=true`.

Grounding and tests:

- `uv run ruff check ...` passed for touched source/tests.
- Focused runtime/voice gate: `217 passed`.
- Grounding/invariant gate: `187 passed`.
- UI idle-fault invariant: `npm --prefix tauri/ui test -- tests/session/grounding-failure.spec.ts` -> `12 passed`.

Assumption corrections:

- The packet's flagship `L2.01` Learn proof is still locked in this local progress state (`course_2_unlocked=false`), so the live voice route was proven through unlocked `L1.03`. This exercises the same `LearnTutorSpeak` -> MOSS sink and grounded tutor ledger.
- A live proof found an adjacent BPM/display bug: Sven loopback could leave stale flat-frame BPM and stale grounded snapshots. The B2 commit includes the low-risk guards that made the visible pill frame and session snapshot honest during tutor speech.
