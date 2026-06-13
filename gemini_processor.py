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

from config import GEMINI_API_KEY, GROQ_API_KEY, HF_API_TOKEN
from image_composer import make_gradient_bg

_gemini = genai.Client(api_key=GEMINI_API_KEY)
_groq   = Groq(api_key=GROQ_API_KEY)

GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"
IMAGEN_MODEL      = "imagen-3.0-generate-002"
QUOTE_PROMPT_FILE = Path("prompts/quote_prompt.txt")
IMAGE_PROMPT_FILE = Path("prompts/image_prompt.txt")

# Output canvas size: 4:5 portrait (1080×1350)
CANVAS_W, CANVAS_H = 1080, 1350


# ---------------------------------------------------------------------------
# Call 1 — Quote generation (Gemini 2.5 Flash primary → Groq fallback)
# ---------------------------------------------------------------------------

def _parse_quote_json(raw: str, source: str) -> dict:
    raw = re.sub(r"^```[a-z]*\n?", "", raw).strip()
    raw = re.sub(r"\n?```$", "", raw).strip()
    data = json.loads(raw)
    required = {"slide_1", "slide_2", "slide_3", "slide_4", "caption", "hashtags", "mood", "visual_theme"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"[{source}] Missing fields: {missing} | Raw: {raw[:200]}")
    return data


def generate_carousel(category: str) -> dict:
    """
    Generate 4-slide quote. Tries Gemini 2.5 Flash first, falls back to Groq.
    Raises RuntimeError only if both fail.
    """
    base_prompt = QUOTE_PROMPT_FILE.read_text().strip()
    full_prompt = f"Category / mood for today: {category}\n\n{base_prompt}"

    # ── Primary: Gemini 2.5 Flash ────────────────────────────────────
    print(f"  [gemini] Calling {GEMINI_TEXT_MODEL} for quote generation...")
    try:
        response = _gemini.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=full_prompt,
        )
        data = _parse_quote_json(response.text.strip(), "gemini")
        print(f"  [gemini] Quote OK")
        return data
    except Exception as exc:
        print(f"  [gemini] Failed ({exc.__class__.__name__}: {str(exc)[:120]}) → falling back to Groq...")

    # ── Fallback: Groq ───────────────────────────────────────────────
    print(f"  [groq] Calling {GROQ_TEXT_MODEL}...")
    try:
        response = _groq.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.9,
            max_tokens=1024,
        )
        data = _parse_quote_json(response.choices[0].message.content.strip(), "groq")
        print(f"  [groq] Quote OK")
        return data
    except Exception as exc:
        raise RuntimeError(
            f"[groq] Quote generation also failed: {exc}\n"
            "Check GROQ_API_KEY and GEMINI_API_KEY."
        ) from exc


# ---------------------------------------------------------------------------
# Call 2 — Image generation
# Priority: Imagen 3 → Hugging Face → Pollinations.ai → gradient
# ---------------------------------------------------------------------------

def _hf_image(prompt: str) -> Image.Image | None:
    """Hugging Face FLUX.1-schnell — free tier, no billing needed."""
    if not HF_API_TOKEN:
        return None
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt[:500]},
            timeout=90,
        )
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            img = Image.open(BytesIO(r.content)).convert("RGB")
            return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
        print(f"  [hf] Response {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [hf] Error: {e}")
    return None


def _pollinations_image(prompt: str, seed: int) -> Image.Image | None:
    """Pollinations.ai — free (rate-limited)."""
    encoded = urllib.parse.quote(prompt[:500])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1350&nologo=true&seed={seed}"
    for attempt in range(1, 3):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                img = Image.open(BytesIO(r.content)).convert("RGB")
                return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
            print(f"  [pollinations] Attempt {attempt}: {r.status_code}")
        except Exception as e:
            print(f"  [pollinations] Attempt {attempt} error: {e}")
        if attempt < 2:
            time.sleep(8)
    return None


def generate_slide_backgrounds(carousel: dict) -> list:
    """
    Image generation priority: Imagen 3 → Hugging Face → Pollinations.ai → gradient.
    Always returns 4 images — gradient is the guaranteed last resort.
    """
    template = IMAGE_PROMPT_FILE.read_text().strip()
    images   = []

    for i, slide_key in enumerate(["slide_1", "slide_2", "slide_3", "slide_4"], 1):
        slide_text = carousel[slide_key]
        prompt     = template.replace("[INSERT SLIDE TEXT HERE]", slide_text)
        img        = None

        print(f"  Slide {i}/4 — trying Imagen 3...")
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
            print(f"  Slide {i} ✓ Imagen 3")
        except Exception as exc:
            print(f"  Imagen 3 failed ({exc.__class__.__name__}) → trying Hugging Face...")

        if img is None:
            img = _hf_image(prompt)
            if img:
                print(f"  Slide {i} ✓ Hugging Face (FLUX.1-schnell)")
            else:
                print(f"  Hugging Face failed → trying Pollinations.ai...")

        if img is None:
            img = _pollinations_image(prompt, seed=i)
            if img:
                print(f"  Slide {i} ✓ Pollinations.ai")
            else:
                print(f"  Pollinations failed → using gradient fallback")

        if img is None:
            img = make_gradient_bg(carousel.get("mood", "mindset"))
            print(f"  Slide {i} ✓ gradient background")

        images.append(img)

    return images
