# ANLZ cue agreement — PSYMIND hotcue XML

Source: `/Users/ozai/Music/PSYMIND-hotcues.xml`

This is a local Rekordbox-compatible hotcue XML with `POSITION_MARK` DJ cues.
It is product-tagged `vibemix`, not the warmed Rekordbox cache at
`~/.cache/vibemix/library.pkl`.

Bench command:

```sh
PYTHONPATH=src uv run python scripts/eval/anlz_cue_agreement.py \
  --rekordbox-xml /Users/ozai/Music/PSYMIND-hotcues.xml \
  --out .planning/eval-runs/anlz-cue-agreement-psymind-hotcues-20260604-122007/psymind-hotcues.json
```

Result:

- `status`: `ok`
- `cached_tracks`: `44`
- `anlz_matched_cached_tracks`: `44`
- `tracks_with_pssi_anchors`: `44`
- `pssi_anchor_count`: `352`
- `cached_cue_source_counts`: `{"dj": 352}`
- `dj_reference_tracks`: `44`
- `cue_agreement_scored_tracks`: `44`
- `cue_agreement_mean_score`: `0.235919`
- `cue_agreement_mean_abs_offset_s`: `0.591633`
- `cue_agreement_weak_labels`: `452`

Interpretation: this is the first real local `cue_agreement(anlz, dj)` number
we can claim from available local files. The warmed Rekordbox cache still has
no DJ cue references, so its agreement score remains an honest null until a true
Rekordbox XML export with cue marks is imported or the production cache carries
structural DJ cues.
