from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile"

DASHBOARD = PROFILE / "github-dashboard.png"
CURTAIN = PROFILE / "curtain.gif"
OUTPUT = PROFILE / "github-dashboard.gif"

KEY_COLOR = (0, 0, 0)
KEY_TOLERANCE = 40
KEY_SOFTNESS = 80
HOLD_LAST_MS = 4000
MIN_FRAME_MS = 30

dashboard = Image.open(DASHBOARD).convert("RGBA")
size = dashboard.size

frames = []
durations = []

with Image.open(CURTAIN) as curtain:
    for frame in ImageSequence.Iterator(curtain):
        duration = max(frame.info.get("duration", 80), MIN_FRAME_MS)
        overlay = frame.convert("RGBA").resize(size, Image.Resampling.LANCZOS)

        if KEY_COLOR is not None:
            data = np.array(overlay)
            diff = np.abs(data[:, :, :3].astype(int) - np.array(KEY_COLOR)).sum(axis=2)
            alpha = np.clip((diff - KEY_TOLERANCE) / KEY_SOFTNESS, 0, 1)
            data[:, :, 3] = (data[:, :, 3] * alpha).astype(np.uint8)
            overlay = Image.fromarray(data, "RGBA")

        combined = Image.alpha_composite(dashboard, overlay).convert("RGB")
        frames.append(combined.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))
        durations.append(duration)

durations[-1] += HOLD_LAST_MS

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
