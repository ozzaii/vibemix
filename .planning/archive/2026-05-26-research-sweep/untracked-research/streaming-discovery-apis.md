# Streaming & Discovery APIs — Beyond-Local Track Discovery + Metadata Enrichment

> Research date: 2026-05-26. Driver: Francesco's "Beatport API" suggestion — let the Viber agent
> discover tracks + enrich metadata from streaming/catalog sources as grounded tools.
>
> **Scope flag (read first):** vibemix OSS is **local-only**. Public-catalog discovery, affiliate
> linking, and any commercial-API integration are **Bravoh-commercial**, not the free OSS app.
> Every source below is tagged OSS-realistic / Bravoh-commercial-later accordingly. The OSS app
> must keep working with zero external catalog keys; these are server-side Bravoh features.

---

## TL;DR

- **Spotify gutted the useful part.** Audio Features, Audio Analysis, Recommendations, and Related
  Artists are **dead for any app created after 2024-11-27**. What survives (search/track/artist
  metadata, popularity) has **no BPM/key/energy** — useless for our DJ-grounding thesis on new apps.
- **Beatport is the only source with native DJ metadata (BPM + key + genre + charts) at catalog
  scale** — but the API is **non-commercial by default, commercial use needs written pre-approval**,
  approval is gated/slow, key is **domain-locked**, and previews link back to Beatport. This is a
  **Bravoh-commercial partnership**, not an OSS drop-in.
- **MusicBrainz + AcoustID = the OSS-realistic backbone.** Free, open data (CC0 core), audio
  fingerprint → canonical metadata + IDs. No BPM/key/energy, no real discovery — pure enrichment/ID.
  Hard 1 req/sec limit; commercial use needs a (cheap, contactable) MetaBrainz plan.
- **SoundCloud API is effectively closed** to new registrations (suspended since ~2022, manual
  AI-agent triage). Treat as unavailable.
- **Discogs = release/catalog metadata + genre/style + marketplace**, free with auth (60 rpm), but
  **no BPM/key**, weak on recent electronic single-track data, and ToS forbids driving traffic
  off-Discogs. Enrichment-only, niche.
- **1001Tracklists has no official public API** — only scrapers/unofficial wrappers. It is *the*
  source for real DJ transition/co-play discovery ("what do DJs actually mix after X"), but using it
  means scraping against unclear ToS → **Bravoh-commercial / partnership only, never bundle a scraper
  in OSS.**

---

## Per-source matrix

