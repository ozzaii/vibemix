#!/usr/bin/env python3
"""Recover the Viber capability packet from the surviving workflow transcript
(the /tmp copy was wiped). Source: the synthesizer agent + journal JSONL of
workflow wf_ba32cbda-6f2. Writes the RECOVERED original markdown to disk;
the correction is applied separately so the recovery is auditable."""
import json
import html
import re
import sys

WF = ("/Users/ozai/.claude/projects/-Users-ozai-projects-dj-set-ai/"
      "05e3ff51-2a3d-4e73-b547-d07179932731/subagents/workflows/wf_ba32cbda-6f2")
SRCS = [WF + "/journal.jsonl", WF + "/agent-ad3d80a372555d032.jsonl"]
DEST = ("/Users/ozai/projects/dj-set-ai/.planning/packets/2026-06-01/"
        "viber-capability-exploration.RECOVERED.md")
HEADER = "# CODEX_READY: Viber Capability"

# Walk every JSON value in every line, collect strings containing the header.
candidates = []

def walk(o):
    if isinstance(o, str):
        if HEADER in o:
            candidates.append(o)
    elif isinstance(o, dict):
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)

for src in SRCS:
    try:
        with open(src, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    walk(json.loads(line))
                except Exception:
                    # line may itself contain the markdown as a raw substring
                    if HEADER in line:
                        candidates.append(line)
    except FileNotFoundError:
        print(f"[warn] missing {src}", file=sys.stderr)

if not candidates:
    print("[fatal] no candidate markdown found in transcripts", file=sys.stderr)
    sys.exit(2)

# Pick the longest candidate (the full packet, not a quoted fragment).
md = max(candidates, key=len)

# Normalize literal escapes that survived JSON-in-JSON nesting.
if "\\n" in md and md.count("\\n") > md.count("\n"):
    try:
        md = md.encode("utf-8").decode("unicode_escape")
    except Exception:
        md = md.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')

# Slice from the real header, drop any preamble.
idx = md.find("# CODEX_READY: Viber Capability")
if idx > 0:
    md = md[idx:]

md = html.unescape(md).rstrip() + "\n"

with open(DEST, "w", encoding="utf-8") as fh:
    fh.write(md)

print(f"[ok] recovered -> {DEST}")
print(f"[ok] chars={len(md)} lines={md.count(chr(10))}")
print(f"[ok] starts: {md[:58]!r}")
print(f"[ok] sections(## )={md.count(chr(10)+'## ')} residual_entities={md.count('&amp;')+md.count('&gt;')+md.count('&lt;')}")
