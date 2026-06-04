/* DEMOCRATIZATION-1 — Settings drawer BRAIN group.
 *
 * The single most consequential setting for a blocked stranger: which brain
 * the live co-host talks to. Today a non-dev with no GEMINI_API_KEY hits a
 * terminal "edit ~/Library/.../vibemix/.env then restart" wall (crash-banner
 * `api-key-missing`). This group gives them a way in WITHOUT touching .env:
 *
 *   - DIRECT — paste your own Gemini key (masked). The key is written by the
 *     BACKEND (Lane B) to app_data_dir()/.env or the keychain. It is never
 *     echoed back, never logged, never committed.
 *   - PROXY — one flip to Bravoh's hosted brain (install-UUID → JWT register).
 *
 * Both persist through ipc.settings.set_brain → ConfigStore.llm_mode; the boot
 * path reads the choice on the next sidecar restart. The ack (brain_ack)
 * carries NO secret — only a coarse key_set boolean.
 *
 * Brain mode is held module-local (the cheap §3.4 fallback): there is no
 * SettingsView.llm_mode field yet, so a cold drawer shows DIRECT until the
 * first toggle. The mode survives mid-session drawer rebuilds (module state),
 * and the brain_ack echo is authoritative.
 *
 * Optimistic repaint (tauri/ui/CLAUDE.md convention): renderRocker flips the
 * lit segment locally before the round-trip; the ~3ms ack self-corrects (on
 * ok:false the mode reverts and the state line shows the reason).
 */

import { vmxLog } from "../../debug-log.js";
import type { SettingsBrainAck } from "../../ipc/messages.js";
import { sendIpcRequest } from "../../ipc/client.js";
import { registerStyle } from "../../session/components/_style-registry.js";
import { renderRocker, setRockerActive } from "../../session/components/rocker.js";
import { invokeTauri } from "../../tauri-runtime.js";
import { renderSettingsGroup } from "./group.js";

type BrainMode = "direct" | "proxy";

// Module-local current mode (the §3.4 local fallback — no llm_mode round-trip
// yet). Survives drawer rebuilds; reset between tests via the hook below.
let _brainMode: BrainMode = "direct";

/** Test hook — restore the cold-boot default so module state never leaks
 *  across specs (mirrors `_resetSessionStateForTests`). */
export function _resetBrainGroupForTests(): void {
  _brainMode = "direct";
}

const CSS = `
  [data-component="brain-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    font-family: var(--type-body);
  }
  [data-component="brain-group"] .vmx-brain__label {
    display: block;
    font-family: var(--type-display);
    font-variation-settings: "wght" 600;
    font-size: 10.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-65);
    line-height: 1;
    margin-bottom: var(--sp-2);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  [data-component="brain-group"] .vmx-brain__note {
    font-family: var(--type-body);
    font-size: 11px;
    line-height: 1.4;
    color: var(--text-muted);
    margin-top: 6px;
  }
  [data-component="brain-group"] .vmx-brain__keyrow {
    display: flex;
    gap: var(--sp-2);
    align-items: stretch;
  }
  /* Masked key field — glass-3 recess, hairline, 2px rose focus ring
     (DESIGN.md §7 Inputs). The field is WRITE-ONLY: never seeded from any
     inbound state, cleared after a good ack. */
  [data-component="brain-group"] .vmx-brain__key {
    flex: 1;
    min-width: 0;
    font-family: var(--type-mono);
    font-size: 12px;
    letter-spacing: 0.04em;
    padding: 9px var(--sp-3);
    color: var(--text-secondary);
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.55),
      inset 0 -1px 0 rgba(255, 255, 255, 0.024);
    transition: border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  [data-component="brain-group"] .vmx-brain__key::placeholder {
    color: var(--text-disabled);
  }
  [data-component="brain-group"] .vmx-brain__key:focus-visible {
    outline: none;
    border-color: var(--brand-40);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.55),
      0 0 0 2px var(--brand-22),
      var(--glow-soft);
  }
  /* Save — the rose primary recipe, recessive until the field has a key. */
  [data-component="brain-group"] .vmx-brain__save {
    font-family: var(--type-display);
    font-variation-settings: "wght" 600;
    font-size: 10.5px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 0 var(--sp-4);
    color: var(--brand);
    background: linear-gradient(180deg, rgba(255, 165, 223, 0.10) 0%, rgba(255, 165, 223, 0.03) 100%);
    border: 1px solid var(--brand-40);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    white-space: nowrap;
    text-shadow: 0 0 4px var(--brand-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 0 10px var(--brand-12);
    transition: color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                opacity var(--motion-snap) ease-out;
  }
  [data-component="brain-group"] .vmx-brain__save:hover:not(:disabled) {
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.09),
      inset 0 0 14px var(--brand-22),
      0 0 10px var(--brand-12);
  }
  [data-component="brain-group"] .vmx-brain__save:disabled {
    color: var(--silk-65);
    background: var(--glass-3);
    border-color: var(--glass-edge);
    text-shadow: none;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    opacity: 0.4;
    cursor: not-allowed;
  }
  /* State line — one honest mono readout. Neutral by default; ok after a
     save; fault carries the backend's verbatim reason. */
  [data-component="brain-group"] .vmx-brain__state {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    min-height: 14px;
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.35;
    color: var(--text-muted);
  }
  [data-component="brain-group"] .vmx-brain__state[data-kind="ok"] { color: var(--text-secondary); }
  [data-component="brain-group"] .vmx-brain__state[data-kind="fault"] {
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.18);
  }
  [data-component="brain-group"] .vmx-brain__restart {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 4px var(--sp-3);
    color: var(--brand);
    background: transparent;
    border: 1px solid var(--brand-22);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
  }
  [data-component="brain-group"] .vmx-brain__restart:hover {
    background: var(--brand-08);
    box-shadow: 0 0 8px var(--brand-12);
  }
`;

