# SPDX-License-Identifier: Apache-2.0
"""Plan 45-03 — contract tests for ``scripts/release/check_bravoh_server_ready.sh``.

The probe is the SHIP-06 / OPS-14 release gate that proves the Bravoh server's
3 contractual endpoints are deployed + the healthz cron is heartbeating, before
``cut_release.sh`` permits SHIP-CUT.

Test plan (12 tests across this file; Tests 1-9 land in Task 1 RED, Tests 10-12
land in Task 2 GREEN — see the Task 1 PLAN.md ``<behavior>`` block):

  1.  File exists, executable, ``set -euo pipefail``, ``bash -n`` clean.
  2.  ``--help`` exits 0, prints flag reference including the 3 flags.
  3.  Unknown flag exits 2 with usage error to stderr.
  4.  Mock 200 + healthz fresh → exit 0 + OK stdout banner.
  5.  Mock returns 404 for ``/vibemix/updates/latest.json`` → exit 1 + structured
      ``BLOCKED_BY=bravoh-server: endpoint missing: /vibemix/updates/latest.json``.
  6.  Mock 200 for healthz but ts is 30 min old → exit 4 + structured
      ``BLOCKED_BY=bravoh-server: healthz stale``.
  7.  Mock unreachable (closed port) → exit 3 + structured
      ``BLOCKED_BY=bravoh-server: network failure``.
  8.  ``--healthz-max-age-s 60`` accepted; 5-min-old ts (under default 600s but
      over the override 60s) → exit 4. Proves the flag changes behaviour.
  9.  Under ``GITHUB_ACTIONS=true`` the failure paths also emit a
      ``::error::check_bravoh_server_ready: ...`` annotation.
  10. jq optional: PATH-stubbed with jq removed → still works via python3
      fallback. (Task 2 GREEN.)
  11. ``--quiet`` suppresses stdout but keeps stderr + exit codes. (Task 2 GREEN.)
  12. ``--max-time 10`` pinned in every curl invocation (source grep). (Task 2 GREEN.)

The mock endpoints are served by ``http.server.ThreadingHTTPServer`` on a random
localhost port — zero network in CI.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE = REPO_ROOT / "scripts" / "release" / "check_bravoh_server_ready.sh"


# ---------------------------------------------------------------------------
# Mock HTTP server fixture
# ---------------------------------------------------------------------------


class _MockState:
    """Per-test mutable knobs the mock handler reads to shape responses."""

    def __init__(self) -> None:
        # Healthz behaviour.
        self.healthz_status = 200
        self.healthz_ts: str | None = _iso_now()
        # Latest.json behaviour.
        self.latest_status = 200
        self.latest_body: dict | None = {"version": "3.0.0", "url": "https://x/y"}
        # Upload (HEAD) behaviour.
        self.upload_status = 401  # auth-gated correctly
        # Request log for assertions.
        self.requests: list[tuple[str, str]] = []


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_offset(seconds: int) -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _make_handler(state: _MockState):
    class _Handler(BaseHTTPRequestHandler):
        # Silence default stderr access log spam.
        def log_message(self, fmt, *args):  # noqa: D401, ANN001
            return

        def _respond_json(self, code: int, body: dict | None) -> None:
            self.send_response(code)
            payload = b""
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def do_GET(self):  # noqa: N802
            state.requests.append(("GET", self.path))
            if self.path == "/vibemix/healthz":
                if state.healthz_status != 200:
                    self.send_response(state.healthz_status)
                    self.end_headers()
                    return
                self._respond_json(
                    200, {"status": "ok", "ts": state.healthz_ts}
                )
                return
            if self.path == "/vibemix/updates/latest.json":
                if state.latest_status != 200:
                    self.send_response(state.latest_status)
                    self.end_headers()
                    return
                self._respond_json(200, state.latest_body)
                return
            self.send_response(404)
            self.end_headers()

        def do_HEAD(self):  # noqa: N802
            state.requests.append(("HEAD", self.path))
            if self.path == "/vibemix/updates/upload":
                self.send_response(state.upload_status)
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

    return _Handler


@pytest.fixture
def mock_server():
    """Yield (state, base_url). State drives response shaping per test."""
    state = _MockState()
    # Bind to a random free port on localhost.
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def _closed_port() -> int:
    """Bind + immediately release a port; returns a port no listener owns."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _run_probe(*args: str, env_extra: dict[str, str] | None = None,
               timeout: int = 30) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(PROBE), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )


