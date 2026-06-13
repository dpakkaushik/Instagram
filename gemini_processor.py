import json
import re
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from google import genai
from google.genai import types
from groq import Groq
from PIL import Image

from config import GEMINI_API_KEY, GROQ_API_KEY

_gemini = genai.Client(api_key=GEMINI_API_KEY)
_groq   = Groq(api_key=GROQ_API_KEY)

GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"
IMAGEN_MODEL      = "imagen-3.0-generate-002"
QUOTE_PROMPT_FILE = Path("prompts/quote_prompt.txt")
IMAGE_PROMPT_FILE = Path("prompts/image_prompt.txt")

# Output canvas size: 4:5 portrait (1080×1350)
CANVAS_W, CANVAS_H = 1080, 1350


# ---------------------------------------------------------------------------
# Call 1 — Quote generation (Groq — free tier, 14 400 req/day)
# ---------------------------------------------------------------------------

def generate_carousel(category: str) -> dict:
    """
    Ask Groq/Llama to write a 4-slide viral Instagram quote for the given category.
    Returns dict with keys: slide_1..4, caption, hashtags, mood, visual_theme.
    Raises RuntimeError on failure — caller must abort the run.
    """
    base_prompt = QUOTE_PROMPT_FILE.read_text().strip()
    full_prompt = f"Category / mood for today: {category}\n\n{base_prompt}"

    print(f"  [groq] Calling {GROQ_TEXT_MODEL} for quote generation...")
    try:
        response = _groq.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.9,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw.strip())
    except Exception as exc:
        raise RuntimeError(
            f"[groq] Quote generation failed: {type(exc).__name__}: {exc}\n"
            "Check GROQ_API_KEY at https://console.groq.com/keys"
        ) from exc

    required = {"slide_1", "slide_2", "slide_3", "slide_4", "caption", "hashtags", "mood", "visual_theme"}
    missing = required - data.keys()
    if missing:
        raise RuntimeError(
            f"[groq] Quote response missing fields: {missing}\n"
            f"Raw response was: {raw[:300]}"
        )

    return data


# ---------------------------------------------------------------------------
# Call 2 — Image generation (Imagen 3 primary, Pollinations.ai fallback)
# ---------------------------------------------------------------------------

def _pollinations_image(prompt: str, slide_num: int) -> Image.Image:
    """Fetch image from Pollinations.ai with 3 retries. Raises RuntimeError on total failure."""
    encoded = urllib.parse.quote(prompt[:500])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1350&nologo=true&seed={slide_num}"
    for attempt in range(1, 4):
        try:
            print(f"    [pollinations] Attempt {attempt}/3...")
            r = requests.get(url, timeout=120)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and "image" in ct:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
                return img
            print(f"    [pollinations] Bad response: {r.status_code} {ct}")
        except Exception as e:
            print(f"    [pollinations] Error: {e}")
        if attempt < 3:
            time.sleep(10)
    raise RuntimeError(f"[pollinations] All 3 attempts failed for slide {slide_num}.")


def generate_slide_backgrounds(carousel: dict) -> list:
    """
    Try Imagen 3 for each slide; fall back to Pollinations.ai if Imagen is unavailable.
    Raises RuntimeError if both fail for any slide — no partial posts.
    Returns list of 4 PIL Images (1080×1350).
    """
    template = IMAGE_PROMPT_FILE.read_text().strip()
    images = []

    for i, slide_key in enumerate(["slide_1", "slide_2", "slide_3", "slide_4"], 1):
        slide_text = carousel[slide_key]
        prompt = template.replace("[INSERT SLIDE TEXT HERE]", slide_text)

        print(f"  [imagen] Generating image for slide {i}/4...")
        img = None

        # ── Primary: Imagen 3 ────────────────────────────────────────
        try:
            response = _gemini.models.generate_images(
                model=IMAGEN_MODEL,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="3:4",
                    output_mime_type="image/jpeg",
                ),
            )
            image_bytes = response.generated_images[0].image.image_bytes
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            img = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
            print(f"  [imagen] Slide {i} OK via Imagen 3")
        except Exception as exc:
            print(f"  [imagen] Imagen 3 unavailable for slide {i}: {exc}")
            print(f"  [imagen] Falling back to Pollinations.ai...")

        # ── Fallback: Pollinations.ai ────────────────────────────────
        if img is None:
            img = _pollinations_image(prompt, i)
            print(f"  [pollinations] Slide {i} OK via Pollinations.ai")

        images.append(img)

    return images
