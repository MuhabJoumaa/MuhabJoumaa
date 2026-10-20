from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

DASHBOARD = PROFILE / "github-dashboard.png"
CURTAIN = PROFILE / "curtain.gif"
OUTPUT = PROFILE / "github-dashboard.gif"

BLACK_THRESHOLD = 15
EDGE_BLUR = 1.2
FRAME_STEP = 3
OUTPUT_WIDTH = 800
PALETTE_COLORS = 128
CURTAIN_STRETCH = 1.3

TEXT_MS = 500
NAME_TEXT = "Muhab Joumaa"
ROLE_TEXT = "Softwareentwickler"
NAME_COLOR = (255, 255, 255)
ROLE_COLOR = (90, 255, 170)
NAME_SIZE = 0.07
ROLE_SIZE = 0.04
FONT_NAMES = ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "Arial.ttf"]


def pick_font(pixels):
    for font_name in FONT_NAMES:
        try:
            return ImageFont.truetype(font_name, pixels)
        except OSError:
            continue
    return ImageFont.load_default(pixels)

HOLD_OPEN_MS = 4000
PLAY_CLOSING = True

dashboard = Image.open(DASHBOARD).convert("RGBA")
if OUTPUT_WIDTH and OUTPUT_WIDTH < dashboard.width:
    new_height = round(dashboard.height * OUTPUT_WIDTH / dashboard.width)
    dashboard = dashboard.resize((OUTPUT_WIDTH, new_height), Image.Resampling.LANCZOS)
size = dashboard.size

name_font = pick_font(round(size[0] * NAME_SIZE))
role_font = pick_font(round(size[0] * ROLE_SIZE))

measure = ImageDraw.Draw(Image.new("RGBA", size))
name_box = measure.textbbox((0, 0), NAME_TEXT, font=name_font)
role_box = measure.textbbox((0, 0), ROLE_TEXT, font=role_font)
name_w, name_h = name_box[2] - name_box[0], name_box[3] - name_box[1]
role_w, role_h = role_box[2] - role_box[0], role_box[3] - role_box[1]

gap = round(size[1] * 0.03)
top = (size[1] - (name_h + gap + role_h)) // 2
name_pos = ((size[0] - name_w) // 2 - name_box[0], top - name_box[1])
role_pos = ((size[0] - role_w) // 2 - role_box[0], top + name_h + gap - role_box[1])

text_layer = Image.new("RGBA", size, (0, 0, 0, 0))
shadow = Image.new("RGBA", size, (0, 0, 0, 0))
for layer, name_fill, role_fill in (
    (text_layer, NAME_COLOR + (255,), ROLE_COLOR + (255,)),
    (shadow, (0, 0, 0, 255), (0, 0, 0, 255)),
):
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text(name_pos, NAME_TEXT, font=name_font, fill=name_fill)
    layer_draw.text(role_pos, ROLE_TEXT, font=role_font, fill=role_fill)
shadow = shadow.filter(ImageFilter.GaussianBlur(size[0] * 0.008))

frames = []
durations = []
revealed_ratio = []

with Image.open(CURTAIN) as curtain:
    for index, frame in enumerate(ImageSequence.Iterator(curtain)):
        if index % FRAME_STEP:
            continue

        duration = max(frame.info.get("duration", 70), 20) * FRAME_STEP
        if index == 0:
            duration = TEXT_MS
        rgb = np.array(frame.convert("RGB"))
        black = rgb.astype(int).sum(axis=2) <= BLACK_THRESHOLD

        center = black.shape[1] // 2
        right = np.cumprod(black[:, center:], axis=1).astype(bool)
        left = np.cumprod(black[:, :center][:, ::-1], axis=1).astype(bool)[:, ::-1]
        revealed = np.concatenate([left, right], axis=1)

        alpha = np.where(revealed, 0, 255).astype(np.uint8)
        overlay = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        wide = round(size[0] * CURTAIN_STRETCH)
        overlay = overlay.resize((wide, size[1]), Image.Resampling.LANCZOS)
        offset = (wide - size[0]) // 2
        overlay = overlay.crop((offset, 0, offset + size[0], size[1]))
        overlay.putalpha(
            overlay.getchannel("A").filter(ImageFilter.GaussianBlur(EDGE_BLUR))
        )

        combined = Image.alpha_composite(dashboard, overlay)
        if index == 0:
            combined = Image.alpha_composite(combined, shadow)
            combined = Image.alpha_composite(combined, shadow)
            combined = Image.alpha_composite(combined, text_layer)
        combined = combined.convert("RGB")
        frames.append(combined)
        durations.append(duration)
        revealed_ratio.append(revealed.mean())

sample = frames[:: max(1, len(frames) // 8)]
sheet = Image.new("RGB", (size[0], size[1] * len(sample) + 40))
for position, picture in enumerate(sample):
    sheet.paste(picture, (0, position * size[1]))
sheet_draw = ImageDraw.Draw(sheet)
sheet_draw.rectangle((0, size[1] * len(sample), size[0] // 2, sheet.height), fill=NAME_COLOR)
sheet_draw.rectangle((size[0] // 2, size[1] * len(sample), size[0], sheet.height), fill=ROLE_COLOR)
palette = sheet.quantize(colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]

open_index = int(np.argmax(revealed_ratio))
durations[open_index] += HOLD_OPEN_MS

if not PLAY_CLOSING:
    frames = frames[: open_index + 1]
    durations = durations[: open_index + 1]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=False,
)

print(f"Animated dashboard created: {OUTPUT} ({len(frames)} frames)")
