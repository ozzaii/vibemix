/**
 * @vitest-environment jsdom
 *
 * Phase 62 Plan 04 — pill index.ts frame→state contract (Task 2).
 *
 * Asserts the reader/writer frame fan-out (62-PATTERNS "Frame fan-out") via
 * the pure exported helpers `toPillFrame` + `reduceFrame` — no bus, no boot:
 *   - snapshot cohost_status TALKING/LISTENING/IDLE → speaking/listening/idle
 *   - defensive voice read: flat `voice` OR nested `meters.voice.rms` (LIVE-05a)
 *   - cohost-reaction (bare + ipc-prefixed) → expand with the VERBATIM text
 *   - flat `voice > threshold` is carried even when cohost_status is absent
 *
 * jsdom env: index.ts imports citation-strip.ts, whose registerStyle() touches
 * document.head at module load — so this spec needs a DOM (the @vitest-environment
 * docblock above routes it without a vitest.config change).
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { applyFrame, initialPillState, tickCollapse } from "./state-machine.js";
import { nextSuggestionRenderKey, type NextSuggestionWire } from "./next-suggestion.js";
import {
  pillFaceLabel,
  pillIntelState,
  pillDebriefInvokeArgs,
  pillCitationChipsRenderKey,
  pillReceiptRenderKey,
  pillOpenState,
  pillHoverCanOpen,
  pillDemoReactionFrame,
  pillDemoNextEnabled,
  pillDemoReactionKeyForShortcut,
  pillDemoReturnFrame,
  pillDemoPadHitPulseSlot,
  pillDemoControlsShouldBeFocusable,
  pillDemoControlsCanHandleShortcut,
  pillDemoControlsHandleShortcutKey,
  pillDemoShortcutTargetCanHandle,
  syncPillDemoControlsActive,
  syncPillDemoControlsHover,
  syncPillDemoPadPointer,
  syncPillDemoShortcutPadAim,
  resetPillDemoPadPointer,
  pillNextCompletionKey,
  pillSuggestionIsHandled,
  pillShouldClearHandledNextOnNull,
  pillPeekCloseKey,
  pillPeekHandleCloseKey,
  pillPeekHandlePrimaryActionClick,
  pillPeekHandlePrimaryActionKey,
  pillPeekPrimaryActionKey,
  pillShouldExposePeekFocus,
  pillShouldExposeNextChrome,
  pillShouldShowFaceWave,
  pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval,
  pillShouldSuppressNextFocusPeek,
  pillRenderLabel,
  pillRootAriaLabel,
  pillReactionDensity,
  pillReactionDisplayText,
  pillReactionFxProfile,
  pillReactionPulseSlot,
  pillNextPulseSlot,
  pillReactionLeadParts,
  pillReactionEchoLabel,
  pillReactionEchoVisible,
  pillRootPrimaryActionAvailable,
  pillWindowHeightForContent,
  pillWindowHeightRenderKey,
  PILL_DEMO_REACTION_KEYS,
  syncPillRootActionability,
  syncFocusableDescendants,
  reduceFrame,
  readDeckState,
  readNextSuggestion,
  toPillFrame,
} from "./index.js";

const T0 = 2_000_000;

describe("pill.css — actionable face polish", () => {
  const pillCss = readFileSync("src/pill/pill.css", "utf8");

  it("keeps the actionable face rail in the one-rose system", () => {
    const rowRailRule = pillCss.match(/\.pill__row::after\s*\{[^}]*\}/s)?.[0];
    expect(rowRailRule).toBeTruthy();
    expect(rowRailRule).toContain("var(--brand-65)");
    expect(rowRailRule).not.toMatch(/--gold/);
  });

  it("keeps demo reaction controls from stealing pointer events from an open pill", () => {
    expect(pillCss).toMatch(/\.pill-demo-controls\s*\{[^}]*z-index:\s*20;/);
    expect(pillCss).toMatch(
      /\.pill\[data-open="true"\] ~ \.pill-demo-controls\s*\{[^}]*z-index:\s*8;/,
    );
  });
});

describe("toPillFrame — defensive normalisation", () => {
  it("reads flat top-level voice on the live frame (LIVE-05a)", () => {
    const f = toPillFrame({ voice: 0.7, cohost_status: "TALKING" });
    expect(f?.voiceRms).toBe(0.7);
    expect(f?.cohostStatus).toBe("TALKING");
  });

  it("reads nested meters.voice.rms on the bridged snapshot (LIVE-05a)", () => {
    const f = toPillFrame({
      type: "snapshot",
      cohost_status: "TALKING",
      meters: { voice: { rms: 0.42, peak: 0.9 } },
    });
    expect(f?.voiceRms).toBe(0.42);
    expect(f?.voicePeak).toBe(0.9);
  });

  it("prefers the flat voice when both are present", () => {
    const f = toPillFrame({ voice: 0.55, meters: { voice: { rms: 0.1 } } });
    expect(f?.voiceRms).toBe(0.55);
  });

  it("drops non-finite voice levels instead of carrying NaN into the waveform", () => {
    expect(toPillFrame({ voice: Number.NaN })).toBeNull();
    const f = toPillFrame({
      type: "snapshot",
      cohost_status: "TALKING",
      meters: { voice: { rms: Number.POSITIVE_INFINITY, peak: Number.NaN } },
    });
    expect(f).toEqual({
      cohostStatus: "TALKING",
      voiceRms: null,
      voicePeak: null,
    });
  });

  it("returns null for a frame carrying nothing the pill reads", () => {
    expect(toPillFrame({ type: "snapshot", track: { title: "x" } })).toBeNull();
    expect(toPillFrame(null)).toBeNull();
    expect(toPillFrame("not an object")).toBeNull();
  });

  it("normalises a cohost-reaction to text + chips from citation_strip", () => {
    const f = toPillFrame({
      type: "cohost-reaction",
      cohost_status: "TALKING",
      voice: 0.62,
      peak: 0.74,
      text: "ride the kick",
      citation_strip: [{ event_id: "ev:KICK@1.0", verb: "kick", timestamp_s: 1.0 }],
    });
    expect(f?.type).toBe("cohost-reaction");
    expect(f?.text).toBe("ride the kick");
    expect(f?.chips?.length).toBe(1);
    expect(f?.cohostStatus).toBe("TALKING");
    expect(f?.voiceRms).toBe(0.62);
    expect(f?.voicePeak).toBe(0.74);
  });

  it("normalises a schema envelope cohost-reaction from payload", () => {
    const f = toPillFrame({
      type: "ipc.session.cohost-reaction",
      ts: "2026-05-28T12:00:00.000Z",
      payload: {
        text: "ride the kick from here",
        event_id: "HEARTBEAT",
        citation_strip: [
          { event_id: "ev:KICK@7.5", verb: "kick", timestamp_s: 7.5 },
        ],
      },
    });
    expect(f?.type).toBe("ipc.session.cohost-reaction");
    expect(f?.text).toBe("ride the kick from here");
    expect(f?.chips).toEqual([
      { event_id: "ev:KICK@7.5", verb: "kick", timestamp_s: 7.5 },
    ]);
  });

  it("WR-06: filters malformed citation chips (no `[undefined @ 0:00]` slop)", () => {
    const f = toPillFrame({
      type: "cohost-reaction",
      text: "kick swap",
      citation_strip: [
        42,
        null,
        {},
        { event_id: "ev:OK@2.0", verb: "kick", timestamp_s: 2.0 }, // the only valid one
        { event_id: "ev:BAD", verb: "x" }, // missing timestamp_s
        { event_id: 7, verb: "x", timestamp_s: 1 }, // event_id wrong type
        { event_id: "ev:NAN", verb: "x", timestamp_s: Number.NaN },
      ],
    });
    expect(f?.chips?.length).toBe(1);
    expect(f?.chips?.[0]?.event_id).toBe("ev:OK@2.0");
  });

  it("WR-06: a non-array citation_strip yields no chips (defensive)", () => {
    const f = toPillFrame({ type: "cohost-reaction", text: "x", citation_strip: "nope" });
    expect(f?.chips).toEqual([]);
  });
});

describe("reduceFrame — frame→state map (READER)", () => {
  it("TALKING → speaking", () => {
    const s = reduceFrame(initialPillState(T0), { cohost_status: "TALKING", voice: 0.5 }, T0 + 1);
    expect(s.mode).toBe("speaking");
    expect(s.voiceRms).toBe(0.5);
  });

  it("LISTENING → listening", () => {
    const s = reduceFrame(initialPillState(T0), { cohost_status: "LISTENING" }, T0 + 1);
    expect(s.mode).toBe("listening");
  });

  it("IDLE → idle", () => {
    const s = reduceFrame(
      reduceFrame(initialPillState(T0), { cohost_status: "TALKING", voice: 0.5 }, T0 + 1),
      { cohost_status: "IDLE" },
      T0 + 2,
    );
    expect(s.mode).toBe("idle");
  });

  it("a frame the pill ignores leaves the state unchanged (same ref)", () => {
    const s0 = initialPillState(T0);
    const s1 = reduceFrame(s0, { type: "snapshot", track: { title: "x" } }, T0 + 1);
    expect(s1).toBe(s0);
  });

  it("carries flat voice even when cohost_status is absent on the flat frame", () => {
    const s = reduceFrame(initialPillState(T0), { voice: 0.33 }, T0 + 1);
    expect(s.voiceRms).toBe(0.33);
  });
});

describe("readDeckState — latest-frame deck context (WR-03)", () => {
  it("returns the deck_state map verbatim when the frame carries one", () => {
    const ds = readDeckState({
      deck_state: { A: { title: "x", camelot: "8A", key: "C", bpm: 128, confidence: 0.9 } },
    });
    expect(ds).not.toBeNull();
    expect(ds!.A?.camelot).toBe("8A");
  });

  it("WR-03: an EMPTY deck_state {} is returned as {} (clears the chips on a deck unload)", () => {
    // A deck unload empties deck_state. readDeckState must return the empty map
    // (NOT null) so the caller replaces view.deckState with {} → the resolved
    // chip falls back to `decks · unknown` (no stale resolved key lingers).
    const ds = readDeckState({ deck_state: {} });
    expect(ds).not.toBeNull();
    expect(ds).toEqual({});
  });

  it("WR-03: a frame that OMITS deck_state returns null (caller keeps last — no thrash)", () => {
    // A bridged ipc.session.snapshot omits deck_state entirely; that frame says
    // nothing about decks, so the caller holds the last flat-frame map rather
    // than wiping it on every interleaved snapshot.
    expect(readDeckState({ type: "snapshot", meters: {} })).toBeNull();
    expect(readDeckState({})).toBeNull();
    expect(readDeckState(null)).toBeNull();
  });
});

describe("readNextSuggestion — tri-state (omitted / null / object)", () => {
  it("returns the suggestion object verbatim", () => {
    const ns = readNextSuggestion({
      next_suggestion: {
        track_id: "t1", title: "X", artist: "A", similarity: 0.8,
        why: "similar vibe", camelot: null, bpm: null,
      },
    });
    expect(ns).not.toBeNull();
    expect((ns as { track_id: string }).track_id).toBe("t1");
  });

  it("explicit null → null (the SuggestionService has no grounded pick → clear)", () => {
    expect(readNextSuggestion({ next_suggestion: null })).toBeNull();
  });

  it("OMITTED field → undefined (a bridged snapshot says nothing → hold last)", () => {
    expect(readNextSuggestion({ type: "snapshot" })).toBeUndefined();
    expect(readNextSuggestion({})).toBeUndefined();
    expect(readNextSuggestion(null)).toBeUndefined();
  });
});

describe("pillFaceLabel — booth-facing face copy", () => {
  it("uses COHOST while a reaction owns the opened body", () => {
    expect(pillFaceLabel("expand", "TALKING")).toBe("COHOST");
    expect(pillFaceLabel("speaking", "TALKING")).toBe("SPEAKING");
    expect(pillFaceLabel("listening", "LISTENING")).toBe("LISTENING");
    expect(pillFaceLabel("idle", "IDLE")).toBe("IDLE");
  });
});

describe("pillReactionDensity — opened reaction readability", () => {
  it("keeps normal reactions large and switches wordy reactions to long mode", () => {
    expect(pillReactionDensity("BOMB. That drop lands clean, ride it two bars.")).toBe("normal");
    expect(
      pillReactionDensity(
        "LIT AFF. That echo-out lands clean, bass swap is locked, ride the vocal for eight bars before you touch the filter.",
      ),
    ).toBe("long");
  });
});

describe("pillReactionDisplayText — long reaction booth glance", () => {
  it("keeps normal reactions verbatim", () => {
    const text = "BOMB. That drop lands clean, ride it two bars.";
    expect(pillReactionDisplayText(text, "normal")).toBe(text);
  });

  it("shortens long reactions while preserving the lead word", () => {
    const text =
      "LIT AFF. That echo-out lands clean, bass swap is locked, ride the vocal for eight bars before you touch the filter.";
    const display = pillReactionDisplayText(text, "long");
    expect(display).toMatch(/^LIT AFF\. /);
    expect(display.endsWith("…")).toBe(true);
    expect(display.length).toBeLessThan(text.length);
    expect(display.length).toBeLessThanOrEqual(92);
  });
});

describe("pillReactionLeadParts — reaction-first body styling", () => {
  it("extracts the supported reaction word while preserving exact text", () => {
    const parts = pillReactionLeadParts("BOMB. That drop lands clean.");
    expect(parts).toEqual({
      tone: "bomb",
      prefix: "",
      lead: "BOMB.",
      rest: " That drop lands clean.",
    });
    expect(`${parts.prefix}${parts.lead}${parts.rest}`).toBe("BOMB. That drop lands clean.");
  });

  it("keeps LIT AFF together as one lead reaction", () => {
    expect(pillReactionLeadParts("Lit Aff: ride the vocal.")).toEqual({
      tone: "lit_aff",
      prefix: "",
      lead: "Lit Aff:",
      rest: " ride the vocal.",
    });
  });

  it("supports clean, sexy, mid, and negative reactions", () => {
    expect(pillReactionLeadParts(" clean move").tone).toBe("clean");
    expect(pillReactionLeadParts("SEXY, tuck the bass").tone).toBe("sexy");
    expect(pillReactionLeadParts("SEXY, tuck the bass").lead).toBe("SEXY,");
    expect(pillReactionLeadParts("MID, not worth forcing").tone).toBe("mid");
    expect(pillReactionLeadParts("MID, not worth forcing").lead).toBe("MID,");
    expect(pillReactionLeadParts("NEGATIVE: key risk").tone).toBe("negative");
    expect(pillReactionLeadParts("NEGATIVE: key risk").lead).toBe("NEGATIVE:");
    expect(pillReactionLeadParts("NEGATIVES: stacked risk").tone).toBe("negative");
    expect(pillReactionLeadParts("NEG, key risk").tone).toBe("negative");
  });

  it("does not promote a reaction word from the middle of a sentence", () => {
    expect(pillReactionLeadParts("that was bomb but late")).toEqual({
      tone: null,
      prefix: "",
      lead: "",
      rest: "that was bomb but late",
    });
  });
});

describe("pillReactionFxProfile — canvas hit energy", () => {
  it("keeps hot reactions visibly stronger than care checks", () => {
    expect(pillReactionFxProfile("bomb").particleCount).toBeGreaterThan(
      pillReactionFxProfile("sexy").particleCount,
    );
    expect(pillReactionFxProfile("lit_aff").ringCount).toBe(2);
    expect(pillReactionFxProfile("sexy").glow).toBeGreaterThan(
      pillReactionFxProfile("clean").glow,
    );
    expect(pillReactionFxProfile("negative").particleCount).toBeGreaterThan(
      pillReactionFxProfile("mid").particleCount,
    );
    expect(pillReactionFxProfile(null)).toEqual({
      particleCount: 0,
      ringCount: 0,
      durationMs: 0,
      glow: 0,
    });
  });
});

describe("pillReactionPulseSlot — same-tone animation replay key", () => {
  it("alternates the shell animation slot by reaction revision", () => {
    expect(pillReactionPulseSlot(T0)).toBe("a");
    expect(pillReactionPulseSlot(T0 + 1)).toBe("b");
    expect(pillReactionPulseSlot(Number.NaN)).toBe("a");
  });
});

describe("pillNextPulseSlot — next-suggestion readiness replay key", () => {
  it("alternates the armed-next animation slot by pulse revision", () => {
    expect(pillNextPulseSlot(0)).toBe("a");
    expect(pillNextPulseSlot(1)).toBe("b");
    expect(pillNextPulseSlot(Number.NaN)).toBe("a");
  });
});

describe("pillDemoPadHitPulseSlot — active pad animation replay key", () => {
  it("alternates the active pad animation slot by hit revision", () => {
    expect(pillDemoPadHitPulseSlot(1)).toBe("b");
    expect(pillDemoPadHitPulseSlot(2)).toBe("a");
    expect(pillDemoPadHitPulseSlot(Number.NaN)).toBe("a");
  });
});

describe("pillReactionEcho — collapsed afterglow", () => {
  it("extracts a short booth label and only shows after the full reaction closes", () => {
    const echo = {
      label: "BOMB",
      tone: "bomb",
      key: "reaction:1",
      until: T0 + 1200,
    } as const;

    expect(pillReactionEchoLabel("BOMB. Room lifted.")).toBe("BOMB");
    expect(pillReactionEchoLabel("Lit Aff: whole room catches")).toBe("LIT AFF");
    expect(pillReactionEchoLabel("that was bomb")).toBe("");
    expect(pillReactionEchoVisible(echo, "expand", T0 + 10)).toBe(false);
    expect(pillReactionEchoVisible(echo, "speaking", T0 + 10)).toBe(false);
    expect(pillReactionEchoVisible(echo, "idle", T0 + 10)).toBe(true);
    expect(pillReactionEchoVisible(echo, "idle", T0 + 1300)).toBe(false);
  });
});

describe("pillDemoReactionFrame — demo buttons use real reaction frames", () => {
  it("covers every supported reaction tone and preserves lead styling", () => {
    expect(PILL_DEMO_REACTION_KEYS).toEqual([
      "clean",
      "sexy",
      "mid",
      "bomb",
      "lit_aff",
      "negative",
    ]);
    for (const key of PILL_DEMO_REACTION_KEYS) {
      const frame = pillDemoReactionFrame(key);
      expect(frame.type).toBe("cohost-reaction");
      expect(frame.text).toBeTruthy();
      expect(frame.chips?.[0]?.event_id).toContain(key);
      expect(pillReactionDensity(frame.text ?? "")).toBe("normal");
      expect(pillReactionLeadParts(frame.text ?? "").tone).toBe(key);
    }
  });

  it("returns the demo pill to idle after the reaction dwell", () => {
    const expanded = applyFrame(initialPillState(T0), pillDemoReactionFrame("sexy"), T0);
    const due = tickCollapse(expanded, T0 + 6000);
    const collapsed = applyFrame(due, pillDemoReturnFrame(), T0 + 6000);

    expect(expanded.mode).toBe("expand");
    expect(expanded.cohostStatus).toBe("TALKING");
    expect(collapsed.mode).toBe("idle");
    expect(collapsed.cohostStatus).toBe("IDLE");
    expect(collapsed.voiceRms).toBe(0);
    expect(collapsed.voicePeak).toBeNull();
  });
});

describe("pillDemoReactionKeyForShortcut — demo pad keyboard contract", () => {
  it("maps number keys 1-6 to the reaction pad order only", () => {
    expect(["1", "2", "3", "4", "5", "6"].map(pillDemoReactionKeyForShortcut)).toEqual(
      PILL_DEMO_REACTION_KEYS,
    );
    expect(pillDemoReactionKeyForShortcut("0")).toBeNull();
    expect(pillDemoReactionKeyForShortcut("7")).toBeNull();
    expect(pillDemoReactionKeyForShortcut("x")).toBeNull();
  });
});

describe("pillPeekPrimaryActionKey — focused DJ KNOWS completion", () => {
  it("accepts Enter and Space only", () => {
    expect(pillPeekPrimaryActionKey("Enter")).toBe(true);
    expect(pillPeekPrimaryActionKey(" ")).toBe(true);
    expect(pillPeekPrimaryActionKey("Space")).toBe(false);
    expect(pillPeekPrimaryActionKey("Escape")).toBe(false);
    expect(pillPeekPrimaryActionKey("1")).toBe(false);
  });
});

describe("pillPeekHandlePrimaryActionKey — real DJ KNOWS completion contract", () => {
  function dispatchRootPrimaryKey(
    root: HTMLElement,
    peek: boolean,
    hasSuggestion: boolean,
    key: string,
  ): { handled: boolean; ev: KeyboardEvent } {
    let handled = false;
    root.addEventListener(
      "keydown",
      (ev) => {
        handled = pillPeekHandlePrimaryActionKey(root, peek, hasSuggestion, ev);
      },
      { once: true },
    );
    const ev = new KeyboardEvent("keydown", {
      key,
      bubbles: true,
      cancelable: true,
    });
    root.dispatchEvent(ev);
    return { handled, ev };
  }

  it("prevents default from the focused root when a grounded suggestion is visible", () => {
    const root = document.createElement("button");
    const { handled, ev } = dispatchRootPrimaryKey(root, true, true, "Enter");

    expect(handled).toBe(true);
    expect(ev.defaultPrevented).toBe(true);
  });

  it("ignores child targets, closed peeks, empty suggestions, and unsupported keys", () => {
    const childTargetRoot = document.createElement("button");
    const child = document.createElement("span");
    childTargetRoot.append(child);
    let handledFromChild = true;
    childTargetRoot.addEventListener("keydown", (ev) => {
      handledFromChild = pillPeekHandlePrimaryActionKey(childTargetRoot, true, true, ev);
    });

    const childEvent = new KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true,
    });
    child.dispatchEvent(childEvent);
    expect(handledFromChild).toBe(false);
    expect(childEvent.defaultPrevented).toBe(false);

    const root = document.createElement("button");
    const closed = new KeyboardEvent("keydown", { key: "Enter", cancelable: true });
    expect(pillPeekHandlePrimaryActionKey(root, false, true, closed)).toBe(false);
    expect(closed.defaultPrevented).toBe(false);

    const empty = dispatchRootPrimaryKey(root, true, false, " ");
    expect(empty.handled).toBe(false);
    expect(empty.ev.defaultPrevented).toBe(false);

    const unsupported = dispatchRootPrimaryKey(root, true, true, "Escape");
    expect(unsupported.handled).toBe(false);
    expect(unsupported.ev.defaultPrevented).toBe(false);
  });
});

describe("pillPeekHandlePrimaryActionClick — face click DJ KNOWS completion contract", () => {
  function dispatchRootPrimaryClick(
    root: HTMLElement,
    target: HTMLElement,
    peek: boolean,
    hasSuggestion: boolean,
    button = 0,
  ): { handled: boolean; ev: MouseEvent } {
    let handled = false;
    root.addEventListener(
      "click",
      (ev) => {
        handled = pillPeekHandlePrimaryActionClick(root, peek, hasSuggestion, ev);
      },
      { once: true },
    );
    const ev = new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      button,
    });
    target.dispatchEvent(ev);
    return { handled, ev };
  }

  it("commits the visible suggestion from the collapsed pill face", () => {
    const root = document.createElement("div");
    const row = document.createElement("div");
    row.className = "pill__row";
    const label = document.createElement("span");
    label.className = "pill__label";
    row.append(label);
    root.append(row);

    const { handled, ev } = dispatchRootPrimaryClick(root, label, true, true);
    expect(handled).toBe(true);
    expect(ev.defaultPrevented).toBe(true);
  });

  it("ignores peek-card, drag, closed, empty, and non-primary clicks", () => {
    const root = document.createElement("div");
    const row = document.createElement("div");
    row.className = "pill__row";
    const peek = document.createElement("div");
    peek.className = "pill__peek";
    const card = document.createElement("div");
    card.className = "vmx-next-card";
    peek.append(card);
    const drag = document.createElement("div");
    drag.className = "pill__drag";
    const noDrag = document.createElement("div");
    noDrag.setAttribute("data-no-drag", "");
    row.append(noDrag);
    root.append(row, peek, drag);

    const fromPeek = dispatchRootPrimaryClick(root, card, true, true);
    expect(fromPeek.handled).toBe(false);
    expect(fromPeek.ev.defaultPrevented).toBe(false);

    const fromDrag = dispatchRootPrimaryClick(root, drag, true, true);
    expect(fromDrag.handled).toBe(false);
    expect(fromDrag.ev.defaultPrevented).toBe(false);

    const closed = dispatchRootPrimaryClick(root, row, false, true);
    expect(closed.handled).toBe(false);
    expect(closed.ev.defaultPrevented).toBe(false);

    const empty = dispatchRootPrimaryClick(root, row, true, false);
    expect(empty.handled).toBe(false);
    expect(empty.ev.defaultPrevented).toBe(false);

    const secondary = dispatchRootPrimaryClick(root, row, true, true, 2);
    expect(secondary.handled).toBe(false);
    expect(secondary.ev.defaultPrevented).toBe(false);
  });
});

describe("pillDemoControlsShouldBeFocusable — narrow expand discipline", () => {
  it("keeps the demo pad operable after opening because narrow CSS docks it", () => {
    expect(pillDemoControlsShouldBeFocusable("expand", true)).toBe(true);
    expect(pillDemoControlsShouldBeFocusable("expand", false)).toBe(true);
    expect(pillDemoControlsShouldBeFocusable("idle", true)).toBe(true);
    expect(pillDemoControlsShouldBeFocusable("speaking", true)).toBe(true);
  });
});

describe("pillDemoControlsCanHandleShortcut — hidden pad discipline", () => {
  it("blocks global number shortcuts while demo controls are inert or hidden", () => {
    const controls = document.createElement("div");
    expect(pillDemoControlsCanHandleShortcut(controls)).toBe(true);

    controls.setAttribute("aria-hidden", "true");
    expect(pillDemoControlsCanHandleShortcut(controls)).toBe(false);

    controls.setAttribute("aria-hidden", "false");
    controls.setAttribute("inert", "");
    expect(pillDemoControlsCanHandleShortcut(controls)).toBe(false);
  });
});

describe("syncPillDemoControlsActive — active pad receipt", () => {
  it("marks one hot-cue pad active and can clear the pad after dwell", () => {
    const controls = document.createElement("div");
    const stage = document.createElement("div");
    stage.id = "pill-demo-stage";
    document.body.append(stage);
    for (const key of PILL_DEMO_REACTION_KEYS) {
      const button = document.createElement("button");
      button.dataset.demoTone = key;
      button.setAttribute("aria-pressed", "false");
      if (key === "lit_aff") {
        button.getBoundingClientRect = () =>
          ({
            x: 256,
            y: 76.8,
            left: 256,
            top: 76.8,
            width: 512,
            height: 76.8,
            right: 768,
            bottom: 153.6,
            toJSON: () => ({}),
          }) as DOMRect;
      }
      controls.append(button);
    }

    syncPillDemoControlsActive(controls, "lit_aff");
    expect(controls.dataset.activeTone).toBe("lit_aff");
    expect(controls.dataset.hitPulseRevision).toBe("1");
    expect(stage.dataset.activeTone).toBe("lit_aff");
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("50.00%");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("15.00%");
    const firstHit = stage.querySelector<HTMLElement>(".pill-demo-stage__hit");
    expect(firstHit?.dataset.tone).toBe("lit_aff");
    expect(firstHit?.getAttribute("aria-hidden")).toBe("true");
    expect(
      Array.from(controls.querySelectorAll<HTMLButtonElement>("button")).map((button) => [
        button.dataset.demoTone,
        button.getAttribute("aria-pressed"),
        button.dataset.hitPulse,
      ]),
    ).toEqual([
      ["clean", "false", undefined],
      ["sexy", "false", undefined],
      ["mid", "false", undefined],
      ["bomb", "false", undefined],
      ["lit_aff", "true", "b"],
      ["negative", "false", undefined],
    ]);

    syncPillDemoControlsActive(controls, "lit_aff");
    expect(controls.dataset.hitPulseRevision).toBe("2");
    expect(
      controls.querySelector<HTMLButtonElement>('button[data-demo-tone="lit_aff"]')?.dataset
        .hitPulse,
    ).toBe("a");
    const secondHit = stage.querySelector<HTMLElement>(".pill-demo-stage__hit");
    expect(secondHit).not.toBe(firstHit);
    expect(stage.querySelectorAll(".pill-demo-stage__hit")).toHaveLength(1);

    secondHit?.dispatchEvent(new Event("animationend"));
    expect(stage.querySelector(".pill-demo-stage__hit")).toBeNull();

    syncPillDemoControlsActive(controls, "lit_aff");
    expect(stage.querySelector(".pill-demo-stage__hit")).not.toBeNull();

    syncPillDemoControlsActive(controls, null);
    expect(controls.dataset.activeTone).toBeUndefined();
    expect(controls.dataset.hitPulseRevision).toBeUndefined();
    expect(stage.dataset.activeTone).toBeUndefined();
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("");
    expect(stage.querySelector(".pill-demo-stage__hit")).toBeNull();
    expect(
      Array.from(controls.querySelectorAll<HTMLButtonElement>("button")).every(
        (button) => button.getAttribute("aria-pressed") === "false",
      ),
    ).toBe(true);
    stage.remove();
  });

  it("releases the previously active pad when another reaction fires", () => {
    const controls = document.createElement("div");
    const clean = document.createElement("button");
    clean.dataset.demoTone = "clean";
    clean.setAttribute("aria-pressed", "false");
    const sexy = document.createElement("button");
    sexy.dataset.demoTone = "sexy";
    sexy.setAttribute("aria-pressed", "false");
    controls.append(clean, sexy);

    syncPillDemoControlsActive(controls, "clean");
    expect(clean.getAttribute("aria-pressed")).toBe("true");
    expect(clean.dataset.hitPulse).toBe("b");
    expect(clean.dataset.releasePulse).toBeUndefined();

    syncPillDemoControlsActive(controls, "sexy");
    expect(clean.getAttribute("aria-pressed")).toBe("false");
    expect(clean.dataset.hitPulse).toBeUndefined();
    expect(clean.dataset.releasePulse).toBe("b");
    expect(sexy.getAttribute("aria-pressed")).toBe("true");
    expect(sexy.dataset.hitPulse).toBe("a");
    expect(controls.dataset.releasePulseRevision).toBe("1");

    clean.dispatchEvent(new Event("animationend"));
    expect(clean.dataset.releasePulse).toBeUndefined();

    syncPillDemoControlsActive(controls, "clean");
    expect(sexy.getAttribute("aria-pressed")).toBe("false");
    expect(sexy.dataset.releasePulse).toBe("a");
    expect(controls.dataset.releasePulseRevision).toBe("2");
  });
});

describe("syncPillDemoControlsHover — booth-light aim preview", () => {
  it("aims the dev stage at the hovered pad without firing a reaction hit", () => {
    const controls = document.createElement("div");
    const stage = document.createElement("div");
    stage.id = "pill-demo-stage";
    document.body.append(stage);

    const button = document.createElement("button");
    button.dataset.demoTone = "sexy";
    button.setAttribute("aria-pressed", "false");
    button.getBoundingClientRect = () =>
      ({
        x: 512,
        y: 153.6,
        left: 512,
        top: 153.6,
        width: 102.4,
        height: 76.8,
        right: 614.4,
        bottom: 230.4,
        toJSON: () => ({}),
      }) as DOMRect;
    controls.append(button);

    syncPillDemoControlsHover(controls, "sexy", button);
    expect(controls.dataset.hoverTone).toBe("sexy");
    expect(stage.dataset.hoverTone).toBe("sexy");
    expect(stage.dataset.activeTone).toBeUndefined();
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("55.00%");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("25.00%");
    expect(stage.querySelector(".pill-demo-stage__hit")).toBeNull();

    syncPillDemoControlsHover(controls, null);
    expect(controls.dataset.hoverTone).toBeUndefined();
    expect(stage.dataset.hoverTone).toBeUndefined();
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("");
    stage.remove();
  });

  it("returns the booth-light aim to the active pad when hover leaves", () => {
    const controls = document.createElement("div");
    const stage = document.createElement("div");
    stage.id = "pill-demo-stage";
    document.body.append(stage);

    const clean = document.createElement("button");
    clean.dataset.demoTone = "clean";
    clean.setAttribute("aria-pressed", "false");
    clean.getBoundingClientRect = () =>
      ({
        x: 0,
        y: 0,
        left: 0,
        top: 0,
        width: 102.4,
        height: 76.8,
        right: 102.4,
        bottom: 76.8,
        toJSON: () => ({}),
      }) as DOMRect;

    const sexy = document.createElement("button");
    sexy.dataset.demoTone = "sexy";
    sexy.setAttribute("aria-pressed", "false");
    sexy.getBoundingClientRect = () =>
      ({
        x: 512,
        y: 153.6,
        left: 512,
        top: 153.6,
        width: 102.4,
        height: 76.8,
        right: 614.4,
        bottom: 230.4,
        toJSON: () => ({}),
      }) as DOMRect;
    controls.append(clean, sexy);

    syncPillDemoControlsActive(controls, "clean");
    expect(stage.dataset.activeTone).toBe("clean");
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("5.00%");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("5.00%");

    syncPillDemoControlsHover(controls, "sexy", sexy);
    expect(stage.dataset.hoverTone).toBe("sexy");
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("55.00%");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("25.00%");

    syncPillDemoControlsHover(controls, null);
    expect(stage.dataset.hoverTone).toBeUndefined();
    expect(stage.dataset.activeTone).toBe("clean");
    expect(stage.style.getPropertyValue("--stage-pad-x")).toBe("5.00%");
    expect(stage.style.getPropertyValue("--stage-pad-y")).toBe("5.00%");
    stage.remove();
  });
});

describe("syncPillDemoShortcutPadAim — keyboard pad tactility", () => {
  it("centers the pad light before a number-key reaction fires", () => {
    const controls = document.createElement("div");
    const button = document.createElement("button");
    button.dataset.demoTone = "bomb";
    button.getBoundingClientRect = () =>
      ({
        x: 200,
        y: 80,
        left: 200,
        top: 80,
        width: 80,
        height: 40,
        right: 280,
        bottom: 120,
        toJSON: () => ({}),
      }) as DOMRect;
    controls.append(button);

    expect(syncPillDemoShortcutPadAim(controls, "bomb")).toBe(true);
    expect(button.style.getPropertyValue("--pad-x")).toBe("50%");
    expect(button.style.getPropertyValue("--pad-y")).toBe("50%");
    expect(button.style.getPropertyValue("--pad-tilt-x")).toBe("0");
    expect(button.style.getPropertyValue("--pad-tilt-y")).toBe("0");
    expect(syncPillDemoShortcutPadAim(controls, "sexy")).toBe(false);
  });
});

describe("pillDemoControlsHandleShortcutKey — real number-key trigger path", () => {
  it("aims the pad, prevents default, and clicks the matching reaction button", () => {
    const controls = document.createElement("div");
    const button = document.createElement("button");
    let clicks = 0;
    button.dataset.demoTone = "bomb";
    button.addEventListener("click", () => {
      clicks += 1;
    });
    button.getBoundingClientRect = () =>
      ({
        x: 200,
        y: 80,
        left: 200,
        top: 80,
        width: 80,
        height: 40,
        right: 280,
        bottom: 120,
        toJSON: () => ({}),
      }) as DOMRect;
    controls.append(button);

    const ev = new KeyboardEvent("keydown", { key: "4", cancelable: true });
    expect(pillDemoControlsHandleShortcutKey(controls, ev)).toBe(true);
    expect(ev.defaultPrevented).toBe(true);
    expect(clicks).toBe(1);
    expect(button.style.getPropertyValue("--pad-x")).toBe("50%");
    expect(button.style.getPropertyValue("--pad-y")).toBe("50%");
  });

  it("ignores modified keys, hidden controls, and editable targets", () => {
    const controls = document.createElement("div");
    const button = document.createElement("button");
    let clicks = 0;
    button.dataset.demoTone = "bomb";
    button.addEventListener("click", () => {
      clicks += 1;
    });
    controls.append(button);

    expect(
      pillDemoControlsHandleShortcutKey(
        controls,
        new KeyboardEvent("keydown", { key: "4", altKey: true, cancelable: true }),
      ),
    ).toBe(false);

    controls.setAttribute("aria-hidden", "true");
    expect(
      pillDemoControlsHandleShortcutKey(
        controls,
        new KeyboardEvent("keydown", { key: "4", cancelable: true }),
      ),
    ).toBe(false);
    controls.setAttribute("aria-hidden", "false");

    const input = document.createElement("input");
    let handled = true;
    input.addEventListener("keydown", (ev) => {
      handled = pillDemoControlsHandleShortcutKey(controls, ev);
    });
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "4", bubbles: true }));

    expect(handled).toBe(false);
    expect(clicks).toBe(0);
  });
});

describe("syncPillDemoPadPointer — hot-cue magnetic highlight", () => {
  it("maps pointer position into clamped CSS vars and clears them on leave", () => {
    const button = document.createElement("button");
    button.getBoundingClientRect = () =>
      ({
        x: 10,
        y: 20,
        left: 10,
        top: 20,
        width: 100,
        height: 50,
        right: 110,
        bottom: 70,
        toJSON: () => ({}),
      }) as DOMRect;

    syncPillDemoPadPointer(button, 35, 45);
    expect(button.style.getPropertyValue("--pad-x")).toBe("25%");
    expect(button.style.getPropertyValue("--pad-y")).toBe("50%");
    expect(button.style.getPropertyValue("--pad-tilt-x")).toBe("-1.75");
    expect(button.style.getPropertyValue("--pad-tilt-y")).toBe("0");

    syncPillDemoPadPointer(button, -50, 1000);
    expect(button.style.getPropertyValue("--pad-x")).toBe("0%");
    expect(button.style.getPropertyValue("--pad-y")).toBe("100%");
    expect(button.style.getPropertyValue("--pad-tilt-x")).toBe("-3.5");
    expect(button.style.getPropertyValue("--pad-tilt-y")).toBe("2.5");

    resetPillDemoPadPointer(button);
    expect(button.style.getPropertyValue("--pad-x")).toBe("");
    expect(button.style.getPropertyValue("--pad-y")).toBe("");
    expect(button.style.getPropertyValue("--pad-tilt-x")).toBe("");
    expect(button.style.getPropertyValue("--pad-tilt-y")).toBe("");
  });
});

describe("pillDemoShortcutTargetCanHandle — editable target discipline", () => {
  it("does not hijack number keys while typing into editable controls", () => {
    expect(pillDemoShortcutTargetCanHandle(null)).toBe(true);
    expect(pillDemoShortcutTargetCanHandle(document.createElement("button"))).toBe(true);
    expect(pillDemoShortcutTargetCanHandle(document.createElement("input"))).toBe(false);
    expect(pillDemoShortcutTargetCanHandle(document.createElement("textarea"))).toBe(false);
    expect(pillDemoShortcutTargetCanHandle(document.createElement("select"))).toBe(false);

    const editable = document.createElement("div");
    editable.contentEditable = "true";
    expect(pillDemoShortcutTargetCanHandle(editable)).toBe(false);

    const editableChild = document.createElement("span");
    editable.append(editableChild);
    expect(pillDemoShortcutTargetCanHandle(editableChild)).toBe(false);

    const readOnly = document.createElement("div");
    readOnly.contentEditable = "false";
    expect(pillDemoShortcutTargetCanHandle(readOnly)).toBe(true);
  });
});

describe("pillDebriefInvokeArgs — citation deep-link", () => {
  it("opens latest Debrief at the cited moment", () => {
    expect(
      pillDebriefInvokeArgs({
        event_id: "ev:KICK@7.5",
        verb: "kick",
        timestamp_s: 7.5,
      }),
    ).toEqual({
      sessionDir: "",
      deepLink: {
        eventId: "ev:KICK@7.5",
        timestampS: 7.5,
      },
    });
  });
});

describe("pillCitationChipsRenderKey — visible receipt memo key", () => {
  it("changes when the readable citation verb is corrected for the same event moment", () => {
    const base = [
      { event_id: "ev:KICK@7.5", verb: "kick", timestamp_s: 7.5 },
    ];
    expect(pillCitationChipsRenderKey(base)).not.toBe(
      pillCitationChipsRenderKey([
        { event_id: "ev:KICK@7.5", verb: "kick swap", timestamp_s: 7.5 },
      ]),
    );
  });
});

describe("pillReceiptRenderKey — reaction receipt replay key", () => {
  it("changes for a fresh reaction over the same cited moment", () => {
    const chips = [
      { event_id: "ev:DROP@64.0", verb: "drop", timestamp_s: 64 },
    ];
    expect(pillReceiptRenderKey(chips, "BOMB. Ride it.", T0 + 6000)).not.toBe(
      pillReceiptRenderKey(chips, "LIT AFF. Same moment, stronger call.", T0 + 6000),
    );
  });

  it("changes for repeated identical reaction copy when the live reaction revision changes", () => {
    const chips = [
      { event_id: "ev:DROP@64.0", verb: "drop", timestamp_s: 64 },
    ];
    expect(pillReceiptRenderKey(chips, "BOMB. Ride it.", T0 + 6000)).not.toBe(
      pillReceiptRenderKey(chips, "BOMB. Ride it.", T0 + 7000),
    );
  });
});

describe("pillWindowHeightForContent — overlay resize boundary", () => {
  it("clamps expand and peek content heights to the native window caps", () => {
    expect(pillWindowHeightForContent("expand", false, 999, 999)).toBe(292);
    expect(pillWindowHeightForContent("listening", true, 999, 999)).toBe(194);
    expect(pillWindowHeightForContent("idle", false, 999, 999)).toBe(44);
  });

  it("treats non-finite or negative DOM measurements as collapsed content", () => {
    expect(pillWindowHeightForContent("expand", false, Number.NaN, 80)).toBe(44);
    expect(pillWindowHeightForContent("speaking", true, 80, Number.POSITIVE_INFINITY)).toBe(44);
    expect(pillWindowHeightForContent("expand", false, -12, 80)).toBe(44);
  });
});

describe("pillWindowHeightRenderKey — expanded-body measurement memo", () => {
  it("changes for same-length reaction copy so different wrapping can resize", () => {
    const shortWords = "tight hook now";
    const longWord = "superlongword!";
    expect(shortWords).toHaveLength(longWord.length);

    const base = {
      mode: "expand" as const,
      peekOpen: false,
      chipsKey: "",
      deckKey: "",
      peekKey: "",
      nextKey: "",
    };

    expect(pillWindowHeightRenderKey({ ...base, reactionText: shortWords })).not.toBe(
      pillWindowHeightRenderKey({ ...base, reactionText: longWord }),
    );
  });

  it("changes when deck receipts inside the expanded pill change", () => {
    const base = {
      mode: "expand" as const,
      peekOpen: false,
      chipsKey: "",
      peekKey: "",
      nextKey: "",
      reactionText: "BOMB",
    };

    expect(pillWindowHeightRenderKey({ ...base, deckKey: "deck:a" })).not.toBe(
      pillWindowHeightRenderKey({ ...base, deckKey: "deck:b" }),
    );
  });

  it("ignores stale reaction copy while the pill is collapsed", () => {
    const base = {
      mode: "idle" as const,
      peekOpen: false,
      chipsKey: "",
      deckKey: "",
      peekKey: "",
      nextKey: "",
    };

    expect(pillWindowHeightRenderKey({ ...base, reactionText: "BOMB" })).toBe(
      pillWindowHeightRenderKey({ ...base, reactionText: "LIT AFF" }),
    );
  });
});

describe("pillOpenState — one body opening contract", () => {
  it("opens the visual body for expand or hover peek only", () => {
    expect(pillOpenState("expand", false)).toBe(true);
    expect(pillOpenState("listening", true)).toBe(true);
    expect(pillOpenState("speaking", false)).toBe(false);
    expect(pillOpenState("idle", false)).toBe(false);
  });
});

describe("pillHoverCanOpen — live face priority", () => {
  it("lets hover own idle/listening, but speaking and reactions keep the face state", () => {
    expect(pillHoverCanOpen("idle")).toBe(true);
    expect(pillHoverCanOpen("listening")).toBe(true);
    expect(pillHoverCanOpen("speaking")).toBe(false);
    expect(pillHoverCanOpen("expand")).toBe(false);
  });
});

describe("pillPeekCloseKey — keyboard exit from focused peek", () => {
  it("uses Escape as the explicit close gesture", () => {
    expect(pillPeekCloseKey("Escape")).toBe(true);
    expect(pillPeekCloseKey("Esc")).toBe(true);
    expect(pillPeekCloseKey("Enter")).toBe(false);
    expect(pillPeekCloseKey(" ")).toBe(false);
  });
});

describe("pillPeekHandleCloseKey — real Escape close contract", () => {
  it("prevents default only when a peek is open and Escape is pressed", () => {
    const close = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
    expect(pillPeekHandleCloseKey(true, close)).toBe(true);
    expect(close.defaultPrevented).toBe(true);

    const noPeek = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
    expect(pillPeekHandleCloseKey(false, noPeek)).toBe(false);
    expect(noPeek.defaultPrevented).toBe(false);

    const enter = new KeyboardEvent("keydown", { key: "Enter", cancelable: true });
    expect(pillPeekHandleCloseKey(true, enter)).toBe(false);
    expect(enter.defaultPrevented).toBe(false);
  });
});

describe("pillShouldExposePeekFocus — hidden drawer focus discipline", () => {
  it("exposes focus only while a grounded peek is visible", () => {
    expect(pillShouldExposePeekFocus(true, true)).toBe(true);
    expect(pillShouldExposePeekFocus(true, false)).toBe(false);
    expect(pillShouldExposePeekFocus(false, true)).toBe(false);
    expect(pillShouldExposePeekFocus(false, false)).toBe(false);
  });
});

describe("pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval — focus continuity", () => {
  it("returns focus only when rebuild/removal drops the focused suggestion surface", () => {
    const root = document.createElement("div");
    const row = document.createElement("div");
    const peek = document.createElement("div");
    const card = document.createElement("button");
    const next = document.createElement("div");
    const nextButton = document.createElement("button");
    const outside = document.createElement("button");
    peek.append(card);
    next.append(nextButton);
    root.append(row, peek, next);

    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(card, root, [next, peek]),
    ).toBe(true);
    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(nextButton, root, [next, peek]),
    ).toBe(true);
    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(row, root, [next, peek]),
    ).toBe(false);
    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(root, root, [next, peek]),
    ).toBe(false);
    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(outside, root, [next, peek]),
    ).toBe(false);
    expect(
      pillShouldReturnFocusToRootAfterSuggestionSurfaceRemoval(null, root, [next, peek]),
    ).toBe(false);
  });
});

describe("pillRootPrimaryActionAvailable — root action affordance", () => {
  it("is available only for an open grounded peek", () => {
    expect(pillRootPrimaryActionAvailable(true, true)).toBe(true);
    expect(pillRootPrimaryActionAvailable(true, false)).toBe(false);
    expect(pillRootPrimaryActionAvailable(false, true)).toBe(false);
  });
});

describe("syncPillRootActionability — aria shortcut affordance", () => {
  it("adds and removes the root primary-action keyboard hint", () => {
    const root = document.createElement("div");
    syncPillRootActionability(root, true);
    expect(root.dataset.actionable).toBe("true");
    expect(root.getAttribute("aria-keyshortcuts")).toBe("Enter Space");
    expect(root.getAttribute("aria-controls")).toBe("pill-peek");
    expect(root.getAttribute("aria-expanded")).toBe("true");

    syncPillRootActionability(root, false);
    expect(root.dataset.actionable).toBe("false");
    expect(root.hasAttribute("aria-keyshortcuts")).toBe(false);
    expect(root.hasAttribute("aria-controls")).toBe(false);
    expect(root.hasAttribute("aria-expanded")).toBe(false);
  });
});

describe("pillShouldExposeNextChrome — reaction ownership", () => {
  it("does not keep next-move chrome mounted while a cohost reaction owns the body", () => {
    expect(pillShouldExposeNextChrome("idle")).toBe(true);
    expect(pillShouldExposeNextChrome("listening")).toBe(true);
    expect(pillShouldExposeNextChrome("speaking")).toBe(true);
    expect(pillShouldExposeNextChrome("expand")).toBe(false);
  });
});

describe("pillShouldShowFaceWave — reaction face chrome ownership", () => {
  it("hides the idle waveform ladder only while a non-speaking reaction owns the pill", () => {
    expect(pillShouldShowFaceWave("expand", "IDLE")).toBe(false);
    expect(pillShouldShowFaceWave("expand", "LISTENING")).toBe(false);
    expect(pillShouldShowFaceWave("expand", "TALKING")).toBe(true);
    expect(pillShouldShowFaceWave("speaking", "TALKING")).toBe(true);
    expect(pillShouldShowFaceWave("idle", "IDLE")).toBe(true);
  });
});

describe("pillShouldSuppressNextFocusPeek — Escape/focus return guard", () => {
  it("suppresses only when focus returns from a child control to the root", () => {
    const root = document.createElement("div");
    const child = document.createElement("button");
    root.append(child);

    expect(pillShouldSuppressNextFocusPeek(root, child)).toBe(true);
    expect(pillShouldSuppressNextFocusPeek(root, root)).toBe(false);
    expect(pillShouldSuppressNextFocusPeek(root, document.createElement("button"))).toBe(false);
    expect(pillShouldSuppressNextFocusPeek(root, null)).toBe(false);
  });
});

describe("pillNextCompletionKey — local completion memory", () => {
  it("keys the handled task by stable suggestion identity, not render-only churn", () => {
    const base = {
      track_id: "t1",
      title: "Strobe",
      artist: "Deadmau5",
      similarity: 0.9,
      why: "similar vibe",
      camelot: "8A",
      bpm: 128,
      transition: {
        candidate_id: "tr_001",
        target_deck: "B",
        cue_slot: "A",
        start_in_bars: 8,
      },
    };

    expect(pillNextCompletionKey(base)).toBe(
      pillNextCompletionKey({
        ...base,
        why: "new wording from backend",
      }),
    );
    expect(pillNextCompletionKey(base)).not.toBe(
      pillNextCompletionKey({
        ...base,
        transition: { ...base.transition, start_in_bars: 4 },
      }),
    );
    expect(pillNextCompletionKey(null)).toBe("");
  });
});

describe("pillSuggestionIsHandled — completed next-card suppression", () => {
  const suggestion = {
    track_id: "demo:velvet-pressure",
    title: "Velvet Pressure",
    artist: "Mira Vale",
    similarity: 0.88,
    why: "same late-night pulse",
    camelot: "8A",
    bpm: 128,
    transition: {
      candidate_id: "demo:transition:velvet-pressure",
      target_deck: "B",
      cue_slot: "A",
      start_in_bars: 8,
      move_grade: { slug: "sexy", label: "SEXY", xp: 48 },
    },
  };

  it("suppresses the same handled suggestion by completion or render key", () => {
    expect(pillSuggestionIsHandled(suggestion, pillNextCompletionKey(suggestion), "")).toBe(
      true,
    );
    expect(pillSuggestionIsHandled(suggestion, "", nextSuggestionRenderKey(suggestion))).toBe(
      true,
    );
    expect(pillSuggestionIsHandled(suggestion, "", "")).toBe(false);
    expect(
      pillSuggestionIsHandled(
        { ...suggestion, transition: { ...suggestion.transition, start_in_bars: 4 } },
        pillNextCompletionKey(suggestion),
        nextSuggestionRenderKey(suggestion),
      ),
    ).toBe(false);
  });
});

describe("syncFocusableDescendants — hidden panel tab discipline", () => {
  it("makes hidden controls inert, then restores their original tab order", () => {
    const root = document.createElement("div");
    const button = document.createElement("button");
    const custom = document.createElement("button");
    custom.tabIndex = 3;
    root.append(button, custom);

    syncFocusableDescendants(root, false);
    expect(root.hasAttribute("inert")).toBe(true);
    expect(button.tabIndex).toBe(-1);
    expect(button.getAttribute("tabindex")).toBe("-1");
    expect(custom.tabIndex).toBe(-1);
    expect(custom.dataset.pillTabIndex).toBe("3");

    syncFocusableDescendants(root, false);
    expect(custom.dataset.pillTabIndex).toBe("3");

    syncFocusableDescendants(root, true);
    expect(root.hasAttribute("inert")).toBe(false);
    expect(button.getAttribute("tabindex")).toBeNull();
    expect(custom.tabIndex).toBe(3);
    expect(custom.getAttribute("tabindex")).toBe("3");
    expect(custom.dataset.pillTabIndex).toBeUndefined();
  });
});

describe("pillRenderLabel — honest hover copy", () => {
  it("says DJ KNOWS only when a grounded peek card is visible", () => {
    expect(pillRenderLabel("IDLE", true, true)).toBe("DJ KNOWS");
    expect(pillRenderLabel("IDLE", true, false)).toBe("IDLE");
    expect(pillRenderLabel("LISTENING", false, false)).toBe("LISTENING");
  });
});

describe("pillRootAriaLabel — focused pill action summary", () => {
  const suggestion: NextSuggestionWire = {
    track_id: "t1",
    title: "Velvet Pressure",
    artist: "Mira Vale",
    similarity: 0.88,
    why: "same late-night pulse",
    camelot: "9A",
    bpm: 126,
    transition: {
      target_deck: "B",
      start_in_bars: 8,
    },
  };

  it("describes the visible load action on the focused pill itself", () => {
    expect(
      pillRootAriaLabel({
        peekVisible: true,
        suggestion,
      }),
    ).toBe(
      [
        "vibemix cohost pill",
        "next: Velvet Pressure. action: load B · in 8 bars. activate to pin this next",
      ].join(". "),
    );
  });

  it("falls back to the base label when no grounded peek is visible", () => {
    expect(
      pillRootAriaLabel({
        peekVisible: false,
        suggestion,
      }),
    ).toBe("vibemix cohost pill");
    expect(
      pillRootAriaLabel({
        peekVisible: true,
        suggestion: null,
      }),
    ).toBe("vibemix cohost pill");
  });
});

describe("pillShouldClearHandledNextOnNull — demo fallback completion memory", () => {
  it("keeps handled fallback cards consumed in demo mode while production null clears", () => {
    expect(pillShouldClearHandledNextOnNull(false)).toBe(true);
    expect(pillShouldClearHandledNextOnNull(true)).toBe(false);
  });
});

describe("pillDemoNextEnabled — dev-only demo fallback", () => {
  it("keeps fabricated next suggestions out of production even when the env flag is set", () => {
    expect(pillDemoNextEnabled({ DEV: true, VITE_VIBEMIX_DEMO_NEXT: "1" })).toBe(true);
    expect(pillDemoNextEnabled({ DEV: false, VITE_VIBEMIX_DEMO_NEXT: "1" })).toBe(false);
    expect(pillDemoNextEnabled({ DEV: true, VITE_VIBEMIX_DEMO_NEXT: "0" })).toBe(false);
  });
});

describe("pillIntelState — one grounded live-intelligence state", () => {
  it("prioritizes reaction, then speaking, knowing, listening, then idle", () => {
    expect(
      pillIntelState({ mode: "idle", hasNext: false, peekVisible: false }),
    ).toBe("idle");
    expect(
      pillIntelState({ mode: "listening", hasNext: true, peekVisible: false }),
    ).toBe("knows");
    expect(
      pillIntelState({ mode: "idle", hasNext: false, hovered: true, peekVisible: false }),
    ).toBe("idle");
    expect(
      pillIntelState({ mode: "idle", hasNext: false, hovered: true, peekVisible: true }),
    ).toBe("knows");
    expect(
      pillIntelState({ mode: "speaking", hasNext: true, hovered: true, peekVisible: true }),
    ).toBe("speaking");
    expect(
      pillIntelState({ mode: "listening", hasNext: false, peekVisible: false }),
    ).toBe("listening");
  });

  it("lets an open cohost reaction own the face over next-suggestion mood", () => {
    expect(
      pillIntelState({ mode: "expand", hasNext: true, peekVisible: false }),
    ).toBe("reaction");
  });
});

describe("reduceFrame — cohost-reaction (WRITER → expand)", () => {
  it("a cohost-reaction drives expand with the VERBATIM text", () => {
    const s = reduceFrame(
      initialPillState(T0),
      {
        type: "cohost-reaction",
        cohost_status: "TALKING",
        voice: 0.62,
        text: "kick swap on the 1",
        citation_strip: [],
      },
      T0 + 5,
    );
    expect(s.mode).toBe("expand");
    expect(s.cohostStatus).toBe("TALKING");
    expect(s.voiceRms).toBe(0.62);
    expect(s.reactionText).toBe("kick swap on the 1");
  });

  it("accepts the ipc.session.cohost-reaction alias", () => {
    const s = reduceFrame(
      initialPillState(T0),
      {
        type: "ipc.session.cohost-reaction",
        payload: { text: "tight", event_id: "HEARTBEAT", citation_strip: [] },
      },
      T0 + 5,
    );
    expect(s.mode).toBe("expand");
    expect(s.reactionText).toBe("tight");
  });

  it("never adds framing — reaction text is the wire string as-is", () => {
    const raw = "no AI: prefix, no marketing voice";
    const s = reduceFrame(initialPillState(T0), { type: "cohost-reaction", text: raw }, T0 + 5);
    expect(s.reactionText).toBe(raw);
  });
});
