# SPDX-License-Identifier: Apache-2.0
"""Keyless deterministic set/crate builder.

``auto_crate`` is the structured gig-prep path beside conversational Viber:
it calls the already-grounded LibraryToolset handlers directly, with no Codex
binary, no login, no shell-bypass, and no model prompt. Fuzzy natural-language
brief interpretation stays on ``library build-set``; this module is for a
bounded query/reference pool plus an explicit energy curve.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from itertools import pairwise
from typing import Any

OWNER_GATES = (
    "O7: product framing for auto_crate as default front door vs Codex fuzzy-brief path",
    "O10: Free/Pro/Studio tier placement for keyless gig-prep",
)

DEFAULT_SET_MIN_DURATION_S = 120.0


@dataclass(slots=True)
class AutoCrateResult:
    """Outcome of one deterministic auto-crate run."""

    name: str | None
    stop_reason: str
    curve: str
    n_slots: int
    query: str | None = None
    ref_track_ids: list[str] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    playlist: dict[str, Any] | None = None
    export_path: str | None = None
    sequence: dict[str, Any] | None = None
    transition_receipts: list[dict[str, Any]] = field(default_factory=list)
    metadata_warnings: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    owner_gates: list[str] = field(default_factory=lambda: list(OWNER_GATES))
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_default_toolset(*, with_embedder: bool = True) -> Any:
    """Build the local LibraryToolset used by the keyless path."""
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.library.staleness import library_freshness_status
    from vibemix.library.store import open_store
    from vibemix.library.toolset import LibraryToolset

    library = RekordboxLibrary()
    if not library.try_load_cache():
        raise RuntimeError(
            "No library cache. Drag a Rekordbox XML onto Settings -> Library "
            "(or run `library embed-folder`) first."
        )
    return LibraryToolset(
        _build_embedder() if with_embedder else None,
        open_store(),
        library,
        freshness_provider=library_freshness_status,
    )


def build_auto_crate(
    *,
    query: str | None = None,
    ref_track_ids: list[str] | None = None,
    curve: str = "opener",
    n_slots: int = 6,
    k: int = 40,
    name: str | None = None,
    export: str | None = None,
    out_path: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    min_duration_s: float | None = None,
    max_duration_s: float | None = None,
    novelty: float | None = None,
    toolset: Any | None = None,
) -> AutoCrateResult:
    """Build a grounded sequence and persist it as playlist/export artifacts."""
    refs = [tid.strip() for tid in (ref_track_ids or []) if isinstance(tid, str) and tid.strip()]
    clean_query = query.strip() if isinstance(query, str) and query.strip() else None
    slots = _positive_int(n_slots, default=6)
    pool_limit = _positive_int(k, default=40)
    clean_name = name.strip() if isinstance(name, str) and name.strip() else None
    result_name = clean_name or _default_name(clean_query, curve)
    trace: list[dict[str, Any]] = []

    if not refs and clean_query is None:
        return AutoCrateResult(
            name=result_name,
            stop_reason="no_intent",
            curve=curve,
            n_slots=slots,
            query=clean_query,
            ref_track_ids=refs,
            tool_trace=trace,
            error="auto-crate needs a query and/or at least one --ref-track-id",
        )

    owns_toolset = toolset is None
    if toolset is None:
        try:
            toolset = build_default_toolset(with_embedder=clean_query is not None)
        except Exception as exc:
            return AutoCrateResult(
                name=result_name,
                stop_reason="setup_error",
                curve=curve,
                n_slots=slots,
                query=clean_query,
                ref_track_ids=refs,
                tool_trace=trace,
                error=str(exc),
            )

    try:
        effective_min_duration_s = _default_set_min_duration(
            min_duration_s,
            max_duration_s=max_duration_s,
        )
        discover_args: dict[str, Any] = {"k": pool_limit}
        if clean_query is not None:
            discover_args["query"] = clean_query
        if refs:
            discover_args["ref_track_ids"] = refs
        for key, value in (
            ("bpm_min", bpm_min),
            ("bpm_max", bpm_max),
            ("min_duration_s", effective_min_duration_s),
            ("max_duration_s", max_duration_s),
        ):
            if value is not None:
                discover_args[key] = value

        discovered = _call_tool(toolset, "discover_pool", discover_args, trace)
        if error := discovered.get("error"):
            return _failed("no_pool", str(error), result_name, curve, slots, clean_query, refs, trace)
        pool = discovered.get("pool")
        pool_ids = [row.get("track_id") for row in pool if isinstance(row, dict)] if isinstance(pool, list) else []
        pool_ids = [tid for tid in pool_ids if isinstance(tid, str)]
        if not pool_ids:
            return _failed(
                "no_pool",
                "discover_pool returned no grounded candidates",
                result_name,
                curve,
                slots,
                clean_query,
                refs,
                trace,
            )

        sequence_args: dict[str, Any] = {"track_ids": pool_ids, "curve": curve, "n_slots": slots}
        if novelty is not None:
            sequence_args["novelty"] = novelty
        sequenced = _call_tool(toolset, "sequence_set", sequence_args, trace)
        if error := sequenced.get("error"):
            return _failed(
                "no_sequence", str(error), result_name, curve, slots, clean_query, refs, trace
            )
        candidates = sequenced.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return _failed(
                "no_sequence",
                "sequence_set returned no candidates",
                result_name,
                curve,
                slots,
                clean_query,
                refs,
                trace,
            )
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        track_ids = [tid for tid in candidate.get("track_ids", []) if isinstance(tid, str)]
        if not track_ids:
            return _failed(
                "no_sequence",
                "best sequence candidate carried no track_ids",
                result_name,
                curve,
                slots,
                clean_query,
                refs,
                trace,
            )

        receipts = _transition_receipts(toolset, track_ids, trace)
        playlist = _call_tool(toolset, "create_playlist", {"name": result_name, "track_ids": track_ids}, trace)
        if error := playlist.get("error"):
            return _failed(
                "no_playlist", str(error), result_name, curve, slots, clean_query, refs, trace
            )

        export_path = None
        stop_reason = "created"
        if export == "rekordbox":
            export_args: dict[str, Any] = {"name": result_name, "track_ids": track_ids}
            if out_path:
                export_args["out_path"] = out_path
            exported = _call_tool(toolset, "export_set", export_args, trace)
            if error := exported.get("error"):
                return _failed(
                    "export_error", str(error), result_name, curve, slots, clean_query, refs, trace
                )
            export_path = str(exported.get("path") or "") or None
            stop_reason = "exported" if export_path else "created"

        warnings = discovered.get("metadata_warnings")
        metadata_warnings = warnings if isinstance(warnings, list) else []
        return AutoCrateResult(
            name=result_name,
            stop_reason=stop_reason,
            curve=curve,
            n_slots=slots,
            query=clean_query,
            ref_track_ids=refs,
            track_ids=track_ids,
            rationale=_grounded_rationale(
                curve=curve,
                pool_count=len(pool_ids),
                candidate=candidate,
                metadata_warnings=metadata_warnings,
                transition_receipts=receipts,
            ),
            playlist={k: playlist[k] for k in playlist if k != "created"},
            export_path=export_path,
            sequence=candidate,
            transition_receipts=receipts,
            metadata_warnings=metadata_warnings,
            tool_trace=trace,
        )
    finally:
        if owns_toolset:
            close = getattr(getattr(toolset, "_store", None), "close", None)
            if callable(close):
                close()


def _call_tool(toolset: Any, name: str, args: dict[str, Any], trace: list[dict[str, Any]]) -> dict[str, Any]:
    dispatch = getattr(toolset, "dispatch", None)
    if callable(dispatch):
        out = dispatch(name, args)
    else:
        handler = getattr(toolset, name)
        out = handler(args)
    if not isinstance(out, dict):
        out = {"error": f"{name} returned {type(out).__name__}"}
    trace.append(
        {
            "name": name,
            "ok": "error" not in out,
            "summary": _summary(name, args, out),
        }
    )
    return out


def _transition_receipts(
    toolset: Any, track_ids: list[str], trace: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for source_id, destination_id in pairwise(track_ids):
        out = _call_tool(
            toolset,
            "transition_slate",
            {
                "source_track_id": source_id,
                "candidate_track_ids": [destination_id],
                "mode": "prep",
                "max_candidates": 1,
            },
            trace,
        )
        row: dict[str, Any] = {"from": source_id, "to": destination_id}
        if error := out.get("error"):
            row["error"] = error
        else:
            candidates = out.get("candidates")
            if isinstance(candidates, list) and candidates:
                first = candidates[0] if isinstance(candidates[0], dict) else {}
                row.update(
                    {
                        "candidate_id": first.get("candidate_id"),
                        "score": first.get("score"),
                        "risk_flags": first.get("risk_flags", []),
                    }
                )
            else:
                row["error"] = "transition_slate returned no candidates"
        receipts.append(row)
    return receipts


def _grounded_rationale(
    *,
    curve: str,
    pool_count: int,
    candidate: dict[str, Any],
    metadata_warnings: list[dict[str, Any]],
    transition_receipts: list[dict[str, Any]],
) -> str:
    track_ids = candidate.get("track_ids") if isinstance(candidate, dict) else []
    selected = len(track_ids) if isinstance(track_ids, list) else 0
    parts = [f"{selected} tracks selected from {pool_count} discovered candidates on curve {curve}."]
    if (energy_fit := _finite_float(candidate.get("energy_fit"))) is not None:
        parts.append(f"Energy fit error {energy_fit:.1f} (lower is better).")
    if (coherence := _finite_float(candidate.get("avg_coherence"))) is not None:
        parts.append(f"Average coherence {coherence:.3f}.")
    relaxed = candidate.get("relaxed_transitions")
    if isinstance(relaxed, int):
        parts.append(f"Relaxed transitions {relaxed}.")
    elif isinstance(relaxed, list):
        parts.append(f"Relaxed transitions {len(relaxed)}.")
    for warning in metadata_warnings:
        if isinstance(warning, dict) and warning.get("field") == "bpm":
            unknown = warning.get("unknown_count")
            total = warning.get("total_count")
            parts.append(f"BPM metadata warning: {unknown}/{total} discovered tracks unknown.")
    resolved = sum(1 for row in transition_receipts if "candidate_id" in row)
    if transition_receipts:
        parts.append(f"Transition receipts resolved {resolved}/{len(transition_receipts)}.")
    return " ".join(parts)


def _failed(
    stop_reason: str,
    error: str,
    name: str,
    curve: str,
    n_slots: int,
    query: str | None,
    ref_track_ids: list[str],
    tool_trace: list[dict[str, Any]],
) -> AutoCrateResult:
    return AutoCrateResult(
        name=name,
        stop_reason=stop_reason,
        curve=curve,
        n_slots=n_slots,
        query=query,
        ref_track_ids=ref_track_ids,
        tool_trace=tool_trace,
        error=error,
    )


def _summary(name: str, args: dict[str, Any], out: dict[str, Any]) -> str:
    if "error" in out:
        return str(out["error"])[:180]
    if name == "discover_pool":
        pool = out.get("pool")
        parts = [f"{len(pool) if isinstance(pool, list) else 0} candidates"]
        if args.get("min_duration_s") is not None:
            parts.append(f"min_dur={args['min_duration_s']}s")
        if args.get("max_duration_s") is not None:
            parts.append(f"max_dur={args['max_duration_s']}s")
        return "; ".join(parts)
    if name == "sequence_set":
        candidates = out.get("candidates")
        return f"{len(candidates) if isinstance(candidates, list) else 0} sequences"
    if name in {"create_playlist", "export_set"}:
        return str(out.get("path") or out.get("m3u_path") or out.get("track_count") or "ok")
    if name == "transition_slate":
        candidates = out.get("candidates")
        source = args.get("source_track_id")
        return f"{source}: {len(candidates) if isinstance(candidates, list) else 0} candidates"
    return "ok"


def _default_name(query: str | None, curve: str) -> str:
    if query:
        words = [word for word in query.replace("/", " ").split() if word]
        if words:
            return " ".join(words[:6]).title()
    return f"Auto Crate {curve.replace('_', ' ').title()}"


def _finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _positive_int(value: Any, *, default: int) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, out)


def _default_set_min_duration(
    min_duration_s: float | None,
    *,
    max_duration_s: float | None,
) -> float | None:
    """Default deterministic set prep to playable-length tracks.

    Explicit user filters win. If max duration is below the default floor, treat
    that as an intentional short-tool crate and avoid a conflicting minimum.
    """
    if min_duration_s is not None:
        return min_duration_s
    if max_duration_s is not None and max_duration_s < DEFAULT_SET_MIN_DURATION_S:
        return None
    return DEFAULT_SET_MIN_DURATION_S


def _build_embedder() -> Any:
    from vibemix.library.embed_factory import build_embedder

    return build_embedder()


__all__ = ["OWNER_GATES", "AutoCrateResult", "build_auto_crate", "build_default_toolset"]
