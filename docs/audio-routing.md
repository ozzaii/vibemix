# Audio Routing

How vibemix listens to your master output AND plays tutor exemplars on
headphones — three recipes from simplest to most advanced.

> **Status:** v9.0 ships Recipe 1 in the first-launch wizard. Recipes 2
> and 3 are documented setups; future wizard work may automate one or
> both (`§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` KAAN-ACTION).

## Goal

Beginner lessons play short audio examples ("the **low** band sounds like
**this**") — those exemplars need to come out somewhere. The live co-host
also needs to **hear** your master mix to react to it in real time.

So we have two audio paths:

- **Master mix → vibemix's ears** (so the AI can react grounded on real
  audio).
- **Tutor exemplars → your headphones** (so a beginner hears the
  demonstration audibly without it bleeding onto the club PA).

How those two paths share your sound card depends on your rig.

## Recipe 1 — Simple (default)

**For:** beginners on a laptop with one DJ controller and headphones.

The wizard's headphone-device picker (Step 2) routes tutor exemplars to
the output device you choose. Your DJ software keeps owning the master
output (whatever it was already pointed at).

Setup:

1. Plug in your headphones.
2. In the vibemix wizard, on Step 2 → "tutor exemplar playback
   (headphones)", pick your headphones from the dropdown.
3. Done. Tutor exemplars route to headphones; your DJ software keeps
   owning master output.

vibemix listens to master via the wizard's **master output device** pick
(BlackHole or whichever input device captures master — see Recipe 2 for
the macOS BlackHole flow).

## Recipe 2 — BlackHole loopback (vibemix needs to listen)

**For:** the live co-host. macOS only.

The live co-host has to *hear* your master mix. macOS doesn't expose a
loopback device by default, so we use BlackHole 2ch as the virtual
patch cable:

- DJ software output  →  BlackHole 2ch (vibemix listens here)
- DJ software output  →  Speakers / club PA (your audience hears here)

Setup:

1. Install BlackHole 2ch — the wizard does this for you on Step 2, OR
   from `https://existential.audio/blackhole`.
2. In your DJ software, pick BlackHole 2ch as the **master output** OR
   route master to both BlackHole 2ch AND your audience speakers via a
   Multi-Output Device (Recipe 3).
3. In the vibemix wizard, pick BlackHole 2ch on Step 2 as the input the
   co-host should listen to.

Tutor exemplars still route to the headphone device from Recipe 1 — the
two flows compose.

## Recipe 3 — Multi-Output Device (advanced)

**For:** users who want headphones to *also* carry the master mix (the
classic DJ "cue-listen" pattern) while vibemix listens to that same
master through BlackHole.

This is the deeper setup. macOS Audio MIDI Setup lets you create a
Multi-Output Device that mirrors one audio stream to several physical
outputs simultaneously:

- DJ master  →  Multi-Output Device  →  BlackHole 2ch (vibemix's ears)
                                    →  Headphones (you hear master)
                                    →  Audience speakers (audience hears master)

Setup:

1. Open **Audio MIDI Setup** (`/Applications/Utilities/Audio MIDI Setup.app`).
2. `+` button → "Create Multi-Output Device".
3. Tick the boxes for **BlackHole 2ch**, your headphones, and your
   audience output.
4. In your DJ software, set master output to the new Multi-Output
   Device.
5. In the vibemix wizard, master input = BlackHole 2ch (Recipe 2) and
   tutor exemplar output = your headphones (Recipe 1).

Caveats:

- Multi-Output Devices have **no master volume** in macOS — adjust each
  physical output's volume separately.
- Sample rate must match across every member device (Audio MIDI Setup
  will warn you if they drift).

## Windows

Recipes 2 and 3 don't apply on Windows the same way — vibemix uses
WASAPI loopback, which captures the system's master output directly
without a virtual patch cable. The wizard's master input pick is your
WASAPI loopback device. Headphone exemplar routing (Recipe 1) is
identical to macOS.

See `docs/windows-setup.md` for the WASAPI loopback flow.

## `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE`

The first-launch wizard automates Recipe 1 (headphone picker only).
Recipes 2 and 3 require user-side configuration in Audio MIDI Setup
(macOS) — the wizard surfaces a link to this document on the
relevant step but does not yet drive the OS-level setup automatically.

A future wizard plan may discharge this KAAN-ACTION by:
- Auto-detecting whether a Multi-Output Device already routes through
  BlackHole, and skipping the manual step when present.
- Surfacing a "create Multi-Output Device" affordance that walks the
  user through Audio MIDI Setup.

For v9.0, the user follows this doc by hand if they need Recipe 2 or 3.
