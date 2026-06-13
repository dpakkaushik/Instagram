import json
import re
from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_API_KEY

_gemini = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_TEXT_MODEL  = "gemini-2.0-flash"
IMAGEN_MODEL       = "imagen-3.0-generate-002"
QUOTE_PROMPT_FILE  = Path("prompts/quote_prompt.txt")
IMAGE_PROMPT_FILE  = Path("prompts/image_prompt.txt")

# Output canvas size: 4:5 portrait (1080×1350)
CANVAS_W, CANVAS_H = 1080, 1350


# ---------------------------------------------------------------------------
# Call 1 — Quote generation
# ---------------------------------------------------------------------------

def generate_carousel(category: str) -> dict:
    """
    Ask Gemini to write a 4-slide viral Instagram quote for the given category.
    Returns dict with keys: slide_1..4, caption, hashtags, mood, visual_theme.
    Raises RuntimeError on failure — caller must abort the run.
    """
    base_prompt = QUOTE_PROMPT_FILE.read_text().strip()
    full_prompt = f"Category / mood for today: {category}\n\n{base_prompt}"

    print(f"  [gemini] Calling {GEMINI_TEXT_MODEL} for quote generation...")
    try:
        response = _gemini.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=full_prompt,
        )
        raw = response.text.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw.strip())
    except Exception as exc:
        raise RuntimeError(
            f"[gemini] Quote generation failed: {type(exc).__name__}: {exc}\n"
            "Check GEMINI_API_KEY and model availability."
        ) from exc

    required = {"slide_1", "slide_2", "slide_3", "slide_4", "caption", "hashtags", "mood", "visual_theme"}
    missing = required - data.keys()
    if missing:
        raise RuntimeError(
            f"[gemini] Quote response missing fields: {missing}\n"
            f"Raw response was: {raw[:300]}"
        )

    return data


# ---------------------------------------------------------------------------
# Call 2 — Image generation (4 Imagen 3 calls, one per slide)
# ---------------------------------------------------------------------------

def generate_slide_backgrounds(carousel: dict) -> list:
    """
    Generate one Imagen 3 image per slide using the image prompt template.
    Each slide's text is inserted into the template individually for maximum relevance.
    Returns list of 4 PIL Images (1080×1350).
    Raises RuntimeError on any failure — caller must abort the run (no partial posts).
    """
    template = IMAGE_PROMPT_FILE.read_text().strip()
    images = []

    for i, slide_key in enumerate(["slide_1", "slide_2", "slide_3", "slide_4"], 1):
        slide_text = carousel[slide_key]
        prompt = template.replace("[INSERT SLIDE TEXT HERE]", slide_text)

        print(f"  [imagen] Generating image for slide {i}/4...")
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
            print(f"  [imagen] Slide {i} OK ({img.size[0]}x{img.size[1]})")
            images.append(img)

        except Exception as exc:
            raise RuntimeError(
                f"[imagen] Failed on slide {i} ({slide_key}): {type(exc).__name__}: {exc}\n"
                "Check that Imagen 3 is enabled on your Gemini API account (billing required). "
                "No partial post will be made."
            ) from exc

    return images
