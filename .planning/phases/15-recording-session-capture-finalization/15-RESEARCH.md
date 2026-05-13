# Phase 15: Recording & Session Capture Finalization — Research

**Researched:** 2026-05-13
**Domain:** Per-session WAV/JSONL/JSON recording lifecycle + retention sweep + in-drawer recording browser
**Confidence:** HIGH (stack + integration points), MEDIUM (Tauri scheme details — verified via WebFetch+WebSearch, not Context7)

## Summary

Phase 15 is small in surface area but load-bearing on three orthogonal axes: (1) on-disk format invariants that downstream POC diagnostic tools (`cohost_v4.py`'s VoiceRecorder reader shape) depend on; (2) a Tauri custom-scheme protocol for `<audio>` playback of locally-written WAV files; (3) retention sweeps that touch live process state on Windows where file-in-use locks are real. Every piece has a clean, low-surface implementation path that reuses existing Phase 11–14 infrastructure: ConfigStore for retention_days, SettingsApplier for the change-event hook, IPC schema + drift gate for 3 new families, SettingsDrawer for the browser UI, Phase 12 confirmDialog for delete.

Two infrastructure details require attention before planning: **(a)** the CONTEXT.md proposes `recording://` as the URL scheme, but Tauri 2's `assetProtocol` config registers only the fixed `asset://localhost/<path>` scheme — a literal `recording://` would require `register_uri_scheme_protocol` (Rust-side custom protocol handler) instead of the config-only path. **(b)** The CSP currently allows `default-src 'self'` only; serving WAV through any non-self scheme requires extending `media-src` (and the asset protocol also needs `asset:` + `http://asset.localhost` on the CSP allowlist). Both are surfaced as Open Questions below — the planner picks one path.

**Primary recommendation:** Use Tauri's built-in `assetProtocol` (URL form `asset://localhost/<absolute_path>`, accessed via `convertFileSrc()`) scoped to `$APPDATA/vibemix/recordings/**` on macOS and `$APPLOCALDATA/vibemix/recordings/**` on Windows. Skip the custom-scheme path — it adds a Rust file + maintenance burden for zero new capability. Update the CSP `media-src` directive accordingly. Hook retention sweep into `SettingsApplier._apply_retention` + `SessionLoop.boot()` + a yet-unwritten `SessionLoop.on_session_close` hook. Use atomic-write pattern (`.tmp` + `os.replace`) for `session.json`, exactly matching the existing `ConfigStore.save()` recipe. Use the `wave` module's existing seekable-header-patching behavior (it auto-rewrites the RIFF length on `close()` — no special crash-recovery code needed for soak-test pass; crashed sessions surface via missing `ended_at_iso` in session.json).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| WAV / JSONL write during session | Python sidecar (audio thread + asyncio) | — | All audio I/O is sidecar-owned; `VoiceRecorder` already lifted from POC. Webview never touches WAV bytes. |
| session.json write at start + close | Python sidecar (asyncio) | — | Sidecar owns session lifecycle; metadata write is a `SessionLoop` concern. |
| Retention sweep | Python sidecar (asyncio) | — | All filesystem mutation outside the recordings/ tree is sidecar-side; Rust shell never deletes user data. |
| Recordings list / delete / usage IPC | Python sidecar | TS shell (consumer) | Sidecar enumerates filesystem + serves index; webview consumes via IPC, like settings.state. |
| Recording browser UI (rows, expand, audio playback) | TS webview | — | Pure presentation; no Rust commands needed. |
| `<audio>` playback of voice.wav | TS webview via Tauri assetProtocol | Rust (asset resolver) | Tauri's built-in asset protocol scopes file reads; webview gets a URL, browser decoder handles WAV. |
| Capability allowlist update | Rust shell (tauri.conf.json5 + capabilities/default.json) | — | Asset protocol scope is shell-tier config, even though no Rust code runs per request. |
| Delete confirmation modal | TS webview | — | Re-uses Phase 12 `confirmDialog` — pure presentation. |

## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| REC-01 | Per-session directory `recordings/<YYYYMMDD-HHMMSS>/` | `VoiceRecorder.__init__` already creates this layout with `datetime.now().strftime("%Y%m%d-%H%M%S")` ([VERIFIED: src/vibemix/audio/recorder.py:52-56]). Plan adds `session.json` write alongside. |
| REC-02 | `input.wav` — 16kHz mono int16 | Already wired ([VERIFIED: recorder.py:65-68] — `setframerate(INPUT_SR_TARGET)` = 16000). No change needed; POC compat test pins the invariant. |
| REC-03 | `voice.wav` — 24kHz mono int16 | Already wired ([VERIFIED: recorder.py:60-63] — `setframerate(OUTPUT_SR)` = 24000). No change needed. |
| REC-04 | `events.jsonl` — session timeline | Already wired ([VERIFIED: recorder.py:70-83] — `events.jsonl` opened append-mode, first line is `session_start` event). Schema is stable; v4 readers parse cleanly. |
| REC-05 | Recording browser UI — list, replay, delete | Greenfield UI inside Settings drawer RECORDING group. 3 new IPC families + 2 new TS components + Tauri assetProtocol scope. UI-SPEC §Layout locks visual. |
| REC-06 | Retention policy enforcement | `retention_days` already persists in ConfigStore ([VERIFIED: config_store.py:144]); sentinel `36500` already handled by retention-slider stop 5 ([VERIFIED: retention-slider.ts:53]). Plan adds the sweep itself. |

## Standard Stack

### Core (sidecar — Python)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `wave` (stdlib) | Python 3.12 | WAV file write — already in use | Mature stdlib; auto-patches RIFF header on `close()` for seekable streams [VERIFIED: docs.python.org/3/library/wave.html]. No additional dependency. |
| `json` (stdlib) | Python 3.12 | session.json + events.jsonl writes | Same recipe ConfigStore uses ([VERIFIED: config_store.py:230-234]). |
| `shutil` (stdlib) | Python 3.12 | `shutil.rmtree` for retention sweep | Standard recursive directory removal. `ignore_errors=True` is the documented pattern for best-effort cleanup [CITED: docs.python.org/3/library/shutil.html]. |
| `pathlib` (stdlib) | Python 3.12 | All path manipulation — already in use | Consistent with rest of `vibemix.runtime` ([VERIFIED: config_store.py imports]). |
| `os.scandir` (stdlib) | Python 3.12 | Per-session-dir size computation | 2-20× faster than `os.walk` + `os.stat`; DirEntry caches `.stat()` so total-bytes loops do 1 syscall per file [CITED: PEP 471, benhoyt.com/writings/scandir]. |
| `datetime` (stdlib) | Python 3.12 | ISO-8601 timestamps for session.json | Already used by recorder for `wall_clock_iso` ([VERIFIED: recorder.py:74]). |
| `jsonschema` | 4.x (already pinned) | IPC schema validation for 3 new families | Phase 11 W0 invariant — no pydantic ([VERIFIED: messages.py:29]). |

### Core (webview — TypeScript)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tauri-apps/api/core` | ^2.11 (already pinned) | `convertFileSrc()` for `<audio src>` mapping | Built-in helper that maps a filesystem path to the `asset://localhost/...` URL the webview can fetch [CITED: v2.tauri.app/reference/javascript/api/namespacecore/]. |
| `IntersectionObserver` (browser API) | — | Virtualized rendering above 50 rows | Native browser API; no third-party dep. CONTEXT Area 2 prescribes "virtualized list of rows". UI-SPEC §Virtualization caps the threshold at 50. |
| HTML5 `<audio>` element | — | voice.wav playback with `preload="metadata"` | UI-SPEC §Component Contracts pins this. Native browser decoder handles 24kHz mono int16 WAV out of the box. |

### Supporting (test-only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | already pinned | Generate synthetic 60-min PCM streams for soak test | Required to produce deterministic int16 buffers; already used by `tests/audio/`. |
| `pytest` markers | already wired | `@pytest.mark.slow` for the 60-min soak | CONTEXT.md Area 4 — soak runs in `pytest -m slow` only. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Built-in `asset://localhost/` (recommended) | Custom `register_uri_scheme_protocol("recording", ...)` in Rust | Custom scheme requires a new Rust file, async responder for large WAVs, manual MIME-type + Range-header handling. The asset protocol does all of this natively. Pick custom scheme ONLY if the scope must be tighter than `$APPDATA/vibemix/recordings/**`. No tighter scope is needed. |
| `os.scandir`-based hand-walk | `pathlib.Path.iterdir()` | iterdir() is slower (extra stat per entry) and less ergonomic for size summation. Stick with scandir. |
| Append `session.json` at session start with placeholder, finalize at close | Write `session.json` ONLY at close | Two-write pattern is what enables crash detection — absence of `ended_at_iso` ⇒ crashed=true. Single-write-at-close would lose all crashed-session metadata. CONTEXT.md Area 1 locked this; research confirms it's correct. |
| Sync playback of audio + events (v2 stretch) | Static event list | Defer per CONTEXT — adds non-trivial JS state; impacts soak-test budget. |

**Installation:** No new pip or npm installs. Everything required is already in `pyproject.toml` and `tauri/ui/package.json` as of Phase 14 close.

**Version verification:** [VERIFIED: pyproject.toml] — `wave` is stdlib, no version pin; `numpy>=1.26`, `jsonschema>=4.21` already present. [VERIFIED: tauri/ui/package.json] — `@tauri-apps/api` already pinned to `^2.11`.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │  Python sidecar (single process)        │
                    │                                          │
   audio thread     │   ┌────────────┐                         │
   (sounddevice    ─┼──▶│ VoiceRec.  │── input.wav (16k)       │
    callbacks)      │   │ push_input │── voice.wav (24k)       │
                    │   │ push_voice │── events.jsonl          │
   asyncio loop    ─┼──▶│ log_event  │                         │
                    │   └────────────┘                         │
                    │         │                                 │
                    │         ▼                                 │
                    │   ┌────────────┐  ┌─────────────────────┐│
                    │   │SessionLoop │──│ RecordingsIndex     ││
                    │   │  .boot()   │  │  - scan recordings/ ││
                    │   │  .close()  │  │  - per-dir totals   ││
                    │   └────────────┘  │  - sweep stale dirs ││
                    │         │         └─────────────────────┘│
                    │         │                  │             │
                    │         ▼                  ▼             │
                    │   ┌────────────┐    ┌──────────────────┐ │
                    │   │ session.   │    │ RetentionSweep   │ │
                    │   │  json      │    │  trigger:        │ │
                    │   │ (atomic    │    │  1. boot         │ │
                    │   │  write)    │    │  2. settings.set │ │
                    │   └────────────┘    │  3. session.close│ │
                    │                     └──────────────────┘ │
                    │                              │           │
                    │                              ▼           │
   ws_bus (8765)   ◀┼─── ipc.recordings.list/usage/delete_ack  │
                    └─────────────────────────────────────────┘
                                       ▲ │
                                       │ ▼
   ┌────────────────────────────────────┴───────────────────────┐
   │   Tauri 2 shell                                             │
   │   ┌─────────────────┐         ┌──────────────────────────┐ │
   │   │ tauri.conf.json5│         │ TS webview                │ │
   │   │ assetProtocol   │         │ ┌────────────────────────┐│ │
   │   │  enable: true   │         │ │ SettingsDrawer         ││ │
   │   │  scope:         │ ──────▶ │ │  RECORDING group       ││ │
   │   │   $APPDATA/...  │         │ │  ├ retention slider    ││ │
   │   │   $APPLOCALDATA │         │ │  ├ disk usage line     ││ │
   │   │   /vibemix/     │         │ │  └ RecordingBrowser    ││ │
   │   │   recordings/** │         │ │     ├ Row              ││ │
   │   └─────────────────┘         │ │     │  └ <audio src=   ││ │
   │                                │ │     │   asset://...    ││ │
   │                                │ │     │   voice.wav>     ││ │
   │                                │ │     └ ConfirmDialog    ││ │
   │                                │ └────────────────────────┘│ │
   │                                └──────────────────────────┘ │
   └──────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions only)

```
src/vibemix/runtime/
├── recordings_index.py        # NEW — RecordingsIndex + RetentionSweep classes
└── session_loop.py            # MODIFIED — wire .boot() + close hook + 3 new ipc handlers

src/vibemix/audio/
└── recorder.py                # MODIFIED — write session.json at __init__, finalize at close()

tauri/ui/src/settings/components/
├── recording-browser.ts       # NEW — list + virtualization + disk usage line
└── recording-row.ts           # NEW — row + expand + audio + transcript overlay

tauri/ui/src/settings/
└── SettingsDrawer.ts          # MODIFIED — append browser to recordingBody after retention slider

tauri/src-tauri/
├── tauri.conf.json5           # MODIFIED — add assetProtocol block + CSP media-src directive
└── capabilities/default.json  # MODIFIED — description note (assetProtocol is plugin-less)

src/vibemix/ui_bus/messages.py             # MODIFIED — 3 new wrapper dataclasses
tauri/ui/src/ipc/messages.schema.json      # MODIFIED — 3 new oneOf entries + payload defs

tests/recording/                # NEW directory
├── __init__.py
├── test_session_metadata.py   # session.json shape + atomic write + crash-detect
├── test_recordings_index.py   # scandir-based summary + delete + usage
├── test_retention_sweep.py    # 3-trigger coverage + Windows lock fallback + ∞ sentinel
├── test_poc_compat.py         # opens fresh recording, reads via v4 VoiceRecorder shape
└── test_60min_soak.py         # @pytest.mark.slow — 60-min synthetic stream
```

### Pattern 1: Two-write session.json with crash-detect

**What:** Write `session.json` twice per session — once at start (with placeholder `ended_at_iso=null, crashed=false, duration_s=0`), once at close (final values). If the process dies between the two writes, the next launch's RetentionSweep walks `recordings/`, finds dirs whose `session.json` has `ended_at_iso=null` AND mtime older than ~30s (i.e., not the active session), and marks them `crashed=true` via an atomic rewrite.

**When to use:** Always — this is the only way to surface crashed sessions in the browser UI without sentinel files.

**Example:**
```python
# src/vibemix/audio/recorder.py — add to __init__ after WAV setup:

SESSION_JSON_VERSION = "1.0"

session_meta = {
    "vibemix_version": __version__,
    "session_json_version": SESSION_JSON_VERSION,
    "started_at_iso": wall_start.isoformat(timespec="milliseconds"),
    "started_at_unix": round(wall_start.timestamp(), 3),
    "ended_at_iso": None,           # filled at close
    "ended_at_unix": None,          # filled at close
    "duration_s": None,             # filled at close
    "voice": voice_id,              # passed via constructor
    "mode": mode,                   # "hype" | "coach"
    "genre": genre,
    "user_level": user_level,       # "beginner" | "intermediate" | "pro"
    "event_count": 0,               # incremented in log_event
    "voice_wav_bytes": 0,           # filled at close
    "input_wav_bytes": 0,           # filled at close
    "events_jsonl_bytes": 0,        # filled at close
    "crashed": False,               # flipped to True by retention sweep if ended_at_iso is None
}
_atomic_write_json(self.session_dir / "session.json", session_meta)
self._session_meta = session_meta  # held for close()
```

```python
# Atomic write — same recipe as ConfigStore.save() at config_store.py:229-234
def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, indent=2, sort_keys=True)
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)   # atomic on POSIX + Windows ReplaceFileW
```
Source: [VERIFIED: config_store.py:229-234], [CITED: docs.python.org/3/library/os.html#os.replace]

### Pattern 2: Tauri assetProtocol with scoped recordings dir

**What:** Configure the built-in asset protocol in `tauri.conf.json5` to expose only the recordings directory; consume via `convertFileSrc()` from the webview.

**When to use:** Phase 15 voice.wav playback. Webview gets an `asset://localhost/<absolute-path>` URL it can drop into `<audio src>`.

**Example:**
```json5
// tauri/src-tauri/tauri.conf.json5 — extend app.security
"app": {
  "security": {
    // EXTEND CSP — adds media-src for asset: scheme; preserves all existing directives
    "csp": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:; media-src 'self' asset: http://asset.localhost; connect-src 'self' ws://127.0.0.1:8765",
    "assetProtocol": {
      "enable": true,
      "scope": [
        "$APPDATA/vibemix/recordings/**",
        "$APPLOCALDATA/vibemix/recordings/**"
      ]
    }
  }
}
```

```ts
// tauri/ui/src/settings/components/recording-row.ts — audio element creation
import { convertFileSrc } from "@tauri-apps/api/core";

function makeAudioElement(absoluteWavPath: string): HTMLAudioElement {
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";   // metadata only — full decode deferred to play()
  audio.style.width = "100%";
  audio.style.accentColor = "var(--amber)";
  audio.src = convertFileSrc(absoluteWavPath);   // → asset://localhost/<path>
  return audio;
}

// On row collapse — release decoder resources:
function teardownAudio(audio: HTMLAudioElement): void {
  audio.pause();
  audio.removeAttribute("src");
  audio.load();                  // releases decoder buffer; documented MDN pattern
}
```
Source: [CITED: v2.tauri.app — assetProtocol config], [CITED: MDN — HTMLMediaElement.load() releases decoder when src removed], [VERIFIED: tauri.conf.json5 current CSP shape].

### Pattern 3: 3-trigger retention sweep

**What:** Run the same sweep function from three call-sites with the same `retention_days` snapshot read at each call. Sweep is best-effort — failures log + continue.

**When to use:** On every retention-policy change, every session start, every session close.

**Example:**
```python
# src/vibemix/runtime/recordings_index.py

import shutil
from datetime import datetime, timedelta

def run_retention_sweep(
    recordings_root: Path,
    retention_days: int,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Walk recordings/, delete dirs older than retention_days. Returns deleted names.

    Sentinel 36500 (∞ from Phase 12 retention slider) skips the sweep entirely.
    """
    if retention_days >= 36500:
        return []
    now = now or datetime.now()
    cutoff = now - timedelta(days=retention_days)
    deleted: list[str] = []
    if not recordings_root.exists():
        return deleted
    for entry in os.scandir(recordings_root):
        if not entry.is_dir():
            continue
        try:
            session_start = datetime.strptime(entry.name, "%Y%m%d-%H%M%S")
        except ValueError:
            continue       # unrecognized name — skip; never delete
        if session_start >= cutoff:
            continue
        try:
            shutil.rmtree(entry.path, ignore_errors=True)
            deleted.append(entry.name)
        except OSError as e:
            log.warning("retention sweep: could not remove %s: %s", entry.name, e)
            # Windows file-in-use: silently continue. The dir will be retried
            # on the next sweep trigger. Never raise into SessionLoop.
    return deleted
```
Source: [CITED: docs.python.org/3/library/shutil.html — `ignore_errors=True` is documented best-effort pattern], [VERIFIED: retention-slider.ts:53 — `36500` sentinel].

### Pattern 4: IPC family addition (3 new families)

**What:** Add `recordings.list` / `recordings.delete` / `recordings.usage` following the exact Phase 12 dataclass-mirror pattern.

**When to use:** Every new IPC family. The drift gate enforces wrapper-count == schema-oneOf-count.

**Example:**
```python
# src/vibemix/ui_bus/messages.py — append after MascotMoodChange

@dataclass(frozen=True, slots=True)
class RecordingSummary:
    session_dir: str           # "20260513-210410"
    started_at_iso: str
    duration_s: float
    event_count: int
    bytes_total: int
    crashed: bool

@dataclass(frozen=True, slots=True)
class RecordingsListPayload:
    pass                       # empty body — list-on-request

@dataclass(frozen=True, slots=True)
class RecordingsListResultPayload:
    sessions: tuple[RecordingSummary, ...]
    bytes_total: int

@dataclass(frozen=True, slots=True)
class RecordingsDeletePayload:
    session_dir: str

@dataclass(frozen=True, slots=True)
class RecordingsDeleteAckPayload:
    session_dir: str
    ok: bool
    error: str | None = None

@dataclass(frozen=True, slots=True)
class RecordingsUsagePayload:
    sessions: int
    bytes_total: int

@dataclass(frozen=True, slots=True)
class RecordingsList:
    type: Literal["ipc.recordings.list"]
    ts: str
    payload: RecordingsListPayload

    @classmethod
    def make(cls) -> "RecordingsList":
        return cls(type="ipc.recordings.list", ts=_now_iso(), payload=RecordingsListPayload())

    def to_json(self) -> str:
        return _serialize(self)
# (... 4 more wrapper classes following same pattern)
```

Source: [VERIFIED: messages.py:360-450 — IpcBoot + StatusTick + PermissionCheck wrapper pattern].

### Anti-Patterns to Avoid

- **Custom `register_uri_scheme_protocol("recording", ...)` for no reason:** Adds Rust code + Range header handling + MIME-type negotiation, none of which buy anything over the built-in asset protocol. Use asset protocol unless a tighter scope than `$APPDATA/vibemix/recordings/**` is required (none is).
- **`shutil.rmtree(path, ignore_errors=False)` for retention sweep:** A locked file on Windows would raise OSError, kill the sweep mid-walk, and leave a half-pruned recordings/. Use `ignore_errors=True` AND wrap the whole iteration in try/except (the sweep is best-effort).
- **Writing `session.json` only at close:** Loses crashed-session metadata. Two-write pattern (start + close) is the only way to detect crashes without a sentinel file.
- **Inline-mounting `<audio>` for every row at list-build time:** 100 rows × decoder allocations = visible scrubbing lag + memory bloat. Lazy-create on expand, tear down on collapse ([CITED: MDN — `removeAttribute("src") + load()` releases decoder]).
- **Walking `recordings/` with `os.walk` for size sums:** `os.scandir` is 2-20× faster because `DirEntry.stat()` is cached; on Windows the size is available without an extra syscall. Use scandir.
- **Persisting computed disk-usage to ConfigStore:** It's a derived value — recomputing on drawer open is cheap (< 50ms for 200 sessions) and avoids stale-cache bugs.
- **Listening to ConfigStore writes via a watcher:** SettingsApplier already has a direct hook in `_apply_retention` — call the sweep right there. No filesystem watcher needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic JSON file writes | Custom temp-file + rename + fsync | Existing ConfigStore.save() recipe ([VERIFIED: config_store.py:229-234]) | Already audited by Phase 12; `os.replace` is atomic on POSIX + Windows ReplaceFileW [CITED: docs.python.org]. |
| WAV header patching after long writes | Manual byte poke at offset 4 for RIFF length | Python `wave` module — auto-patches on `close()` for seekable streams [CITED: docs.python.org/3/library/wave.html] | Already used by VoiceRecorder. Soak-test pass requires it. |
| WAV playback | Custom decoder, Web Audio API graph | Native HTML5 `<audio controls>` element | Browser handles 24kHz mono int16 PCM natively. UI-SPEC §Component Contracts locks this. |
| Asset URL generation | Manual `asset://localhost/${encodeURIComponent(path)}` string concat | `@tauri-apps/api/core` `convertFileSrc()` | Cross-platform path encoding quirks (Windows backslashes, drive letters) handled inside the helper [CITED: GitHub issue 7970]. |
| Local file scheme registration | `register_uri_scheme_protocol` in main.rs | Built-in `assetProtocol` in tauri.conf.json5 | Native handles MIME types, Range requests, async streaming. Custom buys nothing here. |
| Virtualized list | tanstack/virtual, react-window | IntersectionObserver chunked render (CONTEXT-prescribed) | Zero third-party UI dep (registry-safety gate); 12-row chunk is sufficient for ≤200 sessions. |
| File-in-use detection on Windows | psutil + handle inspection | `shutil.rmtree(..., ignore_errors=True)` + log + retry-next-sweep | Sweep is best-effort; locked file gets reaped on next trigger. Detecting which process locks is fragile and unnecessary. |
| ISO 8601 timestamps | Custom format strings | `datetime.now().astimezone().isoformat(timespec="milliseconds")` | Already used by recorder ([VERIFIED: recorder.py:74]). |
| Directory-size summation | os.walk + os.stat per file | os.scandir + DirEntry.stat() (cached) | 2-20× faster + 1 syscall per file on Windows [CITED: PEP 471]. |

**Key insight:** Phase 15 has zero new fundamental problems. Every infrastructure piece already exists in Phases 11-14. The job is wiring + 3 new IPC families + a presentation surface that follows the established pattern.

## Runtime State Inventory

Phase 15 is greenfield additive — it does not rename, refactor, or migrate any existing state. The retention sweep DOES delete existing recordings dirs (intentionally — that's the feature), but no in-place schema migration is involved.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `recordings/<YYYYMMDD-HHMMSS>/` dirs from Phase 2 + Phase 4 + later — these contain `input.wav` + `voice.wav` + `events.jsonl` but NO `session.json` (Phase 15 introduces it). | RetentionSweep MUST treat absent `session.json` as a legacy dir: include in list with `crashed=false, duration_s=0, event_count=0` derived from JSONL line count. NEVER auto-delete legacy dirs unless they exceed retention age. |
| Live service config | None — Phase 15 introduces no new services. | None. |
| OS-registered state | None — no Tauri command registrations change shape (assetProtocol is config-only). | None. |
| Secrets/env vars | None. | None. |
| Build artifacts | None. | None. |

**Nothing found in 4 of 5 categories** — verified by reading CONTEXT.md `<deferred>` (cloud upload, encryption, export bundle all OUT) and PROJECT.md's OUT-of-scope list. Only "Stored data" carries an action: handle legacy-dir-without-session.json gracefully during list/sweep.

## Common Pitfalls

### Pitfall 1: CSP `media-src` directive missing breaks `<audio>` silently
**What goes wrong:** The webview's CSP currently has no `media-src` directive ([VERIFIED: tauri.conf.json5:65]), so it falls back to `default-src 'self'`. The asset protocol URL `asset://localhost/...` is NOT `'self'`, so `<audio src>` fails with a CSP violation in DevTools console and the audio element silently shows duration `--:--`.
**Why it happens:** CSP `default-src` is the catch-all; `media-src` is a separate fetch directive that controls `<audio>` and `<video>` sources.
**How to avoid:** Extend the CSP to include `media-src 'self' asset: http://asset.localhost`. Match the discussion-11498 example exactly.
**Warning signs:** Audio element renders controls but duration stays `--:--`; DevTools console shows "Refused to load media from 'asset://...' because it violates the following Content Security Policy directive: 'default-src self'".

### Pitfall 2: macOS scope variable mismatch — `$APPDATA` vs `$APPLOCALDATA`
**What goes wrong:** Tauri's scope variables resolve differently on macOS vs Windows. On macOS, `$APPDATA` maps to `~/Library/Application Support/<identifier>` AND `$APPLOCALDATA` also maps to `~/Library/Application Support/<identifier>` (they're the same on Apple). On Windows, `$APPDATA` is `%APPDATA%` (Roaming) and `$APPLOCALDATA` is `%LOCALAPPDATA%` (Local). Listing only `$APPDATA` in scope would silently miss Windows installs that wrote to LocalAppData.
**Why it happens:** Tauri uses `dirs` crate (Rust) which honors OS conventions strictly. macOS has no "local vs roaming" distinction; Windows does.
**How to avoid:** ALWAYS include BOTH `$APPDATA/vibemix/recordings/**` and `$APPLOCALDATA/vibemix/recordings/**` in the scope array. The Python side writes to the same dir via `_app_data_dir()` ([VERIFIED: config_store.py:95-115] — macOS: `~/Library/Application Support/vibemix`, Windows: `%APPDATA%/vibemix`). Map Python's path-resolution exactly to Tauri's variables.
**Warning signs:** Audio playback works on macOS, fails silently on Windows; webview console shows "Refused to load due to scope".

### Pitfall 3: `<audio>` decoder leak on row collapse
**What goes wrong:** Setting `audio.pause()` alone does NOT free the decoder buffer; the browser keeps the WAV mmap'd until garbage collection. With 200 rows collapsed-then-re-expanded across a 30-minute session, this measurably leaks memory.
**Why it happens:** `pause()` only stops playback. `removeAttribute("src") + load()` is the documented memory-release recipe.
**How to avoid:** On every row collapse: `audio.pause(); audio.removeAttribute("src"); audio.load();`. UI-SPEC §Virtualization already requires this.
**Warning signs:** Chrome DevTools Memory tab shows growing "MediaElementAudioBuffer" allocations on expand/collapse cycles.

### Pitfall 4: `shutil.rmtree(ignore_errors=True)` masks bugs that aren't file-in-use
**What goes wrong:** `ignore_errors=True` swallows EVERY OSError — including programmer errors like a typo in the path or a permissions bug. The sweep silently does nothing and disk usage never drops.
**Why it happens:** It's a coarse-grained handler.
**How to avoid:** Use `ignore_errors=True` for the common case but wrap the call in try/except OSError as well, log specific errors, and emit a one-shot `ipc.error` if the FIRST sweep on boot deletes zero dirs when it should have deleted some (sentinel: count of dirs older than cutoff > 0 but deleted == 0).
**Warning signs:** Disk usage display shows the same value across multiple retention-day changes; logs show no errors.

### Pitfall 5: `wave.close()` on a partially-written WAV at process crash
**What goes wrong:** If the sidecar crashes mid-session (SIGKILL, OOM, power loss), `wave.close()` never runs, and the RIFF header's "data length" field remains `0` from the open-time placeholder. Most WAV players reject the file or play 0 seconds.
**Why it happens:** The wave module patches the header ONLY on graceful close. Mid-write data is on disk but the header is wrong.
**How to avoid:** Two mitigations: (a) at session boot, scan for `recordings/*/voice.wav` and `input.wav` belonging to crashed sessions (sibling `session.json` has `ended_at_iso=null`) — for each, attempt a one-shot header-patch by computing actual data length from file size − 44-byte header. (b) Mark `crashed=true` in `session.json` regardless of WAV recoverability so the UI can warn the user. Defer (a) to v2 — for v1, marking crashed and offering playback-with-bad-header is acceptable; some players (ffmpeg, Audacity) recover automatically.
**Warning signs:** `<audio>` shows duration `--:--` and won't play despite the file existing on disk.

### Pitfall 6: 60-min soak test starves the test machine
**What goes wrong:** Synthesizing 60 minutes of 16kHz int16 (≈ 115 MB) + 24kHz int16 (≈ 173 MB) in memory at once exhausts CI runners or local laptops.
**How to avoid:** Stream synthetic frames in 100ms chunks (1600 frames at 16kHz; 2400 frames at 24kHz). Use `time.sleep(0)` between chunks to let asyncio breathe. Total wall-clock can be < 60 min — the test asserts WAV duration, NOT real-time pacing.
**Warning signs:** Soak test OOMs at ~30 min; CI runner thrashes swap.

### Pitfall 7: Schema drift on `recordings.list_result` array shape
**What goes wrong:** The schema says `sessions: array of RecordingSummary`, but the Python wrapper uses `tuple[RecordingSummary, ...]` for frozen-dataclass hashability. `dataclasses.asdict` preserves tuples; jsonschema rejects tuples for `type: array`.
**Why it happens:** This is the exact bug fixed by `_tuples_to_lists` in Phase 11 W0 ([VERIFIED: messages.py:46-61]).
**How to avoid:** Use tuples on the Python side as Phase 11 W0 prescribes; the existing `_serialize()` helper already calls `_tuples_to_lists()` before validation. No new helper needed — just don't introduce a parallel serialization path.
**Warning signs:** `npm run check:ipc` passes, but `python scripts/check_ipc_schema.py` fails with "tuple is not of type array".

### Pitfall 8: Recording browser refresh stutters at >50 rows during scroll
**What goes wrong:** Even with IntersectionObserver, if the row creation does synchronous DOM-heavy work (audio creation, transcript render) before being deferred, the scroll lag is visible.
**How to avoid:** Row factory creates ONLY the row shell + 3 cells. Audio + transcript are created lazily inside `setExpanded(true)`. Initial render keeps a stable height per row (44px CSS `min-height`) so the IntersectionObserver root's scroll height is correct without rows being mounted.
**Warning signs:** Drawer open with >100 sessions feels janky; row pop-in is visible mid-scroll.

### Pitfall 9: Legacy recording dirs (pre-Phase-15) break the list
**What goes wrong:** Existing `recordings/<YYYYMMDD-HHMMSS>/` dirs from Phase 2-13 have NO `session.json`. The naive RecordingsIndex throws FileNotFoundError when building summaries.
**How to avoid:** Treat missing `session.json` as "legacy dir" and synthesize a minimal summary: `started_at_iso` from the dir name, `duration_s` from the `voice.wav` WAV header (use `wave.open(...).getnframes() / getframerate()`), `event_count` from `events.jsonl` line count, `crashed=False`, `bytes_total` from scandir-summed file sizes. Reference: legacy data SHOULD be visible in the UI for retention-sweep symmetry.
**Warning signs:** Drawer opens to an empty list despite files existing; sidecar log shows FileNotFoundError on recordings/list.

## Code Examples

Verified patterns from official sources:

### Atomic JSON write (mirrors ConfigStore.save)
```python
# Source: src/vibemix/runtime/config_store.py:229-234 (VERIFIED in-repo)
import json, os
from pathlib import Path

def write_session_json(session_dir: Path, data: dict) -> None:
    target = session_dir / "session.json"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, target)   # atomic on POSIX + Windows ReplaceFileW