| Source | What's accessible | Auth & access | Rate / cost | ToS reality | DISCOVERY vs METADATA | Verdict |
|---|---|---|---|---|---|---|
| **Beatport API v4** | Catalog search (tracks/artists/labels/releases/charts), **BPM, key, genre + sub-genre hierarchy**, Top-N charts per genre, artist/label top-10, ~2-min audio previews (`sample_start_ms`/`sample_end_ms`), user library | OAuth 2.0 + PKCE; bearer token. Must **apply** for a key; access levels gated. Key is **domain-locked** to the domain you registered. | No official published rate limit (community advises ~500ms between calls). Pricing not public — partner-negotiated. | **Non-commercial by default; commercial use must be pre-approved IN WRITING.** Purchase options must link back to Beatport. They can revoke "for any reason or no reason." | **Both** — only source with DJ-native metadata AND charts/genre-top discovery. (Explicit "related/recommended" endpoint not documented.) | **Bravoh-commercial partnership.** The crown jewel for DJ metadata; needs a deal. Not OSS. |
| **Spotify Web API** | Search, track/artist/album metadata, popularity, playlists. **Audio Features / Audio Analysis / Recommendations / Related Artists = DEPRECATED for apps created after 2024-11-27** (403). May-2025: extended quota now needs **250k MAU** to even apply. | Free app + Client Credentials (server-to-server) or OAuth (user). | Standard quota free; extended quota gated behind 250k MAU. | Allowed, but the DJ-useful endpoints are gone for new apps. ToS forbids using data to train competing models. | **Metadata only now** (discovery endpoints killed). No BPM/key/energy for us. | **Skip for grounding.** Maybe a thin "resolve track → Spotify link/popularity" enrich field. No discovery value post-2024. |
| **SoundCloud API** | (When open) track search, stream/preview, user/track metadata, some social signals. | OAuth 2.1. **New app registration suspended since ~2022**; only manual AI-agent triage, no public timeline. | n/a — can't reliably get a key. | Restrictive; gated. | Would be discovery (underground/unreleased) + metadata, *if accessible*. | **Treat as unavailable.** Revisit only if Bravoh secures a partner relationship. |
| **Discogs API** | Release/master/artist DB, **genre + style tags**, label, year, formats, marketplace pricing, images. | Token (key+secret) or OAuth. Free, register an app. | **60 rpm authed / 25 rpm unauth**, by source IP, 60s moving window. Free. Requires unique User-Agent. | Commercial use *generally* permitted but **prohibits driving traffic to non-Discogs services** and reselling API access. | **Metadata only** (no recommendations). | **OSS-realistic, niche.** Good for release/label/genre enrichment + vinyl/discography context. **No BPM/key.** Weak on recent EDM singles. Secondary enricher. |
| **MusicBrainz + AcoustID** | MB: canonical recording/release/artist IDs, titles, ISRC, relationships, labels. AcoustID: **audio fingerprint → MBID match** (30M+ fingerprints, ~10M mapped). | MB: User-Agent required, no key for reads. AcoustID: free API key for non-commercial. | MB: **hard 1 req/sec**. AcoustID: **3 req/sec**. Both **free for non-commercial**; commercial = MetaBrainz plan / AcoustID commercial plan (contactable, cheap). | Core data **CC0 (public domain)**; some non-core CC-BY-NC-SA. Commercial use needs a plan. | **Metadata / identity only.** No BPM/key/energy, no recommendation engine. | **OSS-realistic backbone.** Best free way to canonicalize local files (fingerprint → MBID → enrich). No discovery. Pair with our **own CLAP** vectors for similarity. |
| **1001Tracklists** | DJ setlists, real transition/co-play data ("track A → track B in real sets"), festival/radio show tracklists, track popularity-in-sets. | **No official public API.** Only community scrapers + an unofficial third-party REST wrapper (BeautifulSoup). | n/a (scraping; fragile, IP-blockable). | Unclear/restrictive; data is aggregated from upstream APIs; scraping is legally grey. | **Pure discovery** — the single best "what do DJs actually play next" signal anywhere. | **Bravoh-commercial / partnership only.** Never bundle a scraper in OSS. Highest discovery value, highest ToS risk → needs a licensed deal or scrape on Bravoh server with counsel sign-off. |

---

## DISCOVERY vs METADATA, distilled

- **Real discovery (recommendations / related / charts / co-play):** Beatport (charts + genre-top),
  1001Tracklists (DJ co-play — the gold standard), Spotify (DEAD for new apps).
- **Metadata / enrichment / identity only:** MusicBrainz+AcoustID (canonical ID), Discogs
  (genre/style/label/release), Spotify-surviving (links/popularity), Beatport (BPM/key/genre also
  serves enrichment).
- **The hard truth:** every *managed* recommendation engine that mattered (Spotify) has closed to
  newcomers. The durable discovery moat for vibemix is **our own CLAP audio-similarity engine over
  the user's library + (Bravoh-side) a licensed Beatport/1001TL catalog** — not a third-party reco API.

---

## Recommended MCP tool design

Two grounded tools layered onto the existing Viber toolset (`library/toolset.py`). Keep the
**seen-set grounding invariant**: external results enter the agent's allow-list only after being
echoed back as real IDs, so the LLM can't hallucinate catalog tracks.

### `discover_tracks(query | seed_track_id, source, k)`
Returns candidate tracks **beyond the local library**.
- **OSS-realistic backend:** none that gives true reco for free. Ship the **local-CLAP**
  "find_similar over your own library" as the OSS discovery surface (already our engine).
