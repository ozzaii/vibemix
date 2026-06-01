#!/usr/bin/env python3
"""Recover EVERY Claude-produced workflow document from the surviving session
transcripts (the /tmp copies were wiped by macOS /tmp rotation).

Schema (verified): each workflow journal.jsonl has `type=result` lines with a
`result` string field = that agent's return. The synthesizer's result is the
final markdown doc. We pick, per workflow, the result string that looks most
like a finished document (top-level `# ` heading, most `## ` sections, longest).
Output -> .planning/packets/2026-06-01/recovered/. Writes only under that dir."""
import json
import html
import os
import re

WFROOT = ("/Users/ozai/.claude/projects/-Users-ozai-projects-dj-set-ai/"
          "05e3ff51-2a3d-4e73-b547-d07179932731/subagents/workflows")
OUT = "/Users/ozai/projects/dj-set-ai/.planning/packets/2026-06-01/recovered"
os.makedirs(OUT, exist_ok=True)


def maybe_unwrap(s: str) -> str:
    """If a result is double-encoded JSON ({"markdown":"..."} as a string),
    unwrap to the markdown."""
    t = s.lstrip()
    if t.startswith("{") and '"markdown"' in t[:200]:
        try:
            o = json.loads(t)
            if isinstance(o, dict) and isinstance(o.get("markdown"), str):
                return o["markdown"]
        except Exception:
            pass
    return s


def clean(s: str) -> str:
    s = maybe_unwrap(s)
    # If newlines are still escaped (rare double-encode), expand them.
    if s.count("\\n") > s.count("\n") and s.count("\\n") > 5:
        try:
            s = s.encode("utf-8", "ignore").decode("unicode_escape")
        except Exception:
            s = (s.replace("\\n", "\n").replace("\\t", "\t")
                  .replace('\\"', '"').replace("\\\\", "\\"))
    return html.unescape(s)


def score(md: str):
    """(has_h1, length) — prefer a titled doc, then the LONGEST. Length dominates
    over section-count so a full map never loses to a short titled fragment."""
    has_h1 = 1 if re.search(r"(?m)^# \S", md) else 0
    return (has_h1, len(md))


def title_of(md: str) -> str:
    m = re.search(r"(?m)^# (.+)$", md)
    return (m.group(1).strip() if m else "untitled")[:90]


def slug(t: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return (s[:55] or "untitled")


def assistant_texts(o):
    """Pull text from ASSISTANT messages only (exclude user/input blobs that
    embed the lane JSON + target structure)."""
    msg = o.get("message") if isinstance(o.get("message"), dict) else o
    role = msg.get("role") or o.get("role") or o.get("type")
    if role != "assistant":
        return []
    c = msg.get("content")
    out = []
    if isinstance(c, str):
        out.append(c)
    elif isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                out.append(b["text"])
            elif isinstance(b, str):
                out.append(b)
    return out


rows = []
for d in sorted(os.listdir(WFROOT)):
    wd = os.path.join(WFROOT, d)
    if not d.startswith("wf_") or not os.path.isdir(wd):
        continue
    j = os.path.join(wd, "journal.jsonl")
    candidates = []
    # source 1: journal result strings
    if os.path.exists(j):
        with open(j, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if isinstance(o, dict) and isinstance(o.get("result"), str):
                    candidates.append(o["result"])
    # source 2: assistant messages across every agent transcript (the doc often
    # lives here, not in a journal result)
    for fn in os.listdir(wd):
        if not (fn.startswith("agent-") and fn.endswith(".jsonl")):
            continue
        with open(os.path.join(wd, fn), encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if isinstance(o, dict):
                    candidates.extend(assistant_texts(o))
    # clean + slice each candidate from its first top-level heading
    docs = []
    for c in candidates:
        cc = clean(c)
        m = re.search(r"(?m)^# \S", cc)
        if m:
            cc = cc[m.start():]
        docs.append(cc.rstrip())
    docs = [x for x in docs if len(x) > 600]
    if not docs:
        rows.append((d, "-", 0, "(no document-shaped result)"))
        continue
    # dedup by content
    seen, uniq = set(), []
    for x in sorted(docs, key=len, reverse=True):
        key = x[:200]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(x)
    best = max(uniq, key=score)
    t = title_of(best)
    fn = f"{d}__{slug(t)}.md"
    with open(os.path.join(OUT, fn), "w", encoding="utf-8") as fh:
        fh.write(best + "\n")
    rows.append((d, fn, best.count("\n") + 1, t))
    # ALSO save any OTHER substantial distinct titled doc in this workflow
    # (a workflow can carry more than one real document) — never silently drop.
    alt_i = 0
    for x in uniq:
        if x is best:
            continue
        if x.count("\n") + 1 >= 90 and title_of(x) != t and title_of(x) != "untitled":
            alt_i += 1
            at = title_of(x)
            afn = f"{d}__ALT{alt_i}__{slug(at)}.md"
            with open(os.path.join(OUT, afn), "w", encoding="utf-8") as fh:
                fh.write(x + "\n")
            rows.append((d + f" alt{alt_i}", afn, x.count("\n") + 1, at))

print(f"{'workflow':18} {'lines':>6}  title")
print("-" * 100)
ok = 0
for wf, fn, lines, t in rows:
    if fn == "-":
        print(f"{wf:18} {'--':>6}  {t}")
    else:
        ok += 1
        print(f"{wf:18} {lines:6d}  {t}")
print()
print(f"RECOVERED {ok}/{len(rows)} workflows as document-shaped markdown -> {OUT}/")
