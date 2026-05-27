# Bucket B — Industry Integrations Research

**Researched:** 2026-05-13
**Scope:** First-class deck telemetry for Rekordbox, Mixxx, djay Pro, Serato, Traktor, VirtualDJ — replacing today's screen+nowplaying brittleness
**Audience:** vibemix v1.1 / v2.0 planning
**Confidence:** HIGH on Mixxx + pyrekordbox + MIDI fallback; HIGH on the "no public API" answers for Algoriddim/Serato/Traktor; MEDIUM on ProDJ Link (laptop-only mode is the live question)

---

## TL;DR (the three strategic calls)

1. **Mixxx is the only DJ platform that gives you a real-time read on deck state today, and it is unidirectional out-of-the-box.** Mixxx ships a built-in OSC *client* (it sends, doesn't receive) in 2.4 with broadcast every 500 ms and on UI changes. Per-deck title, BPM, position, volume, play state are all there. Zero install friction for Mixxx users. This is the lowest-risk highest-payoff v1.1 integration and should be the headline "vibemix supports Mixxx natively" story. [VERIFIED: [Mixxx wiki — Osc Client](https://github.com/mixxxdj/mixxx/wiki/osc-client)]

2. **Rekordbox/Serato/Traktor/VirtualDJ/djay Pro all have NO usable real-time deck telemetry that survives a "one-click install" constraint.** Pioneer's ProDJ Link is an Ethernet protocol designed for CDJ hardware; it does not broadcast usefully when Rekordbox runs solo on a laptop. Algoriddim explicitly refuses to ship an API. Serato's "API" is a Web Services SDK for streaming services and history file scraping. Traktor offers MIDI clock out (just BPM, no deck state). VirtualDJ has an OSC server but it's gated behind a paid Pro license. **For these platforms, vibemix's grounding stack stays: BlackHole/WASAPI audio + screen capture + MIDI controller in + Gemini Embedding 2.** [VERIFIED multiple sources, see per-platform sections]

3. **The MIDI controller is the real cross-platform telemetry layer — it's already 80% of the signal and it works the same across every DJ app.** A bedroom DJ in 2026 is overwhelmingly running a DDJ-FLX4 or a DDJ-400 (or one of ~5 close substitutes), all of which expose vol/EQ/filter/tempo/play/cue/sync over standard MIDI. The audible-deck detector + magnitude-aware EQ events vibemix already has in `cohost_v4.py` is the right architectural bet. Mixxx-via-OSC is a complement (lets us *also* read state on Mixxx specifically), not a replacement. **Don't chase per-platform integrations — invest in the MIDI library + audio grounding + Mixxx OSC, and the screen-capture path stays as the universal fallback.** [CITED: `cohost_v4.py:586-732` for the existing ControllerState/DDJ-FLX4 implementation]

---

## Per-platform deep dives

### Pioneer Rekordbox + ProDJ Link

**Protocol surface (what dysentery + beat-link expose):**
ProDJ Link is Pioneer's proprietary UDP-broadcast Ethernet protocol that CDJs, XDJs, and the TORAIZ SP-16/DJS-1000 use to exchange beat clock, position, track metadata, master-tempo handoff, and waveform snippets. Deep-Symmetry's [`dysentery`](https://github.com/Deep-Symmetry/dysentery) (247★, last release v0.2.2 on 2025-05-08) is the Clojure-language reverse-engineering project; [`beat-link`](https://github.com/Deep-Symmetry/beat-link) (132★) is the production Java library; [`beat-link-trigger`](https://github.com/Deep-Symmetry/beat-link-trigger) is the GUI; [`open-beat-control`](https://github.com/Deep-Symmetry/open-beat-control) (53★, last release v0.1.1 on 2020-12-28) is the OSC bridge for non-JVM environments. The Python port [`flesniak/python-prodj-link`](https://github.com/flesniak/python-prodj-link) (204★, requires PyQt5 + PyOpenGL + Construct + netifaces) is more dated and warns "this is still early beta software — it can freeze your players." [VERIFIED: GitHub fetches above]

**Data exposed (when you have CDJ hardware on the LAN):** track ID + title, BPM (master + per-deck), beat position (4/4 phase), play/pause state, tempo slider value, sync state, cue points, waveform data, and on CDJ-3000 only — phrase data (intro/build/drop/outro). Six-channel support was added at the end of 2020. [VERIFIED: dysentery README, [DJ Link packet analysis](https://djl-analysis.deepsymmetry.org/djl-analysis/packets.html)]

**The critical question — does it work for a laptop-only Rekordbox setup with NO CDJ hardware?** **NO.** Multiple confirmations across sources: ProDJ Link is the protocol *between Pioneer hardware on a network*. Rekordbox-the-software running solo on a laptop does **not** emit ProDJ Link broadcast packets in a useful way — when there's no CDJ on the network for it to talk to, the laptop is just a music player. [`python-prodj-link`'s README states explicitly: "You need to be on the same Ethernet network as the players. They are discovered using broadcasts."](https://github.com/flesniak/python-prodj-link) [VERIFIED] Pioneer's own forums confirm the same: ProDJ Link requires Pro-DJ-Link-compatible hardware (CDJ-2000/3000/XDJ-1000/XDJ-RX3/Opus-Quad) on the network. [CITED: [Pioneer rekordbox.com/en/support/link/](https://rekordbox.com/en/support/link/)]

**Firmware health:** CDJ-3000 firmware 3.20 (released April 2025) is the current stable. Firmware 3.30 (Oct 21, 2025) shipped, then Pioneer pulled distribution due to playlist display bugs; users were advised to downgrade. Dysentery/beat-link were updated through 2025 — no reported permanent breakages. DDJ-FLX10 is a controller, not a ProDJ Link participant; it doesn't enter this network. [CITED: [Pioneer firmware 3.20 release](https://www.pioneerdj.com/en/news/2025/cdj-3000-firmware-update-320/), [3.30 suspension notice](https://www.pioneerdj.com/en/news/2025/important-notice-cdj-3000-firmware-ver330/)]

**Vibemix integration shape:** Even *if* a vibemix user has CDJs at home (rare for the target market — bedroom DJs running a $300 controller), the install model would be: bundle the open-beat-control JAR, require Java 9+, expose 53★ unmaintained-since-2020 OSC bridge, configure LAN. This is brutal on the one-click install constraint (red rating). The Python path (python-prodj-link) is also moribund — last meaningful activity 2-3 years back.

**Tractability: LOW for v1, NO-GO for v2 unless we explicitly bet on a "vibemix Pro CDJ" SKU.** The data surface is gorgeous when present, but the user base that has the hardware is tiny relative to bedroom DJs, and the install friction is heavy. If we ever pursue it, the right play is to package the JVM bridge as an optional `~/.vibemix/extras/cdj/` add-on that activates only when a Pioneer device is detected on the LAN, ship dysentery/beat-link unmodified, and use OSC as the wire.

---

### Rekordbox local DB (pyrekordbox)

**The library:** [`dylanljones/pyrekordbox`](https://github.com/dylanljones/pyrekordbox) — 395★, last release v0.4.4 published 2025-08-17, Python 3.8+, tested on Windows and macOS. Supports Rekordbox 5.8.6 / 6.7.7 / 7.0.9. Apache 2.0 license. [VERIFIED: GitHub fetch]

**What it exposes from `master.db`:** Track records (ID, title, artist, album, bpm, key, energy/rating, length, file path), playlist tree, hot cues + memory cues, beat grid (beat positions in samples), waveform analysis (ANLZ files), MySettings (DJ preferences). It's the *full* Rekordbox collection on disk. [CITED: [pyrekordbox docs](https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html)]

**The encryption wall:** Rekordbox 6 and 7 store `master.db` as a SQLCipher-encrypted SQLite database. Pyrekordbox bundles `sqlcipher3-wheels` to handle this transparently *if* it can recover the key. **Starting with Rekordbox 6.6.5, Pioneer obfuscated the `app.asar` file that contained the key, breaking the automatic extraction.** If a vibemix user is on a Rekordbox version ≥6.6.5 (which is most users today) and pyrekordbox has no cached key from a previous version on that machine, pyrekordbox cannot open the database. There's a community workaround via [`liamcottle/pioneer-rekordbox-database-encryption`](https://github.com/liamcottle/pioneer-rekordbox-database-encryption) but it's a separate research project, not a drop-in fix. [VERIFIED: [pyrekordbox README + encryption notes](https://github.com/dylanljones/pyrekordbox)]

**Live monitoring?** No. Pyrekordbox is a one-shot reader. It does not watch the database for changes, has no inotify/FSEvents/ReadDirectoryChangesW integration, and even if we added one ourselves, Rekordbox holds the SQLCipher file open with locks during a session. [VERIFIED: API docs only show `get_content()`/`get_playlist()`-style readers]

**What it's actually useful for in vibemix:** **NOT** for live "what's playing right now" grounding. It IS useful as a one-shot pre-session import: at vibemix startup, dump the user's Rekordbox library to a local cache (track titles + BPM + key + cue points + per-track energy), then use that cache to enrich the now-playing detection ("the user is loading their `house-bangers` playlist, BPM range 124-128, all tracks tagged Energy 4-5") for prompt grounding. This is also the natural place to slot Gemini Embedding 2 — compute embeddings over the Rekordbox library once, then do "what's the next likely track" semantic search.

**Tractability: MID for v1.1 (library import for prompt context), HIGH for v2.0 (Gemini Embedding 2 library indexing).** Install friction is yellow: pip-install + bundled SQLCipher wheels work on Mac+Win, but the post-6.6.5 key-extraction wall means we ship the feature as "best-effort, falls back to manual XML import" for the ~80% of users on current Rekordbox. The fallback path — Rekordbox can export its library to XML (Preferences → Advanced → Database → Export Collection in xml format) — is unencrypted, parses with stdlib `xml.etree.ElementTree`, and still gives us titles + BPM + key. **Recommendation: ship the XML-import path in v1.1, treat pyrekordbox SQLCipher access as opportunistic.**

---

### Mixxx OSC

**Status — the *one* DJ platform where this just works.** Mixxx has shipped OSC *output* (as an OSC client broadcasting to an external OSC server) since 2.x. It is built-in functionality, not a plugin, not controller scripting. The community feature request for OSC *input* (receiving control from external software) is [Launchpad bug #319386](https://bugs.launchpad.net/bugs/319386) and has been open since 2009 — **OSC-in is NOT merged in 2.4 or 2.5.** This is fine for vibemix: we don't want to *control* Mixxx, we want to *read* it. [VERIFIED: [Mixxx wiki — Osc Client](https://github.com/mixxxdj/mixxx/wiki/osc-client)]

**Wire shape:**
- **Send rate:** every 500 ms + on UI events (play press, fader move, track change). [VERIFIED]
- **Per-deck fields broadcast:** `play` state (playing/stopped), `title` (track name), `volume` (with crossfader applied), `position` (relative 0.0-1.0), `duration`, plus `decks` (total count).
- **Protocol:** Standard OSC over UDP. Default port is configurable; community guides use 7777.
- **Verification command:** `dump_osc 7777` (`pyliblo-utils` on Linux; on macOS install via `brew install liblo` and use [`python-osc`](https://pypi.org/project/python-osc/) for the listener side).

**Sample integration code for vibemix:**

```python
# vibemix/platform/mixxx_osc.py
import asyncio
from pythonosc import dispatcher, osc_server

class MixxxBus:
    """Listens for Mixxx's OSC broadcast and exposes the latest deck snapshot.
    Drop-in alongside ControllerState. ~500ms staleness.
    """
    def __init__(self, port: int = 7777):
        self._latest = {'A': {}, 'B': {}, 'master': {}}
        self._lock = asyncio.Lock()
        d = dispatcher.Dispatcher()
        # Mixxx address pattern: /Mixxx/Channel{N}/{control}
        d.map("/Mixxx/Channel*/play", self._on_play)
        d.map("/Mixxx/Channel*/title", self._on_title)
        d.map("/Mixxx/Channel*/volume", self._on_volume)
        d.map("/Mixxx/Channel*/position", self._on_position)
        d.map("/Mixxx/Channel*/duration", self._on_duration)
        self._server = osc_server.AsyncIOOSCUDPServer(
            ("127.0.0.1", port), d, asyncio.get_event_loop()
        )

    def _on_play(self, addr, *args):
        deck = self._deck_from_addr(addr)
        self._latest[deck]['playing'] = bool(args[0])
    # ...similar for title/volume/position/duration

    def snapshot(self) -> dict:
        return dict(self._latest)

    async def start(self):
        self._transport, _ = await self._server.create_serve_endpoint()
```

[ASSUMED: exact OSC address pattern `/Mixxx/Channel{N}/...` — Mixxx docs show URL-style `/Control/[Group]/[Key]` in design proposals but the live implementation address shape needs verification against a running Mixxx 2.5; the dispatcher mapping above will need adjustment. This is the one detail to validate during planning by running `dump_osc` against a live Mixxx instance.]

**Install friction:** Green. User enables OSC in Mixxx Preferences (one toggle) → set port to 7777 (one number) → vibemix auto-detects. No driver install, no kernel extension, no admin elevation. On Windows there may be a Defender prompt for incoming UDP, but it's localhost-only so it stays in the loopback zone.

**Latency model:** Mixxx broadcasts every 500 ms and on UI events. For event-driven things (track change, play press) we get near-instant signal. For continuous things (position, EQ knob — wait, EQ isn't in the broadcast list above), we're at 500 ms staleness. For vibemix's reaction-timing budget of 800-1500 ms end-to-end, this is fine. **However:** the broadcast list per the wiki is limited — title/play/volume/position/duration. **No BPM, no key, no EQ knob position, no cue-point fires.** EQ + cues + BPM still have to come from MIDI/audio. So Mixxx-OSC is a *better track-identity + position-aware* signal, not a complete deck telemetry stream.

**Legal envelope:** Mixxx is GPLv2. We're not linking to or modifying Mixxx code — we're reading network messages it sends to us. That's clean. We can ship "vibemix supports Mixxx" with zero license entanglement. The vibemix code that *parses* Mixxx OSC is Apache-2.0 vibemix code.

**Tractability: HIGH. This is the v1.1 headline feature.** Ship "vibemix natively supports Mixxx" as a co-marketing wedge: Mixxx has ~500-1000k installs and a strong free-software DJ community that's the right cultural audience for vibemix. The MixxxBus class above is ~80 lines and one afternoon's work plus tuning.

---

### djay Pro AI (Algoriddim)

**Official position:** **Algoriddim does not offer an API or SDK for djay Pro.** This is confirmed multiple times in their own community forums when users ask. AppleScript integration is not exposed. There is no URL-scheme `djay://` for external query. There is no `NSAppleEventDescriptor` we can fire. [CITED: [Algoriddim forums — "Djay Pro AI API"](https://community.algoriddim.com/t/djay-pro-ai-api/13185), [Algoriddim forums — "Developer API or SDK"](https://community.algoriddim.com/t/developer-api-or-sdk/25958)]

**What IS available:** MIDI Learn — the standard mapping system every DJ app has. The user can map MIDI events INTO djay Pro from a controller. Useless for *reading* deck state out of djay Pro.

**Reality check on alternatives:**
- **Accessibility API on macOS** — could in theory traverse djay Pro's UI tree and read BPM/track labels via the AX API. We've considered this for other apps. It's brittle (any UI rev breaks it), requires Accessibility permission grant (annoying TCC prompt), and Algoriddim ships UI updates frequently. Not a serious option.
- **Screen capture + OCR** — already our current path. The vision model reads the screen JPEG. This works but is the hallucination-prone path we're trying to replace.
- **Now Playing (MediaRemote)** — djay Pro publishes the current track title via macOS MediaRemote when the user enables it. This is what `nowplaying-cli` reads today in cohost_v4.py. Gives us *one* title, not per-deck — and it's the deck that *djay decided to publish*, which is often wrong when the user is mid-mix. This is exactly the brittleness we want to fix.

**Vibemix shape:** Stays exactly as it is today: BlackHole audio capture + screen JPEG to Gemini multimodal + `nowplaying-cli` for the (unreliable) track title + audible-deck detection from MIDI. There's nothing better to swap in. We accept the screen-capture grounding cost for djay Pro and double down on the anti-hallucination protocol (raw RMS + bands + magnitude-aware EQ moves + Gemini Embedding 2 fingerprinting from audio) rather than trying to extract more from djay.

**Tractability: NO-GO for telemetry integration.** The platform itself is not cooperative. Keep djay Pro support as "vibemix works alongside djay Pro using audio + screen + MIDI" — the same way every other AI DJ tool works alongside djay Pro.

---

### Serato DJ Pro

**Official SDK:** Serato has a Web Services SDK (`@serato/sws-sdk`) on npm. This is for the Serato cloud — streaming-service auth, license management, Studio account. It is **not** a desktop DJ Pro API; it does not expose deck state. [VERIFIED: [npm @serato/sws-sdk](https://www.npmjs.com/package/@serato/sws-sdk)]

**Plugin SDK for Serato DJ Pro:** Serato has historically allowed VST/AU plugins for effects, and Expansion Packs for stems/DVS/Pitch n Time, but **there is no public plugin SDK that gives a third-party plugin access to deck state, track metadata, or playback events.** Effect plugins receive audio buffers but nothing about what track is playing. [CITED: [Serato forums — "Developing a Plugin for Serato"](https://serato.com/forum/discussion/91457)]

**The community workarounds:**
- [`tombell/saga`](https://github.com/tombell/saga) — Go-based websocket API server that watches Serato's session file. **15★, archived 2023-03-08, no longer maintained.** Real-time during a session because Serato continuously appends to its session file as tracks load/play. Output is a websocket on localhost:8080. [VERIFIED: GitHub fetch]
- [`srinitude/serato-dj-api`](https://github.com/srinitude/serato-dj-api) — fork of SSL-API (eladmaz). Same approach: parse the binary session/history file as Serato writes to it. Status uncertain, low star count.
- [`Holzhaus/triseratops`](https://github.com/Holzhaus/triseratops) — Rust crate for parsing Serato's `.crate` library files. Not real-time — this is for offline library introspection.
- [`unbox`](https://github.com/erikrichardlarson/unbox) (355★, last commit 2025-05-28) — universal track-display tool that supports Serato among others. Uses the same session-file polling under the hood. The README requires a "Serato User ID" suggesting it may auth against the Serato cloud for some path.

**Reality:** The session-file-watching approach gives us *track title + BPM* but not per-deck state, not EQ moves, not cue fires. It's a slightly better `nowplaying-cli` for Serato users — not a step-change. And `saga` being archived means we'd either fork it, reimplement it from the Holzhaus-style binary-format docs, or rely on the file path conventions which change between Serato updates.

**Vibemix shape if we ever do this:** Wave 2 add-on: a `vibemix/platform/serato_session.py` that watches `~/Music/_Serato_/History/Sessions/*.session` on macOS (and the equivalent on Windows) for new entries, parses the binary format with a small Rust-or-pure-Python parser, and emits track-change events. Gives us "track title" without screen-OCR. The audible-deck and EQ/move info still come from MIDI.

**Tractability: MID for v1.2+ if we have Serato user demand pulling for it, LOW for v1.1.** Session-file scraping is feasible (saga proved it), but it's a maintenance burden against an undocumented binary format that Serato changes. Don't build it speculatively. Build it if real users ask.

---

### Native Instruments Traktor

**Official API: none for deck state.** Traktor's controller integration is the proprietary `.tsi` (formerly `.tks`) mapping format, used by their Controller Manager. This is for incoming MIDI mapped INTO Traktor — same shape as djay Pro's MIDI Learn. The TSI file format is binary, undocumented officially, and the legacy `.tks` files are XML (older format, removed in modern Traktor). [CITED: [Native Instruments — Configuring MIDI Controller for Traktor](https://www.native-instruments.com/ni-tech-manuals/traktor-pro-manual/en/configuring-midi-controller-for-controlling-traktor)]

**MIDI Clock OUT:** Traktor can send MIDI clock to external software/hardware (`Preferences > MIDI Clock > Send MIDI Clock`). [VERIFIED: [Native Instruments support article](https://support.native-instruments.com/hc/en-us/articles/209590629-How-to-Send-a-MIDI-Clock-Sync-Signal-in-TRAKTOR)] This gives us **BPM only — no track ID, no position, no deck state.** Useless for grounding (BPM we can already estimate from audio with high accuracy).

**OSC support:** Traktor added OSC in version 2.5 (released 2003) but it's primarily for control-IN (sending OSC to drive Traktor). Documentation is sparse and community guides like TouchOSC's Traktor setup focus on the inbound direction. There's no documented Traktor → external OSC broadcast comparable to Mixxx. [CITED: [Wikipedia — Traktor](https://en.wikipedia.org/wiki/Traktor), [TouchOSC — Setup Traktor](https://hexler.net/touchosc/manual/setup-traktor)]

**Reality:** Traktor is the closed-est of the closed DJ apps. Native Instruments treats the deck-state surface as proprietary. The only path to deck telemetry from Traktor is screen capture or MIDI controller monitoring — same as djay Pro.

**Tractability: NO-GO for direct integration.** Stay on the audio + screen + MIDI fallback. Traktor users are a smaller slice of the bedroom-DJ pie than Pioneer-controller-on-Rekordbox/Serato users anyway.

---

### VirtualDJ

**Internal scripting:** VDJScript — VirtualDJ's expression language for plugin/skin/mapping authors. Runs *inside* VirtualDJ. Not exposed to external processes by default. [CITED: VirtualDJ forums]

**OSC server (the good news):** VirtualDJ has an OSC server that answers commands like `/vdj/deck/1/play` and supports query (`/vdj/query/deck/1/get_bpm`) and subscribe (`/vdj/subscribe/deck/1/get_bpm` — pushes updates whenever the value changes). **This is a full bidirectional OSC surface**, comparable to Mixxx's but more capable because it supports subscriptions. [VERIFIED: [VirtualDJ forum — Triggering VirtualDJ via OSC](https://virtualdj.com/forums/266090/General_Discussion/Triggering_VirtualDJ_via_OSC.html)]

**The catch:** **This feature requires a VirtualDJ Pro license (paid).** The free Home version does not enable the OSC server. Pro is $19/month or $299 one-time. So while the integration shape is technically the best of all the closed-source apps (subscribe-on-change is exactly the model we want), it's gated behind a license tier most bedroom DJs aren't on.

**Vibemix shape if we did it:** Trivial — subscribe to the BPM, position, play state, EQ knob, fader on each deck. Code is parallel to the MixxxBus class above. Would deliver per-deck telemetry with sub-100ms latency on user-driven changes.

**Tractability: MID, gated on user demand from the Pro slice of VDJ users.** Not v1.1. If we see signal that vibemix has VirtualDJ Pro users asking for native integration, ship a `vibemix/platform/vdj_osc.py` similar to the Mixxx bridge. Until then it's a future opportunity.

---

## Cross-platform controller MIDI maps + transpiler feasibility

This is the existing strategic bet, and the research only strengthens it. Five reasons:

**1. Controllers are the universal layer.** A user who switches from djay Pro to Rekordbox to Serato is *probably still using the same DDJ-FLX4*. The controller maps cleanly across DJ apps because every app implements MIDI Learn against the same hardware. So if vibemix's grounding is from the controller, it's *automatically* cross-app.

**2. The bedroom-DJ controller market is concentrated.** From the search results, the dominant beginner controllers in 2025-2026 are: Pioneer DDJ-FLX4 (the de facto default — "best beginner DJ controller 2026"), DDJ-400 (still in circulation, FLX4's predecessor), DDJ-FLX6 (mid-tier upgrade), Hercules Inpulse 500/300 (the budget alternative), Numark Mixstream Pro+ (the standalone-capable one). That's five SKUs covering probably 70-85% of bedroom DJs. Pioneer's AlphaTheta brand has been called "dominant force in both consumer and professional DJ environments." [CITED: [The DJ Revolution — Best DJ Controllers Beginners 2026](https://www.thedjrevolution.com/best-dj-controllers-for-beginners/), [AVMaxx — Best DJ Controllers 2025](https://www.avmaxx.com/best-dj-controllers-2025.html)]

**3. The CC/note ID is uncopyrightable fact.** A MIDI note number is a number. Mixxx's GPL XML mapping files document Pioneer DDJ-FLX4 CC numbers as facts. We can use Mixxx XML as a *reference* (read it, transcribe CC numbers, write our own format) without GPL infection, because facts about hardware behavior are not copyrightable. The Mixxx authors have explicitly said this is fine for non-derivative use. (We are NOT redistributing or modifying their XML; we are reading public documentation about hardware behavior.) [CITED: [Mixxx DDJ-FLX4 mapping XML](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml) — reference only]

**4. The DDJ-FLX4 implementation in `cohost_v4.py` already proves it works.** `_CC_MAP` + `_NOTE_MAP` (lines 586-602) decode vol/EQ/filter/tempo/play/cue/sync/jog/loop for both decks A+B and the master crossfader. The audible-deck heuristic on top (cross-references xfader position, deck vol, EQ kill state) gives us "which deck is dominant in the master right now" — the single biggest hallucination class for vibemix. [VERIFIED: `cohost_v4.py:586-732`]

**5. Transpiler feasibility — moderate.** Reading a Mixxx XML mapping and emitting a vibemix-format mapping is straightforward. Reading a Rekordbox `.midi.xml` (different schema) or a Serato `.tsi` (binary, undocumented) or a djay `.djmap` (proprietary plist) is each a separate parser. The *output* side — emitting a Rekordbox/Serato/djay mapping from a vibemix canonical format — is much harder because we'd be writing files the closed apps then load, which means our format has to be precisely what they accept. **Better strategy:** Don't build a transpiler. Ship per-controller mapping files in vibemix's own format (one Python module per controller — `vibemix/midi/library/ddj_flx4.py`, etc.), curate 10, and let community PRs extend. Users keep their existing DJ-app mappings unchanged; vibemix listens to the same controller in parallel.

**Recommended initial library (10 controllers, in priority order):**

| # | Controller | Software shipped with | Why curated |
|---|-----------|----------------------|-------------|
| 1 | Pioneer DDJ-FLX4 | Rekordbox + Serato Lite | Best-selling 2024-2026 beginner controller; already in cohost_v4 |
| 2 | Pioneer DDJ-400 | Rekordbox | FLX4's predecessor, huge installed base |
| 3 | Pioneer DDJ-FLX6 | Rekordbox + Serato | Step-up from FLX4 |
| 4 | Pioneer DDJ-FLX10 | Rekordbox + Serato | Pro 4-deck, FLX-series flagship |
| 5 | Pioneer DDJ-SX3 | Serato | Serato's 4-deck workhorse |
| 6 | Pioneer XDJ-RX3 | Rekordbox | Standalone-or-laptop hybrid |
| 7 | Hercules DJControl Inpulse 500 | DJUCED / Serato Lite | #2 beginner alternative to FLX4 |
| 8 | Hercules DJControl Inpulse 300 | DJUCED / Serato Lite | Cheaper Hercules entry |
| 9 | Numark Party Mix Live | Serato Lite | Sub-$200 entry-level |
| 10 | Numark Mixstream Pro+ | Standalone (Engine DJ) | Standalone trend representative |

Add an 11th *generic* MIDI fallback that learns positionally — when a fader CC is found, infer it as "deck vol" if it's at a low channel; when a button NOTE is hit twice for play/cue, learn the convention. Coverage degrades but the product still runs.

---

## Tractability matrix

| Platform | Data surface | Install friction | Tractability | Recommendation |
|----------|-------------|------------------|--------------|----------------|
| **Mixxx (OSC)** | title, play, volume, position, duration per deck — at 500ms + on-event. No BPM/EQ/cues in broadcast. | **GREEN** — toggle a Mixxx preference, expose one port | **HIGH** | **Ship in v1.1 as headline "vibemix supports Mixxx natively" feature** |
| **MIDI controllers (DDJ-FLX4 etc.)** | vol, EQ, filter, tempo, play, cue, sync, jog, loop, xfader — all decks, all real-time | **GREEN** — USB device, no extra install | **HIGH** | **Continue v1 plan: ship 10-controller library + audible-deck detection** |
| **pyrekordbox library import** | One-shot library snapshot: title, BPM, key, energy, cue points, beat grid | **YELLOW** — pip works, but post-6.6.5 SQLCipher key extraction broken; XML-export fallback is reliable | **MID** | **Ship XML-import path in v1.1, opportunistic SQLCipher in v1.2** |
| **Now Playing (current path, MediaRemote on Mac / GSMTC on Win)** | One track title, no per-deck | **GREEN** — already present | **MID** (status quo) | **Keep as universal fallback; never trust solely** |
| **VirtualDJ OSC** | Full per-deck telemetry incl. BPM, position, EQ, faders — subscribe-on-change | **YELLOW** — requires VirtualDJ Pro paid license | **MID** | **Ship in v1.2 if user demand emerges from VDJ Pro slice** |
| **ProDJ Link (CDJ hardware)** | Full deck telemetry incl. phrase data on CDJ-3000 | **RED** — requires Pioneer CDJ on Ethernet LAN + bundled JVM bridge | **LOW** | **Skip v1/v2 for the bedroom-DJ target. Optional add-on if we ever pursue a Pro SKU** |
| **Serato session-file scraping (saga-style)** | Track title + BPM, no per-deck state | **YELLOW** — file path conventions break across Serato updates; saga itself archived | **LOW-MID** | **Build only if Serato users specifically ask. Maintenance burden** |
| **Traktor** | BPM via MIDI clock out, that's it | **N/A** | **NO-GO** | **Stay on audio + screen + MIDI fallback** |
| **djay Pro AI** | Nothing exposed | **N/A** | **NO-GO** | **Stay on audio + screen + MIDI fallback** |
| **Rekordbox runtime (live deck state)** | Nothing exposed without CDJ hardware | **N/A** | **NO-GO** | **Stay on audio + screen + MIDI fallback** |

---

## Recommended integration stack for vibemix v1.1 + v2.0 (ranked)

**v1.1 — ship within ~4-6 weeks post-launch:**

1. **Mixxx OSC bridge** (`vibemix/platform/mixxx_osc.py`) — ~80 LOC, one afternoon to write, one afternoon to test against real Mixxx. Headline feature. "vibemix is the AI co-host that natively reads your Mixxx state." Drives a Mixxx-community marketing push and lands us in front of the strongest free-software DJ audience.

2. **Pyrekordbox XML-import** (`vibemix/library/rekordbox_xml.py`) — one-shot read of the user's exported Rekordbox collection. Surfaces titles + BPM + key + energy + cue points as prompt-grounding context. Skips the SQLCipher key-extraction wall entirely by using the unencrypted XML export path. ~150 LOC. Adds first-class "vibemix knows your library" capability that no other AI DJ tool does.

3. **Generic-MIDI positional fallback** in the existing MIDI library — when no curated controller matches, learn fader/knob/button conventions positionally so an unknown controller still produces useful event signal. Closes the "controller not supported" gap with graceful degradation.

**v2.0 — ship over the 6-month horizon:**

4. **Gemini Embedding 2 over the imported Rekordbox library** — index every track in the user's library with multimodal Gemini Embedding 2 (text metadata + audio chunk). Enables semantic "what's likely next?" suggestions, "find me tracks vibing like this one," and dramatic improvement on the now-playing grounding (we can compare the live audio embedding against the library's embedded tracks for high-confidence track ID).

5. **Pyrekordbox SQLCipher path** (best-effort) — for the slice of users who are on Rekordbox versions where key extraction still works, or who run the [liamcottle key-extraction workaround](https://github.com/liamcottle/pioneer-rekordbox-database-encryption). Gives live library reads instead of stale XML exports.

6. **VirtualDJ OSC bridge** (`vibemix/platform/vdj_osc.py`) — parallel structure to the Mixxx bridge. Gated on user-demand signal from the Pro slice.

**v2.0+ stretch (only if data warrants):**

7. **Serato session-file watcher** — port `saga`'s approach in pure Python with our own binary-format parser. Maintenance burden, defer until Serato users specifically ask.

8. **Optional CDJ Pro add-on** — bundle `open-beat-control.jar` + Java runtime as a downloadable extras pack. Only activates if a Pioneer ProDJ Link device is detected on the LAN. Lets vibemix work in the rare "user has CDJs at home" case without burdening the default install.

---

## Risk + watchouts

**Firmware breakage risk (Pioneer):** Pioneer has shown willingness to break things in firmware updates — see the 3.30 → suspended → "downgrade to 3.20" debacle in October 2025. dysentery/beat-link has tracked these so far, but a future Pioneer firmware *could* obfuscate or encrypt the ProDJ Link protocol the way they obfuscated the master.db key. Don't bet vibemix's roadmap on ProDJ Link being readable indefinitely. [CITED: [Pioneer 3.30 suspension notice](https://www.pioneerdj.com/en/news/2025/important-notice-cdj-3000-firmware-ver330/)]

**SQLCipher key-extraction wall (Pioneer Rekordbox):** Already happened. Post-6.6.5 the automatic key extraction is broken for fresh installs. **Treat any feature that depends on live `master.db` access as opportunistic, with XML-export as the durable fallback.** Don't write the v1.1 README in a way that promises "vibemix reads your Rekordbox library live."

**Algoriddim's "no API" stance is unlikely to change:** djay Pro is an AI-flavored DJ app that competes for the same "AI in the booth" mindshare as vibemix. Algoriddim has zero incentive to make third-party AI tools easier to integrate with their app. Plan for permanent screen-capture grounding on djay Pro.

**Mixxx XML legal nuance:** Reading XML mapping files for *factual* CC/note numbers is fine. **Don't** copy the JavaScript mapping logic verbatim (that's copyrightable code). When we use Mixxx XML as reference, we write our own decode logic in Python from scratch. Document this in the per-controller mapping module headers ("CC numbers sourced from Pioneer published MIDI implementation chart and verified against Mixxx mapping XML — decode logic written for vibemix").

**Generic MIDI controllers (the long tail):** A real-world user might own a Reloop, Roland, Behringer, Numark Party Mix (original, not Live), or some old Hercules. They'll plug it in, vibemix will see MIDI activity, and a generic positional fallback better produce *something* useful. If it doesn't, the user's "vibemix doesn't work with my controller" issue lands on GitHub Day 1.

**OSC port collisions:** Both Mixxx OSC and VirtualDJ OSC default to user-configurable ports. We need a small port-detection / settings UI ("If you use Mixxx OSC, set its port here"). Don't hardcode 7777 — Mixxx users might already have it bound to TouchOSC or similar.

**Open-source library staleness:** `python-prodj-link` last meaningful commit ~3y back. `saga` archived. `open-beat-control` last release Dec 2020. If we depend on any of them we are de facto the maintainer. **Of these, only `pyrekordbox` (last release 2025-08-17) is actively maintained.** That weights heavily toward the v1.1 path being Mixxx OSC + pyrekordbox + curated MIDI library, and away from the ProDJ Link / Serato session-file / open-beat-control paths.

**License audit for any path we ship:** Mixxx GPLv2 (we read its network output, no link), pyrekordbox MIT (clean to bundle), python-osc MIT (clean), construct MIT (clean). dysentery/beat-link Eclipse Public License (would require careful bundling if we ever did ProDJ Link). No GPL contamination in the recommended v1.1/v2.0 stack.

---

## Open questions for Kaan

1. **Mixxx OSC: do we go big on this in v1.1 marketing, or treat it as quiet feature?** The "vibemix native Mixxx integration" angle is strong (Mixxx community has ~1M installs and a strong free-software ethos that maps to OSS-vibemix's positioning), but it diverts marketing from the broader "vibemix works with everything" message. Recommendation: bullet-pointed feature in the README, full integration cookbook on the wiki, but the hero pitch stays "works alongside any DJ software."

2. **Rekordbox XML import — does the wizard ask the user to do the export, or do we sniff for `~/Library/Pioneer/rekordbox/{collection}.xml` and offer to import if present?** The auto-sniff feels magical but touches user-private library data. Auto-detect-with-confirm seems right. Need a final UX call.

3. **DDJ-FLX10 in v1 or v1.1?** It's listed in our 10-controller library, but the FLX10 has more controls than FLX4 (4-deck, more effects pads, master display). The mapping effort is meaningfully bigger. Question: do FLX10 users feel like a v1 priority, or can they wait for v1.1?

4. **Generic-MIDI fallback — how aggressive on the positional inference?** A safe fallback says "controller detected, vibemix will react to play/pause and major fader moves only." An aggressive fallback tries to learn the full vol/EQ/filter mapping by watching the user mix for the first 60 seconds. The aggressive path has more grounded reactions but a 1% wrong-mapping-from-misinference rate could produce confidently wrong "Deck B EQ-hi killed" claims when the user is actually moving the gain trim. Lean conservative for v1?

5. **VirtualDJ Pro integration — wait for organic signal, or proactively ship in v1.2 to capture the VDJ Pro audience?** VDJ has a *very* engaged paid-user community on its forums. If we ship a `vibemix-with-VDJ` integration and post a demo there, it could be a focused-audience growth lever similar to the Mixxx play. But it's also a small slice of the total addressable bedroom-DJ market. Worth the 2-3 day build cost?

---

## Sources

### Primary (HIGH confidence)
- [Mixxx wiki — Osc Client](https://github.com/mixxxdj/mixxx/wiki/osc-client) — confirms built-in OSC output, 500ms cadence, per-deck fields
- [pyrekordbox README + GitHub](https://github.com/dylanljones/pyrekordbox) — 395★, v0.4.4 (2025-08-17), Rekordbox 5/6/7 support, SQLCipher status
- [Pyrekordbox docs — Database Format](https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html) — schema details, 6.6.5+ key extraction wall
- [dysentery GitHub](https://github.com/Deep-Symmetry/dysentery) — 247★, v0.2.2 (2025-05-08), CDJ-3000 support
- [beat-link GitHub](https://github.com/Deep-Symmetry/beat-link) — 132★, production Java implementation
- [open-beat-control GitHub](https://github.com/Deep-Symmetry/open-beat-control) — 53★, last release Dec 2020 (stale)
- [python-prodj-link GitHub](https://github.com/flesniak/python-prodj-link) — 204★, requires CDJ hardware on LAN
- [Algoriddim community — "Djay Pro AI API"](https://community.algoriddim.com/t/djay-pro-ai-api/13185) — confirms no API
- [VirtualDJ forums — Triggering VirtualDJ via OSC](https://virtualdj.com/forums/266090/General_Discussion/Triggering_VirtualDJ_via_OSC.html) — Pro-license-gated OSC server
- [Pioneer CDJ-3000 Firmware 3.20 release](https://www.pioneerdj.com/en/news/2025/cdj-3000-firmware-update-320/) — current stable
- [Pioneer 3.30 distribution suspension](https://www.pioneerdj.com/en/news/2025/important-notice-cdj-3000-firmware-ver330/) — firmware-risk evidence
- [tombell/saga GitHub](https://github.com/tombell/saga) — 15★, archived 2023-03-08
- [unbox GitHub](https://github.com/erikrichardlarson/unbox) — 355★, last commit 2025-05-28, multi-platform precedent
- `/Users/ozai/projects/dj-set-ai/cohost_v4.py:586-732` — existing DDJ-FLX4 implementation

### Secondary (MEDIUM confidence)
- [Mixxx Osc Backend wiki](https://github.com/mixxxdj/mixxx/wiki/osc_backend) — design proposal (2014), OSC-IN not merged
- [Mixxx Launchpad bug #319386](https://bugs.launchpad.net/bugs/319386) — OSC parameter access feature request open since 2009
- [Native Instruments — Configuring MIDI Controller for Traktor](https://www.native-instruments.com/ni-tech-manuals/traktor-pro-manual/en/configuring-midi-controller-for-controlling-traktor) — confirms no public deck-state API
- [Native Instruments — MIDI Clock in Traktor](https://support.native-instruments.com/hc/en-us/articles/209590629-How-to-Send-a-MIDI-Clock-Sync-Signal-in-TRAKTOR) — BPM-only output
- [Serato sws-sdk on npm](https://www.npmjs.com/package/@serato/sws-sdk) — confirms cloud-only SDK scope
- [pioneer-rekordbox-database-encryption (liamcottle)](https://github.com/liamcottle/pioneer-rekordbox-database-encryption) — community SQLCipher workaround
- [Mixxx DDJ-FLX4 mapping XML](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml) — reference for CC numbers (fact, not protected expression)
- [The DJ Revolution — Best DJ Controllers for Beginners 2026](https://www.thedjrevolution.com/best-dj-controllers-for-beginners/) — controller market positioning
- [AVMaxx — Best DJ Controllers 2025](https://www.avmaxx.com/best-dj-controllers-2025.html) — market view, January 2025

### Tertiary (LOW confidence — flag for validation)
- Exact Mixxx 2.4/2.5 OSC address-pattern format (verify against `dump_osc` during planning)
- Bedroom-DJ controller market share percentages (cited reviews are qualitative; no hard sales numbers found)
- VirtualDJ Pro pricing and user-base size (forum-level signal only, no firm market data)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mixxx OSC address pattern is `/Mixxx/Channel{N}/{control}` | Mixxx integration code snippet | Low — verifiable in 5 minutes with `dump_osc`; pattern adjusts in one line |
| A2 | Bedroom-DJ controller market is 70-85% concentrated in the listed 10 SKUs | Cross-platform controller library | Medium — if wrong, our curated 10 covers fewer users than estimated; generic-MIDI fallback still catches them |
| A3 | Mixxx GPLv2 license does NOT extend to vibemix code that reads network output | Mixxx legal envelope | Low-medium — standard interpretation, but worth a one-line legal review before public claim of "vibemix supports Mixxx" |
| A4 | Pioneer is unlikely to break ProDJ Link irreparably in the foreseeable future | Risk + watchouts | Medium — speculative; dysentery has tracked breakages so far, but a future firmware could go encrypted |
| A5 | VirtualDJ Pro OSC subscription model has sub-100ms latency | VDJ section | Low — not benchmarked; matches typical localhost OSC patterns but unverified for VDJ specifically |

---

*Research completed: 2026-05-13*
*Author: GSD-research-phase for vibemix v2 industry integrations*
*Word count: ~3,300*
