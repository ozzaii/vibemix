# SPDX-License-Identifier: Apache-2.0
"""LibraryToolset — the shared grounded Codex/Viber tool core.

These tests pin the grounding gate (Cardinal Invariant #2) directly on the
toolset, independent of the Codex MCP process that drives it.

No network: vibe_search is monkeypatched, the library is in-memory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library import toolset as tool_mod
from vibemix.library.create_playlist import create_playlist
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def test_local_toolset_import_does_not_load_gemini_sdk() -> None:
    """Codex/MCP local tools must not wake the legacy Gemini embedder SDK."""
    code = """
import json
import sys

import vibemix.library.embed
import vibemix.library.mcp_server
import vibemix.library.toolset

mods = sorted(
    m for m in sys.modules
    if m == "google.genai" or m.startswith("google.genai.")
)
print(json.dumps(mods))
raise SystemExit(1 if mods else 0)
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout) == []


def test_mcp_product_surface_does_not_expose_gemini_youtube_tool(monkeypatch) -> None:
    """The shipped Codex/Viber MCP tool list is local-first and keyless."""
    from vibemix.library import mcp_server

    registered: list[str] = []

    class FakeFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self):
            def register(fn):
                registered.append(fn.__name__)
                return fn

            return register

    fastmcp_mod = ModuleType("mcp.server.fastmcp")
    fastmcp_mod.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", ModuleType("mcp"))
    monkeypatch.setitem(sys.modules, "mcp.server", ModuleType("mcp.server"))
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_mod)

    mcp_server.build_server(SimpleNamespace())

    assert "search_vibe" in registered
    assert "discover_pool" in registered
    assert "get_track_sections" in registered
    assert "transition_slate" in registered
    assert "compile_musical_context" in registered
    assert "smart_hot_cues" in registered
    assert "export_smart_cues" in registered
    assert "ingest_youtube" not in registered


def test_shared_toolset_does_not_dispatch_gemini_youtube_tool(toolset) -> None:
    out = toolset.dispatch(
        "ingest_youtube",
        {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert out == {"error": "unknown tool 'ingest_youtube'"}


def _make_track(
    tid: str,
    bpm: float = 124.0,
    key: str = "8A",
    *,
    cues: tuple[CuePoint, ...] = (),
) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=cues,
        filepath=f"/tmp/{tid}.mp3",
    )


def _section(section_id: str, role: str, start_s: float, end_s: float) -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id="t000",
        role=role,
        source="anlz",
        source_detail="pssi",
        confidence=0.9,
        start_s=start_s,
        end_s=end_s,
        start_beat=round(start_s * 2),
        end_beat=round(end_s * 2),
        bar_count=(end_s - start_s) * 124.0 / 60.0 / 4.0,
        bpm=124.0,
        camelot="8A",
    )


def _issue_smart_cue_proposal(toolset, monkeypatch):
    sections = (
        _section("t000#s000", "intro", 0.0, 32.0),
        _section("t000#s001", "drop", 64.0, 128.0),
        _section("t000#s002", "outro", 192.0, 240.0),
    )
    monkeypatch.setattr(tool_mod, "sections_for_entry", lambda entry: sections)
    toolset.seen.add("t000")
    out = toolset.smart_hot_cues({"track_id": "t000"})
    return out["proposals"][0]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(5)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


def _stub_search(monkeypatch, ids):
    def fake(emb, st, lib, query, k=15):
        return (
            [
                SimpleNamespace(track_id=t, title=f"T{t}", artist="A", bpm=124.0, confidence=0.9)
                for t in ids
            ],
            False,
        )

    monkeypatch.setattr(tool_mod, "vibe_search", fake)


def test_search_populates_seen_set(toolset, monkeypatch):
    _stub_search(monkeypatch, ["t000", "t001"])
    out = toolset.search_vibe({"query": "hypnotic", "k": 2})
    assert {r["track_id"] for r in out["results"]} == {"t000", "t001"}
    assert toolset.seen == {"t000", "t001"}


def test_create_rejects_invented_id(toolset, monkeypatch, tmp_path):
    _stub_search(monkeypatch, ["t000"])
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )
    toolset.search_vibe({"query": "x", "k": 1})
    # GHOST never came from search → whole call rejected, nothing persisted.
    out = toolset.create_playlist({"name": "P", "track_ids": ["t000", "GHOST"]})
    assert "error" in out
    assert "GHOST" in out["error"]
    assert toolset.created is None


