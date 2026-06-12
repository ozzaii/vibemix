# SPDX-License-Identifier: Apache-2.0
"""Export Guard — read-only "will this USB show up on this rig?" auditor.

The 2026-06-11 hand-of-god pack's #2 breakthrough: the safest God-mode wedge
is a read-only USB preflight that predicts booth failure before the DJ leaves
the kitchen. These tests pin that contract over fake USB trees in ``tmp_path``.

Every hardware fact asserted here was verified against official AlphaTheta
notices/manuals by the 2026-06-12 research pass (wf_c61ce5aa-807, 23/24 claims
adversarially confirmed):

* OneLibrary marker = ``PIONEER/rekordbox/exportLibrary.db``; classic Device
  Library = ``PIONEER/rekordbox/export.pdb``; both may coexist (rekordbox
  7.2.11+ writes both).
* CDJ-3000X / OPUS-QUAD read OneLibrary; CDJ-3000 / XDJ-XZ / XDJ-RX3 /
  CDJ-2000NXS2 and older read classic Device Library.
* FLAC/ALAC start at NXS2; XDJ-XZ/RX3 list no ALAC; NXS2 has no exFAT;
  exFAT on CDJ-3000 / XDJ-XZ is firmware-added (warn, not trust).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.library.export_guard import (
    RIG_PROFILES,
    audit_stick,
    format_report,
    run_export_guard,
    scan_stick,
)

# --- fixture helpers ---------------------------------------------------------- #


def _add_device_library(root: Path) -> None:
    rb = root / "PIONEER" / "rekordbox"
    rb.mkdir(parents=True, exist_ok=True)
    (rb / "export.pdb").write_bytes(b"\x00" * 32)


def _add_onelibrary(root: Path) -> None:
    rb = root / "PIONEER" / "rekordbox"
    rb.mkdir(parents=True, exist_ok=True)
    (rb / "exportLibrary.db").write_bytes(b"\x00" * 32)


def _add_usbanlz(root: Path) -> None:
    anlz = root / "PIONEER" / "USBANLZ" / "P016" / "0000875E"
    anlz.mkdir(parents=True, exist_ok=True)
    (anlz / "ANLZ0000.DAT").write_bytes(b"\x00" * 16)


def _add_engine_library(root: Path) -> None:
    db2 = root / "Engine Library" / "Database2"
    db2.mkdir(parents=True, exist_ok=True)
    (db2 / "m.db").write_bytes(b"\x00" * 32)


def _add_serato(root: Path) -> None:
    sub = root / "_Serato_" / "Subcrates"
    sub.mkdir(parents=True, exist_ok=True)
    (sub / "Peak Time.crate").write_bytes(b"\x00" * 16)


def _add_audio(root: Path, names: list[str]) -> None:
    contents = root / "Contents"
    contents.mkdir(exist_ok=True)
    for name in names:
        (contents / name).write_bytes(b"\x00" * 64)


def _healthy_dual_stick(root: Path, n_mp3: int = 4) -> None:
    _add_device_library(root)
    _add_onelibrary(root)
    _add_usbanlz(root)
    _add_audio(root, [f"track{i}.mp3" for i in range(n_mp3)])


# --- scan: stick inventory ------------------------------------------------------ #


def test_scan_detects_library_markers(tmp_path):
    _healthy_dual_stick(tmp_path)
    _add_engine_library(tmp_path)
    _add_serato(tmp_path)
    inv = scan_stick(tmp_path)
    assert inv.has_device_library
    assert inv.has_onelibrary
    assert inv.has_usbanlz
    assert inv.has_engine_library
    assert inv.has_serato
    assert inv.audio_by_format == {"mp3": 4}


def test_scan_empty_stick(tmp_path):
    inv = scan_stick(tmp_path)
    assert not inv.has_device_library
    assert not inv.has_onelibrary
    assert inv.audio_by_format == {}


def test_scan_skips_appledouble_and_hidden(tmp_path):
    # macOS litters sticks with ._resource forks and hidden dirs; counting
    # them would fabricate phantom tracks.
    _add_audio(tmp_path, ["real.mp3", "._real.mp3"])
    hidden = tmp_path / ".Spotlight-V100"
    hidden.mkdir()
    (hidden / "ghost.mp3").write_bytes(b"\x00")
    inv = scan_stick(tmp_path)
    assert inv.audio_by_format == {"mp3": 1}


# --- library format split (the AlphaTheta dual-format trap) ------------------- #


def test_onelibrary_rig_blocks_device_library_only_stick(tmp_path):
    # The XDJ-AZ horror story: classic export looks fine at home, blank at
    # the venue because the rig reads OneLibrary only.
    _add_device_library(tmp_path)
    _add_usbanlz(tmp_path)
    _add_audio(tmp_path, ["a.mp3", "b.mp3"])
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-3000x"])
    assert report["verdict"] == "do_not_take"
    assert any("OneLibrary" in b for b in report["blockers"])


def test_device_library_rig_blocks_onelibrary_only_stick(tmp_path):
    _add_onelibrary(tmp_path)
    _add_audio(tmp_path, ["a.mp3"])
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-3000"])
    assert report["verdict"] == "do_not_take"
    assert any("Device Library" in b for b in report["blockers"])


def test_dual_format_stick_takes_on_both_generations(tmp_path):
    _healthy_dual_stick(tmp_path)
    for rig in ("cdj-3000x", "cdj-3000"):
        report = audit_stick(
            scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES[rig]
        )
        assert report["verdict"] == "take_it", (rig, report["blockers"])


# --- filesystem rules ----------------------------------------------------------- #


def test_unsupported_filesystem_blocks(tmp_path):
    _healthy_dual_stick(tmp_path)
    for fs in ("ntfs", "apfs"):
        inv = scan_stick(tmp_path, filesystem=fs)
        report = audit_stick(inv, RIG_PROFILES["cdj-3000"])
        assert report["verdict"] == "do_not_take", fs
        assert any(fs in b.lower() for b in report["blockers"])


def test_firmware_added_exfat_warns_not_blocks(tmp_path):
    # XDJ-XZ's original manual bans exFAT; the current FAQ allows it.
    # Old-firmware units in the wild may reject the stick: warn, never trust.
    _healthy_dual_stick(tmp_path)
    inv = scan_stick(tmp_path, filesystem="exfat")
    report = audit_stick(inv, RIG_PROFILES["xdj-xz"])
    assert report["verdict"] == "fix_first"
    assert any("exfat" in w.lower() for w in report["warnings"])
    # RX3 lists exFAT natively in its manual — clean.
    report_rx3 = audit_stick(inv, RIG_PROFILES["xdj-rx3"])
    assert report_rx3["verdict"] == "take_it"


def test_exfat_blocked_on_nxs2(tmp_path):
    # CDJ-2000NXS2 official manual: FAT16/FAT32/HFS+ only.
    _healthy_dual_stick(tmp_path)
    inv = scan_stick(tmp_path, filesystem="exfat")
    report = audit_stick(inv, RIG_PROFILES["cdj-2000nxs2"])
    assert report["verdict"] == "do_not_take"


def test_unknown_filesystem_is_honest_absence(tmp_path):
    # Idle ≠ fault: when detection fails the report says unknown, no penalty.
    _healthy_dual_stick(tmp_path)
    inv = scan_stick(tmp_path)
    report = audit_stick(inv, RIG_PROFILES["cdj-3000"])
    assert report["filesystem"]["status"] == "unknown"
    assert report["verdict"] == "take_it"


# --- audio format rules ---------------------------------------------------------- #


def test_flac_blocked_on_pre_nxs2(tmp_path):
    _add_device_library(tmp_path)
    _add_usbanlz(tmp_path)
    _add_audio(tmp_path, ["a.mp3", "b.flac", "c.flac"])
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-2000nxs"])
    assert report["verdict"] == "do_not_take"  # 2/3 unplayable
    assert any("flac" in b.lower() for b in report["blockers"])


def test_flac_fine_on_nxs2(tmp_path):
    _add_device_library(tmp_path)
    _add_usbanlz(tmp_path)
    _add_audio(tmp_path, ["a.mp3", "b.flac"])
    report = audit_stick(
        scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES["cdj-2000nxs2"]
    )
    assert report["verdict"] == "take_it"


def test_m4a_ambiguity_warns_when_rig_lacks_alac(tmp_path):
    # .m4a may be AAC (XZ plays it) or ALAC (XZ's manual lists none) — the
    # auditor cannot decode in V1, so it warns instead of guessing.
    _healthy_dual_stick(tmp_path, n_mp3=8)
    _add_audio(tmp_path, ["maybe_alac.m4a"])
    report = audit_stick(
        scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES["xdj-xz"]
    )
    assert report["verdict"] == "fix_first"
    assert any("m4a" in w.lower() for w in report["warnings"])


# --- missing prep / missing trees ------------------------------------------------ #


def test_raw_files_no_export_warns(tmp_path):
    # A bare stick of audio plays via raw browse, but with no playlists,
    # cues, or waveforms — fix_first, not a green light.
    _add_audio(tmp_path, ["a.mp3", "b.mp3"])
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-3000"])
    assert report["verdict"] == "fix_first"
    assert any("playlist" in w.lower() for w in report["warnings"])


def test_empty_stick_do_not_take(tmp_path):
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-3000"])
    assert report["verdict"] == "do_not_take"


def test_missing_usbanlz_warns(tmp_path):
    # export.pdb without USBANLZ = analysis sidecars gone: no waveforms.
    _add_device_library(tmp_path)
    _add_onelibrary(tmp_path)
    _add_audio(tmp_path, ["a.mp3"])
    report = audit_stick(
        scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES["cdj-3000"]
    )
    assert report["verdict"] == "fix_first"
    assert any("waveform" in w.lower() or "USBANLZ" in w for w in report["warnings"])


def test_engine_stick_on_pioneer_rig_warns(tmp_path):
    _healthy_dual_stick(tmp_path)
    _add_engine_library(tmp_path)
    report = audit_stick(
        scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES["cdj-3000"]
    )
    assert any("Engine" in w for w in report["warnings"])


# --- non-Pioneer rigs ------------------------------------------------------------- #


def test_serato_rig_wants_serato_folder(tmp_path):
    _add_serato(tmp_path)
    _add_audio(tmp_path, ["a.mp3", "b.flac"])
    report = audit_stick(scan_stick(tmp_path), RIG_PROFILES["serato-laptop"])
    assert report["verdict"] == "take_it"

    bare = tmp_path / "bare"
    bare.mkdir()
    _add_audio(bare, ["a.mp3"])
    report = audit_stick(scan_stick(bare), RIG_PROFILES["serato-laptop"])
    assert report["verdict"] == "fix_first"
    assert any("crate" in w.lower() for w in report["warnings"])


def test_engine_os_rig_reads_rekordbox_or_engine(tmp_path):
    # Denon Engine OS hardware reads rekordbox sticks directly.
    _healthy_dual_stick(tmp_path)
    report = audit_stick(
        scan_stick(tmp_path, filesystem="fat32"), RIG_PROFILES["engine-os"]
    )
    assert report["verdict"] == "take_it"


# --- report + CLI ------------------------------------------------------------------ #


def test_format_report_names_the_rig_and_verdict(tmp_path):
    _add_device_library(tmp_path)
    _add_audio(tmp_path, ["a.mp3"])
    text = format_report(audit_stick(scan_stick(tmp_path), RIG_PROFILES["cdj-3000x"]))
    assert "DO NOT TAKE" in text
    assert "CDJ-3000X" in text


def test_run_export_guard_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_export_guard(tmp_path / "nope", "cdj-3000")


def test_run_export_guard_unknown_rig_raises(tmp_path):
    with pytest.raises(KeyError):
        run_export_guard(tmp_path, "cdj-9999")


def test_cli_exit_codes_follow_verdict(tmp_path, capsys):
    import argparse

    import vibemix.__main__ as m

    _add_device_library(tmp_path)
    _add_audio(tmp_path, ["a.mp3"])
    args = argparse.Namespace(
        usb=str(tmp_path), rig="cdj-3000x", json=False, filesystem=None
    )
    # Device-Library-only stick on a OneLibrary rig → do_not_take (2)
    assert m._cmd_library_export_guard(args) == 2
    assert "DO NOT TAKE" in capsys.readouterr().out


def test_cli_json_output_is_machine_readable(tmp_path, capsys):
    import argparse
    import json

    import vibemix.__main__ as m

    _healthy_dual_stick(tmp_path)
    args = argparse.Namespace(
        usb=str(tmp_path), rig="cdj-3000", json=True, filesystem="fat32"
    )
    assert m._cmd_library_export_guard(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"].startswith("vibemix.export-guard.")
    assert payload["verdict"] == "take_it"


def test_cli_missing_path_exits_1(tmp_path, capsys):
    import argparse

    import vibemix.__main__ as m

    args = argparse.Namespace(
        usb=str(tmp_path / "nope"), rig="cdj-3000", json=False, filesystem=None
    )
    assert m._cmd_library_export_guard(args) == 1
    assert "not found" in capsys.readouterr().err.lower()
