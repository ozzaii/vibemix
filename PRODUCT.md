# Product

## Register

product

## Users

Solo DJs across three skill levels — Beginner, Intermediate, Pro — running live sets at home, in a bedroom studio, or in a club. The user is always in flow: cans on, hands on the controller, eyes locked to djay Pro / Rekordbox / Serato. They are not browsing, not reading, not configuring. They want a co-host that notices what they're doing and reacts in a way that feels alive and grounded — never late, never scripted, never generic.

Macroaudience: the broader free-and-open-source DJ tooling community (Mixxx users, custom controller mappers, performance-focused producers) that Bravoh wants to warm into its waitlist via vibemix's GitHub release. The interface is judged by both audiences: the DJ in the moment and the developer skimming the repo.

## Product Purpose

A free, open-source AI co-host for live DJ sets. Runs locally on macOS and Windows. Listens to the master output, watches the DJ software's window, ingests MIDI from the controller, and speaks back into headphones or speakers as either a hype-man (party mode) or a coach (feedback mode). Reactions are grounded in real evidence — audio features, current track, MIDI moves — never hallucinated commentary.

Bravoh's first open-source release. Built as a polished, narrow-scope utility that warms an audience into Bravoh's waitlist. Success looks like 500–1000+ GitHub stars, DJ-set testing that confirms the "real friend in your ear" feel, and a closed beta that converts into Bravoh signups.

## Brand Personality

Three words: **precise, restrained, alive.**

Voice and tone: a confident DJ peer who notices what matters. Not a chatbot. Not a hype-bot. Not a coach reading from a textbook. The interface speaks the same way the cohost does — short, specific, grounded. JetBrains Mono numerics, Saira condensed for labels. Pioneer-grade hardware in idle mode.

The product is unapologetic about being for DJs. No onboarding-tour overlays, no welcome modals with cartoon graphics, no "tap to begin" splash. It opens, it boots, it works.

## Anti-references

- **Voice assistants doing music commentary.** Siri / Alexa / "Hey Spotify" register. We are not a voice assistant.
- **ChatGPT chrome.** Chatbot bubble UI, send button at the bottom, message-stream-as-main-surface. The cohost speaks, it does not chat.
- **Generic AI tool aesthetics.** Neon glow on black, glassmorphism cards floating in nowhere, hero metric layouts ("3,247 reactions delivered ↗ 12%"), lucide icons everywhere, gradient-text headlines.
- **SaaS dashboard sameness.** Cream + teal, navy + gold, blue-and-white card grids. The category-reflex pull for any "developer tool" or "creative tool" landing.
- **"Music app" cliché.** Gradient waveform hero, big "Now Playing" card with album-art bloom, Spotify-green CTAs, vinyl-record loading spinners.
- **`mocks/vibemix-direction-explorations.html`** — Kaan's own discarded earlier directions. The final lock is `mocks/vibemix-direction-final.html`.
- **AI-slop hero homepage feel.** The Tauri app is not a marketing page. No big H1 + supporting metric + CTA composition anywhere in the product surface.

## Design Principles

1. **Real DJ friend in your ear, no AI slop.** Every reaction is tied to real evidence (audio + MIDI + screen + now-playing). If reactions feel scripted, late, hallucinated, or generic, the product has failed regardless of how polished the UI is.

2. **Grounded over clever.** Every UI surface must feel like Pioneer-grade hardware in idle mode — a CDJ-3000 sitting at rest, breathing. Not a software widget pretending to be hardware via faux-3D bevels; tactility comes from inset hairlines, void backgrounds, and one amber light per panel.

3. **Restraint is the point.** The screen is mostly void. Only what matters cuts through. The 20/80 rule is enforced through tokens — silk text and glass surfaces own 80% of any view; amber is the rare deck-light. If more than one panel is sweeping, breathing, or pulsing at the same time, the design is failing.

4. **Hardware tactility.** Type set in Saira condensed display + JetBrains Mono numerics. Hairline 1px borders. Faint inset bezels (the "deck top + deck bottom" inner shadow). The opposite of soft Material-3 elevation or floating-card SaaS.

5. **Sign-of-life, not flashlight.** Motion is restrained breathing — the amber border sweep is 22 seconds, the LED pulse is 1.4 seconds. Never sweeping marketing-tier choreography, never spring-bouncy, never elastic. `prefers-reduced-motion` freezes the sweep entirely.

## Accessibility & Inclusion

- `prefers-reduced-motion: reduce` freezes the amber border-sweep and downgrades glass blurs to half-strength. Honored at the token layer in `tokens.css`.
- Runtime performance escape hatch: Settings → Performance → "Lighter blur" sets `html[data-blur-perf="on"]`, which downgrades all three blur strengths for low-GPU machines (older Intel Macs, Windows laptops with integrated GPUs).
- Type scale: 14px body, hierarchy through Saira's variable `wdth` (75–125) + `wght` (300–800) axes plus uppercase label tracking. No reliance on color alone for hierarchy.
- Contrast: silk (`#d6cfc7`) on void (`#000`) is ~14:1. Amber (`#ff8a3d`) on void is ~7:1. Status LEDs read against their own glass surfaces, never as text-on-text.
- Focus ring: 2px amber outline + 2px offset + `--glow-soft` shadow. Visible on every interactive control via `:focus-visible`.
- Mascot is `aria-hidden="true"` — purely decorative, never carries information the cohost transcript doesn't already say.
