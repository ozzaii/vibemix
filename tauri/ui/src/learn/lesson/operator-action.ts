// SPDX-License-Identifier: Apache-2.0

export interface LearnOperatorActionDevice {
  index?: number;
  name?: string;
  score?: number;
}

export interface LearnOperatorAction {
  prompt: string;
  route?: string;
  current_rekordbox_route?: string;
  target_capture_route?: string;
  route_mismatch?: boolean;
  nowplaying_blocker?: string;
  steps?: string[];
  recommended_output_devices?: LearnOperatorActionDevice[];
}

export function normalizeOperatorAction(raw: unknown): LearnOperatorAction | null {
  if (!isRecord(raw)) return null;
  const prompt = cleanString(raw.prompt);
  if (!prompt) return null;

  const route = cleanString(raw.route);
  const currentRekordboxRoute = cleanString(raw.current_rekordbox_route);
  const targetCaptureRoute = cleanString(raw.target_capture_route);
  const routeMismatch = raw.route_mismatch === true;
  const nowplayingBlocker = cleanString(raw.nowplaying_blocker);
  const steps = Array.isArray(raw.steps)
    ? raw.steps.map(cleanString).filter((step): step is string => Boolean(step))
    : [];
  const recommendedOutputDevices = Array.isArray(raw.recommended_output_devices)
    ? raw.recommended_output_devices
        .map(normalizeOperatorActionDevice)
        .filter((device): device is LearnOperatorActionDevice => device !== null)
    : [];

  return {
    prompt,
    ...(route ? { route } : {}),
    ...(currentRekordboxRoute ? { current_rekordbox_route: currentRekordboxRoute } : {}),
    ...(targetCaptureRoute ? { target_capture_route: targetCaptureRoute } : {}),
    ...(routeMismatch ? { route_mismatch: true } : {}),
    ...(nowplayingBlocker ? { nowplaying_blocker: nowplayingBlocker } : {}),
    ...(steps.length > 0 ? { steps } : {}),
    ...(recommendedOutputDevices.length > 0
      ? { recommended_output_devices: recommendedOutputDevices }
      : {}),
  };
}

export function compactOperatorActionLabel(action: LearnOperatorAction): string {
  const route = action.route ?? "";
  const searchable = `${action.prompt} ${route}`.toLowerCase();
  if (action.route_mismatch) {
    const target = compactTargetRouteLabel(action);
    return target ? `route Rekordbox to ${target}` : "route Rekordbox to capture";
  }
  const rateFixLabel = compactRateFixLabel(searchable, route || action.prompt);
  if (rateFixLabel) {
    return rateFixLabel;
  }
  const routeLabel = compactRouteLabel(route || action.prompt);

  if (searchable.includes("rekordbox") && routeLabel) {
    return `play Rekordbox through ${routeLabel}`;
  }
  if (searchable.includes("rekordbox")) {
    return "play Rekordbox from deck";
  }
  if (searchable.includes("eq exemplar") || searchable.includes("exemplar loops")) {
    const device = action.recommended_output_devices?.find((candidate) =>
      Boolean(candidate.name),
    )?.name;
    return device
      ? clampStatusText(`audition EQ examples on ${compactDeviceName(device)}`)
      : "audition EQ examples";
  }
  return clampStatusText(toStatusSentence(action.prompt));
}

export function operatorActionAriaLabel(action: LearnOperatorAction): string {
  const parts = [action.prompt];
  if (action.route) parts.push(`route: ${action.route}`);
  if (action.current_rekordbox_route) {
    parts.push(`current Rekordbox route: ${action.current_rekordbox_route}`);
  }
  if (action.target_capture_route) {
    parts.push(`target capture route: ${action.target_capture_route}`);
  }
  if (action.route_mismatch) {
    parts.push("route mismatch: yes");
  }
  const steps = action.steps?.filter(Boolean).slice(0, 3) ?? [];
  if (steps.length === 1) {
    parts.push(`next step: ${steps[0]}`);
  } else if (steps.length > 1) {
    parts.push(`steps: ${steps.join("; ")}`);
  }
  return parts.join("; ");
}

function normalizeOperatorActionDevice(raw: unknown): LearnOperatorActionDevice | null {
  if (!isRecord(raw)) return null;
  const name = cleanString(raw.name);
  const index = cleanFiniteNumber(raw.index);
  const score = cleanFiniteNumber(raw.score);
  if (!name && index === undefined && score === undefined) return null;
  return {
    ...(index !== undefined ? { index } : {}),
    ...(name ? { name } : {}),
    ...(score !== undefined ? { score } : {}),
  };
}

function compactRouteLabel(raw: string): string | null {
  if (!raw) return null;
  const blackhole = raw.match(/BlackHole(?:\s+(\d+)ch)?/i);
  if (blackhole) return blackhole[1] ? `BlackHole ${blackhole[1]}ch` : "BlackHole";
  return null;
}

function compactTargetRouteLabel(action: LearnOperatorAction): string | null {
  const raw = action.target_capture_route ?? action.route ?? "";
  if (!raw) return null;
  const routeLabel = compactRouteLabel(raw);
  if (routeLabel) return routeLabel;
  return clampStatusText(compactDeviceName(raw), 28);
}

function compactRateFixLabel(searchable: string, routeOrPrompt: string): string | null {
  const mentions48k =
    searchable.includes("48000hz") ||
    searchable.includes("48khz") ||
    searchable.includes("48k");
  const mentionsRateFix =
    searchable.includes("sample rate") ||
    searchable.includes("from 44100hz") ||
    searchable.includes(" to 48000hz") ||
    searchable.includes("rate");
  if (!mentions48k || !mentionsRateFix) return null;
  if (searchable.includes("aggregate")) return "set aggregate route to 48k";
  const routeLabel = compactRouteLabel(routeOrPrompt);
  if (routeLabel) return `set ${routeLabel} to 48k`;
  if (searchable.includes("rekordbox")) return "set Rekordbox route to 48k";
  return null;
}

function compactDeviceName(raw: string): string {
  return raw.replace(/\s*@\s*\d+Hz\b/i, "").trim();
}

function toStatusSentence(raw: string): string {
  const stripped = raw.trim().replace(/[.!?]+$/u, "");
  if (!stripped) return "";
  return stripped.charAt(0).toLowerCase() + stripped.slice(1);
}

function clampStatusText(raw: string, max = 48): string {
  const text = raw.trim();
  if (text.length <= max) return text;
  const clipped = text.slice(0, max - 3);
  const lastSpace = clipped.lastIndexOf(" ");
  const body = lastSpace >= 18 ? clipped.slice(0, lastSpace) : clipped;
  return `${body.trim()}...`;
}

function cleanString(raw: unknown): string | undefined {
  if (typeof raw !== "string") return undefined;
  const text = raw.trim();
  return text.length > 0 ? text : undefined;
}

function cleanFiniteNumber(raw: unknown): number | undefined {
  if (typeof raw !== "number" || !Number.isFinite(raw)) return undefined;
  return raw;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
