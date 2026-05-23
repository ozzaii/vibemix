"""README shape gate — Phase 19 Plan 19-03.

Verifies the README has all 12 required sections, references all
required assets, names all 10 controllers, contains all 12 FAQ
questions, and doesn't accidentally trip the anti-slop dictionary.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_exists() -> None:
    assert README.exists()


def test_readme_min_length(readme_text: str) -> None:
    assert len(readme_text) > 5000, "README looks too short to be the launch README"


REQUIRED_ASSET_REFS = [
    "docs/assets/hero.png",
    "docs/assets/demo-placeholder.gif",
    "docs/assets/architecture.svg",
    "docs/assets/controllers/",
    "docs/assets/screenshots/",
]


@pytest.mark.parametrize("ref", REQUIRED_ASSET_REFS)
def test_readme_references_asset(readme_text: str, ref: str) -> None:
    assert ref in readme_text, f"README missing reference to {ref}"


# The canonical 10-controller set, locked against the JSON profiles in
# ``src/vibemix/midi/profiles/`` (the actual source of truth for what
# ships out-of-the-box). Phase 68 Wave 0 (Plan 68P01) collapsed the
# duplicated ``midi/controllers/`` ↔ ``midi/profiles/`` catalogs to a
# single canonical directory; the list below is the 10 bundled profile
# IDs verbatim. README carries them in the anti-drift comment block
# beneath the controllers grid so this substring match can find them.
# See ``docs/contributing/midi-catalog.md`` for the migration note.
REQUIRED_CONTROLLERS = [
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
    "pioneer_ddj_flx10",
    "pioneer_ddj_400",
    "pioneer_ddj_1000",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
    "numark_party_mix_live",
    "hercules_inpulse_300",
    "hercules_inpulse_500",
]


@pytest.mark.parametrize("controller", REQUIRED_CONTROLLERS)
def test_readme_names_controller(readme_text: str, controller: str) -> None:
    assert controller in readme_text, f"README missing controller name: {controller}"


REQUIRED_FAQ_QUESTIONS = [
    "What is vibemix?",
    "Is my audio sent to the cloud?",
    "Is this free?",
    "Why no Linux?",
    "Why Gemini",
    "Is the AI actually listening",
    "Can it hallucinate?",
    "What's open-source",
    "Why a Bravoh-managed proxy",
    "Will my recordings be uploaded",
    "What about Mixxx",
    "How do I contribute?",
]


@pytest.mark.parametrize("question", REQUIRED_FAQ_QUESTIONS)
def test_readme_has_faq_question(readme_text: str, question: str) -> None:
    assert question in readme_text, f"README missing FAQ entry: {question!r}"


def test_readme_has_bravoh_footer_with_utm(readme_text: str) -> None:
    assert "altidus.world/vibemix?utm_source=github" in readme_text


def test_readme_has_install_section(readme_text: str) -> None:
    assert "## Install" in readme_text
    assert "vibemix.dmg" in readme_text
    assert "vibemix-installer.msi" in readme_text


def test_readme_has_feature_matrix(readme_text: str) -> None:
    for cell in ["Beginner", "Intermediate", "Pro", "Hype-man", "Coach"]:
        assert cell in readme_text, f"feature matrix missing {cell}"


# Anti-slop gate: README copy must NOT contain generic AI phrases.
# Mirrors the philosophy of src/vibemix/prompts/negative_dict.py.
BANNED_SLOP_PHRASES = [
    "absolutely amazing",
    "as an AI",
    "leverage",
    "delve into",
    "incredibly powerful",
    "groundbreaking",
    "revolutionary",
    "let's dive in",
    "the room is electric",
]


@pytest.mark.parametrize("phrase", BANNED_SLOP_PHRASES)
def test_readme_no_slop(readme_text: str, phrase: str) -> None:
    assert phrase.lower() not in readme_text.lower(), (
        f"README contains slop phrase: {phrase!r}"
    )


def test_midi_mapping_guide_exists() -> None:
    path = REPO_ROOT / "docs" / "midi-mapping.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for section in [
        "## Two paths",
        "## Extracting",
        "## JSON schema",
        "## Submitting",
    ]:
        assert section in text, f"midi-mapping.md missing section: {section}"


def test_readme_has_license_link(readme_text: str) -> None:
    assert "LICENSE" in readme_text
    assert "Apache 2.0" in readme_text


def test_readme_badges_row(readme_text: str) -> None:
    badge_count = readme_text.count("shields.io")
    assert badge_count >= 5, f"expected ≥5 shields.io badges, got {badge_count}"
