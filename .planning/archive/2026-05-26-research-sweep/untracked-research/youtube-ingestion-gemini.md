# YouTube Ingestion + Gemini "Quote-a-Moment" — Research

> Research date: 2026-05-26. Scope: feasibility + architecture for an agent that ingests YouTube
> videos/tracks, "listens" via Gemini, identifies a specific moment, cuts a clip at that moment, and
> presents it in the set (Bravoh-style track-quoting). Web-researched; sources at bottom.
>
> **Headline reality:** Gemini *can* take a public YouTube URL natively as a Part and understand
> audio+video, BUT **the timestamps it returns against a YouTube-URL Part drift badly** (5–10 min off
> over a 30-min video; output truncates early). So the clean design is **two-stage and grounded**:
> Gemini-on-URL = *cheap semantic locate* (which moment, roughly), then **local audio (yt-dlp pull) +
> our own DSP/transcript = precise timestamp + the actual clip cut**. This mirrors vibemix's cardinal
> invariant #3 "trust the audio" — never trust the model's wall-clock; trust the bytes.

---

## 1. Gemini API native YouTube understanding

### What it does
- **Native URL ingestion.** You pass a public YouTube URL directly as a `FileData` Part (no upload, no
  download on our side — Gemini fetches it server-side). It processes **both the audio stream and the
  visual frames** (default 1 FPS sampling). Capabilities: summarize, transcribe (speech), describe
  visuals, answer questions about specific moments, segment/chapter.
- **Models.** Gemini 2.5+ (and 3.x Flash, which vibemix is locked to). Pre-2.5 = 1 video/request;
  2.5+ = up to 10 videos/request (but **use 1 video per request for best results**).

### The exact request shape (google-genai SDK)
```python
from google import genai
from google.genai import types

client = genai.Client()  # picks up GEMINI_API_KEY; vibemix resolves model via model_router, NOT a literal

resp = client.models.generate_content(
    model=model_router.resolve("youtube_understand"),  # NEVER inline a model name (CI grep-gated)
    contents=types.Content(
        parts=[
            types.Part(
                file_data=types.FileData(
                    file_uri="https://www.youtube.com/watch?v=XEzRZ35urlk"
                )
            ),
            types.Part(text="List the breakdown/drop moments with MM:SS timestamps and a one-line caption each."),
        ]
    ),
)
print(resp.text)
```

### Clip a window of the video server-side (don't make Gemini watch the whole thing)
`VideoMetadata` lets you bound what Gemini ingests (cheaper, faster) and change frame rate:
```python
types.Part(
    file_data=types.FileData(file_uri="https://www.youtube.com/watch?v=XEzRZ35urlk"),
    video_metadata=types.VideoMetadata(
        start_offset="1250s",   # only ingest 20:50 .. 26:10
        end_offset="1570s",
        fps=1,                  # default 1; for music, 0.2–1 FPS is plenty (audio carries the signal)
    ),
)
```
For local bytes instead of a URL, use `inline_data=types.Blob(data=..., mime_type="video/mp4")` (or
audio mime) with the same `video_metadata`.

### Limits (current, "preview", subject to change)
| Limit | Value |
|---|---|
| Visibility | **Public videos only** — no private/unlisted. |
| Daily volume (free tier) | **≤ 8 hours** of YouTube video/day. |
| Length (paid tier) | No length cap; **2M-ctx models ≈ 2h video, 1M-ctx ≈ 1h** per request. |
| Videos/request | 1 (pre-2.5) / 10 (2.5+); **prefer 1**. |
| Pricing | YouTube-URL path is in preview, currently **no charge** (will change). |
| Token cost | ~**300 tokens/sec** of video at default media res, ~**100 tokens/sec** at low res. For music, drop media res to "low" — visuals are near-useless, audio dominates. |

