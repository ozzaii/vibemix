# How to allow vibemix on Windows

When you launch vibemix on a fresh Windows 10 or 11 machine for the first
time, Microsoft Defender SmartScreen may show a blue dialog reading
**"Windows protected your PC"**. This is a normal step for any new app
distributed outside the Microsoft Store, and it does **not** mean
vibemix is unsafe — Defender simply hasn't seen the binary enough
times to trust it yet.

Phase 38 of the project ships a SignPath-signed installer. Once that
chain is live and Defender has seen enough downloads of the signed
binary (Microsoft calls this "reputation"), this prompt goes away on
its own. Until then, the steps below walk you through one-click
allow.

## What the prompt looks like

Screenshot placeholder — to be added when a real signed build lands:

> ![SmartScreen warning dialog](./windows-smartscreen-prompt.png)

The dialog has two visible buttons (**Don't run**, with a small
**More info** link in the top-right). The **Run anyway** button only
appears after you click **More info**.

## Step-by-step

1. When the SmartScreen dialog appears, click **More info** (top of the
   dialog, easy to miss).
2. The dialog expands and shows two lines:
   - **App:** `vibemix-setup.msi` (or `vibemix-setup.exe`)
   - **Publisher:** `Bravoh AG` once SignPath is wired; before Phase 38
     completes, this line may read **"Unknown publisher"** — that is
     expected.
3. Click **Run anyway**. The installer proceeds normally.

If you do not see the **More info** link, your organisation may have
configured a stricter SmartScreen policy. In that case, ask your IT
admin to allow `vibemix-setup` for your account — vibemix does not run
elevated and does not modify system audio drivers (BlackHole is a
separate optional install).

## Why this happens

Defender SmartScreen rates every binary it sees by how many users have
already run it. New binaries with low reputation trip the warning even
when they are correctly code-signed. The signed-and-trusted state can
take 1–2 weeks of normal download traffic to build up after a release.

## Will signing fix it?

Code-signing **reduces** the chance of seeing the prompt and removes
the "Unknown publisher" line. It does **not** guarantee the prompt
disappears on day one — Defender still applies the reputation cooldown
to brand-new signed certificates. We do not promise a warning-free
first launch.

## I clicked "Don't run". How do I retry?

Just double-click the installer again. SmartScreen will show the same
dialog and you can pick **More info → Run anyway** the second time.

## Related

- Phase 38 SignPath wiring (DIST-16): the long-term fix.
- macOS Gatekeeper guidance: see `docs/signing-macos.md` for the
  equivalent Mac flow.

## Honesty note

This document does not promise a warning-free install on Windows. The
real fix is reputation building up after Phase 38 ships, which takes
time and is outside our direct control.
