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
import tempfile
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
_PROGRESS_CHUNK_BYTES = 8 * 1024 * 1024
ModelProgress = Callable[[dict[str, object]], None]

CHATTERBOX_MODEL_ENV = "VIBEMIX_CHATTERBOX_MODEL"
CHATTERBOX_MODEL_REVISION_ENV = "VIBEMIX_CHATTERBOX_MODEL_REVISION"
CHATTERBOX_MODEL_REPO = "mlx-community/chatterbox-turbo-8bit"
CHATTERBOX_MODEL_REVISION = "2f2e21a03863f86a1274d1060dcc188e7cde77e1"
CHATTERBOX_ALLOW_PATTERNS: tuple[str, ...] = (
    "*.json",
    "*.safetensors",
    "*.py",
    "*.model",
    "*.tiktoken",
    "*.txt",
    "*.jsonl",
    "*.yaml",
    "*.npz",
    "*.pth",
)
CHATTERBOX_REQUIRED_FILES: dict[str, int] = {
    "added_tokens.json": 418,
    "conds.safetensors": 164_884,
    "config.json": 2_565,
    "merges.txt": 456_318,
    "model.safetensors": 706_233_417,
    "model.safetensors.index.json": 252_012,
    "special_tokens_map.json": 470,
    "tokenizer_config.json": 3_878,
    "vocab.json": 999_186,
}
_CHATTERBOX_SETUP_HINT = (
    "Chatterbox voice model is not ready. Connect to the internet and complete "
    "the first-run voice download before starting a set; offline launches stay "
    "voiceless instead of downloading mid-set."
)


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


def chatterbox_model_name() -> str:
    """Resolved Chatterbox model repo/path from env, else the pinned product repo."""
    return os.environ.get(CHATTERBOX_MODEL_ENV, "").strip() or CHATTERBOX_MODEL_REPO


def chatterbox_model_revision(model_name: str | None = None) -> str | None:
    """Resolved Chatterbox HF revision.

    The product repo is pinned to an immutable commit. Custom/local model paths can
    opt into their own revision with ``VIBEMIX_CHATTERBOX_MODEL_REVISION``.
    """
    override = os.environ.get(CHATTERBOX_MODEL_REVISION_ENV, "").strip()
    if override:
        return override
    model = model_name or chatterbox_model_name()
    return CHATTERBOX_MODEL_REVISION if model == CHATTERBOX_MODEL_REPO else None


def _chatterbox_local_model_path(model_name: str) -> Path | None:
    path = Path(model_name).expanduser()
    if path.exists():
        return path
    # Hugging Face repo ids include "/" too, so only obvious local spellings are
    # treated as paths when absent.
    if model_name.startswith(("~", ".", "/")):
        return path
    return None


def chatterbox_model_snapshot_path(
    model_name: str | None = None,
    revision: str | None = None,
) -> Path | None:
    """Return the local Chatterbox snapshot directory when it is already cached."""
    model = model_name or chatterbox_model_name()
    local = _chatterbox_local_model_path(model)
    if local is not None and local.exists():
        return local
    try:
        from huggingface_hub import try_to_load_from_cache
    except Exception:
        return None

    rev = revision if revision is not None else chatterbox_model_revision(model)
    cached = try_to_load_from_cache(model, "config.json", revision=rev)
    if isinstance(cached, str) and Path(cached).is_file():
        return Path(cached).parent
    return None


def chatterbox_model_cached(
    model_name: str | None = None,
    revision: str | None = None,
) -> bool:
    """True when the Chatterbox runtime files are on disk already.

    This is intentionally offline-only. Runtime availability must not mean "can
    download from Hugging Face during the first generated line."
    """
    model = model_name or chatterbox_model_name()
    local = _chatterbox_local_model_path(model)
    if local is not None and local.exists():
        return True

    snapshot = chatterbox_model_snapshot_path(model, revision)
    if snapshot is None:
        return False
    return all((snapshot / rel).is_file() for rel in CHATTERBOX_REQUIRED_FILES)


def _chatterbox_snapshot_file_results(snapshot: Path, *, status: str) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for rel_path, expected_size in CHATTERBOX_REQUIRED_FILES.items():
        path = snapshot / rel_path
        size = path.stat().st_size if path.is_file() else 0
        files.append(
            {
                "rel_path": rel_path,
                "path": str(path),
                "status": status,
                "size": size or expected_size,
                "sha256": _sha256_file(path) if path.is_file() and size <= 16 * 1024 * 1024 else "",
                "url": f"https://huggingface.co/{CHATTERBOX_MODEL_REPO}/resolve/"
                f"{CHATTERBOX_MODEL_REVISION}/{rel_path}",
            }
        )
    return files