```

### Retention sweep with Windows-aware error handling
```python
# Source: CITED docs.python.org/3/library/shutil.html#shutil.rmtree
import os, shutil, logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("vibemix.recordings")

def sweep(root: Path, retention_days: int) -> list[str]:
    if retention_days >= 36500:    # ∞ sentinel — Phase 12 retention-slider.ts:53
        return []
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = []
    if not root.exists():
        return deleted
    with os.scandir(root) as it:
        for entry in it:
            if not entry.is_dir():
                continue
            try:
                started = datetime.strptime(entry.name, "%Y%m%d-%H%M%S")
            except ValueError:
                continue        # unknown name format — leave alone
            if started >= cutoff:
                continue
            try:
                shutil.rmtree(entry.path, ignore_errors=True)
                # Verify deletion succeeded — Windows file-in-use may leave dir behind silently
                if not Path(entry.path).exists():
                    deleted.append(entry.name)
                else:
                    log.warning("retention: %s still present after rmtree (file in use?)", entry.name)
            except OSError as e:
                log.warning("retention sweep failure on %s: %s", entry.name, e)
    return deleted
```

### scandir-based directory size summation
```python
# Source: CITED PEP 471 + benhoyt.com/writings/scandir
def sum_dir_bytes(d: Path) -> int:
    total = 0
    with os.scandir(d) as it:
        for entry in it:
            if entry.is_file(follow_symlinks=False):
                try:
                    total += entry.stat().st_size  # cached on Windows, 1 syscall on POSIX
                except OSError:
                    pass
    return total
