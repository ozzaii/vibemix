# SPDX-License-Identifier: Apache-2.0
"""``library export-guard`` — read-only "will this USB show up on this rig?".

The 2026-06-11 hand-of-god pack's #2 breakthrough: booth panic is binary —
either the stick shows up on tonight's hardware or it doesn't — and the open
lane is predicting that BEFORE the gig, read-only, with receipts. This module
walks a mounted USB stick, inventories the library formats it carries, and
audits the inventory against a target rig profile, ending in exactly one of
take_it / fix_first / do_not_take.

Contract (the pack's red lines, kept):
* READ-ONLY. Never writes to the stick, a cache, or a library.
* Deterministic — pure checks over the directory tree; no model calls,
  no network, no audio decode.
* Honest absence: what cannot be detected (filesystem, m4a codec) is
  reported as unknown/ambiguous, never guessed into a verdict.

Every hardware fact in ``RIG_PROFILES`` was verified against official
AlphaTheta notices/manuals/FAQs in the 2026-06-12 research pass
(workflow wf_c61ce5aa-807; 23/24 claims survived adversarial verification).
Key sources:
* alphatheta.com "important notice for customers using USB devices" — the
  OneLibrary vs Device Library split table; rekordbox 7.2.11+ writes both.
* Official instruction manuals: CDJ-3000 DRI1586A, CDJ-2000NXS2 DRI1290A,
  CDJ-2000NXS DRI1052, XDJ-XZ DRI1625B, XDJ-RX3 DRI1702C, OPUS-QUAD DRI1795B.
* djl-analysis.deepsymmetry.org — export.pdb / USBANLZ on-disk layout.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "vibemix.export-guard.v1"

# Share of unplayable audio files that flips fix_first into do_not_take.
# Mirrors gig_check's conservative ladder: a green verdict must be safe to
# trust at 1:40 a.m.
DO_NOT_TAKE_BLOCKED_RATIO = 0.30

# Format tokens by audio file extension. Video containers (mp4/m4v/avi/mov)
# are deliberately absent: rekordbox refuses to export them and no player
# treats them as tracks — counting them would fabricate phantom audio.
_AUDIO_EXT = {
    ".mp3": "mp3",
    ".aac": "aac",
    ".m4a": "m4a",
    ".wav": "wav",
    ".aiff": "aiff",
    ".aif": "aiff",
    ".flac": "flac",
    ".alac": "alac",
    ".ogg": "ogg",
    ".oga": "ogg",
}

_DEVICE_LIBRARY_PDB = Path("PIONEER") / "rekordbox" / "export.pdb"
_ONELIBRARY_DB = Path("PIONEER") / "rekordbox" / "exportLibrary.db"
_USBANLZ_DIR = Path("PIONEER") / "USBANLZ"
_ENGINE_DB_CANDIDATES = (
    Path("Engine Library") / "Database2" / "m.db",  # Engine DJ 2.x layout
    Path("Engine Library") / "m.db",  # legacy Engine Library 1.x
)
_SERATO_DIR = Path("_Serato_")


@dataclass(frozen=True, slots=True)
class RigProfile:
    """One target rig's verified capabilities.

    ``formats`` / ``filesystems`` of ``None`` mean "not audited for this
    rig" (no verified fact base) — the audit skips rather than invents.
    ``warn_*`` sets are capabilities that exist but cannot be trusted
    blind (firmware-added, or community-documented as patchy).
    """

    rig_id: str
    label: str
    family: str  # "pioneer" | "engine" | "serato"
    reads_onelibrary: bool = False
    reads_device_library: bool = False
    formats: frozenset[str] | None = None
    warn_formats: frozenset[str] = frozenset()
    filesystems: frozenset[str] | None = None
    warn_filesystems: frozenset[str] = frozenset()
    notes: tuple[str, ...] = ()


_FAT_HFS = frozenset({"fat16", "fat32", "hfsplus"})
_FAT_HFS_EXFAT = frozenset({"fat16", "fat32", "exfat", "hfsplus"})
_SIX_FORMATS = frozenset({"mp3", "aac", "wav", "aiff", "flac", "alac"})
_FIVE_NO_ALAC = frozenset({"mp3", "aac", "wav", "aiff", "flac"})

RIG_PROFILES: dict[str, RigProfile] = {
    "cdj-3000x": RigProfile(
        rig_id="cdj-3000x",
        label="CDJ-3000X",
        family="pioneer",
        reads_onelibrary=True,
        formats=_SIX_FORMATS,
        filesystems=_FAT_HFS_EXFAT,
        notes=(
            "reads OneLibrary only — export with rekordbox 7.2.11+ "
            "(writes both formats)",
        ),
    ),
    "opus-quad": RigProfile(
        rig_id="opus-quad",
        label="OPUS-QUAD",
        family="pioneer",
        reads_onelibrary=True,
        formats=_SIX_FORMATS,
        filesystems=_FAT_HFS_EXFAT,
        notes=("reads OneLibrary (Device Library Plus) only",),
    ),
    "cdj-3000": RigProfile(
        rig_id="cdj-3000",
        label="CDJ-3000",
        family="pioneer",
        reads_device_library=True,
        formats=_SIX_FORMATS,
        filesystems=_FAT_HFS,
        # Launch manual lists FAT16/FAT32/HFS+ only; the current FAQ adds
        # exFAT — firmware-added, so old club units may reject the stick.
        warn_filesystems=frozenset({"exfat"}),
        notes=("fw 3.30 OneLibrary support was withdrawn — Device Library rig",),
    ),
    "cdj-2000nxs2": RigProfile(
        rig_id="cdj-2000nxs2",
        label="CDJ-2000NXS2",
        family="pioneer",
        reads_device_library=True,
        formats=_SIX_FORMATS,
        filesystems=_FAT_HFS,  # manual: FAT16/FAT32/HFS+ — no exFAT, ever
    ),
    "cdj-2000nxs": RigProfile(
        rig_id="cdj-2000nxs",
        label="CDJ-2000NXS (pre-NXS2 generation)",
        family="pioneer",
        reads_device_library=True,
        formats=frozenset({"mp3", "aac", "wav", "aiff"}),
        # Officially listed, but the fleet is community-documented as patchy
        # on everything except MP3 (mid-set load errors on firmware combos).
        warn_formats=frozenset({"aac", "wav", "aiff"}),
        filesystems=_FAT_HFS,
        notes=("only MP3 plays universally across the pre-NXS2 fleet",),
    ),
    "xdj-xz": RigProfile(
        rig_id="xdj-xz",
        label="XDJ-XZ",
        family="pioneer",
        reads_device_library=True,
        formats=_FIVE_NO_ALAC,  # manual lists no ALAC
        filesystems=_FAT_HFS,
        # Original manual: "NTFS and exFAT aren't supported"; current FAQ
        # allows exFAT — firmware-added.
        warn_filesystems=frozenset({"exfat"}),
    ),
    "xdj-rx3": RigProfile(
        rig_id="xdj-rx3",
        label="XDJ-RX3",
        family="pioneer",
        reads_device_library=True,
        formats=_FIVE_NO_ALAC,
        filesystems=_FAT_HFS_EXFAT,  # exFAT native per manual + FAQ
    ),
    "engine-os": RigProfile(
        rig_id="engine-os",
        label="Engine OS hardware (SC5000/SC6000/PRIME 4)",
        family="engine",
        reads_device_library=True,  # Denon: reads rekordbox drives directly
        # Format/filesystem matrices not yet verified against official
        # Denon specs — skipped rather than guessed.
    ),
    "serato-laptop": RigProfile(
        rig_id="serato-laptop",
        label="Serato laptop",
        family="serato",
        formats=frozenset({"mp3", "ogg", "aac", "m4a", "alac", "flac", "aiff", "wav"}),
        # The laptop mounts whatever the OS mounts; no player-side fs rule.
    ),
}


@dataclass(frozen=True, slots=True)
class StickInventory:
    """What a read-only walk of the stick actually found."""

    root: str
    has_device_library: bool
    has_onelibrary: bool
    has_usbanlz: bool
    has_engine_library: bool
    has_serato: bool
    audio_by_format: dict[str, int]
    filesystem: str | None


_FS_ALIASES = {
    "hfs+": "hfsplus",
    "hfs": "hfsplus",
    "mac os extended": "hfsplus",
    "ms-dos fat32": "fat32",
    "ms-dos fat16": "fat16",
    "msdos": "fat32",
    "fat": "fat32",
}


def _normalize_fs(value: str | None) -> str | None:
    if value is None:
        return None
    token = value.strip().lower()
    return _FS_ALIASES.get(token, token)


def _detect_filesystem(root: Path) -> str | None:
    """Best-effort mount filesystem lookup. None = unknown, never a guess."""
    if sys.platform != "darwin":
        return None
    import plistlib
    import subprocess

    try:
        out = subprocess.run(
            ["/usr/sbin/diskutil", "info", "-plist", str(root)],
            capture_output=True,
            timeout=5,
            check=True,
        ).stdout
        info = plistlib.loads(out)
    except Exception:
        return None
    fs_type = str(info.get("FilesystemType", "")).lower()
    fs_name = str(info.get("FilesystemName", "")).lower()
    if fs_type == "msdos":
        return "fat16" if "fat16" in fs_name else "fat32"
    if fs_type in ("exfat", "apfs", "ntfs"):
        return fs_type
    if fs_type == "hfs":
        return "hfsplus"
    return _normalize_fs(fs_name) or None


def scan_stick(root: Path | str, *, filesystem: str | None = None) -> StickInventory:
    """Inventory a mounted stick read-only.

    ``filesystem`` overrides detection (tests, or the operator knows). Hidden
    entries and AppleDouble ``._`` forks are skipped — counting macOS litter
    would fabricate phantom tracks.
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(root)

    anlz_dir = root / _USBANLZ_DIR
    audio: dict[str, int] = {}
    for path in root.rglob("*"):
        rel_parts = path.relative_to(root).parts
        if any(part.startswith(".") or part.startswith("._") for part in rel_parts):
            continue
        fmt = _AUDIO_EXT.get(path.suffix.lower())
        if fmt and path.is_file():
            audio[fmt] = audio.get(fmt, 0) + 1

    return StickInventory(
        root=str(root),
        has_device_library=(root / _DEVICE_LIBRARY_PDB).is_file(),
        has_onelibrary=(root / _ONELIBRARY_DB).is_file(),
        has_usbanlz=anlz_dir.is_dir() and any(anlz_dir.rglob("ANLZ*")),
        has_engine_library=any(
            (root / cand).is_file() for cand in _ENGINE_DB_CANDIDATES
        ),
        has_serato=(root / _SERATO_DIR).is_dir(),
        audio_by_format=audio,
        filesystem=_normalize_fs(filesystem) or _detect_filesystem(root),
    )


