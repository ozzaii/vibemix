"""Generate the bat mascot via Gemini 3.1 Flash Image (Nano Banana 2).
Saves to bat.png. Run multiple times for variations."""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROMPT = """Generate a single image of a neon cyberpunk gothic vampire bat mascot.

Subject: anatomically detailed bat with leathery wings spread wide, deep navy black
fur and skin with subtle iridescent purple highlights, bone structure visible through
the wing membrane glowing faintly magenta, electric cyan eyes radiating bright glow,
sharp white fangs slightly visible, alert pose facing forward and slightly upward.

Style: cinematic creature design, dramatic rim lighting from behind creating a glowing
halo around the wings, photorealistic with painterly texture, occult mystical atmosphere,
slightly menacing but elegant, looks like a magical familiar.

Composition: full body centered in frame, isolated subject, pure black background fading
to navy at the edges, no other elements, no text, no watermark, the bat fills about 70%
of the frame, square 1:1 aspect ratio.

Quality: ultra detailed, 4k, sharp focus on the eyes."""

OUT_DIR = Path(__file__).parent
MODEL = "gemini-3.1-flash-image-preview"


def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    print(f"-> generating with {MODEL}...")
    t0 = time.time()
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    n = 0
    suffix = sys.argv[1] if len(sys.argv) > 1 else ""
    for cand in response.candidates:
        for part in cand.content.parts:
            if part.inline_data and part.inline_data.data:
                name = f"bat{suffix}_{n}.png" if (suffix or n) else "bat.png"
                path = OUT_DIR / name
                path.write_bytes(part.inline_data.data)
                print(f"-> wrote {path} ({len(part.inline_data.data)//1024} KB)")
                n += 1
            elif part.text:
                print(f"-> model said: {part.text[:200]}")
    if n == 0:
        sys.exit("no image returned")
    print(f"-> done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
