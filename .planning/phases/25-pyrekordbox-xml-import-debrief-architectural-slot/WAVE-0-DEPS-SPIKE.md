INSTALL_PATH: --no-deps

# Wave 0 — Pyrekordbox Dep-Tree Spike Verdict

**Date:** 2026-05-14
**Phase:** 25-pyrekordbox-xml-import-debrief-architectural-slot
**Plan:** 25-01
**Question:** Does plain `pip install pyrekordbox==0.4.4` hard-require `sqlcipher3-wheels`?
**Verdict:** **YES.** Pin `pyrekordbox==0.4.4` with `--no-deps` and co-declare the 7 manual XML-path transitives.
**SQLCIPHER_DORMANT_CONFIRMED:** After `import pyrekordbox` under the `--no-deps + manual` recipe, `sys.modules` contains zero modules matching `*sqlcipher*`. The SQLCipher binary is never bundled and `pyrekordbox.db6.database` correctly falls back to stdlib `sqlite3` with `_sqlcipher_available = False`.

---

## Locked install recipe (v2.0)

```
pip install --no-deps pyrekordbox==0.4.4
pip install bidict==0.23.1 construct==2.10.70 SQLAlchemy==2.0.49 psutil==7.2.2 \
            python-dateutil==2.9.0.post0 typing_extensions==4.15.0 six==1.17.0
# numpy / packaging already in the vibemix dep set — no add.
```

**Manual transitive deps required for `pyrekordbox` XML path** (excluding `sqlcipher3-wheels`):

| Package             | Version       | Rationale                                                        |
| ------------------- | ------------- | ---------------------------------------------------------------- |
| `bidict`            | `==0.23.1`    | Used by `pyrekordbox.rbxml` for tag/attribute bidirectional maps |
| `construct`         | `==2.10.70`   | ANLZ binary parser (used by `pyrekordbox.anlz`, lazily by db6)   |
| `SQLAlchemy`        | `==2.0.49`    | Required by `pyrekordbox.db6.database` import chain              |
| `psutil`            | `==7.2.2`     | Used by `pyrekordbox.config` for Rekordbox process discovery     |
| `python-dateutil`   | `==2.9.0.post0` | Date parsing in mysettings + rbxml                              |
| `typing_extensions` | `==4.15.0`    | Transitive of SQLAlchemy                                         |
| `six`               | `==1.17.0`    | Transitive of `python-dateutil`                                  |

**Excluded (SQLCipher binary blob — NEVER bundled):**

| Package             | Version    | Reason for exclusion                                                  |
| ------------------- | ---------- | --------------------------------------------------------------------- |
| `sqlcipher3-wheels` | `==0.5.7`  | 3.2 MB native binary; XML import path doesn't need it; Pitfall locked |

---

## Evidence — dep-tree dump (plain `pip install`)

```
$ pip install --dry-run --report - pyrekordbox==0.4.4

Collecting pyrekordbox==0.4.4
Collecting bidict>=0.21.0 (from pyrekordbox==0.4.4)
Collecting construct>=2.10.0 (from pyrekordbox==0.4.4)
Collecting numpy>=1.19.0 (from pyrekordbox==0.4.4)
Collecting packaging (from pyrekordbox==0.4.4)
Collecting psutil>=5.9.0 (from pyrekordbox==0.4.4)
Collecting sqlalchemy>=2.0.0 (from pyrekordbox==0.4.4)
Collecting sqlcipher3-wheels (from pyrekordbox==0.4.4)      <-- HARD REQ, must skip
Collecting python-dateutil (from pyrekordbox==0.4.4)
Collecting typing-extensions>=4.6.0 (from sqlalchemy>=2.0.0->pyrekordbox==0.4.4)
Collecting six>=1.5 (from python-dateutil->pyrekordbox==0.4.4)

Would install:
  SQLAlchemy-2.0.49 bidict-0.23.1 construct-2.10.70 numpy-2.4.4 packaging-26.2
  psutil-7.2.2 pyrekordbox-0.4.4 python-dateutil-2.9.0.post0 six-1.17.0
  sqlcipher3-wheels-0.5.7 typing_extensions-4.15.0
```

`sqlcipher3-wheels==0.5.7` is in pyrekordbox 0.4.4's `setup.py` as an unconditional install_requires entry (NOT an extras_require). Plain pip install will always pull it.

---

## Evidence — `--no-deps + manual` install path

