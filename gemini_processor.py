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
    try:
        url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(full_prompt)
        r = requests.get(
            url,
            params={"width": 1080, "height": 1080, "nologo": "true", "model": "flux"},
            timeout=90,
        )
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as exc:
        print(f"  [image] Generation failed ({type(exc).__name__}), using gradient")
    return None
