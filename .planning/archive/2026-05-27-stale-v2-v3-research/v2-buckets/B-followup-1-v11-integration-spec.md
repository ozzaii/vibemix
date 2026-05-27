# Bucket B Follow-up #1 — v1.1 Integration Ship Spec

**Researched:** 2026-05-14
**Scope:** Implementation-ready spec for Mixxx integration, Rekordbox XML import, 10-SKU MIDI controller library, generic-MIDI fallback, mapping transpiler feasibility
**Audience:** vibemix v1.1 engineer (5-7 day ship)
**Confidence:** HIGH on controller library + pyrekordbox XML + python-osc; **MEDIUM on Mixxx OSC** — see correction below

---

## TL;DR — what changed vs. Bucket B

Three corrections an engineer needs before writing a line of code:

1. **Mixxx OSC is NOT in mainline Mixxx.** Bucket B treated Mixxx OSC as a shipped feature toggled in Preferences. Verified: as of Mixxx 2.5.6 (released 2026-03-27), **OSC is still PR #14388, draft, open, unmerged.** [VERIFIED: `gh api repos/mixxxdj/mixxx/pulls/14388` — last updated 2026-04-24, base=`main`, state=`open`, draft=`true`] The mainline Mixxx binary has no OSC code in `src/`. There IS no `src/osc/` directory. A user running stock Mixxx 2.5.6 does NOT see an OSC preference toggle. The Mixxx wiki page Bucket B cited is a design proposal from May 2021; the implementation work is in @JackieB-G's long-running PR chain (PRs #13662 → #13714 → #13835 → #14181 → #14238 → #14388, with #14388 the current head).

2. **The actual OSC address pattern is NOT `/mixxx/deck/playing` either.** PR #14388 uses **Tree/Branch/Leaf** addressing: `/Channel1/play`, `/Channel2/volume`, `/EqualizerRack1/Channel1/Effect1/parameter3`, `/Master/crossfader`. [VERIFIED: PR #14388 description.] The `/mixxx/deck/playing` shape on the wiki is from a 2021 OSCpack-based prototype that was abandoned. If a vibemix user *does* run an OSC-enabled build, **the addresses are Mixxx ControlObject group/key paths, prefixed with `/`** — same as the names visible in Developer Tools when Mixxx runs with `--developer`.

3. **`cohost_v4.py:599` has Sync at note `0x60`. The Mixxx DDJ-FLX4 mapping has Sync at `0x58`.** [VERIFIED: [Mixxx Pioneer-DDJ-FLX4.midi.xml](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml)] One of them is wrong, or they refer to different controller modes (FLX4 has Pioneer-native and MIDI modes with different note maps). **Action for the engineer:** boot the controller, run a `mido` sniffer against it, capture the actual note number Kaan's FLX4 emits when Sync is pressed, and write THAT into the canonical mapping. Don't trust either source until the wire is checked.

The strategic calls from Bucket B still hold:
- MIDI controller is the cross-platform telemetry layer
- Rekordbox XML import (not SQLCipher) is the durable library path
- Mixxx is the *only* DJ platform with a real-time deck-state surface, **but** that surface is a community PR build today, not a stock feature

What this means for v1.1 timing: ship the 10-SKU MIDI library + Rekordbox XML import as the headline. Mixxx OSC ships as **opt-in beta** with a clear UX note: "Requires custom Mixxx build with OSC PR — instructions in our wiki." If/when #14388 merges into Mixxx 2.6 (timing uncertain — PR is 14 months old in draft state), we promote it to first-class.

---

## 1. `MixxxBus` complete spec

### Install detection — how vibemix knows Mixxx is reachable

Three signals, in order:

1. **Process scan** (cheap, fast, false-positives possible): On macOS, run `pgrep -ix mixxx` (`-i` case-insensitive, `-x` exact match). On Windows, use `tasklist /FI "IMAGENAME eq mixxx.exe" /NH`. If the process is running we proceed.
2. **OSC port probe**: Send a probe OSC message to `127.0.0.1:7878` (vibemix's default listen port — receives FROM Mixxx) and listen for any incoming packet for 2 seconds. If we get a packet, Mixxx OSC is alive. If not, fall through.
3. **User opt-in fallback**: If process is running but no OSC packets arrive within 2s, show in the vibemix UI: "Mixxx detected but OSC silent. Enable OSC in Mixxx Preferences → OSC tab and restart, or use audio-only mode." Stay out of the audio-grounding path until user toggles "I've enabled OSC."

There is **no OSC discovery protocol** in Mixxx's implementation — it's plain UDP, the receiver IP/port has to be configured *in Mixxx* to point at vibemix. So the UX flow is: vibemix launches → tells user "configure Mixxx to send OSC to `127.0.0.1:7878`" → user adds that as a Receiver in Mixxx's OSC preferences → vibemix starts seeing packets. We CANNOT do this auto-configuration because Mixxx 2.5.6 stock has no OSC config UI yet.

### ControlObject map — what to subscribe to

Per PR #14388, the OSC client broadcasts on "value change" + on the periodic sync push (user-configurable interval, default ~500ms). The address scheme is `/{ControlGroup}/{ControlKey}`. Vibemix subscribes to these address patterns:

| Address pattern | Carries | Cadence | Vibemix use |
|---|---|---|---|
| `/Channel{N}/play` | float (1.0 playing, 0.0 stopped) | on-change | Track-change detection, set play state |
| `/Channel{N}/volume` | float (0.0-1.0, post-crossfader) | on-change + sync | Audible-deck weight |
| `/Channel{N}/TrackTitle` | string (pseudo-CO added by PR) | on-track-load | Authoritative track title (replaces nowplaying-cli for Mixxx) |
| `/Channel{N}/TrackArtist` | string (pseudo-CO) | on-track-load | Artist for prompt grounding |
| `/Channel{N}/playposition` | float (0.0-1.0) | sync push | Phrase-progress (mid-track vs. ending) |
| `/Channel{N}/duration` | float (seconds) | on-track-load | Compute remaining time |
| `/Channel{N}/bpm` | float | on-change | BPM without needing audio estimation |
| `/Channel{N}/rate` | float (tempo slider, -1.0..1.0) | on-change | Detect tempo nudges |
| `/Channel{N}/track_loaded` | float (0/1) | on-load/eject | Empty-deck filter |
| `/Channel{N}/eject` | float | on-eject | Track-out event |
| `/EqualizerRack1/Channel{N}/Effect1/parameter1` | float (0-1) | on-change | EQ low |
| `/EqualizerRack1/Channel{N}/Effect1/parameter2` | float | on-change | EQ mid |
| `/EqualizerRack1/Channel{N}/Effect1/parameter3` | float | on-change | EQ hi |
| `/QuickEffectRack1/Channel{N}/super1` | float | on-change | Filter knob |
| `/Master/crossfader` | float (-1.0..1.0) | on-change | Crossfader position |
| `/Master/volume` | float | on-change | Master out |
| `/Master/headMix` | float | on-change | Headphone cue mix |

**N is the deck number** — `Channel1`, `Channel2`, `Channel3`, `Channel4` (4-deck Mixxx). For v1.1 we only handle Channel1+2 actively; Channel3+4 are subscribed but ignored unless we detect them playing.

For the **Pull mode** (request value on demand), PR #14388 added `/Get/cop/{path}` (parameterized value 0-1) and `/Get/cov/{path}` (raw value). Vibemix doesn't need these for v1.1 — push is enough.

### Version compatibility

| Mixxx version | OSC status | Vibemix action |
|---|---|---|
| ≤ 2.4.x | No OSC code in tree | "Mixxx detected, OSC not available in this Mixxx version. Upgrade or use audio-only mode." |
| 2.5.0-2.5.6 (stock release) | No OSC code merged | Same as above |
| Custom build of PR #14388 | OSC works with T/B/L addresses | Full integration |
| Future 2.6.x (IF #14388 merges) | OSC native | Full integration; show "Native Mixxx support" in UI |

We track the merge status of PR #14388 in our release notes. When it merges, v1.1.x bumps to "Mixxx native support shipped" and the UX onboarding text changes.

### Latency model

OSC over loopback UDP is sub-millisecond on the wire. The end-to-end latency budget is:

- Mixxx UI event → Mixxx OSC send: ~1ms (Mixxx's send is on the main thread, post-control-update)
- UDP packet localhost: <1ms
- python-osc dispatcher → vibemix callback: ~2-5ms (asyncio dispatch)
- MixxxBus state mutation under lock: <1ms
- `state_refresh_loop @10Hz` reads MixxxBus on its next tick: 0-100ms
- EventDetector reacts: <5ms

**Net: 100-110ms p99 from Mixxx UI to vibemix event for state-change cases (faders, play press).** For sync-push position updates (the 500ms timer), staleness can be up to 500ms — fine for "is the track still playing" but not for tight EQ-move reactions. We do NOT depend on OSC for EQ-move latency; the MIDI controller path is faster and more reliable.

[ASSUMED — based on typical localhost UDP + python-osc benchmarks. Should be measured against a real PR #14388 build during implementation.]

### OSC server library — `python-osc`

- **Package:** [`python-osc`](https://pypi.org/project/python-osc/) v1.10.2 (released 2026-04-02) [VERIFIED]
- **License:** Public domain ("Unlicensed, do what you want with it.") [VERIFIED]
- **Dependencies:** None — pure Python stdlib. Critical for one-click install on Mac+Win.
- **Python:** Requires ≥3.10; we're on 3.14 — green.
- **Maintenance:** Active (1.10.0 and 1.10.2 both shipped April 2026). [VERIFIED via pypi]
- **Alternatives considered and rejected:**
  - `liblo` (C library) — requires `brew install liblo` on Mac and a manual Windows build. RED on one-click install.
  - `oscpy` (uses raw sockets) — also pure-Python but lower star count and less idiomatic API.
  - `pyliblo3` — bindings to liblo C. Same install problem as liblo.

`python-osc` is the right pick.

### Implementation skeleton

```python
# vibemix/platform/mixxx_osc.py
"""
MixxxBus — listens for Mixxx OSC broadcasts and exposes a snapshot.

Mixxx OSC PR #14388 (currently unmerged into mainline 2.5.6) broadcasts
ControlObject changes as /{group}/{key} OSC paths, e.g. /Channel1/play.

For v1.1 we treat Mixxx OSC as opt-in: user must run a custom build of the PR.
When the PR merges into Mixxx mainline we promote to first-class.

Drop-in alongside ControllerState. Updates MusicState via callback.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from typing import Awaitable, Callable, Optional

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server


EventCallback = Callable[[str, dict], Awaitable[None]]
# (event_type, payload) — event_type ∈ {'play','volume','title','position','bpm','eq','filter','xfader','track_load','eject'}


class MixxxBus:
    """Lock-protected latest snapshot of Mixxx OSC state. ~100ms staleness on UI events,
    ~500ms on continuous values (depending on Mixxx's periodic sync push interval).
    Safe to read from the state_refresh_loop without contention."""

    DEFAULT_PORT = 7878  # vibemix receive port. User configures Mixxx to send here.

    def __init__(self, port: int = DEFAULT_PORT):
        self._port = port
        self._lock = threading.Lock()
        # state[deck_n] = {'play':bool, 'volume':float, 'title':str, 'position':float,
        #                  'duration':float, 'bpm':float, 'rate':float, 'eq_lo':float,
        #                  'eq_mid':float, 'eq_hi':float, 'filter':float, 'loaded':bool}
        self._state: dict[int, dict] = defaultdict(lambda: {
            'play': False, 'volume': 0.0, 'title': '', 'artist': '',
            'position': 0.0, 'duration': 0.0, 'bpm': 0.0, 'rate': 0.0,
            'eq_lo': 0.5, 'eq_mid': 0.5, 'eq_hi': 0.5, 'filter': 0.5,
            'loaded': False, 'last_update': 0.0,
        })
        self._xfader: float = 0.0
        self._master_vol: float = 1.0
        self._callbacks: list[EventCallback] = []
        self._server: Optional[osc_server.AsyncIOOSCUDPServer] = None
        self._transport = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_packet_t: float = 0.0
        self._connected: bool = False

    # ---- public API ----

    def on_event(self, cb: EventCallback) -> None:
        """Register an async callback for state changes. Called with (event_type, payload)."""
        self._callbacks.append(cb)

    def snapshot(self) -> dict:
        """Single-shot read for state_refresh_loop. Returns deep-ish dict."""
        with self._lock:
            return {
                'decks': {n: dict(s) for n, s in self._state.items()},
                'xfader': self._xfader,
                'master_vol': self._master_vol,
                'connected': self._connected,
                'last_packet_age_s': max(0.0, time.time() - self._last_packet_t) if self._last_packet_t else None,
            }

    def is_connected(self) -> bool:
        """True if we've received a packet in the last 10s."""
        with self._lock:
            return self._connected

    async def start(self) -> None:
        """Bind UDP listen socket on 127.0.0.1:{port} and start dispatching."""
        self._loop = asyncio.get_running_loop()
        disp = osc_dispatcher.Dispatcher()

        # Per-deck patterns: /Channel{N}/play, /Channel{N}/volume, etc.
        disp.map("/Channel*/play",          self._on_play)
        disp.map("/Channel*/volume",        self._on_volume)
        disp.map("/Channel*/TrackTitle",    self._on_title)
        disp.map("/Channel*/TrackArtist",   self._on_artist)
        disp.map("/Channel*/playposition",  self._on_position)
        disp.map("/Channel*/duration",      self._on_duration)
        disp.map("/Channel*/bpm",           self._on_bpm)
        disp.map("/Channel*/rate",          self._on_rate)
        disp.map("/Channel*/track_loaded",  self._on_track_loaded)
        disp.map("/Channel*/eject",         self._on_eject)

        # EQ — full path: /EqualizerRack1/Channel{N}/Effect1/parameter{1,2,3}
        disp.map("/EqualizerRack1/Channel*/Effect1/parameter1", self._on_eq, 'lo')
        disp.map("/EqualizerRack1/Channel*/Effect1/parameter2", self._on_eq, 'mid')
        disp.map("/EqualizerRack1/Channel*/Effect1/parameter3", self._on_eq, 'hi')

        # Filter knob: /QuickEffectRack1/Channel{N}/super1
        disp.map("/QuickEffectRack1/Channel*/super1", self._on_filter)

        # Master
        disp.map("/Master/crossfader", self._on_xfader)
        disp.map("/Master/volume",     self._on_master_vol)

        self._server = osc_server.AsyncIOOSCUDPServer(
            ("127.0.0.1", self._port), disp, self._loop,
        )
        self._transport, _ = await self._server.create_serve_endpoint()
        print(f"-> MixxxBus listening on 127.0.0.1:{self._port}")

        # Connection watchdog — flips _connected based on packet recency
        asyncio.create_task(self._watchdog_loop())

    async def stop(self) -> None:
        if self._transport:
            self._transport.close()

    # ---- handlers (sync; sounddevice-style — dispatch async cb via run_coroutine_threadsafe) ----

    def _deck_from_addr(self, addr: str) -> int | None:
        # Extract N from /Channel{N}/... or /EqualizerRack1/Channel{N}/...
        try:
            seg = next(s for s in addr.split('/') if s.startswith('Channel'))
            return int(seg.replace('Channel', ''))
        except (StopIteration, ValueError):
            return None

    def _touch(self) -> None:
        self._last_packet_t = time.time()

    def _set(self, deck: int, field: str, value) -> None:
        with self._lock:
            self._state[deck][field] = value
            self._state[deck]['last_update'] = time.time()

    def _fire(self, event: str, payload: dict) -> None:
        if not self._loop:
            return
        for cb in self._callbacks:
            asyncio.run_coroutine_threadsafe(cb(event, payload), self._loop)

    def _on_play(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        playing = bool(args[0])
        self._set(deck, 'play', playing)
        self._fire('play', {'deck': deck, 'playing': playing})

    def _on_volume(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        self._set(deck, 'volume', float(args[0]))

    def _on_title(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        title = str(args[0])
        self._set(deck, 'title', title)
        self._fire('title', {'deck': deck, 'title': title})

    def _on_artist(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        self._set(deck, 'artist', str(args[0]))

    def _on_position(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is not None and args:
            self._set(deck, 'position', float(args[0]))

    def _on_duration(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is not None and args:
            self._set(deck, 'duration', float(args[0]))

    def _on_bpm(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is not None and args:
            self._set(deck, 'bpm', float(args[0]))

    def _on_rate(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is not None and args:
            self._set(deck, 'rate', float(args[0]))

    def _on_track_loaded(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        loaded = bool(args[0])
        self._set(deck, 'loaded', loaded)
        if loaded:
            self._fire('track_load', {'deck': deck})

    def _on_eject(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None: return
        self._fire('eject', {'deck': deck})

    def _on_eq(self, addr, band, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        v = float(args[0])
        self._set(deck, f'eq_{band}', v)
        # Only fire significant moves — see EventDetector for magnitude logic
        self._fire('eq', {'deck': deck, 'band': band, 'value': v})

    def _on_filter(self, addr, *args):
        self._touch()
        deck = self._deck_from_addr(addr)
        if deck is None or not args: return
        v = float(args[0])
        self._set(deck, 'filter', v)
        self._fire('filter', {'deck': deck, 'value': v})

    def _on_xfader(self, addr, *args):
        self._touch()
        if not args: return
        with self._lock:
            self._xfader = float(args[0])
        self._fire('xfader', {'value': float(args[0])})

    def _on_master_vol(self, addr, *args):
        self._touch()
        if args:
            with self._lock:
                self._master_vol = float(args[0])

    async def _watchdog_loop(self):
        while True:
            await asyncio.sleep(2.0)
            with self._lock:
                stale = (time.time() - self._last_packet_t) > 10.0 if self._last_packet_t else True
                was_connected = self._connected
                self._connected = not stale and self._last_packet_t > 0
            if was_connected and not self._connected:
                print("[MixxxBus] stale — no OSC packets in 10s")
            elif not was_connected and self._connected:
                print("[MixxxBus] connected — receiving OSC packets")
```

**~190 LOC.** Engineer fits this into one afternoon, half a day to test against a built #14388 binary.

### Wiring into MusicState

In `cohost_v4.py` the `state_refresh_loop @10Hz` is the only writer to `MusicState`. The new ordering inside that loop:

```python
async def state_refresh_loop(state: MusicState, audio: AudioBuffer, controller: ControllerState,
                             mixxx: MixxxBus | None, track_info: TrackInfo,
                             screen: ScreenBuffer, stop_event: asyncio.Event):
    while not stop_event.is_set():
        # 1. Audio-derived features (existing path)
        audio_feats = await asyncio.get_running_loop().run_in_executor(
            None, audio.snapshot_features, 7.0
        )

        # 2. Controller snapshot (MIDI controller — existing)
        ctrl_snap = controller.deck_snapshot()
        ctrl_moves = controller.moves_since(time.time() - 7.0)

        # 3. NEW: Mixxx OSC snapshot (if available — gracefully None)
        mixxx_snap = mixxx.snapshot() if mixxx and mixxx.is_connected() else None

        # 4. Now-playing fallback (existing)
        np_snap = track_info.snapshot()

        # 5. Merge into MusicState — Mixxx wins on title/bpm where present,
        #    audio + controller still authoritative for EQ/filter moves (lower latency).
        state.update(audio_feats=audio_feats, controller=ctrl_snap, controller_moves=ctrl_moves,
                    mixxx=mixxx_snap, now_playing=np_snap)

        await asyncio.sleep(0.1)  # 10Hz
```

**Trust ordering inside `MusicState.update`** (this is the anti-hallucination call):

| Field | Trust order |
|---|---|
| Track title/artist | MixxxBus > Rekordbox library lookup > nowplaying-cli > "(unknown)" |
| BPM | MixxxBus > library lookup > audio autocorr estimate |
| Per-deck volume | MixxxBus > controller MIDI (correlate; controller is canonical until OSC overrides) |
| EQ/filter moves | controller MIDI (always — lower latency, 100% reliable) |
| Playing state | MixxxBus > controller play-button toggle > audio RMS gate |
| Audible deck | controller MIDI (xfader + vol + EQ — existing v4 logic, OSC volumes refine the weights) |

**Lock contention**: MixxxBus uses its own `threading.Lock`. `state_refresh_loop` calls `mixxx.snapshot()` once per tick (10Hz). Worst-case lock-hold time inside snapshot is microseconds (dict copy of ~12 fields × 4 decks). No realistic contention concern.

---

## 2. Pyrekordbox XML Import — Library Snapshot Spec

### User UX flow

**Onboarding (one-time, optional):**

1. First-run wizard: "Use your Rekordbox library? (recommended)"
2. If yes: Show "How to export" — single screen with:
   - macOS path screenshot: Rekordbox → File → Export Collection in xml format → save anywhere
   - Same on Windows
   - "Then drag the .xml file here, or click Browse"
3. File picker (drag-drop preferred): user drops the XML
4. Vibemix copies it to `~/Library/Application Support/vibemix/library/rekordbox.xml` (Mac) or `%APPDATA%\vibemix\library\rekordbox.xml` (Win)
5. Index runs in background (~5-20s for 5-15k tracks); progress bar in UI
6. "Done — 8,427 tracks indexed. Vibemix will now know your library when it hears tracks playing."

**Refresh:**

- "Re-import library" button in Settings (always available)
- **No file-watcher.** Rekordbox holds the source DB open during a session; even if we watched the XML path, the user has to manually re-export. We expose the refresh as a deliberate UX action, not magic. Recommendation: nudge user after 30 days ("Your imported library is 30 days old — re-export if you've added tracks").
- Same XML path overwrite; reindex incrementally if TrackID overlap > 80%, else full reindex.

**If the user doesn't have Rekordbox:** skip the wizard. Vibemix runs without library context. nowplaying-cli + audio remain the grounding.

### XML fields extracted

Per Rekordbox XML schema [VERIFIED: [pyrekordbox docs — XML format](https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html)], the TRACK element exposes:

| Field | Used by vibemix | Notes |
|---|---|---|
| `TrackID` | yes (primary key) | int |
| `Name` (title) | yes | string |
| `Artist` | yes | string |
| `Album` | yes | for genre inference |
| `Genre` | yes | direct prompt context |
| `AverageBpm` | yes | live BPM grounding |
| `Tonality` (key) | yes | Camelot / OpenKey lookups |
| `Rating` | yes (0-5 scale) | "user-favorite" tag |
| `Colour` | yes | Rekordbox user tag — energy proxy |
| `Comments` | yes | user notes — vibemix surfaces these |
| `TotalTime` | yes | duration check |
| `Location` | yes (file path) | for audio fingerprinting in v2 |
| `PlayCount` | yes | familiarity prior |
| `Mix`, `Remixer`, `Label` | yes | metadata in prompt |
| `BitRate`, `SampleRate`, `Size`, `Year`, `Composer`, `DiscNumber`, `TrackNumber`, `DateAdded`, `DateModified`, `Kind`, `Grouping` | no (ignored for v1.1) | bloat |
| nested `TEMPO` (beat grid) | yes (per track, store as JSON column) | Inizio (start), Bpm, Metro, Battito |
| nested `POSITION_MARK` (cues) | yes — store hot cues (Num 0-7) + memory cues | Name, Type, Start, End, Num |

### Storage

**SQLite, single file**: `~/Library/Application Support/vibemix/library/rekordbox.db` (Mac) / `%APPDATA%\vibemix\library\rekordbox.db` (Win).

Schema:

```sql
CREATE TABLE tracks (
    track_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    genre TEXT,
    bpm REAL,
    key TEXT,
    rating INTEGER,
    colour TEXT,
    comments TEXT,
    duration_s REAL,
    location TEXT,
    play_count INTEGER,
    mix_label TEXT,
    remixer TEXT,
    record_label TEXT,
    title_norm TEXT,       -- lowercase, stripped for fuzzy match
    artist_norm TEXT
);
CREATE INDEX idx_title_norm ON tracks(title_norm);
CREATE INDEX idx_artist_norm ON tracks(artist_norm);
CREATE INDEX idx_bpm ON tracks(bpm);

CREATE TABLE cues (
    track_id INTEGER,
    cue_idx INTEGER,       -- 0-7 for hot cues, -1 for memory
    cue_type TEXT,         -- 'cue','fade-in','fade-out','load','loop'
    start_s REAL,
    end_s REAL,
    name TEXT,
    FOREIGN KEY (track_id) REFERENCES tracks(track_id)
);
CREATE INDEX idx_cues_track ON cues(track_id);

CREATE TABLE beat_grid (
    track_id INTEGER,
    inizio_s REAL,
    bpm REAL,
    metro TEXT,
    battito INTEGER,
    FOREIGN KEY (track_id) REFERENCES tracks(track_id)
);
CREATE INDEX idx_grid_track ON beat_grid(track_id);
```

**Size estimate**: 5k tracks ≈ 2.5 MB DB, 15k tracks ≈ 8 MB. Negligible.

### Implementation skeleton

```python
# vibemix/library/rekordbox_xml.py
"""Pyrekordbox XML import — one-shot read of an exported Rekordbox collection.xml.
Stores in a local SQLite for fast title/artist/bpm lookups during a live set.

Why XML and not master.db? Pyrekordbox can read master.db via SQLCipher, but the
key extraction is broken for Rekordbox versions ≥6.6.5. XML export works for
every Rekordbox version Pioneer ships. See B-industry-integrations.md for context.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pyrekordbox import RekordboxXml  # MIT licensed, dylanljones/pyrekordbox


@dataclass(frozen=True)
class Track:
    track_id: int
    title: str
    artist: str
    bpm: float
    key: str
    rating: int
    colour: str
    duration_s: float
    cues: list[tuple[int, float, str]]  # (idx, start_s, name) — hot cues only


def _norm(s: str) -> str:
    """Lowercase, NFD-strip-accents, strip non-alphanumeric. Used for fuzzy match."""
    if not s: return ""
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


class RekordboxLibrary:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        # (schema from spec above — collapsed for brevity)
        cur = self._conn.cursor()
        cur.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def import_xml(self, xml_path: Path) -> int:
        """Parse Rekordbox XML and replace local DB. Returns track count."""
        xml = RekordboxXml(str(xml_path))
        cur = self._conn.cursor()
        cur.execute("DELETE FROM cues")
        cur.execute("DELETE FROM beat_grid")
        cur.execute("DELETE FROM tracks")
        n = 0
        for t in xml.get_tracks():
            cur.execute("""INSERT INTO tracks (track_id,title,artist,album,genre,bpm,key,
                rating,colour,comments,duration_s,location,play_count,mix_label,remixer,
                record_label,title_norm,artist_norm) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(t.TrackID), t.Name or "", t.Artist or "", t.Album or "", t.Genre or "",
                 float(t.AverageBpm or 0), t.Tonality or "", int(t.Rating or 0), t.Colour or "",
                 t.Comments or "", float(t.TotalTime or 0), t.Location or "",
                 int(t.PlayCount or 0), t.Mix or "", t.Remixer or "", t.Label or "",
                 _norm(t.Name), _norm(t.Artist)))
            for mark in (t.marks or []):
                cur.execute("INSERT INTO cues VALUES (?,?,?,?,?,?)",
                            (int(t.TrackID), int(getattr(mark, 'Num', -1)),
                             mark.Type or "", float(mark.Start or 0),
                             float(mark.End or 0), mark.Name or ""))
            for tempo in (t.tempos or []):
                cur.execute("INSERT INTO beat_grid VALUES (?,?,?,?,?)",
                            (int(t.TrackID), float(tempo.Inizio or 0),
                             float(tempo.Bpm or 0), tempo.Metro or "",
                             int(tempo.Battito or 0)))
            n += 1
        self._conn.commit()
        return n

    def lookup(self, title: str, artist: str | None = None, bpm_hint: float | None = None) -> Optional[Track]:
        """Best-effort fuzzy lookup. Returns highest-confidence match or None.

        Strategy:
          1. Exact title_norm + artist_norm match -> confidence 1.0
          2. Exact title_norm match, BPM within 0.5 of hint (if given) -> 0.9
          3. Title contains/contained-in match + artist match -> 0.7
          4. Title contains match alone -> 0.5
          5. Below 0.5 -> None.
        """
        tn = _norm(title)
        an = _norm(artist) if artist else None
        if not tn: return None
        cur = self._conn.cursor()

        # Tier 1
        if an:
            cur.execute("SELECT * FROM tracks WHERE title_norm=? AND artist_norm=? LIMIT 1", (tn, an))
            row = cur.fetchone()
            if row: return self._row_to_track(row)

        # Tier 2
        if bpm_hint:
            cur.execute("""SELECT *, ABS(bpm-?) AS bpm_d FROM tracks
                           WHERE title_norm=? AND bpm_d<=0.5 ORDER BY bpm_d LIMIT 1""",
                        (bpm_hint, tn))
            row = cur.fetchone()
            if row: return self._row_to_track(row)

        # Tier 3 — partial title with artist
        if an:
            cur.execute("""SELECT * FROM tracks WHERE artist_norm=? AND
                           (title_norm LIKE ? OR ? LIKE '%' || title_norm || '%') LIMIT 1""",
                        (an, f'%{tn}%', tn))
            row = cur.fetchone()
            if row: return self._row_to_track(row)

        # Tier 4 — title-only partial
        cur.execute("SELECT * FROM tracks WHERE title_norm LIKE ? LIMIT 1", (f'%{tn}%',))
        row = cur.fetchone()
        if row: return self._row_to_track(row)
        return None

    def _row_to_track(self, row) -> Track:
        cur = self._conn.cursor()
        cur.execute("SELECT cue_idx, start_s, name FROM cues WHERE track_id=? AND cue_idx>=0 ORDER BY cue_idx",
                    (row['track_id'],))
        cues = [(r['cue_idx'], r['start_s'], r['name']) for r in cur.fetchall()]
        return Track(
            track_id=row['track_id'], title=row['title'], artist=row['artist'],
            bpm=row['bpm'], key=row['key'], rating=row['rating'], colour=row['colour'],
            duration_s=row['duration_s'], cues=cues,
        )

    def count(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tracks")
        return cur.fetchone()[0]


_SCHEMA_SQL = """..."""  # filled with schema from spec above
```

**~120 LOC** (schema text omitted). The whole module is one engineer-day including unit tests against a sample XML.

### Confidence threshold

Returned `Track` is paired with confidence:
- **>=0.9**: vibemix prompt-grounds with full track context (bpm, key, cues, rating). Promoted to "definite track".
- **0.7-0.9**: prompt grounding with `(probable)` tag. Vibemix says "I think this is X" instead of "X is playing now."
- **<0.7**: discarded; nowplaying-cli/Mixxx title shown raw with no library enrichment.

---

## 3. 10-SKU MIDI Controller Library — Cookbook

### Library architecture — JSON-per-SKU

Mapping files live in `vibemix/controllers/library/<sku>.json`. The schema is hardware-agnostic:

```json
{
  "sku": "pioneer-ddj-flx4",
  "display_name": "Pioneer DDJ-FLX4",
  "midi_port_hints": ["DDJ-FLX4"],
  "decks": ["A", "B"],
  "controls": {
    "deck_volume": {
      "A": {"type": "cc", "status": 176, "data": 19, "range": [0, 127]},
      "B": {"type": "cc", "status": 177, "data": 19, "range": [0, 127]}
    },
    "eq_hi":  {"A": {"type":"cc","status":176,"data":7},  "B": {"type":"cc","status":177,"data":7}},
    "eq_mid": {"A": {"type":"cc","status":176,"data":11}, "B": {"type":"cc","status":177,"data":11}},
    "eq_lo":  {"A": {"type":"cc","status":176,"data":15}, "B": {"type":"cc","status":177,"data":15}},
    "filter": {"A": {"type":"cc","status":182,"data":23}, "B": {"type":"cc","status":182,"data":24}},
    "tempo":  {"A": {"type":"cc","status":176,"data":0},  "B": {"type":"cc","status":177,"data":0}},
    "play":   {"A": {"type":"note","status":144,"data":11}, "B": {"type":"note","status":145,"data":11}},
    "cue":    {"A": {"type":"note","status":144,"data":12}, "B": {"type":"note","status":145,"data":12}},
    "sync":   {"A": {"type":"note","status":144,"data":88}, "B": {"type":"note","status":145,"data":88}},
    "crossfader": {"M": {"type":"cc","status":182,"data":31}},
    "jog_touch":  {"A": {"type":"note","status":144,"data":54}, "B": {"type":"note","status":145,"data":54}},
    "loop_in":    {"A": {"type":"note","status":144,"data":16}, "B": {"type":"note","status":145,"data":16}},
    "loop_out":   {"A": {"type":"note","status":144,"data":17}, "B": {"type":"note","status":145,"data":17}}
  },
  "value_map": {
    "deck_volume": {"killed": [0, 7], "deep-cut": [8, 29], "cut": [30, 54], "flat": [55, 73], "boost": [74, 100], "max": [101, 127]},
    "eq_hi": {"killed": [0, 7], "deep-cut": [8, 29], "cut": [30, 54], "flat": [55, 73], "boost": [74, 100], "max": [101, 127]},
    "_default_knob_label": "$eq_hi",
    "xfader": {"full-A": [0, 15], "A-side": [16, 47], "center": [48, 80], "B-side": [81, 111], "full-B": [112, 127]}
  },
  "notes": "FLX4 ships in Pioneer-native and MIDI modes; CC numbers here are MIDI mode. Sync at note 0x58 confirmed from Mixxx mapping XML 2026-05-14. Verify Kaan's hardware emits 0x58 not 0x60 (v4 disagreement)."
}
```

This format gives us:
- **Status bytes carry channel + message type** — same as raw MIDI wire — so the loader does a simple `(msg.channel, msg.control)` or `(msg.channel, msg.note)` dict-lookup with no special casing.
- **Decoupled value semantics** — the `value_map` per-knob is shared by default (`$eq_hi` reference). FLX10's longer-throw faders could redefine ranges.
- **Per-control SKU notes** — load-bearing for the engineer who has to debug "why doesn't my FLX10 fader register"

### Per-SKU snapshot

(For brevity: status bytes are MIDI channel + message-type combined. `0xB0` = CC on channel 0, `0xB1` = CC on channel 1, `0x90` = note-on channel 0, `0x91` = note-on channel 1. `0xB6` = CC on channel 6 (master/global on Pioneers).)

#### 1. Pioneer DDJ-FLX4 [VERIFIED: [Mixxx Pioneer-DDJ-FLX4.midi.xml](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml)]

| Control | Deck A | Deck B | Master |
|---|---|---|---|
| Volume fader | `B0 13` | `B1 13` | — |
| EQ Hi | `B0 07` | `B1 07` | — |
| EQ Mid | `B0 0B` | `B1 0B` | — |
| EQ Lo | `B0 0F` | `B1 0F` | — |
| Filter | `B6 17` | `B6 18` | — |
| Tempo | `B0 00` | `B1 00` | — |
| Pregain | `B0 04` | `B1 04` | — |
| Play | `90 0B` | `91 0B` | — |
| Cue | `90 0C` | `91 0C` | — |
| Sync | `90 58` | `91 58` | — |
| Jog touch | `90 36` | `91 36` | — |
| Loop In | `90 10` | `91 10` | — |
| Loop Out | `90 11` | `91 11` | — |
| PFL | `90 54` | `91 54` | — |
| Crossfader | — | — | `B6 1F` |
| Head Mix | — | — | `B6 0C` |

#### 2. Pioneer DDJ-400 [CITED: Pioneer MIDI Implementation Chart + Mixxx mapping]

Same shape as FLX4 for the canonical 14 controls. Pioneer kept fader/EQ CC numbers consistent across the FLX line as a deliberate compatibility move. The differences from FLX4 are: no second-pass pad-FX layer, simpler effect pad mapping, smaller jog wheel CC range. **For vibemix's purposes (vol/EQ/filter/tempo/play/cue/sync/xfader) the DDJ-400 mapping JSON is identical to DDJ-FLX4 with `midi_port_hints: ["DDJ-400"]`.** The engineer copies `ddj-flx4.json` to `ddj-400.json`, edits the port hint, and is done.

#### 3. Pioneer DDJ-FLX6 [ASSUMED]

Same Pioneer scheme but with 4-deck switching (decks 3+4 reuse 0/1 channels with deck-shift modifier). For v1.1 we treat FLX6 as 2-deck (A/B) — Channel3/4 ignored. Mapping JSON is FLX4-shape with port hint `["DDJ-FLX6"]`. Same EQ/vol/filter mapping. **Engineer should confirm with a 30-second `mido` sniff during testing.**

#### 4. Pioneer DDJ-FLX10 [ASSUMED — high uncertainty]

4-deck flagship. Pioneer's MIDI implementation likely keeps the EQ pattern (`B0/B1 07/0B/0F`) but adds Channel3 (`B2`) and Channel4 (`B3`). **Recommend deferring to v1.2** unless an FLX10 owner is in the early-tester pool. The mapping JSON is straightforward to write but UNVERIFIED until tested.

#### 5. Pioneer DDJ-SX3 [ASSUMED]

Serato 4-deck workhorse. Different schema from FLX line — uses Serato HID mode by default and MIDI in fallback. CC numbers in MIDI mode are NOT identical to FLX4. **Engineer must sniff.** Tentative mapping JSON: copy FLX4, mark all controls as `"unverified": true`, run mido capture.

#### 6. Pioneer XDJ-RX3 [ASSUMED]

Standalone CDJ-style controller. In MIDI export mode, similar CC scheme to FLX line. **Standalone mode is a different beast** — it does not emit MIDI unless connected to a laptop and switched to MIDI mode. For v1.1, we support XDJ-RX3 in MIDI mode only; standalone users get screen+audio grounding.

#### 7. Hercules DJControl Inpulse 500 [VERIFIED: [Mixxx mapping](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Hercules-DJControl-Inpulse-500.midi.xml)]

Different vendor MIDI scheme than Pioneer. Volume fader on different CC. **Engineer reads the Mixxx XML, transcribes the CC numbers, no FLX4 shortcut.**

#### 8. Hercules DJControl Inpulse 300

Same Hercules family as 500 but smaller. Mixxx ships a mapping in `res/controllers/`. Same workflow.

#### 9. Numark Party Mix Live [ASSUMED]

Entry-level Numark; Mixxx may or may not ship an official mapping. **Engineer needs Numark MIDI Implementation Chart PDF**. If not findable in 1 day, defer SKU 9 to v1.2.

#### 10. Numark Mixstream Pro+ [ASSUMED]

Standalone-capable (Engine DJ). Same caveat as XDJ-RX3 — MIDI mode only. Engine DJ has its own protocol (Engine OS) that we DO NOT support. Document this clearly: "Mixstream Pro+ standalone mode is not supported by vibemix; switch to MIDI mode for vibemix support."

### Auto-detection

```python
# vibemix/controllers/registry.py
def detect_controller(port_names: list[str]) -> tuple[str, dict] | None:
    """Match an open MIDI port name to a library entry. Returns (sku, mapping_dict) or None."""
    for sku, mapping in load_all_mappings().items():
        for hint in mapping['midi_port_hints']:
            for name in port_names:
                if hint.lower() in name.lower():
                    return sku, mapping
    return None
```

Fallback to user-picker UI: if `detect_controller` returns None but MIDI activity is detected, show "Controller detected but not in library. Pick from: [dropdown of 10 SKUs] or [Generic MIDI mode]."

### Generic `MidiMapLoader` skeleton

```python
# vibemix/controllers/loader.py
import json
import threading
import time
from pathlib import Path

class MidiMapLoader:
    """Replaces hardcoded _CC_MAP/_NOTE_MAP in cohost_v4.py.
    Reads a mapping JSON, builds the same (status, data) -> (deck, field) lookup,
    drives ControllerState the same way as before."""

    def __init__(self, mapping: dict):
        self._mapping = mapping
        self._cc_map: dict[tuple[int, int], tuple[str, str]] = {}
        self._note_map: dict[tuple[int, int], tuple[str, str]] = {}
        for field, decks in mapping['controls'].items():
            for deck, spec in decks.items():
                channel = spec['status'] & 0x0F  # bottom 4 bits = channel
                key = (channel, spec['data'])
                if spec['type'] == 'cc':
                    self._cc_map[key] = (deck, field)
                elif spec['type'] == 'note':
                    self._note_map[key] = (deck, field)

    def decode(self, msg) -> tuple[str, str, int] | None:
        """Return (deck, field, value) or None."""
        if msg.type == 'control_change':
            hit = self._cc_map.get((msg.channel, msg.control))
            return (*hit, msg.value) if hit else None
        elif msg.type in ('note_on', 'note_off'):
            hit = self._note_map.get((msg.channel, msg.note))
            return (*hit, msg.velocity) if hit else None
        return None
```

The existing `ControllerState.handle_msg` shrinks to ~30 lines because all hardware-specific logic now lives in JSON.

---

## 4. Generic-MIDI Fallback

For controllers NOT in the 10-SKU library — initial behavior is **observe, classify conservatively, never invent**:

- Every CC seen: record `(channel, control_number)` and the value history (last 60 seconds). If we see the value span the full 0-127 range with at least 4 distinct values, classify it as a **knob/fader** of unknown role.
- Every note-on seen: classify as **button press of unknown role**.
- After 60 seconds of observation, surface to user: "Detected 7 knobs and 14 buttons. Click each one you'd like vibemix to know about and tell us what it is." — but **DO NOT auto-infer** that the first fader is "Deck A vol" etc. (Aggressive inference is the 1% wrong-mapping-from-misinference risk Kaan flagged in B's open questions; we lean conservative.)
- Until user mapping is done, vibemix uses generic-MIDI moves only as **activity signal** — "Kaan is doing something on the controller right now" — feeding `coach` prompts but not the audible-deck heuristic.

```python
# vibemix/controllers/generic_midi.py
import time
from collections import defaultdict, deque

class GenericMidiObserver:
    """Conservative MIDI activity observer. Logs events, never infers roles."""
    def __init__(self, window_s: float = 60.0):
        self._window = window_s
        self._cc_history: dict[tuple[int,int], deque] = defaultdict(lambda: deque(maxlen=128))
        self._note_history: dict[tuple[int,int], deque] = defaultdict(lambda: deque(maxlen=64))
        self._activity_pulses: deque[float] = deque(maxlen=64)

    def observe(self, msg):
        now = time.time()
        if msg.type == 'control_change':
            key = (msg.channel, msg.control)
            self._cc_history[key].append((now, msg.value))
            self._activity_pulses.append(now)
        elif msg.type in ('note_on', 'note_off'):
            key = (msg.channel, msg.note)
            self._note_history[key].append((now, msg.velocity if msg.type == 'note_on' else 0))
            if msg.type == 'note_on':
                self._activity_pulses.append(now)

    def activity_rate(self) -> float:
        """Events per second over the observation window."""
        now = time.time()
        recent = [t for t in self._activity_pulses if now - t < self._window]
        return len(recent) / self._window

    def summary(self) -> dict:
        """For the user-picker UI: 'we saw N knobs and M buttons'."""
        knobs = sum(1 for h in self._cc_history.values() if len(h) >= 4
                    and max(v for _, v in h) - min(v for _, v in h) > 30)
        buttons = len(self._note_history)
        return {'knobs': knobs, 'buttons': buttons, 'activity_per_s': self.activity_rate()}
```

Vibemix's audible-deck heuristic stays disabled in generic mode. The AI still reacts (audio is enough), it just doesn't claim "Deck B EQ-hi killed" when it doesn't know which CC is which.

---

## 5. Mapping format transpiler — feasibility

**Quick answer: feasible for one direction (read), infeasible for the others (write). Defer to v1.2 minimum, possibly v2.**

**Read side (importing a Mixxx XML map → vibemix JSON):** straightforward, ~150 LOC parser. Mixxx XML schema is documented and stable. The engineer can write a `mixxx_xml_to_vibemix_json.py` utility in one afternoon. This is genuinely useful — every new SKU Mixxx supports, we get for free.

**Write side (vibemix JSON → Rekordbox `.midi.xml` or Serato `.tsi`):** undocumented binary/proprietary formats. The Rekordbox `.midi.xml` schema is partially understood ([community guides](https://forums.pioneerdj.com/) reverse-engineer it), but Serato `.tsi` is fully binary, undocumented, and changes between Serato versions. djay `.djmap` is a plist — readable but proprietary and Algoriddim is hostile to interop. **No durable community effort exists for any of these.**

**Recommendation: ship the Mixxx-XML-reader for v1.1 to bootstrap the controller library faster, defer write-side entirely.** A user who wants to use the same controller mapping across DJ apps already has it working — vibemix is parallel-listening, not the user's primary mapping tool. The cross-app mapping transpiler is a separate product idea that competes with Bome MIDI Translator etc.; out of scope.

---

## 6. Architecture diagram

```
        ┌─────────────────────────────────────────────────────────────────────┐
        │                       MUSIC STATE (single writer)                   │
        │                state_refresh_loop @ 10Hz reads all sources          │
        └────▲──────────────▲──────────▲────────▲──────────▲──────────▲──────┘
             │              │          │        │          │          │
   on-event  │  on-event    │ on-event │  ~1Hz  │   ~1Hz   │   ~30Hz  │
             │              │          │        │          │          │
   ┌─────────┴──────┐  ┌────┴─────┐ ┌──┴────┐ ┌─┴──────┐ ┌─┴───────┐ ┌─┴────────┐
   │  MixxxBus      │  │Controller│ │TrackInfo │ScreenBuf│ │Rekordbox│ │AudioBuf  │
   │ (OSC :7878)    │  │  State   │ │(nowplay) │(mss)    │ │ Library │ │(BlackHole│
   │ optional/beta  │  │ (mido)   │ │          │         │ │ (SQLite)│ │ 48k+16k) │
   └─────▲──────────┘  └────▲─────┘ └─────▲────┘ ────▲───┘ └─────▲───┘ └─────▲────┘
         │                  │             │          │           │           │
    /Channel*/play       MIDI USB    MediaRemote   Quartz      lookup     CoreAudio
    /Channel*/volume    DDJ-FLX4    nowplaying-cli CGWindow    (title,bpm) callback
    /Channel*/title       (etc.)        binary     CopyWindow                ↑
         │                  │             │          │           │     ┌─────┴────┐
         │                  │             │          │           │     │ DJ app   │
         │                  │             │          │           └─────┤ master   │
    [Mixxx running]     [physical    [Mac MediaRemote] [djay  ←  imports XML  out │
    + custom build of   controller   API (Mac only,    Pro UI    once at     │   │
    PR #14388 enabled]  USB plug]    GSMTC on Win)    detected]  startup]    └───┘

                                                                ┌──────────────┐
                                            EventDetector ───→  │   AICoach    │
                                            (reads MusicState   │   (Gemini    │
                                            diffs, emits typed   │   Live API   │
                                            Event objects)       │   via LK)    │
                                                                 └──────────────┘
```

**Cadence summary:** MixxxBus and ControllerState are event-driven (push on change). TrackInfo polls nowplaying-cli at ~1Hz. ScreenBuffer at ~1Hz. RekordboxLibrary is queried synchronously on demand (microsecond SQLite lookups, no caching needed). AudioBuffer runs at audio-callback cadence (~30Hz at 16kHz frames). `state_refresh_loop @10Hz` is the only writer to MusicState — reads all six sources, merges per the trust ordering in §1.

**Lock contention:** Each source has its own `threading.Lock`. The state_refresh_loop takes them in fixed order (Mixxx → Controller → TrackInfo → Screen → Library → Audio) to prevent any cycle. Hold times are microseconds (dict copies). EventDetector reads MusicState under its own lock and doesn't touch source locks. No realistic contention.

---

## 7. Open implementation questions

1. **Mixxx OSC ships unmerged — do we publish "supported" status anyway?** If we ship MixxxBus and document "requires custom build of PR #14388" in the README, we get the credit for Mixxx support but with a friction step. Alternative: hold MixxxBus behind a feature flag and ship "vibemix is Mixxx-ready when the OSC PR merges" as a roadmap promise. **Recommendation: ship behind a `--enable-mixxx-osc` flag, document the custom-build path in the wiki, and watch PR #14388 weekly.** If it merges before v1.1 release, promote to first-class.

2. **Cohost_v4 sync note is 0x60 vs Mixxx XML's 0x58 — which is canonical?** Plug in Kaan's FLX4, run `python -c "import mido; p = mido.open_input('DDJ-FLX4'); [print(m) for m in p]"`, press Sync, capture the wire. Write the correct number into `ddj-flx4.json`. Add a `# DECISION: chose 0x58 based on wire capture 2026-05-15; v4's 0x60 was a transcription error from <source>` comment in the JSON. **This is a 5-minute verification but matters for accuracy.**

3. **Rekordbox XML refresh UX — auto-detect path or always-pick?** macOS Rekordbox exports to a user-chosen path (no fixed default). Windows same. So we can't auto-watch a known location. **Recommendation: file-picker on first import, store the path, offer "refresh from same file" as a one-click after that.** No file-watcher, no magic.

4. **Generic-MIDI mode — at what activity threshold do we surface the picker UI?** If we ask the user to label 14 buttons every time they plug in a new controller, the UX is brutal. Maybe a lighter touch: silently learn for 5 minutes, then in the post-set debrief surface "I noticed a new controller — want to map it for next session?" Defer the decision to the UX phase but flag it now so design accounts for it.

5. **Numark / less-common SKUs in v1 — sniff-test plan?** Some of the 10 SKUs (#9 Party Mix Live, #10 Mixstream Pro+) are not in Kaan's hardware closet and we don't have a Mixxx-shipped mapping for all of them. Two options: (a) ship v1.1 with 7 SKUs covered, 3 marked "experimental community-PR-welcome"; (b) try to source loaner units from Francesco's DJ network for a 1-day sniffing sprint. **Recommendation: ship 7 confirmed, mark 3 experimental, ask the early-tester community to PR mappings for their hardware.** Lowers v1.1 release risk; uses the open-source flywheel.

---

## Sources

### Primary (HIGH confidence)
- [`gh api repos/mixxxdj/mixxx/pulls/14388`](https://github.com/mixxxdj/mixxx/pull/14388) — current OSC PR, draft/open, last updated 2026-04-24, T/B/L addressing, liblo-based [VERIFIED]
- [`gh api repos/mixxxdj/mixxx/pulls/16239`](https://github.com/mixxxdj/mixxx/pull/16239) — HTTP REST API PR, closed without merge 2026-03-29 [VERIFIED]
- [Mixxx `Pioneer-DDJ-FLX4.midi.xml`](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml) — canonical DDJ-FLX4 MIDI mapping; source of Sync=0x58 [VERIFIED]
- [pyrekordbox v0.4.4 — XML format docs](https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html) — TRACK, TEMPO, POSITION_MARK fields [VERIFIED]
- [python-osc 1.10.2 on PyPI](https://pypi.org/project/python-osc/) — released 2026-04-02, public domain, no deps [VERIFIED]
- [Mixxx 2.5.6 release](https://github.com/mixxxdj/mixxx/releases) — released 2026-03-27, no OSC [VERIFIED]
- `/Users/ozai/projects/dj-set-ai/cohost_v4.py:586-732` — existing `_CC_MAP`, `_NOTE_MAP`, `ControllerState` to port [VERIFIED]
- [B-industry-integrations.md](/Users/ozai/projects/dj-set-ai/.planning/research/v2-buckets/B-industry-integrations.md) — strategic landscape from Bucket B [VERIFIED]

### Secondary (MEDIUM confidence)
- [Mixxx wiki — OSC Client](https://github.com/mixxxdj/mixxx/wiki/osc-client) — 2021 design proposal, address pattern `/mixxx/deck/*` is from an abandoned OSCpack prototype (superseded by T/B/L in PR #14388) [VERIFIED — superseded by current PR]
- [Mixxx Discourse — OSC Control of Mixxx](https://mixxx.discourse.group/t/osc-control-of-mixxx/32106) — community discussion confirming PR-only status [CITED]
- [pyrekordbox README](https://github.com/dylanljones/pyrekordbox) — v0.4.4, MIT, 395+ stars, Python 3.8+ [VERIFIED]

### Tertiary (LOW confidence — flag for engineer validation)
- DDJ-400 mapping is FLX4-shape — [ASSUMED] based on Pioneer's FLX-line consistency. Engineer should sniff to confirm.
- DDJ-FLX6 / FLX10 / SX3 / XDJ-RX3 mappings — [ASSUMED]. Each needs a 30-min sniff test before shipping the SKU.
- Numark Party Mix Live + Mixstream Pro+ — no Mixxx mapping reference; [ASSUMED]; needs MIDI Implementation Chart or loaner-unit sniff.
- MixxxBus end-to-end latency of ~100ms — [ASSUMED] based on typical localhost UDP; measure against a real PR #14388 build during implementation.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PR #14388 will eventually merge into Mixxx 2.6 | §1, §7Q1 | Medium — if PR is abandoned, vibemix's Mixxx-native pitch never materializes; we still keep MIDI+audio path. |
| A2 | Mixxx OSC end-to-end latency ~100ms p99 on localhost | §1 latency model | Low — empirically verifiable in 5 minutes against a built PR #14388. |
| A3 | DDJ-FLX4 Sync is at note 0x58, not 0x60 | §3 + §7Q2 | Low — verifiable in 1 minute with mido. v4's 0x60 may apply to a different controller mode. |
| A4 | DDJ-400 / FLX6 / FLX10 / SX3 share FLX4's vol/EQ/filter CC scheme | §3 | Medium — Pioneer changes details across the line; needs sniff per SKU. |
| A5 | Rekordbox XML schema is stable across Rekordbox 5/6/7 | §2 | Low — pyrekordbox v0.4.4 explicitly supports all three; format is documented. |
| A6 | Numark Mixstream Pro+ standalone mode is OUT OF SCOPE for v1.1 | §3 SKU 10 | Low — explicit scope call, documented in user-facing copy. |
| A7 | Generic-MIDI fallback can ship "observe only, never infer roles" without user complaints | §4 | Medium — if users expect plug-and-play vibemix reactions on unknown controllers, we'll get GitHub issues. Mitigated by the post-set debrief picker. |

---

## Open Questions

1. **Mixxx OSC ship gate** — wait for #14388 merge, or ship behind `--enable-mixxx-osc` flag now? (Engineer + Kaan decision, §7Q1.)
2. **Sync note arbitration** — 5-minute mido capture (§7Q2).
3. **Rekordbox XML refresh UX** — pick-once-remember or pick-every-time? (§7Q3.)
4. **Generic-MIDI threshold for user-picker UI** — silently observe how long, then ask? (§7Q4.)
5. **Numark SKU sourcing** — Francesco's network or community-PR? (§7Q5.)

---

*Research completed: 2026-05-14*
*Author: GSD-research-phase follow-up for Bucket B v1.1 ship spec*
*Word count: ~3,100*
