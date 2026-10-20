
from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

BACKGROUND = PROFILE / "background.jpg"
STATS = PROFILE / "stats.svg"
LANGUAGES = PROFILE / "most-used-langs.svg"
OUTPUT = PROFILE / "github-dashboard.png"

WIDTH, HEIGHT = 1200, 650


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def parse_length(value):
    if not value:
        return None
    match = re.fullmatch(
        r"\s*([0-9]*\.?[0-9]+)(?:px)?\s*", value
    )
    return float(match.group(1)) if match else None


def is_full_canvas_rect(element, svg_width, svg_height):
    if local_name(element.tag) != "rect":
        return False

    x = parse_length(element.get("x", "0"))
    y = parse_length(element.get("y", "0"))
    w = element.get("width", "")
    h = element.get("height", "")

    full_width = (
        w.strip() == "100%"
        or (
            parse_length(w) is not None
            and svg_width is not None
            and abs(parse_length(w) - svg_width) < 1
        )
    )

    full_height = (
        h.strip() == "100%"
        or (
            parse_length(h) is not None
            and svg_height is not None
            and abs(parse_length(h) - svg_height) < 1
        )
    )

    return (
        x is not None and y is not None
        and abs(x) < 1 and abs(y) < 1
        and full_width and full_height
    )


def make_svg_transparent(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()

    width = parse_length(root.get("width"))
    height = parse_length(root.get("height"))

    viewbox = root.get("viewBox") or root.get("viewbox")
    if viewbox:
        values = viewbox.replace(",", " ").split()
        if len(values) == 4:
            if width is None:
                width = float(values[2])
            if height is None:
                height = float(values[3])

    for parent in root.iter():
        for child in list(parent):
            if is_full_canvas_rect(child, width, height):
                parent.remove(child)

    style = root.get("style", "")
    style = re.sub(
        r"background(?:-color)?\s*:[^;]+;?",
        "",
        style,
        flags=re.IGNORECASE,
    )
    root.set("style", style)

    return ET.tostring(root, encoding="utf-8")


def load_svg(svg_path, width):
    if not svg_path.exists():
        raise FileNotFoundError(f"Missing SVG file: {svg_path}")

    svg_bytes = make_svg_transparent(svg_path)

    png_bytes = cairosvg.svg2png(
        bytestring=svg_bytes,
        output_width=width,
    )

    return Image.open(BytesIO(png_bytes)).convert("RGBA")


background = Image.open(BACKGROUND).convert("RGB")

scale = max(WIDTH / background.width, HEIGHT / background.height)
background = background.resize((
    round(background.width * scale),
    round(background.height * scale),
))

left = (background.width - WIDTH) // 2
top = (background.height - HEIGHT) // 2

background = background.crop((
    left, top, left + WIDTH, top + HEIGHT
)).convert("RGBA")

overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 65))
canvas = Image.alpha_composite(background, overlay)

draw = ImageDraw.Draw(canvas)

try:
    title_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30
    )
except OSError:
    title_font = ImageFont.load_default()

draw.text(
    (35, 25),
    "Muhab Joumaa | GITHUB STATISTICS",
    font=title_font,
    fill=(80, 255, 170, 255),
)


def add_card(svg_path, x, y, width, max_height):
    card = load_svg(svg_path, width)

    if card.height > max_height:
        new_width = round(card.width * max_height / card.height)
        card = card.resize((
            new_width, max_height
        ), Image.Resampling.LANCZOS)

    canvas.alpha_composite(card, (x, y))


add_card(STATS, 45, 115, 530, 300)
add_card(LANGUAGES, 625, 115, 530, 300)

PROFILE.mkdir(parents=True, exist_ok=True)

canvas.convert("RGB").save(
    OUTPUT,
    format="PNG",
    optimize=True,
)

print(f"Dashboard created successfully: {OUTPUT}")
