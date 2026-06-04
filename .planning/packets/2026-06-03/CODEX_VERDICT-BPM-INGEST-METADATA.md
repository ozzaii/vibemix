# CODEX VERDICT - BPM INGEST METADATA

Item: library folder/catalog ingest missing-BPM repair
SHA: f8ba4bb0
Date: 2026-06-04

## User Value

A Pro/Studio user building sets with Viber/AutoCrate now gets BPM metadata for
raw-folder and catalog tracks when the local audio has a convincing kick-band
tempo lock. This reduces `bpm_unknown` receipts before the AI reasons, without
letting Sven cite estimated BPM as live deck proof.

## What Landed

- Added `vibemix.library.tempo_estimator`, wrapping the existing cue engine
  kick-band autocorrelation BPM detector.
- `library embed-folder` and `library ingest` now fill missing BPM by default
  and expose `--no-bpm` opt-outs.
- `TrackEntry.bpm_source` records `kick_ac` provenance.
- `DeckPoller` strips `kick_ac` BPM from live `DeckTrack` the same way it strips
  `numpy_ks` keys, so offline set-prep metadata never becomes citable live proof.

## Proof

Tests:

```text
uv run ruff check src/vibemix/library/tempo_estimator.py src/vibemix/library/folder_ingest.py src/vibemix/library/ingest.py src/vibemix/library/rekordbox.py src/vibemix/state/deck_poller.py tests/library/test_tempo_estimator.py tests/library/test_folder_ingest.py tests/library/test_ingest.py tests/state/test_deck_poller.py
# All checks passed

uv run pytest -q tests/library/test_tempo_estimator.py tests/library/test_folder_ingest.py tests/library/test_ingest.py tests/state/test_deck_poller.py
# 67 passed

uv run pytest -q tests/library tests/state/test_deck_poller.py tests/memory/test_no_live_path_import.py
# 1102 passed

git diff --check
# clean
```

Real current-source artifact:

```text
HOME=/tmp/vibemix-bpm-proof.WYZnBm/home \
uv run python -m vibemix library embed-folder \
  /tmp/vibemix-bpm-proof.WYZnBm/music --json
```

The run generated a 138 BPM WAV, used the real CLI/CLAP ingest path in an
isolated HOME, then loaded the written `library.pkl`:

```json
{
  "title": "proof-138",
  "bpm": 138.0,
  "bpm_source": "kick_ac",
  "key": "",
  "key_source": ""
}
```

The CLI report included:

```json
"bpm_estimation": {
  "estimated": 1,
  "failed": 0
}
```

## Caveat

This repairs new ingest/reindex runs. An existing `library.pkl` with zero BPMs
will keep those zeroes until the user reimports/reindexes the folder/library.