def test_create_persists_grounded_playlist(toolset, monkeypatch, tmp_path):
    _stub_search(monkeypatch, ["t000", "t001", "t002"])
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )
    toolset.search_vibe({"query": "x", "k": 3})
    out = toolset.create_playlist({"name": "Warm-Up", "track_ids": ["t000", "t001", "t002"]})
    assert out["created"] is True
    assert out["track_ids"] == ["t000", "t001", "t002"]
    assert out["track_count"] == 3
    assert toolset.created is not None


def test_features_camelot_is_deterministic(toolset):
    out = toolset.get_track_features({"track_id": "t000"})
    assert out["key"] == "8A"
    assert out["bpm"] == 124.0
    # Musical-notation key normalizes deterministically (never LLM-computed).
    toolset._library.tracks["t099"] = _make_track("t099", key="Am")
    out = toolset.get_track_features({"track_id": "t099"})
    assert out["key"] == "8A"  # Am → 8A


def test_dispatch_errors_never_raise(toolset):
    assert "error" in toolset.dispatch("search_vibe", {"query": ""})
    assert "error" in toolset.dispatch("get_track_features", {"track_id": "NOPE"})
    assert "error" in toolset.dispatch("create_playlist", {"name": "x", "track_ids": []})
    assert "error" in toolset.dispatch("does_not_exist", {})


def test_smart_hot_cues_rejects_unseen_track(toolset):
    out = toolset.smart_hot_cues({"track_id": "t000"})

    assert "error" in out
    assert "invented" in out["error"]
    assert toolset.issued_cue_proposals == {}


def test_smart_hot_cues_records_issued_proposal(toolset, monkeypatch):
    proposal = _issue_smart_cue_proposal(toolset, monkeypatch)

    proposal_id = proposal["proposal_id"]
    assert proposal_id in toolset.issued_cue_proposals
    assert {cue["slot"] for cue in proposal["cues"]} >= {"A", "D", "F"}
    assert all(cue["cue_id"].startswith(proposal_id + ":") for cue in proposal["cues"])


def test_export_smart_cues_rejects_unissued_proposal(toolset):
    out = toolset.export_smart_cues({"proposal_id": "cueprop_missing"})

    assert "error" in out
    assert "not issued" in out["error"]


def test_export_smart_cues_rejects_raw_model_payload(toolset, monkeypatch):
    proposal = _issue_smart_cue_proposal(toolset, monkeypatch)

    out = toolset.export_smart_cues(
        {
            "proposal_id": proposal["proposal_id"],
            "track_path": "/tmp/smuggled.wav",
            "cues": [{"label": "drop", "start_s": 1.0}],
        }
    )

    assert "error" in out
    assert "rejects raw cue payloads" in out["error"]


def test_export_smart_cues_rejects_cue_id_outside_proposal(toolset, monkeypatch):
    proposal = _issue_smart_cue_proposal(toolset, monkeypatch)

    out = toolset.export_smart_cues(
        {
            "proposal_id": proposal["proposal_id"],
            "selected_cue_ids": [proposal["proposal_id"] + ":Z"],
        }
    )

    assert "error" in out
    assert "not issued in this proposal" in out["error"]


def test_export_smart_cues_revalidates_track_at_write_time(toolset, monkeypatch):
    proposal = _issue_smart_cue_proposal(toolset, monkeypatch)
    del toolset._library.tracks["t000"]

    out = toolset.export_smart_cues({"proposal_id": proposal["proposal_id"]})

    assert "error" in out
    assert "track missing" in out["error"]


def test_export_smart_cues_preserves_slot_nums(toolset, monkeypatch, tmp_path):
    from vibemix.library.export_rekordbox import ExportResult

    proposal = _issue_smart_cue_proposal(toolset, monkeypatch)
    proposal_id = proposal["proposal_id"]
    selected = [f"{proposal_id}:A", f"{proposal_id}:D", f"{proposal_id}:F"]
    captured: dict[str, object] = {}

    def fake_export_set(items, name, out_path, library=None):
        captured["items"] = items
        captured["name"] = name
        captured["out_path"] = out_path
        captured["library"] = library
        return ExportResult(path=tmp_path / "smart-cues.xml", written=1, referenced=1)

    from vibemix.library import export_rekordbox

    monkeypatch.setattr(export_rekordbox, "export_set", fake_export_set)

    out = toolset.export_smart_cues(
        {
            "proposal_id": proposal_id,
            "selected_cue_ids": selected,
            "out_path": str(tmp_path / "smart-cues.xml"),
        }
    )

    assert out["exported"] is True
    assert out["cue_ids"] == selected
    cues = captured["items"][0]["cues"]  # type: ignore[index]
    assert {cue["num"] for cue in cues} == {0, 3, 5}
    assert {cue["name"] for cue in cues} == {"VM A IN", "VM D DROP", "VM F OUT"}


