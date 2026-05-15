# Gemini 3 Flash Judge Rubric — vibemix Eval Harness (EVAL-02 Flash side)

Binary pass/fail judge. ONE question to answer:

**Does the spoken response semantically anchor to the cited event?**

Pass criteria (ALL must hold):
- The response carries at least one citation tag (`[ev:...]`, `[track:...]`,
  `[mix:...]`, or `[emote:...]`).
- The non-citation prose describes WHAT happened in the music using
  listener language (texture / weight / energy / instrument /
  transition), NOT a generic acknowledgment.
- Removing the citation tag still leaves a sentence that makes sense as a
  reaction to the cited event.

Fail criteria (ANY triggers fail):
- The response is < 8 words after stripping citation tags.
- The response is a filler grunt with a citation pasted on
  (e.g. "Yeah. [ev:KICK_SWAP@1:23]" — Pitfall P45).
- The response references an event NOT in the evidence (hallucination).
- The response semantically describes a different event than the cited
  one (e.g. cites KICK_SWAP but talks about a vocal sample).

Emit a JSON object:

```json
{
  "pass": true | false,
  "why":  "<1 sentence reason>"
}
```

ANTI-SELF-PRAISE INSTRUCTION: do NOT pass a response just because it
contains the right citation syntax. The semantic anchor matters more than
the syntactic citation. Score harshly when in doubt.

Pitfall P42 mitigation: this rubric INTENTIONALLY diverges from the Pro
rubric — Pro scores 6 axes including tone + brevity; Flash asks ONLY
the semantic-anchor question. Cross-check by min() aggregation detects
collusion between the two judges.

DO NOT explain your reasoning before the JSON. DO NOT wrap the JSON in
code fences. Emit ONLY the JSON object.
