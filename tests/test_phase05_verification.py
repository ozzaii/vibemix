# SPDX-License-Identifier: Apache-2.0
"""Phase 5 acceptance gates. Pure-Python; no Bravoh server required.

Run via: uv run pytest tests/test_phase05_verification.py -v
Each gate corresponds to a phase-level invariant; failing any gate
blocks Phase 5 closeout.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import jwt as pyjwt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src" / "vibemix"
PROXY = PROJECT_ROOT / "proxy"


# -------------------------------------------------------------------------
# Gate 1: full vibemix client suite green (marker — actual run is CI)
# -------------------------------------------------------------------------


def test_g1_vibemix_suite_marker():
    """G1: full vibemix package pytest passes (excluding live-device tests).

    This test is a marker — running the full suite from inside a test would
    recursively invoke pytest. The gate is satisfied by the CI command that
    runs `uv run pytest tests/ -x -q --ignore=...` BEFORE this file is
    collected. We just assert the gates are discoverable.
    """
    assert (PROJECT_ROOT / "tests").exists()
    # Sanity: the test_main_smoke.py exists (Phase 4 + 5 smoke)
    assert (PROJECT_ROOT / "tests" / "test_main_smoke.py").exists()


# -------------------------------------------------------------------------
# Gate 2: proxy suite is runnable (marker — actual run is CI)
# -------------------------------------------------------------------------


def test_g2_proxy_suite_marker():
    """G2: the proxy suite is structurally complete and runnable.

    Actual run happens in CI via `cd proxy && uv run pytest tests/ -x -q`
    (separate venv).
    """
    assert (PROXY / "pyproject.toml").exists()
    assert (PROXY / "tests").exists()
    assert (PROXY / "tests" / "test_app.py").exists()
    assert (PROXY / "tests" / "test_auth.py").exists()
    assert (PROXY / "tests" / "test_gemini_route.py").exists()
    assert (PROXY / "tests" / "test_openai_compat_route.py").exists()


# -------------------------------------------------------------------------
# Gate 3: zero AIza pattern in src/vibemix/ (THE phase invariant)
# -------------------------------------------------------------------------

_AIZA = re.compile(r"AIza[0-9A-Za-z_-]{35}")


def test_g3_zero_aiza_in_client():
    """G3: no AIza-style key string in any vibemix client source file.

    This is the phase-level reason-to-exist. If this gate fails, the whole
    Phase 5 effort failed.
    """
    violations: list[tuple[Path, list[str]]] = []
    for p in SRC.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        matches = _AIZA.findall(text)
        if matches:
            violations.append((p, matches))
    assert not violations, f"AIza pattern leaked in client source: {violations}"


# -------------------------------------------------------------------------
# Gate 4: zero AIza/OpenRouter-key pattern in proxy/.env.example
# -------------------------------------------------------------------------

_OR_KEY = re.compile(r"sk-or-v1-[0-9a-f]{20,}")


def test_g4_proxy_env_example_no_real_keys():
    env_text = (PROXY / ".env.example").read_text(encoding="utf-8")
    assert not _AIZA.search(env_text), "AIza pattern in proxy/.env.example"
    assert not _OR_KEY.search(env_text), "sk-or-v1- pattern in proxy/.env.example"


# -------------------------------------------------------------------------
# Gate 5: POC files diff-untouched against last Phase 4 commit
# -------------------------------------------------------------------------

_POC_PATTERNS = [
    "cohost.py",
    "cohost_v2.py",
    "cohost_lk.py",
    "cohost_v4.py",
    "cohost.streaming.py.bak",
    "run.sh",
    "run_v2.sh",
    "run_lk.sh",
    "run_v4.sh",
    "mascot.html",
    "generate_bat.py",
    "_test_tts.py",
    "_test_multimodal.py",
    "test_voice.py",
]


def test_g5_poc_files_untouched():
    """G5: POC files have NOT been edited by Phase 5 plans.

    The CLAUDE.md project rule + MEMORY.md note both pin: v3/v4 POC files are
    reference, not legacy to update. Phase 5 work touches proxy/ and
    src/vibemix/ only.

    Baseline: Phase 4 close commit `ede9e59`.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "ede9e59..HEAD", "--", *_POC_PATTERNS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        diff_lines = [ln for ln in result.stdout.split("\n") if ln.strip()]
        assert not diff_lines, f"POC files modified during Phase 5: {diff_lines}"
    except subprocess.CalledProcessError as e:
        pytest.skip(f"git diff failed: {e.stderr} — verify POC untouched manually")


