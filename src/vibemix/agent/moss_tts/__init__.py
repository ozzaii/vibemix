# SPDX-License-Identifier: Apache-2.0
"""Vendored MOSS-TTS-Nano torch-free ONNX CPU engine.

`ort_cpu_runtime` is copied verbatim from OpenMOSS/MOSS-TTS-Nano (Apache-2.0).
It is the *only* MOSS module vibemix vendors — it imports just the stdlib +
numpy + onnxruntime, so it keeps the shipped local path torch-free (mirrors the
CLAP/CUE ONNX engines). The higher-level ``onnx_tts_runtime.OnnxTtsRuntime`` is
deliberately NOT vendored because it ``import torch`` at module load (only for
custom-reference-wav loading); built-in voices need no torch.

The vibemix-facing wrapper that turns this into a LiveKit ``TTS`` provider lives
in ``vibemix.agent.local_tts``. Model weights are NOT vendored — they are cached
under ``~/.cache/vibemix/moss-tts-onnx/`` (like the CLAP/CUE model caches).
"""

from vibemix.agent.moss_tts.ort_cpu_runtime import (
    CodecStreamingDecodeSession,
    OrtCpuRuntime,
    _resolve_stream_decode_frame_budget,
)

__all__ = [
    "OrtCpuRuntime",
    "CodecStreamingDecodeSession",
    "_resolve_stream_decode_frame_budget",
]