def _audit_filesystem(inv: StickInventory, rig: RigProfile) -> dict[str, Any]:
    if rig.filesystems is None:
        return {"detected": inv.filesystem, "status": "not_audited"}
    if inv.filesystem is None:
        return {"detected": None, "status": "unknown"}
    if inv.filesystem in rig.filesystems:
        return {"detected": inv.filesystem, "status": "ok"}
    if inv.filesystem in rig.warn_filesystems:
        return {"detected": inv.filesystem, "status": "warn"}
    return {"detected": inv.filesystem, "status": "unsupported"}


def _audit_library(
    inv: StickInventory, rig: RigProfile, blockers: list[str], warnings: list[str]
) -> bool | None:
    """Append library-visibility receipts; return readable-on-rig (None = n/a)."""
    has_rekordbox = inv.has_device_library or inv.has_onelibrary
    total_audio = sum(inv.audio_by_format.values())

    if rig.family == "serato":
        if not inv.has_serato and total_audio:
            warnings.append(
                "no _Serato_ folder on this stick — audio only, crates and "
                "prep will not follow the drive"
            )
            return False
        return inv.has_serato or None

    if rig.family == "engine":
        if inv.has_engine_library or inv.has_device_library:
            return True
        if inv.has_onelibrary:
            warnings.append(
                "stick carries only OneLibrary — Engine OS support for "
                "OneLibrary-only sticks is unverified"
            )
            return False
        if total_audio:
            warnings.append(
                "no Engine or rekordbox library on this stick — raw file "
                "browse only, no playlists or prepared cues"
            )
        return False if total_audio else None

    # Pioneer family: the AlphaTheta dual-format trap.
    if has_rekordbox:
        readable = (rig.reads_onelibrary and inv.has_onelibrary) or (
            rig.reads_device_library and inv.has_device_library
        )
        if not readable:
            if rig.reads_onelibrary:
                blockers.append(
                    f"stick carries only the classic Device Library — "
                    f"{rig.label} reads OneLibrary; playlists and tracks "
                    f"will not show (re-export with rekordbox 7.2.11+)"
                )
            else:
                blockers.append(
                    f"stick carries only OneLibrary — {rig.label} reads the "
                    f"classic Device Library; playlists and tracks will not show"
                )
        elif inv.has_device_library and not inv.has_usbanlz:
            warnings.append(
                "PIONEER/USBANLZ analysis files are missing — waveforms and "
                "beatgrids will not display on the player"
            )
        if inv.has_engine_library:
            warnings.append(
                f"Engine Library present but {rig.label} cannot read Engine "
                f"libraries — that prep is invisible here"
            )
        return readable

    if total_audio:
        warnings.append(
            f"no rekordbox export on this stick — {rig.label} will browse "
            f"raw files: no playlists, no prepared cues, no waveforms"
        )
    return None


