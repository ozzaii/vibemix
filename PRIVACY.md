# vibemix — Privacy Policy

vibemix runs on your machine. This policy describes what data it handles and
where that data goes. It applies to the open-source vibemix application.

## What stays on your machine

- **Library embeddings and search** — your track library is analyzed locally with
  the CLAP model. Embeddings and search indexes are stored under
  `~/.cache/vibemix/` and never leave your computer.
- **Recordings** — session recordings are written locally under
  `recordings/<session>/` with a default 7-day retention you can change or
  disable in Settings.
- **API keys** — if you bring your own key, it is stored in your operating
  system's keychain, not in plaintext config.
- **DJ profile and memory** — long-term profile data and the optional copilot
  memory store are local SQLite files. The memory recall feature is off by
  default.

## What is sent off your machine

The **live co-host** needs a cloud AI model to react to your set. While a session
is active, audio from your master output, periodic screen frames of your DJ
software, and MIDI controller events are streamed to Bravoh's proxy
(`api.altidus.world`), which forwards them to Google's Gemini model for
analysis. The spoken reaction is streamed back as audio.

- This data is analyzed **in flight** and is **not stored** on Bravoh's end.
- Streaming only happens while a live co-host session is running. The Library,
  set-prep, and offline features do not stream your audio.
- The optional Viber library agent can use your local Codex CLI login; that path
  is governed by your own Codex/OpenAI account terms.

## Telemetry

vibemix does not collect usage analytics by default. Any future telemetry will be
opt-in and documented here before it ships.

## Your controls

- Turn the live co-host off to stop all streaming.
- Change or disable recording retention in Settings.
- Remove local data by deleting `~/.cache/vibemix/` and the `recordings/` folder.

## Changes

Material changes to this policy will be reflected in this file in the public
repository. Questions: `kaan@bravoh.ai`.
