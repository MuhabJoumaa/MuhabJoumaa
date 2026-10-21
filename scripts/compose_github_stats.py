import json
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

BACKGROUND = PROFILE / "background.jpg"
OUTPUT = PROFILE / "github-dashboard.png"
LAYOUT = PROFILE / "layout.json"

COLUMNS = [
    [PROFILE / "stats.svg"],
    [PROFILE / "most-used-langs.svg"],
]

WIDTH, HEIGHT = 1200, 720
MARGIN_X = 40
MARGIN_TOP = 40
MARGIN_BOTTOM = 40
COLUMN_GAP = 40
CARD_GAP = 20
CARD_OPACITY = 0.75
RENDER_SCALE = 3

PROFILE_DETAILS_X = 40
PROFILE_DETAILS_Y = 440
PROFILE_DETAILS_WIDTH = 850
PROFILE_DETAILS_HEIGHT = None

background = Image.open(BACKGROUND).convert("RGB")

ratio = max(
    WIDTH / background.width,
    HEIGHT / background.height,
)

background = background.resize((
    round(background.width * ratio),
    round(background.height * ratio),
))

left = (background.width - WIDTH) // 2
top = (background.height - HEIGHT) // 2

canvas = background.crop((
    left,
    top,
    left + WIDTH,
    top + HEIGHT,
)).convert("RGBA")

profile_details_path = PROFILE / "profile-details.svg"

all_svg_paths = [
    path
    for column in COLUMNS
    for path in column
]

all_svg_paths.append(profile_details_path)

rendered = {}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=RENDER_SCALE)

    for svg_path in all_svg_paths:
        page.goto(svg_path.resolve().as_uri())
        page.wait_for_timeout(1500)

        png = page.locator("svg").first.screenshot(
            omit_background=True
        )

        rendered[svg_path] = Image.open(
            BytesIO(png)
        ).convert("RGBA")

    browser.close()

column_width = (
    WIDTH
    - 2 * MARGIN_X
    - (len(COLUMNS) - 1) * COLUMN_GAP
) // len(COLUMNS)

available = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
rects = []

for column_index, column in enumerate(COLUMNS):
    natural_heights = [
        column_width * rendered[path].height / rendered[path].width
        for path in column
    ]

    gaps = CARD_GAP * (len(column) - 1)
    total_natural_height = sum(natural_heights)

    fit = min(
        1.0,
        (available - gaps) / total_natural_height,
    )

    card_width = round(column_width * fit)

    x = (
        MARGIN_X
        + column_index * (column_width + COLUMN_GAP)
        + (column_width - card_width) // 2
    )

    y = MARGIN_TOP

    for path in column:
        card = rendered[path]

        card_height = round(
            card_width * card.height / card.width
        )

        card = card.resize(
            (card_width, card_height),
            Image.Resampling.LANCZOS,
        )

        alpha = card.getchannel("A").point(
            lambda a: int(a * CARD_OPACITY)
        )
        card.putalpha(alpha)

        canvas.alpha_composite(card, (x, y))
        rects.append([x, y, card_width, card_height])

        y += card_height + CARD_GAP

profile_card = rendered[profile_details_path]
profile_width = PROFILE_DETAILS_WIDTH

if PROFILE_DETAILS_HEIGHT is None:
    profile_height = round(
        profile_width * profile_card.height / profile_card.width
    )
else:
    profile_height = PROFILE_DETAILS_HEIGHT

profile_card = profile_card.resize(
    (profile_width, profile_height),
    Image.Resampling.LANCZOS,
)

alpha = profile_card.getchannel("A").point(
    lambda a: int(a * CARD_OPACITY)
)
profile_card.putalpha(alpha)

canvas.alpha_composite(
    profile_card,
    (PROFILE_DETAILS_X, PROFILE_DETAILS_Y),
)

rects.append([
    PROFILE_DETAILS_X,
    PROFILE_DETAILS_Y,
    profile_width,
    profile_height,
])

LAYOUT.parent.mkdir(parents=True, exist_ok=True)

LAYOUT.write_text(
    json.dumps({
        "canvas": [WIDTH, HEIGHT],
        "cards": rects,
    }, indent=2),
    encoding="utf-8",
)

canvas.convert("RGB").save(OUTPUT, quality=95)

print(f"Dashboard created: {OUTPUT}")
print(f"Layout saved: {LAYOUT}")
print(
    "Profile details position:",
    PROFILE_DETAILS_X,
    PROFILE_DETAILS_Y,
)
print(
    "Profile details size:",
    profile_width,
    profile_height,
    )
