# Insta Pipeline

Automated Instagram news pipeline:
RSS feeds → Gemini summarisation + image generation → 1080×1080 card → instagrapi post

---

## Stack

| Layer | Tool |
|---|---|
| News source | BBC, Guardian, Al Jazeera, NPR, Reuters (RSS, free, no key) |
| AI processing | Gemini 2.0 Flash (summary + caption + image gen) |
| Card design | Pillow (1080×1080 JPEG) |
| Instagram | instagrapi |
| Scheduler | schedule (runs every N hours) |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download fonts + create .env
python setup.py

# 3. Fill in .env
#    GEMINI_API_KEY, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

# 4. Dry run (generates images, skips posting)
python main.py --dry

# 5. Single real run
python main.py --once

# 6. Scheduled runs (default: every 6 hours)
python main.py
```

---

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | required | Google AI Studio key |
| `INSTAGRAM_USERNAME` | required | Instagram username |
| `INSTAGRAM_PASSWORD` | required | Instagram password |
| `NEWS_TOPIC` | `world news` | Topic filter for news |
| `POST_COUNT` | `5` | Articles per run |
| `POST_INTERVAL_HOURS` | `6` | Hours between scheduled runs |

---

## Output

Generated cards are saved to `output/card_<id>_<n>.jpg` before posting.

---

## Notes

- First login creates `session.json` — subsequent runs reuse it to avoid repeated logins
- instagrapi is an unofficial library; use a secondary account if concerned about ToS
- Gemini image generation falls back to a coloured gradient if the model is unavailable
- Instagram allows ~25 posts/day; 5 posts every 6 hours = 20/day (within limit)
