# SPDX-License-Identifier: Apache-2.0
"""The live Judge producer — bridges the pure Judge to the running session.

`intel/transition_judge.py` is import-light (no registry, no recorder); this is
the thin orchestrator that runs it on a live frame and does the two side effects
the live loop needs: GROUND the verdict (write a resolvable ``[judge:]`` citation
so the co-host's voiced verdict atom survives the strip) and PERSIST it (a
``transition_judged`` row for debrief/replay/calibration).

Abstain-first by construction: on a JUDGED verdict it writes the citation + a
scored row; on an ABSTAIN it records the silence (calibration needs to see the
Judge correctly stay quiet) with NO citation and ``score=None``. Non-fatal — a
None registry/recorder never raises, so a producer hiccup can't wedge the loop.
"""
from __future__ import annotations

from typing import Any

from vibemix.intel.transition_judge import (
    TRANSITION_JUDGED_KIND,
    TransitionVerdict,
    judge_transition,
    verdict_event_fields,
)
from vibemix.state.live_signal import LiveSignalFrame

#: The citation source the co-host voices for a Judge verdict (see the 4-site
#: grammar lock in evidence_registry.py). Keep in sync with EVIDENCE_SOURCES.
JUDGE_CITATION_SOURCE = "judge"


def _verdict_citation_key(t_session: float) -> str:
    """The registry key (citation body) for a verdict at ``t_session``.

    Shape ``transition@<t>`` (1-decimal), matching the grammar's
    ``[judge:<verdict_id>]`` form. ``t_session`` is monotonic, so the key is
    unique per transition without threading a counter through the loop.
    """
    return f"transition@{round(t_session, 1)}"


def verdict_citation_id(t_session: float) -> str:
    """The fully-qualified citation id voiced for a judged transition."""

    return f"{JUDGE_CITATION_SOURCE}:{_verdict_citation_key(t_session)}"


def judge_and_record(
    frame: LiveSignalFrame,
    *,
    registry: Any | None = None,
    recorder: Any | None = None,
    track_a: str | None = None,
    track_b: str | None = None,
) -> TransitionVerdict:
    """Judge a live frame; ground + persist the verdict. Returns the verdict.

    ``registry`` is an ``EvidenceRegistry`` (or None); ``recorder`` exposes
    ``log_event(kind, **fields)`` (or None). Both judged and abstained verdicts
    persist — the abstain row is load-bearing (it proves the Judge stayed silent
    correctly). Only a judged verdict writes a citation.
    """
    verdict = judge_transition(frame)
    t = frame.t_session

    citation_id: str | None = None
    if verdict.verdict_state == "judged":
        key = _verdict_citation_key(t)
        if registry is not None:
            registry.write(JUDGE_CITATION_SOURCE, key, t)
        citation_id = verdict_citation_id(t)

    if recorder is not None:
        fields = verdict_event_fields(
            verdict, track_a=track_a, track_b=track_b, citation_id=citation_id
        )
        recorder.log_event(TRANSITION_JUDGED_KIND, **fields)

    return verdict
