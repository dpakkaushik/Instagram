"""
Insta Pipeline — main entry point.

Usage:
  python main.py          # run once now, then every N hours (set in .env)
  python main.py --once   # run exactly once and exit
  python main.py --dry    # fetch + generate images, skip posting
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

from config import NEWS_TOPIC, POST_COUNT, POST_INTERVAL_HOURS
from news_fetcher import fetch_news

def _pick_topic() -> str:
    topics = [t.strip() for t in NEWS_TOPIC.split(",") if t.strip()]
    if len(topics) <= 1:
        return NEWS_TOPIC.strip()
    idx = (datetime.now().hour // 2) % len(topics)
    return topics[idx]
from gemini_processor import summarize_news, generate_background_image
from image_composer import compose_card
from instagram_poster import post_image

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

DRY_RUN = "--dry" in sys.argv


def run_pipeline() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    topic = _pick_topic()
    print(f"\n{'='*56}")
    print(f"  Pipeline started at {ts}")
    print(f"  Topic: '{topic}'  |  Count: {POST_COUNT}  |  Dry: {DRY_RUN}")
    print(f"{'='*56}")

    articles = fetch_news(topic=topic, count=POST_COUNT)
    if not articles:
        print("[pipeline] No articles fetched — aborting run")
        return

    print(f"[pipeline] Fetched {len(articles)} articles\n")
    posted = 0

    for idx, article in enumerate(articles, 1):
        short_title = article["title"][:60]
        print(f"[{idx}/{len(articles)}] {short_title}...")

        try:
            # 1 — Summarise with Gemini
            print("  · Summarising with Gemini...")
            processed = summarize_news(article)

            # 2 — Generate background image
            print("  · Generating background image...")
            bg = generate_background_image(processed["image_prompt"])

            # 3 — Compose card
            print("  · Composing 1080×1080 card...")
            card = compose_card(
                headline=processed["headline"],
                caption=processed["caption"],
                source=article["source"],
                bg_image=bg,
            )

            # 4 — Save to disk
            img_path = OUTPUT_DIR / f"card_{article['id']}_{idx:02d}.jpg"
            card.save(str(img_path), "JPEG", quality=95)
            print(f"  · Saved: {img_path}")

            # 5 — Build caption
            ig_caption = (
                f"{processed['headline']}\n\n"
                f"{processed['caption']}\n\n"
                f"{processed['hashtags']}\n\n"
                f"Source: {article['source']}"
            )

            # 6 — Post
            if DRY_RUN:
                print("  · [DRY RUN] Skipping post")
            else:
                print("  · Posting to Instagram...")
                url = post_image(str(img_path), ig_caption)
                print(f"  DONE Live -> {url}")
                posted += 1

            # Polite gap between posts
            if idx < len(articles) and not DRY_RUN:
                print("  · Waiting 30 s before next post...")
                time.sleep(30)

        except Exception as exc:
            print(f"  ERROR on article {idx}: {exc}")
            continue

    label = "generated" if DRY_RUN else "posted"
    print(f"\n[pipeline] Done — {posted if not DRY_RUN else len(articles)} cards {label}.\n")


if __name__ == "__main__":
    if "--once" in sys.argv or "--dry" in sys.argv:
        run_pipeline()
    else:
        print(f"[scheduler] Running now, then every {POST_INTERVAL_HOURS} hour(s). Ctrl+C to stop.\n")
        run_pipeline()
        schedule.every(POST_INTERVAL_HOURS).hours.do(run_pipeline)
        while True:
            schedule.run_pending()
            time.sleep(60)
