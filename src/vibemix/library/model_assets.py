# SPDX-License-Identifier: Apache-2.0
"""Local AI model asset installer/status helpers.

The desktop app and CLI need one narrow setup seam: know where local model
assets belong, verify what is present, and download only assets that have a
stable upstream source. CLAP is hosted on Hugging Face; CUE-DETR is currently a
locally exported ONNX artifact. A release/ops build can provide a hosted CUE
artifact through env vars; otherwise CUE is reported as a manual target.
"""

from __future__ import annotations

import hashlib
import os
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from vibemix.library.cache_paths import CLAP_ONNX_ENV, clap_onnx_dir

_CLAP_ENV = CLAP_ONNX_ENV
_CLAP_BASE_URL = "https://huggingface.co/Xenova/larger_clap_music_and_speech/resolve/main"
_CUE_URL_ENV = "VIBEMIX_CUE_ONNX_URL"
_CUE_SHA_ENV = "VIBEMIX_CUE_ONNX_SHA256"
_CUE_SIZE_ENV = "VIBEMIX_CUE_ONNX_SIZE"
_MOSS_ARCHIVE_URL_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_URL"
_MOSS_ARCHIVE_SHA_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SHA256"
_MOSS_ARCHIVE_SIZE_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SIZE"
_PROGRESS_CHUNK_BYTES = 8 * 1024 * 1024
ModelProgress = Callable[[dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class ModelFile:
    rel_path: str
    size: int
    sha256: str
    source_rel_path: str | None = None

    @property
    def url(self) -> str:
        return f"{_CLAP_BASE_URL}/{self.source_rel_path or self.rel_path}"


_CLAP_FILES: tuple[ModelFile, ...] = (
    ModelFile(
        "onnx/audio_model.onnx",
        281_749_092,
        "3ecc72d27740e2a09ced20cf22fd6244122e5e506008763a0f368b3b4ff6eac8",
    ),
    ModelFile(
        "onnx/text_model.onnx",
        501_513_769,
        "96c0f248bfaabe5d467958245beb0243e387ed628251e3b407b856848379e89c",
    ),
    ModelFile(
        "preprocessor_config.json",
        541,
        "9739f58296aa6f9ac18008fd0150fb2649bc554985fbde86d0a4041c882ac753",
    ),
    ModelFile(
        "tokenizer.json",
        2_108_774,
        "dc239041d98de27ffc3975473a1a23e3db4c937b23c138c38bbc66588bd247e5",
    ),
    ModelFile(
        "vocab.json",
        798_293,
        "ed19656ea1707df69134c4af35c8ceda2cc9860bf2c3495026153a133670ab5e",
    ),
    ModelFile(
        "merges.txt",
        456_318,
        "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
    ),
)


def clap_model_files() -> tuple[ModelFile, ...]:
    """Return the pinned CLAP files the app installer manages.

    The runtime loads ``onnx/audio_model.onnx`` and ``onnx/text_model.onnx``.
    The default manifest intentionally pins the full-precision Xenova ONNX
    files. fp16/q8 can become an installer variant only after parity testing
    proves there is no quality regression on the DJ-library retrieval gate.
    """
    return _CLAP_FILES


def _clap_model_dir() -> Path:
    """Resolved CLAP model directory (env override, else vibemix cache)."""
    return clap_onnx_dir()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_ok(path: Path, spec: ModelFile) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, None
    if path.stat().st_size != spec.size:
        return False, _sha256_file(path)
    digest = _sha256_file(path)
    return digest == spec.sha256, digest


def _notify_progress(progress: ModelProgress | None, frame: dict[str, object]) -> None:
    if progress is None:
        return
    try:
        progress(frame)
    except Exception:
        # Progress is UI telemetry. It must never make model setup fail.
        return


def _download_file(
    spec: ModelFile,
    dest: Path,
    *,
    progress: ModelProgress | None = None,
    model_id: str = "clap",
    n: int = 1,
    total: int = 1,
) -> dict[str, object]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(spec.url, headers={"User-Agent": "vibemix-model-installer/1"})
    tmp_path: Path | None = None
    h = hashlib.sha256()
    size = 0
    next_progress_at = _PROGRESS_CHUNK_BYTES
    try:
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "downloading",
                "rel_path": spec.rel_path,
                "downloaded": 0,
                "size": spec.size,
            },
        )
        with urlopen(req, timeout=120) as response:  # nosec B310 - fixed HTTPS manifest
            with tempfile.NamedTemporaryFile(
                prefix=dest.name + ".", suffix=".tmp", dir=dest.parent, delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    h.update(chunk)
                    size += len(chunk)
                    if size >= next_progress_at:
                        _notify_progress(
                            progress,
                            {
                                "id": model_id,
                                "n": n,
                                "total": total,
                                "status": "downloading",
                                "rel_path": spec.rel_path,
                                "downloaded": size,
                                "size": spec.size,
                            },
                        )
                        next_progress_at = size + _PROGRESS_CHUNK_BYTES
        digest = h.hexdigest()
        if size != spec.size or digest != spec.sha256:
            raise RuntimeError(
                f"checksum mismatch for {spec.rel_path}: size={size} sha256={digest}"
            )
        os.replace(tmp_path, dest)
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "downloaded",
                "rel_path": spec.rel_path,
                "downloaded": size,
                "size": spec.size,
            },
        )
        return {
            "rel_path": spec.rel_path,
            "source_rel_path": spec.source_rel_path or spec.rel_path,
            "path": str(dest),
            "status": "downloaded",
            "size": size,
            "sha256": digest,
            "url": spec.url,
        }
    except (OSError, RuntimeError, URLError) as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "error",
                "rel_path": spec.rel_path,
                "downloaded": size,
                "size": spec.size,
                "error": str(exc),
            },
        )
        raise RuntimeError(f"download failed for {spec.rel_path}: {exc}") from exc


