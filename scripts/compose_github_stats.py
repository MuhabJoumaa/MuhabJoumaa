from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

BACKGROUND = PROFILE / "background.jpg"
STATS = PROFILE / "stats.svg"
LANGUAGES = PROFILE / "most-used-langs.svg"
OUTPUT = PROFILE / "github-dashboard.png"

WIDTH, HEIGHT = 1200, 650

background = Image.open(BACKGROUND).convert("RGB")
ratio = max(WIDTH / background.width, HEIGHT / background.height)
background = background.resize((
    round(background.width * ratio),
    round(background.height * ratio),
))
left = (background.width - WIDTH) // 2
top = (background.height - HEIGHT) // 2
background = background.crop((
    left, top, left + WIDTH, top + HEIGHT
)).convert("RGBA")

shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 95))
canvas = Image.alpha_composite(background, shade)
draw = ImageDraw.Draw(canvas)

try:
    title_font = ImageFont.truetype("DejaVuSans.ttf", 30)
except OSError:
    title_font = ImageFont.load_default()

draw.text(
    (35, 25),
    "Muhab Joumaa | GITHUB STATISTICS",
    font=title_font,
    fill=(90, 255, 170, 255),
)

def load_svg(path, width):
    if not path.exists():
        raise FileNotFoundError(f"Missing SVG: {path}")

    png_bytes = cairosvg.svg2png(
        url=str(path),
        output_width=width,
    )
    return Image.open(BytesIO(png_bytes)).convert("RGBA")

def add_card(svg_path, x, y, width, height):
    panel = Image.new("RGBA", (width + 24, height + 24),
                      (8, 15, 25, 205))
    canvas.alpha_composite(panel, (x - 12, y - 12))

    card = load_svg(svg_path, width)
    card.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas.alpha_composite(card, (x, y))

add_card(STATS, 45, 110, 530, 260)
add_card(LANGUAGES, 625, 110, 530, 260)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
canvas.convert("RGB").save(OUTPUT, quality=95)

print(f"Dashboard created: {OUTPUT}")
