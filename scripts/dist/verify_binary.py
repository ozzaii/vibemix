# SPDX-License-Identifier: Apache-2.0
"""scripts/dist/verify_binary.py — Phase 18 Wave 1 (VERIFY-04).

Post-codesign / post-MSI binary attack verification gate. Walks the
shipped vibemix bundle (``.app`` on macOS, ``.msi`` on Windows), unpacks
every PyInstaller archive it finds (via the in-house ``_pyinstxtractor``
shim), and runs raw-byte scans for the canonical API-key patterns:

- Google AI Studio / Gemini: ``AIza[A-Za-z0-9_-]{35}``
- AWS access key:           ``AKIA[A-Z0-9]{16}``
- Google OAuth bearer:      ``ya29.[A-Za-z0-9_-]{20,}``
- OpenAI:                   ``sk-[A-Za-z0-9_-]{20,}``
- Generic 39-char shape:    ``\\b[A-Za-z0-9_-]{39}\\b`` (Google API key
  silhouette, useful when a key was rotated through a less-greppable
  format)

Exit codes:
- 0 — bundle clean
- 1 — bundle flagged
- 2 — usage / inspection error (MSI on a non-Windows host without 7z, etc.)

The matched byte sequences are NEVER written to logs or the JSON report.
Only the pattern name + bundle-relative source path are persisted; that
is the load-bearing redaction invariant (T-18-01 / T-18-02 in the plan's
threat model).

This is the runtime twin of ``scripts.build_sidecar.assert_no_aiza_leak``
(Phase 11 Wave 1). The build-time gate scans the PyInstaller ``--onedir``
output before signing; this script scans the post-sign / post-MSI
artifact, where the bundle shape is different (``.app`` on macOS,
``.msi`` archive on Windows). Both are deliberately separate functions.

CLI: ``python -m scripts.dist.verify_binary <bundle> [--report PATH]``
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import _pyinstxtractor

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Strict — Google AI Studio / Gemini key. 4 + 35 = 39 chars total.
AIZA_PATTERN: re.Pattern[bytes] = re.compile(rb"AIza[A-Za-z0-9_\-]{35}")

# AWS access key id — 4-char "AKIA" prefix + 16 uppercase/digits.
AKIA_PATTERN: re.Pattern[bytes] = re.compile(rb"AKIA[A-Z0-9]{16}")

# Google OAuth 2 bearer / refresh token.
YA29_PATTERN: re.Pattern[bytes] = re.compile(rb"ya29\.[A-Za-z0-9_\-]{20,}")

# OpenAI sk-* keys (legacy + project-scoped both start ``sk-``).
SK_PATTERN: re.Pattern[bytes] = re.compile(rb"sk-[A-Za-z0-9_\-]{20,}")

# Generic Google-API-key shape: 39 base64url-ish chars between word
# boundaries. This is the high-noise heuristic — fonts (.woff2 has long
# base64-shaped tables), wasm blobs, and images regularly contain random
# 39-char runs of [A-Za-z0-9_-]. The allowlist below suppresses generic39
# (only) on those suffixes; the strict patterns above always scan.
GENERIC_KEY_PATTERN: re.Pattern[bytes] = re.compile(rb"\b[A-Za-z0-9_\-]{39}\b")


class Pattern(str, Enum):
    """Named patterns. ``.value`` matches the ``pattern`` field on
    serialized ``Hit`` records. Use a string enum so JSON serialisation
    is automatic.
    """

    AIZA = "aiza"
    AKIA = "akia"
    YA29 = "ya29"
    SK = "sk-"
    GENERIC39 = "generic39"


_STRICT_PATTERNS: tuple[tuple[Pattern, re.Pattern[bytes]], ...] = (
    (Pattern.AIZA, AIZA_PATTERN),
    (Pattern.AKIA, AKIA_PATTERN),
    (Pattern.YA29, YA29_PATTERN),
    (Pattern.SK, SK_PATTERN),
)

# Suffixes where the *generic-39* heuristic produces too many false
# positives. Strict patterns (AIza/AKIA/ya29/sk-) still run on these.
# Documented in CONTEXT Area 5: "the 39-char generic shape is a
# high-noise heuristic; binary assets are skipped because they trip the
# regex on random byte runs".
_HIGH_FALSE_POSITIVE_SUFFIXES: tuple[str, ...] = (
    ".woff2",
    ".woff",
    ".ttf",
    ".otf",
    ".wasm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".mp3",
    ".wav",
    ".ogg",
)

# Chunked-read size — 4 MiB matches build_sidecar.py for parity.
_CHUNK: int = 4 * 1024 * 1024

# Files we even try to scan. ``""`` covers the main PyInstaller binary
# on POSIX (no extension).
_SCAN_SUFFIXES_STRICT: frozenset[str] = frozenset(
    (
        ".py",
        ".pyc",
        ".pyz",
        ".so",
        ".dylib",
        ".dll",
        ".pyd",
        ".bin",
        ".json",
        ".txt",
        ".cfg",
        ".ini",
        ".plist",
        ".exe",
        ".node",
        "",
    )
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hit:
    """A single key-pattern match. Field names are intentionally chosen
    so that no field can be (mis)used to store the matched bytes —
    enforced by the absence of ``matched``/``value``/``bytes``/``string``
    in this dataclass."""

    source: str
    pattern: str
    binary_offset: int | None = None


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of scanning a bundle."""

    ok: bool
    scanned: int
    hits: tuple[Hit, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MsiInspectionUnavailable(RuntimeError):
    """Raised when a ``.msi`` bundle is handed in but neither ``msiexec``
    (Windows-only) nor a ``7z`` fallback is on PATH."""


# ---------------------------------------------------------------------------
# Scanning core
# ---------------------------------------------------------------------------


def _iter_files(root: Path) -> Iterator[Path]:
    """Yield every regular file under ``root`` (recursive)."""
    for path in root.rglob("*"):
        try:
            if path.is_file():
                yield path
        except OSError:
            # Symlink loops, permission errors, etc. — skip silently.
            continue


def _read_chunks(path: Path) -> Iterator[bytes]:
    """Yield 4 MiB chunks of ``path``; silent on read errors."""
    try:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    return
                yield chunk
    except OSError as exc:
        logging.getLogger(__name__).debug("cannot read %s: %s", path, exc)


def _scan_chunk_for_patterns(
    chunk: bytes,
    *,
    include_generic39: bool,
) -> Iterator[tuple[Pattern, int]]:
    """Yield ``(pattern, offset_within_chunk)`` for every match in
    ``chunk``. Only the offset is yielded — the matched bytes are
    discarded immediately by the caller to honour the redaction
    invariant."""
    for name, regex in _STRICT_PATTERNS:
        for match in regex.finditer(chunk):
            yield name, match.start()
    if include_generic39:
        for match in GENERIC_KEY_PATTERN.finditer(chunk):
            yield Pattern.GENERIC39, match.start()


def _scan_file(
    path: Path,
    *,
    relative_to: Path,
    allowlist_suffixes: frozenset[str],
) -> Iterator[Hit]:
    """Scan a single file. Yields a Hit per match. Always runs the
    strict patterns; runs generic39 only when the suffix is not in
    ``allowlist_suffixes``.
    """
    suffix = path.suffix.lower()
    include_generic39 = suffix not in allowlist_suffixes
    rel = _safe_relative(path, relative_to)
    base_offset = 0
    for chunk in _read_chunks(path):
        for pattern, off in _scan_chunk_for_patterns(
            chunk, include_generic39=include_generic39
        ):
            yield Hit(source=rel, pattern=pattern.value, binary_offset=base_offset + off)
        base_offset += len(chunk)


def _safe_relative(path: Path, root: Path) -> str:
    """Bundle-relative POSIX-style path string. Falls back to absolute
    if ``path`` is not under ``root`` (e.g. extracted into a temp
    dir)."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# PyInstaller archive support
# ---------------------------------------------------------------------------


def _extract_pyinstaller_archive(pyz_path: Path, out_dir: Path) -> bool:
    """Try to extract ``pyz_path`` as a PyInstaller CArchive into
    ``out_dir``. Returns True if extraction wrote anything, False
    otherwise (e.g. the file isn't a PyInstaller bundle). Never
    raises."""
    arc = _pyinstxtractor.PyInstArchive(pyz_path)
    if not arc.open():
        return False
    try:
        arc.extract(out_dir)
        return any(out_dir.rglob("*"))
    finally:
        arc.close()


@contextmanager
def _extracted_archive(pyz_path: Path) -> Iterator[Path | None]:
    """Context manager wrapping ``_extract_pyinstaller_archive`` with
    automatic temp-dir cleanup. Yields the extraction root on success,
    or ``None`` if the file wasn't a PyInstaller bundle.
    """
    tmp = tempfile.mkdtemp(prefix="vibemix-pyz-")
    tmp_path = Path(tmp)
    try:
        ok = _extract_pyinstaller_archive(pyz_path, tmp_path)
        yield tmp_path if ok else None
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _is_pyinstaller_candidate(path: Path) -> bool:
    """Cheap pre-filter: PyInstaller archives usually live at well-known
    spots (``base_library.zip`` is a real zip; the main exe + ``.pyz``
    side files are CArchives). We only spend a real ``open()`` on
    suffixes worth trying."""
    suffix = path.suffix.lower()
    if suffix in (".pyz", ".bin"):
        return True
    if suffix == "" and path.is_file():
        # Main binary on POSIX has no extension; reading its tail for
        # the cookie magic is cheap.
        return True
    if suffix == ".exe":
        return True
    return False


# ---------------------------------------------------------------------------
# MSI inspection
# ---------------------------------------------------------------------------


def _inspect_msi(
    msi_path: Path,
    out_dir: Path,
    *,
    platform: str | None = None,
    runner: object | None = None,
    which: object | None = None,
) -> Path:
    """Extract ``msi_path`` into ``out_dir`` and return ``out_dir``.

    On Windows: invokes ``msiexec /a <msi> /qb TARGETDIR=<out_dir>`` via
    ``subprocess.check_call``. On non-Windows: tries ``7z x``. If
    neither is available, raises ``MsiInspectionUnavailable``.

    ``platform`` / ``runner`` / ``which`` are injection seams for unit
    tests; in production they default to ``sys.platform``,
    ``subprocess.check_call``, and ``shutil.which``.
    """
    plat = platform if platform is not None else sys.platform
    run = runner if runner is not None else subprocess.check_call
    where = which if which is not None else shutil.which

    out_dir.mkdir(parents=True, exist_ok=True)

    if plat == "win32":
        cmd = [
            "msiexec",
            "/a",
            str(msi_path),
            "/qb",
            f"TARGETDIR={out_dir}",
        ]
        run(cmd)  # type: ignore[misc]
        return out_dir

    seven_zip = where("7z")  # type: ignore[misc]
    if seven_zip:
        run([seven_zip, "x", f"-o{out_dir}", "-y", str(msi_path)])  # type: ignore[misc]
        return out_dir

    raise MsiInspectionUnavailable(
        "MSI inspection requires Windows (msiexec) or 7z on PATH; "
        f"neither is available on platform={plat!r}."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_bundle(
    bundle: Path,
    *,
    allowlist_suffixes: Iterable[str] = _HIGH_FALSE_POSITIVE_SUFFIXES,
    platform: str | None = None,
    runner: object | None = None,
    which: object | None = None,
) -> VerifyResult:
    """Scan ``bundle`` (a ``.app`` directory or ``.msi`` file) and return
    a :class:`VerifyResult`. Never raises on a bundle that exists; only
    raises on usage errors (missing file, unavailable MSI inspector).
    """
    bundle = Path(bundle)
    if not bundle.exists():
        raise FileNotFoundError(f"bundle not found: {bundle}")

    allow = frozenset(s.lower() for s in allowlist_suffixes)
    suffix = bundle.suffix.lower()

    log = logging.getLogger(__name__)
    log.info("scan_bundle: starting on %s", bundle)

    if suffix == ".msi" and bundle.is_file():
        # Extract MSI into a temp tree and walk that.
        tmp = tempfile.mkdtemp(prefix="vibemix-msi-")
        try:
            extracted = _inspect_msi(
                bundle,
                Path(tmp),
                platform=platform,
                runner=runner,
                which=which,
            )
            return _scan_tree(extracted, allow)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # Anything else (.app directory, raw onedir, single binary) — walk
    # directly.
    if bundle.is_dir():
        return _scan_tree(bundle, allow)
    if bundle.is_file():
        return _scan_tree(bundle.parent, allow, root=bundle.parent, single=bundle)

    # Shouldn't happen — exists() succeeded but neither dir nor file.
    raise FileNotFoundError(f"unrecognised bundle shape: {bundle}")


def _scan_tree(
    root: Path,
    allow: frozenset[str],
    *,
    single: Path | None = None,
) -> VerifyResult:
    """Walk ``root`` (or just ``single`` if provided), scanning each
    file and recursing into PyInstaller archives. Returns a
    :class:`VerifyResult`.
    """
    log = logging.getLogger(__name__)
    hits: list[Hit] = []
    scanned = 0

    files: Iterable[Path]
    if single is not None:
        files = (single,)
    else:
        files = _iter_files(root)

    for path in files:
        suffix = path.suffix.lower()
        # We always scan files with no suffix (main binary) and any
        # suffix in the strict set OR the allowlisted-binary set
        # (allowlisted suffixes still get the strict patterns).
        is_scannable = (
            suffix in _SCAN_SUFFIXES_STRICT or suffix in allow or suffix == ""
        )
        if not is_scannable:
            continue
        scanned += 1
        for hit in _scan_file(path, relative_to=root, allowlist_suffixes=allow):
            hits.append(hit)
            log.info(
                "hit pattern=%s source=%s offset=%s (value redacted)",
                hit.pattern,
                hit.source,
                hit.binary_offset,
            )

        # PyInstaller archive recursion. We try to extract any file that
        # could plausibly be a CArchive; non-PyInstaller files are a
        # no-op (open() returns False).
        if _is_pyinstaller_candidate(path):
            with _extracted_archive(path) as extracted:
                if extracted is not None:
                    sub = _scan_tree(extracted, allow)
                    scanned += sub.scanned
                    # Re-anchor nested hits at the parent-archive source
                    # so the report says "inside <archive>:<entry>".
                    archive_rel = _safe_relative(path, root)
                    for sub_hit in sub.hits:
                        hits.append(
                            Hit(
                                source=f"{archive_rel}!{sub_hit.source}",
                                pattern=sub_hit.pattern,
                                binary_offset=sub_hit.binary_offset,
                            )
                        )

    ok = not hits
    return VerifyResult(ok=ok, scanned=scanned, hits=tuple(hits))


def verify(bundle: Path, **kwargs: object) -> VerifyResult:
    """Public alias for :func:`scan_bundle` — accepted by the plan's
    artifact contract.
    """
    return scan_bundle(bundle, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_report(result: VerifyResult, report_path: Path) -> None:
    """Serialize ``result`` to ``report_path`` as JSON.

    Shape: ``{"status": "clean"|"flagged", "scanned": int, "binary_count": int,
    "flagged_strings": [...], "hits": [{"source": str, "pattern": str}]}``

    The ``flagged_strings`` field is intentionally the *list of pattern
    names* (deduplicated), NEVER the matched bytes. Plan
    threat-model T-18-01 enforced.
    """
    status = "clean" if result.ok else "flagged"
    payload = {
        "status": status,
        "scanned": result.scanned,
        "binary_count": result.scanned,
        "flagged_strings": sorted({h.pattern for h in result.hits}),
        "hits": [
            {"source": h.source, "pattern": h.pattern} for h in result.hits
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_binary",
        description=(
            "Scan a vibemix bundle (.app on macOS, .msi on Windows) for "
            "leaked API-key strings. Exits 1 if any pattern is matched. "
            "Phase 18 Wave 1 — VERIFY-04."
        ),
    )
    parser.add_argument(
        "bundle",
        type=Path,
        help="Path to the .app directory or .msi file to verify.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=(
            "Where to write verify-report.json. Defaults to "
            "<bundle>.verify-report.json next to the bundle."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Reserved for future tuning — currently treats warnings the "
            "same as failures. No-op in v1."
        ),
    )
    parser.add_argument(
        "--allowlist-suffix",
        action="append",
        default=None,
        metavar="SUFFIX",
        help=(
            "Repeatable. Add a suffix to the generic-39 false-positive "
            "allowlist (e.g. --allowlist-suffix .data)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("VIBEMIX_VERIFY_LOG_LEVEL", "INFO"),
        format="[verify_binary] %(message)s",
    )
    log = logging.getLogger(__name__)

    bundle: Path = args.bundle
    if not bundle.exists():
        log.error("bundle not found: %s", bundle)
        return 2

    allow = list(_HIGH_FALSE_POSITIVE_SUFFIXES)
    if args.allowlist_suffix:
        allow.extend(s.lower() for s in args.allowlist_suffix)

    try:
        result = scan_bundle(bundle, allowlist_suffixes=allow)
    except MsiInspectionUnavailable as exc:
        log.error("%s", exc)
        return 2
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2

    report_path: Path = (
        args.report
        if args.report is not None
        else bundle.with_name(bundle.name + ".verify-report.json")
    )
    write_report(result, report_path)

    log.info(
        "scanned=%d hits=%d report=%s",
        result.scanned,
        len(result.hits),
        report_path,
    )
    if result.ok:
        return 0
    # Loud non-zero — patterns and source paths only; never the bytes.
    for hit in result.hits:
        log.error("LEAK pattern=%s source=%s (value redacted)", hit.pattern, hit.source)
    return 1


if __name__ == "__main__":
    sys.exit(main())