def _audit_audio(
    inv: StickInventory, rig: RigProfile, warnings: list[str]
) -> tuple[dict[str, Any], int]:
    """Per-format playability; returns (audio section, blocked file count)."""
    total = sum(inv.audio_by_format.values())
    if rig.formats is None:
        return (
            {
                "total": total,
                "by_format": dict(sorted(inv.audio_by_format.items())),
                "blocked": [],
                "warned": [],
                "status": "not_audited",
            },
            0,
        )

    blocked: list[dict[str, Any]] = []
    warned: list[dict[str, Any]] = []
    for fmt, count in sorted(inv.audio_by_format.items()):
        if fmt == "m4a" and "m4a" not in rig.formats:
            # An .m4a container holds AAC or ALAC; without decoding we
            # cannot know which, so the verdict must not pretend to.
            if "aac" in rig.formats and "alac" in rig.formats:
                continue
            if "aac" in rig.formats:
                reason = (
                    f"m4a may be ALAC, which {rig.label} does not list — "
                    f"verify or transcode before the gig"
                )
                warned.append({"format": fmt, "count": count, "reason": reason})
                warnings.append(f"{count} m4a file(s): {reason}")
            else:
                blocked.append(
                    {
                        "format": fmt,
                        "count": count,
                        "reason": f"{rig.label} plays neither AAC nor ALAC",
                    }
                )
            continue
        if fmt not in rig.formats:
            blocked.append(
                {
                    "format": fmt,
                    "count": count,
                    "reason": f"{fmt} is not in {rig.label}'s supported formats",
                }
            )
        elif fmt in rig.warn_formats:
            reason = f"{fmt} support is patchy on {rig.label} — MP3 is the safe bet"
            warned.append({"format": fmt, "count": count, "reason": reason})
            warnings.append(f"{count} {fmt} file(s): {reason}")

    blocked_n = sum(b["count"] for b in blocked)
    return (
        {
            "total": total,
            "by_format": dict(sorted(inv.audio_by_format.items())),
            "blocked": blocked,
            "warned": warned,
            "status": "ok",
        },
        blocked_n,
    )


