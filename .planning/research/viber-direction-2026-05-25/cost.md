# Cost Tracker Audit — vibemix (branch `live-tuning-or-brain`)

Read-only audit. Goal: prove every euro figure traces to a real measured token count, or is explicitly flagged as an estimate. Date 2026-05-25. SDK `google-genai==1.68.0` installed (pin `>=2.0.1`).

---

## VERDICT (per surface)

| Surface | Bulletproof? | Why |
|---|---|---|
| `SessionMeter` — **live_coach** path | **YES** | Billed from real `usage_metadata` (`prompt_token_count` / `cached_content_token_count` / `candidates_token_count`), recorded once post-stream. Rates verified correct. Cache split is real. |
| `SessionMeter` — **tts / debrief / debrief_tts / embedding** paths | **N/A (dead rates)** | These keys exist in `ROUTE_PRICING` but have **zero `record()` call sites**. They never produce a euro number, so they cannot be wrong — but they are also dead weight that implies coverage that does not exist. |
| `BudgetTelemetry.current_cost_estimate_eur()` (embed-folder `~€` line) | **NO — ESTIMATE, not measured** | `audio_embeds × 0.0006 + text_embeds × 0.0001`. Pure counters × fixed per-call constants. No token count touches it. Confirmed below with quantified error. |

Bottom line: the **live brain/coach** cost is bulletproof and measured. The **embedding/library** cost is an unmeasured estimate that the UI prints with a `~€` prefix (honest tilde) but never reconciles against reality.

---

## HALLUCINATION RISKS (each € number: measured vs estimated)

### 1. live_coach session cost — MEASURED ✅
- Source: `dj_cohost.py:1589-1597`. After the Gemini stream completes (`else` branch, no exception), the **last-seen** `usage_metadata` is recorded once. `usage_metadata` repeats across chunks; capturing last + recording once is correct (avoids double-billing). Verified at `dj_cohost.py:1442, 1484-1489`.
- `SessionMeter.record()` (`budget.py:194-253`) clamps `cached ≤ prompt`, computes `fresh_input = prompt − cached`, bills `fresh×input + cached×cached_input + output×output`. Arithmetic is sound and defensive (never raises — hot-path safe).
- OpenRouter brain path returns `usage_metadata=None` → `record_untracked()` (`dj_cohost.py:1598-1599`, `budget.py:255-262`). **No tokens fabricated.** This is the correct behavior — untracked calls are counted, not invented.
- Per-path euro in `summary()` (`budget.py:298-304`) = `cost_usd × USD_TO_EUR`. Real tokens all the way through. **No hallucination.**

### 2. Embedding / library cost — ESTIMATED ⚠️ (the known issue, confirmed)
- Source chain: `embed.py:728` (`increment_audio_embed`) / `embed.py:749` (`increment_text_embed`) → `BudgetTelemetry` counters → `current_cost_estimate_eur()` (`budget.py:353-359`) → surfaced at `folder_ingest.py:375-376` and `:402` (`~€{cost:.4f}` per-file progress) and `__main__.py:1603` (`total=... ~€...`) and `:1658` (`current_cost_estimate_eur:`).
- The number is `audio_embeds × COST_PER_AUDIO_EMBED_USD(0.0006) + text_embeds × COST_PER_TEXT_QUERY_USD(0.0001)`, then `× USD_TO_EUR`. **These are call counters times a fixed guessed per-call price. Zero token measurement.**
- **Why the estimate is structurally wrong (not just imprecise):** the `0.0006` constant assumes "60s clip ≈ 1000 audio tokens" (`budget.py:40`). At the verified Gemini rate of **32 tokens/sec**, a 60s clip is actually `60 × 32 = 1920` tokens, costing `1920 × $6.50/1M = $0.01248`. The hardcoded `0.0006` is **~20× too low.** The comment's "1000 audio tokens" is itself wrong (would only be ~31s of audio), and the `$6.50/1M` it multiplies by gives `0.0065` not `0.0006` even on its own stated assumption — so the constant is internally inconsistent **and** off by an order of magnitude against the real rate.
- **Error risk quantified:** real per-audio-embed ≈ **$0.01248** vs charged **$0.0006** → the embed-folder `~€` line under-reports audio embedding cost by roughly **20×**. Embedding a 1547-file library (3 excerpts/track ≈ 4641 audio embeds) shows `~€0.0026×4641×0.92 ≈ €0.0026`… i.e. it would display **~€0.003** when the true spend is closer to **~€0.053**. Small absolute euros, but the **per-call unit is wrong by 20×**, which poisons `project_monthly_cost()` and the €50 budget-gate test that depends on the same `COST_PER_AUDIO_EMBED_USD` constant.
- **`project_monthly_cost()` inherits the same bug** (`budget.py:94-125` all use `COST_PER_AUDIO_EMBED_USD`/`COST_PER_TEXT_QUERY_USD`). The "land under €50 at 1000 DAU" gate is being satisfied with a unit price ~20× below reality. **The gate is currently green for the wrong reason.** Re-checking with the correct $0.01248/audio-embed unit will materially raise the projection.

