# 51-02 SUMMARY — Dev-loop that reflects HEAD (env-gated source sidecar spawn)

**Requirements:** BRINGUP-04 (dev-loop)
**Status:** complete

## Env-gated resolver design (Bundled vs DevSource)

`resolve_sidecar_invocation(bundled, wizard_mode, manifest_parent, env)` is a
**pure, side-effect-free** function with the environment injected as a closure
(unit tests pass a fake map; it never reads `std::env`). It returns:

- `SidecarInvocation::Bundled(PathBuf)` when `VIBEMIX_DEV_SIDECAR` is absent —
  the shipped/release path, byte-identical to HEAD.
- `SidecarInvocation::DevSource { program, args, cwd }` when
  `VIBEMIX_DEV_SIDECAR == "1"` — runs the repo Python entrypoint so
  `cargo tauri dev` reflects `src/vibemix/` HEAD.

**Why it branches before `resource_dir()`:** the spawn loop computes `bundled`
lazily — under the dev flag it sets `bundled = None` and **never calls
`resolve_sidecar_path`** (which calls `resource_dir()`). That is the RESEARCH §2
landmine: `resource_dir()` errors / points at a non-existent bundle under
`cargo tauri dev`. Only the Bundled arm resolves it.

## Proof the release path is unchanged

- Unit test `resolve_sidecar_flag_absent_returns_bundled` pins flag-absent →
  `Bundled(path verbatim)`.
- The Bundled arm in the spawn loop is byte-identical to HEAD:
  `app.shell().command(&bin)` + optional `--wizard`. All downstream supervision
  (child publish, log drain, `exit_code==0` wizard→session handoff, exit-code
  sentinels 2=port-in-use / 3=audio-device-missing) is untouched — only the
  command-construction lines changed.
- `cargo check` is clean (no warnings); `cargo test` → **55 passed**.

## Shell-scope finding (no capability change needed)

The shell ACL (`capabilities/default.json` `shell:allow-execute`) only gates the
**JS-invoked** `plugin:shell|execute` command. Rust-side
`app.shell().command(program).spawn()` is a thin wrapper over the OS spawn with
**no scope check** (verified in `tauri-plugin-shell-2.3.5`: scope enforcement
lives in `commands.rs::execute`, not `process::Command::spawn`). So the dev
interpreter (`uv` / a custom python) spawns without widening any capability —
the shipped ACL is unchanged.

## Env contract + rebuild route

| Env var | Effect | Default |
|---|---|---|
| `VIBEMIX_DEV_SIDECAR=1` | spawn from source | unset → bundled |
| `VIBEMIX_DEV_PYTHON` | interpreter for `-m vibemix` | `uv` → `uv run python -m vibemix` |
| `VIBEMIX_DEV_REPO` | sidecar cwd (repo root) | `CARGO_MANIFEST_DIR` two hops up |

- Fast loop: `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev` (or
  `./scripts/dev/run_sidecar_from_source.sh` standalone).
- Rebuild route (prod fidelity): `uv run python scripts/build_sidecar.py
  --spec vibemix-core.macos.spec` then plain `cargo tauri dev`.

## Verification (observed)

- `cargo test --manifest-path tauri/src-tauri/Cargo.toml` → **55 passed**
  (6 new resolver tests + the existing 49).
- `cargo check` → clean, no warnings.
- `bash -n scripts/dev/run_sidecar_from_source.sh` → ok; git mode `100755`.
- `docs/dev-loop.md` references `VIBEMIX_DEV_SIDECAR`, `cargo tauri dev`,
  `scripts/build_sidecar.py`.

## Commits

- `535a271` feat(51-02): env-gated sidecar invocation resolver + unit tests.
- `6c2ce68` feat(51-02): spawn sidecar from source under VIBEMIX_DEV_SIDECAR=1.
- `298c9a3` docs(51-02): dev-loop source-spawn script + doc.