def audit_stick(inv: StickInventory, rig: RigProfile) -> dict[str, Any]:
    """Audit one stick inventory against one rig profile. Pure and read-only."""
    blockers: list[str] = []
    warnings: list[str] = []
    total_audio = sum(inv.audio_by_format.values())
    has_any_library = (
        inv.has_device_library
        or inv.has_onelibrary
        or inv.has_engine_library
        or inv.has_serato
    )

    if total_audio == 0 and not has_any_library:
        blockers.append("stick is empty — no audio files and no library database")
    elif total_audio == 0:
        blockers.append(
            "library database present but no audio files found — tracks will "
            "not load"
        )

    fs_section = _audit_filesystem(inv, rig)
    if fs_section["status"] == "unsupported":
        blockers.append(
            f"filesystem {fs_section['detected']} is not supported by "
            f"{rig.label} — the stick will not mount"
        )
    elif fs_section["status"] == "warn":
        warnings.append(
            f"filesystem {fs_section['detected']} support on {rig.label} is "
            f"firmware-added — old units may reject this stick (FAT32 is the "
            f"safe bet)"
        )

    readable = _audit_library(inv, rig, blockers, warnings)
    audio_section, blocked_files = _audit_audio(inv, rig, warnings)

    blocked_ratio = blocked_files / total_audio if total_audio else 0.0
    if blocked_ratio > DO_NOT_TAKE_BLOCKED_RATIO:
        fmts = ", ".join(
            f"{b['format']} ×{b['count']}" for b in audio_section["blocked"]
        )
        blockers.append(
            f"{blocked_files} of {total_audio} audio file(s) cannot play on "
            f"{rig.label} ({fmts})"
        )
    elif blocked_files:
        fmts = ", ".join(
            f"{b['format']} ×{b['count']}" for b in audio_section["blocked"]
        )
        warnings.append(
            f"{blocked_files} audio file(s) will not play on {rig.label} ({fmts})"
        )

    if blockers:
        verdict = "do_not_take"
    elif warnings or blocked_files:
        verdict = "fix_first"
    else:
        verdict = "take_it"

    return {
        "schema": SCHEMA,
        "rig": rig.rig_id,
        "rig_label": rig.label,
        "verdict": verdict,
        "blockers": blockers,
        "warnings": warnings,
        "library": {
            "device_library": inv.has_device_library,
            "onelibrary": inv.has_onelibrary,
            "usbanlz": inv.has_usbanlz,
            "engine": inv.has_engine_library,
            "serato": inv.has_serato,
            "readable_on_rig": readable,
        },
        "filesystem": fs_section,
        "audio": audio_section,
        "rig_notes": list(rig.notes),
        "stick": inv.root,
    }


