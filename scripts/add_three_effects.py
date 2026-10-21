import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

INPUT = PROFILE / "github-dashboard.gif"
OUTPUT = PROFILE / "github-dashboard-fx.gif"
LAYOUT = PROFILE / "layout.json"

DEFAULT_CANVAS = (1200, 650)
DEFAULT_CARDS = [(40, 132, 540, 222), (621, 132, 538, 384)]

NEON_COLOR = (90, 255, 170)
NEON_WIDTH = 2
NEON_GLOW = 5
NEON_PULSE_MS = 1400
FADE_MS = 400

SHINE_STRENGTH = 0.30
SHINE_MS = 900
SHINE_PERIOD_MS = 2200
SHINE_DELAY_MS = 500
SHINE_STAGGER_MS = 200
SHINE_SLANT = 0.6
SHINE_WIDTH = 0.09

GLITCH_STEP_MS = 100
GLITCH_SHIFT = 0.012
GLITCH_SLICES = 5
GLITCH_BAND = (0.30, 0.70)

STEP_MS = 150
PALETTE_COLORS = 128
SEED = 11

base = []
with Image.open(INPUT) as source:
    for frame in ImageSequence.Iterator(source):
        base.append((frame.convert("RGB"), max(frame.info.get("duration", 70), 20)))

width, height = base[0][0].size
size = (width, height)

if LAYOUT.exists():
    layout = json.loads(LAYOUT.read_text())
    canvas_w, canvas_h = layout["canvas"]
    cards = layout["cards"]
else:
    canvas_w, canvas_h = DEFAULT_CANVAS
    cards = DEFAULT_CARDS

scale = width / canvas_w
rects = [
    (round(x * scale), round(y * scale), round(w * scale), round(h * scale))
    for x, y, w, h in cards
]
radius = max(2, round(5 * scale))

masks = []
grids = []
for x, y, w, h in rects:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    masks.append(np.asarray(mask, dtype=np.float32) / 255)
    yy, xx = np.mgrid[0:h, 0:w]
    grids.append((xx + SHINE_SLANT * yy) / (w + SHINE_SLANT * h))

hold_index = max(range(len(base)), key=lambda i: base[i][1])
hold_total = base[hold_index][1]

plan = []
for index, (_, duration) in enumerate(base):
    if index == 0:
        parts = max(1, round(duration / GLITCH_STEP_MS))
        for k in range(parts):
            plan.append(("glitch", index, k, parts, duration / parts))
    elif index == hold_index:
        parts = max(1, round(duration / STEP_MS))
        for k in range(parts):
            plan.append(("hold", index, k, parts, duration / parts))
    else:
        plan.append(("plain", index, 0, 1, duration))

rng = np.random.default_rng(SEED)
frames = []
durations = []
hold_frames = []
hold_time = 0.0
y0, y1 = int(height * GLITCH_BAND[0]), int(height * GLITCH_BAND[1])

for kind, index, k, parts, duration in plan:
    picture = base[index][0]

    if kind == "glitch" and parts > 1:
        amount = 1 - k / (parts - 1)
        if amount > 0:
            arr = np.array(picture)
            shift = max(2, int(width * GLITCH_SHIFT * amount))
            dx = int(rng.integers(1, shift + 1)) * int(rng.choice([-1, 1]))
            band = arr[y0:y1]
            band[:, :, 0] = np.roll(band[:, :, 0], dx, axis=1)
            band[:, :, 2] = np.roll(band[:, :, 2], -dx, axis=1)
            for _ in range(max(1, round(GLITCH_SLICES * amount))):
                sy = int(rng.integers(y0, y1 - 14))
                sh = int(rng.integers(3, 14))
                sx = int(rng.integers(-4 * shift, 4 * shift + 1))
                arr[sy:sy + sh] = np.roll(arr[sy:sy + sh], sx, axis=1)
            picture = Image.fromarray(arr)

    if kind == "hold":
        t = hold_time
        hold_time += duration
        env = max(0.0, min(1.0, t / FADE_MS, (hold_total - t) / FADE_MS))
        pulse = 0.6 + 0.4 * math.sin(2 * math.pi * t / NEON_PULSE_MS)
        level = env * pulse

        core = Image.new("RGB", size, (0, 0, 0))
        core_draw = ImageDraw.Draw(core)
        color = tuple(int(c * level) for c in NEON_COLOR)
        for x, y, w, h in rects:
            core_draw.rounded_rectangle(
                (x - 1, y - 1, x + w, y + h),
                radius=radius,
                outline=color,
                width=NEON_WIDTH,
            )
        halo = core.filter(ImageFilter.GaussianBlur(NEON_GLOW)).point(
            lambda v: min(255, int(v * 3))
        )
        wide = core.filter(ImageFilter.GaussianBlur(NEON_GLOW * 2.5)).point(
            lambda v: min(255, int(v * 5))
        )
        light = ImageChops.add(ImageChops.add(core, halo), wide)
        picture = ImageChops.screen(picture, light)

        for n, (x, y, w, h) in enumerate(rects):
            start = SHINE_DELAY_MS + n * SHINE_STAGGER_MS
            if t < start:
                continue
            phase = (t - start) % SHINE_PERIOD_MS
            if phase > SHINE_MS:
                continue
            position = -0.25 + 1.5 * phase / SHINE_MS
            band_light = (
                np.exp(-(((grids[n] - position) / SHINE_WIDTH) ** 2))
                * masks[n]
                * SHINE_STRENGTH
                * env
            )
            region = np.asarray(picture.crop((x, y, x + w, y + h)), dtype=np.float32)
            region = region + band_light[:, :, None] * 255
            picture = picture.copy()
            picture.paste(Image.fromarray(np.clip(region, 0, 255).astype(np.uint8)), (x, y))

        hold_frames.append(len(frames))

    frames.append(picture)
    durations.append(max(20, int(round(duration / 10) * 10)))

sample = frames[:: max(1, len(frames) // 8)]
sample.append(frames[min(1, len(frames) - 1)])
if hold_frames:
    sample.append(frames[hold_frames[len(hold_frames) // 2]])

sheet = Image.new("RGB", (width, height * len(sample) + 40))
for position, picture in enumerate(sample):
    sheet.paste(picture, (0, position * height))
sheet_draw = ImageDraw.Draw(sheet)
sheet_draw.rectangle((0, height * len(sample), width // 2, sheet.height), fill=NEON_COLOR)
sheet_draw.rectangle((width // 2, height * len(sample), width, sheet.height), fill=(255, 255, 255))
palette = sheet.quantize(
    colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
)
frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=False,
)

print(f"Effects added: {OUTPUT} ({len(frames)} frames)")
