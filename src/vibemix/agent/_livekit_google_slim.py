# SPDX-License-Identifier: Apache-2.0
"""Import only the LiveKit Google LLM submodule VibeMix uses.

``livekit.plugins.google.__init__`` eagerly imports Google Cloud STT/TTS,
which pulls grpc and the cloud speech/text-to-speech clients into local/demo
paths that only need Gemini LLM. These helpers install
package stubs with the real package search paths, then import the exact leaf
modules without executing the eager package initializer.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import sys
from types import ModuleType
from typing import Any


def _google_package_getattr(name: str) -> Any:
    if name == "LLM":
        return google_llm_class()
    if name == "__version__":
        module = importlib.import_module("livekit.plugins.google.version")
        return module.__version__
    if name == "EndpointingSensitivity":
        module = importlib.import_module("livekit.plugins.google.models")
        return module.EndpointingSensitivity
    raise AttributeError(f"module 'livekit.plugins.google' has no attribute {name!r}")


def _stub_package(name: str) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing

    spec = importlib.util.find_spec(name)
    if spec is None or spec.submodule_search_locations is None:
        raise ModuleNotFoundError(f"cannot locate package {name!r}")

    search_locations = list(spec.submodule_search_locations)
    package_spec = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    package_spec.origin = spec.origin
    package_spec.submodule_search_locations = search_locations

    module = ModuleType(name)
    module.__file__ = spec.origin
    module.__loader__ = None
    module.__package__ = name
    module.__path__ = search_locations
    module.__spec__ = package_spec
    if name == "livekit.plugins.google":
        module.__getattr__ = _google_package_getattr  # type: ignore[attr-defined]
    sys.modules[name] = module
    parent_name, _, child_name = name.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, child_name, module)
    return module


def _ensure_google_package_stubs() -> None:
    _stub_package("livekit.plugins.google")


def google_llm_class() -> type[Any]:
    _ensure_google_package_stubs()
    module = importlib.import_module("livekit.plugins.google.llm")
    google_pkg = sys.modules["livekit.plugins.google"]
    google_pkg.LLM = module.LLM  # type: ignore[attr-defined]
    return module.LLM
