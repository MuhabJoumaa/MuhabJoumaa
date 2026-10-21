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

DEFAULT_CANVAS = (1200, 720)
DEFAULT_CARDS = [
    (40, 40, 540, 221),
    (40, 281, 540, 318),
    (620, 40, 540, 386),
]

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

STEP_MS = 100
PALETTE_COLORS = 128
SEED = 11

OBJECT_ENABLED = True
OBJECT_OUTER = "icosahedron"
OBJECT_INNER = "cube"
OBJECT_COLOR = (90, 255, 170)
OBJECT_INNER_COLOR = (80, 200, 255)
OBJECT_SPIN_Y = 55
OBJECT_SPIN_X = 28
OBJECT_SCALE = 1.0
CAMERA_DISTANCE = 3.5

OBJECT2_ENABLED = True
OBJECT2_OUTER = "octahedron"
OBJECT2_INNER = "cube"
OBJECT2_COLOR = (255, 65, 75)
OBJECT2_INNER_COLOR = (255, 150, 90)
OBJECT2_SCALE = 0.95
OBJECT2_X = 0.88
OBJECT2_Y = 0.78


def make_shape(name):
    if name == "cube":
        points = [
            (x, y, z)
            for x in (-1, 1)
            for y in (-1, 1)
            for z in (-1, 1)
        ]
    elif name == "octahedron":
        points = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
            (0, 0, 1),
            (0, 0, -1),
        ]
    else:
        phi = (1 + math.sqrt(5)) / 2
        points = []
        for a in (-1, 1):
            for b in (-phi, phi):
                points += [
                    (0, a, b),
                    (a, b, 0),
                    (b, 0, a),
                ]

    verts = np.array(points, dtype=np.float64)
    verts /= np.linalg.norm(verts, axis=1, keepdims=True)

    distances = np.linalg.norm(
        verts[:, None] - verts[None, :],
        axis=2,
    )

    shortest = distances[distances > 1e-6].min()

    edges = [
        (i, j)
        for i in range(len(verts))
        for j in range(i + 1, len(verts))
        if distances[i, j] < shortest * 1.01
    ]

    return verts, edges


def rotation_matrix(ax, ay):
    rx = np.array([
        [1, 0, 0],
        [0, math.cos(ax), -math.sin(ax)],
        [0, math.sin(ax), math.cos(ax)],
    ])

    ry = np.array([
        [math.cos(ay), 0, math.sin(ay)],
        [0, 1, 0],
        [-math.sin(ay), 0, math.cos(ay)],
    ])

    return ry @ rx


base = []

with Image.open(INPUT) as source:
    for frame in ImageSequence.Iterator(source):
        base.append((
            frame.convert("RGB"),
            max(frame.info.get("duration", 70), 20),
        ))

width, height = base[0][0].size
size = (width, height)

if LAYOUT.exists():
    layout = json.loads(LAYOUT.read_text())
    canvas_w, canvas_h = layout["canvas"]
    cards = layout["cards"]
else:
    canvas_w, canvas_h = DEFAULT_CANVAS
    cards = DEFAULT_CARDS

scale_x = width / canvas_w
scale_y = height / canvas_h

rects = [
    (
        round(x * scale_x),
        round(y * scale_y),
        round(w * scale_x),
        round(h * scale_y),
    )
    for x, y, w, h in cards
]

radius = max(2, round(5 * min(scale_x, scale_y)))

object_center = None
object_radius = 0
free_areas = []

