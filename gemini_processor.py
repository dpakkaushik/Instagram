import json
import re
from io import BytesIO

import requests
from google import genai
from PIL import Image

from config import GEMINI_API_KEY

_gemini = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_TEXT_MODEL = "gemini-2.0-flash"


def summarize_news(article: dict) -> dict:
    """Return headline, caption, hashtags, image_prompt via Gemini 2.0 Flash."""
    prompt = f"""You are a viral Instagram news content creator.
Given this news article, produce SENSATIONAL, attention-grabbing Instagram content that stops the scroll.

Title:   {article['title']}
Source:  {article['source']}
Summary: {article.get('summary', '')[:500]}

Rules:
- Headline: dramatic, urgent, emotionally charged — max 80 chars
- Caption: 2-3 sentences, conversational, creates urgency or curiosity
- Hashtags: 6 relevant trending hashtags
- Image prompt: vivid cinematic scene matching the story, no text, photorealistic

Reply with ONLY valid JSON (no markdown, no code fences):
{{
  "headline":     "SHOCKING: Something urgent happened!",
  "caption":      "2-3 sentence engaging caption, max 220 chars",
  "hashtags":     "#tag1 #tag2 #tag3 #tag4 #tag5 #tag6",
  "image_prompt": "Detailed photorealistic background image prompt, no text, cinematic lighting"
}}"""

    try:
        response = _gemini.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        raw = response.text.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw.strip())
    except Exception:
        pass

    return {
        "headline":     article["title"][:80],
        "caption":      article.get("summary", "")[:220],
        "hashtags":     "#news #breakingnews #world #latest #trending",
        "image_prompt": f"News photography, {article['title'][:60]}, professional, cinematic",
    }


def generate_background_image(prompt: str) -> Image.Image | None:
    """Generate background via Pollinations.ai (free, no key). Falls back to None (gradient) on failure."""
    full_prompt = (
        f"Cinematic photorealistic news background: {prompt}. "
        "No text, no watermarks, dramatic lighting, professional journalism style, 4K."
    )
    url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(full_prompt)

    for attempt in range(3):
        try:
            print(f"  [image] Attempt {attempt + 1}/3...")
            r = requests.get(
                url,
                params={"width": 1080, "height": 1080, "nologo": "true", "model": "flux"},
                timeout=120,
            )
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            if "image" not in content_type:
                print(f"  [image] Unexpected content-type: {content_type} — retrying")
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            print(f"  [image] Generated ({img.size[0]}x{img.size[1]})")
            return img
        except Exception as exc:
            print(f"  [image] Attempt {attempt + 1} failed: {type(exc).__name__}: {exc}")

    print("  [image] All attempts failed — using gradient fallback")
    return None
