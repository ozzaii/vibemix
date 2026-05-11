# macOS ScreenCaptureKit — User Reference

Starting Phase 8, vibemix's macOS screen capture uses Apple's **ScreenCaptureKit** (`pyobjc-framework-ScreenCaptureKit`) instead of the older `mss` library. This page covers what you need (macOS 12.3+), what to expect on first run (a system permission prompt), and where to look if capture stops working.

## macOS minimum

**12.3+ is required.** ScreenCaptureKit was introduced at WWDC 2022 and ships with macOS 12.3 / 13 / 14 / 15. macOS 11 and older are **not supported** — this matches PROJECT.md's platform constraint.

The migration is forced by macOS 15.0 obsoleting `Quartz.CGWindowListCreateImageFromArray` (the API `mss` wraps internally). On macOS 14 and earlier the old path still works, but vibemix would silently fail on macOS 15+ without this migration. Hence Phase 8.

## What ScreenCaptureKit needs (one-time setup)

On the first launch where vibemix tries to capture screen frames, macOS pops the **Screen & System Audio Recording** permission prompt. Approving it adds vibemix to:

```
System Settings → Privacy & Security → Screen & System Audio Recording
```

The Phase 11 calibration wizard surfaces this proactively — the prompt fires during the friendly first-run flow, not mid-set.

## What stayed the same

`Quartz.CGWindowListCopyWindowInfo` still enumerates windows for the picker. That Quartz API is **not deprecated** — only `CGWindowListCreateImageFromArray` (the capture path) is. ScreenCaptureKit's `SCShareableContent` is heavier and async for what's essentially a synchronous list-windows query, so we kept the lightweight Quartz path. (Decision D-Enumeration API in Phase 8 CONTEXT.)

## What changed under the hood (for the curious)

Window-targeted capture uses `SCContentFilter.initWithDesktopIndependentWindow_` against the SCWindow whose ID matches the Quartz-enumerated `kCGWindowNumber`. `SCStream` delivers frames to an Objective-C delegate on a private dispatch queue; the delegate converts CMSampleBuffer → CVPixelBuffer → PIL → JPEG synchronously and pushes the bytes into the same thread-safe single-slot frame ring the old `mss` path used. The asyncio runtime reads via `latest()` at 1Hz.

**Privacy gate**: vibemix never captures full-screen. A specific window must be picked in the calibration wizard, no exceptions, no fallback. `capture(bounds=None)` raises. This is enforced by tests.

## Troubleshooting

- **"Screen capture stopped working after a macOS update"** — System Settings → Privacy & Security → Screen & System Audio Recording → make sure vibemix is checked. macOS sometimes resets these permissions on major version bumps.
- **"No window appears in the picker"** — confirm the DJ app is open and on the active Space. vibemix uses `kCGWindowListOptionOnScreenOnly` so off-screen windows don't appear.
- **"Permission prompt didn't appear"** — quit vibemix, delete the app from the privacy list (if present), re-launch. The prompt only fires on the FIRST `SCShareableContent.getShareableContentWithCompletionHandler_` call after a permission reset.
- **"macOS 11 user reports broken capture"** — not supported. Direct them to macOS 12.3 or later. (Same as PROJECT.md.)

## What's deferred to later phases

- **Phase 11 (Tauri Shell + Calibration Wizard)** owns the first-run UX — surfacing the permission prompt friendly-style, showing the picker, persisting the chosen window/app handle, and handling re-pick on app launch.
- **Phase 16 (Hallucination Verification Gate)** runs the first authoritative live screen-capture tests on real macOS 15 with a real Rekordbox / djay / Serato window.
- **Phase 20 (Day-Zero Operations)** repeats the live capture verification on a fresh macOS install (the "I just bought a new Mac" scenario).
- **System-audio capture via ScreenCaptureKit** is out of scope. Audio is owned by Phase 2's BlackHole/sounddevice path; ScreenCaptureKit's audio API is not used.
