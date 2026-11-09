#!/usr/bin/env python3
"""make a repeatable, tileable lavender texture with soft color variation and grain.

run with: python3 generate_bandcamp_background.py
edit the settings below to change the tile, colors, variation, and grain.
"""

import argparse
import binascii
import random
import struct
import zlib
from pathlib import Path


WIDTH = 512
HEIGHT = 512
OUTPUT = Path(__file__).with_name("bandcamp-background.png")

# plum, violet, and orchid keep the tile colorful without making it too light.
PALETTE = (
    (0.00, (65, 37, 97)),
    (0.24, (101, 55, 145)),
    (0.47, (133, 70, 181)),
    (0.68, (171, 93, 191)),
    (0.85, (203, 131, 208)),
    (1.00, (230, 185, 232)),
)

VARIATION_BASE = 0.50
# broad, soft noise gives the color variation without distinct cloud shapes.
NOISE_LAYERS = ((3, 0.12), (6, 0.075), (12, 0.045), (24, 0.024), (48, 0.012))
VARIATION_BLUR_PASSES = 3
PARTICLE_COUNT = 2600
PARTICLE_CLUSTER_COUNT = 34
GLITCH_PIXEL_COUNT = 900
GLITCH_STREAK_COUNT = 24


def png_chunk(kind, data):
    body = kind + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)
    )


def make_noise_grid(rng, size):
    return [[rng.uniform(-1.0, 1.0) for _ in range(size)] for _ in range(size)]


def noise_at(grid, size, x, y):
    """sample smooth noise from a grid that repeats on every edge."""
    gx = x * size / WIDTH
    gy = y * size / HEIGHT
    ix, iy = int(gx), int(gy)
    fx, fy = gx - ix, gy - iy
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    x1, y1 = (ix + 1) % size, (iy + 1) % size
    top = grid[iy][ix] + (grid[iy][x1] - grid[iy][ix]) * fx
    bottom = grid[y1][ix] + (grid[y1][x1] - grid[y1][ix]) * fx
    return top + (bottom - top) * fy


def make_palette_table(size=2049):
    table = []
    for index in range(size):
        value = index / (size - 1)
        for stop_index in range(len(PALETTE) - 1):
            low, low_color = PALETTE[stop_index]
            high, high_color = PALETTE[stop_index + 1]
            if value <= high:
                blend = (value - low) / (high - low)
                table.append(tuple(
                    round(a + (b - a) * blend)
                    for a, b in zip(low_color, high_color)
                ))
                break
    return table


def blur_field(field):
    """soften the color variation and wrap the blur around the tile edges."""
    for _ in range(VARIATION_BLUR_PASSES):
        horizontal = [0.0] * len(field)
        for y in range(HEIGHT):
            row = y * WIDTH
            for x in range(WIDTH):
                left = row + (x - 1) % WIDTH
                center = row + x
                right = row + (x + 1) % WIDTH
                horizontal[center] = (
                    field[left] + 2.0 * field[center] + field[right]
                ) * 0.25

        softened = [0.0] * len(field)
        for y in range(HEIGHT):
            row = y * WIDTH
            above = ((y - 1) % HEIGHT) * WIDTH
            below = ((y + 1) % HEIGHT) * WIDTH
            for x in range(WIDTH):
                softened[row + x] = (
                    horizontal[above + x]
                    + 2.0 * horizontal[row + x]
                    + horizontal[below + x]
                ) * 0.25
        field = softened
    return field


def make_field(seed):
    rng = random.Random(seed)
    noise = [(make_noise_grid(rng, size), amplitude) for size, amplitude in NOISE_LAYERS]
    palette = make_palette_table()
    field = [0.0] * (WIDTH * HEIGHT)

    for y in range(HEIGHT):
        for x in range(WIDTH):
            value = VARIATION_BASE
            for grid, amplitude in noise:
                value += noise_at(grid, len(grid), x, y) * amplitude
            field[y * WIDTH + x] = value

    field = blur_field(field)
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        row_offset = y * WIDTH
        for x in range(WIDTH):
            value = field[row_offset + x]
            color = palette[round(min(1.0, max(0.0, value)) * (len(palette) - 1))]
            offset = (row_offset + x) * 3
            pixels[offset:offset + 3] = bytes(color)
    return pixels, rng


def add_grain(pixels, rng):
    """add small purple flecks, wrapping edge marks to the other side."""
    clusters = [
        (rng.randrange(WIDTH), rng.randrange(HEIGHT))
        for _ in range(PARTICLE_CLUSTER_COUNT)
    ]
    for particle in range(PARTICLE_COUNT):
        if particle % 3:
            cx, cy = rng.choice(clusters)
            x = round(rng.gauss(cx, WIDTH * 0.045)) % WIDTH
            y = round(rng.gauss(cy, HEIGHT * 0.045)) % HEIGHT
        else:
            x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)

        if rng.random() < 0.78:
            color, opacity = (116, 74, 151), rng.uniform(0.12, 0.32)
        else:
            color, opacity = (255, 249, 255), rng.uniform(0.14, 0.34)
        radius = rng.choices((0, 1, 2), weights=(0.76, 0.21, 0.03), k=1)[0]

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > radius * radius:
                    continue
                px, py = (x + dx) % WIDTH, (y + dy) % HEIGHT
                offset = (py * WIDTH + px) * 3
                for channel in range(3):
                    original = pixels[offset + channel]
                    pixels[offset + channel] = round(
                        original * (1.0 - opacity) + color[channel] * opacity
                    )


def add_glitch_pixels(pixels, rng):
    """add purple dead pixels and short glitch streaks across the tile."""
    dead_pixel = (51, 16, 79)
    bright_pixel = (202, 157, 226)
    for _ in range(GLITCH_PIXEL_COUNT):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        color = dead_pixel if rng.random() < 0.92 else bright_pixel
        offset = (y * WIDTH + x) * 3
        pixels[offset:offset + 3] = bytes(color)

    for _ in range(GLITCH_STREAK_COUNT):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        length = rng.randint(2, 6)
        color = dead_pixel if rng.random() < 0.9 else bright_pixel
        for step in range(length):
            offset = (y * WIDTH + (x + step) % WIDTH) * 3
            pixels[offset:offset + 3] = bytes(color)


def make_image(seed):
    pixels, rng = make_field(seed)
    add_grain(pixels, rng)
    add_glitch_pixels(pixels, rng)

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
    parser.add_argument("--seed", type=int, default=20261109, help="seed for repeatable colors and grain")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="where to save the png")
    args = parser.parse_args()

    if WIDTH < 2 or HEIGHT < 2 or WIDTH != HEIGHT:
        parser.error("width and height must match and be at least 2 for a tileable square image")

    image = make_image(args.seed)
    args.output.write_bytes(image)
    print(f"made {WIDTH}x{HEIGHT} tile at {args.output} ({len(image):,} bytes, seed {args.seed})")


if __name__ == "__main__":
    main()
