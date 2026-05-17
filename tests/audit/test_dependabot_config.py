"""DEPS-10 — assert .github/dependabot.yml has the 4 ecosystem entries
with weekly schedule + major-bump ignore + no auto-merge."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEPENDABOT = REPO / ".github" / "dependabot.yml"

REQUIRED_ECOSYSTEMS = {"pip", "cargo", "npm", "github-actions"}


def _load():
    return yaml.safe_load(DEPENDABOT.read_text())


def test_dependabot_exists():
    assert DEPENDABOT.is_file(), f"missing {DEPENDABOT}"


def test_dependabot_version_is_2():
    d = _load()
    assert d["version"] == 2


def test_four_ecosystems_present():
    d = _load()
    ecos = {u["package-ecosystem"] for u in d["updates"]}
    assert ecos == REQUIRED_ECOSYSTEMS, f"got: {ecos} expected: {REQUIRED_ECOSYSTEMS}"


def test_every_ecosystem_is_weekly():
    d = _load()
    for u in d["updates"]:
        assert u["schedule"]["interval"] == "weekly", \
            f"{u['package-ecosystem']} not weekly: {u['schedule']}"


def test_every_ecosystem_ignores_majors():
    d = _load()
    for u in d["updates"]:
        ignores = u.get("ignore", [])
        has_major_ignore = any(
            "version-update:semver-major" in i.get("update-types", [])
            for i in ignores
        )
        assert has_major_ignore, \
            f"{u['package-ecosystem']} does not ignore semver-major bumps"


def test_no_auto_merge_anywhere():
    # Dependabot has no native auto-merge; auto-merge is a workflow
    # the user adds. We assert no `auto-merge: true` string in the file.
    text = DEPENDABOT.read_text()
    assert "auto-merge: true" not in text, \
        "DEPS-10: auto-merge must NOT be enabled — manual review per CONTEXT § Dependabot"


def test_open_prs_limit_set_per_ecosystem():
    d = _load()
    for u in d["updates"]:
        limit = u.get("open-pull-requests-limit")
        assert isinstance(limit, int) and limit > 0, \
            f"{u['package-ecosystem']} missing open-pull-requests-limit"
