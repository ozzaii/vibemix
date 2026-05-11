"""Quick smoke test: Gemini 3 Flash multimodal — does it actually reason about audio?
Sends a real chunk of music + a prompt, checks if response references the audio.
Usage: source .venv/bin/activate && set -a && source .env && set +a && python3 _test_multimodal.py
"""
import os, sys, wave, time
from pathlib import Path
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY missing")
client = genai.Client(api_key=api_key)

# Latest recording with real music
rec_dir = Path("/Users/ozai/projects/dj-set-ai/recordings/20260510-132307")
input_wav = rec_dir / "input.wav"
print(f"-> loading {input_wav} ({input_wav.stat().st_size / 1024:.0f}KB)")

# Read raw PCM (skip 44-byte WAV header) — input.wav is 16kHz mono int16
with open(input_wav, "rb") as f:
    f.seek(44)
    pcm = f.read()
print(f"-> {len(pcm)/(16000*2):.1f}s of audio")

# Take last 15 seconds — like cohost.py would send
chunk_bytes = 15 * 16000 * 2
audio_chunk = pcm[-chunk_bytes:] if len(pcm) > chunk_bytes else pcm
print(f"-> sending last {len(audio_chunk)/(16000*2):.1f}s ({len(audio_chunk)/1024:.0f}KB)")

MODEL = "gemini-3-flash-preview"
PROMPT = (
    "You are listening to a snippet of music from a DJ set. "
    "Describe what you actually HEAR in this audio — be specific about elements "
    "(kick pattern, bass, melody, vocals, energy level, any drops/breakdowns). "
    "If silent, say 'silence'. Respond in one short paragraph."
)

print(f"-> calling {MODEL}")
t0 = time.time()
resp = client.models.generate_content(
    model=MODEL,
    contents=[
        types.Content(role="user", parts=[
            types.Part(text=PROMPT),
            types.Part(inline_data=types.Blob(
                data=audio_chunk,
                mime_type="audio/pcm;rate=16000",
            )),
        ]),
    ],
)
dt = time.time() - t0
print(f"-> got response in {dt:.2f}s\n")
print("=" * 60)
print(resp.text)
print("=" * 60)
