// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";

import { parseDebriefBootUrl } from "../url-state.js";

describe("parseDebriefBootUrl", () => {
  it("keeps URLSearchParams-decoded percent signs intact", () => {
    const state = parseDebriefBootUrl(
      "?session=/tmp/Kaan%20%25crate&deepLinkEventId=ev%3AKICK%40%25&deepLinkTimestampS=7.5",
    );

    expect(state.sessionDir).toBe("/tmp/Kaan %crate");
    expect(state.sessionId).toBe("Kaan %crate");
    expect(state.deepLink).toEqual({ eventId: "ev:KICK@%", timestampS: 7.5 });
  });

  it("drops deep links with invalid timestamps", () => {
    const state = parseDebriefBootUrl(
      "?session=/tmp/session-a&deepLinkEventId=ev%3A1&deepLinkTimestampS=nope",
    );

    expect(state.sessionDir).toBe("/tmp/session-a");
    expect(state.deepLink).toBeNull();
  });

  it("recognizes explicit mock mode", () => {
    expect(parseDebriefBootUrl("?mock=1").isMockMode).toBe(true);
    expect(parseDebriefBootUrl("?session=mock")).toMatchObject({
      sessionDir: "/tmp/vibemix-demo-session",
      sessionId: "demo-session",
      isMockMode: true,
    });
  });
});