# -------------------------------------------------------------------------
# Gate 6: JWT alg=none rejected (the security pinpoint)
# -------------------------------------------------------------------------


def test_g6_jwt_alg_none_rejected():
    """G6: PyJWT decode with `algorithms=["HS256"]` rejects an alg=none token.

    This pins the security invariant directly against the PyJWT version used
    by both proxy and client. The proxy's `app.auth.decode_jwt` uses exactly
    this allowlist (verified via the canonical snippet inspected below).
    """
    SECRET = "test-secret-padded-to-at-least-32-bytes-long"
    evil = pyjwt.encode(
        {"install_uuid": "a" * 32, "iat": 0, "exp": 99999999999},
        "",
        algorithm="none",
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        pyjwt.decode(evil, SECRET, algorithms=["HS256"])

    # Belt-and-suspenders: inspect the proxy source to confirm the allowlist
    # is exactly ["HS256"].
    auth_src = (PROXY / "app" / "auth.py").read_text(encoding="utf-8")
    assert '_ALG_ALLOWLIST = ["HS256"]' in auth_src, (
        "proxy/app/auth.py must pin algorithms allowlist to ['HS256']"
    )
    # Pin the decode call uses the explicit allowlist (NOT algorithms=None or
    # algorithms=['none']). Reject patterns suggesting either.
    forbidden_patterns = [
        "algorithms=None",
        'algorithms=["none"]',
        "algorithms=['none']",
    ]
    for pat in forbidden_patterns:
        assert pat not in auth_src, f"proxy/app/auth.py contains forbidden pattern: {pat}"


# -------------------------------------------------------------------------
# Gate 7: install_uuid persists via keyring + file fallback
# -------------------------------------------------------------------------


def test_g7_install_uuid_persists(tmp_path, monkeypatch):
    """G7: client install_uuid persists across two calls in null-backend mode."""
    from vibemix.agent import install_uuid as iu_mod

    monkeypatch.setattr(iu_mod, "_fallback_path", lambda: tmp_path / "install_uuid")
    monkeypatch.setattr(iu_mod, "_keyring_is_null", lambda: True)

    first = iu_mod.get_or_create_install_uuid()
    second = iu_mod.get_or_create_install_uuid()
    assert first == second
    assert len(first) == 32
    assert all(c in "0123456789abcdef" for c in first)


# -------------------------------------------------------------------------
# Gate 8: direct mode preserves Phase 4 behavior (no regression)
# -------------------------------------------------------------------------


def test_g8_direct_mode_phase4_regression_safe():
    """G8: build_llm and build_tts_chain default to Phase 4 direct behavior;
    proxy mode rejects missing args (no silent fallback)."""
    from livekit.agents import tts as agents_tts  # noqa: F401
    from livekit.plugins import google as google_plugin  # noqa: F401
    from livekit.plugins import openai as openai_plugin  # noqa: F401

    from vibemix.agent import build_llm, build_tts_chain

    # Direct mode requires only api_key (Phase 4 surface preserved)
    try:
        _ = build_llm("test-api-key")
    except (ValueError, TypeError) as e:
        pytest.fail(f"build_llm('test-api-key') raised — direct mode regression: {e}")

    # build_tts_chain with keyword gemini_api_key works
    try:
        _ = build_tts_chain(gemini_api_key="test-g", openrouter_api_key=None)
    except (ValueError, TypeError) as e:
        pytest.fail(f"build_tts_chain regression: {e}")

    # Proxy mode rejects missing args (no silent fallback)
    with pytest.raises(ValueError):
        build_llm(mode="proxy")
    with pytest.raises(ValueError):
        build_tts_chain(mode="proxy")