def _download_url_to_file(
    *,
    url: str,
    dest: Path,
    expected_size: int,
    expected_sha256: str,
    rel_path: str,
    progress: ModelProgress | None = None,
    model_id: str = "cue-detr",
    n: int = 1,
    total: int = 1,
) -> dict[str, object]:
    """Download one env-configured model file with size/SHA verification."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "vibemix-model-installer/1"})
    tmp_path: Path | None = None
    h = hashlib.sha256()
    size = 0
    next_progress_at = _PROGRESS_CHUNK_BYTES
    try:
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "downloading",
                "rel_path": rel_path,
                "downloaded": 0,
                "size": expected_size,
            },
        )
        with urlopen(req, timeout=120) as response:  # nosec B310 - operator-provided HTTPS URL
            with tempfile.NamedTemporaryFile(
                prefix=dest.name + ".", suffix=".tmp", dir=dest.parent, delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    h.update(chunk)
                    size += len(chunk)
                    if size >= next_progress_at:
                        _notify_progress(
                            progress,
                            {
                                "id": model_id,
                                "n": n,
                                "total": total,
                                "status": "downloading",
                                "rel_path": rel_path,
                                "downloaded": size,
                                "size": expected_size,
                            },
                        )
                        next_progress_at = size + _PROGRESS_CHUNK_BYTES
        digest = h.hexdigest()
        if size != expected_size or digest != expected_sha256:
            raise RuntimeError(f"checksum mismatch for {rel_path}: size={size} sha256={digest}")
        os.replace(tmp_path, dest)
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "downloaded",
                "rel_path": rel_path,
                "downloaded": size,
                "size": expected_size,
            },
        )
        return {
            "rel_path": rel_path,
            "path": str(dest),
            "status": "downloaded",
            "size": size,
            "sha256": digest,
            "url": url,
        }
    except (OSError, RuntimeError, URLError) as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        _notify_progress(
            progress,
            {
                "id": model_id,
                "n": n,
                "total": total,
                "status": "error",
                "rel_path": rel_path,
                "downloaded": size,
                "size": expected_size,
                "error": str(exc),
            },
        )
        raise RuntimeError(f"download failed for {rel_path}: {exc}") from exc


def _ensure_model_dir(root: Path) -> None:
    """Ensure ``root`` is a real directory, repairing stale cache sentinels.

    Older setup experiments used symlinks for the CLAP cache. If the symlink
    target disappears, ``Path.mkdir(parents=True)`` raises ``FileExistsError``
    and first-run model setup dies before it can download anything. The model
    cache is app-owned, so a non-directory or broken symlink at this exact path
    is treated as corrupt setup state and moved aside.
    """
    if root.is_dir():
        return
    if root.is_symlink() or root.exists():
        stale = root.with_name(f"{root.name}.invalid")
        stale.unlink(missing_ok=True)
        root.replace(stale)
    root.mkdir(parents=True, exist_ok=True)


def install_clap_model(
    *, force: bool = False, progress: ModelProgress | None = None
) -> dict[str, object]:
    """Download/verify the CLAP ONNX snapshot into the vibemix cache.

    Existing files are checksum-verified and skipped unless ``force`` is true.
    Writes are atomic per file, so a failed download never leaves a partial file
    at the final path.
    """
    root = _clap_model_dir()
    _ensure_model_dir(root)
    files: list[dict[str, object]] = []
    errors: list[str] = []
    total = len(_CLAP_FILES)
    for index, spec in enumerate(_CLAP_FILES, start=1):
        dest = root / spec.rel_path
        ok, digest = _file_ok(dest, spec)
        if ok and not force:
            _notify_progress(
                progress,
                {
                    "id": "clap",
                    "n": index,
                    "total": total,
                    "status": "verified",
                    "rel_path": spec.rel_path,
                    "downloaded": spec.size,
                    "size": spec.size,
                },
            )
            files.append(
                {
                    "rel_path": spec.rel_path,
                    "source_rel_path": spec.source_rel_path or spec.rel_path,
                    "path": str(dest),
                    "status": "skipped",
                    "size": spec.size,
                    "sha256": digest,
                    "url": spec.url,
                }
            )
            continue
        try:
            if progress is None:
                files.append(_download_file(spec, dest))
            else:
                files.append(
                    _download_file(
                        spec,
                        dest,
                        progress=progress,
                        model_id="clap",
                        n=index,
                        total=total,
                    )
                )
        except RuntimeError as exc:
            errors.append(str(exc))
    return {
        "id": "clap",
        "installed": not errors and all((root / f.rel_path).is_file() for f in _CLAP_FILES),
        "path": str(root),
        "files": files,
        "errors": errors,
    }


def install_cue_model(
    *, force: bool = False, progress: ModelProgress | None = None
) -> dict[str, object]:
    """Install or verify the CUE-DETR ONNX artifact.

    By default this is an honest manual target. Release/ops builds can make it
    one-click by setting ``VIBEMIX_CUE_ONNX_URL`` plus size/SHA env pins. The
    URL must be HTTPS and every download is verified before the final rename.
    """
    from vibemix.library.cue_detr import model_path as cue_model_path
    from vibemix.library.cue_detr import model_status as cue_model_status

    path = cue_model_path().expanduser()
    cue = cue_model_status()
    files: list[dict[str, object]] = []
    errors: list[str] = []
    config, config_errors = _cue_download_config()

    if bool(cue["installed"]) and not force:
        _notify_progress(
            progress,
            {
                "id": "cue-detr",
                "n": 1,
                "total": 1,
                "status": "verified",
                "rel_path": path.name,
                "downloaded": path.stat().st_size,
                "size": path.stat().st_size,
            },
        )
        files.append(
            {
                "rel_path": path.name,
                "path": str(path),
                "status": "skipped",
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
                "url": config["url"] if config else "",
            }
        )
    elif config_errors:
        errors.extend(config_errors)
    elif config is None:
        errors.append(
            "CUE-DETR ONNX is not hosted by default; set VIBEMIX_CUE_ONNX_URL "
            "with VIBEMIX_CUE_ONNX_SHA256 and VIBEMIX_CUE_ONNX_SIZE, set "
            "VIBEMIX_CUE_ONNX_PATH, or place cuedetr.fp32.onnx in the vibemix cache."
        )
        _notify_progress(
            progress,
            {
                "id": "cue-detr",
                "n": 1,
                "total": 1,
                "status": "error",
                "rel_path": path.name,
                "downloaded": 0,
                "size": 0,
                "error": errors[-1],
            },
        )
    else:
        try:
            if progress is None:
                files.append(
                    _download_url_to_file(
                        url=config["url"],
                        dest=path,
                        expected_size=config["size"],
                        expected_sha256=config["sha256"],
                        rel_path=path.name,
                    )
                )
            else:
                files.append(
                    _download_url_to_file(
                        url=config["url"],
                        dest=path,
                        expected_size=config["size"],
                        expected_sha256=config["sha256"],
                        rel_path=path.name,
                        progress=progress,
                        model_id="cue-detr",
                        n=1,
                        total=1,
                    )
                )
            cue = cue_model_status()
        except RuntimeError as exc:
            errors.append(str(exc))

    return {
        "id": "cue-detr",
        "installed": bool(cue["installed"]),
        "path": cue["path"],
        "files": files,
        "errors": errors,
    }


def _archive_member_paths(archive_path: Path) -> list[str]:
    suffixes = "".join(archive_path.suffixes).lower()
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            return zf.namelist()
    if suffixes.endswith((".tar", ".tar.gz", ".tgz")) or tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as tf:
            return tf.getnames()
    raise RuntimeError("MOSS TTS archive must be a .zip, .tar, .tar.gz, or .tgz file")


def _safe_extract_archive(archive_path: Path, dest_root: Path) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    root = dest_root.resolve()

    def _check_member(name: str) -> None:
        target = (root / name).resolve()
        if not target.is_relative_to(root):
            raise RuntimeError(f"unsafe path in MOSS archive: {name}")

    for name in _archive_member_paths(archive_path):
        _check_member(name)

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(root)
        return
    with tarfile.open(archive_path) as tf:
        tf.extractall(root, filter="data")


def _moss_archive_config() -> tuple[dict[str, object] | None, list[str]]:
    url = os.environ.get(_MOSS_ARCHIVE_URL_ENV, "").strip()
    if not url:
        return None, []

    errors: list[str] = []
    if not url.startswith("https://"):
        errors.append(f"{_MOSS_ARCHIVE_URL_ENV} must be an https:// URL")

    sha = os.environ.get(_MOSS_ARCHIVE_SHA_ENV, "").strip().lower()
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        errors.append(f"{_MOSS_ARCHIVE_SHA_ENV} must be a 64-character lowercase SHA-256")

    raw_size = os.environ.get(_MOSS_ARCHIVE_SIZE_ENV, "").strip()
    try:
        size = int(raw_size)
    except ValueError:
        size = 0
    if size <= 0:
        errors.append(f"{_MOSS_ARCHIVE_SIZE_ENV} must be a positive byte count")

    if errors:
        return None, errors
    return {"url": url, "sha256": sha, "size": size}, []


def moss_model_installable() -> bool:
    """Whether a release/ops build configured a verified MOSS archive source."""
    return bool(os.environ.get(_MOSS_ARCHIVE_URL_ENV, "").strip())


def install_moss_model(
    *, force: bool = False, progress: ModelProgress | None = None
) -> dict[str, object]:
    """Install or verify the required local MOSS TTS model tree.

    The repo does not ship or guess a public 600MB+ model URL. Release/ops builds
    can make this one-click by setting archive URL/SHA/size pins; otherwise the
    installer returns an actionable manual setup error instead of pretending
    there is a fallback voice.
    """
    from vibemix.agent.local_tts import candidate_model_dir
    from vibemix.agent.local_tts import model_status as moss_model_status

    path = candidate_model_dir().expanduser()
    root = path.parent
    status = moss_model_status()
    files: list[dict[str, object]] = []
    errors: list[str] = []
    config, config_errors = _moss_archive_config()

    if bool(status["installed"]) and not force:
        _notify_progress(
            progress,
            {
                "id": "moss-tts",
                "n": 1,
                "total": 1,
                "status": "verified",
                "rel_path": path.name,
                "downloaded": 0,
                "size": 0,
            },
        )
        files.append(
            {
                "rel_path": path.name,
                "path": str(path),
                "status": "skipped",
                "size": 0,
                "sha256": "",
                "url": config["url"] if config else "",
            }
        )
    elif config_errors:
        errors.extend(config_errors)
    elif config is None:
        errors.append(
            "MOSS TTS ONNX is not hosted by default; set VIBEMIX_MOSS_TTS_DIR "
            "to a complete MOSS-TTS-Nano-100M-ONNX directory, place the model "
            "under the vibemix cache, or provide VIBEMIX_MOSS_TTS_ARCHIVE_URL "
            "with VIBEMIX_MOSS_TTS_ARCHIVE_SHA256 and VIBEMIX_MOSS_TTS_ARCHIVE_SIZE."
        )
        _notify_progress(
            progress,
            {
                "id": "moss-tts",
                "n": 1,
                "total": 1,
                "status": "error",
                "rel_path": path.name,
                "downloaded": 0,
                "size": 0,
                "error": errors[-1],
            },
        )
    else:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="moss-tts.", dir=root) as tmp_dir:
            archive_path = Path(tmp_dir) / "moss-tts-onnx.archive"
            try:
                if progress is None:
                    files.append(
                        _download_url_to_file(
                            url=config["url"],
                            dest=archive_path,
                            expected_size=config["size"],
                            expected_sha256=config["sha256"],
                            rel_path=archive_path.name,
                            model_id="moss-tts",
                        )
                    )
                else:
                    files.append(
                        _download_url_to_file(
                            url=config["url"],
                            dest=archive_path,
                            expected_size=config["size"],
                            expected_sha256=config["sha256"],
                            rel_path=archive_path.name,
                            progress=progress,
                            model_id="moss-tts",
                            n=1,
                            total=1,
                        )
                    )
                _safe_extract_archive(archive_path, root)
                status = moss_model_status()
                if not bool(status["installed"]):
                    missing = ", ".join(str(m) for m in status.get("missing", []))
                    mismatched = ", ".join(str(m) for m in status.get("mismatched", []))
                    detail = "; ".join(part for part in (missing, mismatched) if part)
                    errors.append(f"MOSS archive did not produce a usable model tree: {detail}")
            except RuntimeError as exc:
                errors.append(str(exc))

    if not errors:
        status = moss_model_status()
    return {
        "id": "moss-tts",
        "installed": bool(status["installed"]),
        "path": status["path"],
        "files": files,
        "errors": errors,
    }


def cue_model_install_status() -> dict[str, object]:
    """Back-compat name for the CUE install target."""
    return install_cue_model()


def cue_model_installable() -> bool:
    """Whether the app can attempt a CUE-DETR install from configured pins.

    A missing URL means CUE is a manual/optional model and should not look like
    a broken first-run setup action. If a URL is present but SHA/size pins are
    missing or invalid, this still returns True so the installer can surface the
    configuration error explicitly.
    """
    return bool(os.environ.get(_CUE_URL_ENV, "").strip())


def _cue_download_config() -> tuple[dict[str, object] | None, list[str]]:
    url = os.environ.get(_CUE_URL_ENV, "").strip()
    if not url:
        return None, []

    errors: list[str] = []
    if not url.startswith("https://"):
        errors.append(f"{_CUE_URL_ENV} must be an https:// URL")

    sha = os.environ.get(_CUE_SHA_ENV, "").strip().lower()
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        errors.append(f"{_CUE_SHA_ENV} must be a 64-character lowercase SHA-256")

    raw_size = os.environ.get(_CUE_SIZE_ENV, "").strip()
    try:
        size = int(raw_size)
    except ValueError:
        size = 0
    if size <= 0:
        errors.append(f"{_CUE_SIZE_ENV} must be a positive byte count")

    if errors:
        return None, errors
    return {"url": url, "sha256": sha, "size": size}, []


def install_models(
    target: str, *, force: bool = False, progress: ModelProgress | None = None
) -> dict[str, object]:
    """Install supported local model assets.

    ``target`` is ``"required"``, ``"clap"``, ``"moss"``, ``"cue"``, or
    ``"all"``. ``"required"`` installs the first-run required CLAP snapshot plus
    required MOSS TTS model. CUE-DETR downloads only when a release/ops build
    provides an HTTPS artifact URL plus size/SHA pins. Otherwise that target
    reports an actionable manual setup error.
    """
    if target not in {"required", "clap", "moss", "cue", "all"}:
        raise ValueError("target must be 'required', 'clap', 'moss', 'cue', or 'all'")

    results: list[dict[str, object]] = []
    target_progress: ModelProgress | None = None
    if progress is not None:

        def target_progress(frame: dict[str, object]) -> None:
            progress({"target": target, **frame})

    if target in {"required", "clap", "all"}:
        if target_progress is None:
            results.append(install_clap_model(force=force))
        else:
            results.append(install_clap_model(force=force, progress=target_progress))
    if target in {"required", "moss", "all"}:
        if target_progress is None:
            results.append(install_moss_model(force=force))
        else:
            results.append(install_moss_model(force=force, progress=target_progress))
    if target in {"cue", "all"}:
        if target_progress is None:
            results.append(install_cue_model(force=force))
        else:
            results.append(install_cue_model(force=force, progress=target_progress))

    return {
        "target": target,
        "results": results,
        "ok": all(not r["errors"] for r in results),
    }
