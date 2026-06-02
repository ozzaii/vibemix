# SPDX-License-Identifier: Apache-2.0
"""Tests for the vibemix-dev MCP server (observe+drive surface).

NEW ISLAND — touches no existing test. Exercises tool registration, the
which_handler scanner reuse, and the read-only tools against FAKES. The ws
tools are tested against a FAKE in-process websockets.serve on an EPHEMERAL
port (NOT :8765 — the real co-host owns that, Invariant #4); the dev server
attaches as a CLIENT only, so a fake server on a throwaway port proves the
client path without ever binding the cardinal socket.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibemix.runtime import dev_mcp_server as dms

# ---------------------------------------------------------------------------
# Config / path resolution
# ---------------------------------------------------------------------------


def _cfg(tmp: Path, **over) -> dms.DevServerConfig:
    cfg = dms.DevServerConfig(
        repo_root=over.get("repo_root", tmp / "repo"),
        log_root=over.get("log_root", tmp / "logroot"),
        data_root=over.get("data_root", tmp / "dataroot"),
        ws_uri=over.get("ws_uri", "ws://127.0.0.1:59999"),
    )
    return cfg


def test_ui_log_path_is_bundle_id_logs(tmp_path):
    cfg = _cfg(tmp_path)
    assert cfg.ui_log_path() == cfg.log_root / "vibemix" / "logs" / "ui.log"


def test_parse_args_defaults_are_os_aware_and_resolve():
    cfg = dms.parse_args([])
    # bundle-id segment present in the default log root (the ui.log anchor).
    assert dms._BUNDLE_ID in str(cfg.log_root)
    # plain data root ends in /vibemix (NOT the bundle-id dir) — the split-brain.
    assert cfg.data_root.name == "vibemix"
    assert dms._BUNDLE_ID not in str(cfg.data_root)
    assert cfg.ws_uri == dms.DEFAULT_WS_URI


def test_parse_args_overrides_resolve_absolute(tmp_path):
    cfg = dms.parse_args(
        ["--repo-root", str(tmp_path / "r"), "--log-root", str(tmp_path / "l"),
         "--data-root", str(tmp_path / "d"), "--ws-uri", "ws://127.0.0.1:1"]
    )
    assert cfg.repo_root == (tmp_path / "r").resolve()
    assert cfg.log_root == (tmp_path / "l").resolve()
    assert cfg.data_root == (tmp_path / "d").resolve()
    assert cfg.ws_uri == "ws://127.0.0.1:1"


# ---------------------------------------------------------------------------
# Tool registration — all seven tools live on the FastMCP server
# ---------------------------------------------------------------------------


def test_build_server_registers_all_seven_tools(tmp_path):
    cfg = _cfg(tmp_path)
    server = dms.build_server(cfg)
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "ws_observe",
        "ws_trigger",
        "learn_probe",
        "tail_ui_log",
        "tail_events",
        "which_handler",
        "sidecar_status",
    }
    # Every tool carries a real description (no bare stubs).
    for t in tools:
        assert t.description and len(t.description) > 20


# ---------------------------------------------------------------------------
# tail_ui_log — read-only, fail-soft
# ---------------------------------------------------------------------------


def test_tail_ui_log_absent_is_actionable(tmp_path):
    cfg = _cfg(tmp_path)
    out = dms.tool_tail_ui_log(cfg, lines=10)
    assert "error" in out
    assert "ui.log" in out["error"]
    assert out["lines"] == []


def test_tail_ui_log_returns_last_n_lines(tmp_path):
    cfg = _cfg(tmp_path)
    log = cfg.ui_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"t=1.{i} [vmx:click] control-{i}" for i in range(50)]
    log.write_text("\n".join(lines) + "\n")
    out = dms.tool_tail_ui_log(cfg, lines=5)
    assert out["count"] == 5
    assert out["lines"][-1] == "t=1.49 [vmx:click] control-49"
    assert out["lines"][0] == "t=1.45 [vmx:click] control-45"


# ---------------------------------------------------------------------------
# tail_events — latest + named session, JSON-parsed, fail-soft
# ---------------------------------------------------------------------------


def _write_session(data_root: Path, name: str, events: list[dict]) -> Path:
    sess = data_root / "recordings" / name
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n"
    )
    return sess


def test_tail_events_no_recordings_is_actionable(tmp_path):
    cfg = _cfg(tmp_path)
    out = dms.tool_tail_events(cfg)
    assert "error" in out
    assert "recordings" in out["error"]


def test_tail_events_latest_session_parses_json(tmp_path):
    cfg = _cfg(tmp_path)
    _write_session(
        cfg.data_root,
        "20260530-100000",
        [{"kind": "event", "type": "HEARTBEAT"}, {"kind": "citation_count", "count": 0}],
    )
    out = dms.tool_tail_events(cfg, lines=10)
    assert out["count"] == 2
    assert out["events"][0] == {"kind": "event", "type": "HEARTBEAT"}
    # The anti-slop signal is visible to the agent.
    assert out["events"][1]["count"] == 0


def test_tail_events_picks_newest_by_mtime(tmp_path):
    cfg = _cfg(tmp_path)
    old = _write_session(cfg.data_root, "20260530-090000", [{"kind": "event", "type": "OLD"}])
    new = _write_session(cfg.data_root, "20260530-110000", [{"kind": "event", "type": "NEW"}])
    # Force mtime ordering deterministically (name sort != mtime sort guard).
    import os

    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))
    out = dms.tool_tail_events(cfg)
    assert out["events"][0]["type"] == "NEW"


def test_tail_events_named_session_by_bare_name(tmp_path):
    cfg = _cfg(tmp_path)
    _write_session(cfg.data_root, "20260530-090000", [{"kind": "event", "type": "PICKME"}])
    _write_session(cfg.data_root, "20260530-110000", [{"kind": "event", "type": "OTHER"}])
    out = dms.tool_tail_events(cfg, session="20260530-090000")
    assert out["events"][0]["type"] == "PICKME"


# ---------------------------------------------------------------------------
# which_handler — reuse the check_ipc_wiring scanner against the REAL repo
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[2]
_HAS_CHECKER = (
    _REPO / ".claude" / "skills" / "ipc-wiring-checker" / "scripts" / "check_ipc_wiring.py"
).exists()


@pytest.mark.skipif(not _HAS_CHECKER, reason="ipc-wiring-checker skill not in this checkout")
def test_which_handler_resolves_wired_type():
    cfg = dms.DevServerConfig(repo_root=_REPO)
    out = dms.tool_which_handler(cfg, "ipc.session.snapshot")
    assert out["matched_types"] == ["ipc.session.snapshot"]
    res = out["results"][0]
    assert res["type"] == "ipc.session.snapshot"
    # snapshot is emitted by the sidecar and consumed by the shell -> WIRED.
    assert res["wiring"].startswith("WIRED")
    assert res["sidecar_py"]  # at least one python ref


@pytest.mark.skipif(not _HAS_CHECKER, reason="ipc-wiring-checker skill not in this checkout")
def test_which_handler_substring_resolves_control():
    cfg = dms.DevServerConfig(repo_root=_REPO)
    out = dms.tool_which_handler(cfg, "session")
    # "session" is a substring of several real ipc types.
    assert len(out["matched_types"]) >= 1
    assert all("session" in t for t in out["matched_types"])


def test_which_handler_missing_checker_is_actionable(tmp_path):
    cfg = _cfg(tmp_path)  # repo_root is an empty tmp dir -> no skill present
    out = dms.tool_which_handler(cfg, "ipc.session.snapshot")
    assert "error" in out
    assert "repo-root" in out["error"]


def test_which_handler_unknown_type_is_honest(tmp_path):
    if not _HAS_CHECKER:
        pytest.skip("checker absent")
    cfg = dms.DevServerConfig(repo_root=_REPO)
    out = dms.tool_which_handler(cfg, "ipc.totally.invented.type.xyz")
    assert out["matched_types"] == []
    assert "note" in out


# ---------------------------------------------------------------------------
# ws_observe / ws_trigger — against a FAKE in-process server on an EPHEMERAL
# port (never :8765). The dev server attaches as a CLIENT only.
# ---------------------------------------------------------------------------


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_ws_observe_refused_is_actionable():
    # Nothing listening on this port -> fail-soft with the launch hint.
    cfg = dms.DevServerConfig(ws_uri=f"ws://127.0.0.1:{_free_port()}")
    out = asyncio.run(dms.tool_ws_observe_async(cfg, seconds=0.3))
    assert "error" in out
    assert out["count"] == 0
    assert "Invariant #4" in out["error"]


def test_ws_observe_collects_frames_from_fake_bus():
    websockets = pytest.importorskip("websockets")

    async def scenario():
        port = _free_port()
        sent = [
            {"music": 0.1, "voice": 0.0, "mic": 0.0, "audible": True},  # mascot frame
            {"type": "ipc.session.snapshot", "payload": {"cohost_status": "TALKING"}},
            {"type": "ipc.status.tick", "payload": {"gemini": "ok"}},
        ]

        async def handler(ws):
            for f in sent:
                await ws.send(json.dumps(f))
            # Keep the connection open until the observer's window closes.
            await asyncio.sleep(1.0)

        server = await websockets.serve(handler, "127.0.0.1", port)
        try:
            cfg = dms.DevServerConfig(ws_uri=f"ws://127.0.0.1:{port}")
            # No filter -> all three frames.
            allf = await dms.tool_ws_observe_async(cfg, seconds=0.6)
            # Only the snapshot.
            snap = await dms.tool_ws_observe_async(
                cfg, seconds=0.6, type_filter="ipc.session.snapshot"
            )
            # Only the mascot (type-less + meters) frame.
            masc = await dms.tool_ws_observe_async(cfg, seconds=0.6, type_filter="mascot")
            return allf, snap, masc
        finally:
            server.close()
            await server.wait_closed()

    allf, snap, masc = asyncio.run(scenario())
    assert allf["count"] == 3
    assert snap["count"] == 1
    assert snap["frames"][0]["payload"]["cohost_status"] == "TALKING"
    assert masc["count"] == 1
    assert "type" not in masc["frames"][0]


def test_ws_trigger_sends_frame_to_fake_bus():
    websockets = pytest.importorskip("websockets")

    async def scenario():
        port = _free_port()
        received: list[dict] = []

        async def handler(ws):
            try:
                async for raw in ws:
                    frame = json.loads(raw)
                    received.append(frame)
                    if frame.get("type") == "ipc.settings.get":
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "ipc.settings.get_result",
                                    "payload": {"key": "voice", "value": "on"},
                                }
                            )
                        )
            except Exception:
                pass

        server = await websockets.serve(handler, "127.0.0.1", port)
        try:
            cfg = dms.DevServerConfig(ws_uri=f"ws://127.0.0.1:{port}")
            conf = await dms.tool_ws_trigger_async(cfg, action="trigger")
            # Give the server a beat to record the frame.
            await asyncio.sleep(0.2)
            ipc_conf = await dms.tool_ws_trigger_async(
                cfg, action="ipc.settings.get", payload={"key": "voice"}
            )
            await asyncio.sleep(0.2)
            return conf, ipc_conf, received
        finally:
            server.close()
            await server.wait_closed()

    conf, ipc_conf, received = asyncio.run(scenario())
    # The bare control went as {action: trigger}.
    assert conf["sent"] == {"action": "trigger"}
    # The ipc.* action was wrapped as a typed envelope {type, ts, payload}.
    assert ipc_conf["sent"]["type"] == "ipc.settings.get"
    assert ipc_conf["sent"]["payload"] == {"key": "voice"}
    ts = datetime.fromisoformat(ipc_conf["sent"]["ts"])
    assert ts.tzinfo == UTC
    # The fake bus actually received both frames.
    assert {"action": "trigger"} in received
    received_ipc = next(r for r in received if r.get("type") == "ipc.settings.get")
    assert datetime.fromisoformat(received_ipc["ts"]).tzinfo == UTC
    assert ipc_conf["reply"] == {
        "type": "ipc.settings.get_result",
        "payload": {"key": "voice", "value": "on"},
    }


def test_learn_probe_starts_lesson_sends_ack_and_summarizes_frames():
    websockets = pytest.importorskip("websockets")

    async def scenario():
        port = _free_port()
        received: list[dict] = []

        async def handler(ws):
            raw_start = await ws.recv()
            start = json.loads(raw_start)
            received.append(start)
            assert start["type"] == "ipc.learn.start_lesson"
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.lesson_loaded",
                        "payload": {"lesson_id": "L1.03"},
                    }
                )
            )
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.highlight",
                        "payload": {"control_id": "eq_hi:A"},
                    }
                )
            )
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.tutor_speak",
                        "payload": {
                            "text": (
                                "twist the top EQ knob on deck A and listen "
                                "for the cymbals getting brighter or darker."
                            )
                        },
                    }
                )
            )

            raw_ack = await ws.recv()
            ack = json.loads(raw_ack)
            received.append(ack)
            assert ack["type"] == "ipc.learn.ack"
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.advance",
                        "payload": {"lesson_id": "L1.03", "reason": "action_matched"},
                    }
                )
            )
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.complete_lesson",
                        "payload": {"lesson_id": "L1.03", "reason": "completed"},
                    }
                )
            )
            await asyncio.sleep(0.1)

        server = await websockets.serve(handler, "127.0.0.1", port)
        try:
            cfg = dms.DevServerConfig(ws_uri=f"ws://127.0.0.1:{port}")
            out = await dms.tool_learn_probe_async(
                cfg,
                lesson_id="L1.03",
                control_id="eq_hi:A",
                value=65,
                prev_value=64,
                settle_seconds=0.4,
            )
            return out, received
        finally:
            server.close()
            await server.wait_closed()

    out, received = asyncio.run(scenario())
    assert [frame["type"] for frame in received] == [
        "ipc.learn.start_lesson",
        "ipc.learn.ack",
    ]
    assert received[1]["payload"] == {
        "control_id": "eq_hi:A",
        "source": "midi",
        "value": 65,
        "prev_value": 64,
        "direction": "down",
    }
    assert out["summary"]["lesson_loaded"] is True
    assert out["summary"]["highlighted_controls"] == ["eq_hi:A"]
    assert out["summary"]["advanced"] is True
    assert out["summary"]["completed"] is True


def test_ws_trigger_refused_is_actionable():
    cfg = dms.DevServerConfig(ws_uri=f"ws://127.0.0.1:{_free_port()}")
    out = asyncio.run(dms.tool_ws_trigger_async(cfg, action="trigger"))
    assert "error" in out
    assert "Invariant #4" in out["error"]


def test_ws_tools_fail_soft_on_malformed_uri():
    # A bad scheme raises websockets InvalidURI (NOT an OSError subclass). All
    # three ws-touching tools must catch it and return an actionable dict, never
    # let a raw traceback escape (fail-soft contract). Regression for the
    # OSError-only catch that let InvalidURI through.
    pytest.importorskip("websockets")
    bad = dms.DevServerConfig(ws_uri="http://127.0.0.1:1/not-ws")
    obs = asyncio.run(dms.tool_ws_observe_async(bad, seconds=0.2))
    assert "error" in obs and obs["count"] == 0
    trig = asyncio.run(dms.tool_ws_trigger_async(bad, action="trigger"))
    assert "error" in trig
    stat = asyncio.run(dms.tool_sidecar_status_async(bad))
    assert stat["ws_reachable"] is False
    assert stat["ws_error"]


# ---------------------------------------------------------------------------
# sidecar_status — brain-mute diagnostic; presence-only, never the key value
# ---------------------------------------------------------------------------


def test_sidecar_status_reports_unreachable_and_no_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_DEV_SIDECAR", raising=False)
    cfg = _cfg(tmp_path, ws_uri=f"ws://127.0.0.1:{_free_port()}")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)
    out = asyncio.run(dms.tool_sidecar_status_async(cfg))
    assert out["ws_reachable"] is False
    assert out["ws_error"]
    assert out["dev_sidecar"] is False
    assert out["gemini_key_present"] is False
    assert out["gemini_key_source"] is None
    assert "brain_mute_hint" in out


def test_sidecar_status_detects_key_in_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-value")
    monkeypatch.setenv("VIBEMIX_DEV_SIDECAR", "1")
    cfg = _cfg(tmp_path, ws_uri=f"ws://127.0.0.1:{_free_port()}")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)
    out = asyncio.run(dms.tool_sidecar_status_async(cfg))
    assert out["gemini_key_present"] is True
    assert out["gemini_key_source"] == "env"
    assert out["dev_sidecar"] is True
    # The KEY VALUE is never echoed back anywhere in the response.
    assert "fake-key-value" not in json.dumps(out)


def test_sidecar_status_detects_key_in_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".env").write_text("GEMINI_API_KEY=sekret-from-dotenv\nOTHER=1\n")
    cfg = _cfg(tmp_path, repo_root=repo, ws_uri=f"ws://127.0.0.1:{_free_port()}")
    out = asyncio.run(dms.tool_sidecar_status_async(cfg))
    assert out["gemini_key_present"] is True
    assert out["gemini_key_source"] == str(repo / ".env")
    assert "sekret-from-dotenv" not in json.dumps(out)


def test_gemini_key_present_ignores_empty_value(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".env").write_text("GEMINI_API_KEY=\n")
    present, src = dms._gemini_key_present(repo)
    assert present is False
    assert src is None