- **Bravoh-commercial backend:** Beatport charts/genre-top + (licensed) 1001TL co-play. Server-side,
  proxied through the Bravoh key (same per-client rate-limit pattern as the Gemini proxy).
- Output schema: `{external_id, source, title, artist, bpm?, key?, genre?, preview_url?,
  buy_url (Beatport link-back), provenance}`. `provenance` makes grounding auditable.

### `enrich_metadata(track_id | file_path | fingerprint)`
Fills missing fields on a track the user already has or a discovered candidate.
- **OSS-realistic backend (default):** AcoustID fingerprint → MBID → MusicBrainz canonical
  metadata + Discogs genre/style/label. Free, respects 1 rps (MB) / 3 rps (AcoustID) / 60 rpm
  (Discogs) — enforce a token-bucket. **No BPM/key from these** — BPM/key stays from our own
  offline DSP / cue engine.
- **Bravoh-commercial backend:** Beatport for authoritative BPM/key/genre when the track exists in
  their catalog.
- Output: merged record with **per-field source attribution** (so the co-host can cite "key from
  Beatport" vs "key from local analysis").

### Wiring notes
- Both tools are **server-side in Bravoh** for any commercial source; OSS app calls only the local
  CLAP + (optionally) the free MB/AcoustID/Discogs path with the user's own keys / a shared
  rate-limited proxy.
- Reuse the existing budget/telemetry seam (`library budget --json`) to bound external-call cost.
- Respect domain-lock (Beatport) and User-Agent/rate rules (MB/Discogs) at the proxy layer.

---

## Now vs later

| Phase | Source | Why |
|---|---|---|
| **OSS now** | Local CLAP similarity (own engine) | True "discovery" with zero external dep; on-thesis (grounded by real audio). |
| **OSS now (optional, free)** | MusicBrainz + AcoustID + Discogs enrichment | Free, open, canonicalizes the user's own files. Rate-limited, no BPM/key. |
| **Bravoh-commercial later** | Beatport API partnership | Only native DJ metadata + charts at scale. Needs written commercial approval + domain-lock + link-back. The real catalog moat. |
| **Bravoh-commercial later** | 1001Tracklists (licensed or counsel-approved scrape) | Best DJ co-play discovery signal; highest ToS/legal risk → deal or server-side scrape only. |
| **Skip** | Spotify (discovery), SoundCloud | Spotify reco/audio-features dead for new apps; SoundCloud registration closed. |

---

## Sources

- Beatport: [API key request announcement](https://groups.google.com/g/beatport-api/c/sU8TCHEOpuY), [v4 endpoint gist](https://gist.github.com/kemo/506ca56e35b9506ee5233bc4d773c1c8), [Partner Portal](https://partnerportal.beatport.com/hc/en-us), [Terms & Conditions](https://support.beatport.com/hc/en-us/articles/4414997837716-Terms-and-Conditions)
- Spotify: [Changes to the Web API (2024-11-27)](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), [TechCrunch coverage](https://techcrunch.com/2024/11/27/spotify-cuts-developer-access-to-several-of-its-recommendation-features/), [Web API reference](https://developer.spotify.com/documentation/web-api/reference)
- SoundCloud: [Registration reopen issue #219](https://github.com/soundcloud/api/issues/219), [API guide](https://developers.soundcloud.com/docs/api/guide), [API ToU](https://developers.soundcloud.com/docs/api/terms-of-use)
- Discogs: [API Terms of Use](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use), [API docs / accessing](https://www.discogs.com/developers/accessing.html), [rate-limit forum](https://www.discogs.com/forum/thread/1104957)
- MusicBrainz / AcoustID: [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API), [Data License](https://musicbrainz.org/doc/About/Data_License), [AcoustID web service](https://acoustid.org/webservice), [AcoustID FAQ](https://acoustid.org/faq)
- 1001Tracklists: [unofficial Python scraper](https://github.com/leandertolksdorf/1001-tracklists-api), [unofficial REST wrapper](https://github.com/yss14/1001tracklist-api), [privacy policy](https://www.1001tracklists.com/info/privacy.html)
