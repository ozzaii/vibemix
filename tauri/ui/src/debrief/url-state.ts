// SPDX-License-Identifier: Apache-2.0

export interface DebriefDeepLinkPayload {
  eventId: string;
  timestampS: number;
}

export interface DebriefBootState {
  sessionDir: string;
  sessionId: string;
  isMockMode: boolean;
  deepLink: DebriefDeepLinkPayload | null;
}

function isTruthyParam(value: string | null): boolean {
  return value === "1" || value === "true";
}

function sessionIdFromDir(sessionDir: string): string {
  return sessionDir.split("/").pop() || "session";
}

export function parseDebriefBootUrl(search: string): DebriefBootState {
  const params = new URLSearchParams(search);
  const rawSessionDir = params.get("session") ?? "";
  const isMockMode = isTruthyParam(params.get("mock")) || rawSessionDir === "mock";
  const sessionDir = isMockMode ? "/tmp/vibemix-demo-session" : rawSessionDir;
  const sessionId = isMockMode ? "demo-session" : sessionIdFromDir(sessionDir);

  const deepLinkEventId = params.get("deepLinkEventId");
  const rawTimestamp = params.get("deepLinkTimestampS");
  const timestampS = rawTimestamp == null ? NaN : Number(rawTimestamp);
  const deepLink =
    deepLinkEventId && Number.isFinite(timestampS)
      ? { eventId: deepLinkEventId, timestampS }
      : null;

  return { sessionDir, sessionId, isMockMode, deepLink };
}