### 3. cache_hit log event (events.jsonl) — MEASURED ✅
- `dj_cohost.py:1490-1506` logs `cache_hit` events from real `cached_content_token_count`, deduped per-turn against last emitted value. This is genuine telemetry, not a counter. Correct.

---

## WRONG PRICES

Verified all `ROUTE_PRICING` rates against Google's official pricing (May 2026). Model map: `live_coach`=gemini-3.5-flash, `debrief`=gemini-3-pro-preview, `embedding`=gemini-embedding-2 (`_router_config.py:27-40`).

| Path | Code (in/out/cached USD per 1M) | Real 2026 price | Verdict |
|---|---|---|---|
| `live_coach` | 1.50 / 9.00 / 0.15 | gemini-3.5-flash: 1.50 / 9.00 / 0.15 | ✅ CORRECT |
| `live_coach_tts` | 1.00 / 20.00 / 1.00 | gemini-3.x-flash-TTS: 1.00 (text in) / 20.00 (audio out) | ✅ CORRECT (cached==input, no cache on TTS — right) |
| `debrief` | 2.00 / 12.00 / 0.20 | gemini-3.1-pro ≤200k: 2.00 / 12.00 / 0.20 | ✅ CORRECT (≤200k tier; **>200k tier is 4/18/0.40 — not handled, but debrief prompts are small**) |
| `debrief_tts` | 1.00 / 20.00 / 1.00 | flash-TTS: 1.00 / 20.00 | ✅ CORRECT |
| `embedding` | input 0.20, output 0.00, cached 0.20 | gemini-embedding-2: text 0.20 / 1M | ✅ CORRECT **for text**, but **MISSING the audio rate 6.50/1M** — embedding-2 bills audio at $6.50/1M and this row only models text. Since embedding is never `record()`-ed anyway, it's latent, but if wired it would under-bill all audio embeds to the text rate. |

The separate constants `PRICING` (`budget.py:35-38`: text 0.20, audio 6.50/1M) and `COST_PER_AUDIO_EMBED_USD`/`COST_PER_TEXT_QUERY_USD` (`:41-43`) coexist. `PRICING` has the **correct** $6.50/1M audio rate; the per-call constants are the broken derivation from it.

**Gate compliance:** `budget.py` contains **no model literals** (grep CLEAN) — keys are router-paths only. No CLAUDE.md gate violation. ✅

---

## CACHE-HIT CORRECTNESS — two distinct concepts, NOT conflated ✅

The audit confirms the two "cache" notions are tracked separately and correctly:

**(a) LOCAL content-hash embed cache** — `embed.py` `_track_hash` (SHA256 of file bytes ‖ model ‖ strategy version). Re-embed = 0 API calls = free. Tracked via `BudgetTelemetry.increment_cache_hit()` → `cache_hits` counter (`budget.py:349-351`). It is correctly **excluded from the cost estimate** (`current_cost_estimate_eur` only sums `audio_embeds + text_embeds`, never `cache_hits`). A cache hit costs nothing and adds nothing. Correct.

**(b) Gemini server-side CONTEXT cache (live brain)** — real `cached_content_token_count` from `usage_metadata`, billed at the 90%-discount `cached_input` rate (0.15 vs 1.50 for live_coach). Tracked by `SessionMeter` per-path; `savings_usd = cached × (input − cached_input)/1e6` (`budget.py:229`). `cache_hit_rate` in `summary()` = `cached_tokens / input_tokens` over `_CACHE_ELIGIBLE_PATHS` only (tts/embedding excluded because their cached==input → no real discount; `budget.py:173-175, 287-296`). This is exactly right: the rate reflects only paths where caching saves money.

The two never mix: (a) is a call-count counter on the embedding telemetry singleton; (b) is a token-level split on the session meter. Different objects, different surfaces, different files. **No conflation.** ✅

