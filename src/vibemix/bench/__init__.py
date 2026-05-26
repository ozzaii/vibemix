# SPDX-License-Identifier: Apache-2.0
"""vibemix.bench — the validation instrument (Phase 81 / One Mind milestone).

A dev/eval instrument, NOT a runtime feature. The harness is THIN COMPOSITION
over the real Phase 77-80 product seams: a :class:`~vibemix.bench.cell.BenchCell`
(one point in the model × grounding × prompting × contexting × lens × taste
matrix) → an assembler that builds ONE prompt by REUSING the shipped builders
(``build_lens_instruction`` / ``AICoach.build_prompt`` / ``build_parts_description``
/ ``model_router.resolve``) — never re-authoring prompt text — → a runner that
issues one injected-client ``generate_content`` per cell with a per-cell 429
fail-safe → a recorder that writes each cell verbatim.

The harness EXPRESSES the full 6-D matrix; the documented RUNS are the two
focused studies (``STUDY_A`` arch-axis, ``STUDY_B`` model-axis) + the decisive
no-audio cell (``NO_AUDIO_CELL``). The offline gate (fake client) is the
honest-green proof; the live run is one documented ``vibemix bench run`` command.
"""

from __future__ import annotations
