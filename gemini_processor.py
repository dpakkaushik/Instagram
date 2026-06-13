import json
import re
from pathlib import Path

from google import genai
from groq import Groq

from config import GEMINI_API_KEY, GROQ_API_KEY

_gemini = genai.Client(api_key=GEMINI_API_KEY)
_groq   = Groq(api_key=GROQ_API_KEY)

GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"
QUOTE_PROMPT_FILE = Path("prompts/quote_prompt.txt")


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
    """Generate 4-slide quote. Tries Gemini 2.5 Flash first, falls back to Groq."""
    base_prompt = QUOTE_PROMPT_FILE.read_text().strip()
    full_prompt = f"Category / mood for today: {category}\n\n{base_prompt}"

    # Primary: Gemini 2.5 Flash
    print(f"  [gemini] Calling {GEMINI_TEXT_MODEL}...")
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

    # Fallback: Groq
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