def run_export_guard(
    root: Path | str, rig_id: str, *, filesystem: str | None = None
) -> dict[str, Any]:
    """Scan + audit in one call. KeyError on an unknown rig id (caller maps
    it to the available-rig list); FileNotFoundError on a missing mount."""
    rig = RIG_PROFILES[rig_id]
    return audit_stick(scan_stick(root, filesystem=filesystem), rig)


# --- human report -------------------------------------------------------------- #

_VERDICT_LINES = {
    "take_it": "TAKE IT — this stick will show up tonight",
    "fix_first": "FIX FIRST — it mounts, but tonight has known holes",
    "do_not_take": "DO NOT TAKE — this stick will betray you at the booth",
}

_PRESENT = {True: "yes", False: "no"}


def format_report(report: dict[str, Any]) -> str:
    """Render the verdict report as terminal text, gig-check-style."""
    lib = report["library"]
    fs = report["filesystem"]
    audio = report["audio"]
    lines = [
        f"vibemix Export Guard — {report['rig_label']} — "
        f"{_VERDICT_LINES[report['verdict']]}",
        f"stick: {report['stick']}",
        (
            f"filesystem: {fs['detected'] or 'unknown'} ({fs['status']})"
            f" | library: Device {_PRESENT[lib['device_library']]}"
            f" · OneLibrary {_PRESENT[lib['onelibrary']]}"
            f" · ANLZ {_PRESENT[lib['usbanlz']]}"
            f" · Engine {_PRESENT[lib['engine']]}"
            f" · Serato {_PRESENT[lib['serato']]}"
        ),
    ]
    if audio["total"]:
        fmt_list = ", ".join(f"{k} ×{v}" for k, v in audio["by_format"].items())
        lines.append(f"audio: {audio['total']} file(s) ({fmt_list})")
    for blocker in report["blockers"]:
        lines.append(f"  [x] {blocker}")
    for warning in report["warnings"]:
        lines.append(f"  [!] {warning}")
    for note in report["rig_notes"]:
        lines.append(f"  [i] rig note: {note}")
    return "\n".join(lines)
