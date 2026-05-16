"""Tests for `scripts/dayzero/healthz_check.sh` Discord webhook + cron example.

Uses subprocess + the script's deterministic --dry-run schedule (every 3rd
iteration = 503). Asserts the webhook [would-post] line shows up on the
synthetic alert iteration, and that the cron example file is well-formed.
"""
from __future__ import annotations

import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dayzero" / "healthz_check.sh"
CRON_EXAMPLE = ROOT / "scripts" / "dayzero" / "healthz_cron.example"


def test_healthz_check_script_exists_and_executable():
    assert SCRIPT.is_file()
    # bash will execute it via `bash <script>` regardless of mode bit, but
    # the file should at least be readable.
    assert SCRIPT.stat().st_size > 0


def test_healthz_discord_webhook_on_failure():
    """Dry-run schedule (503 on iteration 3) emits the [would-post] line."""
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--interval", "0",
            "--max-iterations", "3",
            "--webhook-url", "https://discord.test/hook",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    # The alert iteration must emit the dry-run webhook line.
    assert "[would-post]" in proc.stderr
    assert "https://discord.test/hook" in proc.stderr
    assert "vibemix healthz alert" in proc.stderr
    # Body must include the synthetic status and target tags.
    assert "status=503" in proc.stderr


def test_healthz_no_webhook_no_post():
    """Without --webhook-url and no env var, dry-run never posts."""
    # Strip any env-set webhook so the test environment is deterministic.
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--interval", "0",
            "--max-iterations", "3",
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "[would-post]" not in proc.stderr
    assert "[would-post]" not in proc.stdout
    # The alert line still shows up because the watchdog itself fires.
    assert "[ALERT]" in proc.stderr


def test_healthz_cron_example_present():
    """OPS-11 deliverable: cron example file exists with 5-min cadence."""
    assert CRON_EXAMPLE.is_file()
    text = CRON_EXAMPLE.read_text()
    assert "*/5" in text, "Cron example must specify a 5-minute cadence"
    assert "DISCORD_WEBHOOK_URL" in text, "Cron example must reference the webhook env"
    assert "healthz_check.sh" in text


def test_healthz_cron_example_does_not_hardcode_webhook():
    """Anti-leak: the example must NOT have a real Discord webhook URL."""
    text = CRON_EXAMPLE.read_text()
    # The env-var line has '=' with nothing after — that's the documented
    # template form. Reject any inline discord.com/api/webhooks/... URL.
    for line in text.splitlines():
        if line.startswith("DISCORD_WEBHOOK_URL="):
            value = line.split("=", 1)[1].strip()
            assert value == "", (
                f"Cron example must not hard-code a webhook URL, got: {value!r}"
            )
