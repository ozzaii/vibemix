# vibemix — Economia dei Costi del Co-Host Live

**Stato:** modello di costo interno verificato contro le fonti, ricontrollato
2026-05-31. Le righe Gemini, DeepSeek, Hume, Deepgram e OpenAI sono radicate
nelle pagine ufficiali correnti. La riga Cartesia resta una stima legacy
derivata e non verificata, quindi questa copia non è pronta per prezzi esterni
finché quel tasso effettivo non viene confermato in fatturazione. Riproduci ogni
cifra con `vibemix library budget --stack live`. Questo documento misura il
costo. Non sceglie il modello di business e non valuta la qualità dei modelli
(quello lo decide l'orecchio di Kaan).

## In breve

Un DJ attivo ogni giorno costa circa **€9.74 al mese**. La voce del co-host si mangia circa tre quarti di quella cifra. Il cervello Gemini (che pensa e ascolta) prende quasi tutto il resto. La preparazione dei set e la pipeline LiveKit arrotondano a zero. Il fornitore di text-to-speech è la leva che muove il conto.

Stack scelto: cervello `gemini-3.5-flash`, voce **Cartesia Sonic**, ascolto mic→Gemini (nessun speech-to-text separato), preparazione set **DeepSeek V4 Pro**, LiveKit in **locale** (modalità diretta).

## Quanto costa un DJ

Per DJ attivo, con lo stack scelto (cervello `gemini-3.5-flash` + voce Cartesia):

| Utilizzo | €/DJ/mese | €/set |
|---|---|---|
| Attivo ogni giorno (20 set/mese) | **€9.74** | €0.49 |
| Occasionale (4 set/mese) | **€1.95** | €0.49 |

### Perché €9.74

| Voce | €/DJ/mese | Quota | Cosa paghi |
|---|---|---|---|
| **TTS (voce Cartesia)** | **7.39** | **76%** | il co-host che parla ~12s per reazione, ~1.600 reazioni/mese |
| cervello (`gemini-3.5-flash`, testo) | 1.33 | 14% | leggere le prove, scrivere la reazione |
| ascolto (stesso Gemini, audio in ingresso) | 0.99 | 10% | sentire il set (master + mic) come token audio |
| Viber preparazione set (DeepSeek V4 Pro) | 0.02 | ~0% | creare set, rispondere a domande, fuori sessione |
| LiveKit | 0.00 | 0% | modalità diretta locale, nessuna stanza Cloud |

Il cervello Gemini ascolta e pensa in una singola chiamata al modello: `ascolto` è la sua metà audio in ingresso, `cervello` è la sua metà testo. Insieme prendono il 24%. Parlare prende l'altro 76%. Paghi perché il co-host parli.

## Il benchmark di costo: cervello fisso, voce variabile

Cervello fermo su `gemini-3.5-flash`. Flotta a 10.000 DJ attivi al giorno.

| Voce TTS | €/DJ/mese | Flotta €/mese | Nota |
|---|---|---|---|
| Gemini 2.5 Flash TTS (economica) | 6.79 | €67.887 | la più economica sulla carta, ma **muta in live** |
| **Cartesia Sonic (scelta live)** | **9.74** | **€97.374** | funziona in live; riga costo legacy derivata/non verificata |
| Gemini 3.1 Flash TTS (collegata oggi) | 11.23 | €112.341 | premium, il conto di oggi |

Cartesia vince il test di affidabilità live perché produce davvero audio. Con la
riga sensitivity legacy derivata gira anche il 13% sotto la voce Gemini 3.1 che
il router usa oggi (€97k contro €112k di flotta), ma non presentare quel prezzo
Cartesia all'esterno finché la conversione del piano pubblico o della
fatturazione account non viene confermata. Gemini 2.5 TTS è ancora più
economica, ma restituisce "No audio content generated" sulla macchina live,
quindi è fuori.

## Le cinque leve di costo, in ordine

1. **Fornitore TTS.** Sposta la flotta da €68k (Gemini 2.5) a €147k (ElevenLabs). La decisione che conta.
2. **Lunghezza della risposta parlata + densità delle reazioni.** Entrambe alimentano direttamente la voce TTS e hanno rischio-qualità quasi nullo. Ridurre la risposta parlata 12s→9s risparmia ~18%; limitare 80→60 reazioni/set risparmia ~25%. Un vero amico DJ è conciso e sceglie i momenti, quindi un co-host più stringato può suonare più autentico, non meno.
3. **Utilizzo (set/mese).** Lineare. Un DJ occasionale a 4 set costa un quinto di uno quotidiano a 20.
4. **Livello del cervello.** Una leva vera, non gratis. Sostituire il premium `gemini-3.5-flash` con il Flash più economico taglia la flotta di ~€13,5k (14%), perché il Flash più economico ha una tariffa audio-in di $1.00/1M contro $1.50/1M del premium, quindi riduce sia il cervello che l'ascolto. È l'unica leva che cambia cosa dice il co-host, quindi viene dopo le leve della voce a rischio zero e si decide sull'orecchio di Kaan.
5. **Trasporto LiveKit.** La modalità diretta locale costa €0. LiveKit Cloud fatturerebbe $0,01 per **minuto-sessione-agente**, circa €138k/mese a 10k DAU, più grande di tutto il resto dello stack messo insieme. Girare in locale è la più grande decisione di costo, ed è già presa.

## Cache: l'ipotesi portante

La cifra di €9.74 assume un cache-hit implicito del 90% sull'input. Quel singolo numero regge il modello. Un hit del 90% taglia il costo del testo in ingresso del cervello di ~5 volte. Scendi a cache fredda (0% hit) e il conto per DJ sale a €12.34 (+38%). Il repository non misura mai il tasso reale, quindi tratta il 90% come un default speranzoso, non un fatto. Il `SessionMeter` in `budget.py` calcola già il vero `cache_hit_rate` da `usage_metadata`. Misuralo con un soak live prima di fidarti di €9.74. Anche il conteggio dei token di input del cervello (modellato a 1.900) è probabilmente basso: un prompt grounded completo con il blocco persona più lo stack anti-slop e di citazione sempre allegato arriva più vicino a 3.300-4.600 token. Al 90% di cache aggiunge circa €0.67. A cache fredda aggiunge €3.53, quindi i due rischi si sommano.

## Prezzi verificati contro le fonti (USD)

| Modello | Ruolo | Input /1M | Output /1M | Cache in /1M | Fonte | Letto |
|---|---|---|---|---|---|---|
| `gemini-3.5-flash` | cervello | $1.50 | $9.00 | $0.15 | ai.google.dev/gemini-api/docs/pricing | 2026-05-31 |
| `gemini-3.1-flash-tts-preview` | voce | $1.00 testo | $20.00 audio | — | stessa | 2026-05-31 |
| `gemini-2.5-flash-preview-tts` | voce | $0.50 testo | $10.00 audio | — | stessa | 2026-05-31 |
| Cartesia Sonic (`sonic-3`) | voce | legacy derivata ~$29.9/1M car | — | — | cartesia.ai/pricing (NON VERIFICATA: la pagina corrente elenca minuti Sonic-3.5, non uno SKU per carattere) | 2026-05-31 |
| `deepseek-v4-pro` | Viber | $0.435 | $0.87 | $0.0036 | nota ufficiale api-docs.deepseek.com sul prezzo a 1/4 | 2026-05-31 |
| Deepgram Nova-3 (STT alt.) | ascolto | — | — | — | $0.0048/min streaming | 2026-05 |
| LiveKit Cloud agent (non usato) | trasporto | — | — | — | $0.01/min-sessione-agente, livekit.io/pricing | 2026-05 |

Gemini fattura l'audio TTS a 25 token al secondo. `gemini-3.5-flash` non elenca
una tariffa audio separata, quindi l'audio viaggia sulla sua tariffa standard di
input $1.50/1M (non gratis). La pagina ufficiale DeepSeek dice che il prezzo V4
Pro viene regolato a un quarto del prezzo originale dopo la fine della promo del
75% il 2026-05-31 15:59 UTC, quindi $0.435/$0.87 è la riga ufficiale corrente.
Cartesia è diversa: la pagina pubblica corrente elenca minuti Sonic-3.5 e prezzi
di piano, ma non uno SKU esatto per carattere. Il repo mantiene la vecchia riga
$29.9/1M caratteri solo come placeholder sensitivity non verificato finché il
tasso effettivo account/fatturazione non viene confermato.

## Ipotesi dietro i numeri

- Una reazione: 1.900 token in ingresso, 40 token in uscita (dal benchmark Fase-81; probabilmente più vicino a 3.300-4.600 input in produzione, vedi sezione Cache), ~12s parlati, ~18s di finestra audio verso il cervello.
- 80 reazioni per set da 75 minuti (~1,07/min, ben sotto il tetto di ~205 del floor globale di 22s).
- Cache-hit implicito del 90% sull'input (non verificato, vedi sezione Cache).
- Il DJ attivo quotidiano fa 20 set/mese (generoso, ~5/settimana); l'occasionale ne fa 4.
- USD verso EUR a 0,92.

## Avvertenze

- La tariffa per carattere di Cartesia è legacy derivata, non uno SKU ufficiale.
  Non usare il titolo €9.74/€97k come copia prezzi esterna finché la conversione
  pubblica Sonic o la fatturazione account corrente non viene confermata.
- Gemini TTS è la voce cloud più economica sulla carta, eppure non restituisce audio sulla macchina live. Cartesia è la scelta live per affidabilità, non solo per costo. La catena di fallback collegata oggi degrada da Cartesia verso le voci Gemini mute, quindi una secondaria non-Gemini funzionante (OpenAI tts-1) va inserita nella catena.
- La reazione da 12s/30 parole è più chiacchierona di una vera battuta secca (5-12 parole, ~6s). Una reazione più stringata abbassa il conto per DJ verso €5.6, quindi la lunghezza parlata è una leva reale di prodotto e di costo.
- Questo prova il costo. Se `gemini-3.5-flash` suoni come un vero amico DJ resta una decisione dell'orecchio di Kaan.

## Riprodurre

```bash
# lo stack scelto
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3
# il benchmark di costo a tre voci
vibemix library budget --stack live --dau 10000 --brain live_coach --tts live_coach_tts          # Gemini 3.1 TTS
vibemix library budget --stack live --dau 10000 --brain live_coach --tts live_coach_tts_fallback  # Gemini 2.5 TTS
# la leva del livello del cervello (Flash più economico)
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts sonic-3
# il what-if di LiveKit Cloud + cache fredda + DJ occasionale
vibemix library budget --stack live --dau 10000 --livekit-per-min 0.01
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --cache-hit 0.0
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --sessions-per-month 4
```
