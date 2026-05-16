# SPDX-License-Identifier: Apache-2.0
"""Spike scripts — out-of-runtime investigations gated from `src/vibemix/`.

This package is excluded from the Plan 41-01 grep gate
(`scripts/release/check_no_hardcoded_model.sh` scopes to `src/vibemix/`),
so spike scripts MAY carry model literals that are forbidden in runtime
code. Verify via `tests/repo/test_live_spike_scaffold.py`.
"""
