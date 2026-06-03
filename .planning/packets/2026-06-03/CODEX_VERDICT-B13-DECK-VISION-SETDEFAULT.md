# CODEX VERDICT - B13 deck-vision setdefault

Item: B13 - light launchd-dark deck vision by defaulting
`VIBEMIX_DECK_VISION`.

SHA: `eb18efb0` (audited current HEAD; no code change)

Verdict: no-code reject. The CODEX_READY packet's corrected premise holds at
current source: adding `os.environ.setdefault("VIBEMIX_DECK_VISION", "1")` would
start a screen-capture buffer, but no live consumer reads that buffer into
Sven, MusicState, or a cited claim. It would spend CPU and jump the documented
deck-vision eval gate without making the app hear, see, or feel more intelligent.

Evidence:
- `_apply_packaged_defaults()` still only self-enables `VIBEMIX_LOCAL_TTS`.
- `_deck_vision_capture_enabled()` still gates only the ScreenCaptureKit capture
  loop.
- `DJCoHostAgent` still keeps the live screen leg hard-wired off.
- `DeckPoller` still defaults `vision_enabled=False` and documents the Kaan
  sign-off gate.
- `tests/test_main_smoke.py` still pins deck vision default-off behavior.

By-eye / by-ear artifact:
- No runtime proof was launched for this item because the packet's acceptance
  criterion is explicitly not "the dead loop runs"; the next real proof would
  require a deck-vision reader wired through the eval-cleared DeckPoller path and
  a cited screen-derived deck fact resolving in the EvidenceRegistry.

Grounding / gates:
- No co-host say/when path changed.
- Owner gates remain: deck-vision accuracy eval and Kaan sign-off before any
  vision-derived deck fact can influence state or voice.

Packet assumption:
- The packet is correct: do not flip the default until the downstream consumer
  exists and the eval gate is cleared.
