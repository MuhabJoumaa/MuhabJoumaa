import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

INPUT = PROFILE / "github-dashboard.gif"
OUTPUT = PROFILE / "github-dashboard-glow.gif"

PARTICLE_COUNT = 30
COLORS = [(90, 255, 170), (80, 200, 255), (255, 255, 255)]
MIN_RADIUS = 1.5
MAX_RADIUS = 3.5
GLOW_BLUR = 5
GLOW_STRENGTH = 1.0
STEP_MS = 150
STATIC_LOOP_MS = 6000
PALETTE_COLORS = 128
SEED = 7

base = []
with Image.open(INPUT) as source:
    for frame in ImageSequence.Iterator(source):
        duration = frame.info.get("duration") or STATIC_LOOP_MS
        base.append((frame.convert("RGB"), max(duration, 20)))

width, height = base[0][0].size

timeline = []
for index, (_, duration) in enumerate(base):
    parts = 1 if duration <= 2 * STEP_MS else round(duration / STEP_MS)
    for _ in range(parts):
        timeline.append((index, duration / parts))

total = sum(duration for _, duration in timeline)

random.seed(SEED)
particles = []
for _ in range(PARTICLE_COUNT):
    particles.append({
        "x": random.uniform(0, width),
        "y": random.uniform(0, height),
        "radius": random.uniform(MIN_RADIUS, MAX_RADIUS),
        "color": random.choice(COLORS),
        "rise": random.choice([1, 1, 2]),
        "sway": random.uniform(6, 22),
        "sway_cycles": random.randint(1, 3),
        "twinkle_cycles": random.randint(2, 5),
        "phase": random.random(),
    })

edge = height * 0.12
frames = []
durations = []
elapsed = 0.0

for index, duration in timeline:
    u = elapsed / total
    elapsed += duration

    core = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(core)

    for p in particles:
        y = (p["y"] - p["rise"] * height * u) % height
        x = p["x"] + p["sway"] * math.sin(2 * math.pi * (p["sway_cycles"] * u + p["phase"]))
        twinkle = 0.5 + 0.5 * math.sin(2 * math.pi * (p["twinkle_cycles"] * u + p["phase"]))
        fade = min(1.0, y / edge, (height - y) / edge)
        brightness = (0.35 + 0.65 * twinkle) * fade
        color = tuple(int(c * brightness) for c in p["color"])
        r = p["radius"]
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

    halo = core.filter(ImageFilter.GaussianBlur(GLOW_BLUR)).point(
        lambda v: min(255, int(v * 4 * GLOW_STRENGTH))
    )
    wide = core.filter(ImageFilter.GaussianBlur(GLOW_BLUR * 3)).point(
        lambda v: min(255, int(v * 8 * GLOW_STRENGTH))
    )
    light = ImageChops.add(ImageChops.add(core, halo), wide)

    frames.append(ImageChops.screen(base[index][0], light))
    durations.append(max(20, int(round(duration / 10) * 10)))

sample = frames[:: max(1, len(frames) // 10)]
sheet = Image.new("RGB", (width, height * len(sample)))
for position, picture in enumerate(sample):
    sheet.paste(picture, (0, position * height))
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

print(f"Glow particles added: {OUTPUT} ({len(frames)} frames)")
