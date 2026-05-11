# SPDX-License-Identifier: Apache-2.0
"""LICENSE + SPDX header presence checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_license_apache_2_0():
    license_path = REPO_ROOT / "LICENSE"
    assert license_path.exists(), "LICENSE missing at repo root"
    text = license_path.read_text()
    assert "Apache License" in text
    assert "Version 2.0" in text


def test_spdx_header_in_init():
    init_path = REPO_ROOT / "src" / "vibemix" / "__init__.py"
    first_line = init_path.read_text().splitlines()[0]
    assert first_line == "# SPDX-License-Identifier: Apache-2.0"
