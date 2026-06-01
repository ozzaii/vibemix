# No Spoken Fallbacks Invariant

Date: 2026-05-31

## Product Rule

If the system catches an unsafe live claim, Sven must not speak a canned
replacement. A guard hit means the turn was unsafe. The correct default for the
live co-host is:

1. log the raw model text,
2. log the guard reason and evidence summary,
3. enqueue it for repair/eval if needed,
4. stay silent on the audio path.

Do not turn safety fallbacks into user-facing product behavior. That reads fake,
and it trains the product to sound confident while admitting it lacks evidence.

## What Happened

Two different paths exposed the same bad phrase:

- Viber/library chat produced a bad text row for request
  `find me dark rolling hypnotic techno` while live context was attached:
  `I caught the live move. The useful note is the sound change right there.`
- Sven/live co-host separately spoke the same phrase in recorded sessions after
  `live_claim_guard` caught unsupported transition/EQ/live-move claims.

Current source evidence does not show a direct Viber -> Sven TTS bridge. The
actual coupling was worse and subtler: both paths used the same shared held
reply copy, and `DJCoHostAgent.llm_node` emitted the guard-corrected text as
audio.

## Engineering Fix Shape

Viber/chat may still return an honest text result such as "no grounded library
results" when the user explicitly asks the library agent. Sven/live co-host must
not voice guard replacements on unsolicited live events.

For live co-host turns, `live_claim_guard.corrected == true` should be treated
like a strip:

- no yielded TTS chunks,
- no `ai_text` spoken row,
- no transcript/cohost-reaction publish,
- raw and corrected text remain in artifacts/logs,
- `reaction_evidence` / `ai_message` stop reason records the strip.

## Release Gate

Before release, run the cohost/Viber report against the final recording set and
fail any blocker where:

- a Viber library/crate request is answered with live/deck/move language, or
- a live-cohost guard replacement becomes spoken audio/transcript/UI reaction.

Controller hardware is not required for the deterministic guard tests, but any
fresh hardware-specific claim still needs a live pass when the controller is
plugged in again.
