// SPDX-License-Identifier: Apache-2.0
//
// Wreck Room — the Learn front door. One button, two decks, Sven in your ear.
//
// The shape of the game lives in the Python round director
// (vibemix/learn/wreck_round.py): groove locked, Sven shoves deck B, a save
// window counts down, you drag the pitch fader and jog until the kicks fuse.
// This surface only renders measured truth: every number on screen rides the
// existing ipc.learn.* wire (live_grade save fields, waveform_ready,
// playhead_tick, tutor_speak) and every control ride is the existing
// ipc.learn.ack envelope. Zero new IPC types.
//
// Honesty rules baked in:
//   - no autoplay: audio starts only from the one button, and a refused start
//     surfaces as an authored line, never a dead button (idle is not a fault)
//   - streak/difficulty are NEVER number chips; they reach the user as plain
//     receipt words or Sven's speech (the anti-gamification law)
//   - the save countdown is the single breathing element while a window is
//     open (One-Rose)

import "./booth.css";

import { emitIpc } from "../../ipc/client.js";
import { LearnWsClient } from "../ws-client.js";
import { LiveGradeMeter, type LiveGradePayload } from "../live-meter.js";
import {
  WaveformDisplay,
  type PlayheadTickPayload,
  type WaveformReadyPayload,
} from "../waveform-display.js";
import { startAnalogControlDrag } from "../drag-control.js";

const CENTER_CC = 64;
const TEMPO_CC_RATE_SPAN = 640;
const FADER_TRAVEL_PX = 132;
const AUDIO_WATCHDOG_MS = 2500;

const IDLE_SVEN_LINE =
  "two decks are waiting. drop the needle and I will wreck the mix. you save it.";
const IDLE_HINT = "headphones on. laptop speakers hide the kicks.";
const NO_AUDIO_HINT =
  "the decks did not start. check your sound output, then drop the needle again.";

export interface WreckBoothDeps {
  /** Skip the ws client in jsdom tests; window events still drive the UI. */
  connectWs?: boolean;
}

export interface WreckBoothHandle {
  root: HTMLElement;
  teardown(): void;
}

type AckPayload = {
  control_id: string;
  source: "click";
  value?: number;
  prev_value?: number;
  direction?: "" | "up" | "down";
};

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function saveWords(payload: LiveGradePayload): string {
  const streak = Math.max(0, Math.round(payload.save_streak ?? 0));
  if (payload.save_landed) {
    return streak === 1
      ? "first clean save."
      : `${streak} clean saves in a row.`;
  }
  if (payload.save_floor_expired) {
    return "the window closed. next groove is coming.";
  }
  if (payload.save_attempt_active) {
    const remaining = payload.save_floor_seconds_remaining;
    if (typeof remaining === "number" && Number.isFinite(remaining)) {
      return `save it. ${remaining.toFixed(1)} seconds.`;
    }
    return "save it.";
  }
  if (streak > 0) {
    return `${streak} clean ${streak === 1 ? "save" : "saves"} so far.`;
  }
  return "";
}

