"""
Instagram Reel Pipeline — main entry point.

Usage:
  python main.py          # run once now, then every N hours
  python main.py --once   # run exactly once and exit
  python main.py --dry    # generate everything, skip posting
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import schedule

from config import QUOTE_CATEGORY, POST_INTERVAL_HOURS
from gemini_processor import generate_carousel, generate_slide_backgrounds
from image_composer import compose_card
from instagram_poster import post_carousel

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

DRY_RUN = "--dry" in sys.argv


def _pick_category() -> str:
    categories = [c.strip() for c in QUOTE_CATEGORY.split(",") if c.strip()]
    if len(categories) <= 1:
        return QUOTE_CATEGORY.strip()
    now = datetime.now()
    idx = (now.hour * 4 + now.minute // 15) % len(categories)
    return categories[idx]


def run_pipeline() -> None:
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_id   = datetime.now().strftime("%Y%m%d_%H%M%S")
    category = _pick_category()

    print(f"\n{'='*60}")
    print(f"  Instagram Reel Pipeline — {ts}")
    print(f"  Category: {category}  |  Dry run: {DRY_RUN}")
    print(f"{'='*60}")

    try:
        # ── STEP 1: Generate 4-slide quote ───────────────────────────
        print("\n[1/5] Generating quote (Gemini text)...")
        carousel = generate_carousel(category)
        print(f"  Mood       : {carousel['mood']}")
        print(f"  Slide 1    : {carousel['slide_1']}")
        print(f"  Slide 2    : {carousel['slide_2']}")
        print(f"  Slide 3    : {carousel['slide_3']}")
        print(f"  Slide 4    : {carousel['slide_4']}")
        print(f"  Theme      : {carousel['visual_theme']}")

        # ── STEP 2: Generate slide backgrounds ───────────────────────
        print("\n[2/4] Generating backgrounds...")
        bg_images = generate_slide_backgrounds(carousel)

        # ── STEP 3: Compose slide cards ──────────────────────────────
        print("\n[3/4] Composing slide cards...")
        image_paths = []
        slide_keys  = ["slide_1", "slide_2", "slide_3", "slide_4"]

        for i, (key, bg) in enumerate(zip(slide_keys, bg_images), 1):
            card = compose_card(
                slide_text   = carousel[key],
                slide_num    = i,
                total_slides = 4,
                bg_image     = bg,
                category     = category,
            )
            path = OUTPUT_DIR / f"slide_{run_id}_{i:02d}.jpg"
            card.save(str(path), "JPEG", quality=95)
            image_paths.append(str(path))
            print(f"  Slide {i}/4 saved: {path.name}")

        # ── STEP 4: Post ─────────────────────────────────────────────
        ig_caption = (
            f"{carousel['caption']}\n\n"
            f"{carousel['hashtags']}"
        )

        if DRY_RUN:
            print("\n[4/4] DRY RUN — skipping post")
            print(f"  Caption preview:\n  {ig_caption[:200]}")
            print(f"\n  Output files in: {OUTPUT_DIR.resolve()}")
        else:
            print("\n[4/4] Posting carousel to Instagram...")
            url = post_carousel(image_paths, ig_caption)
            print(f"\n  POSTED: {url}")

        print(f"\n{'='*60}")
        print(f"  Pipeline complete — {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n{'!'*60}")
        print(f"  PIPELINE FAILED")
        print(f"  Error type : {type(exc).__name__}")
        print(f"  Message    : {exc}")
        print(f"{'!'*60}")
        print(traceback.format_exc())
        print("  Run aborted — no post was made.\n")
        sys.exit(1)


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
