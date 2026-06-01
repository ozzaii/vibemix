# vibemix — Economia dei Costi del Co-Host Live

**Stato:** modello di costo interno verificato contro il sorgente, ricontrollato
2026-06-01. La voce di produzione è **solo MOSS locale**: nella catena live non
c'è fallback Cartesia, Gemini TTS, OpenAI TTS o altro TTS cloud a pagamento. Le
voci cloud restano nel modello solo come righe sensitivity esplicite. Riproduci
ogni cifra con `vibemix library budget --stack live`. Questo documento misura i
costi; non decide la qualità del modello.

## In breve

Un DJ attivo ogni giorno costa circa **€0.99 al mese** con lo stack corrente. Il
costo del provider voce è **€0.00** perché MOSS gira on-device. La voce di costo
dominante è ora l'ascolto/audio-input verso il cervello Gemini.

Stack scelto: cervello `live_coach_cand_25flash`, voce **Local MOSS**, ascolto
mic→Gemini Part (nessun speech-to-text separato), preparazione set **DeepSeek V4
Pro**, LiveKit in **locale** (modalità diretta).

## Quanto costa un DJ

Per DJ attivo, con lo stack scelto:

| Utilizzo | €/DJ/mese | €/set |
|---|---:|---:|
| Attivo ogni giorno (20 set/mese) | **€0.99** | **€0.05** |
| Occasionale (4 set/mese) | **€0.20** | **€0.05** |

### Perché €0.99

| Voce | €/DJ/mese | Flotta €/mese @ 10k DAU | Cosa paghi |
|---|---:|---:|---|
| ascolto | **0.66** | **6,624** | token audio-input Gemini per la finestra live |
| cervello | 0.31 | 3,066 | leggere prove e scrivere la reazione |
| tts | **0.00** | **0** | voce MOSS locale; nessun costo provider |
| Viber preparazione set | 0.02 | 227 | set building e domande biblioteca fuori sessione |
| LiveKit | 0.00 | 0 | modalità diretta locale; nessuna stanza Cloud |

Il centro di gravità del costo si è spostato dalla voce all'ascolto. MOSS toglie
il vecchio costo cloud-TTS; non toglie il bisogno di distribuire/scaricare il
modello MOSS e provarlo su un artifact release reale.

## Sensitivity: quanto costerebbe una voce pagata

Cervello/ascolto fissi sul default corrente. Flotta a 10.000 DJ attivi al
giorno.

| Voce TTS | Flotta €/mese | Nota |
|---|---:|---|
| **Local MOSS (produzione)** | **9,917** | default corrente; costo provider TTS zero |
| OpenAI tts-1 | 47,011 | solo what-if pagato |
| Gemini value TTS | 54,371 | solo what-if storico |
| Cartesia Sonic | 83,858 | sensitivity legacy derivata; **NON VERIFICATA** |
| Gemini premium TTS | 98,825 | solo what-if storico |
| ElevenLabs Flash v2.5 | 133,565 | solo what-if pagato |
| Hume Octave 2 | 133,565 | solo what-if pagato |

Cartesia **non** è la voce di produzione. La riga resta perché il modello budget
mantiene confronti sensitivity storici, ma il prezzo è legacy derivato e non va
usato come copia prezzi esterna.

## Altre leve di costo

1. **Finestra di ascolto e tier del cervello.** Con MOSS locale, i token
   audio-input sono la voce pagata principale. Ridurre contesto audio inutile
   vale più che cambiare vendor voce.
2. **Lunghezza della risposta parlata + densità delle reazioni.** Contano ancora
   per sensazione prodotto e carico locale/modello, ma non aggiungono spesa
   provider TTS sul percorso di produzione.
3. **Utilizzo (set/mese).** Lineare. Un DJ occasionale a 4 set costa un quinto
   di un DJ quotidiano a 20.
4. **Trasporto LiveKit.** La modalità diretta locale costa €0. LiveKit Cloud
   fatturerebbe per minuto-sessione-agente e non fa parte del percorso default.

## Cache: l'ipotesi portante

La cifra €0.99 assume un cache-hit implicito del 90% sull'input. A cache fredda
(0% hit), il costo flotta sale da €9,917 a €16,713/mese a 10k DAU. Il
`SessionMeter` in `budget.py` calcola il vero `cache_hit_rate` da
`usage_metadata`; misuralo in un soak live prima di usare il modello per
decisioni di prezzo.

## Prezzi verificati contro le fonti

| Riga | Ruolo | Fonte | Stato |
|---|---|---|---|
| Gemini brain/listening | cervello + audio input | ai.google.dev/gemini-api/docs/pricing | verificato 2026-05-31 |
| Local MOSS | voce | `vibemix.agent.local_tts` | verificato come costo provider zero |
| DeepSeek V4 Pro | Viber | nota ufficiale api-docs.deepseek.com | verificato 2026-05-31 |
| Cartesia Sonic | what-if voce | cartesia.ai/pricing | **non verificata**, legacy derivata |
| OpenAI / ElevenLabs / Hume | what-if voce | pagine prezzo vendor | righe confronto soltanto |
| LiveKit Cloud agent | what-if trasporto | livekit.io/pricing | non usato in modalità diretta locale |

## Avvertenze

- Questo prova la matematica del costo a livello sorgente, non la readiness di
  release. Un'app distribuibile deve ancora provare disponibilità modello MOSS,
  comportamento sidecar packaged e audio live su macchina pulita.
- Il 90% di cache-hit non è ancora un fatto prodotto misurato live.
- Questo prova il costo, non il gusto. Se il cervello scelto e la voce MOSS
  suonino come un vero amico DJ resta una prova d'ascolto.

## Riprodurre

```bash
# stack costo produzione corrente
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local

# righe what-if voce pagata
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts live_coach_tts_fallback
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts live_coach_tts
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts sonic-3

# cache fredda e DJ occasionale
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local --cache-hit 0.0
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local --sessions-per-month 4
```