if OBJECT_ENABLED:
    xs = sorted({
        0,
        width,
        *(x for x, y, w, h in rects),
        *(x + w for x, y, w, h in rects),
    })

    ys = sorted({
        0,
        height,
        *(y for x, y, w, h in rects),
        *(y + h for x, y, w, h in rects),
    })

    for i, x1 in enumerate(xs[:-1]):
        for x2 in xs[i + 1:]:
            for j, y1 in enumerate(ys[:-1]):
                for y2 in ys[j + 1:]:
                    area_w = x2 - x1
                    area_h = y2 - y1

                    if area_w < 60 or area_h < 60:
                        continue

                    blocked = any(
                        x < x2
                        and x + w > x1
                        and y < y2
                        and y + h > y1
                        for x, y, w, h in rects
                    )

                    if not blocked:
                        free_areas.append(
                            (area_w * area_h, x1, y1, area_w, area_h)
                        )

    best = max(free_areas, default=None)

    if best is not None:
        _, x, y, area_w, area_h = best

        object_center = (
            x + area_w / 2,
            y + area_h / 2,
        )

        object_radius = (
            min(area_w, area_h) * 0.34 * OBJECT_SCALE
        )

        objects = [
            (
                *make_shape(OBJECT_OUTER),
                1.0,
                1,
                OBJECT_COLOR,
            ),
            (
                *make_shape(OBJECT_INNER),
                0.5,
                -1,
                OBJECT_INNER_COLOR,
            ),
        ]

object2_center = None
object2_radius = 0

if OBJECT2_ENABLED:
    object2_center = (
        width * OBJECT2_X,
        height * OBJECT2_Y,
    )

    object2_radius = (
        min(width, height) * 0.12 * OBJECT2_SCALE
    )

    objects2 = [
        (
            *make_shape(OBJECT2_OUTER),
            1.0,
            1,
            OBJECT2_COLOR,
        ),
        (
            *make_shape(OBJECT2_INNER),
            0.5,
            -1,
            OBJECT2_INNER_COLOR,
        ),
    ]

masks = []
grids = []

for x, y, w, h in rects:
    mask = Image.new("L", (w, h), 0)

    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=radius,
        fill=255,
    )

    masks.append(
        np.asarray(mask, dtype=np.float32) / 255
    )

    yy, xx = np.mgrid[0:h, 0:w]
    grids.append(
        (xx + SHINE_SLANT * yy) / (w + SHINE_SLANT * h)
    )

hold_index = max(
    range(len(base)),
    key=lambda i: base[i][1],
)

hold_total = base[hold_index][1]

plan = []

for index, (_, duration) in enumerate(base):
    if index == 0:
        parts = max(1, round(duration / GLITCH_STEP_MS))

        for k in range(parts):
            plan.append((
                "glitch",
                index,
                k,
                parts,
                duration / parts,
            ))

    elif index == hold_index:
        parts = max(1, round(duration / STEP_MS))

        for k in range(parts):
            plan.append((
                "hold",
                index,
                k,
                parts,
                duration / parts,
            ))

    else:
        plan.append((
            "plain",
            index,
            0,
            1,
            duration,
        ))

rng = np.random.default_rng(SEED)

frames = []
durations = []
hold_frames = []
hold_time = 0.0

y0 = int(height * GLITCH_BAND[0])
y1 = int(height * GLITCH_BAND[1])