export function mountWreckBooth(
  mount: HTMLElement,
  deps: WreckBoothDeps = {},
): WreckBoothHandle {
  mount.replaceChildren();

  const root = document.createElement("section");
  root.className = "wreck-booth";
  root.dataset.round = "idle";
  root.setAttribute("aria-label", "wreck room practice booth");

  // ---- Sven line (the co-host speaking on this surface) ----
  const sven = document.createElement("p");
  sven.className = "wreck-booth__sven";
  sven.setAttribute("aria-live", "polite");
  sven.textContent = IDLE_SVEN_LINE;

  // ---- waveforms ----
  const waves = document.createElement("div");
  waves.className = "wreck-booth__waves";

  // ---- meter + controls row ----
  const row = document.createElement("div");
  row.className = "wreck-booth__row";

  const meterHost = document.createElement("div");
  meterHost.className = "wreck-booth__meter";

  const controls = document.createElement("div");
  controls.className = "wreck-booth__controls";
  controls.innerHTML = `
    <svg viewBox="0 0 220 170" role="group" aria-label="deck B controls">
      <g class="wreck-booth__fader" data-control="tempo:B" tabindex="0"
         role="slider" aria-label="deck B pitch fader"
         aria-valuemin="0" aria-valuemax="127" aria-valuenow="${CENTER_CC}">
        <rect class="wreck-booth__fader-track" x="34" y="14" width="6" height="${FADER_TRAVEL_PX}" rx="3"></rect>
        <line class="wreck-booth__fader-center" x1="24" x2="50" y1="${14 + FADER_TRAVEL_PX / 2}" y2="${14 + FADER_TRAVEL_PX / 2}"></line>
        <rect class="wreck-booth__fader-cap" x="20" y="${14 + FADER_TRAVEL_PX / 2 - 9}" width="34" height="18" rx="4"></rect>
      </g>
      <g class="wreck-booth__jog" data-control="jog:B" data-cx="146" data-cy="80" tabindex="0"
         role="slider" aria-label="deck B jog wheel"
         aria-valuemin="0" aria-valuemax="127" aria-valuenow="${CENTER_CC}">
        <circle class="wreck-booth__jog-body" cx="146" cy="80" r="54"></circle>
        <circle class="wreck-booth__jog-inner" cx="146" cy="80" r="34"></circle>
        <line class="wreck-booth__jog-marker" x1="146" y1="32" x2="146" y2="48"></line>
      </g>
      <text class="wreck-booth__control-label" x="37" y="166">pitch</text>
      <text class="wreck-booth__control-label" x="146" y="166">jog</text>
    </svg>
  `;

  // ---- actions + receipt ----
  const actions = document.createElement("div");
  actions.className = "wreck-booth__actions";
  const go = document.createElement("button");
  go.type = "button";
  go.className = "wreck-booth__go";
  go.textContent = "drop the needle";
  const receipt = document.createElement("p");
  receipt.className = "wreck-booth__receipt";
  receipt.textContent = IDLE_HINT;
  actions.append(go, receipt);

  row.append(meterHost, controls);
  root.append(sven, waves, row, actions);
  mount.append(root);

  // ---- wire plumbing -------------------------------------------------------
  let ws: LearnWsClient | null = null;
  if (deps.connectWs !== false) {
    ws = new LearnWsClient();
    ws.connect();
  }

  const emitLearnIpc = (type: string, payload: AckPayload): void => {
    void (async () => {
      try {
        await emitIpc(type, payload as unknown as Record<string, unknown>);
      } catch {
        ws?.sendIpc(type, payload as unknown as Record<string, unknown>);
      }
    })();
  };

  const waveform = WaveformDisplay(waves);
  const meter = LiveGradeMeter(meterHost);

  let running = false;
  let audioSeen = false;
  let watchdog: number | null = null;

  const setRunning = (next: boolean): void => {
    running = next;
    go.textContent = next ? "lift the needle" : "drop the needle";
    if (!next) {
      root.dataset.round = "idle";
      meter.reset();
    }
  };

  const armAudioWatchdog = (): void => {
    if (watchdog !== null) window.clearTimeout(watchdog);
    watchdog = window.setTimeout(() => {
      watchdog = null;
      if (!audioSeen && running) {
        receipt.textContent = NO_AUDIO_HINT;
        setRunning(false);
      }
    }, AUDIO_WATCHDOG_MS);
  };

  go.addEventListener("click", () => {
    if (running) {
      emitLearnIpc("ipc.learn.ack", {
        control_id: "wreck_stop",
        source: "click",
        value: 0,
        direction: "down",
      });
      setRunning(false);
      receipt.textContent = IDLE_HINT;
      return;
    }
    audioSeen = false;
    setRunning(true);
    receipt.textContent = IDLE_HINT;
    emitLearnIpc("ipc.learn.ack", {
      control_id: "wreck_round",
      source: "click",
      value: 127,
      direction: "down",
    });
    armAudioWatchdog();
  });

  // ---- on-screen deck B controls -------------------------------------------
  const faderGroup = controls.querySelector<SVGGElement>(".wreck-booth__fader");
  const jogGroup = controls.querySelector<SVGGElement>(".wreck-booth__jog");
  const faderCap = controls.querySelector<SVGRectElement>(".wreck-booth__fader-cap");
  const jogMarker = controls.querySelector<SVGLineElement>(".wreck-booth__jog-marker");

  let faderValue = CENTER_CC;
  let jogValue = CENTER_CC;
  let faderDragging = false;

  const paintFader = (value: number): void => {
    faderValue = clamp(Math.round(value), 0, 127);
    if (faderCap) {
      const y = 14 + (1 - faderValue / 127) * FADER_TRAVEL_PX - 9;
      faderCap.setAttribute("y", y.toFixed(1));
    }
    faderGroup?.setAttribute("aria-valuenow", String(faderValue));
  };

  const paintJog = (value: number): void => {
    jogValue = clamp(Math.round(value), 0, 127);
    if (jogMarker) {
      const angle = (jogValue - CENTER_CC) * 2.4;
      jogMarker.setAttribute("transform", `rotate(${angle.toFixed(1)} 146 80)`);
    }
    jogGroup?.setAttribute("aria-valuenow", String(jogValue));
  };

  const sendControlFrame = (
    controlId: string,
    value: number,
    prevValue: number,
    direction: "" | "up" | "down",
  ): void => {
    emitLearnIpc("ipc.learn.ack", {
      control_id: controlId,
      source: "click",
      value,
      prev_value: prevValue,
      direction,
    });
  };

  const onFaderDown = (event: PointerEvent): void => {
    if (!faderGroup) return;
    faderDragging = true;
    startAnalogControlDrag({
      event,
      group: faderGroup,
      controlId: "tempo:B",
      ackControlId: "tempo:B",
      visualControlId: "tempo:B",
      initialValue: faderValue,
      apply: (positions) => {
        const next = positions["tempo:B"];
        if (typeof next === "number") paintFader(next);
      },
      emit: (frame) => {
        sendControlFrame(frame.controlId, frame.value, frame.prevValue, frame.direction);
      },
    });
    const release = (): void => {
      faderDragging = false;
      window.removeEventListener("pointerup", release, true);
      window.removeEventListener("pointercancel", release, true);
    };
    window.addEventListener("pointerup", release, true);
    window.addEventListener("pointercancel", release, true);
  };

  const onJogDown = (event: PointerEvent): void => {
    if (!jogGroup) return;
    startAnalogControlDrag({
      event,
      group: jogGroup,
      controlId: "jog:B",
      ackControlId: "jog:B",
      visualControlId: "jog:B",
      initialValue: jogValue,
      apply: (positions) => {
        const next = positions["jog:B"];
        if (typeof next === "number") paintJog(next);
      },
      emit: (frame) => {
        sendControlFrame(frame.controlId, frame.value, frame.prevValue, frame.direction);
      },
    });
    const recenter = (): void => {
      // A released jog has no absolute position; recenter so the next nudge
      // has full travel both ways (the wire only ever carries deltas).
      paintJog(CENTER_CC);
      window.removeEventListener("pointerup", recenter, true);
      window.removeEventListener("pointercancel", recenter, true);
    };
    window.addEventListener("pointerup", recenter, true);
    window.addEventListener("pointercancel", recenter, true);
  };

  faderGroup?.addEventListener("pointerdown", onFaderDown);
  jogGroup?.addEventListener("pointerdown", onJogDown);

  // ---- inbound wire ----------------------------------------------------------
  const onWaveformReady = (ev: Event): void => {
    const payload = (ev as CustomEvent<WaveformReadyPayload>).detail;
    if (!payload) return;
    audioSeen = true;
    waveform.updateWaveforms(payload);
    if (running) root.dataset.round = "groove";
  };

  const onPlayheadTick = (ev: Event): void => {
    const payload = (ev as CustomEvent<PlayheadTickPayload>).detail;
    if (!payload) return;
    audioSeen = true;
    waveform.updatePlayhead(payload);
    // Honest fader: when Sven shoves deck B's tempo the cap jumps with it, so
    // the learner drags a control that tells the truth about the deck.
    if (!faderDragging) {
      const a = payload.decks.A?.bpm;
      const b = payload.decks.B?.bpm;
      if (
        typeof a === "number" &&
        typeof b === "number" &&
        Number.isFinite(a) &&
        Number.isFinite(b) &&
        a > 0
      ) {
        paintFader(CENTER_CC + (b / a - 1) * TEMPO_CC_RATE_SPAN);
      }
    }
  };

  const onLiveGrade = (ev: Event): void => {
    const payload = (ev as CustomEvent<LiveGradePayload>).detail;
    if (!payload) return;
    audioSeen = true;
    if (!running) setRunning(true);
    meter.update(payload);
    waveform.updateGrade({
      verdict: payload.verdict,
      phase_error_beats: payload.phase_error_beats,
      save_landed: payload.save_landed,
    });
    if (payload.save_attempt_active) {
      root.dataset.round = "hunt";
    } else if (payload.save_landed) {
      root.dataset.round = "landed";
    } else if (payload.save_floor_expired) {
      root.dataset.round = "missed";
    } else {
      root.dataset.round = "groove";
    }
    const words = saveWords(payload);
    if (words) receipt.textContent = words;
  };

  const onTutorSpeak = (ev: Event): void => {
    const detail = (
      ev as CustomEvent<{ text?: string; tts_marker?: string }>
    ).detail;
    if (typeof detail?.text === "string" && detail.text.trim()) {
      sven.textContent = detail.text.trim();
    }
    const marker = typeof detail?.tts_marker === "string" ? detail.tts_marker : "";
    if (
      marker.startsWith("wreck_round.busy") ||
      marker.startsWith("wreck_round.no_deck")
    ) {
      // The backend refused the round and said why in Sven's own voice; the
      // local audio watchdog must not overrule that with a device diagnosis.
      if (watchdog !== null) {
        window.clearTimeout(watchdog);
        watchdog = null;
      }
      setRunning(false);
      receipt.textContent = IDLE_HINT;
    }
  };

  window.addEventListener("ipc.learn.waveform_ready", onWaveformReady);
  window.addEventListener("ipc.learn.playhead_tick", onPlayheadTick);
  window.addEventListener("ipc.learn.live_grade", onLiveGrade);
  window.addEventListener("ipc.learn.tutor_speak", onTutorSpeak);

  paintFader(CENTER_CC);
  paintJog(CENTER_CC);

  return {
    root,
    teardown(): void {
      if (watchdog !== null) window.clearTimeout(watchdog);
      if (running) {
        emitLearnIpc("ipc.learn.ack", {
          control_id: "wreck_stop",
          source: "click",
          value: 0,
          direction: "down",
        });
      }
      window.removeEventListener("ipc.learn.waveform_ready", onWaveformReady);
      window.removeEventListener("ipc.learn.playhead_tick", onPlayheadTick);
      window.removeEventListener("ipc.learn.live_grade", onLiveGrade);
      window.removeEventListener("ipc.learn.tutor_speak", onTutorSpeak);
      faderGroup?.removeEventListener("pointerdown", onFaderDown);
      jogGroup?.removeEventListener("pointerdown", onJogDown);
      meter.dispose();
      waveform.dispose();
      ws?.close();
      mount.replaceChildren();
    },
  };
}
