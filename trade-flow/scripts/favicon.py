#!/usr/bin/env python3
"""The Trade Flow favicon: a small treemap.

One tile list drives both outputs, so they cannot drift apart:

  * an SVG, for browsers that take vector favicons, and
  * a 64px PNG, rasterised here in pure Python, for the ones that do not
    (Safari has been the holdout). No imaging library needed.

The colours are the game's own: the accent blue, the export green and the
import amber, on the dark page ground.

Usage:  python3 scripts/favicon.py [DIR]     write favicon.svg / favicon.png to DIR
"""

import base64
import pathlib
import struct
import sys
import zlib

GRID = 32
BG = "#10151c"
BG_RADIUS = 7
TILE_RADIUS = 1.2

# (x, y, width, height, fill) on a 32 x 32 grid, 1.5 units between tiles and a
# 3 unit margin. A big tile beside a column that keeps halving is the shape a
# treemap has, and it still reads when the browser squeezes it to 16px.
TILES = [
    (3, 3, 14, 26, "#4fc3f7"),          # accent blue
    (18.5, 3, 10.5, 11.5, "#34d399"),   # export green
    (18.5, 16, 10.5, 7, "#fbbf24"),     # import amber
    (18.5, 24.5, 4.75, 4.5, "#7f93aa"),
    (24.75, 24.5, 4.25, 4.5, "#2b87b3"),
]


def svg():
    parts = [f'<rect width="{GRID}" height="{GRID}" rx="{BG_RADIUS}" fill="{BG}"/>']
    for x, y, w, h, fill in TILES:
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                     f'rx="{TILE_RADIUS:g}" fill="{fill}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">%s</svg>'
            % (GRID, GRID, "".join(parts)))


def _rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def _inside(px, py, x, y, w, h, r):
    """Is (px, py) inside the rounded rectangle?"""
    dx = max(abs(px - (x + w / 2)) - (w / 2 - r), 0)
    dy = max(abs(py - (y + h / 2)) - (h / 2 - r), 0)
    return dx * dx + dy * dy <= r * r


def png(size=64, samples=4):
    """Rasterise the same shapes, averaging samples x samples points per pixel."""
    shapes = [(0, 0, GRID, GRID, BG_RADIUS, _rgb(BG))]
    shapes += [(x, y, w, h, TILE_RADIUS, _rgb(fill)) for x, y, w, h, fill in TILES]
    scale = GRID / size
    rows = []
    for j in range(size):
        row = bytearray([0])                       # PNG filter type: none
        for i in range(size):
            r = g = b = hits = 0
            for sj in range(samples):
                for si in range(samples):
                    px = (i + (si + .5) / samples) * scale
                    py = (j + (sj + .5) / samples) * scale
                    top = None
                    for x, y, w, h, rad, rgb in shapes:   # later shapes paint over
                        if _inside(px, py, x, y, w, h, rad):
                            top = rgb
                    if top:
                        r, g, b, hits = r + top[0], g + top[1], b + top[2], hits + 1
            if hits:
                row += bytes([round(r / hits), round(g / hits), round(b / hits),
                              round(255 * hits / (samples * samples))])
            else:
                row += bytes(4)                    # fully transparent corner
        rows.append(bytes(row))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)   # 8-bit RGBA
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def svg_data_uri():
    return "data:image/svg+xml;base64," + base64.b64encode(svg().encode()).decode()


def png_data_uri():
    return "data:image/png;base64," + base64.b64encode(png()).decode()


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if out is None:
        print(f"svg {len(svg())} bytes, png {len(png())} bytes")
    else:
        out.mkdir(parents=True, exist_ok=True)
        (out / "favicon.svg").write_text(svg())
        (out / "favicon.png").write_bytes(png())
        print(f"wrote {out}/favicon.svg and favicon.png")