for kind, index, k, parts, duration in plan:
    picture = base[index][0]

    if kind == "glitch" and parts > 1:
        amount = 1 - k / (parts - 1)

        if amount > 0:
            arr = np.array(picture)

            shift = max(
                2,
                int(width * GLITCH_SHIFT * amount),
            )

            dx = (
                int(rng.integers(1, shift + 1))
                * int(rng.choice([-1, 1]))
            )

            band = arr[y0:y1]
            band[:, :, 0] = np.roll(
                band[:, :, 0],
                dx,
                axis=1,
            )
            band[:, :, 2] = np.roll(
                band[:, :, 2],
                -dx,
                axis=1,
            )

            for _ in range(max(1, round(GLITCH_SLICES * amount))):
                sy = int(rng.integers(y0, max(y0 + 1, y1 - 14)))
                sh = int(rng.integers(3, 14))
                sx = int(rng.integers(-4 * shift, 4 * shift + 1))

                arr[sy:sy + sh] = np.roll(
                    arr[sy:sy + sh],
                    sx,
                    axis=1,
                )

            picture = Image.fromarray(arr)

    if kind == "hold":
        t = hold_time
        hold_time += duration

        env = max(
            0.0,
            min(
                1.0,
                t / FADE_MS,
                (hold_total - t) / FADE_MS,
            ),
        )

        pulse = (
            0.6
            + 0.4 * math.sin(2 * math.pi * t / NEON_PULSE_MS)
        )

        level = env * pulse

        core = Image.new("RGB", size, (0, 0, 0))
        core_draw = ImageDraw.Draw(core)

        color = tuple(
            int(c * level)
            for c in NEON_COLOR
        )

        for x, y, w, h in rects:
            core_draw.rounded_rectangle(
                (x - 1, y - 1, x + w, y + h),
                radius=radius,
                outline=color,
                width=NEON_WIDTH,
            )

        obj_light = None

        if object_center is not None:
            ease = env ** 0.7

            obj_core = Image.new("RGB", size, (0, 0, 0))
            obj_draw = ImageDraw.Draw(obj_core)

            for verts, edges, size_factor, direction, obj_color in objects:
                ax = (
                    0.35
                    + math.radians(
                        OBJECT_SPIN_X * direction * t / 1000
                    )
                )

                ay = math.radians(
                    OBJECT_SPIN_Y * direction * t / 1000
                )

                points = verts @ rotation_matrix(ax, ay).T
                depth = points[:, 2]

                persp = CAMERA_DISTANCE / (CAMERA_DISTANCE - depth)
                reach = object_radius * size_factor * ease

                px = object_center[0] + points[:, 0] * persp * reach
                py = object_center[1] - points[:, 1] * persp * reach

                for a, b in sorted(
                    edges,
                    key=lambda e: depth[e[0]] + depth[e[1]],
                ):
                    mid = (depth[a] + depth[b]) / 2

                    bright = (
                        0.3 + 0.7 * (mid + 1) / 2
                    ) * ease

                    line_color = tuple(
                        int(v * bright)
                        for v in obj_color
                    )

                    obj_draw.line(
                        (px[a], py[a], px[b], py[b]),
                        fill=line_color,
                        width=2,
                    )

                for i in range(len(verts)):
                    bright = (
                        0.4 + 0.6 * (depth[i] + 1) / 2
                    ) * ease

                    dot_color = tuple(
                        int(min(255, v * bright + 40 * bright))
                        for v in obj_color
                    )

                    r = 2.4 * persp[i]

                    obj_draw.ellipse(
                        (
                            px[i] - r,
                            py[i] - r,
                            px[i] + r,
                            py[i] + r,
                        ),
                        fill=dot_color,
                    )

            obj_halo = obj_core.filter(
                ImageFilter.GaussianBlur(3)
            ).point(
                lambda v: min(255, int(v * 1.3))
            )

            obj_wide = obj_core.filter(
                ImageFilter.GaussianBlur(9)
            ).point(
                lambda v: min(255, int(v * 1.6))
            )

            obj_light = ImageChops.add(
                ImageChops.add(obj_core, obj_halo),
                obj_wide,
            )

        obj2_light = None

        if object2_center is not None:
            ease = env ** 0.7

            obj2_core = Image.new("RGB", size, (0, 0, 0))
            obj2_draw = ImageDraw.Draw(obj2_core)

            for verts, edges, size_factor, direction, obj_color in objects2:
                ax = (
                    0.35
                    + math.radians(
                        OBJECT_SPIN_X * direction * t / 1000
                    )
                )

                ay = math.radians(
                    OBJECT_SPIN_Y * direction * t / 1000
                )

                points = verts @ rotation_matrix(ax, ay).T
                depth = points[:, 2]

                persp = CAMERA_DISTANCE / (CAMERA_DISTANCE - depth)
                reach = object2_radius * size_factor * ease

                px = object2_center[0] + points[:, 0] * persp * reach
                py = object2_center[1] - points[:, 1] * persp * reach

                for a, b in sorted(
                    edges,
                    key=lambda e: depth[e[0]] + depth[e[1]],
                ):
                    mid = (depth[a] + depth[b]) / 2

                    bright = (
                        0.3 + 0.7 * (mid + 1) / 2
                    ) * ease

                    line_color = tuple(
                        int(v * bright)
                        for v in obj_color
                    )

                    obj2_draw.line(
                        (px[a], py[a], px[b], py[b]),
                        fill=line_color,
                        width=2,
                    )

                for i in range(len(verts)):
                    bright = (
                        0.4 + 0.6 * (depth[i] + 1) / 2
                    ) * ease

                    dot_color = tuple(
                        int(min(255, v * bright + 40 * bright))
                        for v in obj_color
                    )

                    r = 2.4 * persp[i]

                    obj2_draw.ellipse(
                        (
                            px[i] - r,
                            py[i] - r,
                            px[i] + r,
                            py[i] + r,
                        ),
                        fill=dot_color,
                    )

            obj2_halo = obj2_core.filter(
                ImageFilter.GaussianBlur(3)
            ).point(
                lambda v: min(255, int(v * 1.3))
            )

            obj2_wide = obj2_core.filter(
                ImageFilter.GaussianBlur(9)
            ).point(
                lambda v: min(255, int(v * 1.6))
            )

            obj2_light = ImageChops.add(
                ImageChops.add(obj2_core, obj2_halo),
                obj2_wide,
            )

        halo = core.filter(
            ImageFilter.GaussianBlur(NEON_GLOW)
        ).point(
            lambda v: min(255, int(v * 3))
        )

        wide = core.filter(
            ImageFilter.GaussianBlur(NEON_GLOW * 2.5)
        ).point(
            lambda v: min(255, int(v * 5))
        )

        light = ImageChops.add(
            ImageChops.add(core, halo),
            wide,
        )

        picture = ImageChops.screen(picture, light)

        if obj_light is not None:
            picture = ImageChops.screen(picture, obj_light)

        if obj2_light is not None:
            picture = ImageChops.screen(picture, obj2_light)

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

            region = np.asarray(
                picture.crop((x, y, x + w, y + h)),
                dtype=np.float32,
            )

            region = region + band_light[:, :, None] * 255

            picture = picture.copy()

            picture.paste(
                Image.fromarray(
                    np.clip(region, 0, 255).astype(np.uint8)
                ),
                (x, y),
            )

        hold_frames.append(len(frames))

    frames.append(picture)

    durations.append(
        max(20, int(round(duration / 10) * 10))
    )

