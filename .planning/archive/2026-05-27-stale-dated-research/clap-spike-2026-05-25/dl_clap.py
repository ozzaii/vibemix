"""Robust background download of laion/larger_clap_music (the 777MB CLAP model).

History: stalled twice before — ~88M via the Xet backend, 0B via from_pretrained.
So: DISABLE Xet (the thing that stalled) and DISABLE hf_transfer → plain
resumable HTTP, which cleanly resumes the partial blobs already in the cache.
Retry loop survives a flaky connection; each snapshot_download call resumes
where the last left off (no re-download of completed blobs).
"""
import os
import time

# Must be set BEFORE importing huggingface_hub.
os.environ["HF_HUB_DISABLE_XET"] = "1"        # avoid the backend that stalled
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"  # plain resumable HTTP
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

from huggingface_hub import snapshot_download  # noqa: E402

REPO = "laion/larger_clap_music"

for attempt in range(1, 21):
    t0 = time.time()
    try:
        print(f"[attempt {attempt}] snapshot_download({REPO}) ...", flush=True)
        path = snapshot_download(REPO)
        print(f"DONE in {time.time() - t0:.0f}s -> {path}", flush=True)
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — resume-and-retry on any transient failure
        print(f"[attempt {attempt}] FAILED after {time.time() - t0:.0f}s: {e!r}", flush=True)
        time.sleep(8)

print("GAVE UP after 20 attempts", flush=True)
raise SystemExit(1)
