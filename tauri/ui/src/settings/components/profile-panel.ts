/* profile-panel.ts — Phase 32 / PROFILE-07.
 *
 * Settings → Profile panel. Three render states:
 *
 *   1. consent OFF              → empty state + "ENABLE" affordance.
 *   2. consent ON, no profile   → "no profile yet — vibemix learns after
 *                                 your next session" + regenerate button
 *                                 (which will most likely return
 *                                 insufficient_evidence on first try).
 *   3. consent ON + profile     → key:value pairs + regenerate / delete.
 *
 * IPC contract (Plan 32-05 + 32-06):
 *   outbound: ipc.profile.view              → ipc.profile.view_result
 *   outbound: ipc.profile.regenerate        → ipc.profile.regenerate_result
 *   outbound: ipc.profile.delete            → ipc.profile.delete_ack
 *   outbound: ipc.profile.set_consent       → ipc.profile.consent_state
 *
 * CDJ Whisper visual discipline:
 *   - Amber accent ONLY on the small consent ON LED + the confirm action
 *     glyph on Regenerate. Delete is fault-red (matches the recording-row
 *     delete affordance).
 *   - Monochrome key:value table. Mono type for the values.
 *   - No emojis (per project convention — and Kaan blocked them in CSS).
 *   - All copy lowercase; uppercase reserved for the group header.
 */

import { registerStyle } from "../../session/components/_style-registry.js";
import { emitIpc, sendIpcRequest } from "../../ipc/client.js";
import type {
  ProfileDeleteAck,
  ProfileRegenerateResult,
  ProfileViewResult,
} from "../../ipc/messages.js";

export interface ProfilePanelHandle {
  element: HTMLElement;
  /** Re-fetch view + re-render. Called after regenerate / delete / consent
   *  toggle so the panel always reflects the on-disk truth. */
  refresh(): Promise<void>;
  /** Tear down (unsubscribe + cancel pending requests). The Settings drawer
   *  calls this when the user closes the panel. */
  dispose(): void;
}

interface ProfileViewSnapshot {
  profile: Record<string, unknown> | null;
  bytes: number;
  consent: boolean;
}

const CSS = `
  .vmx-profile-panel {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
    color: var(--silk);
    font-family: var(--type-body);
    font-size: 12px;
    line-height: 1.5;
  }
  .vmx-profile-panel__consent-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding-bottom: var(--sp-2);
    border-bottom: 1px solid var(--silk-22);
  }
  .vmx-profile-panel__consent-led {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-2);
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--silk-65);
  }
  .vmx-profile-panel__consent-led[data-on="true"] {
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-profile-panel__consent-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--silk-22);
    box-shadow: inset 0 0 0 1px var(--silk-40);
  }
  .vmx-profile-panel__consent-led[data-on="true"] .vmx-profile-panel__consent-dot {
    background: var(--amber);
    box-shadow: 0 0 6px var(--amber-22);
  }
  .vmx-profile-panel__bytes {
    font-family: var(--type-mono);
    font-size: 10px;
    color: var(--silk-40);
    letter-spacing: 0.05em;
  }
  .vmx-profile-panel__empty {
    color: var(--silk-65);
    font-style: italic;
    padding: var(--sp-3) 0;
  }
  .vmx-profile-panel__table {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px var(--sp-3);
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.45;
  }
  .vmx-profile-panel__key {
    color: var(--silk-65);
    text-transform: lowercase;
  }
  .vmx-profile-panel__value {
    color: var(--silk);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .vmx-profile-panel__actions {
    display: flex;
    gap: var(--sp-2);
    padding-top: var(--sp-2);
    border-top: 1px solid var(--silk-22);
  }
  .vmx-profile-panel__btn {
    flex: 1;
    appearance: none;
    border: 1px solid var(--silk-22);
    background: transparent;
    color: var(--silk);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 6px var(--sp-3);
    border-radius: 4px;
    cursor: pointer;
    transition: border-color 120ms ease, color 120ms ease;
  }
  .vmx-profile-panel__btn:hover:not(:disabled) {
    border-color: var(--silk);
  }
  .vmx-profile-panel__btn[data-variant="primary"]:hover:not(:disabled) {
    border-color: var(--amber);
    color: var(--amber);
  }
  .vmx-profile-panel__btn[data-variant="danger"]:hover:not(:disabled) {
    border-color: var(--led-fault, #d4413a);
    color: var(--led-fault, #d4413a);
  }
  .vmx-profile-panel__btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .vmx-profile-panel__enable {
    appearance: none;
    border: 1px solid var(--amber-22);
    background: transparent;
    color: var(--amber);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 6px var(--sp-3);
    border-radius: 4px;
    cursor: pointer;
  }
  .vmx-profile-panel__footer {
    font-family: var(--type-mono);
    font-size: 10px;
    color: var(--silk-40);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding-top: var(--sp-2);
  }
  .vmx-profile-panel__status {
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-65);
    padding: var(--sp-2) 0;
    min-height: 1em;
  }
  .vmx-profile-panel__status[data-error="true"] {
    color: var(--led-fault, #d4413a);
  }
`;

