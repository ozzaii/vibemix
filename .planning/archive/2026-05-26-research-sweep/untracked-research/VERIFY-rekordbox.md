# VERIFY — Rekordbox / pyrekordbox claims fact-check

**Verifying:** `.planning/research/rekordbox-readwrite-deepdive.md`
**Date:** 2026-05-26
**Method:** context7 MCP was NOT available in this environment (no `mcp__context7__*` tools exist). Verified against authoritative pyrekordbox sources: GitHub repo `dylanljones/pyrekordbox` (source at the **`v0.4.4` release tag**), the readthedocs docs, GitHub discussions, and the Pioneer XML format spec.
**Constraint honored:** no real SQLCipher key value is reproduced anywhere below.

---

## Verdict table

| # | Claim (from deepdive) | Verdict | Evidence |
|---|---|---|---|
| 1a | `pyrekordbox.rbxml` `RekordboxXml` has `add_track(location, **kwargs)` and `Track` has `add_mark()` for hot/memory cues | **CONFIRMED** | `rbxml.py` @ `v0.4.4`: `RekordboxXml.add_track(self, location, **kwargs) -> Track` (def ~L1107); `Track.add_mark(...) -> PositionMark` (def ~L632). https://github.com/dylanljones/pyrekordbox/blob/v0.4.4/pyrekordbox/rbxml.py |
| 1b | `add_mark()` is in the released **0.4.4** (not only an unmerged branch) | **CONFIRMED** | Method present in source at the `v0.4.4` tag (XML write is the released, supported path). |
| 1c | `add_mark()` accepts `Red`/`Green`/`Blue` color params (deepdive §4.1 L140–141: `track.add_mark(..., Red=204, Green=0, Blue=204)`) | **REFUTED** | v0.4.4 signature is exactly `add_mark(self, Name="", Type="cue", Start=0.0, End=None, Num=-1) -> PositionMark` — **no color params**. The code comment in §4.1 will raise `TypeError`. See "Correction" below. |
| 2a | Cue-WRITE to `master.db` is genuinely unavailable in 0.4.4 (no released `add_cue`); `NotImplementedError` blocker | **CONFIRMED** | `db6/database.py` @ v0.4.4 has add_* for album/artist/genre/label/content/playlist only — **no `add_cue`**. Maintainer: "all progress … is in the `cues` branch"; "a `NotImplementedError` is raised if a VBR/ABR encoded MP3 file is detected." https://github.com/dylanljones/pyrekordbox/discussions/113 |
| 2b | The "cues" branch is real and unmerged, stuck on VBR/ABR `InMpegAbs` offsets | **CONFIRMED** | Discussion #113: maintainer "still can't reproduce the correct `InMpegAbs` values"; progress confined to unmerged `cues` branch. |
| 3a | SQLCipher key is a single hardcoded constant shared across RB6 **and** RB7 | **CONFIRMED** | db6 format doc: master.db is "an SQLite3 database encrypted with SQLCipher4"; key is a documented community constant (liamcottle repo; pyrekordbox). https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html (key value intentionally not reproduced) |
| 3b | `python -m pyrekordbox download-key` is a real command that fetches+caches the key | **CONFIRMED** | Quickstart (0.4.4 stable docs): "a command for downloading the key from known sources and writing it to the cache file: `python -m pyrekordbox download-key` … Once the key is cached the database can be opened without providing the key." https://pyrekordbox.readthedocs.io/en/stable/quickstart.html |
| 3c | (mechanism) post-6.6.5 app.asar obfuscation broke regex key-scrape → `download-key` is the workaround | **CONFIRMED** | Discussion #97 + quickstart: 6.6.5 obfuscated app.asar; `download-key` pulls from known external sources instead of scraping the app. https://github.com/dylanljones/pyrekordbox/discussions/97 |
| 4a | master.db has a `DjmdCue` table for cues | **CONFIRMED** | db6 format doc has a dedicated `djmdCue` section (memory + hot cues, column specs). https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html |
| 4b | USN / `rb_local_usn` must be bumped on write; pyrekordbox exposes USN helpers | **CONFIRMED** | db6 doc lists `usn` + `rb_local_usn` default columns. `db6/database.py` @ v0.4.4 has `get_local_usn()`, `set_local_usn()`, `increment_local_usn(num=1)`, `autoincrement_usn(set_row_usn=True)`. (Names differ slightly from deepdive — see Correction.) |
| 4c | pyrekordbox refuses to `commit()` while Rekordbox is running | **CONFIRMED** | `db6/database.py` `commit()` checks `get_rekordbox_pid()` and raises: "Rekordbox is running. Please close Rekordbox before commiting changes." |
| 5a | XML TRACK attrs (Location, Name, Artist, AverageBpm, Tonality, TotalTime, …) | **CONFIRMED** | xml format doc lists TrackID, Name, Artist, …, TotalTime, Year, AverageBpm, …, Location, Remixer, Tonality, Label, Mix, Colour. https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html |
| 5b | XML POSITION_MARK attrs Name/Type/Start/End/Num; Type 0=cue 1=fade-in 2=fade-out 3=load 4=loop | **CONFIRMED** | xml doc: POSITION_MARK = Name, Type, Start, End, Num. Pioneer spec: Cue=0, Fade-In=1, Fade-Out=2, Load=3, Loop=4. https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf |
| 5c | XML POSITION_MARK carries per-mark Red/Green/Blue color (the *schema* claim in §1/§2.4/§3.2) | **CONFIRMED** | Pioneer XML spec: POSITION_MARK supports Red, Green, Blue color attributes (newer export format). https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf — **but pyrekordbox's `add_mark()` does not expose them; see 1c.** |
| 5d | XML TEMPO attrs Inizio/Bpm/Metro/Battito | **CONFIRMED** | xml format doc: TEMPO = Inizio, Bpm, Metro, Battito. https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html |

