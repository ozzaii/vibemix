"""OPP-03 validator tests — exercise the three gate functions with
real fixtures + synthetic failure cases."""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit" / "scan_opportunities.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_scan_opportunities", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()

ALLOWED_RED_RATINGS = _mod.ALLOWED_RED_RATINGS
CONSTRAINT_VIOLATORS = _mod.CONSTRAINT_VIOLATORS
DEFAULT_SCAN = _mod.DEFAULT_SCAN
gate_adr_existence = _mod.gate_adr_existence
gate_auto_red = _mod.gate_auto_red
gate_md_yaml_parity = _mod.gate_md_yaml_parity
run_gates = _mod.run_gates


def test_constraint_violators_covers_memory_set():
    # CONTEXT Decision 8 — the auto-Red set must include the memory-
    # enumerated triggers verbatim.
    names = {v.lower() for v in CONSTRAINT_VIOLATORS}
    for must in (
        "clap", "mert", "openl3",
        "openai direct", "anthropic api direct",
        "demucs", "spleeter",
        "ableton link", "daw api",
        "linux-only",
        "prodj link", "cdj-link-py",
        "dante via", "loopback audio", "soundflower",
        "auto-rig pro",
    ):
        assert must in names, f"CONSTRAINT_VIOLATORS missing '{must}'"


def test_allowed_red_ratings_is_exactly_the_two_red_colors():
    assert ALLOWED_RED_RATINGS == frozenset({"red-constraint", "red-risk"})


def test_real_fixtures_pass_parity_and_auto_red():
    """Real fixtures pass parity + auto-red. ADR gate may fail before
    Plan 48-04 commits the ADR file; that is expected."""
    import yaml as _y
    data = _y.safe_load(_mod.YAML_FILE.read_text())
    errors: list[str] = []
    gate_md_yaml_parity(DEFAULT_SCAN, data, errors)
    assert errors == [], f"real fixtures parity gate must be clean, got: {errors}"
    errors.clear()
    gate_auto_red(data, errors)
    assert errors == [], f"real fixtures auto-red gate must be clean, got: {errors}"


def test_auto_red_fails_when_clap_is_yellow_defer():
    data = {
        "python": {}, "rust": {}, "js": {},
        "opportunity_evaluations": [
            {
                "id": "DEP-OPP-99",
                "date": "2026-05-18",
                "candidate": "CLAP audio embedding (synthetic test row)",
                "category": "python-dep",
                "rating": "yellow-defer",
                "install_impact": "red",
                "rationale": "synthetic test row for the auto-red gate",
                "integration_surface": "none",
                "rejected_constraints": [],
                "adr_sidecar": "",
            },
        ],
    }
    errors: list[str] = []
    gate_auto_red(data, errors)
    assert errors, "CLAP candidate rated yellow-defer must trigger the gate"
    assert "CLAP" in errors[0]
    assert "yellow-defer" in errors[0]


def test_auto_red_passes_when_clap_is_red_constraint():
    data = {
        "python": {}, "rust": {}, "js": {},
        "opportunity_evaluations": [
            {
                "id": "DEP-OPP-99",
                "date": "2026-05-18",
                "candidate": "CLAP audio embedding (synthetic)",
                "category": "python-dep",
                "rating": "red-constraint",
                "install_impact": "red",
                "rationale": "synthetic row correctly marked red-constraint",
                "integration_surface": "none",
                "rejected_constraints": [],
                "adr_sidecar": "",
            },
        ],
    }
    errors: list[str] = []
    gate_auto_red(data, errors)
    assert errors == [], f"correctly-marked CLAP row should not trigger gate, got: {errors}"


def test_adr_existence_fails_for_green_adopt_without_adr():
    data = {
        "python": {}, "rust": {}, "js": {},
        "opportunity_evaluations": [
            {
                "id": "DEP-OPP-99",
                "date": "2026-05-18",
                "candidate": "Synthetic green-adopt without ADR",
                "category": "integration",
                "rating": "green-adopt",
                "install_impact": "green",
                "rationale": "synthetic test — missing adr_sidecar",
                "integration_surface": "docs-only",
                "rejected_constraints": [],
                "adr_sidecar": "",
            },
        ],
    }
    errors: list[str] = []
    gate_adr_existence(data, errors)
    assert errors, "green-adopt without adr_sidecar must trigger gate"
    assert "DEP-OPP-99" in errors[0]


def test_adr_existence_fails_when_adr_path_does_not_exist():
    data = {
        "python": {}, "rust": {}, "js": {},
        "opportunity_evaluations": [
            {
                "id": "DEP-OPP-99",
                "date": "2026-05-18",
                "candidate": "Synthetic green-adopt with nonexistent ADR",
                "category": "integration",
                "rating": "green-adopt",
                "install_impact": "green",
                "rationale": "synthetic test — ADR path points to a nonexistent file",
                "integration_surface": "docs-only",
                "rejected_constraints": [],
                "adr_sidecar": ".planning/decisions/DOES-NOT-EXIST.md",
            },
        ],
    }
    errors: list[str] = []
    gate_adr_existence(data, errors)
    assert errors, "missing ADR file on disk must trigger gate"


def test_parity_gate_detects_missing_yaml_id(tmp_path: Path):
    scan_md = tmp_path / "scan.md"
    scan_md.write_text("DEP-OPP-99 only-in-md; DEP-OPP-01 in-both")
    data = {
        "python": {}, "rust": {}, "js": {},
        "opportunity_evaluations": [
            {
                "id": "DEP-OPP-01",
                "date": "2026-05-18",
                "candidate": "row in yaml that matches md",
                "category": "integration",
                "rating": "green-adopt",
                "install_impact": "green",
                "rationale": "synthetic test row for the parity gate",
                "integration_surface": "docs-only",
                "rejected_constraints": [],
                "adr_sidecar": ".planning/decisions/DEP-OPP-01-obs-browser-source.md",
            },
        ],
    }
    errors: list[str] = []
    gate_md_yaml_parity(scan_md, data, errors)
    assert errors, "md_only id must trigger parity gate"
    assert "DEP-OPP-99" in errors[0]
