from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageSequence

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
HOLD_OPEN_MS = 4000
PLAY_CLOSING = True

dashboard = Image.open(DASHBOARD).convert("RGBA")
if OUTPUT_WIDTH and OUTPUT_WIDTH < dashboard.width:
    new_height = round(dashboard.height * OUTPUT_WIDTH / dashboard.width)
    dashboard = dashboard.resize((OUTPUT_WIDTH, new_height), Image.Resampling.LANCZOS)
size = dashboard.size

frames = []
durations = []
revealed_ratio = []

with Image.open(CURTAIN) as curtain:
    for index, frame in enumerate(ImageSequence.Iterator(curtain)):
        if index % FRAME_STEP:
            continue

        duration = max(frame.info.get("duration", 70), 20) * FRAME_STEP
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

        combined = Image.alpha_composite(dashboard, overlay).convert("RGB")
        frames.append(combined)
        durations.append(duration)
        revealed_ratio.append(revealed.mean())

sample = frames[:: max(1, len(frames) // 8)]
sheet = Image.new("RGB", (size[0], size[1] * len(sample)))
for position, picture in enumerate(sample):
    sheet.paste(picture, (0, position * size[1]))
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