# ---------------------------------------------------------------------------
# Phase 82 Wave 0 — CURATE-01 SEAM #1: genre via the ONE perception mechanism
#
# Today `get_track_features` hardcodes `genre: None` (toolset.py:124). Plan 02
# routes it through the SHARED `genre_prototypes` mechanism the co-host already
# reads (state/refresh.py:254 -> GenrePrototypeLookup.classify_playing), so the
# curator and co-host derive genre from ONE source — not two parallel notions.
#
# Plan 02 (this commit) landed the seam: get_track_features now routes genre
# through GenrePrototypeLookup.classify_playing, so these are real-green (the
# xfail scaffolds flipped). Honest-null on the mechanism's abstain.
#
# Honest green: NO genai.Client, NO GEMINI_API_KEY. The in-memory `library`
# fixture sets `lib.tracks` directly and never writes RekordboxLibrary.CACHE_PATH
# (the library.pkl gotcha) — we monkeypatch the prototype mechanism instead.
# Pitfall 2: the assertions pin that the curator routes through `genre_prototypes`
# (classify_playing), NEVER a fresh np.mean/cosine classifier in toolset.py.
# ---------------------------------------------------------------------------

from vibemix.library import genre_prototypes as _proto_mod  # noqa: E402


def test_genre_via_prototypes_when_classified(toolset, monkeypatch):
    """get_track_features routes genre through the shared prototype mechanism.

    Monkeypatch the ONE perception mechanism (GenrePrototypeLookup.classify_playing)
    to return a real label for the known track; assert the seam surfaces that
    library-derived label — NOT the hardcoded `None` of today.
    """

    def fake_classify_playing(self, track_id: str):
        return ("hardtechno", 0.91) if track_id == "t000" else ("unknown", 0.0)

    # Patch the class method — robust to however the seam binds the lookup.
    monkeypatch.setattr(
        _proto_mod.GenrePrototypeLookup,
        "classify_playing",
        fake_classify_playing,
        raising=True,
    )
    out = toolset.get_track_features({"track_id": "t000"})
    assert out["genre"] == "hardtechno", (
        "CURATE-01: genre must be the prototype-resolved label, not None"
    )


def test_genre_honest_none_on_abstain(toolset, monkeypatch):
    """On prototype abstain (("unknown", 0.0)), genre is honest-null, never fabricated.

    This pins TWO things at once: (1) the seam actually CONSULTS the shared
    prototype mechanism (it must be called — proven by the spy), and (2) on its
    abstain the genre is honest-null (None/"unknown"), byte-identical class to
    today's `genre: None` and the Camelot honest-null at toolset.py:116. The
    model NEVER invents a genre (invariant #3, Trust the audio).

    RED today because the seam does not yet call the mechanism (the spy is never
    hit); it flips GREEN only when Plan 02 routes the curator genre through
    `genre_prototypes` — a strict xfail, so the "genre is already None" path can
    never silently satisfy it.
    """
    called: list[str] = []

    def fake_abstain(self, track_id: str):
        called.append(track_id)
        return ("unknown", 0.0)

    monkeypatch.setattr(
        _proto_mod.GenrePrototypeLookup,
        "classify_playing",
        fake_abstain,
        raising=True,
    )
    out = toolset.get_track_features({"track_id": "t000"})
    # The seam MUST route through the shared mechanism (Pitfall 2: no parallel
    # classifier) — proven by the spy firing for this track_id.
    assert called == ["t000"], (
        "CURATE-01: get_track_features must consult genre_prototypes, not a "
        "parallel np.mean/cosine classifier"
    )
    assert out["genre"] in (None, "unknown"), (
        "CURATE-01: prototype abstain must yield honest-null genre, never a fabrication"
    )
