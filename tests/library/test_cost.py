# SPDX-License-Identifier: Apache-2.0
"""Live-stack cost model — per-turn → per-session → per-DJ-month → fleet.

The cache-blend is the load-bearing insight (Kaan, 2026-05-30): with ~90%
implicit cache hits across a continuous set, the input leg collapses ~5-9x. The
production voice is now local MOSS, so paid TTS appears only as an explicit
what-if sensitivity row.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from vibemix.library.pricing import price_for_model, price_for_path


def test_brain_reaction_cost_applies_the_cache_blend() -> None:
    """A reaction's brain cost blends cached + fresh input at the cache-hit rate;
    output is never cached."""
    from vibemix.library.cost import brain_reaction_usd

    row = price_for_path("live_coach")  # 1.50 in / 9.00 out / 0.15 cached (USD/1M)
    usd = brain_reaction_usd(
        row, input_tokens=1900, output_tokens=40, cache_hit_rate=0.90
    )
    # effective input rate = 0.9*0.15 + 0.1*1.50 = 0.285 /1M
    # input  = 1900 * 0.285 / 1e6 = 0.0005415
    # output = 40   * 9.00  / 1e6 = 0.00036
    assert usd == pytest.approx(0.0009015, rel=1e-9)


def test_brain_cost_falls_with_a_higher_cache_hit_rate() -> None:
    """The whole point of caching: more hits ⇒ strictly cheaper input."""
    from vibemix.library.cost import brain_reaction_usd

    row = price_for_path("live_coach")
    hot = brain_reaction_usd(row, input_tokens=1900, output_tokens=40, cache_hit_rate=0.95)
    cold = brain_reaction_usd(row, input_tokens=1900, output_tokens=40, cache_hit_rate=0.0)
    assert hot < cold


def test_tts_reaction_cost_gemini_is_audio_token_billed() -> None:
    """Paid Gemini TTS what-if bills the spoken audio per token plus the small
    text-input charge for the words it speaks."""
    from vibemix.library.cost import tts_reaction_usd

    row = price_for_model("live_coach_tts_fallback")  # 0.50 text-in / 10.00 audio-out /1M
    usd = tts_reaction_usd(row, speech_seconds=12.0, text_tokens=40)
    # audio = 12 * 25 = 300 tok * 10.00 / 1e6 = 0.003
    # text  = 40 * 0.50 / 1e6 = 0.00002
    assert usd == pytest.approx(0.00302, rel=1e-9)


def test_tts_reaction_cost_moss_local_is_zero_provider_bill() -> None:
    """MOSS is local/on-device, so provider TTS cost is explicitly zero."""
    from vibemix.library.cost import tts_reaction_usd
    from vibemix.library.pricing import price_for_model

    row = price_for_model("moss-local")
    assert tts_reaction_usd(row, speech_seconds=12.0, text_tokens=40) == 0.0


def test_tts_reaction_cost_vendor_is_per_character() -> None:
    """Per-character vendors (ElevenLabs/Hume) bill the spoken characters."""
    from vibemix.library.cost import tts_reaction_usd
    from vibemix.library.pricing import price_for_model

    row = price_for_model("eleven_flash_v2_5")  # $50/1M char
    usd = tts_reaction_usd(row, speech_seconds=12.0, chars_per_second=14.0)
    # 12 * 14 = 168 char * 50 / 1e6 = 0.0084
    assert usd == pytest.approx(0.0084, rel=1e-9)


def test_listen_cost_gemini_audio_part_uses_brain_audio_input_rate() -> None:
    """The default STT fork — mic→Gemini audio Part — is billed as the brain's
    audio-input tokens, NOT a separate vendor."""
    from vibemix.library.cost import listen_reaction_usd

    brain = price_for_path("live_coach_cand_25flash")  # audio_input 1.00/1M
    usd = listen_reaction_usd(audio_in_seconds=18.0, brain_row=brain)
    # 18 * 25 = 450 tok * 1.00 / 1e6 = 0.00045
    assert usd == pytest.approx(0.00045, rel=1e-9)


def test_listen_cost_dedicated_stt_is_per_minute_and_dearer() -> None:
    """A dedicated STT bills per audio-minute — and here costs MORE than the
    mic→Gemini Part, confirming the Part is the cost-sane default."""
    from vibemix.library.cost import listen_reaction_usd
    from vibemix.library.pricing import price_for_model

    brain = price_for_path("live_coach_cand_25flash")
    stt = price_for_model("nova-3-streaming")  # $0.0048/min
    part = listen_reaction_usd(audio_in_seconds=18.0, brain_row=brain)
    dedicated = listen_reaction_usd(audio_in_seconds=18.0, brain_row=brain, stt_row=stt)
    # 18/60 * 0.0048 = 0.00144
    assert dedicated == pytest.approx(0.00144, rel=1e-9)
    assert dedicated > part


def test_listen_cost_falls_back_to_input_rate_when_no_separate_audio_rate() -> None:
    """A model with no SEPARATE audio-in rate (gemini-3.5-flash) still bills the
    audio as input tokens at its standard input rate — NEVER free."""
    from vibemix.library.cost import listen_reaction_usd

    brain = price_for_path("live_coach")  # audio_input None, input 1.50/1M
    usd = listen_reaction_usd(audio_in_seconds=18.0, brain_row=brain)
    # 18 * 25 = 450 tok * 1.50 / 1e6 = 0.000675  (not 0)
    assert usd == pytest.approx(0.000675, rel=1e-9)
    assert usd > 0


def _default_inputs():
    """The cost-sane default live stack: cheap Gemini brain + local MOSS voice +
    mic→Gemini Part STT + DeepSeek Viber, at the bench-measured turn profile."""
    from vibemix.library.cost import LiveStackSpec, TurnProfile, UsageProfile

    spec = LiveStackSpec(
        live_brain_path="live_coach_cand_25flash",
        tts_path="moss-local",
        stt="gemini_part",
        viber_model="deepseek-v4-pro",
    )
    turn = TurnProfile(
        input_tokens=1900, output_tokens=40, speech_seconds=12.0,
        audio_in_seconds=18.0, cache_hit_rate=0.90,
    )
    usage = UsageProfile(
        reactions_per_set=80, sessions_per_month=20,
        viber_calls_per_month=20, viber_input_tokens=4000,
        viber_output_tokens=1200, viber_cache_hit_rate=0.90,
    )
    return spec, turn, usage


def test_compute_live_cost_legs_sum_to_the_monthly_total() -> None:
    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    bd = compute_live_cost(spec, turn, usage, dau=10_000)
    leg_sum = sum(leg.per_dj_month_eur for leg in bd.legs)
    assert leg_sum == pytest.approx(bd.total_per_dj_month_eur, rel=1e-9)
    assert {leg.name for leg in bd.legs} == {"brain", "listen", "tts", "viber", "livekit"}


def test_livekit_leg_is_zero_in_direct_mode() -> None:
    """vibemix runs the LiveKit pipeline LOCALLY (direct mode — no Cloud room),
    so the LiveKit leg is an explicit €0, never a silent omission."""
    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    bd = compute_live_cost(spec, turn, usage, dau=10_000)
    lk = next(leg for leg in bd.legs if leg.name == "livekit")
    assert lk.per_dj_month_eur == 0.0


def test_livekit_cloud_rate_adds_a_real_leg_scaling_with_set_minutes() -> None:
    """The what-if: IF LiveKit Cloud were used, its per-minute rate bills the full
    set length — surfaced so the local-vs-cloud choice is costed, not assumed."""
    from dataclasses import replace

    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    cloud = compute_live_cost(
        replace(spec, livekit_per_min_usd=0.005), turn, usage, dau=10_000
    )
    lk = next(leg for leg in cloud.legs if leg.name == "livekit")
    # set_minutes 75 default * $0.005/min * 0.92 = 0.345 / session
    assert lk.per_session_eur == pytest.approx(75 * 0.005 * 0.92, rel=1e-9)
    assert lk.per_session_eur > 0


def test_listen_is_the_dominant_leg_for_the_default_moss_stack() -> None:
    """With MOSS local, listening/audio-in becomes the dominant paid leg."""
    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    bd = compute_live_cost(spec, turn, usage, dau=10_000)
    assert bd.dominant_leg == "listen"


def test_fleet_scales_linearly_with_dau() -> None:
    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    one = compute_live_cost(spec, turn, usage, dau=1)
    many = compute_live_cost(spec, turn, usage, dau=10_000)
    assert many.fleet_month_eur == pytest.approx(
        one.total_per_dj_month_eur * 10_000, rel=1e-9
    )


def test_fleet_at_10k_reflects_moss_removing_paid_tts() -> None:
    """The MOSS default should be far below the old paid-Gemini-TTS anchor."""
    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    bd = compute_live_cost(spec, turn, usage, dau=10_000)
    assert 5_000 <= bd.fleet_month_eur <= 20_000


def test_premium_tts_swap_moves_the_fleet_more_than_a_premium_brain_swap() -> None:
    """Decision-grade: adding paid TTS changes the fleet bill far more than
    switching the brain tier — because MOSS removes the default voice bill."""
    from dataclasses import replace

    from vibemix.library.cost import compute_live_cost

    spec, turn, usage = _default_inputs()
    base = compute_live_cost(spec, turn, usage, dau=10_000).fleet_month_eur
    premium_tts = compute_live_cost(
        replace(spec, tts_path="eleven_flash_v2_5"), turn, usage, dau=10_000
    ).fleet_month_eur
    premium_brain = compute_live_cost(
        replace(spec, live_brain_path="live_coach"), turn, usage, dau=10_000
    ).fleet_month_eur
    assert (premium_tts - base) > (premium_brain - base)


def test_sensitivity_covers_the_named_axes_and_carries_the_unverified_flag() -> None:
    from vibemix.library.cost import sensitivity_rows

    spec, turn, usage = _default_inputs()
    rows = sensitivity_rows(spec, turn, usage, dau=10_000)
    axes = {r.axis for r in rows}
    assert {"tts", "stt", "brain", "cache_hit", "viber"} <= axes
    # The Cartesia row's UNVERIFIED status must survive into the table.
    cartesia = [r for r in rows if "cartesia" in r.label.lower() or "sonic" in r.label.lower()]
    assert cartesia and cartesia[0].verified is False


def test_sensitivity_lower_cache_hit_costs_more() -> None:
    from vibemix.library.cost import sensitivity_rows

    spec, turn, usage = _default_inputs()
    rows = sensitivity_rows(spec, turn, usage, dau=10_000)
    cache = {r.label: r.fleet_month_eur for r in rows if r.axis == "cache_hit"}
    assert cache["0%"] > cache["95%"]


def test_live_budget_report_is_a_complete_serializable_dict() -> None:
    """The CLI/JSON surface: breakdown + sensitivity + the echoed assumptions
    (so the reader sees exactly what the numbers rest on)."""
    import json

    from vibemix.library.cost import live_budget_report

    spec, turn, usage = _default_inputs()
    rep = live_budget_report(spec, turn, usage, dau=10_000)

    assert rep["dau"] == 10_000
    assert rep["mode"] == "live_stack"
    assert len(rep["legs"]) == 5
    assert rep["dominant_leg"] in {"brain", "listen", "tts", "viber", "livekit"}
    assert "fleet_month_eur" in rep["totals"]
    assert len(rep["sensitivity"]) > 5
    # The assumptions the bill rests on are echoed back, not hidden.
    for k in ("input_tokens", "output_tokens", "cache_hit_rate", "reactions_per_set"):
        assert k in rep["assumptions"]
    assert set(rep["stack"]) == {"brain", "tts", "stt", "viber"}
    # Round-trips through JSON (the --json path must not choke).
    json.dumps(rep)


@pytest.mark.cli
def test_live_budget_cli_defaults_to_moss_local_voice() -> None:
    """The real CLI default must match the product voice policy: MOSS-only."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vibemix",
            "library",
            "budget",
            "--stack",
            "live",
            "--dau",
            "100",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["stack"]["tts"] == "moss-local"
    tts_leg = next(leg for leg in payload["legs"] if leg["name"] == "tts")
    assert tts_leg["per_session_eur"] == 0.0
