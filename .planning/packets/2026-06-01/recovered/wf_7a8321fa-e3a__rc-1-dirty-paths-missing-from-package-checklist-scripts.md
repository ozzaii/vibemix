# RC=1: "Dirty paths missing from package checklist: scripts/eval/judge.py, tests/eval/test_judge_pro_rubric.py"

git diff --stat -- scripts/eval/judge.py tests/eval/test_judge_pro_rubric.py
# scripts/eval/judge.py               | 205 ++++++++++++++++++++++++++++++++----
# tests/eval/test_judge_pro_rubric.py |  90 +++++++++++++++-
# 2 files changed, 276 insertions(+), 19 deletions

uv run pytest tests/eval/test_judge_pro_rubric.py -v
# 14 passed in 1.06s
```

### Recommendation:

**CRITICAL** — Assign to a new **Package 16** (2-Judge Eval Gate) or fold into the existing Hold Lane audit lane before any git clean/stash. This is blocking infrastructure for rebuild evaluation rigor, not optional polish.
