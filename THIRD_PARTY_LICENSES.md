# Third-Party Licenses And Clean-Room References

This file records non-bundled upstream projects and public references whose
behavior is acknowledged by vibemix source comments. It is not the dependency
manifest; runtime dependency attributions live in `NOTICE`, and bundled-asset
attributions live in `NOTICE.md`.

## Clean-Room Algorithm References

The following vibemix modules are Apache-2.0 source files in this repository.
Their comments cite Mixxx behavior or source-file names as public references for
clean-room reimplementation. No Mixxx source files are bundled, vendored,
linked, or redistributed by these modules.

Upstream: Mixxx
License: GPLv2 or later, as stated by the Mixxx project.
Repository: https://github.com/mixxxdj/mixxx

| vibemix file | Reference cited in source comments |
| --- | --- |
| `src/vibemix/audio/cues.py` | Mixxx `AnalyzerSilence` audible-bound behavior and the -60 dB threshold. |
| `src/vibemix/audio/grid.py` | Mixxx `src/track/beats.cpp` constant-tempo beatgrid model. |
| `src/vibemix/audio/miniplayer.py` | Mixxx `EngineBufferScaleLinear::do_scale` block resampling behavior and `EngineXfader` equal-power gain behavior. |
| `src/vibemix/audio/xfade.py` | Mixxx `EngineXfader` constant-power crossfader behavior. |
| `src/vibemix/learn/beatmatch_judge.py` | Mixxx `BpmControl` and `SyncControl` beat-phase and tempo-fold behavior. |
| `src/vibemix/state/transition_clock.py` | Mixxx `AutoDJProcessor` transition-planning behavior. |

## Vendored Source And Optional Model References

The following third-party source or model references are used by local
inference paths. Runtime dependency attributions still live in `NOTICE`.

Upstream: OpenMOSS / MOSS-TTS-Nano
License: Apache-2.0, as stated by the OpenMOSS source repository and the
MOSS-TTS-Nano ONNX model cards.
Source repository: https://github.com/OpenMOSS/MOSS-TTS-Nano
ONNX model repository: https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX
Companion codec repository:
https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX

| vibemix file or asset | Treatment |
| --- | --- |
| `src/vibemix/agent/moss_tts/ort_cpu_runtime.py` | Vendored torch-free ONNX CPU runtime wrapper copied from OpenMOSS / MOSS-TTS-Nano under Apache-2.0. |
| `MOSS-TTS-Nano-100M-ONNX` and `MOSS-Audio-Tokenizer-Nano-ONNX` model trees | Optional local model cache or release-hosted archive for local MOSS speech. They are not bundled in the source tree or wheel by default; any bundled or hosted release archive must preserve Apache-2.0 attribution and the archive URL/SHA/size release pins. |

## Maintenance Rule

When a future source file cites an upstream project, standard, paper, or public
implementation as the basis for a clean-room algorithm, add the source file and
reference here in the same change. If copied or vendored code is ever introduced,
this file is not enough; the license, source-offer, and packaging treatment must
be reviewed as a separate release gate.
