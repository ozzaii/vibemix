#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit and optionally play the packaged Learn EQ exemplars.

Default mode is non-interactive and prints one JSON summary:

    uv run python scripts/audition_learn_exemplars.py

Human ear-pass mode uses the same dedicated Learn exemplar player seam:

    uv run python scripts/audition_learn_exemplars.py --play --device-index 3
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_exemplar_mod = importlib.import_module("vibemix.learn.exemplar")
_audio_decode_mod = importlib.import_module("vibemix.library.audio_decode")

_packaged_bank_dir = _exemplar_mod._packaged_bank_dir
load_audio_stereo = _audio_decode_mod.load_audio_stereo
EXPECTED_BANDS = ("sub", "low", "mid", "high")
RMS_FLOOR = 1e-6
DEFAULT_PROOF_DIR = Path("/tmp/vibemix-live-learn-proof")
DEFAULT_APPROVAL_PATH = DEFAULT_PROOF_DIR / "learn-exemplar-ear-pass-current.json"
DEFAULT_AUDITION_PATH = DEFAULT_PROOF_DIR / "learn-exemplar-audition-current.json"
VIRTUAL_OUTPUT_TOKENS = (
    "blackhole",
    "loopback",
    "soundflower",
    "aggregate",
    "capture",
    "rekordbox",
)
PRIMARY_AUDIBLE_OUTPUT_TOKENS = ("speaker", "headphone", "headphon")
DJ_AUDIBLE_OUTPUT_TOKENS = ("ddj", "flx")


def operator_commands() -> dict[str, str]:
    """Return the exact human ear-pass command sequence."""
    approval_path = str(DEFAULT_APPROVAL_PATH)
    return {
        "list_output_devices": (
            "uv run python scripts/audition_learn_exemplars.py --list-devices"
        ),
        "play": (
            "uv run python scripts/audition_learn_exemplars.py --play "
            "--device-index <output-device-index> --say-prompts "
            f"--out {DEFAULT_AUDITION_PATH}"
        ),
        "approve": (
            "uv run python scripts/audition_learn_exemplars.py "
            "--approve-ear-pass --approved-by <name> "
            f"--audition {DEFAULT_AUDITION_PATH} --approval-out {approval_path}"
        ),
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }


def list_output_devices() -> list[dict[str, Any]]:
    """Return sounddevice output devices as JSON-safe rows."""
    sd = importlib.import_module("sounddevice")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    try:
        default_output = int(sd.default.device[1])
    except (AttributeError, IndexError, TypeError, ValueError):
        default_output = None

    rows: list[dict[str, Any]] = []
    for index, device in enumerate(devices):
        max_output_channels = int(device.get("max_output_channels", 0))
        if max_output_channels <= 0:
            continue
        hostapi_name = ""
        try:
            hostapi = hostapis[int(device.get("hostapi", -1))]
            hostapi_name = str(hostapi.get("name", ""))
        except (IndexError, TypeError, ValueError):
            hostapi_name = ""
        rows.append(
            {
                "index": index,
                "name": str(device.get("name", "")),
                "hostapi": hostapi_name,
                "max_output_channels": max_output_channels,
                "default_sample_rate": int(float(device.get("default_samplerate", 0))),
                "is_default_output": index == default_output,
            }
        )
    return rows


def _output_device_score(row: dict[str, Any]) -> int:
    name = str(row.get("name") or "").strip().lower()
    if not name:
        return -100
    score = 0
    if any(token in name for token in VIRTUAL_OUTPUT_TOKENS):
        score -= 100
    if any(token in name for token in PRIMARY_AUDIBLE_OUTPUT_TOKENS):
        score += 100
    if any(token in name for token in DJ_AUDIBLE_OUTPUT_TOKENS):
        score += 70
    if row.get("is_default_output") is True:
        score += 4
    channels = int(row.get("max_output_channels") or 0)
    if channels >= 2:
        score += 2
    return score


