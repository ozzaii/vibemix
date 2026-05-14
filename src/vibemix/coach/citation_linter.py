# SPDX-License-Identifier: Apache-2.0
"""CitationLinter — Phase 20 response-level grounding gate.

The linter walks every parsed citation atom in a Gemini reply and validates
it against an EvidenceRegistry snapshot. Decision is **response-level
binary** (whole-utterance valid vs invalid). A single bad atom strips the
whole reply. The ``LintResult.missing`` tuple surfaces every miss for
telemetry, but the runtime decision in ``DJCoHostAgent.llm_node`` is binary.

This is NEVER per-atom partial-strip and NEVER token-level partial-strip
— v2.x territory only (CONTEXT Deferred Ideas).

The seven EBNF atom shapes (``ev`` / ``aud`` / ``midi`` / ``track`` /
``screen`` / ``mix`` / ``tend``) dispatch through ``_validate_atom``:

- ``ev`` / ``aud`` / ``midi`` — body MUST contain ``@``; split once and
  parse the trailing float as ``t``. Look up
  ``has(source, key, t, tol=LIVE_TOLERANCE_S)`` against the snapshot.
  Missing ``@`` or non-numeric ``t`` → MALFORMED.
- ``track`` / ``screen`` / ``mix`` / ``tend`` — body has no ``@t``;
  presence check on ``snapshot[source][body]`` only.
- Unknown source — already filtered out by the EBNF regex in
  ``parse_citations`` (the regex whitelists the 7 sources). The linter
  never sees them; the case is pinned by
  ``test_unknown_source_treated_as_no_citations``.

Stateless: a single CitationLinter instance is safe to share across all
DJCoHostAgent instances. The registry snapshot + tolerance flow per-call.

This module imports only stdlib (via ``parse_citations`` which itself uses
the stdlib ``re`` compiled regex). No third-party regex deps — the brief
locks this in <done> and the verification grep gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.coach.constants import DEBRIEF_TOLERANCE_S, LIVE_TOLERANCE_S
from vibemix.state.evidence_registry import EVIDENCE_SOURCES, parse_citations

# Sources where the body shape is ``key@t`` (time-keyed lookup with
# tolerance). The complement of this set inside EVIDENCE_SOURCES is the
# existence-only set (track / screen / mix / tend).
_TIME_KEYED_SOURCES: frozenset[str] = frozenset({"ev", "aud", "midi"})


@dataclass(frozen=True, slots=True)
class LintResult:
    """Frozen result of a single CitationLinter.check call.

    Fields:
        valid: True iff the response can be emitted as-is. Response-level
            binary — never partial.
        citations_found: Total parsed atoms across the response, valid +
            invalid combined. Surfaces emission-rate signal even on strip.
        missing: Tuple of ``(source, body)`` atoms that did NOT match the
            registry. Tuple-frozen for hashability + immutability.
        reason: One-word tag for telemetry / log routing. One of
            ``"valid"`` / ``"no_citations"`` / ``"invalid_atoms"`` /
            ``"malformed_atom"``. Per planner deviation #6 — promotes the
            decision tag to a first-class field instead of inferring from
            ``valid + missing`` at every log site.
    """

    valid: bool
    citations_found: int
    missing: tuple[tuple[str, str], ...]
    reason: str


class CitationLinter:
    """Stateless response-level citation grounding validator.

    Construction takes no args — the registry snapshot + tolerance band
    are passed per-call. The class is intentionally stateless so a single
    instance can serve every DJCoHostAgent across the lifetime of the
    process (parallel sessions, replay tests, etc.) with zero coupling.
    """

    def __init__(self) -> None:
        # Stateless on purpose. The class exists only to provide a typed
        # call site for `check()`; future telemetry / metrics hooks can
        # land here without touching every caller.
        pass

    def check(
        self,
        text: str,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
        *,
        mode: str = "live",
    ) -> LintResult:
        """Validate every citation atom in ``text`` against the snapshot.

        Args:
            text: The full LLM response — the WHOLE utterance, not a chunk.
                Per the response-level contract there is no streaming
                partial-validate path.
            registry_snapshot: A frozen snapshot from
                ``EvidenceRegistry.snapshot()``. ``None`` is treated as a
                defensive "nothing to ground against" state — returns
                ``no_citations``.
            mode: ``"live"`` (default, ±1.0s tolerance) or ``"debrief"``
                (±2.0s tolerance, Phase 25 architectural slot). Unknown
                modes raise ``ValueError`` — fail loud.

        Returns:
            A frozen ``LintResult``. The decision ladder mirrors the
            tasks-list spec:

            1. ``citations_found == 0`` → ``no_citations``.
            2. Any atom MALFORMED → ``malformed_atom``.
            3. Any atom invalid against registry → ``invalid_atoms``.
            4. All atoms valid → ``valid``.
        """
        # Mode dispatch — fail loud on unknown.
        if mode == "live":
            tol = LIVE_TOLERANCE_S
        elif mode == "debrief":
            tol = DEBRIEF_TOLERANCE_S
        else:
            raise ValueError(f"unknown mode: {mode!r} (expected 'live' or 'debrief')")

        # Defensive: no snapshot → nothing to ground against. Treat as a
        # cold-start state where the response cannot be verified — strip.
        if registry_snapshot is None:
            return LintResult(
                valid=False, citations_found=0, missing=(), reason="no_citations"
            )

        atoms = parse_citations(text)
        if not atoms:
            return LintResult(
                valid=False, citations_found=0, missing=(), reason="no_citations"
            )

        missing: list[tuple[str, str]] = []
        any_malformed = False
        for source, body in atoms:
            valid_atom, malformed = self._validate_atom(
                source, body, registry_snapshot, tol
            )
            if not valid_atom:
                missing.append((source, body))
            if malformed:
                any_malformed = True

        if any_malformed:
            reason = "malformed_atom"
        elif missing:
            reason = "invalid_atoms"
        else:
            return LintResult(
                valid=True,
                citations_found=len(atoms),
                missing=(),
                reason="valid",
            )

        return LintResult(
            valid=False,
            citations_found=len(atoms),
            missing=tuple(missing),
            reason=reason,
        )

    @staticmethod
    def _validate_atom(
        source: str,
        body: str,
        snapshot: dict[str, dict[str, tuple[float, ...]]],
        tol: float,
    ) -> tuple[bool, bool]:
        """Return ``(valid, malformed)``.

        ``malformed`` only surfaces for time-keyed atoms (ev/aud/midi)
        whose body is missing ``@`` or whose post-``@`` substring is not
        a float. Existence-only atoms (track/screen/mix/tend) cannot be
        malformed in v2.0 — their body shape is free-form.

        Unknown sources should never reach here (parse_citations regex
        whitelists EVIDENCE_SOURCES) but if they do, treat as malformed
        so the strip path catches them rather than silently passing.
        """
        if source not in EVIDENCE_SOURCES:
            # Defensive — parse_citations regex already whitelists, but a
            # future change there must not silently weaken the linter.
            return (False, True)

        if source in _TIME_KEYED_SOURCES:
            if "@" not in body:
                return (False, True)
            key, _, t_str = body.partition("@")
            try:
                t_target = float(t_str)
            except ValueError:
                return (False, True)
            times = snapshot.get(source, {}).get(key, ())
            valid = any(abs(t_obs - t_target) <= tol for t_obs in times)
            return (valid, False)

        # Existence-only sources — track / screen / mix / tend.
        valid = body in snapshot.get(source, {})
        return (valid, False)