registerStyle("vmx-profile-panel", CSS);

const VIEW_TIMEOUT_MS = 5_000;
const REGENERATE_TIMEOUT_MS = 15_000;

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length === 0 ? "—" : v.join(", ");
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>);
    if (entries.length === 0) return "—";
    return entries.map(([k, vv]) => `${k}: ${String(vv)}`).join("\n");
  }
  if (typeof v === "number") return Number.isInteger(v) ? `${v}` : v.toFixed(1);
  return String(v);
}

async function fetchView(): Promise<ProfileViewSnapshot> {
  const reply = (await sendIpcRequest<ProfileViewResult>(
    "ipc.profile.view",
    {},
    "ipc.profile.view_result",
    VIEW_TIMEOUT_MS,
  )) as ProfileViewResult;
  return {
    profile: (reply.payload.profile as Record<string, unknown> | null) ?? null,
    bytes: reply.payload.bytes,
    consent: reply.payload.consent,
  };
}

async function fetchRegenerate(): Promise<ProfileRegenerateResult> {
  return (await sendIpcRequest<ProfileRegenerateResult>(
    "ipc.profile.regenerate",
    {},
    "ipc.profile.regenerate_result",
    REGENERATE_TIMEOUT_MS,
  )) as ProfileRegenerateResult;
}

async function fetchDelete(): Promise<ProfileDeleteAck> {
  return (await sendIpcRequest<ProfileDeleteAck>(
    "ipc.profile.delete",
    {},
    "ipc.profile.delete_ack",
    VIEW_TIMEOUT_MS,
  )) as ProfileDeleteAck;
}