# ---------------------------------------------------------------------------
# Task 1 — Tests 1-9 (RED until Task 2 GREEN lands the probe body)
# ---------------------------------------------------------------------------


def test_1_script_exists_executable_syntax_clean():
    assert PROBE.is_file(), f"missing: {PROBE}"
    assert os.access(PROBE, os.X_OK), f"not +x: {PROBE}"
    text = PROBE.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text, "must use `set -euo pipefail`"
    # bash -n must exit 0.
    rc = subprocess.run(
        ["bash", "-n", str(PROBE)], capture_output=True, text=True, check=False
    )
    assert rc.returncode == 0, f"bash -n failed: {rc.stderr}"


def test_2_help_lists_three_flags():
    result = _run_probe("--help")
    assert result.returncode == 0, result.stderr
    assert "--endpoint-base" in result.stdout
    assert "--quiet" in result.stdout
    assert "--healthz-max-age-s" in result.stdout
    # Cross-reference the 5 exit codes are documented.
    for code in ("0", "1", "2", "3", "4"):
        assert code in result.stdout, f"exit code {code} not in --help"


def test_3_unknown_flag_exits_2_with_usage():
    result = _run_probe("--definitely-not-a-flag")
    assert result.returncode == 2, (
        f"expected exit 2 for unknown flag, got {result.returncode}: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # Usage hint should appear on stderr.
    assert "unknown" in result.stderr.lower() or "usage" in result.stderr.lower()


def test_4_all_endpoints_ok_exits_zero(mock_server):
    state, base = mock_server
    state.healthz_ts = _iso_now()
    result = _run_probe("--endpoint-base", base)
    assert result.returncode == 0, (
        f"expected exit 0; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "OK" in result.stdout
    assert "3/3" in result.stdout or "3 of 3" in result.stdout
    # Confirm the mock saw all 3 endpoints hit.
    paths = {p for _, p in state.requests}
    assert "/vibemix/healthz" in paths
    assert "/vibemix/updates/latest.json" in paths
    assert "/vibemix/updates/upload" in paths


def test_5_missing_endpoint_exits_one_with_structured_blocker(mock_server):
    state, base = mock_server
    state.latest_status = 404
    state.healthz_ts = _iso_now()
    result = _run_probe("--endpoint-base", base)
    assert result.returncode == 1, (
        f"expected exit 1 for missing endpoint; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "BLOCKED_BY=bravoh-server" in result.stderr
    assert "endpoint missing" in result.stderr
    assert "/vibemix/updates/latest.json" in result.stderr


def test_6_stale_healthz_exits_four(mock_server):
    state, base = mock_server
    # 30 min ago — well past the default 600s.
    state.healthz_ts = _iso_offset(seconds=30 * 60)
    result = _run_probe("--endpoint-base", base)
    assert result.returncode == 4, (
        f"expected exit 4 for stale healthz; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "BLOCKED_BY=bravoh-server" in result.stderr
    assert "stale" in result.stderr.lower()


def test_7_network_failure_exits_three():
    port = _closed_port()
    base = f"http://127.0.0.1:{port}"
    result = _run_probe("--endpoint-base", base, timeout=60)
    assert result.returncode == 3, (
        f"expected exit 3 for closed port; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "BLOCKED_BY=bravoh-server" in result.stderr
    assert "network" in result.stderr.lower()


def test_8_max_age_override_changes_stale_threshold(mock_server):
    state, base = mock_server
    # 5 minutes old — under default 600s, OVER --healthz-max-age-s 60.
    state.healthz_ts = _iso_offset(seconds=5 * 60)

    # Default 600s threshold → ts is fresh → exit 0.
    result_default = _run_probe("--endpoint-base", base)
    assert result_default.returncode == 0, (
        "5-min-old ts should be fresh under default 600s; "
        f"got exit {result_default.returncode}\n"
        f"stdout={result_default.stdout!r}\nstderr={result_default.stderr!r}"
    )

    # Override to 60s → ts is stale → exit 4.
    result_strict = _run_probe(
        "--endpoint-base", base, "--healthz-max-age-s", "60"
    )
    assert result_strict.returncode == 4, (
        "5-min-old ts should be stale under --healthz-max-age-s 60; "
        f"got exit {result_strict.returncode}\n"
        f"stdout={result_strict.stdout!r}\nstderr={result_strict.stderr!r}"
    )


def test_9_github_actions_annotation_on_failure(mock_server):
    state, base = mock_server
    state.latest_status = 404
    state.healthz_ts = _iso_now()
    result = _run_probe(
        "--endpoint-base", base,
        env_extra={"GITHUB_ACTIONS": "true"},
    )
    assert result.returncode == 1
    assert "::error::check_bravoh_server_ready" in result.stderr, (
        "GH Actions annotation missing; stderr=\n" + result.stderr
    )


# ---------------------------------------------------------------------------
# Task 2 — Tests 10-12 (GREEN: pinned in Task 2)
# ---------------------------------------------------------------------------


def test_10_jq_optional_python3_fallback(mock_server, tmp_path):
    """PATH-stubbed without jq → probe still works via python3 fallback."""
    state, base = mock_server
    state.healthz_ts = _iso_now()

    # Build a sanitized PATH dir containing every binary the probe needs
    # EXCEPT jq. We symlink curl/python3/bash/date/grep/sed/awk/tr/etc. from
    # the real PATH but omit jq.
    sanitized = tmp_path / "bin"
    sanitized.mkdir()
    needed = [
        "bash", "curl", "python3", "date", "grep", "sed", "awk", "tr",
        "cat", "rm", "mktemp", "head", "tail", "cut", "test", "[", "echo",
        "printf", "true", "false", "env", "expr", "dirname", "basename",
        "uname", "id", "tty",
    ]
    for name in needed:
        src = shutil.which(name)
        if src:
            (sanitized / name).symlink_to(src)
    # Sanity: jq should be ABSENT from sanitized.
    assert not (sanitized / "jq").exists(), "test fixture broken: jq leaked"

    result = subprocess.run(
        ["bash", str(PROBE), "--endpoint-base", base],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(sanitized)},
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        "probe must work without jq via python3 fallback; "
        f"got exit {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_11_quiet_suppresses_stdout(mock_server):
    state, base = mock_server
    state.healthz_ts = _iso_now()
    result = _run_probe("--endpoint-base", base, "--quiet")
    assert result.returncode == 0
    # Quiet mode: no OK banner on stdout. (Stderr is unaffected since
    # success path has no stderr anyway.)
    assert result.stdout.strip() == "", (
        f"--quiet should suppress stdout; got stdout={result.stdout!r}"
    )


def test_12_max_time_10_in_every_curl_invocation():
    text = PROBE.read_text(encoding="utf-8")
    # Only match REAL curl invocations — exclude:
    #   - comments (start with #)
    #   - `command -v curl` existence checks
    #   - shell error messages containing the word "curl"
    # A real invocation starts with `curl ` then a curl flag (`-s`, `-S`, etc.).
    import re
    curl_call = re.compile(r"(^|[\s\(`=])curl\s+-[A-Za-z]")
    curl_lines = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "command -v curl" in ln:
            continue
        # Strip out string literals inside `echo "..."` / `echo '...'` so a
        # diagnostic message containing the word `curl` doesn't trip the
        # detector. Only the actual command position is relevant.
        if re.match(r'^\s*echo\b', ln):
            continue
        if curl_call.search(ln):
            curl_lines.append(ln)
    assert curl_lines, "probe must invoke curl at least once"
    for ln in curl_lines:
        assert "--max-time" in ln, (
            f"curl line missing --max-time (T-45-03-02 mitigation): {ln!r}"
        )
        # Pin the value to 10 specifically.
        assert "--max-time 10" in ln or "--max-time\t10" in ln, (
            f"curl --max-time must be 10s: {ln!r}"
        )
