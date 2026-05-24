<!-- SPDX-License-Identifier: Apache-2.0 -->
# Bring Your Own Gemini API Key

vibemix's default mode (`direct`) already runs against your own Gemini key
when `GEMINI_API_KEY` is set in the environment. This doc walks the BYO path
end-to-end on macOS / Windows / Linux: where to get a key, where to put it,
how to verify the client builds, and how to switch back to the Bravoh proxy
if you change your mind.

## Why BYO

By default, vibemix routes coach prompts through the Bravoh proxy at
`api.altidus.world` so contributors can try the co-host without setting up
a Google AI Studio account. BYO mode skips the proxy entirely — your prompts
go direct to `generativelanguage.googleapis.com`. You want this when:

- **Privacy.** Your evidence packets (audio summaries, MIDI moves, deck
  state) go straight to Google under their TOS — no Bravoh telemetry hop,
  no per-install UUID, no aggregated usage logging on the Bravoh side.
- **Cost.** You spend your own Gemini quota / billing rather than the
  rate-limited free Bravoh pool. Useful if you push past the free-tier
  request budget during a long set.
- **Control.** You pick the Gemini model and region, you see Google's raw
  429 / quota errors directly, and you cut one network hop of latency.

## Get a Gemini API key

Gemini API keys are minted from Google AI Studio. The current free tier is
enough to drive a few practice sessions per day, but real DJ-set use will
push you onto paid quota fast.

1. Open <https://aistudio.google.com/apikey> in a browser and sign in with
   a Google account.
2. Click **Create API key**. Pick an existing Google Cloud project, or let
   AI Studio create a fresh one.
3. Copy the key. It starts with `AIza...` and is roughly 39 characters.
4. Check the free-tier note on the same page — Gemini's free tier is
   currently capped around 50 requests/day per project on certain models,
   and the cap moves; rely on the AI Studio dashboard, not this doc.

Keep this key secret — anyone with it can spend your quota.

## Set the env vars

vibemix reads two environment variables for BYO mode:

- `VIBEMIX_LLM_MODE` — `direct` is the default, so setting it is a
  belt-and-braces clarity move rather than strictly required. Set it to
  `proxy` to opt in to the Bravoh proxy.
- `GEMINI_API_KEY` — the key you minted in the previous step.

Pick the row for your OS and paste into the matching shell rc-file (or
PowerShell profile) so the values survive a reboot.

| Platform | Where to put it | Lines to add |
| -------- | --------------- | ------------ |
| **macOS** | `~/.zshrc` (or `~/.zprofile`) | `export VIBEMIX_LLM_MODE=direct`<br>`export GEMINI_API_KEY=AIza...your-key...` |
| **Linux** | `~/.bashrc` (or `~/.profile` for non-bash shells) | `export VIBEMIX_LLM_MODE=direct`<br>`export GEMINI_API_KEY=AIza...your-key...` |
| **Windows (PowerShell, current session)** | Run in a terminal | `$env:VIBEMIX_LLM_MODE = 'direct'`<br>`$env:GEMINI_API_KEY = 'AIza...your-key...'` |
| **Windows (PowerShell, persistent)** | Run once, then reopen the shell | `[Environment]::SetEnvironmentVariable('VIBEMIX_LLM_MODE', 'direct', 'User')`<br>`[Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'AIza...your-key...', 'User')` |

After editing an rc-file, `source ~/.zshrc` (or `source ~/.bashrc`, or open
a fresh terminal tab) so the new values land in your shell. On Windows
PowerShell, the `[Environment]::SetEnvironmentVariable` form persists across
sessions but does NOT update the current session — close and reopen the
terminal, or also run the `$env:` form to get both.

## Verify

Once the env vars are set, prove the Gemini client builds against your key
before you spin up the full co-host:

```bash
uv run python -c "from google import genai; import os; c = genai.Client(api_key=os.environ['GEMINI_API_KEY']); print('OK — client built for', c.__class__.__name__)"
```

A successful run prints `OK — client built for Client`. If you see
`KeyError: 'GEMINI_API_KEY'`, the env var didn't propagate to the subprocess
— check that you sourced the rc-file in *this* terminal and that the
variable name is spelled exactly `GEMINI_API_KEY` (case-sensitive).

After the smoke passes, run the real co-host:

```bash
uv run python -m vibemix
```

Talk into your DJ setup (BlackHole on macOS, WASAPI loopback on Windows)
for roughly 30 seconds, then watch for the AI co-host reply in the floating
pill / mascot overlay. If you see "no GEMINI_API_KEY" in the console, the
key still isn't reaching the subprocess — fix the shell rc-file sourcing
first, then re-run.

## Switch back to Bravoh proxy

If you want to go back to the rate-limited free Bravoh pool — for example
to ship a quick demo to a friend without sharing your key — the path is two
exports plus a restart. Note that simply *unsetting* `VIBEMIX_LLM_MODE`
defaults back to `direct` mode (BYO), so to actually USE the Bravoh proxy
you need `proxy` mode explicitly plus a proxy JWT.

```bash
# Bravoh-proxy mode (sends prompts through api.altidus.world):
export VIBEMIX_LLM_MODE=proxy
export VIBEMIX_PROXY_JWT=<bravoh-issued-token>
# Optional: override the proxy URL during local dev.
# export VIBEMIX_PROXY_BASE_URL=https://api.altidus.world
unset GEMINI_API_KEY   # not used in proxy mode; safe to clear
```

On Windows: `$env:VIBEMIX_LLM_MODE = 'proxy'` plus
`$env:VIBEMIX_PROXY_JWT = '...'`; `Remove-Item Env:GEMINI_API_KEY` to clear.

Restart vibemix after the env vars change. The gate code that picks between
BYO and proxy is at `src/vibemix/runtime/session_loop.py:842`.

## Privacy & Limits

**Privacy.** In BYO mode, your evidence packets — audio summaries, MIDI
move snippets, deck state, current-track metadata — go direct to
`generativelanguage.googleapis.com`. Google's API TOS apply (including
Google's data-retention and abuse-detection policies for the Gemini API);
no Bravoh telemetry hop, no per-install UUID aggregated on Bravoh's side.
This is the opposite of the proxy mode, in which the Bravoh proxy
normally records anonymized usage to inform model-routing decisions. BYO
mode skips that aggregation entirely.

**Limits.** Gemini's free tier on AI Studio is currently capped near
50 requests/day on the default models (Google moves these numbers — check
your AI Studio dashboard, not this doc). When you hit the cap, the Gemini
SDK surfaces a 429 from Google's API directly; vibemix's existing error
path (the same one Plan 69-03 wires for proxy fallback) surfaces a clean
"co-host unavailable" message in the pill / mascot rather than crashing
or hallucinating a coach line. If you push past free-tier limits often,
move the API key's project to paid billing in Google Cloud Console.

For the broader contributor surface — including the
"vibemix is Apache-2.0, the Bravoh proxy is closed-source" carveout —
see [`CONTRIBUTING.md`](../CONTRIBUTING.md) "Scope: vibemix vs Bravoh".

---

## See also

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — contributor scope + Bravoh carveout.
- [`docs/release-process.md`](release-process.md) — how vibemix cuts and ships releases.
- [`MAINTAINERS.md`](../MAINTAINERS.md) — who to reach about Bravoh-proxy issues.