```

### IntersectionObserver chunked list virtualization
```ts
// Source: CITED gusruss89.medium.com + andreaverlicchi.eu/blog/using-intersection-observers
// Pattern: render only rows within the visible viewport.
function mountVirtualizedList(
  container: HTMLElement,
  rows: RecordingSummary[],
  rowFactory: (summary: RecordingSummary) => HTMLElement,
): void {
  if (rows.length <= 50) {
    // Below the threshold: full mount, simpler + faster
    for (const summary of rows) container.append(rowFactory(summary));
    return;
  }
  // Above 50: render in 12-row chunks gated by IntersectionObserver
  const CHUNK = 12;
  let renderedCount = 0;
  const sentinel = document.createElement("div");
  sentinel.style.height = "1px";
  sentinel.setAttribute("aria-hidden", "true");
  const observer = new IntersectionObserver((entries) => {
    if (!entries[0]?.isIntersecting) return;
    const next = rows.slice(renderedCount, renderedCount + CHUNK);
    for (const summary of next) sentinel.before(rowFactory(summary));
    renderedCount += next.length;
    if (renderedCount >= rows.length) observer.disconnect();
  }, { root: container, rootMargin: "200px" });
  container.append(sentinel);
  observer.observe(sentinel);
}
```

### `<audio>` decoder lifecycle (mount + teardown)
```ts
// Source: CITED developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement
import { convertFileSrc } from "@tauri-apps/api/core";

