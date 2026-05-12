# SPDX-License-Identifier: Apache-2.0
"""scripts/build_sidecar.py — Phase 11 Wave 1.

End-to-end PyInstaller build pipeline for the ``vibemix-core`` Tauri
sidecar. Detects the host's Rust target triple via ``rustc -vV``, runs
PyInstaller against ``vibemix-core.macos.spec`` or ``vibemix-core.windows.spec``,
and then copies + renames the resulting ``dist/vibemix-core/`` onedir
into ``tauri/src-tauri/binaries/vibemix-core-<triple>/`` with the inner
executable renamed to ``vibemix-core-<triple>{exe_suffix}`` — that's the
exact filename Tauri's ``externalBin`` configuration expects (RESEARCH
Pitfall 4).

CI gate: every successful build runs ``assert_no_aiza_leak`` over the
final bundle. Any byte sequence matching ``AIza[A-Za-z0-9_-]{35}`` aborts
the build with a non-zero exit code — that's the Phase 5 invariant
applied at packaging time (RESEARCH Pitfall 5; ARCH-01 / DIST-05).

Usage on macOS (Apple Silicon):
    uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec

Usage on Windows:
    uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec

Output: tauri/src-tauri/binaries/vibemix-core-<triple>/vibemix-core-<triple>[.exe]

Anti-pattern guards built in:
- Refuses to run with ``--onefile`` (caller can't pass it; the spec files
  use --onedir exclusively per RESEARCH Pitfall 1).
- ``--no-aiza-check`` prints a loud WARNING and the rest of the
  build still runs, but CI must NEVER pass this flag.
- ``rustc -vV`` is the triple source — NOT ``cargo metadata`` (the script
  must work before Wave 2 creates a Cargo.toml in tauri/src-tauri/).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Pattern for the Gemini API key prefix. The full key is 39 characters:
# ``AIza`` + 35 base64url-ish chars. RESEARCH Pitfall 5 — Phase 5 invariant.
AIZA_PATTERN = re.compile(rb"AIza[A-Za-z0-9_-]{35}")
AIZA_PATTERN_TEXT = re.compile(r"AIza[A-Za-z0-9_-]{35}")

# Files we scan with ``strings`` (or fallback byte read) for AIza leaks.
# Anything that ships in the bundle is fair game; .py / .json / .txt are
# scanned as text + bytes. .pyc / .so / .dylib are byte-only.
_SCAN_SUFFIXES = (".py", ".pyc", ".so", ".dylib", ".dll", ".pyd", ".bin", ".json", ".txt", "")

# Chunked byte read size for fallback scanning (Windows `strings` absent).
_CHUNK = 4 * 1024 * 1024  # 4 MiB

# Project root resolves from the script location; one level up from
# ``scripts/build_sidecar.py``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where Tauri's externalBin lookup expects per-triple binaries.
_TAURI_BINARIES_DIR = _PROJECT_ROOT / "tauri" / "src-tauri" / "binaries"


# ---------------------------------------------------------------------------
# Triple detection
# ---------------------------------------------------------------------------


def detect_target_triple() -> str:
    """Return the host Rust target triple by parsing ``rustc -vV``.

    Examples (verified on real installs):
    - ``aarch64-apple-darwin`` (Apple Silicon)
    - ``x86_64-apple-darwin`` (Intel Mac)
    - ``x86_64-pc-windows-msvc`` (typical Windows 11 x64)
    - ``x86_64-unknown-linux-gnu`` (CI matrix only — v1 excludes Linux end users)

    Raises RuntimeError if rustc is not on PATH. We deliberately do NOT
    fall back to ``cargo metadata`` (per A7) — ``cargo metadata`` requires
    a Cargo.toml in the cwd, and Wave 2 hasn't created tauri/src-tauri/
    Cargo.toml yet.
    """
    try:
        out = subprocess.check_output(["rustc", "-vV"], text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "rustc not on PATH. Install Rust via https://rustup.rs/ to "
            "build the Tauri sidecar (target-triple detection needs it)."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"rustc -vV failed: {exc}") from exc

    for line in out.splitlines():
        if line.startswith("host: "):
            triple = line.split("host: ", 1)[1].strip()
            if not triple:
                raise RuntimeError(f"rustc -vV produced empty host line:\n{out}")
            return triple

    raise RuntimeError(f"rustc -vV did not include a host line:\n{out}")


def exe_suffix_for_triple(triple: str) -> str:
    """Return ``.exe`` if the triple targets Windows, else empty string."""
    return ".exe" if "windows" in triple else ""


# ---------------------------------------------------------------------------
# PyInstaller orchestration
# ---------------------------------------------------------------------------


def run_pyinstaller(spec: Path, *, clean: bool = True) -> Path:
    """Invoke PyInstaller against ``spec`` via ``uv run``.

    Returns the resulting ``dist/vibemix-core/`` path. Raises
    CalledProcessError if PyInstaller exits non-zero.

    ``clean`` (default True) wipes PyInstaller's intermediate caches so
    that a fresh build doesn't pick up stale modules — this is the
    recommended flag for CI matrix builds (RESEARCH §Pitfall + STACK).
    """
    if not spec.exists():
        raise FileNotFoundError(f"spec file not found: {spec}")

    dist_dir = _PROJECT_ROOT / "dist"
    cmd = [
        "uv",
        "run",
        "pyinstaller",
        str(spec),
        "--noconfirm",
        "--distpath",
        str(dist_dir),
    ]
    if clean:
        cmd.append("--clean")

    print(f"[build_sidecar] running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True, cwd=_PROJECT_ROOT)

    out_dir = dist_dir / "vibemix-core"
    if not out_dir.is_dir():
        raise RuntimeError(
            f"PyInstaller succeeded but {out_dir} not found — "
            f"check the spec's COLLECT(name=...) value."
        )
    return out_dir


def install_into_tauri_binaries(
    onedir: Path,
    triple: str,
    *,
    exe_suffix: str,
) -> Path:
    """Copy ``onedir`` into ``tauri/src-tauri/binaries/vibemix-core-<triple>/``
    and rename the inner binary to ``vibemix-core-<triple><exe_suffix>``.

    Returns the path to the renamed binary. Idempotent: nukes the target
    dir if it already exists (rebuilds overwrite cleanly).

    Raises RuntimeError if the source binary is missing or the rename
    target collides with an existing file in an unexpected way.
    """
    if not onedir.is_dir():
        raise RuntimeError(f"source onedir not found: {onedir}")

    src_binary = onedir / f"vibemix-core{exe_suffix}"
    if not src_binary.exists():
        raise RuntimeError(
            f"expected inner binary {src_binary} missing — "
            f"spec file must have COLLECT(name='vibemix-core')."
        )

    target_dir = _TAURI_BINARIES_DIR / f"vibemix-core-{triple}"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(onedir, target_dir)
    renamed = target_dir / f"vibemix-core-{triple}{exe_suffix}"
    original = target_dir / f"vibemix-core{exe_suffix}"
    if renamed.exists():
        # shouldn't happen — shutil.copytree to fresh dir — but defensive.
        raise RuntimeError(f"rename target {renamed} already exists")
    original.rename(renamed)

    # Sanity: preserve / re-assert executable bit on POSIX. shutil.copytree
    # preserves permissions by default, but we re-assert in case a remote
    # filesystem stripped them.
    if exe_suffix == "":
        st = renamed.stat()
        renamed.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if not os.access(renamed, os.X_OK):
            raise RuntimeError(f"renamed binary {renamed} is not executable")
    return renamed


# ---------------------------------------------------------------------------
# AIza leak gate
# ---------------------------------------------------------------------------


def _scan_file_for_aiza(path: Path) -> list[str]:
    """Scan ``path`` for any AIza-prefixed Gemini key. Returns the list of
    matches (empty if clean). Uses ``strings`` when available (macOS /
    Linux) and falls back to chunked byte read on Windows (no `strings`).
    """
    matches: list[str] = []

    # Try the system ``strings`` first — fastest + handles binary files
    # cleanly. ``strings`` is GNU binutils-flavored on macOS/Linux; on
    # Windows there's no built-in equivalent, hence the fallback.
    #
    # NOTE: ``strings`` on macOS can emit non-UTF8 bytes (older Mach-O
    # sections with Latin-1 string-table content; pyc magic-byte runs).
    # We capture raw bytes + match the byte regex; text decode happens
    # only for human-readable error logs, not for matching.
    use_strings = shutil.which("strings") is not None
    if use_strings:
        try:
            proc = subprocess.run(
                ["strings", "-a", str(path)],
                capture_output=True,
                timeout=120,
                check=False,
            )
            # AIza is pure ASCII; match against raw bytes to avoid the
            # UTF-8 decode crashing on a single non-ASCII byte upstream.
            matches.extend(
                m.decode("ascii", errors="replace")
                for m in AIZA_PATTERN.findall(proc.stdout)
            )
        except subprocess.TimeoutExpired:
            print(f"[build_sidecar] strings timed out on {path}; falling back to byte scan", file=sys.stderr)
            use_strings = False  # fall through to byte read

    if not use_strings:
        try:
            with path.open("rb") as fh:
                while True:
                    chunk = fh.read(_CHUNK)
                    if not chunk:
                        break
                    matches.extend(m.decode("ascii", errors="replace") for m in AIZA_PATTERN.findall(chunk))
        except OSError as exc:
            print(f"[build_sidecar] cannot read {path}: {exc}", file=sys.stderr)

    return matches


def assert_no_aiza_leak(bundle_dir: Path) -> None:
    """Walk ``bundle_dir`` recursively and abort if any file contains an
    AIza-prefixed Gemini key string.

    Raises RuntimeError on first leak found (with the file path). Prints
    ``OK: no AIza-pattern strings found in bundle`` to stderr on success.

    Files included in the scan:
    - Everything with a suffix in ``_SCAN_SUFFIXES``.
    - Files with NO suffix (the main PyInstaller binary on macOS/Linux is
      ``vibemix-core`` with no extension).

    This is the Phase 5 invariant enforced at packaging time
    (RESEARCH Pitfall 5).
    """
    if not bundle_dir.is_dir():
        raise RuntimeError(f"bundle dir not found: {bundle_dir}")

    leak_count = 0
    files_scanned = 0
    for path in bundle_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        # Empty suffix is the main binary on POSIX; we want to scan it.
        if suffix and suffix not in _SCAN_SUFFIXES:
            continue
        files_scanned += 1
        matches = _scan_file_for_aiza(path)
        if matches:
            leak_count += len(matches)
            # Don't print the actual key value — just enough to identify
            # the file. The leak itself is the secret; logs are not.
            print(
                f"[build_sidecar] AIza LEAK in {path.relative_to(_PROJECT_ROOT) if path.is_relative_to(_PROJECT_ROOT) else path}: "
                f"{len(matches)} match(es) (values redacted)",
                file=sys.stderr,
            )

    if leak_count > 0:
        raise RuntimeError(
            f"API KEY LEAK: found {leak_count} AIza-pattern match(es) across "
            f"{files_scanned} scanned file(s) in {bundle_dir}. Bundle is "
            f"UNSAFE to ship. Review .env exclusion in the spec file + verify "
            f"no test fixtures contain real keys."
        )
    print(
        f"[build_sidecar] OK: no AIza-pattern strings found in bundle "
        f"({files_scanned} file(s) scanned in {bundle_dir})",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def build_and_install(
    spec: Path,
    *,
    triple: str | None = None,
    skip_aiza_check: bool = False,
) -> Path:
    """End-to-end: detect triple → pyinstaller → copy + rename → AIza gate.

    Returns the absolute path of the final installed binary inside
    ``tauri/src-tauri/binaries/vibemix-core-<triple>/``. Caller should
    print this path for visual verification.
    """
    if triple is None:
        triple = detect_target_triple()
    suffix = exe_suffix_for_triple(triple)

    print(f"[build_sidecar] target triple: {triple}", file=sys.stderr)
    print(f"[build_sidecar] spec:          {spec}", file=sys.stderr)

    onedir = run_pyinstaller(spec)

    installed = install_into_tauri_binaries(onedir, triple, exe_suffix=suffix)
    bundle_dir = installed.parent

    if skip_aiza_check:
        print(
            "[build_sidecar] WARNING: AIza leak check SKIPPED — "
            "CI must NEVER pass --no-aiza-check; this is a Phase 5 invariant.",
            file=sys.stderr,
        )
    else:
        assert_no_aiza_leak(bundle_dir)

    print(f"[build_sidecar] installed: {installed}", file=sys.stderr)
    return installed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_sidecar",
        description=(
            "Build the vibemix-core PyInstaller bundle + install into the "
            "Tauri externalBin layout (vibemix-core-<triple>/)."
        ),
    )
    parser.add_argument(
        "--spec",
        required=True,
        help=(
            "Path to .spec file — vibemix-core.macos.spec or vibemix-core.windows.spec. "
            "Cross-compilation is rare and must be explicit."
        ),
    )
    parser.add_argument(
        "--triple",
        default=None,
        help="Override target triple (default: detect from `rustc -vV`).",
    )
    parser.add_argument(
        "--no-aiza-check",
        action="store_true",
        help=(
            "Skip the AIza key-leak gate. DANGEROUS; CI must NEVER pass this. "
            "Phase 5 invariant — ARCH-01 / DIST-05."
        ),
    )
    args = parser.parse_args(argv)

    spec = Path(args.spec).resolve()
    try:
        installed = build_and_install(
            spec,
            triple=args.triple,
            skip_aiza_check=args.no_aiza_check,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[build_sidecar] FAILED: {exc}", file=sys.stderr)
        return 1

    # Final visual marker for the executor / human verifier.
    print(installed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