---

## EXACT FIX RECOMMENDATIONS (make embedding cost measured)

**The SDK cannot give you embed token counts on this client.** Confirmed: `EmbedContentResponse` exposes only `embeddings`, `metadata` (`EmbedContentMetadata`), `sdk_http_response`. The only token-bearing fields — `EmbedContentMetadata.billable_character_count` and `ContentEmbedding.statistics.token_count` — are both documented **"Vertex API only."** vibemix uses `genai.Client(api_key=...)` everywhere (`__main__.py:755,1402,1544`; `session_loop.py:859`) = Gemini **Developer** API, never Vertex → these fields are always `None`. So real measured embed tokens are **not obtainable from the response**.

**Most accurate alternative — derive audio tokens from exact clip duration × the documented rate:**

Verified rate: **Gemini audio = 32 tokens / second** (official docs). gemini-embedding-2 audio = **$6.50 / 1M tokens**; text = **$0.20 / 1M tokens** (verified).

1. **Fix the broken per-call constant.** `budget.py:40-43`:
   - Current: `COST_PER_AUDIO_EMBED_USD = 0.0006` (≈20× too low, internally inconsistent).
   - Replace per-call audio constant with a **duration-derived** computation: `audio_tokens = ceil(clip_seconds × 32)`, `cost_usd = audio_tokens × 6.50 / 1e6`. For the fixed `EXCERPT_DURATION = 60` (`embed.py:143`): `60 × 32 = 1920 tokens → $0.01248/embed`. (Note: memory says emb-2 audio cap is really ~80s; if excerpts grow, the derivation auto-scales — a hardcoded constant does not.)
   - Text: a query is variable-length, so estimate `text_tokens ≈ ceil(chars/4)` and bill `× 0.20/1e6`, OR keep a documented worst-case constant. Either way, label it ESTIMATE.

2. **Make `BudgetTelemetry` accumulate measured seconds, not bare call counts.** `budget.py:329-359`:
   - Change `increment_audio_embed()` → `add_audio_embed(clip_seconds: float)` accumulating `total_audio_seconds`; compute cost as `total_audio_seconds × 32 × 6.50/1e6 × USD_TO_EUR`.
   - Pass the real clip duration from the call site: `embed.py:710-729` already controls `EXCERPT_DURATION` and the ffmpeg `-t` slice (`embed.py:687`), so the exact seconds embedded are known at `_call_gemini_audio_single`. Wire it through.
   - For text: pass `len(text)` from `_call_gemini_text` (`embed.py:731-750`) and divide by 4 for an explicit-estimate token count.

3. **Add the audio rate to the `embedding` ROUTE_PRICING row** (`budget.py:167`) if you ever route embeds through `SessionMeter` — today it only models the text rate (0.20) and would under-bill audio. Better: keep embedding on the duration-derived `BudgetTelemetry` path and document that `SessionMeter`'s `embedding` key is reserved/unused.

4. **Re-run the €50 budget gate** (`test_monthly_projection_under_50_eur`) after fixing the unit price — it is currently passing against a unit ~20× below reality. Expect the projection to rise; the 500-track/36-month lock (`budget.py:54-58`) may need revisiting. Flag for Kaan: this is a real headroom change, not a cosmetic one.

5. **Label the UI number honestly.** `folder_ingest.py:402` / `__main__.py:1603` already prefix `~€` (good — signals estimate). After the duration-fix it remains an estimate (token count derived, not returned by API), so keep the tilde and ideally add "(est., 32 tok/s)" once in the summary line.

**Files/lines touched:** `budget.py:40-43` (constants), `budget.py:339-359` (telemetry seconds), `budget.py:94-125` (projection unit), `budget.py:167` (embedding audio rate), `embed.py:710-750` (pass clip seconds/char count), and the €50 gate test.

---

## Sources
- [Understand and count tokens | Gemini API](https://ai.google.dev/gemini-api/docs/tokens) — audio = 32 tokens/sec
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing) — model rates + 90% context-cache discount
- [Gemini Embedding GA — Google Developers Blog](https://developers.googleblog.com/gemini-embedding-available-gemini-api/) — embedding-2: $0.20/1M text, $6.50/1M audio
- [Gemini 3.5 Flash pricing](https://pricepertoken.com/pricing-page/model/google-gemini-3.5-flash) — 1.50 / 9.00 / 0.15 cached