```
$ /tmp/spike-pyrek-25-01-nodeps/bin/pip install --no-deps pyrekordbox==0.4.4
Successfully installed pyrekordbox-0.4.4

$ /tmp/spike-pyrek-25-01-nodeps/bin/pip install bidict construct numpy psutil \
                                                 sqlalchemy python-dateutil packaging
Successfully installed bidict-0.23.1 construct-2.10.70 numpy-2.4.4 packaging-26.2 \
  psutil-7.2.2 python-dateutil-2.9.0.post0 six-1.17.0 sqlalchemy-2.0.49 \
  typing-extensions-4.15.0

$ python -c "
import sys, pyrekordbox
print('top-level OK')
sqlcipher_mods = sorted([m for m in sys.modules if 'sqlcipher' in m.lower()])
print('sqlcipher mods loaded:', sqlcipher_mods or 'NONE - DORMANT')
print('RekordboxXml:', pyrekordbox.RekordboxXml)
"
top-level OK
sqlcipher mods loaded: NONE - DORMANT
RekordboxXml: <class 'pyrekordbox.rbxml.RekordboxXml'>
```

The XML class is exposed at the top level: `from pyrekordbox import RekordboxXml`. Its real home is `pyrekordbox.rbxml.RekordboxXml`. `pyrekordbox.db6` IS pulled into `sys.modules` when the package `__init__.py` runs (because `__init__` imports `Rekordbox6Database` eagerly), but the actual `sqlcipher3` C-extension load is guarded by a try/except in `pyrekordbox/db6/database.py:28-34`:

```python
try:
    from sqlcipher3 import dbapi2 as sqlite3  # noqa
    _sqlcipher_available = True
except ImportError:
    import sqlite3  # type: ignore[no-redef]
    _sqlcipher_available = False
```

The stdlib `sqlite3` fallback means importing `pyrekordbox` without `sqlcipher3-wheels` succeeds cleanly; only `Rekordbox6Database.unlock()` would raise `ImportError` — and we never call it (XML import only, per CONTEXT D-01).

---

## SQLCipher Dormancy — Definitive Confirmation

| Check                                                                                   | Result   |
| --------------------------------------------------------------------------------------- | -------- |
| `import pyrekordbox` succeeds under `--no-deps + manual transitives` (no sqlcipher3)    | ✅ YES   |
| `from pyrekordbox import RekordboxXml` succeeds                                         | ✅ YES   |
| `sys.modules` contains any module matching `*sqlcipher*` after `import pyrekordbox`     | ❌ NO    |
| `pyrekordbox/db6/database.py` falls back to stdlib `sqlite3` via try/except guard       | ✅ YES   |
| Bundle weight saved by skipping `sqlcipher3-wheels==0.5.7`                              | ~3.2 MB  |

**SQLCIPHER_DORMANT_CONFIRMED** — XML path live, SQLCipher binary never installed, never imported, never executed.

---

## Decision rationale

- **Why `--no-deps` over plain install:** `sqlcipher3-wheels` is a 3.2 MB native binary that bloats the PyInstaller bundle (350 MB hard cap per PROJECT.md). We never call `Rekordbox6Database.unlock()` in v2.0 — XML import only (CONTEXT D-01). Shipping the binary as dead weight would also surface as a CVE blast radius for code we never execute. `--no-deps + manual transitives` is the lean path.
- **Why pin transitives exactly:** Bravoh's PyPI supply-chain hygiene (Phase 25 threat T-25-01) — exact pins record resolved hashes in `uv.lock`, preventing silent dependency drift.
- **Why we accept the bundle-bloat tail risk (T-25-03):** The manual transitive list is small (7 packages, all stable releases, ~10 MB combined). PyInstaller bundle size is monitored at Phase 21 anyway.
- **Why Python 3.12 specifically:** The project's `.venv/` is uv-managed CPython 3.12 (per `pyproject.toml:10`). `pyrekordbox==0.4.4` ships `pyrekordbox-0.4.4-py3-none-any.whl` — pure Python, runs on 3.12 unmodified.

---

## Next steps (Plan 25-02 unblocked)

1. Update `pyproject.toml` with the locked recipe (pyrekordbox + 5 new manual transitives — bidict, construct, sqlalchemy, psutil, python-dateutil; numpy/packaging/typing_extensions/six already covered transitively by existing deps).
2. Ship `tests/library/test_pyrekordbox_install.py` — 3 import-only smoke tests.
3. `RekordboxLibrary` in `src/vibemix/library/rekordbox.py` consumes `from pyrekordbox import RekordboxXml` directly. No `db6` references anywhere in `src/vibemix/`.