def _snapshot_tqdm_class(progress: ModelProgress | None, *, model_id: str, rel_path: str):
    """Return a disabled tqdm subclass that optionally mirrors byte progress."""
    from tqdm.auto import tqdm

    class _ModelAssetTqdm(tqdm):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            self._is_bytes = kwargs.get("unit") == "B"
            self._next_emit_at = 0
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)
            if self._is_bytes:
                self._emit()

        def _emit(self) -> None:
            if progress is None:
                return
            _notify_progress(
                progress,
                {
                    "id": model_id,
                    "n": 1,
                    "total": 1,
                    "status": "downloading",
                    "rel_path": rel_path,
                    "downloaded": int(self.n),
                    "size": int(self.total or sum(CHATTERBOX_REQUIRED_FILES.values())),
                },
            )

        def update(self, n=1):  # type: ignore[no-untyped-def]
            result = super().update(n)
            if self._is_bytes and int(self.n) >= self._next_emit_at:
                self._emit()
                self._next_emit_at = int(self.n) + _PROGRESS_CHUNK_BYTES
            return result

        def refresh(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            result = super().refresh(*args, **kwargs)
            if getattr(self, "_is_bytes", False):
                self._emit()
            return result

    return _ModelAssetTqdm


def install_chatterbox_model(
    *, force: bool = False, progress: ModelProgress | None = None
) -> dict[str, object]:
    """Pre-fetch the pinned Chatterbox-Turbo MLX snapshot into the HF cache.

    The model is intentionally not bundled into the DMG. This installer makes
    the first-run wizard pay the network cost before the live set, so the TTS
    runtime either starts warm-from-disk or stays honestly muted offline.
    """
    model = chatterbox_model_name()
    revision = chatterbox_model_revision(model)
    rel = f"{model}@{revision or 'default'}"
    snapshot = chatterbox_model_snapshot_path(model, revision)
    files: list[dict[str, object]] = []
    errors: list[str] = []

    if snapshot is not None and chatterbox_model_cached(model, revision) and not force:
        _notify_progress(
            progress,
            {
                "id": "chatterbox",
                "n": 1,
                "total": 1,
                "status": "verified",
                "rel_path": rel,
                "downloaded": sum(CHATTERBOX_REQUIRED_FILES.values()),
                "size": sum(CHATTERBOX_REQUIRED_FILES.values()),
            },
        )
        return {
            "id": "chatterbox",
            "installed": True,
            "path": str(snapshot),
            "repo": model,
            "revision": revision or "",
            "files": _chatterbox_snapshot_file_results(snapshot, status="skipped"),
            "errors": [],
        }

    try:
        from huggingface_hub import snapshot_download

        _notify_progress(
            progress,
            {
                "id": "chatterbox",
                "n": 1,
                "total": 1,
                "status": "downloading",
                "rel_path": rel,
                "downloaded": 0,
                "size": sum(CHATTERBOX_REQUIRED_FILES.values()),
            },
        )
        snapshot_path = Path(
            snapshot_download(
                model,
                revision=revision,
                allow_patterns=list(CHATTERBOX_ALLOW_PATTERNS),
                force_download=force,
                tqdm_class=_snapshot_tqdm_class(progress, model_id="chatterbox", rel_path=rel),
            )
        )
        if not chatterbox_model_cached(model, revision):
            missing = [
                rel_path
                for rel_path in CHATTERBOX_REQUIRED_FILES
                if not (snapshot_path / rel_path).is_file()
            ]
            raise RuntimeError(f"snapshot is missing required file(s): {', '.join(missing)}")
        files = _chatterbox_snapshot_file_results(snapshot_path, status="downloaded")
        _notify_progress(
            progress,
            {
                "id": "chatterbox",
                "n": 1,
                "total": 1,
                "status": "downloaded",
                "rel_path": rel,
                "downloaded": sum(CHATTERBOX_REQUIRED_FILES.values()),
                "size": sum(CHATTERBOX_REQUIRED_FILES.values()),
            },
        )
        snapshot = snapshot_path
    except Exception as exc:
        errors.append(f"{_CHATTERBOX_SETUP_HINT} Details: {exc}")
        _notify_progress(
            progress,
            {
                "id": "chatterbox",
                "n": 1,
                "total": 1,
                "status": "error",
                "rel_path": rel,
                "downloaded": 0,
                "size": sum(CHATTERBOX_REQUIRED_FILES.values()),
                "error": errors[-1],
            },
        )

    return {
        "id": "chatterbox",
        "installed": not errors and snapshot is not None and chatterbox_model_cached(model, revision),
        "path": str(snapshot or ""),
        "repo": model,
        "revision": revision or "",
        "files": files,
        "errors": errors,
    }


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

    ``target`` is ``"required"``, ``"clap"``, ``"chatterbox"``, ``"cue"``, or
    ``"all"``. ``"required"`` installs the first-run required CLAP snapshot plus
    the Chatterbox voice model. CUE-DETR downloads only when a release/ops build
    provides an HTTPS artifact URL plus size/SHA pins. Otherwise that target
    reports an actionable manual setup error.
    """
    if target not in {"required", "clap", "chatterbox", "cue", "all"}:
        raise ValueError("target must be 'required', 'clap', 'chatterbox', 'cue', or 'all'")

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
    if target in {"required", "chatterbox", "all"}:
        if target_progress is None:
            results.append(install_chatterbox_model(force=force))
        else:
            results.append(install_chatterbox_model(force=force, progress=target_progress))
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
