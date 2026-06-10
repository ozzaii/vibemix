import { describe, expect, it } from "vitest";

import { selectReactionIntent } from "./reaction-intent.js";

describe("selectReactionIntent", () => {
  it("maps a fresh whitelisted snapshot intent to a production mascot state", () => {
    const selected = selectReactionIntent(
      { type: "snapshot", reaction_intent: "fist_pump", reaction_intent_seq: 7 },
      6,
    );
    expect(selected).toEqual({
      intent: "fist_pump",
      seq: 7,
      state: "celebrate",
    });
  });

  it("dedupes the same 30Hz snapshot sequence", () => {
    expect(
      selectReactionIntent(
        { type: "snapshot", reaction_intent: "fist_pump", reaction_intent_seq: 7 },
        7,
      ),
    ).toBeNull();
  });

  it("allows the same intent to re-fire when the backend increments the sequence", () => {
    const first = selectReactionIntent(
      { type: "snapshot", reaction_intent: "nod", reaction_intent_seq: 1 },
      0,
    );
    const second = selectReactionIntent(
      { type: "snapshot", reaction_intent: "nod", reaction_intent_seq: 2 },
      first?.seq ?? 0,
    );
    expect(first?.state).toBe("react_yes");
    expect(second?.state).toBe("react_yes");
    expect(second?.seq).toBe(2);
  });

  it("drops unknown intents and frames without a numeric sequence", () => {
    expect(
      selectReactionIntent(
        { type: "snapshot", reaction_intent: "wink", reaction_intent_seq: 1 },
        0,
      ),
    ).toBeNull();
    expect(
      selectReactionIntent(
        { type: "snapshot", reaction_intent: "wave", reaction_intent_seq: "1" },
        0,
      ),
    ).toBeNull();
  });

  it("selects intents off the REAL flat live frame (no type key)", () => {
    const selected = selectReactionIntent(
      {
        music: 0.4,
        voice: 0.0,
        mic: 0.0,
        bpm: 128,
        reaction_intent: "headbang",
        reaction_intent_seq: 3,
      },
      2,
    );
    expect(selected).toEqual({
      intent: "headbang",
      seq: 3,
      state: "react_drop",
    });
  });
});
