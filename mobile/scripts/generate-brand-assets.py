#!/usr/bin/env python3
"""Regenerate the Homely launcher / splash / favicon PNGs from canonical geometry.

Why this exists
---------------
`android/` is generated (git-ignored) and the raster assets under `assets/` were
authored before the abstract brandmark landed. This script rasterises the *same*
geometry declared in `src/design/brandmark-shape.ts` (two mirrored strokes plus a
central core) so the committed PNGs can never drift back to the old literal house.

Reproducibility
---------------
The script parses `src/design/brandmark-shape.ts` at run time — no geometry is
duplicated here. It only needs Python + Pillow (both available locally):

    python scripts/generate-brand-assets.py

Colours come from the design tokens in `src/design/tokens.ts`:
  - background `#123D34`  = light-theme `primary`
  - strokes    `#F2F7F4`  = light-theme `textOnPrimary`
  - core       `#BCACDA`  = dark-theme `accent` (the lilac token that stays
    legible on the deep petrol background; the light-theme `#7E6FA0` only
    reaches ~2.7:1 contrast against `#123D34`).
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

MOBILE_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = MOBILE_ROOT / "assets"
SHAPE_SOURCE = MOBILE_ROOT / "src" / "design" / "brandmark-shape.ts"

BACKGROUND = (0x12, 0x3D, 0x34, 255)
STROKE = (0xF2, 0xF7, 0xF4, 255)
CORE = (0xBC, 0xAC, 0xDA, 255)

# Supersampling factor used to obtain smooth anti-aliased edges from Pillow's
# non-AA drawing primitives before downscaling with Lanczos.
SUPERSAMPLE = 4
CURVE_SEGMENTS = 96


def _read_shape() -> dict:
    """Extract the canonical geometry from the TypeScript source of truth."""
    source = SHAPE_SOURCE.read_text(encoding="utf-8")

    def grab(pattern: str) -> str:
        match = re.search(pattern, source)
        if match is None:
            raise SystemExit(f"Could not find {pattern!r} in {SHAPE_SOURCE}")
        return match.group(1)

    size = float(grab(r"BRANDMARK_SIZE\s*=\s*([0-9.]+)"))
    return {
        "size": size,
        "left": grab(r"left:\s*'([^']+)'"),
        "right": grab(r"right:\s*'([^']+)'"),
        "stroke_width": float(grab(r"BRANDMARK_STROKE_WIDTH\s*=\s*([0-9.]+)")),
        "core_r": float(grab(r"r:\s*([0-9.]+)")),
        "core_cx": size / 2.0,
        "core_cy": size / 2.0,
    }


def _flatten_path(d: str) -> list[tuple[float, float]]:
    """Flatten the absolute M/C commands used by the brandmark into a polyline."""
    tokens = re.findall(r"[MC]|-?\d+(?:\.\d+)?", d)
    points: list[tuple[float, float]] = []
    current: tuple[float, float] | None = None
    index = 0

    while index < len(tokens):
        command = tokens[index]
        if command == "M":
            x, y = float(tokens[index + 1]), float(tokens[index + 2])
            current = (x, y)
            points.append(current)
            index += 3
        elif command == "C":
            x0, y0 = current  # type: ignore[misc]
            x1, y1, x2, y2, x3, y3 = (float(value) for value in tokens[index + 1 : index + 7])
            for step in range(1, CURVE_SEGMENTS + 1):
                t = step / CURVE_SEGMENTS
                mt = 1 - t
                px = (
                    mt**3 * x0
                    + 3 * mt**2 * t * x1
                    + 3 * mt * t**2 * x2
                    + t**3 * x3
                )
                py = (
                    mt**3 * y0
                    + 3 * mt**2 * t * y1
                    + 3 * mt * t**2 * y2
                    + t**3 * y3
                )
                points.append((px, py))
            current = (x3, y3)
            index += 7
        else:  # pragma: no cover - defensive, geometry only uses M/C
            raise SystemExit(f"Unsupported SVG command {command!r} in {d!r}")

    return points


def _render_mark(
    canvas: int,
    *,
    background: tuple[int, int, int, int] | None,
    stroke: tuple[int, int, int, int],
    core: tuple[int, int, int, int],
    ink_fraction: float,
    shape: dict,
) -> Image.Image:
    """Render the brandmark centred on a `canvas` square.

    `ink_fraction` is the share of the canvas the mark's larger ink dimension
    should occupy, which keeps the art inside Android's adaptive-icon safe zone.
    """
    big = canvas * SUPERSAMPLE
    base = background if background is not None else (0, 0, 0, 0)
    image = Image.new("RGBA", (big, big), base)
    draw = ImageDraw.Draw(image)

    left = _flatten_path(shape["left"])
    right = _flatten_path(shape["right"])
    half_stroke = shape["stroke_width"] / 2
    ink = left + right

    min_x = min(point[0] for point in ink) - half_stroke
    max_x = max(point[0] for point in ink) + half_stroke
    min_y = min(point[1] for point in ink) - half_stroke
    max_y = max(point[1] for point in ink) + half_stroke
    ink_w, ink_h = max_x - min_x, max_y - min_y

    scale = ink_fraction * big / max(ink_w, ink_h)
    mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2

    def to_px(point: tuple[float, float]) -> tuple[float, float]:
        return (big / 2 + (point[0] - mid_x) * scale, big / 2 + (point[1] - mid_y) * scale)

    line_width = max(1, round(shape["stroke_width"] * scale))
    radius = line_width / 2

    # Stamp a disc at every flattened point. The discs overlap heavily, so the
    # union is a solid stroke with round caps and no polyline-joint seams.
    for path in (left, right):
        for point in path:
            x, y = to_px(point)
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=stroke)

    core_x, core_y = to_px((shape["core_cx"], shape["core_cy"]))
    core_radius = shape["core_r"] * scale
    draw.ellipse(
        [core_x - core_radius, core_y - core_radius, core_x + core_radius, core_y + core_radius],
        fill=core,
    )

    return image.resize((canvas, canvas), Image.Resampling.LANCZOS)


def main() -> None:
    shape = _read_shape()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    opaque = dict(background=BACKGROUND, stroke=STROKE, core=CORE)
    transparent = dict(background=None, stroke=STROKE, core=CORE)
    monochrome = dict(background=None, stroke=(255, 255, 255, 255), core=(255, 255, 255, 255))

    outputs = [
        # (filename, canvas, options, ink_fraction)
        ("icon.png", 1024, opaque, 0.62),
        ("splash-icon.png", 1024, transparent, 0.72),
        ("favicon.png", 48, opaque, 0.66),
        ("android-icon-foreground.png", 512, transparent, 0.60),
        ("android-icon-monochrome.png", 432, monochrome, 0.60),
    ]

    for name, canvas, options, fraction in outputs:
        _render_mark(canvas, ink_fraction=fraction, shape=shape, **options).save(
            ASSETS_DIR / name
        )
        print(f"wrote {name} ({canvas}x{canvas})")

    # The adaptive background layer is the flat brand colour; Android tints the
    # foreground/monochrome layers on top of it.
    Image.new("RGBA", (512, 512), BACKGROUND).save(ASSETS_DIR / "android-icon-background.png")
    print("wrote android-icon-background.png (512x512)")


if __name__ == "__main__":
    main()
