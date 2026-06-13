import textwrap
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CANVAS = (1080, 1350)   # 4:5 portrait for Instagram Reels / feed
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
    """Dark gradient over the bottom half so white text is always readable."""
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    scrim_start = int(CANVAS[1] * 0.42)
    for y in range(scrim_start, CANVAS[1]):
        t = (y - scrim_start) / (CANVAS[1] - scrim_start)
        alpha = int(200 * t)
        d.line([(0, y), (CANVAS[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(canvas, overlay)


def _draw_slide_text(d: ImageDraw.ImageDraw, slide_text: str) -> None:
    """Large centered quote text in the lower-center of the card."""
    font = _load_font("RobotoBold.ttf", 66)
    wrapped = textwrap.fill(slide_text, width=20)
    lines = wrapped.splitlines()

    line_h = 82
    total_h = len(lines) * line_h
    start_y = int(CANVAS[1] * 0.52) - total_h // 2

    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (CANVAS[0] - tw) // 2
        # Shadow
        d.text((x + 2, start_y + 2), line, font=font, fill=(0, 0, 0, 160))
        # Text
        d.text((x, start_y), line, font=font, fill="white")
        start_y += line_h


def _draw_slide_indicator(d: ImageDraw.ImageDraw, slide_num: int, total: int, accent: tuple) -> None:
    """Dot indicators bottom-center: ● ● ○ ○"""
    dot_r = 6
    gap = 22
    total_w = total * (dot_r * 2) + (total - 1) * (gap - dot_r * 2)
    start_x = (CANVAS[0] - total_w) // 2
    y = CANVAS[1] - 52

    for i in range(1, total + 1):
        cx = start_x + (i - 1) * gap
        fill = accent if i == slide_num else (120, 120, 120)
        d.ellipse([cx - dot_r, y - dot_r, cx + dot_r, y + dot_r], fill=fill)


def _draw_brand(d: ImageDraw.ImageDraw) -> None:
    """Small brand label top-center."""
    font = _load_font("Roboto.ttf", 22)
    label = "Daily Wisdom"
    bbox = d.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    d.text(((CANVAS[0] - tw) // 2, 28), label, font=font, fill=(200, 200, 200, 180))


def make_gradient_bg(category: str) -> Image.Image:
    """Generate a rich dark-to-accent diagonal gradient background."""
    accent = CATEGORY_COLORS.get(category.lower(), DEFAULT_ACCENT)
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
    slide_text: str,
    slide_num: int,
    total_slides: int,
    bg_image: Image.Image,
    category: str = "mindset",
) -> Image.Image:
    accent = CATEGORY_COLORS.get(category.lower(), DEFAULT_ACCENT)

    canvas = bg_image.resize(CANVAS, Image.LANCZOS).convert("RGBA")
    canvas = _add_text_scrim(canvas)

    d = ImageDraw.Draw(canvas)
    _draw_brand(d)
    _draw_slide_text(d, slide_text)
    _draw_slide_indicator(d, slide_num, total_slides, accent)

    return canvas.convert("RGB")
