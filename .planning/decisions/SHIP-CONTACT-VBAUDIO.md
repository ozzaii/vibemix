# §SHIP-CONTACT-VBAUDIO — VB-Audio OEM/bundle redistribution inquiry

**Status**: draft (Kaan-action — copy/paste + send)
**Audience**: VB-Audio Software (Vincent Burel) — `licensing@vb-audio.com` (primary), `contact@vb-audio.com` (fallback)
**Subject**: `VB-CABLE OEM redistribution inquiry — vibemix (Apache-2.0 OSS, indie macOS/Windows app)`
**Sender**: Kaan Özkan, founder / OZAI (`kaanozknn@gmail.com`)
**When to send**: independent of v3.1 ship — future Win install-flow optimization. Current install path (download at first launch via `installer/companion/fetch_drivers.ps1`) is legally clean and does NOT need this permission.

---

## Why send it

Today's Win flow downloads VB-CABLE on first launch from the official `vb-audio.com/Cable/` URL and runs the vendor-signed installer — that's a redirect, not redistribution, so we don't need a license. Long-term, bundling the driver inside the Inno Setup `.exe` would:

1. Cut first-launch latency (no internet dependency for offline DJs).
2. Lock the SHA at release time (no race between manifest pin + vendor re-upload).
3. Let SmartScreen reputation accumulate against a single signed installer instead of two.

OEM/bundle redistribution requires written agreement per the VB-Audio EULA. This email is the ask.

---

## Email body (copy verbatim)

```
Subject: VB-CABLE OEM redistribution inquiry — vibemix (Apache-2.0 OSS, indie macOS/Windows app)

Hello,

I'm Kaan Özkan, founder of OZAI. I'm preparing the v1.0 release of vibemix,
a free and open-source (Apache-2.0) AI co-host for live DJ sets — runs locally
on macOS and Windows, listens to the master output, talks back into the DJ's
headphones. Source: https://github.com/ozzaii/vibemix

VB-CABLE is the cleanest Windows option we found for capturing the DJ
software's master bus to feed into our local pipeline. We want users to have
the smoothest possible install, so I'd like to ask for explicit permission
to do one of the following:

  1. Bundle the official VB-CABLE Windows installer (VBCABLE_Driver_Pack43.zip,
     SHA-256 pinned in our manifest) inside our Inno Setup installer, invoking
     your installer with /S silent flag during our first-launch setup wizard.
     We would NOT modify, repackage, or re-sign the binary — we'd ship the
     official VB-Audio installer byte-for-byte, with attribution + EULA shown
     to the user before install.

  2. If full bundling is off the table: continue our current pattern of
     downloading VBCABLE_Driver_Pack43.zip from vb-audio.com/Cable/ on first
     launch (over HTTPS, SHA-256 verified), but with written acknowledgement
     that this fetch-and-install pattern is acceptable for a free OSS app.
     We're already doing this, so a short "yes that's fine" reply works.

For context, our distribution is small-scale (target audience ~500–2k DJs
in year one) and entirely non-commercial — vibemix is open source, Apache-2.0,
no paid tier. Our backing org (Bravoh) ships separately and is the legal
entity for vibemix releases.

I'm happy to:
  - Add a "Powered by VB-Audio Software — donate at vb-audio.com" banner in
    our install wizard.
  - Display the VB-CABLE EULA verbatim in the wizard before installing.
  - Link to your donation page from our first-run companion screen.
  - Share download stats if useful for your records.

If there's a paid OEM tier we should know about for an OSS project, please
let me know the terms.

Thanks for VB-CABLE — it's the only Windows option that doesn't make me want
to ship Mac-only.

Best,
Kaan Özkan
Founder, OZAI  /  vibemix maintainer
kaanozknn@gmail.com
https://github.com/ozzaii/vibemix
```

---

## After sending

1. File reply (or "no reply within 14 days" timestamp) under `.planning/decisions/SHIP-CONTACT-VBAUDIO-REPLY.md`.
2. If approved → open follow-up ticket to swap `fetch_drivers.ps1` from URL-fetch to bundled-binary mode + update Inno Setup `.iss` to ship the redistributable.
3. If denied or silent → keep the fetch-at-launch path; no v1.0 ship impact.

This carveout closes when (a) reply received OR (b) Kaan decides the optimization isn't worth the wait.