def recommended_output_devices(rows: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    """Prefer audible outputs for a human ear-pass; avoid loopback/capture sinks."""
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        score = _output_device_score(row)
        if score <= 0:
            continue
        try:
            index = int(row.get("index"))
        except (TypeError, ValueError):
            index = 9999
        copy = dict(row)
        copy["recommendation_score"] = score
        copy["recommendation_reason"] = "audible_output_for_human_ear_pass"
        scored.append((score, -index, copy))
    scored.sort(reverse=True)
    return [row for _, _, row in scored[:limit]]


def ear_pass_operator_action(output_devices: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    recommended = recommended_output_devices(output_devices or [])
    if recommended:
        device = recommended[0]
        device_index = int(device["index"])
        device_name = str(device["name"])
        play_command = (
            "uv run python scripts/audition_learn_exemplars.py --play "
            f"--device-index {device_index} --say-prompts --out {DEFAULT_AUDITION_PATH}"
        )
        prompt = (
            f"Listen to the four EQ exemplar loops on {device_name}, then "
            "approve them or replace the bank."
        )
    else:
        play_command = operator_commands()["play"]
        prompt = "Choose an audible output, listen to the four EQ exemplar loops, then approve or replace them."
    return {
        "prompt": prompt,
        "recommended_output_devices": recommended,
        "steps": [
            operator_commands()["list_output_devices"],
            play_command,
            operator_commands()["approve"],
            operator_commands()["verify"],
        ],
    }


def _say_prompt(text: str, *, enabled: bool) -> bool:
    """Speak an operator prompt on macOS. Best-effort and quiet by default."""
    if not enabled or sys.platform != "darwin":
        return False
    try:
        subprocess.run(
            ["say", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return True


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(float(value), 1e-12))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(bank_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    bank = bank_dir or _packaged_bank_dir()
    manifest_path = bank / "MANIFEST.json"
    return bank, json.loads(manifest_path.read_text())


def audit_track(bank: Path, rel: str, meta: dict[str, Any]) -> dict[str, Any]:
    path = bank / rel
    samples, sr = load_audio_stereo(path)
    abs_samples = np.abs(samples)
    peak = float(np.max(abs_samples)) if samples.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
    duration_s = float(samples.shape[0] / sr) if sr else 0.0
    clipped_samples = int(np.count_nonzero(abs_samples >= 0.999))
    digest = _sha256(path)
    band = rel.split("/", 1)[0]
    channels = int(samples.shape[1]) if samples.ndim == 2 else 1
    sample_rate_matches = int(sr) == int(meta.get("sample_rate_hz", 0))
    hash_matches = digest == meta.get("sha256")
    clip_free = clipped_samples == 0
    non_silent = rms > RMS_FLOOR
    duration_valid = duration_s > 0
    stereo = channels == 2
    integrity_passed = (
        hash_matches
        and stereo
        and sample_rate_matches
        and duration_valid
        and clip_free
        and non_silent
    )
    return {
        "band": band,
        "rel": rel,
        "title": str(meta.get("title", "")),
        "artist": str(meta.get("artist", "")),
        "license": str(meta.get("license", "")),
        "sample_rate_hz": int(sr),
        "manifest_sample_rate_hz": int(meta.get("sample_rate_hz", 0)),
        "sample_rate_matches": sample_rate_matches,
        "duration_s": round(duration_s, 3),
        "duration_valid": duration_valid,
        "channels": channels,
        "stereo": stereo,
        "peak": round(peak, 6),
        "peak_dbfs": round(_dbfs(peak), 2),
        "rms": round(rms, 6),
        "rms_dbfs": round(_dbfs(rms), 2),
        "clipped_samples": clipped_samples,
        "clip_free": clip_free,
        "non_silent": non_silent,
        "sha256": digest,
        "manifest_sha256": str(meta.get("sha256", "")),
        "hash_matches": hash_matches,
        "integrity_passed": integrity_passed,
        "technical_passed": integrity_passed,
        "needs_human_ear_pass": True,
    }


def _technical_failures(rows: list[dict[str, Any]], missing_bands: list[str]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = [
        {"scope": "bank", "reason": "missing_band", "band": band} for band in missing_bands
    ]
    checks = (
        ("hash_matches", "sha256_mismatch"),
        ("stereo", "not_stereo"),
        ("sample_rate_matches", "sample_rate_mismatch"),
        ("duration_valid", "invalid_duration"),
        ("clip_free", "clipped_samples"),
        ("non_silent", "silent_or_too_quiet"),
    )
    for row in rows:
        for field, reason in checks:
            if row.get(field) is not True:
                failures.append(
                    {
                        "scope": "track",
                        "reason": reason,
                        "band": row.get("band"),
                        "rel": row.get("rel"),
                    }
                )
    return failures


def _approval_track_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "band": row.get("band"),
            "rel": row.get("rel"),
            "title": row.get("title"),
            "sha256": row.get("sha256"),
        }
        for row in summary.get("tracks", [])
        if isinstance(row, dict)
    ]


def _bank_fingerprint(bank: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a stable fingerprint for the exact packaged exemplar bank."""
    manifest_sha256 = _sha256(bank / "MANIFEST.json")
    track_rows = [
        {
            "artist": row.get("artist"),
            "band": row.get("band"),
            "license": row.get("license"),
            "rel": row.get("rel"),
            "sample_rate_hz": row.get("sample_rate_hz"),
            "sha256": row.get("sha256"),
            "title": row.get("title"),
        }
        for row in sorted(rows, key=lambda item: str(item.get("rel") or ""))
    ]
    payload = {
        "expected_bands": list(EXPECTED_BANDS),
        "manifest_sha256": manifest_sha256,
        "tracks": track_rows,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "algorithm": "sha256-canonical-json-v1",
        "digest": digest,
        "manifest_sha256": manifest_sha256,
        "track_count": len(track_rows),
    }


def write_ear_pass_approval(
    summary: dict[str, Any],
    out_path: Path,
    *,
    approved_by: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Write explicit human approval for the exact current exemplar hashes."""
    if summary.get("technical_passed") is not True or summary.get("passed") is not True:
        raise ValueError("cannot approve exemplars until the technical audit passes")
    approved_by = approved_by.strip()
    if not approved_by:
        raise ValueError("--approved-by is required for ear-pass approval")
    approval = {
        "schema_version": 1,
        "proof": "learn_exemplar_ear_pass",
        "approved": True,
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).isoformat(),
        "notes": notes or "",
        "bank_dir": summary.get("bank_dir"),
        "bank_fingerprint": summary.get("bank_fingerprint"),
        "tracks": _approval_track_rows(summary),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return approval


def validate_ear_pass_approval(
    summary: dict[str, Any],
    approval: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate an approval artifact against the current technical audit rows."""
    errors: list[str] = []
    if approval is None:
        errors.append("approval artifact is missing")
    else:
        if approval.get("schema_version") != 1:
            errors.append("approval schema_version is not 1")
        if approval.get("proof") != "learn_exemplar_ear_pass":
            errors.append("approval proof is not learn_exemplar_ear_pass")
        if approval.get("approved") is not True:
            errors.append("approval approved flag is not true")
        if not str(approval.get("approved_by") or "").strip():
            errors.append("approval approved_by is missing")
        current_fingerprint = summary.get("bank_fingerprint")
        approved_fingerprint = approval.get("bank_fingerprint")
        if not isinstance(current_fingerprint, dict):
            errors.append("current bank_fingerprint is missing")
        elif not isinstance(approved_fingerprint, dict):
            errors.append("approval bank_fingerprint is missing")
        else:
            if approved_fingerprint.get("algorithm") != current_fingerprint.get("algorithm"):
                errors.append("approval bank_fingerprint algorithm mismatch")
            if approved_fingerprint.get("digest") != current_fingerprint.get("digest"):
                errors.append("approval bank fingerprint mismatch")
            if approved_fingerprint.get("manifest_sha256") != current_fingerprint.get(
                "manifest_sha256"
            ):
                errors.append("approval manifest hash mismatch")
        approval_rows = approval.get("tracks")
        if not isinstance(approval_rows, list):
            errors.append("approval tracks must be a list")
            approval_rows = []
        current_by_rel = {
            str(row.get("rel")): row
            for row in summary.get("tracks", [])
            if isinstance(row, dict) and row.get("rel")
        }
        approval_by_rel = {
            str(row.get("rel")): row
            for row in approval_rows
            if isinstance(row, dict) and row.get("rel")
        }
        if set(approval_by_rel) != set(current_by_rel):
            errors.append("approval track set does not match current exemplar bank")
        for rel, current in current_by_rel.items():
            approved = approval_by_rel.get(rel)
            if not isinstance(approved, dict):
                continue
            if approved.get("sha256") != current.get("sha256"):
                errors.append(f"approval hash mismatch for {rel}")
    return {
        "approved": not errors,
        "errors": errors,
        "artifact": approval,
    }


def _load_approval(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, json.JSONDecodeError) as exc:
        return None, repr(exc)
    if not isinstance(raw, dict):
        return None, "approval root is not an object"
    return raw, None


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, json.JSONDecodeError) as exc:
        return None, repr(exc)
    if not isinstance(raw, dict):
        return None, "artifact root is not an object"
    return raw, None


def validate_audition_artifact(
    summary: dict[str, Any],
    audition: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate that the current bank was actually played before approval."""
    errors: list[str] = []
    if audition is None:
        errors.append("audition artifact is missing")
    else:
        if audition.get("schema_version") != 2:
            errors.append("audition schema_version is not 2")
        if audition.get("technical_passed") is not True:
            errors.append("audition technical_passed is not true")
        if audition.get("human_ear_pass") != "auditioned_by_user":
            errors.append("audition did not record playback")
        current_fingerprint = summary.get("bank_fingerprint")
        audition_fingerprint = audition.get("bank_fingerprint")
        if not isinstance(current_fingerprint, dict):
            errors.append("current bank_fingerprint is missing")
        elif not isinstance(audition_fingerprint, dict):
            errors.append("audition bank_fingerprint is missing")
        else:
            if audition_fingerprint.get("algorithm") != current_fingerprint.get("algorithm"):
                errors.append("audition bank_fingerprint algorithm mismatch")
            if audition_fingerprint.get("digest") != current_fingerprint.get("digest"):
                errors.append("audition bank fingerprint mismatch")
            if audition_fingerprint.get("manifest_sha256") != current_fingerprint.get(
                "manifest_sha256"
            ):
                errors.append("audition manifest hash mismatch")
        playback = audition.get("playback")
        if not isinstance(playback, dict):
            errors.append("audition playback metadata is missing")
        else:
            expected_tracks = len(summary.get("tracks", [])) if isinstance(summary.get("tracks"), list) else 0
            if int(playback.get("played_count") or 0) != expected_tracks:
                errors.append("audition played_count does not match current bank")
            if playback.get("device_index") is None:
                errors.append("audition device_index is missing")
    return {
        "played": not errors,
        "errors": errors,
        "artifact": audition,
    }


def audit_packaged_bank(
    bank_dir: Path | None = None,
    *,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    bank, manifest = _load_manifest(bank_dir)
    tracks = manifest.get("tracks", {})
    rows = [
        audit_track(bank, rel, meta)
        for rel, meta in sorted(tracks.items())
        if isinstance(meta, dict)
    ]
    present_bands = {row["band"] for row in rows}
    missing_bands = [band for band in EXPECTED_BANDS if band not in present_bands]
    bank_fingerprint = _bank_fingerprint(bank, rows)
    technical_failures = _technical_failures(rows, missing_bands)
    technical_passed = (
        bool(rows)
        and not missing_bands
        and all(row["technical_passed"] for row in rows)
    )
    approval_status: dict[str, Any] | None = None
    approval_error: str | None = None
    if approval_path is not None:
        approval, approval_error = _load_approval(approval_path)
        partial_summary = {
            "technical_passed": technical_passed,
            "bank_dir": str(bank),
            "bank_fingerprint": bank_fingerprint,
            "tracks": rows,
        }
        approval_status = validate_ear_pass_approval(partial_summary, approval)
        approval_status["path"] = str(approval_path)
        if approval_error and approval_error != "missing":
            approval_status["errors"].append(approval_error)

    approval_valid = (
        approval_status is not None
        and approval_status.get("approved") is True
        and technical_passed
    )
    if not technical_passed:
        diagnosis_code = "technical_audit_failed"
        diagnosis_severity = "failed"
        diagnosis_message = "Packaged exemplar WAV integrity failed; replace or regenerate the bank."
        next_action = "replace or regenerate the packaged exemplar bank"
    elif approval_valid:
        diagnosis_code = "technical_and_ear_pass_approved"
        diagnosis_severity = "approved"
        diagnosis_message = "Packaged exemplar WAV integrity and human ear-pass are approved."
        next_action = "keep approval artifact with release evidence"
    else:
        diagnosis_code = "technical_audit_passed_ear_pass_pending"
        diagnosis_severity = "needs_ear_pass"
        diagnosis_message = "Packaged exemplar WAV integrity passed; human ear-pass is still required."
        next_action = (
            "list output devices, play the four loops through the Learn player, "
            "then write explicit approval or replace the bank"
        )

    return {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": technical_passed,
        "technical_passed": technical_passed,
        "bank_dir": str(bank),
        "bank_fingerprint": bank_fingerprint,
        "expected_bands": list(EXPECTED_BANDS),
        "missing_bands": missing_bands,
        "technical_failures": technical_failures,
        "tracks": rows,
        "human_ear_pass": approval_status,
        "human_ear_pass_required": not approval_valid,
        "release_ready": approval_valid,
        "diagnosis": {
            "code": diagnosis_code,
            "severity": diagnosis_severity,
            "message": diagnosis_message,
            "next_action": next_action,
        },
        "next_action": next_action,
        "operator_commands": operator_commands(),
        "operator_action": ear_pass_operator_action(),
    }


def play_tracks(
    rows: list[dict[str, Any]],
    *,
    device_index: int,
    gap_s: float,
    say_prompts: bool = False,
) -> dict[str, Any]:
    audio_cue_mod = importlib.import_module("vibemix.learn.audio_cue")
    music_state_mod = importlib.import_module("vibemix.state.music_state")
    player = audio_cue_mod.ExemplarPlayer(
        device_index=device_index,
        state=music_state_mod.MusicState(),
    )
    spoken_prompt_count = 0
    try:
        for row in rows:
            path = Path(row["abs_path"])
            band = str(row["band"])
            print(
                f"playing {band} exemplar: {row['title']} ({path.name})",
                file=sys.stderr,
                flush=True,
            )
            if _say_prompt(f"{band} EQ exemplar.", enabled=say_prompts):
                spoken_prompt_count += 1
            player.play(str(path))
            time.sleep(float(row["duration_s"]) + max(0.0, gap_s))
            player.stop()
    finally:
        player.stop()
    return {
        "device_index": device_index,
        "say_prompts": bool(say_prompts),
        "spoken_prompt_count": spoken_prompt_count,
        "played_count": len(rows),
    }


def _rows_with_paths(summary: dict[str, Any]) -> list[dict[str, Any]]:
    bank = Path(summary["bank_dir"])
    rows = []
    for row in summary["tracks"]:
        copy = dict(row)
        copy["abs_path"] = str(bank / str(row["rel"]))
        rows.append(copy)
    return rows


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audition_learn_exemplars",
        description="Audit and optionally play the packaged Learn EQ exemplar bank.",
    )
    parser.add_argument("--play", action="store_true", help="Play each exemplar after auditing.")
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Attach available sounddevice output devices to the JSON summary.",
    )
    parser.add_argument(
        "--approval",
        type=Path,
        default=None,
        help="Validate an existing human ear-pass approval artifact.",
    )
    parser.add_argument(
        "--approve-ear-pass",
        action="store_true",
        help=(
            "After listening, write explicit human approval for the exact current "
            "exemplar hashes."
        ),
    )
    parser.add_argument(
        "--approved-by",
        default=None,
        help="Required with --approve-ear-pass.",
    )
    parser.add_argument(
        "--approval-out",
        type=Path,
        default=DEFAULT_APPROVAL_PATH,
        help=f"Approval artifact path (default: {DEFAULT_APPROVAL_PATH}).",
    )
    parser.add_argument(
        "--audition",
        type=Path,
        default=DEFAULT_AUDITION_PATH,
        help=(
            "Audition artifact required by --approve-ear-pass "
            f"(default: {DEFAULT_AUDITION_PATH})."
        ),
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the JSON summary to this path.")
    parser.add_argument(
        "--device-index",
        type=int,
        default=None,
        help="sounddevice output index for --play.",
    )
    parser.add_argument("--gap-s", type=float, default=0.5, help="Gap between played exemplars.")
    parser.add_argument(
        "--say-prompts",
        action="store_true",
        help="On macOS, speak a short band label before each played exemplar.",
    )
    return parser


def write_audit_summary(summary: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


write_summary = write_audit_summary


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = audit_packaged_bank(approval_path=args.approval)
    if args.list_devices:
        try:
            summary["output_devices"] = list_output_devices()
            summary["operator_action"] = ear_pass_operator_action(summary["output_devices"])
        except Exception as exc:
            summary["output_devices"] = []
            summary["output_device_error"] = repr(exc)
            summary["operator_action"] = ear_pass_operator_action([])
    if args.play:
        if args.device_index is None:
            summary["passed"] = False
            summary["error"] = "--play requires --device-index"
            if "output_devices" not in summary:
                try:
                    summary["output_devices"] = list_output_devices()
                except Exception as exc:
                    summary["output_devices"] = []
                    summary["output_device_error"] = repr(exc)
            summary["operator_action"] = ear_pass_operator_action(summary["output_devices"])
            summary["next_action"] = (
                "choose an output_devices[].index, then rerun --play "
                "--device-index <output-device-index>"
            )
        else:
            summary["playback"] = play_tracks(
                _rows_with_paths(summary),
                device_index=args.device_index,
                gap_s=args.gap_s,
                say_prompts=args.say_prompts,
            )
            summary["human_ear_pass"] = "auditioned_by_user"
            summary["diagnosis"] = {
                "code": "auditioned_manual_approval_needed",
                "severity": "needs_approval",
                "message": (
                    "Packaged exemplar WAVs were played through the Learn player; "
                    "record explicit human approval before marking release-ready."
                ),
                "next_action": "approve each loop in the release checklist or replace the bank",
            }
            summary["next_action"] = (
                "approve each loop in the release checklist or replace the bank"
            )
    if args.approve_ear_pass:
        try:
            audition, audition_error = _load_json_object(args.audition)
            audition_status = validate_audition_artifact(summary, audition)
            audition_status["path"] = str(args.audition)
            if audition_error and audition_error != "missing":
                audition_status["errors"].append(audition_error)
                audition_status["played"] = False
            summary["audition"] = audition_status
            if audition_status["played"] is not True:
                raise ValueError(
                    "valid audition artifact is required before approval: "
                    + "; ".join(audition_status["errors"])
                )
            approval = write_ear_pass_approval(
                summary,
                args.approval_out,
                approved_by=str(args.approved_by or ""),
                notes=None,
            )
            summary["human_ear_pass"] = validate_ear_pass_approval(summary, approval)
            summary["human_ear_pass"]["path"] = str(args.approval_out)
            summary["human_ear_pass_required"] = False
            summary["release_ready"] = True
            summary["diagnosis"] = {
                "code": "technical_and_ear_pass_approved",
                "severity": "approved",
                "message": (
                    "Packaged exemplar WAV integrity and human ear-pass are approved."
                ),
                "next_action": "keep approval artifact with release evidence",
            }
            summary["next_action"] = "keep approval artifact with release evidence"
        except ValueError as exc:
            summary["passed"] = False
            summary["error"] = str(exc)
    if args.out is not None:
        write_audit_summary(summary, args.out)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("passed") is True else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