---

## Corrections to the deepdive

1. **§4.1 code (L140–141) — WRONG API.** `track.add_mark(..., Red=204, Green=0, Blue=204)` will raise `TypeError`: `add_mark()` in 0.4.4 takes only `Name, Type, Start, End, Num`. The XML *schema* does support per-mark `Red/Green/Blue` (claim 5c is correct), but to emit them via pyrekordbox you must set the attributes on the returned `PositionMark` object after `add_mark()` (e.g. mutate the node's attribs), not pass them as `add_mark` kwargs. The narrative claim "newer XML carries per-mark Red/Green/Blue" stands; only the one-liner API call is wrong.

2. **§2.2 / §4.4 USN helper names — minor.** Deepdive lists `get_local_usn()` / `increment_local_usn()` / "an autoincrement path". Confirmed names in v0.4.4 are `get_local_usn()`, `set_local_usn()`, `increment_local_usn()`, and `autoincrement_usn(set_row_usn=True)` (not `autoincrement_local_usn`). Functionally as described.

3. **§2.4 add/delete "whitelist" — nuance.** v0.4.4 `add()`/`delete()` accept any `tables.Base` instance (no hard table whitelist in those methods). The practical "supported writes" set the deepdive lists matches the convenience `add_*` methods that exist (`add_album/add_artist/add_genre/add_label/add_content/add_to_playlist`) — there is **no `add_cue`**, which is the load-bearing point and is correct. Treat "whitelist" as "the add_* convenience methods that exist," not an enforced guard.

4. **API-name drift note (not a deepdive error).** The *latest* readthedocs (0.4.5.dev) renames the DB class toward `MasterDatabase` and the installer surfaces `install-sqlcipher`. The deepdive targets **0.4.4**, where `Rekordbox6Database` and `download-key` are correct. No correction needed for a 0.4.4-pinned doc, but flag if/when the pin moves.

---

## Summary (5 lines)

1. **XML write path is solid:** `RekordboxXml.add_track()` + `Track.add_mark()` are real and shipped in **0.4.4** — the recommended v1 cue-export path is sound.
2. **One concrete API bug:** `add_mark()` does **not** accept `Red/Green/Blue` (deepdive §4.1 snippet will `TypeError`); the XML *schema* does support per-mark RGB, so set color on the returned `PositionMark`, not via add_mark kwargs.
3. **Direct-DB cue write confirmed unavailable in 0.4.4** (no `add_cue`; only the unmerged `cues` branch, blocked on VBR/ABR `InMpegAbs` → `NotImplementedError`).
4. **Key + DB guardrails confirmed:** single hardcoded SQLCipher key for RB6/7, `python -m pyrekordbox download-key` is a real caching command, `DjmdCue` table + USN columns exist, USN helpers exist, and `commit()` hard-refuses while Rekordbox is running.
5. **XML schema (TRACK/POSITION_MARK/TEMPO incl. RGB) confirmed** against Pioneer's spec; minor USN-helper-name and "whitelist" wording nits noted above. context7 was unavailable — used pyrekordbox repo @ v0.4.4 + docs + Pioneer spec instead.
