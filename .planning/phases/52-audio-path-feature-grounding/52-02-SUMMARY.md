# 52-02 SUMMARY — Add psytrance genre profile (GENRE-01 data layer)

**Requirements:** GENRE-01
**Status:** complete

## What shipped

`src/vibemix/state/genre/profiles/psytrance.json` — the missing profile that
was the direct cause of Kaan's psytrance misclassification (the library held
only disco/drum_and_bass/house/pop/techno, so psy ran under techno's wrong
band-signature + phase thresholds).

## Final values shipped + grounding rationale (vs techno)

| field | psytrance | techno | why |
|---|---|---|---|
| bpm_range | [138, 150] | [125, 175] | psy's tight full-on/Goa tempo band; fully inside [100,180] |
| band_signature.sub | [0.30, 0.50] | [0.25, 0.45] | heavier offbeat-rolling-bass — the discriminator |
| band_signature.mid | [0.08, 0.20] | [0.10, 0.25] | lighter mid (less groove-clap energy) |
| expected_crest_factor | [4.0, 7.0] | [3.5, 6.5] | punchier transients on the rolling bassline |
| build_climb_threshold | 0.028 | 0.025 | steeper psy builds |
| drop_jump_threshold | 0.065 | 0.060 | sharper drops |
| absolute_thresholds | mirrored from techno | — | RMS scale is genre-agnostic |

Band-signature midpoint sum = 0.915 (within the [0.85, 1.10] sanity bound). The
heavier-sub / lighter-mid contrast vs techno is what lets the Plan 52-03
detector discriminate psy from techno on band shape (BPM bands overlap).

## Validates via the hand-written `_parse_profile` (no pydantic)

`load_profile('psytrance')` returns a valid frozen `GenreProfile` — load goes
through `_parse_profile` (Critical Constraint 6: no new heavy deps). A dedicated
test (`test_psytrance_raw_json_passes_handwritten_validator`) re-validates the
raw JSON directly through `_parse_profile` so future schema drift is caught.

## The count-assertion fix that kept the suite green (the landmine)

`tests/state/test_genre_profile.py` hard-asserted exactly 5 profiles. Adding
psytrance.json makes `list_profiles()` return 6 (psytrance sorts between pop and
techno). Updated:
- `PROFILE_NAMES` 5 → 6 (includes psytrance).
- `test_list_profiles_returns_all_five` → `..._returns_all_six`.
- The parametrized per-profile sanity loops (band-sum / bpm-range / crest /
  RMS-order / round-trip) now also cover psytrance and pass.

## Verification (observed)

- `pytest -q tests/state/test_psytrance_profile.py` → **7 passed**.
- `pytest -q tests/state/test_genre_profile.py` → **51 passed** (was 45; the
  +6 are the parametrized loops now covering psytrance).
- `list_profiles()` → `['disco','drum_and_bass','house','pop','psytrance','techno']`.

## Commits (3 atomic)

- `b75d3da` feat(52-02): add psytrance genre profile (GENRE-01).
- `a66b799` test(52-02): pin psytrance profile loads + validates with locked values (GENRE-01).
- `9ed792b` test(52-02): expand profile-count assertion to include psytrance (GENRE-01).
