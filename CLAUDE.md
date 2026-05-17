# Insta Pipeline — Claude Code Context

## What this project does

Automated Instagram news pipeline:
**RSS feeds → Groq (text AI) → Gemini (image AI) → Pillow (card) → Selenium (Instagram post)**

Runs on a schedule (default every 1 hour) or manually with `--once` / `--dry`.

---

## File map

| File | Role |
|---|---|
| `main.py` | Orchestrator — CLI flags, scheduler loop, calls each stage |
| `news_fetcher.py` | RSS ingestion (BBC, Guardian, Al Jazeera, NPR, Reuters, HN) |
| `gemini_processor.py` | Groq text summarisation + Gemini image generation |
| `image_composer.py` | Pillow 1080×1080 card composer |
| `instagram_poster.py` | undetected-chromedriver + Selenium Instagram uploader |
| `config.py` | Loads `.env` values; raises on missing required keys |
| `setup.py` | One-time setup: downloads fonts, creates `.env` from example |

---

## Environment variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | yes | — | Google AI Studio key |
| `GROQ_API_KEY` | yes | — | Groq console key (free, 14 400 req/day) |
| `INSTAGRAM_USERNAME` | yes | — | Instagram account username |
| `INSTAGRAM_PASSWORD` | yes | — | Instagram account password |
| `INSTAGRAM_SESSION_ID` | no | — | Optional session cookie (not used in code currently) |
| `NEWS_TOPIC` | no | `world news` | Keyword filter bubbled to top of article list |
| `POST_COUNT` | no | `5` | Articles processed per run |
| `POST_INTERVAL_HOURS` | no | `6` | Gap between scheduled runs |

---

## How to run

```bash
# Install dependencies (see Known issues re: requirements.txt)
pip install -r requirements.txt
pip install undetected-chromedriver groq schedule

# One-time font + .env setup
python setup.py

# Dry run — generates cards, skips posting
python main.py --dry

# Single real run
python main.py --once

# Scheduled loop (every POST_INTERVAL_HOURS)
python main.py
```

---

## AI stack

- **Text** — Groq `llama-3.1-8b-instant` via `groq` SDK. Produces `headline`, `caption`, `hashtags`, `image_prompt` as JSON.
- **Image** — Gemini `gemini-2.5-flash-image` via `google-genai` SDK. Falls back to a colour gradient if the model is unavailable.

---

## Instagram posting mechanism

Uses **undetected-chromedriver + Selenium** (browser automation), NOT the Instagram API or instagrapi.

- Session is persisted to `instagram_cookies.json` after first login.
- Human-like typing delays and random sleeps are used to reduce bot detection.
- Chrome profile data lives in `chrome_profile/`.
- Instagram rate limit: ~25 posts/day. Current default (2 posts/hour) stays well within this.

---

## Output

Cards saved to `output/card_<id>_<nn>.jpg` (1080×1080 JPEG, quality 95) before posting.

---

## Known issues

1. **`requirements.txt` is outdated** — lists `instagrapi` (not used) and is missing `undetected-chromedriver`, `groq`, `schedule`.
2. **`.env.example` missing `GROQ_API_KEY`** — required by `config.py`, will raise on startup if absent.
3. **README says "instagrapi"** — actual implementation uses Selenium browser automation.
4. **Font fallback** — if Roboto fonts are absent from `fonts/` and `C:/Windows/Fonts`, Pillow falls back to a bitmap font that renders poorly on cards.
