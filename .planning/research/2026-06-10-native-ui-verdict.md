# Native UI Rewrite — Verdict (2026-06-10)

**Question (Kaan):** the app is download-only, not a web app — should the Tauri/TS UI be rewritten in Swift or another native library, one-shot, before the expensive quality pass?

**Verdict: STAY ON TAURI + framework-free TS/CSS. Confidence 0.86.**
Adversarial panel: 3 advocate agents (full-Swift / best-cross-platform-native / stay-Tauri) each built their strongest case with live web research; an adversarial judge attacked all three and committed. Full case texts + judge output: `.planning/packets/2026-06-10/UI-QUALITY-AUDIT-FULL.json` (key `verdict`). This re-opens and re-confirms the 2026-06-05 NATIVE-UI-DECISION on fresh merits, not precedent.

## Why the rewrite loses

- **The premise is half-false.** There is no React to remove: the UI is framework-free vanilla TS (61.2k lines) + CSS (12.9k), sole runtime dep `three`. Tauri ships no Chromium — it renders in the system WebView. The "web tax" Kaan is pricing mostly isn't being paid.
- **Swift is secretly TWO rewrites.** SwiftUI does not exist on Windows; the Swift-on-Windows lane is toolchain-only (UI = write a second app against WinUI 3 via swift-winrt, whose flagship patron just exited). The binding macOS+Windows v1 charter makes "full native Swift" ~1.7–2× an already-fatal 4–7 month solo cost.
- **Best cross-platform candidate (Flutter) wins its bracket, loses the decision.** One GPU renderer on both platforms fits a zero-native-widget product — but the 2–4 month re-platform lands entirely on the launch schedule, and every documented UI failure traces to TS/Python wiring seams, none to a WebView limitation.
- **The rewrite torches the encoded product knowledge.** 37.9k test lines / 1,614 green tests pin shipped bug-fixes (idle≠fault guard, optimistic repaint, citation-gated UI, pill focus dance). The three.js organism has no Swift port path. Dual-maintenance limbo with no second engineer is the documented stall mode.
- **The genuine native gaps are reachable inside Tauri.** Vibrancy already ships (`pill_window.rs:112-117`); the non-activating fullscreen HUD has a documented in-shell recipe (tauri-nspanel / objc2 NSPanel subclass per `pill_window.rs:47-61` + NATIVE-UI-DECISION.md §4). WKWebView throttling hits occluded windows — the pill is by definition visible and on top.

## What was conceded to the Swift case (honest losses of staying)

The founder's instinct is right about WHERE the web stack is weakest: the floating HUD primitive, first-class OS materials (macOS 26 Liquid Glass), gig-laptop footprint of 8 webview surfaces, and MAS distribution (`macOSPrivateApi: true` is a MAS disqualifier — irrelevant for v1's signed DMG path). The ws-bus thin-client boundary keeps a **post-launch** native macOS surface unusually cheap — that exit hatch is deliberately kept open (condition 4).

## Judge's conditions (the work that makes "stay" excellent)

1. **Ship the non-activating pill NOW** — real NSPanel (`.nonactivatingPanel + .fullScreenAuxiliary + .canJoinAllSpaces`), acceptance-tested in the BUILT artifact over real fullscreen Rekordbox; zero focus-steal = pass. Watch the tauri-plugin-store geometry-save panic (plugins-workspace #1546).
2. **Stand up a Windows/WebView2 visual QA lane before launch** — pixel-verify the pink-mock surfaces (backdrop-filter, fonts, canvas perf) on WebView2; pair with acrylic/mica as the Windows vibrancy analog. Currently untested and Windows is v1.
3. **Budget the 8-surface webview footprint** on a gig-laptop profile — lazy-create secondary windows, destroy hidden surfaces, pause/decimate three.js when occluded; make UI RAM/CPU a tracked number.
4. **Keep the ws-bus/IPC seam UI-agnostic** — no Tauri-specific leakage into `messages.schema.json`/`IpcRouterBus`; this is the cheap exit hatch to a future native surface. Treat coupling PRs as regressions.
5. **Swift Liquid-Glass pill spike stays PARKED** behind NATIVE-UI-DECISION.md §5 gates; trigger only post-launch, only if the nspanel pill fails a felt-quality bar live, judged by A/B feel.
6. **Spend every reclaimed week on the real launch gates** — Sven friend-score, cold-start silence, fresh-user empty deck, go-live determinism. The toolkit question is settled precisely so this work gets the time.
7. MAS/private-API audit only if MAS ever becomes a goal — not a v1 item, not a rewrite justification.

**Judge's strongest counterargument against itself** (kept on the record): if the crate-path pill fails the by-feel test over fullscreen DJ software in the built artifact, "stay" didn't avoid the native work — it deferred it to post-launch, in public. Hence condition 1 ships first and gets the felt-quality bar.
