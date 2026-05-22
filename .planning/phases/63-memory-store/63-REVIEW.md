---
phase: 63-memory-store
reviewed: 2026-05-22T07:20:45Z
depth: deep
files_reviewed: 4
files_reviewed_list:
  - src/vibemix/memory/__init__.py
  - src/vibemix/memory/index_sqlite_vec_memory.py
  - src/vibemix/memory/store.py
  - src/vibemix/memory/retention.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 63: Code Review Report

**Reviewed:** 2026-05-22T07:20:45Z
**Depth:** deep (cross-file: store ↔ backend ↔ retention ↔ reused library primitives)
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the Phase 63 v6.0 Memory Store storage spine: the vec0 backend clone
(`index_sqlite_vec_memory.py`), the `MemoryStore` facade (`store.py`), the
retention sweep (`retention.py`), and the barrel (`__init__.py`).

The high-value security and parity invariants hold and were verified
empirically (not just read):

- **Path-traversal defense is sound.** `_validate_session_id` rejects `..`,
  absolute paths, separators (`/`, `\`), NUL bytes, empty/`.` ids, and accepts
  legitimate `YYYYMMDD-HHMMSS` ids. The two-layer floor + `is_relative_to(root.resolve())`
  containment is correct, fires on **both** `add_record` and `delete_session`,
  and has no symlink/TOCTOU bypass (resolve() before compare; nothing touches FS
  on a bad id). Confirmed by direct probing.
- **SQL is fully parameterized.** No f-string/`%`/`.format` interpolation of
  `session_id`/`record_id`/`signature` reaches SQL — the only f-strings build
  `?`-placeholder lists, and the values are always passed as bound params. The
  `vec_library`→`vec_memory` + `track_id`→`record_id` rename is consistent (only
  docstring mentions of `vec_library` remain; no leftover identifiers in SQL).
- **`cosine_topk` is the only ranking path.** No `MATCH`, `vec_distance_cosine`,
  `ORDER BY distance`, or native vec0 KNN anywhere. `cosine_topk` is imported
  verbatim from `vibemix.library._cosine`, never forked. float32 + (768,) dtype
  discipline is preserved end-to-end (backend asserts, `cosine_topk` re-asserts,
  `np.stack(np.frombuffer(...))` round-trips to a writeable float32 array).
- **No-extraction / no-live-path by construction.** No `generate_content` /
  `generate_reply` / chat surface; no hardcoded `gemini-embedding-*` literal; no
  import of coach loop / MusicState / ws_bus / agent / prompts. The lazy
  `config_store` import is genuinely load-bearing — verified at runtime that
  `import vibemix.memory.store` leaves `sys.modules` CLEAN of the live path.
- **`delete_session` atomicity is correct on the sqlite-vec path.** The
  `moments` DELETE is staged on the shared `self.db` connection and the
  backend's `DELETE FROM vec_memory` + single `commit()` closes one transaction
  over both — no orphaned vectors. The numpy fallback's vector-after-metadata
  ordering leaves only a reconcilable orphan, swept by `reconcile_orphans`.
- **Retention is correct.** Oldest-session-first, whole-session eviction; the
  count pass stops at `len(survivors) - 1` so it never empties the store; the
  ∞-sentinel (both caps `None`) short-circuits without reading the store. No
  off-by-one. `app_data_dir()` (durable) is used, not `~/.cache`.

All 19 `tests/memory/` tests pass. No Critical findings. Three Warnings (an
inaccurate atomicity docstring claim, a connection leak on the sqlite-vec
fallback path, and a retention-caps default footgun) and four Info items below.

## Warnings

### WR-01: `add_record` docstring claims one-transaction atomicity that does not exist

**File:** `src/vibemix/memory/store.py:280-311` (esp. docstring 289-302; also `index_sqlite_vec_memory.py:122`)
**Issue:** The `add_record` docstring and the module/class docstrings repeatedly
state the vec0 vector + `moments` row are committed "inside one transaction
(single-writer, atomic)". This is false even on the sqlite-vec path.
`self._backend.add_batch(...)` calls `SqliteVecMemoryStore.add_batch`, which ends
with its **own** `self.db.commit()` (`index_sqlite_vec_memory.py:122`) **before**
`add_record` writes the `moments` row. So the sequence is: commit vector → write
moments row → commit moments. There are two commits, not one transaction. The
ordering is still vector-first (a crash between the two leaves a reconcilable
orphan vector, which is the documented-safe direction), so this is **not a
data-loss bug** — but the "atomic / one transaction" claim in the docstrings is
inaccurate and will mislead Phase 64/65 maintainers reasoning about crash
windows. (Contrast `delete_session`, which genuinely *is* one transaction on the
sqlite-vec path because it stages the moments DELETE and lets `backend.delete`'s
single commit close both.)
**Fix:** Correct the docstring to describe the real guarantee — "vector-first,
two commits; a crash between them leaves at worst a reconcilable orphan vector
(swept by `reconcile_orphans`), never a metadata row pointing at a missing
vector." Do not claim atomicity for `add_record`. (Optionally, if true single-
transaction add is wanted on the sqlite-vec path, drop the `commit()` from
`add_batch` and commit once in `add_record` — but that would diverge from the
shared backend contract `NumpyStore` can't honor, so the docstring fix is the
right call.)

### WR-02: sqlite-vec connection leaked when the extension probe fails (fallback path)

**File:** `src/vibemix/memory/index_sqlite_vec_memory.py:64-71`; `src/vibemix/memory/store.py:182-218`
**Issue:** `SqliteVecMemoryStore.__init__` opens `self.db = sqlite3.connect(...)`
(line 67) and then calls `sqlite_vec.load(self.db)` (line 71), which is the
documented re-raise point on a host with no extension wheel (Win ARM64,
Assumption A2 — the *expected* fallback path, not a rare error). When it raises,
`open_memory_store`'s `except Exception` (store.py:195) catches it and falls
through to `NumpyStore`, but the already-opened `self.db` connection is **never
closed** — the partially-constructed object is discarded with a live sqlite
handle. This leaks a connection (and a file handle on `memory.db`) every time the
fallback engages. On the single-shot boot path the impact is one leaked handle,
but the fallback can also be hit by tests instantiating many stores, and on
Windows an unclosed handle to `memory.db` can interfere with later
delete/replace. (This bug is inherited verbatim from the library's
`SqliteVecStore`, but it ships here in the documented-common fallback path.)
**Fix:** Guard the post-connect work so a failure closes the connection before
re-raising:
```python
def __init__(self, db_path: Path) -> None:
    self._db_path = Path(db_path)
    self._db_path.parent.mkdir(parents=True, exist_ok=True)
    self.db = sqlite3.connect(str(self._db_path))
    try:
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self.db.execute(...vec_memory...)
        self.db.execute(...moments...)
        self.db.execute(...idx_moments_session...)
        self.db.commit()
    except Exception:
        try:
            self.db.close()
        finally:
            raise
```

### WR-03: `MemoryStore.run_retention_sweep` overrides production caps with `None`, silently making boot calls a no-op

**File:** `src/vibemix/memory/store.py:430-448`; `src/vibemix/memory/retention.py:69-73`
**Issue:** `run_memory_retention_sweep` (the module function) defaults to the
real budget (`DEFAULT_MAX_MOMENTS=10_000`, `DEFAULT_MAX_AGE_DAYS=180`). But the
`MemoryStore.run_retention_sweep` method defaults **both** params to `None` and
passes them through **explicitly** (`max_moments=max_moments,
max_age_days=max_age_days`), which overrides the module defaults. So
`store.run_retention_sweep()` with no args hits the `(None, None)` ∞-sentinel and
is a **silent no-op** — it never bounds growth. The method is the ergonomic,
discoverable call surface (it's what the docstring at store.py:7-9 and the
"intended to run at boot" framing point a wiring author at), yet calling it the
obvious way does nothing. A downstream author wiring boot/session-close to
`store.run_retention_sweep()` (the natural choice over importing the module
function) would ship an unbounded-growth regression that no test catches (the
existing tests pass explicit caps). This is a real footgun for the deferred
call-site wiring, not a style nit. (T-63-10 "unbounded growth" depends on the
caller picking the right entry point.)
**Fix:** Make the method default to the production caps so the obvious call is
correct, e.g.:
```python
def run_retention_sweep(self, *, max_moments=DEFAULT_MAX_MOMENTS,
                        max_age_days=DEFAULT_MAX_AGE_DAYS):
    from vibemix.memory.retention import (
        DEFAULT_MAX_AGE_DAYS, DEFAULT_MAX_MOMENTS, run_memory_retention_sweep,
    )
    return run_memory_retention_sweep(self, max_moments=max_moments,
                                      max_age_days=max_age_days)
```
(The existing RED test that calls `store.run_retention_sweep(max_moments=10_000)`
and expects a no-op still passes, because it explicitly disables the age axis;
but verify the test's intent — if it asserts a no-op on a count-only call it is
encoding the footgun. Either way the no-arg call should bound growth.)

## Info

### IN-01: `SESSION_DIR_RE` is defined and documented but never used

**File:** `src/vibemix/memory/store.py:77-82`
**Issue:** `SESSION_DIR_RE = re.compile(r"^\d{8}-\d{6}$")` is declared with a
detailed comment claiming it is "Reused verbatim so a recordings-session id ...
is validated against the identical shape", but `_validate_session_id` never
calls `.match()` on it — validation is done by an ad-hoc substring/separator
check instead. The regex is dead code, and the comment overstates the actual
defense (memory ids are NOT shape-constrained to `YYYYMMDD-HHMMSS`; any
separator-free, non-`..`, non-NUL string is accepted). This is intentional per
the docstring ("the memory store does not require recordings ids"), so the
behavior is fine — but the unused symbol + the "validated against the identical
shape" claim are misleading.
**Fix:** Either drop `SESSION_DIR_RE` (and the "identical shape" wording), or
actually use it as an optional stricter check. Recommend deleting it and
trimming the comment to describe the floor that is actually enforced.

### IN-02: `add_record` does not validate `record_id` (empty/blank accepted as PK)

**File:** `src/vibemix/memory/store.py:280-311`
**Issue:** `session_id` is validated, but `record_id` is passed straight into the
vec0 PRIMARY KEY and the `moments` PRIMARY KEY with no shape check. An empty
string or whitespace `record_id` is accepted. This is not a security issue
(`record_id` never reaches the filesystem — it's only a SQL-bound param and a
vec0 key) and the `f"{session_id}:{seq}"` scheme is Phase 64's contract, but a
malformed/empty `record_id` would silently collide on the PK and corrupt
ordering. Low risk because the only writer is Phase 64.
**Fix:** Optionally add a cheap guard (`if not record_id or not
isinstance(record_id, str): raise ValueError`) so Phase 64 ingest bugs surface
loudly at the store boundary rather than as a silent PK overwrite.

### IN-03: Age-pass eviction can empty the store, unlike the count pass

**File:** `src/vibemix/memory/retention.py:119-137`
**Issue:** The count pass is carefully guarded to "never empty the store"
(`idx < len(survivors) - 1`, leaving the last session standing). The age pass has
no such guard — if every session's newest moment is older than `max_age_days`,
the age pass evicts **all** of them, leaving an empty store. This is defensible
(genuinely stale data should go) and is arguably correct, but it contradicts the
"a retention sweep must never empty the store" framing in the count-pass comment
(line 142-143) and the SUMMARY. Worth a one-line note so a future reader doesn't
assume the no-empty guarantee is global.
**Fix:** Add a comment on the age pass clarifying that age-based eviction is the
one path that may legitimately empty the store (truly stale install), in
contrast to the count pass.

### IN-04: `print()` to stdout for backend-selection diagnostics in a headless storage layer

**File:** `src/vibemix/memory/store.py:189-217` (5 `print(..., file=sys.stdout)` calls)
**Issue:** `open_memory_store` uses `print(..., file=sys.stdout, flush=True)` for
backend-selection logging in addition to `logger.warning`. This is copied
verbatim from `library/store.py`, so it matches house style, but a pure storage
spine emitting unconditional stdout lines (`-> memory store: backend=...`) on
every instantiation is noisy for a library that Phase 64/65 will call
repeatedly, and it's redundant with the `logger` call already present. Not a bug.
**Fix:** Consider dropping the `print()` calls and relying on the `logger`
(downgrade the `reason=ok` line to `logger.info`/`debug`), matching the
"structured event logging" convention. Low priority — consistent with the
library precedent.

---

_Reviewed: 2026-05-22T07:20:45Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
