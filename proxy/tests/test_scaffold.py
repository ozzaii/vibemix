# SPDX-License-Identifier: Apache-2.0
"""SCAFFOLD-01..07 — pyproject + .gitignore + .env.example shape checks."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


_PROXY = Path(__file__).resolve().parent.parent
_ROOT = _PROXY.parent

_AIZA = re.compile(r"AIza[0-9A-Za-z_-]{35}")
_OR_KEY = re.compile(r"sk-or-v1-[0-9a-f]{20,}")


def test_scaffold_01_pyproject_parses_and_basic_fields() -> None:
    data = tomllib.loads((_PROXY / "pyproject.toml").read_text())
    project = data["project"]
    assert project["name"] == "vibemix-proxy"
    assert "version" in project
    assert project["requires-python"] == ">=3.12,<3.13"


def test_scaffold_02_runtime_deps_present() -> None:
    data = tomllib.loads((_PROXY / "pyproject.toml").read_text())
    deps = data["project"]["dependencies"]
    required = {
        "fastapi": "0.115",
        "uvicorn": "0.32",
        "pyjwt": "2.12.1",
        "slowapi": "0.1.9",
        "redis": "5.0",
        "google-genai": "2.0.1",
        "httpx": "0.28",
        "pydantic": "2.13",
        "pydantic-settings": "2.6",
        "python-dotenv": "1.0",
    }
    for pkg, min_ver in required.items():
        matches = [d for d in deps if d.split(">=", 1)[0].split("[", 1)[0].strip() == pkg]
        assert matches, f"{pkg} missing from runtime deps"
        spec = matches[0]
        # extract version after >=
        m = re.search(r">=([0-9.]+)", spec)
        assert m, f"{pkg} spec missing >= version: {spec}"
        assert m.group(1) >= min_ver, f"{pkg} pinned at {m.group(1)} < {min_ver}"


def test_scaffold_03_dev_deps_declared() -> None:
    data = tomllib.loads((_PROXY / "pyproject.toml").read_text())
    dev = data["dependency-groups"]["dev"]
    for pkg in ("pytest", "pytest-asyncio", "fakeredis", "ruff"):
        assert any(d.startswith(pkg + ">=") for d in dev), f"{pkg} missing from dev deps"


def test_scaffold_04_proxy_gitignore_lines() -> None:
    text = (_PROXY / ".gitignore").read_text()
    for line in (".env", ".venv/", "__pycache__/", "*.pyc", ".pytest_cache/", ".ruff_cache/"):
        assert line in text.splitlines(), f"missing line in proxy/.gitignore: {line}"


def test_scaffold_05_env_example_keys_and_no_secrets() -> None:
    text = (_PROXY / ".env.example").read_text()
    for key in (
        "GEMINI_API_KEY=",
        "OPENROUTER_API_KEY=",
        "JWT_SECRET=",
        "REDIS_URL=",
        "ALLOWED_ORIGINS=",
        "RATE_LIMIT_PER_MIN=",
        "RATE_LIMIT_PER_DAY=",
        "JWT_TTL_DAYS=",
    ):
        assert key in text, f"{key} missing from .env.example"
    assert not _AIZA.search(text), "AIza pattern leaked into .env.example"
    assert not _OR_KEY.search(text), "sk-or-v1- pattern leaked into .env.example"


def test_scaffold_06_root_gitignore_covers_proxy_paths() -> None:
    text = (_ROOT / ".gitignore").read_text()
    # Either explicit `proxy/.env` line OR a pattern that matches it (`.env`).
    assert ".env" in text.splitlines() or "proxy/.env" in text, (
        "root .gitignore must cover proxy/.env"
    )
    assert ".venv/" in text.splitlines() or "proxy/.venv/" in text, (
        "root .gitignore must cover proxy/.venv/"
    )


def test_scaffold_07_package_markers_exist() -> None:
    assert (_PROXY / "app" / "__init__.py").exists()
    assert (_PROXY / "tests" / "__init__.py").exists()
