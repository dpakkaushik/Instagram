"""
One-time setup: download Roboto fonts from Google APIs into ./fonts/
Run: python setup.py
"""

import urllib.request
from pathlib import Path
import zipfile
import io

FONT_DIR = Path("fonts")
FONT_DIR.mkdir(exist_ok=True)

FONTS = {
    "Roboto.ttf":         "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "RobotoBold.ttf":     "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "RobotoLight.ttf":    "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Light.ttf",
}

def download_fonts() -> None:
    print("Downloading Roboto fonts...")
    for filename, url in FONTS.items():
        dest = FONT_DIR / filename
        if dest.exists():
            print(f"  ✓ {filename} already present")
            continue
        try:
            print(f"  >> {filename} ...")
            urllib.request.urlretrieve(url, dest)
            print(f"  OK {filename}")
        except Exception as exc:
            print(f"  FAIL: {filename}: {exc}")
            print("    Falling back to Pillow's built-in font (lower quality)")

def check_env() -> None:
    from pathlib import Path
    if not Path(".env").exists():
        import shutil
        shutil.copy(".env.example", ".env")
        print("\n.env created from .env.example — fill in your credentials before running.")
    else:
        print("\n.env already exists.")

if __name__ == "__main__":
    download_fonts()
    check_env()
    print("\nSetup complete. Next steps:")
    print("  1. Edit .env with your GEMINI_API_KEY, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD")
    print("  2. pip install -r requirements.txt")
    print("  3. python main.py --dry     # test without posting")
    print("  4. python main.py --once    # run once and post")
    print("  5. python main.py           # run on schedule")
