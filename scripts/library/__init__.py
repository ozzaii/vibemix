# SPDX-License-Identifier: Apache-2.0
"""scripts/library/ — power-user library tooling.

``migrate_embeddings_2`` is a legacy Gemini cache audit/cleanup helper. Current
product library embeddings use local CLAP ONNX via ``embed_factory.build_embedder``;
this package is not part of the normal model-install or re-embed path.
"""
