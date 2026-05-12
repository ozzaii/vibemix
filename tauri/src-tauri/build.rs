// Phase 11 Wave 2 — standard Tauri 2 build script.
//
// Keep this file minimal — Phase 11 plan explicitly bans "build.rs magic".
// Tauri's build script wires the embedded resources (icons, capabilities,
// tauri.conf.json5) and generates the gen/schemas/ directory the
// capability allowlist references via `$schema`.

fn main() {
    tauri_build::build()
}
