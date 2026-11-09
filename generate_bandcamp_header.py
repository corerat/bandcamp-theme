#!/usr/bin/env python3
"""make a repeatable 975x180 glitch-art header for my bandcamp page.

run with: python3 generate_bandcamp_header.py
use --seed to make a different, repeatable arrangement.
"""

import argparse
import binascii
import random
import struct
import zlib
from pathlib import Path


WIDTH = 975
HEIGHT = 180
OUTPUT = Path(__file__).with_name("bandcamp-header.png")
NAVBAR_COLOR = (56, 36, 72)  # #382448

PALETTE = (
    (39, 24, 55),
    (72, 39, 101),
    (112, 52, 150),
    (159, 69, 184),
)

# this small 5x7 lowercase font keeps the name quiet and monospaced.
FONT = {
    "a": ("00000", "01110", "00001", "01111", "10001", "10011", "01101"),
    "c": ("00000", "01110", "10000", "10000", "10000", "10001", "01110"),
    "e": ("00000", "01110", "10001", "11111", "10000", "10001", "01110"),
    "o": ("00000", "01110", "10001", "10001", "10001", "10001", "01110"),
    "r": ("00000", "10110", "11001", "10000", "10000", "10000", "10000"),
    "t": ("01000", "11100", "01000", "01000", "01000", "01001", "00110"),
}
WORDMARK = "corerat"
LETTER_SCALE = 2
GLITCH_COUNT = 14
PARTICLE_COUNT = 450


def png_chunk(kind, data):
    body = kind + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)
    )


def noise_grid(rng, size_x, size_y):
    return [
        [rng.uniform(-1.0, 1.0) for _ in range(size_x)]
        for _ in range(size_y)
    ]


def smooth_noise(grid, x, y):
    size_y, size_x = len(grid), len(grid[0])
    gx, gy = x * size_x / WIDTH, y * size_y / HEIGHT
    ix, iy = int(gx), int(gy)
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    x1, y1 = (ix + 1) % size_x, (iy + 1) % size_y
    top = grid[iy][ix] + (grid[iy][x1] - grid[iy][ix]) * fx
    bottom = grid[y1][ix] + (grid[y1][x1] - grid[y1][ix]) * fx
    return top + (bottom - top) * fy


def blend(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def set_pixel(pixels, x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        offset = (y * WIDTH + x) * 3
        pixels[offset:offset + 3] = bytes(color)


def draw_rect(pixels, x, y, width, height, color):
    for row in range(max(0, y), min(HEIGHT, y + height)):
        start = (row * WIDTH + max(0, x)) * 3
        end = (row * WIDTH + min(WIDTH, x + width)) * 3
        if end > start:
            pixels[start:end] = bytes(color) * ((end - start) // 3)


def make_background(seed):
    rng = random.Random(seed)
    noise = (
        (noise_grid(rng, 4, 2), 0.115),
        (noise_grid(rng, 9, 4), 0.065),
        (noise_grid(rng, 24, 8), 0.035),
        (noise_grid(rng, 72, 18), 0.015),
    )
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            value = 0.49
            for grid, amplitude in noise:
                value += smooth_noise(grid, x, y) * amplitude

            # a little glow gives the purple background some depth.
            glow_x = (x - WIDTH * 0.52) / (WIDTH * 0.7)
            glow_y = (y - HEIGHT * 0.48) / (HEIGHT * 1.1)
            value += 0.08 * max(0.0, 1.0 - glow_x * glow_x - glow_y * glow_y)
            value = min(1.0, max(0.0, value))
            segment = min(2, int(value * 3))
            color = blend(PALETTE[segment], PALETTE[segment + 1], value * 3 - segment)

            # darken the sides slightly to keep the middle from feeling flat.
            edge = min(1.0, min(x, WIDTH - 1 - x) / 210)
            shade = 0.80 + 0.20 * edge
            color = tuple(round(channel * shade) for channel in color)
            offset = (y * WIDTH + x) * 3
            pixels[offset:offset + 3] = bytes(color)
    return pixels, rng


def add_particles(pixels, rng):
    colors = ((225, 175, 240), (255, 156, 222), (143, 226, 236))
    for _ in range(PARTICLE_COUNT):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        if rng.random() < 0.72:
            color = (19, 9, 31)
        else:
            color = rng.choice(colors)
        set_pixel(pixels, x, y, color)


def add_glitch_bars(pixels, rng):
    accents = ((91, 56, 117), (103, 58, 122), (108, 63, 128))
    for _ in range(GLITCH_COUNT):
        y = rng.randrange(HEIGHT)
        x = rng.randrange(WIDTH)
        width = rng.choices((2, 3, 5, 8, 12, 18), (22, 28, 24, 15, 8, 3), k=1)[0]
        height = 1
        color = rng.choice(accents) if rng.random() < 0.22 else (40, 25, 55)
        draw_rect(pixels, x, y, width, height, color)

    # add a few almost invisible glitch marks.
    for _ in range(6):
        y = rng.randrange(HEIGHT)
        x = rng.randrange(WIDTH)
        width = rng.randrange(4, 16)
        draw_rect(pixels, x, y, width, 1, rng.choice(accents))


def draw_wordmark(pixels):
    scale = LETTER_SCALE
    advance = 6 * scale
    total_width = len(WORDMARK) * advance - scale
    start_x = WIDTH - total_width - 18
    start_y = HEIGHT - 7 * scale - 12

    for index, character in enumerate(WORDMARK):
        glyph = FONT[character]
        char_x = start_x + index * advance
        for row, bits in enumerate(glyph):
            for column, bit in enumerate(bits):
                if bit == "1":
                    draw_rect(
                        pixels,
                        char_x + column * scale,
                        start_y + row * scale,
                        scale - 1,
                        scale - 1,
                        (205, 184, 218),
                    )


def blend_into_navbar(pixels):
    transition_y = HEIGHT - 2
    for x in range(WIDTH):
        offset = (transition_y * WIDTH + x) * 3
        current = pixels[offset:offset + 3]
        pixels[offset:offset + 3] = bytes(blend(current, NAVBAR_COLOR, 0.5))
    draw_rect(pixels, 0, HEIGHT - 1, WIDTH, 1, NAVBAR_COLOR)


def make_png(seed):
    pixels, rng = make_background(seed)
    add_particles(pixels, rng)
    add_glitch_bars(pixels, rng)
    draw_wordmark(pixels)
    blend_into_navbar(pixels)

    scanlines = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        scanlines.append(0)
        scanlines.extend(pixels[y * stride:(y + 1) * stride])
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">2I5B", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(scanlines, 6))
        + png_chunk(b"IEND", b"")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261109, help="seed for repeatable artwork")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="output PNG path")
    args = parser.parse_args()

    image = make_png(args.seed)
    args.output.write_bytes(image)
    print(f"made {WIDTH}x{HEIGHT} header at {args.output} ({len(image):,} bytes, seed {args.seed})")


if __name__ == "__main__":
    main()
