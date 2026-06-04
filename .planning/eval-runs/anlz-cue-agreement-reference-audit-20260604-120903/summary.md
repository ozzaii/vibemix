# ANLZ cue-agreement reference audit

Status: `honest_null_no_dj_reference_cues`. ANLZ PSSI first-fill is available for `45` cached tracks (`360` anchors), but the local library has `0` DJ-reference tracks, so a numeric `cue_agreement(anlz, dj)` score is not claimable.

Reference audit:

```json
{
  "anlz_sidecar_pcob_pco2_dj_anchor_count": 0,
  "anlz_sidecar_tracks_with_pcob_pco2_dj_cues": 0,
  "cache_structural_dj_anchor_count": 0,
  "cache_tracks_with_structural_dj_cues": 0,
  "missing_reference_reason": "cache has no structural DJ cues and matched ANLZ sidecars have no PCOB/PCO2 DJ cue entries",
  "numeric_agreement_claimable": false
}
```
