import textwrap
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CANVAS = (1080, 1080)
FONT_DIR = Path(__file__).parent / "fonts"

# Accent colours per source
SOURCE_COLORS: dict[str, tuple[int, int, int]] = {
    "BBC World":    (187, 0,   0),
    "The Guardian": (0,   82,  147),
    "Al Jazeera":   (0,   154, 68),
    "NPR":          (43,  108, 176),
    "Reuters":      (255, 140, 0),
    "Hacker News":  (255, 102, 0),
}
DEFAULT_ACCENT = (220, 50, 50)


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        FONT_DIR / filename,
        Path("C:/Windows/Fonts") / filename,
        Path("/usr/share/fonts/truetype/dejavu") / filename,
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    # Built-in bitmap fallback — will look rough but never crash
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background helpers
# ---------------------------------------------------------------------------

def _gradient(color1: tuple, color2: tuple) -> Image.Image:
    img = Image.new("RGB", CANVAS)
    draw = ImageDraw.Draw(img)
    for y in range(CANVAS[1]):
        t = y / CANVAS[1]
        r = int(color1[0] * (1 - t) + color2[0] * t)
        g = int(color1[1] * (1 - t) + color2[1] * t)
        b = int(color1[2] * (1 - t) + color2[2] * t)
        draw.line([(0, y), (CANVAS[0], y)], fill=(r, g, b))
    return img


def _prepare_background(bg: Image.Image | None, accent: tuple) -> Image.Image:
    if bg:
        base = bg.resize(CANVAS, Image.LANCZOS).filter(ImageFilter.GaussianBlur(4))
    else:
        dark = tuple(max(0, c - 70) for c in accent)
        base = _gradient(accent, dark)  # type: ignore[arg-type]
    return base.convert("RGBA")


# ---------------------------------------------------------------------------
# Overlay layers
# ---------------------------------------------------------------------------

def _add_overlays(canvas: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Top bar dark strip
    d.rectangle([0, 0, CANVAS[0], 96], fill=(0, 0, 0, 170))

    # Bottom-half dark vignette for text legibility
    for y in range(int(CANVAS[1] * 0.38), CANVAS[1]):
        t = (y - CANVAS[1] * 0.38) / (CANVAS[1] * 0.62)
        alpha = int(210 * t)
        d.line([(0, y), (CANVAS[0], y)], fill=(0, 0, 0, alpha))

    # Bottom bar solid strip
    d.rectangle([0, CANVAS[1] - 76, CANVAS[0], CANVAS[1]], fill=(0, 0, 0, 210))

    return Image.alpha_composite(canvas, overlay)


# ---------------------------------------------------------------------------
# Text + badge drawing
# ---------------------------------------------------------------------------

def _draw_source_badge(d: ImageDraw.ImageDraw, source: str, accent: tuple) -> None:
    label = source.upper()[:18]
    font = _load_font("RobotoBold.ttf", 24)
    bbox = d.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    pill_w = tw + 28
    d.rounded_rectangle([28, 22, 28 + pill_w, 74], radius=10, fill=accent)
    d.text((42, 34), label, font=font, fill="white")


def _draw_live_badge(d: ImageDraw.ImageDraw) -> None:
    font = _load_font("RobotoBold.ttf", 20)
    label = "LATEST"
    d.rounded_rectangle([CANVAS[0] - 160, 26, CANVAS[0] - 28, 70],
                        radius=10, fill=(220, 30, 30))
    d.text((CANVAS[0] - 148, 38), label, font=font, fill="white")


def _draw_headline(d: ImageDraw.ImageDraw, headline: str) -> int:
    font = _load_font("RobotoBold.ttf", 58)
    wrapped = textwrap.fill(headline, width=24)
    y = 590
    for line in wrapped.splitlines()[:4]:
        d.text((52, y), line, font=font, fill="white",
               stroke_width=2, stroke_fill=(0, 0, 0, 180))
        y += 72
    return y


def _draw_caption(d: ImageDraw.ImageDraw, caption: str, start_y: int) -> None:
    font = _load_font("Roboto.ttf", 30)
    wrapped = textwrap.fill(caption, width=40)
    y = start_y + 12
    for line in wrapped.splitlines()[:3]:
        d.text((52, y), line, font=font, fill=(215, 215, 215),
               stroke_width=1, stroke_fill=(0, 0, 0, 120))
        y += 42


def _draw_footer(d: ImageDraw.ImageDraw, accent: tuple) -> None:
    font = _load_font("Roboto.ttf", 22)
    today = date.today().strftime("%B %d, %Y")
    # Accent line above footer bar
    d.line([(0, CANVAS[1] - 76), (CANVAS[0], CANVAS[1] - 76)], fill=accent, width=3)
    d.text((32, CANVAS[1] - 54), f"InstaNews Pipeline  •  {today}",
           font=font, fill=(175, 175, 175))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_card(
    headline: str,
    caption: str,
    source: str,
    bg_image: Image.Image | None,
) -> Image.Image:
    accent = SOURCE_COLORS.get(source, DEFAULT_ACCENT)

    canvas = _prepare_background(bg_image, accent)
    canvas = _add_overlays(canvas)

    d = ImageDraw.Draw(canvas)
    _draw_source_badge(d, source, accent)
    _draw_live_badge(d)
    caption_start = _draw_headline(d, headline)
    _draw_caption(d, caption, caption_start)
    _draw_footer(d, accent)

    return canvas.convert("RGB")
