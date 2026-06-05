import type { CitationChip } from "./components/citation-strip.js";

export type CohostStatus = "LISTENING" | "TALKING" | "IDLE";

export interface TranscriptLine {
  role: "ai" | "user" | "system";
  text: string;
  ts: string;
}

export type ReactionsByTs = ReadonlyMap<string, readonly CitationChip[]>;

/** Milliseconds before an active ungrounded co-host reads as a fault. */
export const GROUNDING_FAILURE_MS = 5000;
