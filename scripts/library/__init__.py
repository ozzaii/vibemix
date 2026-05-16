# SPDX-License-Identifier: Apache-2.0
"""scripts/library/ — power-user library tooling.

Plan 41-05 introduces ``migrate_embeddings_2`` for explicit cache audit
and re-embed flows. The default migration UX is lazy-on-first-launch
(triggered by the LibraryEmbedder GA-rename probe naturally bumping
EXCERPT_STRATEGY_VERSION); this package is for power-users who want to
pre-warm or verify cache state explicitly.
"""
