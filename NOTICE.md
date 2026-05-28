# NOTICE

vibemix bundles third-party assets under the following licenses. Library and
runtime dependency attributions live in the sibling `NOTICE` file (the
Apache-clean dep manifest); this file holds the bundled-asset attributions
that require per-track licensing acknowledgements.

## CC-BY Audio Assets

The following audio exemplar files are bundled in
`src/vibemix/learn/assets/band_exemplars/` under the Creative Commons
Attribution 4.0 International License (CC-BY-4.0). These tracks are used as
the honest-null fallback when a user's library has fewer than 3 tracks
passing the band-share floor for a given EQ band (Phase 93 EXEMPLAR-03).

> **Sourcing of these tracks is parked as KAAN-ACTION §EXEMPLAR-BANK-SOURCING.**
> Each track that lands MUST carry a corresponding row below AND a matching
> entry in `src/vibemix/learn/assets/band_exemplars/MANIFEST.json`. CI gate:
> `tests/learn/test_exemplar_packaged_fallback.py::test_manifest_attribution_present_in_notice`
> walks the manifest and asserts every entry's `title` + `artist` strings
> appear verbatim in this file.

| Filename | Title | Artist | Source | License |
|----------|-------|--------|--------|---------|
| _none yet — see §EXEMPLAR-BANK-SOURCING_ |  |  |  |  |

## §EXEMPLAR-BANK-SOURCING — KAAN-ACTION ride-forward

The bank directory layout ships empty in Plan 93-04. Populating it is a
licensing question (sourcing 1-4 CC-BY-licensed tracks per band — sub /
low / mid / high — from CC-BY archives like Free Music Archive, ccMixter,
or Wikimedia) rather than an engineering question. The engine code paths
+ honest-null reason + attribution scaffold are all in place; once Kaan
funds the asset acquisition, drop the audio files into
`src/vibemix/learn/assets/band_exemplars/<band>/`, append rows to the
MANIFEST `tracks` dict, and add the corresponding attribution lines here.

CC-BY-4.0 §3(a)(1) requires attribution that includes the creator's name,
the work's title, the URL of the source, and the license. The table
columns above are organized to make that mechanical: one row per file,
all four required attribution elements.

License text: https://creativecommons.org/licenses/by/4.0/legalcode