### Timestamp / transcription reliability — THE load-bearing caveat
- **Transcription content is accurate**; **timestamps drift** when the source is a *YouTube URL Part*.
  Documented: a 30-min video transcribes fine but timestamps end at ~17 min and are off by 5–10 min.
  (googleapis/python-genai issue #1359; Google AI dev forum.)
- **Fix that the community confirms:** if you **download the file and upload the bytes** (inline_data
  or Files API) the timestamps stop drifting and are accurate. Same prompt, different ingestion path.
- **Implication for us:** **never present a Gemini-from-URL timestamp as a verified cut point.** Use
  the URL pass only to *locate the moment semantically* ("the drop is somewhere around the 4-minute
  mark, after the filtered build"), then resolve the exact sample offset locally (Section 2/3). This
  keeps us honest under invariant #2 (citation grounding) and #3 (trust the audio).

---

## 2. Audio / clip extraction (yt-dlp + ffmpeg)

### Pull best audio with yt-dlp (Python API)
```python
import yt_dlp

ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "/tmp/vibemix_yt/%(id)s.%(ext)s",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "wav",   # wav for DSP/CLAP; "mp3" if you need a small artifact
        "preferredquality": "0",
    }],
    "quiet": True,
    "noplaylist": True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=XEzRZ35urlk", download=True)
    audio_path = f"/tmp/vibemix_yt/{info['id']}.wav"
    duration_s = info["duration"]
```
Notes: yt-dlp shells out to **ffmpeg** for the audio extract (ffmpeg must be on PATH — already a
vibemix prereq for the audio stack). yt-dlp `2026.02.x` is current/functional as of this research.

### Cut a precise [start, end] "moment" with ffmpeg
**Frame/sample-accurate (re-encode) — use this for the quotable clip:**
```bash
# audio-only, exact window, re-encoded -> accurate boundaries
ffmpeg -ss 00:03:58.000 -i input.wav -to 00:04:14.000 -c:a pcm_s16le clip.wav
# (-to is interpreted relative to the seek when -ss precedes -i in modern ffmpeg; or use -t <dur>)
```
For a shareable artifact:
```bash
ffmpeg -ss 238.0 -i input.wav -t 16.0 -c:a libmp3lame -q:a 2 clip.mp3
```
**Fast keyframe-copy (rough cut, NOT sample-accurate)** — only for video, avoid for our use:
```bash
ffmpeg -i input.mp4 -ss 00:03:58 -to 00:04:14 -c copy clip.mp4   # snaps to nearest keyframe (±sec)
```

**Rules of thumb that matter for "moment" precision:**
- `-ss` **before** `-i` = fast input seek (good for long files); `-ss` **after** `-i` = decode-from-zero,
  most precise but slow. With **re-encode** either placement is accurate; with `-c copy` you snap to
  keyframes (can be seconds off → unacceptable for quoting a beat/drop). **Always re-encode for clips.**
- For audio (`-c:a pcm_s16le` / `libmp3lame`) there are no keyframe constraints — cuts are
  sample-accurate regardless, so audio quoting is the easy, reliable path.

### Embedding the cut clip
The clip.wav drops straight into vibemix's existing embed path. The chosen engine is **CLAP**
(`library/clap_engine.py`, laion_clap 630k-fusion, 512-dim, deterministic 10s-chunk mean-pool;
mean-centering mandatory — anisotropic). A 10–20s quote clip is one-or-two chunks → one mean-pooled
512-dim vector → store/compare in `library.db` exactly like local tracks. (Gemini stays the co-host
*brain* only; embeddings = CLAP per the 2026-05-26 decision.)

---

## 3. "Quote a track moment" — agent tool design

### The pattern
`(locate timestamp, semantic)  →  (resolve exact offset, grounded)  →  (cut clip)  →  (present w/ caption)`

This is intentionally **two-stage + verified** because of the timestamp-drift caveat (Section 1).

```
┌─ Stage A: LOCATE (cheap, semantic) ────────────────────────────────────┐
│ Gemini on YouTube URL Part (low media res, fps≈0.2, optional start/end  │
│ window) → returns candidate moments: rough MM:SS + caption + reason.    │
│ Treat MM:SS as a HINT, never as truth.                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │ candidate ~MM:SS + caption
                              ▼
┌─ Stage B: RESOLVE (grounded, local) ───────────────────────────────────┐
│ yt-dlp pull audio (cache by video_id) → run local DSP around the hint:  │
│  - onset/RMS/energy + downbeat grid (numpy/scipy already in-repo) to     │
│    snap to the actual drop/breakdown boundary near the hint;            │
│  - OR re-run Gemini on the *downloaded bytes* (inline_data) for a window │
│    where its timestamps are reliable, then DSP-snap to the beat.        │
│ Output: exact [start_s, end_s] aligned to a musical boundary.           │
└─────────────────────────────────────────────────────────────────────────┘
                              │ verified [start_s, end_s]
                              ▼
┌─ Stage C: CUT ──────────────────────────────────────────────────────────┐
│ ffmpeg re-encode audio clip (sample-accurate). Persist artifact +       │
│ provenance (video_id, url, start_s, end_s, snap_method).                │
└─────────────────────────────────────────────────────────────────────────┘
                              │ clip.wav/.mp3 + provenance
                              ▼
┌─ Stage D: PRESENT ──────────────────────────────────────────────────────┐
│ Emit a quote object to the UI: caption + clip + deep-link                │
│ (https://youtu.be/<id>?t=<start_s>) + the citation that proves it.      │
│ Optional: CLAP-embed the clip so it joins similarity/curate.            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tool shape for the Codex + MCP agent
Slot these alongside the existing grounded tool core in `library/toolset.py` (shared by both the
`gemini` built-in fn-calling backend and the `codex` MCP-STDIO backend via `library/mcp_server.py`).
Keep grounding identical across backends: the agent may only quote moments it has **resolved**, never
raw model-emitted timestamps (seen-set + re-validation, same discipline as `search_vibe`).

```python
# library/toolset.py — new grounded tools (sketch; wire via existing tool registry)

def yt_locate_moments(url: str, want: str, window: tuple[int,int] | None = None) -> list[dict]:
    """Stage A. Gemini-on-URL locate. Returns candidate moments:
       [{"hint_s": float, "caption": str, "why": str}]  -- hint_s is UNVERIFIED."""

def yt_resolve_moment(url: str, hint_s: float, kind: str) -> dict:
    """Stage B. yt-dlp pull (cached by video_id) + local DSP snap near hint_s.
       kind in {drop, breakdown, build, intro, outro, vocal, fill}.
       Returns {"start_s": float, "end_s": float, "snap_method": str, "confidence": float}."""

def yt_cut_clip(url: str, start_s: float, end_s: float, fmt: str = "wav") -> dict:
    """Stage C. ffmpeg re-encode, sample-accurate. Returns {"clip_path", "video_id", "provenance"}."""

def quote_moment(url: str, want: str) -> dict:
    """Stage D convenience: locate -> resolve -> cut -> build the UI quote object.
       Returns {"caption","clip_path","deep_link","start_s","end_s","video_id","citation_id"}.
       citation_id MUST resolve in EvidenceRegistry (invariant #2) or the quote is dropped."""
```

**Grounding contract (release gate):** every quote the agent surfaces carries a `citation_id` that
resolves in `EvidenceRegistry`. The evidence is the *resolved local offset + snap_method*, not the
Gemini hint. Un-resolvable → strip to ack-bank / silently drop. This is the same anti-slop gate that
already governs live reactions, extended to quotes.

**No-hang discipline** (carried from the Viber/AIRA template): bounded agent loop, per-request
wall-clock timeout, handlers always return, heartbeat. yt-dlp + ffmpeg run under
`loop.run_in_executor` (blocking) with their own timeout; a failed pull logs + returns an actionable
error, never wedges the agent.

### Caching & provenance
- Cache pulled audio by `video_id` under `~/.cache/vibemix/yt/` (mirrors the embeddings/library cache
  convention). Content-hash the clip window so repeated quotes of the same moment are free.
- Store provenance with every clip: `{video_id, url, title, uploader, start_s, end_s, snap_method,
  confidence, fetched_at}` — needed for the UI caption, the deep-link, and any later takedown/cleanup.

---

## 4. Matching a user's local track to its YouTube version

Goal: user has a local file; agent wants to quote the *YouTube* version of the same track.

### Pipeline
1. **Get clean artist/title.** Prefer existing tags (vibemix already reads Rekordbox collection.xml +
   track metadata). Fall back to filename parse ("Artist - Title (Mix).wav").
2. **Search YouTube via yt-dlp `ytsearch`** (no API key, no download):
```python
import yt_dlp
query = f"{artist} {title}"
opts = {"quiet": True, "skip_download": True, "extract_flat": True, "default_search": "ytsearch5"}
with yt_dlp.YoutubeDL(opts) as ydl:
    res = ydl.extract_info(query, download=False)  # -> {"entries": [ {id,title,uploader,duration,...}, ... ]}
candidates = res["entries"]
```
   CLI equivalent for quick probing:
   `yt-dlp --skip-download --print "%(id)s | %(title)s | %(duration)s" "ytsearch5:Artist Title"`
3. **Rank candidates** to avoid quoting the wrong upload (live edit, sped-up, cover, 10-hour loop):
   - **Duration match** — `abs(yt.duration - local.duration) <= ~3s` is the strongest cheap signal
     (kills most mismatches: extended mixes, loops, shorts).
   - **Title fuzzy match** on normalized artist+title (strip "(Official Video)", "[HD]", etc.).
   - **Uploader signal** — official artist/label channel > random reupload.
   - **Strongest verification (use when ambiguous):** pull the candidate's audio, **CLAP-embed it, and
     cosine against the local track's vector.** High similarity = same track, version-robust. This is
     exactly the engine we already have; reuse it as the disambiguator.
4. **Confidence gate.** Below threshold → don't quote (return "couldn't find a matching upload")
   rather than quote a wrong video. Honest-miss > confident-wrong (anti-slop).

### Tool
```python
def find_youtube_version(local_track_id: str) -> dict | None:
    """Tag/filename -> ytsearch5 -> rank by duration+title+uploader, CLAP-verify if ambiguous.
       Returns {"url","video_id","title","confidence"} or None if below gate."""
```

---

## 5. Legal / ToS reality (local app)

**Short version:** the Gemini-URL path is clean; the yt-dlp *download* path is a YouTube-ToS gray zone
that we should treat conservatively and keep user-initiated + ephemeral.

| Vector | Reality | Stance for vibemix |
|---|---|---|
| **Gemini takes a public YouTube URL** | Google's own first-party API ingests the URL server-side; we never download. This is Google ingesting Google-adjacent public content — the cleanest path. | **Primary "listen" path.** Use it for Stage-A locate freely. |
| **yt-dlp downloading audio** | The **yt-dlp tool itself is legal** to distribute/run (US/EU/most). **Downloading from YouTube violates YouTube ToS** (ToS only permits offline via the YouTube app/Premium). ToS breach is **contract, not criminal** — remedy is account action / civil, not jail. | Allowed technically; treat as **user-initiated, transient**. Don't build a download farm. |
| **Copyright** | Downloading/redistributing copyrighted audio you don't license = infringement regardless of tool. **Clips can fall under fair use/dealing** (short, transformative, commentary/criticism — which is literally what a co-host "quote + caption" is), but that's a defense, not a blanket right, and it's jurisdiction-dependent. | Keep clips **short (≤~15–30s), transformative (paired with the AI's commentary), ephemeral (cache, not a library you redistribute)**. Don't ship/exfiltrate clips off-device. |
| **Redistribution** | Re-uploading or sharing the ripped audio/clip is where real liability lives. | **Local-only.** Clips live in `~/.cache/vibemix/`; nothing uploaded to a vibemix server. The deep-link (`youtu.be/<id>?t=<s>`) sends users to YouTube — that's the safe "share." |

**Design guardrails (recommended):**
- **Default to the deep-link, not the rip.** The safest "quote" is caption + `youtu.be/<id>?t=<start>`
  that opens YouTube at the moment — zero download, zero clip artifact. Offer the local clip only as a
  user-initiated, on-device convenience.
- **User-initiated only.** No background/bulk ripping. The agent quotes when the user/flow asks.
- **Ephemeral cache, on-device.** Clips in the local cache, auto-pruneable; never uploaded to Bravoh
  infra (also avoids putting Bravoh's name on the rip).
- **Public-only** (Gemini enforces this anyway).
- **Don't advertise "download YouTube audio"** as a feature; frame it as "quote a moment" /
  "listen along." The capability is incidental to the AI-commentary value.
- This is a **product/legal decision for Kaan** — engineering can ship deep-link-only as the safe
  default and gate the local-clip rip behind an explicit, off-by-default user action.

---

## Concrete vibemix wiring summary
- **Engine split stays intact:** Gemini = brain/locate; **CLAP = all embedding/similarity/quote-verify**.
- **Trust the audio (#3):** Gemini-URL timestamps are hints; local DSP/bytes give the real cut.
- **Citation grounding (#2):** every quote carries an EvidenceRegistry citation = the *resolved* offset.
- **Reuse:** `library/toolset.py` tool core + `mcp_server.py` (Codex) / built-in fn-calling (Gemini);
  CLAP embed path; `~/.cache/vibemix/` cache convention; `run_in_executor` for yt-dlp/ffmpeg.
- **New deps:** `yt-dlp` (CLI/pyapi), `ffmpeg` (already a prereq). Both lazy-imported / shelled.

## Sources
- Gemini video understanding (URL Part, VideoMetadata, FPS, limits): https://ai.google.dev/gemini-api/docs/video-understanding
- Gemini video understanding (.txt mirror): https://ai.google.dev/gemini-api/docs/video-understanding.md.txt
- Vertex AI YouTube summarize sample: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/googlegenaisdk-textgen-with-youtube-video
- Gemini 2.5 video understanding (Google Dev blog): https://developers.googleblog.com/en/gemini-2-5-video-understanding/
- Timestamp drift on YouTube-URL transcription (python-genai #1359): https://github.com/googleapis/python-genai/issues/1359
- Timestamp accuracy thread (Google AI dev forum): https://discuss.ai.google.dev/t/improve-timestamp-accuracy-on-video-understanding/95356
- Gemini transcribe-YouTube sample (philschmid): https://github.com/philschmid/gemini-samples/blob/main/examples/gemini-analyze-transcribe-youtube.ipynb
- yt-dlp (repo, audio + ytsearch): https://github.com/yt-dlp/yt-dlp
- yt-dlp audio download tutorial: https://blog.elijahlopez.ca/posts/yt-dlp-audio-download/
- yt-dlp metadata (no download): https://www.hrekov.com/blog/youtube-metadata-python-yt-dlp
- yt-dlp ytsearch how-to: https://write.corbpie.com/searching-youtube-videos-with-yt-dlp/
- ffmpeg clipping (-ss/-to/-t, copy vs re-encode): https://www.mux.com/articles/clip-sections-of-a-video-with-ffmpeg
- ffmpeg trim/cut precise (2026 guide): https://wavespeed.ai/blog/posts/blog-how-to-trim-cut-video-ffmpeg-timestamps-duration/
- yt-dlp legality / YouTube ToS: https://audioutils.com/blog/is-yt-dlp-legal
- Downloading YouTube legally in 2026: https://www.bestvideodownloader.net/how-to-download-youtube-videos-legally-2026/
