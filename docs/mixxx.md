# Cue export to Mixxx, Serato, and Rekordbox

vibemix detects structural hot cues (INTRO / BUILD / BREAKDOWN / DROP / OUTRO)
from the audio itself and hands them off to your DJ software. This page is about
getting those cues into **Mixxx** specifically — and why the route that reaches
Mixxx is the same one that reaches Serato and Rekordbox in a single write.

## Why Mixxx is the odd one out

Rekordbox and Serato can both import a Rekordbox `collection.xml`. Mixxx cannot.
Mixxx does not read a Rekordbox XML off disk — point it at one and nothing
happens. So the obvious "export an XML" route lights up Pioneer's world and
leaves Mixxx dark.

The bridge that actually reaches all three is not a file on the side — it is the
cue data written **into the audio file** as Serato `Markers2` tags. Mixxx 2.3+,
Serato, and Rekordbox all auto-import hot cues from those tags the moment a track
loads, with no database write on their end. One tag write per file, three
ecosystems lit. That is the route for Mixxx.

## The three export routes

vibemix can hand cues off three ways. They differ in what they carry and who
reads them:

| Route | Carries | Reaches | How it lands |
|-------|---------|---------|--------------|
| **Rekordbox XML** (`collection.xml`) | hot cues + titles | Rekordbox, Pioneer hardware (via USB export), Serato (imports rekordbox xml) | File → Import → rekordbox xml. Additive — your collection is never edited in place. **Mixxx ignores it.** |
| **M3U8 playlist** | track order + titles only — **no cues** | any player, including Mixxx and Serato | imported as a new additive playlist/crate. Order only; the cues ride elsewhere. |
| **Serato Markers2 tags** | hot cues, written into the audio file | **Mixxx 2.3+ + Serato + Rekordbox** | auto-imported from the file on load. No DB write anywhere. One write, three ecosystems. |

In `src/vibemix/library/cue_folder.py`:

- `export_cued_folder(..., export="rekordbox"|"m3u8"|"both")` writes the XML
  and/or the M3U8. The XML carries the cues; the M3U8 is order-only.
- `write_m3u8(tracks, out_path)` is the neutral order-only writer — every entry
  is `#EXTINF:-1` because the cue path never measures track duration.
- `tag_folder_serato(folder, ...)` is the Markers2 route — the one that reaches
  Mixxx. It walks the folder, auto-cues each track, and writes the cues into the
  files.

The cue colors and pad labels are single-sourced from `cue_export.py`
(`_LABEL_COLORS` / `_LABEL_TO_MARK_NAME`), so a DROP pad is the same red and the
same `DROP` label whether it landed via the Rekordbox XML or the Serato tag.

## Opt-in and merge safety

The Rekordbox XML and the M3U8 are new files vibemix writes next to your
library — they touch nothing you own. The Serato tag route is different: it
**mutates your audio file** to embed the cues. Because of that it is gated:

- **Opt-in.** `write_serato_cues` / `tag_folder_serato` do nothing unless
  `allow_write=True` is passed — surfaced as a `--write-tags` flag when the CLI
  ships. Call it without that and you get back `{"written": False, "reason":
  "opt-in required..."}`, never a silent file edit.
- **Merge by default.** Cues are unioned by pad index. vibemix's cues win on the
  pads it writes; every other pad — anything you hot-cued by hand — is read back
  off the file and preserved. vibemix never clobbers a hand-set cue
  (`_merge_cues` in `export_serato.py`). It also keeps any other `GEOB` frames in
  the file intact and only replaces the `Serato Markers2` one.
- **Format scope in v1.** Tag-writing covers `.mp3`, `.aif`, and `.aiff`
  (ID3 containers). A FLAC or MP4 file comes back `{"written": False}` with a
  reason — those carriers are a follow-up, not a silent skip.

Serato cue positions are stored in milliseconds and are sample-rate independent,
so the same tag reads correctly regardless of the file's sample rate — no
per-file SR bookkeeping, unlike a direct database write would need.

## Installing the Serato extra

Writing Serato tags needs `mutagen` to write the ID3 container. It is an opt-in
extra because **mutagen is GPL-2.0-or-later** — vibemix's own tree is Apache-2.0,
and mutagen stays a runtime dependency that is lazy-imported and never vendored
into the source. The Markers2 binary payload itself is reimplemented from the
documented, reverse-engineered format, so no GPL parser code is copied in.

Install it with the project runner (the uv venv has no `pip`):

```bash
uv pip install -e ".[serato]"
```

or pull it in as part of a wider install (`.[ai-local]` covers the on-device
model path; add `serato` when you want tag-writing):

```bash
uv pip install -e ".[ai-local,serato]"
```

Without the extra, the cue-detection and the Rekordbox/M3U8 routes still work —
only `tag_folder_serato` will fail at the `mutagen` import, actionably.

## Honest status

- **The cue CLI subcommand is not wired yet.** There is no `library cue <folder>`
  subparser and no `--write-tags` flag in `src/vibemix/__main__.py` today. The
  `cue` strings you'll find in the CLI are `embed-folder --strategy cue_anchored`
  (cue-anchored embedding) and `library models --install cue` (the CUE-DETR
  detection model) — both unrelated to folder cue export. The engine and the
  Python API below are shipped and tested; the CLI surface is coming.

  Until it lands, drive it from Python:

  ```python
  from vibemix.library.cue_folder import export_cued_folder, tag_folder_serato

  # Rekordbox + a neutral M3U8 (no file mutation):
  report = export_cued_folder("~/Music/crate", "out.xml", export="both")
  print(report.tracks_cued, report.cues_total, report.outputs)

  # Serato tags — reaches Mixxx + Serato + Rekordbox (mutates your files):
  counts = tag_folder_serato("~/Music/crate", allow_write=True)
  print(counts)  # {"tagged": ..., "cues_total": ..., "skipped": ..., "scanned": ...}
  ```

  A track the engine finds no cues in produces no output — vibemix never
  fabricates a placeholder cue (Invariant #3: trust the audio). Per-file decode
  errors are recorded and skipped, never fatal.

- **The bytes are spec-conformant and round-trip tested; the pad render is a
  one-time eye-check.** The Markers2 encoder/decoder is asserted against the
  documented byte layout and round-trips encode→decode in tests. Whether a
  *specific* Mixxx or Serato build draws the pad on the deck is a human
  eye-check you do once per target build — green tests prove the format is
  correct, not that any given app drew it.
