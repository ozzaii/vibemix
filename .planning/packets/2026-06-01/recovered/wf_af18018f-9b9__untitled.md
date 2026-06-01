I reproduced the finding in full. Every tool call succeeded this turn, including the cited grep and targeted reads.

## Verdict: CONFIRMED — holds=true

I independently re-ran the exact cited command and re-read every load-bearing line. The finding reproduces precisely.

### Evidence reproduced

**The double-guard (SettingsDrawer.ts:1201-1207)** — verbatim match to the claim:
- `1201-1203`: `if (!profilePanelHandle) { profilePanelHandle = renderProfilePanel({ autoload: false }); }`
- `1204-1207`: `if (ui.open && !profilePanelLoadedThisOpen) { profilePanelLoadedThisOpen = true; void profilePanelHandle.refresh(); }`

**Construction emits NO view (profile-panel.ts:451 + 253)** — confirmed. Line 253: `const autoload = options.autoload ?? true;` and line 451: `if (autoload) void refresh();`. Since the drawer passes `autoload: false`, the `?? true` default is overridden and `refresh()` is NOT called at construction. The claim cited line 451 as the autoload gate; reproduced exactly.

**refresh() -> fetchView() is the sole emitter (profile-panel.ts:215-221)** — confirmed. `fetchView()` is the only place `sendIpcRequest("ipc.profile.view", {}, "ipc.profile.view_result", ...)` fires (grep shows `ipc.profile.view` only at lines 217/219, inside `fetchView`). The module header comment at line 13 documents `outbound: ipc.profile.view → ipc.profile.view_result`.

**Module-level flags (SettingsDrawer.ts:771-772)** — confirmed: `let profilePanelHandle: ProfilePanelHandle | null = null;` / `let profilePanelLoadedThisOpen = false;`.

**disposeDrawerBodyResources does NOT reset the flags (873-884)** — confirmed. That function splices `bodyDisposers` and nulls `hotkeyHandle`, `retentionHandle`, `recordingBrowserHandle` only. It does NOT touch `profilePanelHandle` or `profilePanelLoadedThisOpen`.

**Flags reset ONLY in disposeProfilePanelHandle (886-892)** — confirmed: it nulls `profilePanelHandle` and sets `profilePanelLoadedThisOpen = false`. Called from `closeSettings()` (705) and `unmountSettingsDrawer()` (729). Reproduced both call sites.

**Mid-session refresh storm cannot re-fire** — confirmed by tracing the refresh path. `subscribeSettingsUI(() => handle.refresh())` at line 640; `handle.refresh()` (628-633) calls `renderDrawerBody`; `renderDrawerBody` re-enters the guard at 1204 but `profilePanelLoadedThisOpen` is already `true` (set at 1205 on first open, never reset by the body-render path), so the guard is false and no second `ipc.profile.view` fires. Recordings load (`loadRecordings`) and settings pushes route through the same subscriber, so they likewise cannot re-fire it.

### Adversarial probes that could have refuted it — all failed to

1. **`beginDrawerBodyRender` (901-905)** bumps `bodyRenderId` and calls `disposeDrawerBodyResources()` on every render — I checked whether it also resets the profile flag. It does NOT (it only delegates to `disposeDrawerBodyResources`, which leaves the profile flag untouched). So body re-renders do not re-arm the view. No refutation.
2. **`unmountSettingsDrawer` (727)** calls `disposeDrawerBodyResources()` AND `disposeProfilePanelHandle()` (729) separately — the flag reset on teardown comes from the latter, consistent with the claim. No refutation.
3. **`openSettings` (654-683)** — the closed→open transition is driven by `openSettingsState()` -> `subscribeSettingsUI` -> `refresh()`, with the comment at 664-666 confirming the state subscriber refreshes closed→open. On that first open-render, `profilePanelLoadedThisOpen` was reset to `false` by the prior `closeSettings()`, so the guard fires exactly once. The `if (wasOpen) mountedHandle.refresh()` at 666 is an idempotent re-open guard that hits the already-true flag — no extra view. No refutation.

### Classification: WIRED

`ipc.profile.view` -> `ipc.profile.view_result` is a real `sendIpcRequest` round-trip (profile-panel.ts:216-221) whose reply hydrates the panel (`reply.payload.profile/bytes/consent`, 222-226) — it live-applies data into the rendered panel, not echo/optimistic/dead. The request-hygiene property (exactly one view per open cycle, re-fires once on next open) holds as stated.

One scope note, not a refutation: the "exactly once per open" guarantee is enforced by the `closeSettings()` reset path (705). The view re-arms only when the drawer is closed via `closeSettings` or `unmountSettingsDrawer`. There is no code path that opens the drawer while bypassing a prior close, so the invariant holds for all reachable states. I already returned the structured verdict via the StructuredOutput tool (holds=true).
