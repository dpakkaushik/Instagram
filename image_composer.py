import textwrap
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CANVAS = (1080, 1350)   # 4:5 portrait
FONT_DIR = Path(__file__).parent / "fonts"

CATEGORY_COLORS: dict[str, tuple] = {
    "mindset":    (99,  102, 241),
    "growth":     (16,  185, 129),
    "love":       (244,  63,  94),
    "resilience": (245, 158,  11),
    "courage":    (239,  68,  68),
    "success":    (234, 179,   8),
    "peace":      (14,  165, 233),
    "wisdom":     (168,  85, 247),
}
DEFAULT_ACCENT = (255, 255, 255)

MOOD_COLORS: dict[int, tuple] = {
    1: (99,  102, 241),   # purple  — quiet exhaustion
    2: (245, 158,  11),   # amber   — bittersweet time
    3: (244,  63,  94),   # rose    — soft isolation
    4: (14,  165, 233),   # sky     — acceptance / letting go
}


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        FONT_DIR / filename,
        Path("C:/Windows/Fonts") / filename,
        Path("/usr/share/fonts/truetype/dejavu") / filename,
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _add_text_scrim(canvas: Image.Image) -> Image.Image:
    """Dark gradient over the full image so white text is always readable."""
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(CANVAS[1]):
        t = y / CANVAS[1]
        # Darker in the middle where the quote sits
        mid = abs(t - 0.5) * 2          # 0 at centre, 1 at edges
        alpha = int(160 + (1 - mid) * 60)
        d.line([(0, y), (CANVAS[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(canvas, overlay)


def _draw_quote(d: ImageDraw.ImageDraw, quote: str, accent: tuple) -> None:
    """Large centred quote text in the vertical middle of the card."""
    font = _load_font("RobotoBold.ttf", 72)
    wrapped = textwrap.fill(quote, width=18)
    lines = wrapped.splitlines()

    line_h = 92
    total_h = len(lines) * line_h
    start_y = (CANVAS[1] - total_h) // 2

    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (CANVAS[0] - tw) // 2
        # Soft shadow
        d.text((x + 3, start_y + 3), line, font=font, fill=(0, 0, 0, 140))
        d.text((x, start_y), line, font=font, fill="white")
        start_y += line_h


def _draw_accent_bar(d: ImageDraw.ImageDraw, accent: tuple) -> None:
    """Thin coloured bar at the very bottom — subtle brand mark."""
    bar_h = 6
    d.rectangle([(0, CANVAS[1] - bar_h), (CANVAS[0], CANVAS[1])], fill=accent)


def make_gradient_bg(mood_number: int = 1) -> Image.Image:
    """Fallback gradient if no template image is found."""
    accent = MOOD_COLORS.get(mood_number, DEFAULT_ACCENT)
    img = Image.new("RGB", CANVAS)
    pixels = img.load()
    w, h = CANVAS
    dark = (12, 12, 20)
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.4 + y / h * 0.6)
            r = int(dark[0] + (accent[0] - dark[0]) * t * 0.6)
            g = int(dark[1] + (accent[1] - dark[1]) * t * 0.6)
            b = int(dark[2] + (accent[2] - dark[2]) * t * 0.6)
            pixels[x, y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    return img


def compose_card(
    quote: str,
    mood_number: int,
    bg_image: Image.Image,
) -> Image.Image:
    accent = MOOD_COLORS.get(mood_number, DEFAULT_ACCENT)

    canvas = bg_image.resize(CANVAS, Image.LANCZOS).convert("RGBA")
    canvas = _add_text_scrim(canvas)

    d = ImageDraw.Draw(canvas)
    _draw_quote(d, quote, accent)
    _draw_accent_bar(d, accent)

    return canvas.convert("RGB")
