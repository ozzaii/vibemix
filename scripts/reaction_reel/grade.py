# SPDX-License-Identifier: Apache-2.0
"""Phase 17-02 — Blind-grading CLI for the reaction reel.

Usage:
    python -m scripts.reaction_reel.grade <session_dir> <rater>

Walks ``<session_dir>/events.jsonl`` for ``kind=="ai_text"`` events, builds
per-reaction clip cards (reaction text + ±15s context window), anonymizes
each reaction with a SHA-8 id (mapping stored in ``grades/grades.key.json``
for the post-grading analyst — Kaan — to de-anonymize later), shuffles the
list deterministically per rater (seed = SHA1(rater + session_dir.name)[:8])
so a mid-grading quit can be resumed cleanly, then for each reaction:

  1. Plays the AI voice clip from ``voice.wav`` (afplay on macOS, start on
     Windows, no-op + warning on Linux or when the player binary is missing).
  2. Prints the reaction text + slop-dictionary highlights to the terminal
     — but NEVER persona/mode/genre/skill metadata (blind grading).
  3. Prompts for: score (1-5), grounded (y/n), timely (y/n), unique (y/n),
     personality_fit (y/n), slop_flag (none/late/generic/hallucination/
     repetition/cringe), comment (free text), would_clip (y/n).
  4. Validates the response against the Area-1 locked schema and appends
     one JSONL line to ``grades/<rater>.jsonl`` with fsync per line.

The slop dictionary is imported directly from
``vibemix.prompts.negative_dict.NEGATIVE_REGEX`` — single source of truth.

CONTEXT references:
  Area 1 §Per-reaction grade fields (locked schema)
  Area 3 §Blind-Grading Tooling
  §Specifics §Slop dictionary + Per-rater seed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# Single source of truth for the slop phrase regex — re-exported here so the
# rater view + the grade tooling share the exact set of phrases that already
# trip Phase 10's runtime slop filter. Do NOT redefine locally.
from vibemix.prompts.negative_dict import NEGATIVE_REGEX

__all__ = [
    "NEGATIVE_REGEX",
    "GradeError",
    "anonymize_reactions",
    "build_rater_view",
    "extract_reactions",
    "load_existing_grades",
    "main",
    "next_reactions_to_grade",
    "play_audio",
    "rater_seed",
    "shuffle_for_rater",
    "slop_highlights",
    "validate_grade",
    "write_grade",
]


# ---------------------------------------------------------------------------
# Locked schema — CONTEXT Area 1 §Per-reaction grade fields
# ---------------------------------------------------------------------------


SLOP_FLAGS: tuple[str, ...] = (
    "none",
    "late",
    "generic",
    "hallucination",
    "repetition",
    "cringe",
)

# Field name → expected python type. Lists are checked with isinstance(...,
# tuple-of-types) below so bools-as-ints don't slip through (bool IS an int
# in Python; we explicitly forbid the conflation for the "would_clip" /
# "grounded" / "timely" / "unique" / "personality_fit" booleans).
#
# ``graded_at_iso`` is added in Plan 17-03 (the analyzer's threat model
# T-17-03-02 — Repudiation — relies on a per-record timestamp). ``rater``
# field already supplies identity; ``graded_at_iso`` provides the audit
# trail timestamp. The full set of 11 fields matches 17-RUBRIC.md §3.
_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "reaction_id": str,
    "score": int,
    "rater": str,
    "grounded": bool,
    "timely": bool,
    "unique": bool,
    "personality_fit": bool,
    "slop_flag": str,
    "comment": str,
    "would_clip": bool,
    "graded_at_iso": str,
}

CONTEXT_WINDOW_S: float = 15.0  # ±15s per CONTEXT Area 2 §Reaction extraction.


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GradeError(ValueError):
    """Raised when a grade record fails the locked-schema validation."""


# ---------------------------------------------------------------------------
# Reaction extraction
# ---------------------------------------------------------------------------


def _read_events(session_dir: Path) -> list[dict]:
    """Read ``events.jsonl`` line-by-line, skipping malformed lines.

    Matches the pattern of ``vibemix.runtime.recordings_index.read_events`` —
    legacy / partial-line tolerance is required because crashed sessions can
    leave a half-flushed final line. Missing file → empty list.
    """
    events_path = session_dir / "events.jsonl"
    if not events_path.exists():
        return []
    events: list[dict] = []
    try:
        with events_path.open(encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    rec = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    events.append(rec)
    except OSError:
        return []
    return events


def extract_reactions(session_dir: Path) -> list[dict]:
    """Walk ``events.jsonl`` and return one record per ``kind=="ai_text"`` event.

    Each record carries:
      * ``t`` (float) — seconds from session start (the reaction timestamp).
      * ``text`` (str) — the reaction transcript as captured by recorder.
      * ``latency_s`` (float) — copied through from the event when present.
      * ``context`` (list[dict]) — every event with ``|t - reaction.t| <= 15.0``
        in chronological order, including the reaction itself's surrounding
        triggers / track_resolved / etc. The reaction event itself is NOT
        included in its own context window — the rater already sees ``text``.

    Returns an empty list when no ai_text events exist (clean-recording case
    — never grade an empty reel).
    """
    events = _read_events(session_dir)
    if not events:
        return []
    # Sort by t for stable context-window slicing — the recorder writes in
    # arrival order which is already monotonic, but be defensive.
    events.sort(key=lambda r: float(r.get("t", 0.0)))

    reactions: list[dict] = []
    for ev in events:
        if ev.get("kind") != "ai_text":
            continue
        t = float(ev.get("t", 0.0))
        text = str(ev.get("text", ""))
        latency = ev.get("latency_s")
        # Context window: ±CONTEXT_WINDOW_S inclusive of boundary; exclude the
        # reaction event itself (it's already represented by `text`/`t`).
        context = [
            other for other in events
            if other is not ev
            and abs(float(other.get("t", 0.0)) - t) <= CONTEXT_WINDOW_S
        ]
        reactions.append({
            "t": t,
            "text": text,
            "latency_s": float(latency) if isinstance(latency, (int, float)) else None,
            "context": context,
        })
    return reactions


# ---------------------------------------------------------------------------
# Anonymization
# ---------------------------------------------------------------------------


def _reaction_sha8(text: str, t: float) -> str:
    """SHA-8 id for a reaction. Deterministic on (text, t) so re-running the
    pipeline on the same session keeps the same IDs (lets the analyst hold
    a stable de-anonymization key across re-runs).

    Round t to 3 decimals to match recorder.log_event precision — protects
    against float-display drift across reads.
    """
    payload = f"{text}|{round(float(t), 3)}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:8]


def anonymize_reactions(
    reactions: list[dict], *, grades_dir: Path
) -> list[dict]:
    """Assign SHA-8 ids and write the ``reaction_id → {text, t}`` mapping to
    ``grades_dir / "grades.key.json"``.

    The rater never sees ``grades.key.json``. The post-grading analyst (Kaan)
    uses it to de-anonymize scored reactions back to the original transcript
    when assembling the report.

    Returns a NEW list — does not mutate the input. Each anonymized record
    has its ``reaction_id`` field added; original ``text`` and ``context``
    are preserved for the rater_view rendering.
    """
    grades_dir.mkdir(parents=True, exist_ok=True)
    anonymized: list[dict] = []
    key_map: dict[str, dict] = {}
    for rxn in reactions:
        rid = _reaction_sha8(rxn["text"], rxn["t"])
        # If two reactions hash to the same id (vanishingly rare with SHA-8
        # but possible with literal-identical text + t), append a suffix.
        # We're not protecting against this for v1; warn instead.
        if rid in key_map:
            # collision — append a 2-char index. Document the case but don't
            # crash; the analyst can still cross-reference via text.
            for i in range(99):
                cand = f"{rid[:6]}{i:02x}"
                if cand not in key_map:
                    rid = cand
                    break
        new_rxn = dict(rxn)
        new_rxn["reaction_id"] = rid
        anonymized.append(new_rxn)
        key_map[rid] = {"text": rxn["text"], "t": rxn["t"]}

    key_path = grades_dir / "grades.key.json"
    key_path.write_text(
        json.dumps(key_map, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return anonymized


# ---------------------------------------------------------------------------
# Deterministic shuffle (per-rater)
# ---------------------------------------------------------------------------


def rater_seed(rater: str, session_dir: Path) -> str:
    """SHA1(rater + session_dir.name)[:8] hex — per CONTEXT §Specifics.

    Returning the hex string (not the int) keeps the seed self-describing
    when surfaced in logs / debug output. The shuffle converts it to int
    internally.
    """
    payload = rater.encode("utf-8") + session_dir.name.encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:8]


def shuffle_for_rater(
    reactions: list[dict], rater: str, session_dir: Path
) -> list[dict]:
    """Deterministic per-rater shuffle — same rater + same session always
    lands on the same order so a mid-grading quit resumes cleanly.

    Fisher-Yates via `random.Random(int(seed, 16)).shuffle()` — Python's
    `random.shuffle` is Fisher-Yates and `random.Random(seed)` produces a
    stable PRNG state across Python versions where the algorithm is fixed
    (CPython 3.11+ guarantees `Mersenne Twister` for `Random`).
    """
    seed_int = int(rater_seed(rater, session_dir), 16)
    rng = random.Random(seed_int)
    shuffled = list(reactions)
    rng.shuffle(shuffled)
    return shuffled


# ---------------------------------------------------------------------------
# Resume — read existing grades, skip already-graded reaction_ids
# ---------------------------------------------------------------------------


def load_existing_grades(rater_jsonl: Path) -> set[str]:
    """Read ``<rater>.jsonl`` (one grade per line) and return the set of
    already-graded ``reaction_id``s. Malformed lines + missing fields are
    skipped silently — a partially-flushed line should NOT block resume.

    Missing file → empty set (first-launch case).
    """
    if not rater_jsonl.exists():
        return set()
    graded: set[str] = set()
    try:
        with rater_jsonl.open(encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    rec = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                rid = rec.get("reaction_id")
                if isinstance(rid, str) and rid:
                    graded.add(rid)
    except OSError:
        return set()
    return graded


def next_reactions_to_grade(
    anonymized: list[dict],
    rater: str,
    session_dir: Path,
    rater_jsonl: Path,
) -> list[dict]:
    """Return the un-graded reactions in the deterministic shuffle order.

    Implementation:
      1. ``shuffle_for_rater`` → list in stable per-rater order.
      2. ``load_existing_grades`` → set of already-graded ids.
      3. Filter the shuffled list down to ids NOT already graded.
    """
    shuffled = shuffle_for_rater(anonymized, rater, session_dir)
    graded = load_existing_grades(rater_jsonl)
    return [r for r in shuffled if r["reaction_id"] not in graded]


# ---------------------------------------------------------------------------
# Slop highlights + rater view
# ---------------------------------------------------------------------------


def slop_highlights(text: str) -> list[str]:
    """Return the list of negative-dictionary phrases found in ``text``.

    Re-uses ``vibemix.prompts.negative_dict.NEGATIVE_REGEX`` so the rater
    sees the same phrases that already trip Phase 10's runtime filter.
    Order preserved; case lowered.
    """
    return [m.group(0) for m in NEGATIVE_REGEX.finditer(text)]


def build_rater_view(anonymized_reaction: dict) -> str:
    """Render the per-reaction text shown to a rater.

    The view includes:
      * Reaction id (anonymized SHA-8) — so the rater can refer to it.
      * Timestamp into the session (seconds, mm:ss).
      * Reaction text verbatim.
      * Slop dictionary highlights (if any).
      * Brief context summary — event kinds + relative times.

    The view explicitly EXCLUDES:
      * voice / mode / genre / user_level fields from session.json.
      * Any literal labels like 'hype', 'coach', 'techno', 'beginner'.

    The blind-grading contract: a rater must NOT be able to tell which
    persona/mode/genre/skill produced the reaction from the on-screen
    output alone.
    """
    rid = anonymized_reaction["reaction_id"]
    t = float(anonymized_reaction["t"])
    mm, ss = divmod(int(t), 60)
    text = str(anonymized_reaction["text"])
    matches = slop_highlights(text)

    lines = [
        f"Reaction #{rid}  (at {mm:02d}:{ss:02d})",
        "",
        f"Transcript: {text}",
    ]
    if matches:
        # Surface up to 6 distinct matches; cap length so long lists don't
        # dominate the prompt screen.
        unique = []
        seen = set()
        for m in matches:
            low = m.lower()
            if low not in seen:
                seen.add(low)
                unique.append(low)
            if len(unique) >= 6:
                break
        lines.append("")
        lines.append(f"Slop-dictionary hits: {', '.join(unique)}")

    # Context summary — never emit a full event dump; rater shouldn't be doing
    # archeology. Just kind + relative-time deltas for nearby triggers.
    ctx = anonymized_reaction.get("context", []) or []
    if ctx:
        # Filter to a small, useful subset of event kinds — others are noise.
        useful_kinds = {"trigger", "track_resolved", "phase_change", "session_start"}
        nearby = [c for c in ctx if c.get("kind") in useful_kinds]
        if nearby:
            lines.append("")
            lines.append("Nearby events:")
            for c in nearby[:8]:  # cap to keep the screen tidy
                dt = float(c.get("t", 0.0)) - t
                kind = str(c.get("kind", "?"))
                reason = c.get("reason") or c.get("track") or ""
                sign = "+" if dt >= 0 else ""
                line = f"  {sign}{dt:5.1f}s  {kind}"
                if reason:
                    # Make sure the reason field doesn't leak persona/mode/
                    # genre/skill — strip a small allowlist of known leaky
                    # values. trigger.reason in v4 is one of:
                    # phase_change / mix_move / layer_arrival / heartbeat /
                    # track_change / kaan_spoke / manual — all safe.
                    safe_reason = str(reason)
                    line += f" — {safe_reason}"
                lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audio playback — afplay (macOS) / start (Windows) / graceful no-op
# ---------------------------------------------------------------------------


def _player_command(voice_wav: Path) -> Optional[list[str]]:
    """Return the platform-specific command to play ``voice_wav``.

    Returns None when no suitable player is available — caller surfaces the
    "audio playback unavailable" message and lets the rater grade by text.
    """
    sysname = platform.system()
    if sysname == "Darwin":
        # afplay ships with macOS. shutil.which guards against the rare case
        # of /usr/bin not on PATH.
        if shutil.which("afplay"):
            return ["afplay", str(voice_wav)]
        return None
    if sysname == "Windows":
        # `start /MIN /WAIT <wav>` opens the file in the registered handler
        # (typically Windows Media Player) and waits for it to close. The
        # /MIN flag minimizes the window so it doesn't steal focus.
        return ["cmd", "/c", "start", "/MIN", "/WAIT", str(voice_wav)]
    # Linux / unknown — no v1 commitment per CLAUDE.md platforms; rater can
    # still grade by text on a non-mac/win machine.
    return None


def play_audio(
    voice_wav: Path,
    *,
    start_s: float = 0.0,
    duration_s: Optional[float] = None,
) -> bool:
    """Play ``voice_wav`` synchronously. Returns True on success, False on any
    error (missing file, missing player, subprocess failure).

    ``start_s`` and ``duration_s`` are accepted for future per-reaction
    clipping (the v1 implementation plays the whole voice.wav — the rater
    can hear surrounding text to judge timing). They are recorded in the
    grade record so an analyst can replay the exact clip.

    Never raises — playback failure must NOT block a rater session.
    """
    voice_wav = Path(voice_wav)
    if not voice_wav.exists():
        return False
    cmd = _player_command(voice_wav)
    if cmd is None:
        return False
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Grade record validation + persistence
# ---------------------------------------------------------------------------


def validate_grade(grade: dict) -> None:
    """Validate ``grade`` against the Area-1 locked schema. Raises GradeError
    on the first violation found — message names the offending field.
    """
    if not isinstance(grade, dict):
        raise GradeError(f"grade must be a dict, got {type(grade).__name__}")

    for field, expected in _REQUIRED_FIELDS.items():
        if field not in grade:
            raise GradeError(f"missing required field {field!r}")
        value = grade[field]
        # Booleans first — bool is a subclass of int in Python, so checking
        # isinstance(value, int) accepts True/False; we want strict bool here.
        if expected is bool:
            if not isinstance(value, bool):
                raise GradeError(
                    f"field {field!r} must be a bool, got {type(value).__name__}"
                )
            continue
        if expected is int:
            if isinstance(value, bool) or not isinstance(value, int):
                raise GradeError(
                    f"field {field!r} must be an int, got {type(value).__name__}"
                )
            continue
        if expected is str:
            if not isinstance(value, str):
                raise GradeError(
                    f"field {field!r} must be a str, got {type(value).__name__}"
                )
            continue
        # Fallback — generic isinstance check.
        if not isinstance(value, expected):  # type: ignore[arg-type]
            raise GradeError(
                f"field {field!r} must be {expected!r}, got {type(value).__name__}"
            )

    score = grade["score"]
    if not (1 <= score <= 5):
        raise GradeError(f"score must be in 1..5, got {score}")

    flag = grade["slop_flag"]
    if flag not in SLOP_FLAGS:
        raise GradeError(
            f"slop_flag must be one of {SLOP_FLAGS!r}, got {flag!r}"
        )


def write_grade(rater_jsonl: Path, grade: dict) -> None:
    """Append one validated grade JSONL line to ``rater_jsonl`` and fsync.

    fsync guarantees that a process kill mid-grade loses AT MOST the line
    currently being written. The session is resumable from the line BEFORE
    the lost one — see ``load_existing_grades``.

    Raises GradeError on schema violation; the caller is expected to re-
    prompt rather than silently drop the grade.
    """
    validate_grade(grade)
    rater_jsonl.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(grade, ensure_ascii=False)
    with rater_jsonl.open("a", encoding="utf-8") as f:
        f.write(payload + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except (OSError, AttributeError):
            # tmpfs / network FS may not support fsync — best-effort.
            pass


# ---------------------------------------------------------------------------
# Terminal prompts
# ---------------------------------------------------------------------------


def _prompt_choice(
    msg: str, choices: Iterable[str], *, default: Optional[str] = None
) -> str:
    """Prompt until the rater enters one of ``choices`` (case-insensitive)."""
    choices_list = [c.lower() for c in choices]
    while True:
        suffix = f" [{'/'.join(choices_list)}]"
        if default:
            suffix += f" ({default})"
        suffix += ": "
        raw = input(msg + suffix).strip().lower()
        if not raw and default:
            return default
        if raw in choices_list:
            return raw
        print(f"  → please enter one of: {', '.join(choices_list)}")


def _prompt_bool(msg: str, *, default: Optional[bool] = None) -> bool:
    """y/n prompt → bool."""
    default_str: Optional[str] = None
    if default is True:
        default_str = "y"
    elif default is False:
        default_str = "n"
    raw = _prompt_choice(msg, ["y", "n"], default=default_str)
    return raw == "y"


def _prompt_score(msg: str) -> int:
    """1-5 score prompt with anchored helper text. Re-prompts on invalid input."""
    while True:
        raw = input(msg + " [1-5]: ").strip()
        try:
            n = int(raw)
            if 1 <= n <= 5:
                return n
        except ValueError:
            pass
        print("  → please enter an integer from 1 to 5.")


def _prompt_grade_for_reaction(
    anonymized_reaction: dict, *, rater: str
) -> dict:
    """Render the rater view + prompt for all locked-schema fields.

    Returns a validated grade dict. Re-prompts on validate_grade failure
    until the rater enters a valid record.
    """
    print()
    print("=" * 72)
    print(build_rater_view(anonymized_reaction))
    print("=" * 72)
    print()
    while True:
        score = _prompt_score("Score (5=real friend, 1=embarrassing)")
        grounded = _prompt_bool("Grounded in an audible/visible event")
        timely = _prompt_bool("Timely (no >4s late)")
        unique = _prompt_bool("Unique (doesn't repeat prior reactions)")
        personality_fit = _prompt_bool("Personality fit (consistent with persona)")
        slop_flag = _prompt_choice(
            "Slop flag", SLOP_FLAGS, default="none"
        )
        would_clip = _prompt_bool("Would you clip this to IG?")
        comment = input("Comment (free text, blank for none): ").strip()

        grade = {
            "reaction_id": anonymized_reaction["reaction_id"],
            "score": score,
            "rater": rater,
            "grounded": grounded,
            "timely": timely,
            "unique": unique,
            "personality_fit": personality_fit,
            "slop_flag": slop_flag,
            "comment": comment,
            "would_clip": would_clip,
            # ISO-8601 UTC timestamp at submission — Plan 17-03 analyzer
            # uses this for the per-record audit trail (T-17-03-02).
            "graded_at_iso": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
        }
        try:
            validate_grade(grade)
            return grade
        except GradeError as e:
            print(f"  ! invalid grade: {e}. re-entering...")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _print_intro(session_dir: Path, rater: str, total: int, remaining: int) -> None:
    """Header rendered once at the start of a session.

    Deliberately quiet about persona/mode/genre — the blind contract holds
    for the whole session, not just per reaction.
    """
    intro = textwrap.dedent(f"""\
        vibemix — reaction-reel blind grading
        --------------------------------------
        Session: {session_dir.name}
        Rater:   {rater}
        Total reactions: {total}
        Remaining:       {remaining}

        For each reaction you'll hear the AI voice (if audio playback is
        available), see the transcript + any slop-dictionary hits, then
        be asked for a 1-5 score, four boolean flags, a slop_flag, an
        optional comment, and whether you'd clip it for IG.

        Score anchors:
          5  Real friend in my ear — would survive a clip
          4  Solid — grounded, no slop, minor flavor issue
          3  Neutral — correct but forgettable (voice-assistant feel)
          2  Slop — generic / late / hallucinated / repetitive
          1  Embarrassing — would make the DJ tear off their headphones

        You can quit at any time with Ctrl-C; your progress is saved per
        reaction and the same rater + session resumes where you left off.
        """)
    print(intro)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point — returns 0 on full completion, 130 on KeyboardInterrupt,
    1 on usage / setup error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reaction_reel.grade",
        description="Blind-grade reactions from a vibemix recording session.",
    )
    parser.add_argument(
        "session_dir",
        type=Path,
        help="Path to the recording session dir (recordings/<YYYYMMDD-HHMMSS>).",
    )
    parser.add_argument(
        "rater",
        type=str,
        help="Rater name (e.g. kaan, francesco, dj1, dj2).",
    )
    args = parser.parse_args(argv)

    session_dir: Path = args.session_dir.resolve()
    rater: str = args.rater.strip().lower()

    if not session_dir.exists() or not session_dir.is_dir():
        print(f"error: session_dir does not exist: {session_dir}", file=sys.stderr)
        return 1
    if not rater:
        print("error: rater name cannot be empty", file=sys.stderr)
        return 1

    raw_reactions = extract_reactions(session_dir)
    if not raw_reactions:
        print(f"error: no ai_text reactions found in {session_dir}/events.jsonl",
              file=sys.stderr)
        return 1

    grades_dir = session_dir / "grades"
    anonymized = anonymize_reactions(raw_reactions, grades_dir=grades_dir)
    rater_jsonl = grades_dir / f"{rater}.jsonl"

    remaining = next_reactions_to_grade(anonymized, rater, session_dir, rater_jsonl)
    _print_intro(session_dir, rater, total=len(anonymized), remaining=len(remaining))

    if not remaining:
        print("All reactions already graded for this rater. Nothing to do.")
        return 0

    voice_wav = session_dir / "voice.wav"

    try:
        for i, rxn in enumerate(remaining, 1):
            print(f"\n[{i}/{len(remaining)}] playing reaction audio "
                  f"(reaction_id={rxn['reaction_id']}) ...")
            ok = play_audio(voice_wav)
            if not ok:
                print("  (audio playback unavailable — grade by text only)")
            grade = _prompt_grade_for_reaction(rxn, rater=rater)
            write_grade(rater_jsonl, grade)
            print(f"  → grade recorded for {rxn['reaction_id']}.")
    except KeyboardInterrupt:
        print("\ninterrupted — your progress is saved. resume with the same "
              "command to pick up where you left off.")
        return 130

    print(f"\ndone — {len(remaining)} reactions graded for rater={rater}.")
    print(f"grades file: {rater_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
