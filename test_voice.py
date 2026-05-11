"""Smoke test: ask Gemini to say one sentence and play it through speakers.
If you hear a voice, the output side is wired correctly."""
import asyncio, os, sys
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=types.Content(parts=[types.Part(
            text="You are a hype DJ co-host. Say one short fire sentence to introduce yourself."
        )]),
    )
    async with client.aio.live.connect(
        model="gemini-3.1-flash-live-preview", config=cfg
    ) as session:
        await session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": "Introduce yourself, one sentence."}]}],
            turn_complete=True,
        )
        pcm = bytearray()
        async for r in session.receive():
            if r.data:
                pcm.extend(r.data)
            if r.server_content and r.server_content.turn_complete:
                break
        if not pcm:
            sys.exit("no audio received")
        audio = np.frombuffer(bytes(pcm), dtype=np.int16)
        print(f"-> got {len(audio)/24000:.1f}s of audio, playing on speakers")
        sd.play(audio, samplerate=24000, device="MacBook Pro Speakers")
        sd.wait()
        print("-> done. if you heard it, you're good.")

asyncio.run(main())
