# tests/dist/fixtures — Synthetic Bundle Generation

Phase 18 Wave 1. These fixtures back `tests/dist/test_verify_binary.py`.

## Planted byte policy — NO REAL KEYS

Every "planted" byte sequence used by the verify-binary tests is an
**obviously-not-a-real-key shape sentinel** synthesised at test runtime
from a literal prefix + a single-character fill. They exist purely so
the scanner can match the pattern; they are not real keys, never were,
and are never committed to the tree as quoted strings.

The canonical sentinels:

| Pattern family | Sentinel                  | Bytes (Python literal)              |
|----------------|---------------------------|-------------------------------------|
| `aiza`         | `AIzaAAAAAAAAAAAAAAA...`  | `b"AIza" + b"A" * 35`               |
| `akia`         | `AKIAAAAAAAAAAAAAAAAA`    | `b"AKIA" + b"A" * 16`               |
| `ya29`         | `ya29.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | `b"ya29." + b"x" * 40` |
| `sk-`          | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`   | `b"sk-" + b"x" * 40`   |
| `generic39`    | `A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9T`       | hand-rolled 39-char run |

Even an over-eager regex like
`grep -RE "AIza[A-Za-z0-9_-]{35}" tests/dist/` will only ever match the
synthesis expression `b"AIza" + b"A" * 35` (which is shape, not value)
or the post-synthesis byte buffer that pytest holds in memory — never
a committed real-key literal.

## Allowlisted suffixes — generic-39 false-positive class

The `generic39` regex (`\b[A-Za-z0-9_-]{39}\b`) is a heuristic; binary
assets routinely contain random 39-char runs. For these suffixes the
generic-39 scan is suppressed (strict `AIza`/`AKIA`/`ya29`/`sk-` always
run):

- `.woff2`, `.woff`, `.ttf`, `.otf`  — font tables full of base64-ish
  glyph payload
- `.wasm`  — instruction stream looks like high-entropy ASCII
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.ico`, `.webp`  — compressed image
  payload
- `.mp3`, `.wav`, `.ogg`  — audio frames

## Synthetic PyInstaller archive

`fixture_pyinstaller_archive` builds a tiny valid CArchive in memory at
test time using `conftest._build_pyinstaller_archive_bytes`. The
in-house `_pyinstxtractor.PyInstArchive` reads the same format
(cookie + TOC + zlib payloads), so the round-trip test exercises the
real extractor — not a mock.

## Extending the fixtures

To add a new planted pattern:

1. Define an **obviously-fake** synthesis expression
   (`b"<prefix>" + b"<filler>" * <length>`).
2. Reuse the `make_fake_app` factory — plant the bytes via
   `planted_bytes=`.
3. Assert via `pattern.value` from `scripts.dist.verify_binary.Pattern`
   so the test stays in sync with the enum.