registerStyle("vmx-brain-group", CSS);

const MODE_NOTE: Record<BrainMode, string> = {
  direct: "I use your own Gemini key. It stays on this device.",
  proxy: "I run on Bravoh's hosted brain. No key needed.",
};

export function BrainGroup(): HTMLElement {
  const body = document.createElement("div");
  body.setAttribute("data-component", "brain-group");

  // --- mode rocker ---------------------------------------------------------
  const modeWrap = document.createElement("div");
  modeWrap.dataset.wire = "settings.brain.mode";
  const modeLabel = document.createElement("span");
  modeLabel.className = "vmx-brain__label";
  modeLabel.textContent = "CO-HOST BRAIN";
  modeWrap.append(modeLabel);
  const rocker = renderRocker({
    ariaLabel: "brain path",
    options: [
      { id: "direct", label: "DIRECT" },
      { id: "proxy", label: "PROXY" },
    ],
    active: _brainMode,
    variant: "rocker",
    onChange: (id) => onModeChange(id as BrainMode),
  });
  modeWrap.append(rocker);
  const modeNote = document.createElement("p");
  modeNote.className = "vmx-brain__note";
  modeNote.textContent = MODE_NOTE[_brainMode];
  modeWrap.append(modeNote);
  body.append(modeWrap);

  // --- direct-only section (key + save), rebuilt on mode change ------------
  const directWrap = document.createElement("div");
  directWrap.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-4);";
  body.append(directWrap);

  // --- state line ----------------------------------------------------------
  const stateLine = document.createElement("div");
  stateLine.className = "vmx-brain__state";
  stateLine.dataset.wire = "settings.brain.state";
  stateLine.dataset.kind = "neutral";
  body.append(stateLine);

  let keyInput: HTMLInputElement | null = null;
  let saveBtn: HTMLButtonElement | null = null;

  function setState(kind: "neutral" | "ok" | "fault", text: string, withRestart = false): void {
    stateLine.replaceChildren();
    stateLine.dataset.kind = kind;
    const msg = document.createElement("span");
    msg.textContent = text;
    stateLine.append(msg);
    if (withRestart) {
      const restart = document.createElement("button");
      restart.type = "button";
      restart.className = "vmx-brain__restart";
      restart.textContent = "Restart now";
      restart.addEventListener("click", (e) => {
        e.preventDefault();
        // Boot re-reads ConfigStore.llm_mode + the dotenv key on restart;
        // there is no mid-session brain hot-swap.
        void invokeTauri("restart_sidecar").catch((err) => {
          setState("fault", "Could not restart. Quit and reopen vibemix.");
          vmxLog("[vmx:error]", "restart_sidecar failed", { err: String(err) });
        });
      });
      stateLine.append(restart);
    }
  }

  function buildDirectSection(): void {
    directWrap.replaceChildren();
    keyInput = null;
    saveBtn = null;
    if (_brainMode !== "direct") return;

    const keyWrap = document.createElement("div");
    keyWrap.dataset.wire = "settings.brain.key";
    const keyLabel = document.createElement("span");
    keyLabel.className = "vmx-brain__label";
    keyLabel.textContent = "Gemini key";
    keyWrap.append(keyLabel);

    const row = document.createElement("div");
    row.className = "vmx-brain__keyrow";
    const input = document.createElement("input");
    input.type = "password";
    input.className = "vmx-brain__key";
    input.placeholder = "AIza…";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-label", "Gemini API key");
    row.append(input);

    const save = document.createElement("button");
    save.type = "button";
    save.className = "vmx-brain__save";
    save.dataset.wire = "settings.brain.save";
    save.textContent = "Save key";
    save.disabled = true;
    row.append(save);
    keyWrap.append(row);

    const note = document.createElement("p");
    note.className = "vmx-brain__note";
    note.textContent = "Paste a Gemini key, then restart to start the co-host.";
    keyWrap.append(note);

    input.addEventListener("input", () => {
      save.disabled = input.value.trim().length === 0;
    });
    save.addEventListener("click", (e) => {
      e.preventDefault();
      const key = input.value.trim();
      if (!key) return;
      save.disabled = true;
      save.textContent = "Saving…";
      void persist(
        { mode: "direct", gemini_api_key: key },
        {
          onDone: () => {
            save.textContent = "Save key";
            save.disabled = input.value.trim().length === 0;
          },
          clearInput: true,
        },
      );
    });

    keyInput = input;
    saveBtn = save;
    directWrap.append(keyWrap);
  }

  function onModeChange(next: BrainMode): void {
    const prev = _brainMode;
    if (next === prev) return;
    // Optimistic — renderRocker already flipped the lit segment. Reflect the
    // structural change (show/hide the key field) immediately too.
    _brainMode = next;
    modeNote.textContent = MODE_NOTE[next];
    buildDirectSection();
    setState("neutral", "");
    // A bare mode flip keeps any existing key (gemini_api_key omitted).
    void persist({ mode: next }, { revertTo: prev });
  }

  function revertMode(to: BrainMode): void {
    _brainMode = to;
    setRockerActive(rocker, to);
    modeNote.textContent = MODE_NOTE[to];
    buildDirectSection();
  }

  async function persist(
    payload: { mode: BrainMode; gemini_api_key?: string },
    opts: { revertTo?: BrainMode; clearInput?: boolean; onDone?: () => void } = {},
  ): Promise<void> {
    let ack: SettingsBrainAck;
    try {
      ack = await sendIpcRequest<SettingsBrainAck>(
        "ipc.settings.set_brain",
        payload,
        "ipc.settings.brain_ack",
      );
    } catch (err) {
      vmxLog("[vmx:error]", "set_brain failed", { err: String(err), mode: payload.mode });
      setState("fault", "Could not reach the sidecar. Try again.");
      if (opts.revertTo) revertMode(opts.revertTo);
      opts.onDone?.();
      return;
    }
    const result = ack.payload;
    if (!result.ok) {
      setState("fault", result.error ?? "That did not save. Try again.");
      if (opts.revertTo) revertMode(opts.revertTo);
      opts.onDone?.();
      return;
    }
    if (opts.clearInput && keyInput) keyInput.value = "";
    setState(
      "ok",
      result.restart_required ? "Saved. Restart to apply." : "Saved.",
      result.restart_required,
    );
    opts.onDone?.();
  }

  buildDirectSection();

  const group = renderSettingsGroup({
    header: "BRAIN",
    badge: "MODEL",
    children: body,
  });
  group.setAttribute("data-component", "brain-group");
  return group;
}
