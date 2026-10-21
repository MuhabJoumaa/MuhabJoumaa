import json
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

BACKGROUND = PROFILE / "background.jpg"
STATS = PROFILE / "stats.svg"
LANGUAGES = PROFILE / "most-used-langs.svg"
OUTPUT = PROFILE / "github-dashboard.png"
LAYOUT = PROFILE / "layout.json"

WIDTH, HEIGHT = 1200, 650
CARD_MAX_WIDTH = 540
CARD_MAX_HEIGHT = 400
GAP = 40
CARD_OPACITY = 0.75

background = Image.open(BACKGROUND).convert("RGB")
ratio = max(WIDTH / background.width, HEIGHT / background.height)
background = background.resize((
    round(background.width * ratio),
    round(background.height * ratio),
))
left = (background.width - WIDTH) // 2
top = (background.height - HEIGHT) // 2
canvas = background.crop((
    left, top, left + WIDTH, top + HEIGHT
)).convert("RGBA")

cards = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=2)
    for svg_path in (STATS, LANGUAGES):
        page.goto(svg_path.resolve().as_uri())
        page.wait_for_timeout(1500)
        png = page.locator("svg").first.screenshot(omit_background=True)
        card = Image.open(BytesIO(png)).convert("RGBA")
        card.thumbnail((CARD_MAX_WIDTH, CARD_MAX_HEIGHT), Image.Resampling.LANCZOS)
        alpha = card.getchannel("A").point(lambda a: int(a * CARD_OPACITY))
        card.putalpha(alpha)
        cards.append(card)
    browser.close()

total_width = sum(c.width for c in cards) + GAP
max_height = max(c.height for c in cards)

x = (WIDTH - total_width) // 2
y = (HEIGHT - max_height) // 2

rects = []
for card in cards:
    canvas.alpha_composite(card, (x, y))
    rects.append([x, y, card.width, card.height])
    x += card.width + GAP

LAYOUT.write_text(json.dumps({"canvas": [WIDTH, HEIGHT], "cards": rects}))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
canvas.convert("RGB").save(OUTPUT, quality=95)

print(f"Dashboard created: {OUTPUT}")