sample = frames[::max(1, len(frames) // 8)]
sample.append(frames[min(1, len(frames) - 1)])

if hold_frames:
    sample.append(
        frames[hold_frames[len(hold_frames) // 2]]
    )

sheet = Image.new(
    "RGB",
    (width, height * len(sample) + 40),
)

for position, picture in enumerate(sample):
    sheet.paste(
        picture,
        (0, position * height),
    )

sheet_draw = ImageDraw.Draw(sheet)

sheet_draw.rectangle(
    (0, height * len(sample), width // 2, sheet.height),
    fill=NEON_COLOR,
)

sheet_draw.rectangle(
    (
        width // 2,
        height * len(sample),
        width * 3 // 4,
        sheet.height,
    ),
    fill=(255, 255, 255),
)

sheet_draw.rectangle(
    (
        width * 3 // 4,
        height * len(sample),
        width,
        sheet.height,
    ),
    fill=OBJECT2_COLOR,
)

palette = sheet.quantize(
    colors=PALETTE_COLORS,
    method=Image.Quantize.MEDIANCUT,
    dither=Image.Dither.NONE,
)

frames = [
    f.quantize(
        palette=palette,
        dither=Image.Dither.NONE,
    )
    for f in frames
]

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=False,
)

print(f"Effects added: {OUTPUT} ({len(frames)} frames)")