function mountAudio(absoluteWavPath: string): HTMLAudioElement {
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = convertFileSrc(absoluteWavPath);
  return audio;
}

function teardownAudio(audio: HTMLAudioElement | null): void {
  if (!audio) return;
  audio.pause();
  audio.removeAttribute("src");
  audio.load();   // releases decoder + buffer; documented MDN pattern
}
```

### Tauri assetProtocol scope (literal config syntax)
```json5
// Source: CITED v2.tauri.app/reference/config — assetProtocol
// Source: CITED github.com/orgs/tauri-apps/discussions/11498 — scope variable usage
"app": {
  "security": {
    "csp": "...; media-src 'self' asset: http://asset.localhost; ...",
    "assetProtocol": {
      "enable": true,
      "scope": [
        "$APPDATA/vibemix/recordings/**",
        "$APPLOCALDATA/vibemix/recordings/**"
      ]
    }
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tauri v1 `tauri.allowlist.protocol.asset` config + `assetScope` array | Tauri v2 `app.security.assetProtocol.scope` | Tauri 2.0 release (Oct 2024) | Slightly renamed config keys; semantic-equivalent. Phase 11 is already on v2 — use new keys. [CITED: v2.tauri.app/blog/tauri-20] |
| Custom URL scheme via `register_uri_scheme_protocol` (synchronous) | `register_asynchronous_uri_scheme_protocol` for I/O-heavy responders | Tauri 2.0 | Only relevant if custom scheme chosen (not recommended for Phase 15). [CITED: docs.rs/tauri Builder] |
| `from_file_path` URL conversion (deprecated v1 API) | `convertFileSrc()` from `@tauri-apps/api/core` | Tauri 2.0 | Use the v2 helper; handles Windows path quirks. [CITED: Tauri issue 7970] |

**Deprecated/outdated:**
- `tauri.allowlist.*` (v1) — replaced by `app.security` + capabilities-based permission model in v2.
- Manual `asset://localhost/${path}` string concatenation — use `convertFileSrc()` instead (cross-platform).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | macOS `$APPDATA` and `$APPLOCALDATA` Tauri scope variables both resolve to `~/Library/Application Support/<identifier>` | Pitfall 2 | LOW — even if only one resolves there, listing both in scope is safe (the unused one is a no-op). Verified by `dirs` crate docs convention; Tauri uses `dirs::data_dir()` and `dirs::data_local_dir()` which both return `~/Library/Application Support` on macOS. |
| A2 | Built-in HTML5 `<audio>` plays 24kHz mono int16 WAV in Tauri 2 WebView (WKWebView on macOS, WebView2 on Windows) | Pattern 2 | LOW — both engines support PCM WAV natively (universal browser format since IE9 era). If wrong, fallback is custom Web Audio decode — would expand Phase 15 scope materially. Smoke-test with one WAV at plan-checker time to confirm. |
| A3 | `session.json` v1 schema is forward-compatible: future fields go in extras without breaking old POC readers | Pattern 1 | LOW — POC's `cohost_v4.py` only reads `events.jsonl`, not session.json (which doesn't exist in POC). Compatibility surface is the JSONL alone. |
| A4 | The `wave` module's auto-header-patching on close() makes the 60-min soak test pass even though writeframes() is called every 100ms across 36000 iterations | Pattern 3 / Pitfall 5 | LOW — the wave module appends data + seeks the file pointer on EVERY write; close() patches the RIFF length once. Documented behavior. [CITED: docs.python.org/3/library/wave.html] |
| A5 | `IntersectionObserver` on the drawer body's overflow region works without explicit `root` because the drawer scrolls naturally | Code Examples — Virtualization | LOW — Phase 12 drawer has `overflow-y: auto` on body; setting `root: container` is correct. If wrong, drop the `root` option for window-scoped fallback. |
| A6 | Tauri scope `$APPDATA/vibemix/recordings/**` matches the dir created by Python's `_app_data_dir() / "recordings"` ([VERIFIED: config_store.py:104]) on macOS | Pattern 2 | LOW — Python writes to `~/Library/Application Support/vibemix/`; Tauri scope variable resolves to the same. But the recordings root is NOT in ConfigStore — `VoiceRecorder.__init__` currently defaults to `Path.cwd() / "recordings"` ([VERIFIED: recorder.py:46]). Phase 15 MUST change `VoiceRecorder` to use the OS-aware path OR construct VoiceRecorder with an explicit root from `_app_data_dir() / "recordings"`. **This is the only material design decision the planner must make — see Open Questions Q1.** |
| A7 | 60-minute synthetic soak can run in < 60s wall-clock (deterministic, not real-time-paced) | Pitfall 6 | LOW — `writeframes(silence_bytes)` is O(n) on file write speed; SSD writes 100 MB in ~1s. Asserts WAV duration via `getnframes()/getframerate()`, not real time. |
| A8 | Windows-locked-file scenario during retention sweep is rare in practice because all recording dirs older than retention_days are sessions that ended cleanly | Pitfall 4 | MEDIUM — antivirus on Windows can briefly lock files post-write. The "retry on next sweep trigger" pattern mitigates this; worst case = stale dir lingers an extra session. |

**Total assumed claims: 8.** All are low-to-medium risk; none are blocking. The planner should validate A6 explicitly (recordings root location) during planning.

## Open Questions

1. **Recordings root: `cwd()/recordings` (POC) vs `$APPDATA/vibemix/recordings` (Tauri scope)?**
   - What we know: `VoiceRecorder.__init__` accepts an optional `root` parameter ([VERIFIED: recorder.py:45]); current call sites pass nothing → defaults to `Path.cwd() / "recordings"` ([VERIFIED: recorder.py:46, `__main__.py:287` `VoiceRecorder()`]). The Tauri assetProtocol scope needs an absolute, app-data-dir-relative path so that scoped reads work in production.
   - What's unclear: Should Phase 15 change the default to `_app_data_dir() / "recordings"`, OR pass an explicit root from `SessionLoop`/`__main__`?
   - **Recommendation:** Change `__main__.py` to pass `recordings_root = _app_data_dir() / "recordings"` explicitly to `VoiceRecorder(root=recordings_root)`. Keep the `Path.cwd() / "recordings"` default for backward-compat with the POC v4 script (which still ships in-repo). This way Phase 15 doesn't break `cohost_v4.py` and aligns production with the Tauri scope. Plan must surface a CONTEXT amendment if Kaan disagrees.

2. **`recording://` scheme name vs Tauri's built-in `asset://`?**
   - What we know: CONTEXT.md Area 2 + UI-SPEC §Tauri Configuration Delta both prescribe `recording://session_dir/voice.wav`. Tauri 2's `assetProtocol` config registers ONLY the fixed `asset://` scheme.
   - What's unclear: Is the `recording://` name aspirational/cosmetic, or does it carry a security/branding rationale?
   - **Recommendation:** Use the built-in `asset://` via `convertFileSrc()`. The scope mechanism already limits reads to `$APPDATA/vibemix/recordings/**`, so the security goal is met. If the planner wants the literal `recording://` scheme for cosmetic clarity, add a Rust `register_uri_scheme_protocol("recording", ...)` handler — it's ~30 lines, but it's a maintenance debt for zero new functionality. Recommend the built-in path; surface to user/discuss-phase only if asked.

3. **Recordings index — recompute on every list, or maintain a persistent index file?**
   - What we know: CONTEXT Area 3 says "live read on drawer open + after each sweep". 200 sessions × ~5 syscalls each = ~1000 syscalls = <100ms on SSD.
   - What's unclear: Will users have >500 sessions in practice? (60 min/day × 7 days = 7 sessions; unbounded retention could mean hundreds over months.)
   - **Recommendation:** Recompute on every list — at 200 sessions the cost is invisible. If real-world usage shows >1000 sessions, add a sidecar in-memory cache invalidated on session-close + delete + sweep. Don't pre-optimize.

4. **Crashed-session detection — sweep-time, or boot-time-only?**
   - What we know: Crash detection needs a pass that finds `session.json` files with `ended_at_iso=null`.
   - What's unclear: Should this run only on boot, or also during periodic sweep?
   - **Recommendation:** Boot-time only. Mid-session sweeps shouldn't touch the active session's session.json. Implementation: at `SessionLoop.run()` startup, before anything else, walk `recordings/*` and rewrite any session.json with `ended_at_iso=null AND mtime older than ~30s` to set `crashed=true`. This rewrite is a separate atomic write per file.

5. **`session.json` version field — needed in v1?**
   - What we know: Plan adds `session_json_version: "1.0"`.
   - What's unclear: Is forward-compat versioning premature? POC has no equivalent.
   - **Recommendation:** Include it. Marginal cost; saves a migration scramble in v2 when we add `gemini_model_used` or similar to the schema.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `wave` (stdlib) | recorder | ✓ | 3.12 | — |
| Python `shutil` (stdlib) | retention sweep | ✓ | 3.12 | — |
| Python `os.scandir` (stdlib) | RecordingsIndex | ✓ | 3.12 | — |
| Python `jsonschema` | IPC family validation | ✓ | already pinned ≥4.21 | — |
| Tauri 2 `@tauri-apps/api` `convertFileSrc` | webview audio URL | ✓ | ^2.11 ([VERIFIED: tauri/ui/package.json]) | — |
| Tauri 2 assetProtocol config | local file serving | ✓ | built-in | custom scheme via `register_uri_scheme_protocol` (defer) |
| WKWebView (macOS) native `<audio>` WAV support | voice.wav playback | ✓ | macOS 12.3+ | — |
| WebView2 (Windows) native `<audio>` WAV support | voice.wav playback | ✓ | Windows 10+ | — |
| `IntersectionObserver` API | virtualized list | ✓ | both engines (since 2018) | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (already wired) + vitest 2.x (already wired) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) + `tauri/ui/vitest.config.ts` |
| Quick run command | `pytest tests/recording/ -x` (skips `slow` marker by default) |
| Full suite command | `pytest -m "not slow" && pytest -m slow tests/recording/test_60min_soak.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REC-01 | Per-session dir created with `%Y%m%d-%H%M%S` name | unit | `pytest tests/recording/test_session_metadata.py::test_session_dir_name_format -x` | ❌ Wave 0 |
| REC-02 | `input.wav` is 16kHz mono int16 | unit | `pytest tests/recording/test_poc_compat.py::test_input_wav_format -x` | ❌ Wave 0 |
| REC-03 | `voice.wav` is 24kHz mono int16 | unit | `pytest tests/recording/test_poc_compat.py::test_voice_wav_format -x` | ❌ Wave 0 |
| REC-04 | `events.jsonl` is parseable + monotonic + has session_start first | unit | `pytest tests/recording/test_poc_compat.py::test_events_jsonl_shape -x` | ❌ Wave 0 |
| REC-04 | session.json round-trips through atomic write | unit | `pytest tests/recording/test_session_metadata.py::test_atomic_write_survives_simulated_crash -x` | ❌ Wave 0 |
| REC-04 | Crashed session is detected on next boot | unit | `pytest tests/recording/test_session_metadata.py::test_crashed_session_marked -x` | ❌ Wave 0 |
| REC-05 | `ipc.recordings.list` returns valid RecordingSummary[] | integration | `pytest tests/recording/test_recordings_index.py::test_list_round_trip -x` | ❌ Wave 0 |
| REC-05 | `ipc.recordings.delete` removes the dir | integration | `pytest tests/recording/test_recordings_index.py::test_delete_removes_dir -x` | ❌ Wave 0 |
| REC-05 | `ipc.recordings.usage` matches recomputed total | integration | `pytest tests/recording/test_recordings_index.py::test_usage_matches_scandir -x` | ❌ Wave 0 |
| REC-05 | Recording browser renders rows from list response (DOM) | vitest jsdom | `npx vitest run tauri/ui/src/settings/components/recording-browser.spec.ts` | ❌ Wave 0 |
| REC-05 | Row collapse tears down `<audio>` decoder | vitest jsdom | `npx vitest run tauri/ui/src/settings/components/recording-row.spec.ts` | ❌ Wave 0 |
| REC-05 | Delete confirm uses Phase 12 confirmDialog with destructive variant | vitest jsdom | `npx vitest run tauri/ui/src/settings/components/recording-row.spec.ts` | ❌ Wave 0 |
| REC-06 | Sweep deletes dirs older than retention_days | unit | `pytest tests/recording/test_retention_sweep.py::test_old_dir_deleted -x` | ❌ Wave 0 |
| REC-06 | Sweep skips when retention_days == 36500 (∞ sentinel) | unit | `pytest tests/recording/test_retention_sweep.py::test_infinity_sentinel_skips -x` | ❌ Wave 0 |
| REC-06 | Sweep fires on boot, on retention change, on session close | integration | `pytest tests/recording/test_retention_sweep.py::test_three_triggers -x` | ❌ Wave 0 |
| REC-06 | Sweep is best-effort on Windows file-in-use | unit (mock) | `pytest tests/recording/test_retention_sweep.py::test_oserror_does_not_raise -x` | ❌ Wave 0 |
| Soak | 60-min synthetic stream — WAVs valid + JSONL monotonic | integration (slow) | `pytest -m slow tests/recording/test_60min_soak.py -x` | ❌ Wave 0 |
| IPC | 3 new families pass drift gate | CI gate | `python scripts/check_ipc_schema.py && npm run check:ipc` | ✓ (gate exists; new families add coverage) |

### Sampling Rate
- **Per task commit:** `pytest tests/recording/ -x -m "not slow"` + `npx vitest run tauri/ui/src/settings/components/recording-*.spec.ts` (<30s combined)
- **Per wave merge:** `pytest -m "not slow"` (full suite, ~90s) + `npm run check:ipc` + `python scripts/check_ipc_schema.py`
- **Phase gate:** `pytest -m slow tests/recording/test_60min_soak.py` (one-shot, ~60-90s) + everything from "per wave merge" green

### Wave 0 Gaps
- [ ] `tests/recording/__init__.py` — empty marker file
- [ ] `tests/recording/conftest.py` — shared fixtures: `tmp_recordings_dir`, `make_fake_session(crashed=False, age_days=0)`, `synthetic_pcm_chunks`
- [ ] `tests/recording/test_session_metadata.py` — covers REC-04 atomic write + crash-detect
- [ ] `tests/recording/test_recordings_index.py` — covers REC-05 IPC roundtrips
- [ ] `tests/recording/test_retention_sweep.py` — covers REC-06 three-trigger semantics
- [ ] `tests/recording/test_poc_compat.py` — covers REC-02/03/04 v4 reader-shape (must run in default pytest)
- [ ] `tests/recording/test_60min_soak.py` — `@pytest.mark.slow` 60-min stream
- [ ] `tauri/ui/src/settings/components/recording-browser.spec.ts` — vitest jsdom
- [ ] `tauri/ui/src/settings/components/recording-row.spec.ts` — vitest jsdom

*Framework install:* None — pytest 8.x + vitest 2.x already wired (Phase 11/12).

## Security Domain

> Phase 15 surface: filesystem write (WAVs/JSONL/JSON), filesystem read (browser list), filesystem delete (retention + manual). Custom URL scheme registration to webview.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local sidecar ↔ local webview only. |
| V3 Session Management | no | Sessions here = DJ sessions (recordings), not user-auth sessions. |
| V4 Access Control | yes | Tauri assetProtocol `scope` array IS the access control — restricts webview reads to `$APPDATA/vibemix/recordings/**`. |
| V5 Input Validation | yes | `ipc.recordings.delete` payload `session_dir` MUST be validated as a `[0-9]{8}-[0-9]{6}` pattern AND must not escape the recordings root. |
| V6 Cryptography | no | Phase 15 explicitly defers encryption-at-rest to v2 (CONTEXT `<deferred>`); OS-level FileVault/BitLocker covers the case. |
| V7 Errors & Logging | yes | Sweep failures must be logged but never crash the session. No PII in logs (track titles already PII-banned per Phase 11 W4 privacy gate). |
| V8 Data Protection | yes | Recording dir is `chmod 0o700` ([VERIFIED: recorder.py:47]); preserve this invariant. Tauri scope provides additional webview-side gate. |
| V12 Files & Resources | yes | Path traversal in delete: `session_dir` must not contain `..` or absolute prefix. Validate at sidecar entry. |

### Known Threat Patterns for {Tauri 2 webview + Python sidecar + local filesystem}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `ipc.recordings.delete {session_dir: "../../etc/passwd"}` | Tampering | Validate `session_dir` against `^[0-9]{8}-[0-9]{6}$` regex; resolve against recordings root with `path.is_relative_to(recordings_root)`; reject otherwise. |
| Webview reads arbitrary file via crafted `asset://` URL escape | Information Disclosure | Tauri scope `$APPDATA/vibemix/recordings/**` enforces; no symlink-following (Tauri resolves real paths). |
| Delete request spam → DoS sidecar | Denial of Service | Single in-flight delete per session_dir; Tauri's existing 10s IPC timeout caps blast radius. |
| Malicious WAV in recordings dir crashes WebView decoder | Denial of Service | WAVs are sidecar-written only; sidecar never accepts WAVs from external sources. No attack surface in v1. |
| events.jsonl line exceeds JSON max | Tampering | Defensive: catch JSONDecodeError per line in the JSONL parser; skip and log. Single bad line doesn't break the list. |
| Race: drawer queries `recordings.list` while sweep is mid-delete | Data integrity | Sweep + list both read filesystem state; brief inconsistency is acceptable (the next list call resolves it). Don't lock. |
| Crashed session.json rewrite race during retention sweep + concurrent session_loop boot | Data integrity | Crashed-detection rewrite ONLY runs at SessionLoop.boot() before any new session opens; sweep doesn't touch session.json content. |

## Project Constraints (from CLAUDE.md)

These directives MUST hold for any Phase 15 plan:

- **No CLAP — Gemini Embedding 2 only** (PROJECT memory; irrelevant here — no embedding work).
- **POC files are reference, untouchable** (`cohost*.py`, `mascot.html`, `mocks/*`): Phase 15 introduces a `session.json` writer but MUST NOT modify `cohost_v4.py`'s `VoiceRecorder` shape; POC compat test runs the new recordings dir through v4's reader path to prove no break.
- **One-click install is HARD requirement**: Phase 15 MUST NOT add new pip or npm deps. Verified — every primitive is stdlib or already-pinned.
- **No scope creep**: Phase 15 ships browser + retention sweep + session.json. NO encryption, NO export bundle, NO cloud upload, NO synced playback. Mirror UI-SPEC §Out of Scope.
- **CDJ Whisper v5 visual contract LOCKED**: zero new tokens, zero new design directions. UI-SPEC §Color/§Typography/§Spacing all pin v5 primitives.
- **No emojis in source/copy** (`frontend-enforcement`): inline SVG icons only ([VERIFIED: UI-SPEC §Registry Safety]).
- **20/80 rule + retro-futurist hardware vocabulary**: amber reserved to 5 declared uses per UI-SPEC §Color; destructive uses `--rec`.
- **PRIVACY HARD RULE**: recording dirs are `chmod 0o700` ([VERIFIED: recorder.py:47]); preserve this. Track titles + MIDI moves stay sidecar-side until user opens a session.
- **Tauri capability allowlist must not silently broaden**: Phase 15's assetProtocol scope is an EXPLICIT addition documented in `capabilities/default.json` description (per Phase 11 W4 precedent).

## Sources

### Primary (HIGH confidence — in-repo, verified)
- `/Users/ozai/projects/dj-set-ai/.planning/phases/15-recording-session-capture-finalization/15-CONTEXT.md` — locked user decisions
- `/Users/ozai/projects/dj-set-ai/.planning/phases/15-recording-session-capture-finalization/15-UI-SPEC.md` — locked UI design contract
- `/Users/ozai/projects/dj-set-ai/.planning/REQUIREMENTS.md` — REC-01..06 + traceability
- `/Users/ozai/projects/dj-set-ai/.planning/STATE.md` — current project position (Phase 14 closed; 27 IPC families baseline)
- `/Users/ozai/projects/dj-set-ai/src/vibemix/audio/recorder.py` — VoiceRecorder current shape (lifted from cohost_v4.py:771-850)
- `/Users/ozai/projects/dj-set-ai/src/vibemix/runtime/session_loop.py` — SessionLoop pattern (handler registration, snapshot loop, run lifecycle)
- `/Users/ozai/projects/dj-set-ai/src/vibemix/runtime/settings.py` — SettingsApplier `_apply_retention` hook point (lines 251-262)
- `/Users/ozai/projects/dj-set-ai/src/vibemix/runtime/config_store.py` — atomic write recipe (lines 229-234) + `_app_data_dir()` (lines 95-115)
- `/Users/ozai/projects/dj-set-ai/src/vibemix/ui_bus/messages.py` — wrapper dataclass pattern + `_tuples_to_lists` serialization helper
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/ipc/messages.schema.json` — JSON Schema source-of-truth (27 oneOf entries at Phase 14 close)
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/settings/SettingsDrawer.ts` — `recordingBody` insertion site (lines 562-582)
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/settings/components/retention-slider.ts` — 36500 sentinel + 6 stops (lines 47-54)
- `/Users/ozai/projects/dj-set-ai/tauri/src-tauri/tauri.conf.json5` — current CSP + identifier + app.security shape
- `/Users/ozai/projects/dj-set-ai/tauri/src-tauri/capabilities/default.json` — capability allowlist + windows scope
- `/Users/ozai/projects/dj-set-ai/scripts/check_ipc_schema.py` — drift gate (count parity + per-wrapper roundtrip)

### Secondary (MEDIUM confidence — official docs, single fetch)
- [Tauri 2 Configuration Reference — assetProtocol](https://v2.tauri.app/reference/config/)
- [Tauri 2 Plugin File System (FsScope path variables)](https://v2.tauri.app/plugin/file-system/)
- [Tauri 2 Command Scopes](https://v2.tauri.app/security/scope/)
- [Tauri Discussion #11498 — Display image via asset protocol](https://github.com/orgs/tauri-apps/discussions/11498)
- [Tauri Discussion #5597 — Registering a custom URI scheme example](https://github.com/tauri-apps/tauri/discussions/5597)
- [Tauri Issue #7970 — convertFileSrc Windows path behavior](https://github.com/tauri-apps/tauri/issues/7970)
- [Tauri Issue #4826 — Local audio files on macOS](https://github.com/tauri-apps/tauri/issues/4826)
- [Tauri docs.rs Builder — register_uri_scheme_protocol + async variant](https://docs.rs/tauri/latest/tauri/struct.Builder.html)
- [Python docs — wave module (auto header patching on seekable streams)](https://docs.python.org/3/library/wave.html)
- [Python docs — shutil.rmtree (ignore_errors semantics)](https://docs.python.org/3/library/shutil.html)
- [Python docs — os.replace (cross-platform atomicity)](https://docs.python.org/3/library/os.html#os.replace)
- [PEP 471 — os.scandir](https://peps.python.org/pep-0471/)
- [MDN — HTMLMediaElement (decoder release via load() after removeAttribute("src"))](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/audio)
- [Ben Hoyt — Contributing os.scandir to Python (performance numbers)](https://benhoyt.com/writings/scandir/)
- [Tauri 2.0 Stable Release Notes](https://v2.tauri.app/blog/tauri-20/)

### Tertiary (LOWER confidence — community, single source)
- [Slav Basharov — Building a music player with Tauri + Svelte (convertFileSrc audio usage)](https://slavbasharov.com/blog/building-music-player-tauri-svelte) — informs `<audio>` + convertFileSrc pattern; cross-verified with MDN.
- [Medium — Super Simple List Virtualization in React with IntersectionObserver](https://gusruss89.medium.com/super-simple-list-virtualization-in-react-with-intersectionobserver-ca340fe98a34) — vanilla pattern adapted; the React framing is irrelevant to the chunked-render technique.
- [Andrea Verlicchi — Using IntersectionObserver to create vanilla lazyload](https://www.andreaverlicchi.eu/blog/using-intersection-observers-to-create-vanilla-lazyload) — vanilla JS pattern reference.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primitive is stdlib or already-pinned dep; no novel library choices.
- Architecture: HIGH — every integration point already exists in Phases 11-14 (ConfigStore, SettingsApplier, SettingsDrawer, IPC drift gate, atomic write recipe, scandir patterns).
- Pitfalls: HIGH for CSP / scope variable / decoder lifecycle (verified via Tauri docs + MDN); MEDIUM for Windows file-in-use behavior (best-effort mitigation strategy chosen; runtime evidence will come from soak test).
- Tauri assetProtocol semantics: MEDIUM — verified via web sources but not Context7 (no Tauri Context7 lookup available); the planner should run `npm run tauri dev` and load one WAV via `<audio src=convertFileSrc(...)>` as a plan-checker spot-check before locking the asset-protocol path.

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (1 month — stable stdlib + already-shipped Tauri 2.11 line; CSP/scope semantics rarely change).

---

**Ready for planner.** Open Question Q1 (recordings root location) is the single material decision worth surfacing to discuss-phase if the autonomous "just use `$APPDATA/vibemix/recordings`" recommendation is non-obvious; everything else is wiring + tests.

Sources:
- [Tauri 2 Configuration Reference](https://v2.tauri.app/reference/config/)
- [Tauri 2 File System plugin (path variables)](https://v2.tauri.app/plugin/file-system/)
- [Tauri 2 Command Scopes](https://v2.tauri.app/security/scope/)
- [Tauri Discussion #11498 — assetProtocol example](https://github.com/orgs/tauri-apps/discussions/11498)
- [Tauri Discussion #5597 — Custom URI scheme example](https://github.com/tauri-apps/tauri/discussions/5597)
- [Tauri Issue #7970 — convertFileSrc Windows path](https://github.com/tauri-apps/tauri/issues/7970)
- [Tauri Issue #4826 — macOS local audio](https://github.com/tauri-apps/tauri/issues/4826)
- [Tauri Builder docs.rs](https://docs.rs/tauri/latest/tauri/struct.Builder.html)
- [Python wave module](https://docs.python.org/3/library/wave.html)
- [Python shutil.rmtree](https://docs.python.org/3/library/shutil.html)
- [Python os.replace](https://docs.python.org/3/library/os.html#os.replace)
- [PEP 471 — os.scandir](https://peps.python.org/pep-0471/)
- [MDN HTMLMediaElement](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/audio)
- [Ben Hoyt — Contributing os.scandir](https://benhoyt.com/writings/scandir/)
- [Tauri 2.0 Release Notes](https://v2.tauri.app/blog/tauri-20/)
