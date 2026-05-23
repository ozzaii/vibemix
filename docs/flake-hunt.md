# vibemix — Flake-Hunt Protocol

> Reproducible 10× consecutive `pytest -q` loop that surfaces non-deterministic
> tests before they land in the green badge. A flaky test hidden inside CI is
> worse than a known-red one — it teaches contributors that "re-run until green"
> is normal. This doc is how we keep that drift out of the tree.

## Why

TEST-03 says: any test that fails on a 10× consecutive re-run (i.e. < 100% pass
rate) is either **stabilised via test surgery** or **quarantined behind
`@pytest.mark.flaky` + a linked GitHub issue**. The default is surgery — quarantine
is the escape hatch when the non-determinism is genuinely external (a timing
edge in a Gemini API mock, an OS scheduler quirk on hosted runners) and the fix
is non-trivial.

The 10× hunt proves a test is actually deterministic. The static gate at
`tests/repo/test_no_silent_flakes.py` enforces that every `@pytest.mark.flaky`
carries a `# issue: https://github.com/.../issues/N` comment within 3 lines
above it — but only a repeated run reveals which tests need that marker.

## Run the hunt

From the repo root, with `uv` and the project's `.venv` already provisioned:

```bash
set -euo pipefail
for i in $(seq 1 10); do
  echo "=== Run $i/10 ==="
  uv run pytest -q --tb=line || exit 1
done && echo "10× GREEN — flake-hunt clean"
```

Wall-clock budget: ~36 minutes on Kaan's Mac (3.6 min × 10). Background the
loop if you need the terminal. If any iteration exits non-zero, the `|| exit 1`
clause stops the hunt immediately — re-run the failing test in isolation with
`uv run pytest <path>::<test_id> -v` 5× to characterise whether it's a real
race or a one-off blip.

## When to run

- **Before opening a PR that touches `tests/` or any shared fixture.** A new
  fixture race surfaces on its own commit, not three months later when an
  unrelated PR's CI run goes red.
- **Quarterly across the full suite.** Even unchanged code can drift flaky as
  dependencies update (a timing-sensitive mock, a CPython scheduler change).
  Pick a Sunday, run the hunt, sign off in `KAAN-ACTION-LEGAL.md §V7-LIVE-06`
  (the re-baseline discharge surface).
- **Before each `v0.x.0` release tag.** The release badge promise is "the
  tests on `main` are deterministic" — verify that's still true at every cut.

## If a test fails on run N but passed on N-1

**Default: surgery, not quarantine.** Read the failing test. Identify the
non-determinism source: timing assumption, hash ordering, fixture leak, a
network call that snuck past a mock, an `asyncio` loop that wasn't drained.
Fix it. Re-run the 10× hunt to confirm. Most flakes are 5-minute fixes once
the cause is named.

**If surgery is non-trivial or the flake is genuinely external** (a Gemini API
mock that 1-in-N hits a real edge, a hosted-runner CPU spike that breaks a
strict timing assertion): quarantine it.

1. Open a GitHub issue at <https://github.com/bravoh-ai/vibemix/issues/new>
   titled `Flake: <test_id> non-deterministic`. Body: which iteration failed,
   one-paragraph characterisation, what surgery you tried and why it didn't
   hold.
2. In the test file, add the decorator + adjacent issue link:

   ```python
   # issue: https://github.com/bravoh-ai/vibemix/issues/N
   @pytest.mark.flaky
   def test_known_flaky_thing():
       ...
   ```

   The `# issue:` comment must live within 3 lines above the decorator —
   `tests/repo/test_no_silent_flakes.py` AST-walks the tree and fails CI if
   it doesn't.

3. Do **NOT** add `(reruns=N)` arguments. The `flaky` marker is pure tagging,
   not auto-retry. The repo intentionally does not install `pytest-rerunfailures`
   or `pytest-repeat` — chasing green via reruns masks non-determinism instead
   of fixing it.

**Anti-pattern.** Do not increase `reruns=N` past 3 to mask non-determinism.
If a test needs more than 3 reruns to pass, it's not flaky — it's broken.
Surgery or quarantine; nothing in between.

## Autonomous-mode bridge

Under `gsd-autonomous fully`, `gh issue create` may be unavailable (auth
absent, rate limit, network drop). The gate still has to hold — so the
`# issue:` URL points at a placeholder
(`https://github.com/bravoh-ai/vibemix/issues/PENDING-FLAKE-NN`) and a
matching `§V7-LIVE-NN` entry in `KAAN-ACTION-LEGAL.md` captures the failing
test, the iteration count, the suspected cause, and a "create GH issue:
<title>" line for Kaan to discharge later. The P03 gate checks URL shape
only, not issue existence — bridge is intentional, not a loophole.

## See also

- `tests/repo/test_no_silent_flakes.py` — the static gate that enforces the
  `# issue:` adjacency.
- `tests/repo/test_no_silent_skips.py` — sibling gate for skip/skipif/xfail.
- `KAAN-ACTION-LEGAL.md §V7-LIVE` — the discharge surface for both per-test
  quarantine bridges and the periodic re-baseline.
