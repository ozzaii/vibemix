// SPDX-License-Identifier: Apache-2.0
//
// The cohesive DesktopShell's single state store. Vanilla-TS reimplementation
// of the role Bravoh's DesktopSidebarContext + activation state play in React:
// it holds the structural state that makes the five folded interior surfaces
// read as ONE app, and notifies subscribers on change.
//
// Two kinds of state live here:
//   - Structural (user-driven): which surface is active, is the sidebar
//     collapsed, is the grounding panel open.
//   - Activation (audio-driven, "self-arranging"): idle -> listening -> live.
//     The shell rearranges itself around this without any setup screen, which
//     is the "pick it up, start play, everything arranges, go" contract.
//
// Connection is tracked separately so the footer can show an HONEST status:
// idle with connection "disconnected" is EXPECTED, never a fault (cardinal
// invariant #5). The store never conflates "no music yet" with "broken".

export type SurfaceId = "deck" | "crate" | "learn" | "debrief" | "settings";
export type ActivationState = "idle" | "listening" | "live";
export type ConnectionState = "connected" | "reconnecting" | "disconnected";

export interface ShellModel {
  collapsed: boolean;
  activeSurface: SurfaceId;
  activation: ActivationState;
  panelOpen: boolean;
  connection: ConnectionState;
}

type Listener = (model: Readonly<ShellModel>) => void;

const STORAGE_KEY = "vibemix:shell";
const SURFACE_IDS: readonly SurfaceId[] = ["deck", "crate", "learn", "debrief", "settings"];

interface PersistedShape {
  collapsed?: boolean;
  activeSurface?: SurfaceId;
}

function readPersisted(): PersistedShape {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as PersistedShape;
    return {
      collapsed: typeof parsed.collapsed === "boolean" ? parsed.collapsed : undefined,
      activeSurface:
        parsed.activeSurface && SURFACE_IDS.includes(parsed.activeSurface)
          ? parsed.activeSurface
          : undefined,
    };
  } catch {
    // Corrupt or unavailable storage is non-fatal; fall back to defaults.
    return {};
  }
}

function writePersisted(model: ShellModel): void {
  try {
    const shape: PersistedShape = {
      collapsed: model.collapsed,
      activeSurface: model.activeSurface,
    };
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(shape));
  } catch {
    // Persistence is best-effort; never throw on a private-mode / quota error.
  }
}

export class ShellStore {
  private model: ShellModel;
  private readonly listeners = new Set<Listener>();

  constructor(initial?: Partial<ShellModel>) {
    const persisted = readPersisted();
    this.model = {
      collapsed: persisted.collapsed ?? false,
      activeSurface: persisted.activeSurface ?? "deck",
      activation: "idle",
      panelOpen: false,
      connection: "disconnected",
      ...initial,
    };
  }

  getState(): Readonly<ShellModel> {
    return this.model;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private set(patch: Partial<ShellModel>, persist = false): void {
    let changed = false;
    for (const key of Object.keys(patch) as (keyof ShellModel)[]) {
      if (this.model[key] !== patch[key]) {
        changed = true;
        break;
      }
    }
    if (!changed) return;
    this.model = { ...this.model, ...patch };
    if (persist) writePersisted(this.model);
    for (const listener of this.listeners) listener(this.model);
  }

  setCollapsed(collapsed: boolean): void {
    this.set({ collapsed }, true);
  }

  toggleCollapsed(): void {
    this.setCollapsed(!this.model.collapsed);
  }

  setActiveSurface(activeSurface: SurfaceId): void {
    this.set({ activeSurface }, true);
  }

  setPanelOpen(panelOpen: boolean): void {
    this.set({ panelOpen });
  }

  togglePanel(): void {
    this.setPanelOpen(!this.model.panelOpen);
  }

  setConnection(connection: ConnectionState): void {
    this.set({ connection });
  }

  /**
   * Drive the self-arranging activation. Going "live" auto-opens the grounding
   * panel (the receipt for what the co-host just reacted to); dropping back to
   * "idle" closes it. This is the layout arranging itself around the music,
   * not the user configuring panels.
   */
  setActivation(activation: ActivationState): void {
    if (activation === "live") {
      this.set({ activation, panelOpen: true });
    } else if (activation === "idle") {
      this.set({ activation, panelOpen: false });
    } else {
      this.set({ activation });
    }
  }
}
