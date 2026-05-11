"""Quick smoke test: Gemini 3.1 Flash TTS direct call.
Sends one short text, saves PCM to /tmp/test_tts.wav, prints info.
Usage: source .venv/bin/activate && set -a && source .env && set +a && python3 _test_tts.py
"""
import os, sys, wave
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY missing")
client = genai.Client(api_key=api_key)

TEXT = "yo this drop is sick bro"
VOICE = "Achird"  # tripped/laid-back voice
MODEL = "gemini-3.1-flash-tts-preview"

print(f"-> calling {MODEL} | voice={VOICE} | text='{TEXT}'")
resp = client.models.generate_content(
    model=MODEL,
    contents=TEXT,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE),
            ),
        ),
    ),
)

# Extract PCM bytes from response
pcm = resp.candidates[0].content.parts[0].inline_data.data
mime = resp.candidates[0].content.parts[0].inline_data.mime_type
print(f"-> got {len(pcm)} bytes | mime={mime}")

# Gemini TTS PCM is 24kHz mono int16 LE
out = "/tmp/test_tts.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(24000)
    w.writeframes(pcm)
print(f"-> wrote {out} ({len(pcm)/(24000*2):.2f}s)")
