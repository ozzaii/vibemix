# vibemix — Research Questions

Open questions surfaced during exploration / scoping that need investigation before they become requirements.

---

## Memory layer (v.next: The Memory Turn — 2026-05-18)

- **Which session artifacts ground the copilot best?** Voice transcripts (Kaan's speech + AI's speech)? EventDetector typed events (track changes, phase changes, mix moves)? Track-to-track sequences? Mic-on moments + crowd reads? All-of-the-above embedded multi-modally? — First phase's research, not a pre-decided answer.
- **What's the retrieval shape per coach prompt?** Top-k cosine? Hybrid cosine + BM25? Time-weighted decay? Recency-vs-similarity tradeoff? Per-prompt budget (token count of retrieved context)?
- **Retention & sizing.** What's the per-install storage budget? Forever-retention or rolling window? Does the user see / control / delete? Privacy implications for shared machines?
- **Cold-start UX.** What does session #1 feel like with no memory? How does the user *notice* memory growing over sessions? Is it shown anywhere (memory introspection UI) or invisible-but-felt?
- **Multimodal embedding tradeoffs.** Gemini Embedding 002 is multimodal — but ~180s audio cap per call. What's the cost/quality of embedding raw audio vs only embedding structured artifacts derived from audio?
- **Phase 32 DJ profile interaction.** Does the ~2KB structured profile get retired, kept as a fast-path cache, or layered as a derived view over the embedding store?

---
