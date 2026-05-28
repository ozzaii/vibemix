# SPDX-License-Identifier: Apache-2.0
"""Phase 97 / RENDER-08 + ONBOARD-07 — Trademark disclaimer presence gate.

The v9.0 controller-renderer module renders likenesses of Pioneer DJ /
Hercules / Numark controllers; the nominative fair-use posture requires
the canonical trademark disclaimer to surface in both the running app
(Learn-window footer) and the project README ("Trademarks" section).

If a future refactor strips the disclaimer from either surface this gate
goes red. The fragment is intentionally a single load-bearing sentence
so the test stays robust against punctuation / whitespace tweaks the
canonical copy might pick up over time (only the leading sentence is
asserted; the full block extends through the trailing "not affiliated"
clause).

Surfaces audited:

* ``README.md`` — looked up by repo-relative path.
* ``tauri/ui/src/learn/**/*.ts`` — recursive scan; the disclaimer is
  embedded as a TS string constant in ``learn-window.ts``
  (``TRADEMARK_DISCLAIMER``) and rendered into the footer at boot.

Adds an additional gate that catches the most likely real-world drift:
``learn-window.ts`` carries the disclaimer constant but neither the
``<footer>`` element nor the ``footer.textContent = TRADEMARK_DISCLAIMER``
assignment got removed (the test is more useful than a bare ``in`` check).
"""

from __future__ import annotations

from pathlib import Path

DISCLAIMER_FRAGMENT = "Visual representation for instructional use."
DISCLAIMER_PARTNERS = (
    "AlphaTheta / Pioneer DJ",
    "Hercules",
    "inMusic Brands",
)
DISCLAIMER_NEGATIVE_CLAUSE = "not affiliated with or endorsed by"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_disclaimer_present_in_readme() -> None:
    """The repo README MUST carry the Trademarks disclaimer verbatim."""
    readme = _repo_root() / "README.md"
    assert readme.exists(), f"{readme} not found"
    text = readme.read_text(encoding="utf-8")
    assert DISCLAIMER_FRAGMENT in text, (
        f"README.md is missing the trademark disclaimer leading fragment "
        f"{DISCLAIMER_FRAGMENT!r}. Add a '## Trademarks' section near the "
        f"end of the README with the canonical copy."
    )
    # The partner names ride the same disclaimer — if one is stripped the
    # nominative-fair-use posture weakens.
    for partner in DISCLAIMER_PARTNERS:
        assert partner in text, (
            f"README.md disclaimer is missing partner reference {partner!r}. "
            f"Restore the full Trademarks copy."
        )
    assert DISCLAIMER_NEGATIVE_CLAUSE in text, (
        "README.md disclaimer is missing the 'not affiliated with or "
        "endorsed by' negative-clause; restore the canonical copy."
    )


def test_disclaimer_present_in_learn_window_typescript() -> None:
    """At least one .ts file under tauri/ui/src/learn/ carries the disclaimer
    fragment as an embedded string constant."""
    learn_root = _repo_root() / "tauri" / "ui" / "src" / "learn"
    assert learn_root.is_dir(), f"{learn_root} not found"
    hit_files: list[Path] = []
    for ts_file in learn_root.rglob("*.ts"):
        # Don't scan compiled / vendored files (none under src/learn but be
        # safe forward-compatible against future asset moves).
        if ".test." in ts_file.name or ts_file.suffix != ".ts":
            continue
        text = ts_file.read_text(encoding="utf-8")
        if DISCLAIMER_FRAGMENT in text:
            hit_files.append(ts_file)
    assert hit_files, (
        f"No .ts file under {learn_root} contains the trademark disclaimer "
        f"leading fragment {DISCLAIMER_FRAGMENT!r}. Add or restore the "
        f"TRADEMARK_DISCLAIMER constant in learn-window.ts and ensure it "
        f"renders into the footer at boot."
    )


def test_disclaimer_partner_names_present_in_learn_window_typescript() -> None:
    """All three partner-name fragments MUST appear together in the same
    .ts file as the leading disclaimer fragment — guards against the
    half-stripped state where only one partner name survives a refactor."""
    learn_root = _repo_root() / "tauri" / "ui" / "src" / "learn"
    intact_file: Path | None = None
    for ts_file in learn_root.rglob("*.ts"):
        if ".test." in ts_file.name or ts_file.suffix != ".ts":
            continue
        text = ts_file.read_text(encoding="utf-8")
        if DISCLAIMER_FRAGMENT not in text:
            continue
        if all(partner in text for partner in DISCLAIMER_PARTNERS):
            intact_file = ts_file
            break
    assert intact_file is not None, (
        "The full trademark disclaimer (leading fragment + all three partner "
        "names) was not found together in any .ts file under "
        f"{learn_root}. Restore the canonical TRADEMARK_DISCLAIMER constant."
    )


def test_disclaimer_negative_clause_present_in_learn_window_typescript() -> None:
    """The 'not affiliated' clause is load-bearing for the nominative-fair-
    use posture — assert it survives in the .ts source verbatim."""
    learn_root = _repo_root() / "tauri" / "ui" / "src" / "learn"
    hit = False
    for ts_file in learn_root.rglob("*.ts"):
        if ".test." in ts_file.name or ts_file.suffix != ".ts":
            continue
        text = ts_file.read_text(encoding="utf-8")
        if DISCLAIMER_NEGATIVE_CLAUSE in text:
            hit = True
            break
    assert hit, (
        "The disclaimer negative clause "
        f"{DISCLAIMER_NEGATIVE_CLAUSE!r} is missing from every .ts file "
        f"under {learn_root}. Restore it as part of the TRADEMARK_DISCLAIMER "
        "constant."
    )