export function renderProfilePanel(): ProfilePanelHandle {
  const root = document.createElement("section");
  root.className = "vmx-profile-panel";
  root.setAttribute("data-testid", "profile-panel");

  let disposed = false;
  let currentSnapshot: ProfileViewSnapshot = {
    profile: null,
    bytes: 0,
    consent: false,
  };

  function setStatus(text: string, error = false): void {
    const node = root.querySelector(
      ".vmx-profile-panel__status",
    ) as HTMLElement | null;
    if (node) {
      node.textContent = text;
      node.dataset.error = error ? "true" : "false";
    }
  }

  function render(): void {
    root.replaceChildren();

    const consentRow = document.createElement("div");
    consentRow.className = "vmx-profile-panel__consent-row";
    const consentLed = document.createElement("span");
    consentLed.className = "vmx-profile-panel__consent-led";
    consentLed.dataset.on = currentSnapshot.consent ? "true" : "false";
    const dot = document.createElement("span");
    dot.className = "vmx-profile-panel__consent-dot";
    consentLed.append(
      dot,
      document.createTextNode(
        `consent ${currentSnapshot.consent ? "on" : "off"}`,
      ),
    );
    consentRow.append(consentLed);

    if (currentSnapshot.consent) {
      const bytes = document.createElement("span");
      bytes.className = "vmx-profile-panel__bytes";
      bytes.textContent = `${currentSnapshot.bytes} / 2048 bytes`;
      consentRow.append(bytes);
    } else {
      const enableBtn = document.createElement("button");
      enableBtn.type = "button";
      enableBtn.className = "vmx-profile-panel__enable";
      enableBtn.textContent = "enable";
      enableBtn.setAttribute("data-testid", "profile-panel-enable");
      enableBtn.addEventListener("click", () => {
        void enableConsent();
      });
      consentRow.append(enableBtn);
    }
    root.append(consentRow);

    if (!currentSnapshot.consent) {
      const empty = document.createElement("div");
      empty.className = "vmx-profile-panel__empty";
      empty.textContent =
        "profile disabled. enable to let vibemix learn your style.";
      root.append(empty);
      appendStatusAndFooter();
      return;
    }

    if (currentSnapshot.profile === null) {
      const empty = document.createElement("div");
      empty.className = "vmx-profile-panel__empty";
      empty.textContent =
        "no profile yet. vibemix learns after your next session.";
      root.append(empty);
    } else {
      const table = document.createElement("div");
      table.className = "vmx-profile-panel__table";
      for (const [k, v] of Object.entries(currentSnapshot.profile)) {
        const keyCell = document.createElement("div");
        keyCell.className = "vmx-profile-panel__key";
        keyCell.textContent = k;
        const valCell = document.createElement("div");
        valCell.className = "vmx-profile-panel__value";
        valCell.textContent = fmtValue(v);
        table.append(keyCell, valCell);
      }
      root.append(table);
    }

    const actions = document.createElement("div");
    actions.className = "vmx-profile-panel__actions";

    const regenBtn = document.createElement("button");
    regenBtn.type = "button";
    regenBtn.className = "vmx-profile-panel__btn";
    regenBtn.dataset.variant = "primary";
    regenBtn.textContent = "regenerate now";
    regenBtn.setAttribute("data-testid", "profile-panel-regenerate");
    regenBtn.addEventListener("click", () => {
      void regenerate();
    });
    actions.append(regenBtn);

    if (currentSnapshot.profile !== null) {
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "vmx-profile-panel__btn";
      delBtn.dataset.variant = "danger";
      delBtn.textContent = "delete profile";
      delBtn.setAttribute("data-testid", "profile-panel-delete");
      delBtn.addEventListener("click", () => {
        void deleteProfile();
      });
      actions.append(delBtn);
    }
    root.append(actions);
    appendStatusAndFooter();
  }

  function appendStatusAndFooter(): void {
    const status = document.createElement("div");
    status.className = "vmx-profile-panel__status";
    status.setAttribute("data-testid", "profile-panel-status");
    status.dataset.error = "false";
    root.append(status);

    const footer = document.createElement("div");
    footer.className = "vmx-profile-panel__footer";
    footer.textContent = "stays on this machine · never uploaded";
    root.append(footer);
  }

  async function refresh(): Promise<void> {
    if (disposed) return;
    try {
      currentSnapshot = await fetchView();
      render();
    } catch (err) {
      setStatus(`load failed: ${(err as Error).message ?? err}`, true);
    }
  }

  async function enableConsent(): Promise<void> {
    try {
      await emitIpc("ipc.profile.set_consent", { consent: true });
      // Sidecar fires ipc.profile.consent_state asynchronously. Re-fetch
      // view to capture the new state — the view_result carries the
      // consent flag so we don't have to chase the consent_state echo.
      await refresh();
    } catch (err) {
      setStatus(`enable failed: ${(err as Error).message ?? err}`, true);
    }
  }

  async function regenerate(): Promise<void> {
    setStatus("regenerating…");
    try {
      const reply = await fetchRegenerate();
      if (reply.payload.ok && reply.payload.profile) {
        setStatus("profile updated.");
      } else {
        const reason = reply.payload.error ?? "unknown";
        if (reason === "consent_off") {
          setStatus("consent is off. enable above to regenerate.", true);
        } else if (reason === "insufficient_evidence") {
          setStatus(
            "not enough session data yet. keep mixing and try again.",
            false,
          );
        } else {
          setStatus(`regenerate failed: ${reason}`, true);
        }
      }
      await refresh();
    } catch (err) {
      setStatus(`regenerate failed: ${(err as Error).message ?? err}`, true);
    }
  }

  async function deleteProfile(): Promise<void> {
    setStatus("deleting…");
    try {
      const reply = await fetchDelete();
      if (reply.payload.ok) {
        setStatus("profile deleted.");
      } else if (reply.payload.error === "not_found") {
        setStatus("nothing to delete. no profile on disk.", false);
      } else {
        setStatus(`delete failed: ${reply.payload.error ?? "unknown"}`, true);
      }
      await refresh();
    } catch (err) {
      setStatus(`delete failed: ${(err as Error).message ?? err}`, true);
    }
  }

  // Initial render with empty state; refresh() fills the actual snapshot.
  render();
  void refresh();

  return {
    element: root,
    refresh,
    dispose(): void {
      disposed = true;
    },
  };
}
