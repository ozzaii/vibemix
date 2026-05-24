# SPDX-License-Identifier: Apache-2.0
"""Phase 70 Plan 70P05 — GH-05 one-stop GitHub front-porch presence suite.

This is "GitHub sexified, generated, tested" encoded in code: a single CI gate
that pins everything Waves 0-3 of Phase 70 produced (plus the four Phase 69 OSS
files) so a stranger landing on the README always sees a coherent, non-rotted
front porch. Asset deletion, hash drift, a broken badge, a malformed issue
template, or a missing OSS file all fail CI here.

What this suite pins
--------------------
1. Every README badge URL returns HTTP 200          (network-marked)
2. Demo asset present + under the <=8MB size cap     (PLACEHOLDER-tolerant)
3. OG image present + sha256 matches MANIFEST.yaml
4. README hero hash matches the sentinel             (via check_readme_hero_hash)
5. Every .github/ISSUE_TEMPLATE/*.yml is valid GitHub Forms shape
6. .github/pull_request_template.md exists + non-empty
7. The four P69 OSS files exist + are README-linked

CONTEXT reconciliation #1 (doc-vs-reality) — READ BEFORE EDITING
----------------------------------------------------------------
The ROADMAP SC5 wording assumes the OLD GitHub issue-template format:
`.github/ISSUE_TEMPLATE/*.md` with `---\nname:\nabout:\n---` front-matter.
REALITY: the repo uses GitHub **Issue Forms** — `.github/ISSUE_TEMPLATE/*.yml`
with the Forms schema (`name:` + `description:` + `body:`). This suite validates
the ACTUAL `.yml` Forms shape (yaml.safe_load + name/description/body keys), NOT
`.md` `about:` front-matter. `config.yml` is the special Issue-Forms *config*
file (`blank_issues_enabled:` / `contact_links:`) — it is NOT a form and is
EXCLUDED from the Forms validation (validated separately for its own shape).

Network discipline
-------------------
Only `test_readme_badge_urls_resolve_200` is `@pytest.mark.network`. It is
DESELECTED from the default offline `pytest -q` grid (Phase 67/68 marker
convention) and runs in CI with network. Everything else runs offline-clean.

Intentional overlap
--------------------
`test_four_oss_files_present_and_linked` deliberately overlaps
tests/repo/test_oss_presence.py — GH-05 is the *one-stop* suite per the ROADMAP,
so it re-asserts the OSS-file presence under one roof. The overlap is by design.

Run with:
    PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m "not network"
    PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m network   # CI w/ network
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# Shared constants
# --------------------------------------------------------------------------- #

_DEMO_SIZE_CAP_BYTES: int = 8 * 1024 * 1024  # 8 MiB == 8388608 (ROADMAP P70)
_PLACEHOLDER_SENTINEL: str = "PLACEHOLDER"

# The four P69 OSS-01 canonical docs (mirrors tests/repo/test_oss_presence.py;
# overlap is intentional — GH-05 is the one-stop suite).
_REQUIRED_OSS_FILES: list[str] = [
    "MAINTAINERS.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]
_OSS_MIN_BYTES: int = 200

# GitHub Issue Forms config file — NOT a form; excluded from Forms validation.
_ISSUE_FORMS_CONFIG: str = "config.yml"

# README badge URLs extracted dynamically below so the test never drifts behind
# an edit to the README badge block.
_BADGE_SRC_RE = re.compile(r'src="(https://img\.shields\.io/[^"]+)"')


def _readme_text() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _badge_urls() -> list[str]:
    """Every shields.io badge URL referenced from README.md (deduped, ordered)."""
    urls = _BADGE_SRC_RE.findall(_readme_text())
    # dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _issue_form_yml_files() -> list[Path]:
    """Every .github/ISSUE_TEMPLATE/*.yml EXCEPT the special config.yml."""
    tmpl_dir = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
    return sorted(
        p for p in tmpl_dir.glob("*.yml") if p.name != _ISSUE_FORMS_CONFIG
    )


# --------------------------------------------------------------------------- #
# 1. Badge URLs (network-marked — deselected from the default offline grid)
# --------------------------------------------------------------------------- #


@pytest.mark.network
@pytest.mark.parametrize("url", _badge_urls())
def test_readme_badge_urls_resolve_200(url: str) -> None:
    """Every README shields.io badge URL returns HTTP 200.

    Network-marked: the default offline `pytest -q` grid DESELECTS this; CI runs
    it with network. `timeout=5` keeps a hung shields.io from stalling CI
    (T-70P05-03 DoS mitigation). `requests` is a transitive dep of the
    google-genai/httpx ecosystem; importorskip keeps a minimal env green.
    """
    requests = pytest.importorskip("requests")
    resp = requests.get(url, timeout=5)
    assert resp.status_code == 200, (
        f"README badge URL did not return 200: {url} "
        f"(got {resp.status_code}). A dead badge rots the front porch — fix the "
        "URL in README.md or the workflow it points at."
    )


def test_at_least_one_badge_url_present() -> None:
    """Sanity: the README badge block has not been silently emptied.

    Guards against a vacuous network test (zero parametrize cases would make
    test 1 collect nothing and pass trivially). Offline — always runs.
    """
    urls = _badge_urls()
    assert len(urls) >= 5, (
        f"Expected >=5 shields.io badges in README.md, found {len(urls)}. "
        "The badge block (release/build/license/platforms/stars + the "
        "supply-chain row) appears to have been stripped."
    )


# --------------------------------------------------------------------------- #
# 2. Demo asset present + size cap (PLACEHOLDER-tolerant)
# --------------------------------------------------------------------------- #


def test_demo_poster_present() -> None:
    """The Wave 3 (70P04) CDJ-Whisper poster still is committed + non-trivial.

    The README hero <video poster=> + <img> fallback point at this PNG; it
    carries the visual until Francesco's real demo.mp4 lands (§ASSETS-DEMO-CUT).
    """
    poster = REPO_ROOT / "docs" / "assets" / "demo-poster.png"
    assert poster.is_file(), (
        f"Missing demo poster at {poster.relative_to(REPO_ROOT)}. "
        "Wave 3 (Plan 70P04) ships this CDJ-Whisper still."
    )
    assert poster.stat().st_size > 1024, (
        "docs/assets/demo-poster.png is suspiciously small (<1KB); placeholder?"
    )


def test_demo_asset_under_size_cap_or_placeholder() -> None:
    """The hero demo asset is <=8MB once it lands; PLACEHOLDER tolerated until then.

    Under autonomous mode the real docs/assets/demo.mp4 is gated on Francesco's
    capture day (§ASSETS-DEMO-CUT). Until it lands, the README hero sentinel is
    `sha256=PLACEHOLDER` and this gate TOLERATES the missing .mp4 (T-70P05-04
    accept). When the real film lands, the <=8388608-byte cap activates and the
    sha256=PLACEHOLDER sentinel must flip (enforced by check_readme_hero_hash.py).
    """
    demo = REPO_ROOT / "docs" / "assets" / "demo.mp4"
    readme = _readme_text()
    if demo.is_file():
        size = demo.stat().st_size
        assert size <= _DEMO_SIZE_CAP_BYTES, (
            f"docs/assets/demo.mp4 is {size} bytes, over the "
            f"{_DEMO_SIZE_CAP_BYTES}-byte (8MB) cap. Re-encode the 30-sec film "
            "smaller (§ASSETS-DEMO-CUT runbook)."
        )
    else:
        # Demo not shipped yet — the README hero sentinel MUST still be the
        # documented placeholder, else the README claims a real film that
        # doesn't exist.
        assert f"sha256={_PLACEHOLDER_SENTINEL}" in readme, (
            "docs/assets/demo.mp4 is absent but the README hero block is NOT "
            "sha256=PLACEHOLDER. Either ship the <=8MB demo.mp4 or reset the "
            "hero sentinel to PLACEHOLDER (Pitfall P68 / §ASSETS-DEMO-CUT)."
        )


# --------------------------------------------------------------------------- #
# 3. OG image present + hash matches MANIFEST (ROADMAP SC3 named test)
# --------------------------------------------------------------------------- #


def test_og_card_present_and_hash_matches() -> None:
    """docs/assets/og-card.png exists and its sha256 matches MANIFEST.yaml.

    ROADMAP SC3 names this test exactly. The OG card is the social-unfurl image;
    a silent re-cut or deletion (T-70P05-01) fails here because the committed
    bytes no longer match the MANIFEST-pinned digest.
    """
    og = REPO_ROOT / "docs" / "assets" / "og-card.png"
    assert og.is_file(), (
        f"Missing OG card at {og.relative_to(REPO_ROOT)}. "
        "Wave 1 (Plan 70P02) ships this 1200x630 source-generated card."
    )

    manifest = yaml.safe_load(
        (REPO_ROOT / "docs" / "assets" / "MANIFEST.yaml").read_text(encoding="utf-8")
    )
    entries = [
        e for e in manifest["assets"] if e["path"] == "docs/assets/og-card.png"
    ]
    assert len(entries) == 1, (
        "docs/assets/MANIFEST.yaml must have exactly one og-card.png entry "
        f"under `assets:` (found {len(entries)})."
    )
    expected = entries[0]["sha256"]
    actual = _sha256_file(og)
    assert actual == expected, (
        "og-card.png hash drift vs MANIFEST.yaml:\n"
        f"  MANIFEST expects: {expected}\n"
        f"  og-card.png is:   {actual}\n"
        "Re-run scripts/regenerate_assets.sh and update the MANIFEST sha256, "
        "or restore the committed PNG."
    )


# --------------------------------------------------------------------------- #
# 4. README hero hash matches sentinel (re-assert GH-01 integrity)
# --------------------------------------------------------------------------- #


def test_readme_hero_hash_matches_sentinel() -> None:
    """scripts/check_readme_hero_hash.py's check() returns exit code 0.

    Re-asserts the GH-01 hero-hash integrity from inside the one-stop suite.
    PLACEHOLDER -> 0 (pending, autonomous-mode exception); a real SHA must match
    the committed asset. Imports check() directly from the scripts module so the
    single source of truth for the logic stays scripts/check_readme_hero_hash.py.
    """
    script_path = REPO_ROOT / "scripts" / "check_readme_hero_hash.py"
    assert script_path.is_file(), (
        f"Missing {script_path.relative_to(REPO_ROOT)} — GH-01 hero-hash gate."
    )
    spec = importlib.util.spec_from_file_location(
        "_vibemix_check_readme_hero_hash", script_path
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    code, msg = mod.check(REPO_ROOT / "README.md", REPO_ROOT)
    assert code == 0, (
        f"README hero-hash gate failed (exit {code}): {msg}\n"
        "The README hero <video> sha256 sentinel drifted from the committed "
        "asset. See scripts/check_readme_hero_hash.py."
    )


# --------------------------------------------------------------------------- #
# 5. Issue templates are valid GitHub Forms (.yml — CONTEXT reconciliation #1)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "yml_path", _issue_form_yml_files(), ids=lambda p: p.name
)
def test_issue_templates_are_valid_github_forms(yml_path: Path) -> None:
    """Each .github/ISSUE_TEMPLATE/*.yml (except config.yml) is a valid Form.

    GitHub Issue Forms shape: non-empty file, parses with yaml.safe_load, and the
    loaded mapping has `name`, `description`, and `body` keys. This validates the
    REAL .yml shape, NOT the old `.md` `about:` front-matter (CONTEXT
    reconciliation #1). A template silently reverted to .md, or with a missing
    required key, fails here (T-70P05-02).
    """
    assert yml_path.stat().st_size > 0, f"{yml_path.name} is empty."
    data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        f"{yml_path.name} must parse to a mapping (GitHub Forms shape), "
        f"got {type(data).__name__}. Did it revert to .md front-matter?"
    )
    for key in ("name", "description", "body"):
        assert key in data, (
            f"{yml_path.name} is missing the required GitHub Forms key "
            f"'{key}:'. Required Forms keys are name/description/body — NOT the "
            "old .md `about:` front-matter (CONTEXT reconciliation #1)."
        )
    assert isinstance(data["body"], list) and data["body"], (
        f"{yml_path.name} `body:` must be a non-empty list of form elements."
    )


def test_issue_forms_config_has_valid_shape() -> None:
    """config.yml is the special Issue-Forms config (NOT a form).

    Validated separately: exists, parses, and carries `blank_issues_enabled`
    OR `contact_links` (its distinct shape). Excluded from the Forms-key check
    above because it has no `name`/`description`/`body`.
    """
    cfg = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / _ISSUE_FORMS_CONFIG
    assert cfg.is_file(), (
        f"Missing {cfg.relative_to(REPO_ROOT)} — the Issue-Forms config."
    )
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        f"config.yml must parse to a mapping, got {type(data).__name__}."
    )
    assert "blank_issues_enabled" in data or "contact_links" in data, (
        "config.yml must carry `blank_issues_enabled:` or `contact_links:` "
        "(the GitHub Issue-Forms config shape). It is NOT a form and must not "
        "be validated as one."
    )


def test_at_least_one_issue_form_present() -> None:
    """Sanity: the parametrized Forms test isn't collecting zero cases.

    Guards against a vacuous pass if ISSUE_TEMPLATE/*.yml were all deleted.
    """
    forms = _issue_form_yml_files()
    assert len(forms) >= 1, (
        "No GitHub Issue Forms (.github/ISSUE_TEMPLATE/*.yml excluding "
        "config.yml) found. The form templates appear to have been removed."
    )


# --------------------------------------------------------------------------- #
# 6. PR template exists + non-empty
# --------------------------------------------------------------------------- #


def test_pull_request_template_exists_nonempty() -> None:
    """.github/pull_request_template.md exists and is non-trivially sized."""
    pr = REPO_ROOT / ".github" / "pull_request_template.md"
    assert pr.is_file(), (
        f"Missing {pr.relative_to(REPO_ROOT)} — the PR template."
    )
    size = pr.stat().st_size
    assert size >= 50, (
        f".github/pull_request_template.md is suspiciously small ({size} bytes "
        "< 50); placeholder or accidentally truncated?"
    )


# --------------------------------------------------------------------------- #
# 7. Four P69 OSS files present + README-linked (intentional overlap)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("filename", _REQUIRED_OSS_FILES)
def test_four_oss_files_present_and_linked(filename: str) -> None:
    """Each P69 OSS doc exists at repo root, is non-trivial, and is README-linked.

    Intentional overlap with tests/repo/test_oss_presence.py — GH-05 is the
    one-stop front-porch suite, so it re-asserts the OSS surface under one roof.
    """
    path = REPO_ROOT / filename
    assert path.is_file(), (
        f"Missing OSS file {filename} at repo root (P69 OSS-01)."
    )
    size = path.stat().st_size
    assert size >= _OSS_MIN_BYTES, (
        f"OSS file {filename} is suspiciously small ({size} bytes "
        f"< {_OSS_MIN_BYTES}); placeholder?"
    )
    assert filename in _readme_text(), (
        f"OSS file {filename} is not linked from README.md. "
        "Add it to the Community section."
    )
