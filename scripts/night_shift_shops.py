# Five original voxel storefronts for the corner's ground floors, at the ramen stand's scale (0.05 m voxels):
# electronics repair (tooling), net cafe (job search), hydroponics florist (projects), 24h mart (spare slot) and the
# hobby store GAME HUB (games, 2026-11-04), plus Block_Low, the 2 m low block beside the florist.
# Run on the kit after night_shift_ramen.py:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-kit.blend --python scripts/night_shift_shops.py
# Adds kit_custom/Shop_{Repair,NetCafe,Florist,Mart} and renders _attachments/previews/night-shift-3d-shops.png.
# Local voxel axes: x along the facade (reads left to right from the street), y = 0 is the facade plane with the street
# at -y, z up. Each shop is one whole ground floor (W wide, D deep, 50 tall = 2.5 m) so the corner's upper blocks
# stack on it. The camera looks down at 30 degrees, so only the front 24 voxels of the interior can be seen: props stand
# there and the back wall closes it off. Signs, awnings and sidewalk props sit at y < 0.
import bpy, sys, math, random, os
from mathutils import Vector, Euler

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
sys.path.insert(0, VAULT + r"\scripts")
import night_shift_ramen as R
from night_shift_ramen import box, cyl, vox

V = R.V
P = {**R.P,
     "conc": ((0.30, 0.29, 0.33), None), "conc_d": ((0.17, 0.16, 0.20), None), "seam": ((0.12, 0.11, 0.14), None),
     "tile_a": ((0.34, 0.35, 0.38), None), "tile_b": ((0.24, 0.25, 0.28), None), "wall_in": ((0.40, 0.40, 0.44), None),
     "sign_bg": ((0.04, 0.04, 0.06), None), "desk": ((0.12, 0.12, 0.15), None), "box_c": ((0.55, 0.40, 0.24), None),
     "pcb": ((0.04, 0.35, 0.16), None), "copper": ((0.75, 0.45, 0.20), None), "tool_y": ((0.90, 0.68, 0.10), None),
     "vio_panel": ((0.22, 0.12, 0.35), None), "chair_k": ((0.07, 0.07, 0.09), None), "chair_r": ((0.65, 0.06, 0.12), None),
     "hair": ((0.10, 0.07, 0.08), None), "jacket": ((0.15, 0.20, 0.35), None), "soil": ((0.15, 0.09, 0.05), None),
     "leaf_d": ((0.05, 0.25, 0.08), None), "leaf_m": ((0.12, 0.45, 0.12), None), "leaf_l": ((0.35, 0.68, 0.18), None),
     "pvc": ((0.82, 0.83, 0.80), None), "bucket": ((0.18, 0.22, 0.28), None), "terra": ((0.62, 0.28, 0.14), None),
     "awn_g": ((0.08, 0.42, 0.24), None), "fl_r": ((0.85, 0.08, 0.15), None), "fl_y": ((0.95, 0.80, 0.10), None),
     "fl_w": ((0.95, 0.93, 0.95), None), "fl_p": ((0.90, 0.30, 0.70), None), "fl_o": ((0.95, 0.45, 0.10), None),
     "mart_blue": ((0.04, 0.16, 0.55), None), "can_r": ((0.80, 0.10, 0.10), None), "can_b": ((0.10, 0.30, 0.80), None),
     "can_y": ((0.90, 0.80, 0.15), None), "can_g": ((0.15, 0.60, 0.25), None), "snack_o": ((0.95, 0.50, 0.10), None),
     # glow (base colour x strength, as in the ramen palette)
     "neon_org": ((1.0, 0.42, 0.08), 1.3), "neon_grn": ((0.25, 1.0, 0.35), 1.3), "neon_vio": ((0.6, 0.25, 1.0), 1.3),
     "screen_c": ((0.20, 0.85, 1.0), 0.9), "screen_g": ((0.30, 1.0, 0.50), 0.8), "screen_b": ((0.30, 0.45, 1.0), 0.9),
     "screen_w": ((0.85, 0.90, 1.0), 0.8), "grow": ((1.0, 0.22, 0.85), 1.2), "lamp_w": ((1.0, 0.88, 0.65), 1.2),
     "fluor": ((0.88, 0.95, 1.0), 1.1), "fridge": ((0.70, 0.90, 1.0), 0.7),
     }
FLOWERS = ("fl_r", "fl_y", "fl_w", "fl_p", "fl_o")
SCREENS = ("screen_c", "screen_g", "screen_b", "screen_w", "static", "board")
PRODUCTS = ("can_r", "can_b", "can_y", "can_g", "snack_o", "box_c", "white", "red_b")

# 5x7 pixel font for the signs (original lettering, only the glyphs the signs use)
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I":("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    " ": (".....",) * 7,
}


def text(s, x0, y, zt, col):
    """Letters on the plane y, top row at zt, 6 voxels per character."""
    for i, ch in enumerate(s):
        for r, row in enumerate(FONT[ch]):
            for c, v in enumerate(row):
                if v == "#":
                    vox[(x0 + i * 6 + c, y, zt - r)] = col
    return x0 + len(s) * 6 - 1


def shell(W, D, fascia, floor, ID=24):
    box(0, 3, 0, D - 1, 0, 49, "conc"); box(W - 4, W - 1, 0, D - 1, 0, 49, "conc")   # piers, full depth
    box(0, W - 1, 0, D - 1, 46, 49, "conc_d")                                       # slab the upper blocks sit on
    box(0, W - 1, 0, 1, 40, 49, fascia)                                             # sign band over the opening
    box(4, W - 5, ID, ID, 1, 45, "wall_in")                                         # back wall; the rest stays hollow
    a, b = floor
    box(4, W - 5, 0, ID - 1, 0, 0, lambda x, y, z: a if (x // 4 + y // 4) % 2 else b)
    for x in range(W):
        vox[(x, -1, 40)] = vox[(x, -1, 49)] = "steel_d"                            # sign ledge and cap
    for px in (0, W - 4):
        box(px, px + 3, 0, 0, 0, 1, "steel_d")                                      # kick plate
        for z in (13, 26, 38):
            box(px, px + 3, 0, 0, z, z, "seam")                                     # cast panel seams


def screen(x0, x1, y, z0, z1, kind, rnd):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            vox[(x, y, z)] = rnd.choice(("screen_w", "board", "screen_b")) if kind == "static" else kind


def monitor(x0, y0, z0, w, h, rnd):
    box(x0, x0 + w - 1, y0, y0 + 4, z0, z0 + h - 1, "desk")
    screen(x0 + 1, x0 + w - 2, y0, z0 + 1, z0 + h - 2, rnd.choice(SCREENS), rnd)


def plant(rnd, cx, cy, z0, h, cols, fruit=None):
    for z in range(z0, z0 + h):
        top = z == z0 + h - 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if rnd.random() < (0.35 if top else 0.85):
                    vox[(cx + dx, cy + dy, z)] = fruit if fruit and rnd.random() < 0.12 else rnd.choice(cols)


def bucket(rnd, x, y, z0, col):
    """A florist's bucket of cut flowers: stems with heads at different heights."""
    cyl(x, y, 2, z0, z0 + 4, "bucket")
    for _ in range(9):
        dx, dy, h = rnd.randint(-1, 1), rnd.randint(-1, 1), rnd.randint(3, 7)
        for z in range(z0 + 5, z0 + 5 + h):
            vox[(x + dx, y + dy, z)] = "leaf_m"
        vox[(x + dx, y + dy, z0 + 5 + h)] = col
        for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if rnd.random() < 0.5:
                vox[(x + dx + ex, y + dy + ey, z0 + 4 + h)] = col


GEAR = ("..#.#..", ".#####.", "###.###", "#.....#", "###.###", ".#####.", "..#.#..")


def blade_sign():
    """REPAIR as a vertical blade on the left pier: a board in front of the facade (y -6, brackets back to the wall), gear icon on top,
    the letters stacked below, amber on a dark board with a framed edge. Spans z 8 to 66 so it rises past the fascia."""
    x0, x1, y, zt = 0, 10, -6, 66
    box(x0, x1, y, y, 7, zt, "sign_bg")
    for z in range(7, zt + 1):
        vox[(x0, y, z)] = vox[(x1, y, z)] = "neon_org"
    for x in range(x0, x1 + 1):
        vox[(x, y, 7)] = vox[(x, y, zt)] = "neon_org"
    for r, row in enumerate(GEAR):                              # gear, centred
        for c, v in enumerate(row):
            if v == "#":
                vox[(x0 + 2 + c, y - 1, zt - 2 - r)] = "neon_org"
    for i, ch in enumerate("REPAIR"):                            # letters stacked, 5 wide, 8 rows each
        for r, row in enumerate(FONT[ch]):
            for c, v in enumerate(row):
                if v == "#":
                    vox[(x0 + 3 + c, y - 1, zt - 12 - i * 8 - r)] = "neon_org"
    for z in (12, 40, 60):                                       # brackets back to the pier
        box(x0 + 4, x0 + 5, y + 1, -1, z, z, "steel_d")


def repair():
    W, D, rnd = 80, 44, random.Random(11)
    shell(W, D, "sign_bg", ("tile_b", "conc_d"))
    blade_sign()                                              # vertical amber blade with a gear (sign pilot, 2026-11-05)
    box(6, W - 7, -1, -1, 44, 44, "neon_org")                 # thin amber strip along the dark fascia
    for z in range(35, 40):                                   # half-raised roll shutter
        box(4, W - 5, 0, 0, z, z, "steel" if z % 2 else "steel_d")
    box(37, 43, -1, -1, 35, 35, "steel")
    # workbench with a strip light, a gutted board, an open laptop, a magnifier lamp, an iron and parts bins
    box(6, 52, 3, 9, 1, 15, "desk"); box(5, 53, 2, 9, 16, 16, "steel")
    for x in range(6, 53):
        vox[(x, 2, 13)] = "neon_org"
        if x % 6 == 0:
            box(x, x, 3, 3, 2, 12, "seam")
    box(9, 19, 4, 8, 17, 17, "pcb")
    for x, y in ((11, 5), (14, 6), (17, 5), (12, 7), (16, 7)):
        vox[(x, y, 18)] = "board"
    for x in range(10, 19, 2):
        vox[(x, 8, 18)] = "copper"
    box(23, 33, 4, 7, 17, 17, "steel_d"); box(23, 33, 8, 8, 17, 24, "steel_d"); screen(24, 32, 8, 18, 23, "screen_c", rnd)
    box(25, 31, 8, 8, 22, 22, "screen_w")
    box(41, 41, 8, 8, 17, 27, "steel"); box(41, 45, 8, 8, 27, 27, "steel"); box(43, 47, 5, 8, 25, 26, "steel_d")
    box(44, 46, 4, 4, 25, 26, "lamp_w")
    box(35, 38, 5, 5, 17, 17, "tool_y"); vox[(39, 5, 17)] = "steel"; box(36, 37, 7, 7, 17, 18, "steel_d")
    for i, c in enumerate(("red_b", "crate", "yel_b")):
        box(47, 51, 3 + 2 * i, 4 + 2 * i, 17, 18 + i, c)
    # back shelving: monitors and TVs waiting for repair, boxes on top and on the floor
    for px in (6, 28, 50):
        box(px, px + 1, 16, 23, 1, 36, "steel_d")
    for z in (10, 21, 32):
        box(6, 51, 16, 23, z, z, "steel")
    for z0 in (11, 22):
        x = 8
        while True:
            w = rnd.choice((6, 8, 10))
            if x + w > 50:
                break
            if x <= 28 <= x + w or x <= 29 <= x + w:
                x = 30; continue
            monitor(x, 17, z0, w, rnd.choice((5, 7, 9)), rnd); x += w + 1
    x = 8
    while x < 48:
        w, h = rnd.randint(5, 9), rnd.randint(4, 9)
        box(x, min(x + w, 49), 17, 22, 1, h, "box_c" if rnd.random() < 0.7 else "desk"); x += w + 2
    for x in range(8, 49, 7):
        box(x, x + 4, 18, 22, 33, 33 + rnd.randint(1, 3), "box_c")
    box(56, 73, 14, 23, 1, 30, "steel_d")                   # parts cabinet with labelled drawers
    for x in range(57, 72, 4):
        for z in range(2, 29, 3):
            box(x, x + 2, 13, 13, z, z + 1, rnd.choice(("steel", "crate", "red_b", "yel_b", "steel", "white")))
            vox[(x + 1, 12, z)] = "white"
    for x, y in ((12, 6), (31, 5), (48, 7)):                 # cables hanging from the ceiling
        box(x, x, y, y, 29, 45, "rubber"); vox[(x, y, 28)] = "copper"
    box(40, 40, 12, 12, 34, 45, "rubber"); box(37, 43, 10, 14, 32, 33, "steel_d"); box(38, 42, 10, 14, 31, 31, "lamp_w")
    box(76, 77, -9, -2, 18, 44, "sign_bg")                   # blade sign, seen from the cross street side
    for y in range(-9, -1):
        for z in range(18, 45):
            if y in (-9, -2) or z in (18, 44):
                vox[(78, y, z)] = "neon_org"
    for i, ch in enumerate("FIX"):
        for r, row in enumerate(FONT[ch]):
            for c, v in enumerate(row):
                if v == "#":
                    vox[(78, -8 + c, 41 - i * 8 - r)] = "neon_cyan"
    box(76, 77, -1, -1, 21, 21, "steel_d"); box(76, 77, -1, -1, 41, 41, "steel_d")
    box(5, 13, -6, -1, 0, 6, "box_c"); box(6, 11, -5, -2, 7, 10, "box_c")   # sidewalk: crates and a dead CRT
    for x in range(5, 14):
        vox[(x, -6, 3)] = "cream"
    box(17, 25, -7, -2, 0, 7, "desk"); screen(18, 24, -7, 1, 6, "board", rnd)
    box(0, 3, 0, 0, 15, 24, "white"); box(0, 3, 0, 0, 22, 24, "red_b")      # flyer on the left pier
    return W, D


def netcafe():
    W, D, rnd = 120, 44, random.Random(23)                    # 6 m: the corner building's ground floor (2026-11-03)
    o = W - 80                                                # the front desk, fridge and job board keep to the right end
    shell(W, D, "sign_bg", ("tile_b", "desk"))
    x0 = (W - 59) // 2
    for x in range(x0, x0 + 9):                               # monitor icon, then NET CAFE
        for z in range(42, 48):
            vox[(x, -1, z)] = "neon_vio" if x in (x0, x0 + 8) or z in (42, 47) else "board"
    vox[(x0 + 4, -1, 41)] = "neon_vio"
    text("NET CAFE", x0 + 12, -1, 47, "neon_blue")           # electric blue + violet, its own colour (2026-11-05)
    for x in range(4, W - 4):
        vox[(x, -1, 39)] = "neon_vio"                         # glowing lip over the opening
    booths = list(range(7, W - 40, 16))
    for px in [b - 1 for b in booths] + [booths[-1] + 15]:   # booth dividers with lit edges
        box(px, px, 12, 23, 1, 25, "vio_panel"); box(px, px, 12, 12, 1, 25, "neon_vio"); box(px, px, 12, 23, 25, 25, "neon_vio")
    for k, bx in enumerate(booths):
        box(bx, bx + 14, 14, 23, 1, 11, "desk"); box(bx, bx + 14, 13, 23, 12, 12, "steel_d")
        box(bx + 2, bx + 12, 19, 21, 13, 22, "desk"); box(bx + 6, bx + 8, 20, 21, 13, 13, "steel")
        screen(bx + 3, bx + 11, 19, 14, 21, rnd.choice(("screen_c", "screen_b", "screen_g")), rnd)
        box(bx + 3, bx + 11, 19, 19, 21, 21, "screen_w")
        box(bx + 4, bx + 7, 19, 19, 15, 18, "screen_w" if k != 1 else "neon_yel")
        box(bx + 4, bx + 10, 15, 16, 13, 13, "rubber")
        for x in range(bx + 4, bx + 11):
            vox[(x, 15, 13)] = "neon_pink" if x % 2 else "neon_cyan"
        box(bx + 3, bx + 11, 9, 9, 1, 1, "steel_d"); box(bx + 7, bx + 7, 5, 13, 1, 1, "steel_d")   # gaming chair
        box(bx + 6, bx + 8, 8, 10, 2, 6, "steel_d"); box(bx + 4, bx + 10, 7, 11, 7, 8, "chair_k")
        box(bx + 4, bx + 10, 6, 6, 9, 18, "chair_k"); box(bx + 6, bx + 6, 6, 6, 10, 17, "chair_r"); box(bx + 8, bx + 8, 6, 6, 10, 17, "chair_r")
        box(bx + 3, bx + 3, 7, 11, 11, 11, "chair_k"); box(bx + 11, bx + 11, 7, 11, 11, 11, "chair_k")
        if k == 1:                                            # someone in booth 2, headphones on
            box(bx + 4, bx + 10, 8, 11, 19, 21, "jacket"); box(bx + 5, bx + 9, 8, 12, 22, 26, "hair")
            box(bx + 4, bx + 4, 9, 11, 23, 25, "neon_pink"); box(bx + 10, bx + 10, 9, 11, 23, 25, "neon_pink")
            box(bx + 5, bx + 9, 10, 10, 27, 27, "rubber")
    box(58 + o, 74 + o, 3, 8, 1, 14, "desk"); box(57 + o, 75 + o, 2, 8, 15, 15, "steel_d")        # front desk with a till
    for x in range(58 + o, 75 + o):
        vox[(x, 2, 13)] = "neon_vio"
    box(63 + o, 68 + o, 6, 8, 16, 21, "desk"); screen(64 + o, 67 + o, 6, 17, 20, "screen_c", rnd)
    box(66 + o, 74 + o, 18, 23, 1, 24, "steel")                       # drinks fridge
    for x in range(67 + o, 74 + o):
        for z in range(2, 24):
            vox[(x, 18, z)] = "steel" if z % 5 == 1 else (rnd.choice(PRODUCTS[:5]) if x % 2 and z % 5 in (2, 3) else "fridge")
    box(57 + o, 64 + o, 19, 23, 1, 20, "desk")                        # snack rack
    for z in (5, 10, 15, 20):
        for x in range(57 + o, 65 + o):
            vox[(x, 18, z - 1)] = rnd.choice(PRODUCTS)
    # job board on the sidewalk: today's listings as lit lines
    box(65 + o, 65 + o, -10, -9, 0, 31, "steel_d"); box(76 + o, 76 + o, -10, -9, 0, 31, "steel_d")
    box(66 + o, 75 + o, -10, -10, 13, 31, "board"); box(65 + o, 76 + o, -10, -9, 32, 32, "steel_d")
    box(66 + o, 75 + o, -10, -10, 28, 30, "neon_yel")
    for z in range(15, 27, 2):
        box(67 + o, 66 + o + rnd.randint(4, 8), -10, -10, z, z, "screen_w")
    box(0, 3, 0, 0, 16, 25, "neon_vio"); box(1, 2, 0, 0, 17, 24, "board")          # small lit frame on the pier
    return W, D


def florist():
    W, D, rnd = 120, 48, random.Random(37)
    shell(W, D, "sign_bg", ("conc", "conc_d"))
    for x in range(4, W - 4):                                 # the lettering is on the balcony panel above (patio())
        vox[(x, -1, 44)] = "neon_grn"
    for y in range(-7, 0):                                    # short striped awning under the fascia
        z = 39 - (-y - 1) // 2
        for x in range(4, W - 4):
            vox[(x, y, z)] = "awn_g" if (x // 5) % 2 else "white"
    for x in range(4, W - 4):
        vox[(x, -8, 36)] = "awn_g" if (x // 5) % 2 else "white"
        if x % 5 in (1, 2, 3):
            vox[(x, -8, 35)] = "awn_g" if (x // 5) % 2 else "white"
    # three grow racks: PVC frames, magenta grow lights under each shelf, trays of greens and herbs
    for rx in (8, 46, 84):
        for px in (rx, rx + 29):
            for py in (14, 23):
                box(px, px, py, py, 1, 32, "pvc")
        for zb in (1, 11, 21, 31):
            box(rx, rx + 29, 14, 23, zb, zb, "pvc")
        for zb in (11, 21, 31):
            box(rx + 1, rx + 28, 14, 15, zb - 1, zb - 1, "grow")
        for zb, cols, fruit in ((1, ("leaf_d", "leaf_m"), "fl_r"), (11, ("leaf_m", "leaf_l"), None), (21, ("leaf_l", "leaf_m"), "fl_y")):
            box(rx + 1, rx + 28, 15, 22, zb + 1, zb + 1, "bucket")
            for x in range(rx + 2, rx + 28, 3):
                for y in (16, 20):
                    plant(rnd, x, y, zb + 2, rnd.randint(3, 7), cols, fruit)
        for x in range(rx, rx + 30, 2):                       # vines trailing off the top shelf
            for z in range(32 - rnd.randint(2, 9), 32):
                vox[(x, 13, z)] = rnd.choice(("leaf_m", "leaf_d"))
        box(rx + 14, rx + 14, 13, 13, 33, 34, "pvc")
    box(8, 113, 13, 13, 35, 35, "pvc")                        # irrigation main feeding the racks
    for i, x in enumerate(range(8, 53, 6)):                   # buckets of cut flowers inside the door
        bucket(rnd, x, 4 + (i % 2) * 3, 1, FLOWERS[i % len(FLOWERS)])
    for x in (62, 80):                                        # hanging planters with trailing vines
        box(x, x, 5, 5, 30, 45, "steel"); box(x - 2, x + 2, 3, 7, 26, 29, "terra")
        plant(rnd, x, 5, 30, 2, ("leaf_m", "leaf_l"))
        for vx, vy in ((x - 2, 3), (x + 2, 3), (x - 2, 7), (x, 3), (x + 2, 7)):
            for z in range(26 - rnd.randint(3, 9), 26):
                vox[(vx, vy - (1 if vy == 3 else -1), z)] = rnd.choice(("leaf_m", "leaf_d", "leaf_l"))
    box(94, 114, 3, 8, 1, 12, "wood_m"); box(93, 115, 2, 8, 13, 13, "wood_l")      # counter with till and a vase
    for x in range(94, 115, 4):
        box(x, x, 2, 2, 2, 11, "wood_d")
    box(108, 112, 5, 7, 14, 17, "desk"); screen(109, 111, 5, 15, 16, "screen_g", rnd)
    cyl(99, 5, 1, 14, 18, "pvc"); plant(rnd, 99, 5, 19, 3, ("fl_p", "fl_w", "leaf_m"))
    # sidewalk: a two-step flower stand and a potted palm by the right pier
    box(10, 52, -12, -9, 0, 4, "wood_m"); box(10, 52, -8, -3, 0, 9, "wood_l")
    for x in range(10, 53, 3):
        vox[(x, -12, 2)] = vox[(x, -8, 6)] = "wood_d"
    for i, x in enumerate(range(13, 51, 6)):
        bucket(rnd, x, -10, 5, FLOWERS[(i + 2) % len(FLOWERS)])
        bucket(rnd, x + 3, -5, 10, FLOWERS[(i + 4) % len(FLOWERS)])
    box(104, 110, -7, -2, 0, 7, "terra"); box(103, 111, -8, -1, 8, 8, "terra"); box(104, 110, -7, -2, 8, 8, "soil")
    for z in range(9, 27):
        box(106, 107, -5, -4, z, z, "wood_d" if z % 3 == 0 else "wood_m")
    for a in range(8):
        dx, dy = math.cos(a * math.pi / 4 + 0.3), math.sin(a * math.pi / 4 + 0.3)
        for t in range(1, 10):
            x, y, z = 106 + round(dx * t), -5 + round(dy * t), 27 - t * t // 12
            if 0 <= x < W:
                vox[(x, y, z)] = "leaf_l" if t % 3 else "leaf_m"
                vox[(x, y, z - 1)] = "leaf_m"
    return W, D


def mart():
    W, D, rnd = 120, 48, random.Random(41)
    shell(W, D, "mart_blue", ("tile_a", "white"))
    box(0, W - 1, 0, 0, 41, 41, "snack_o")                    # orange band under the lettering
    text("24H", 36, -1, 48, "neon_yel"); text("MART", 60, -1, 48, "fluor")
    for x in (24, 44, 64, 84, 104):                           # shopfront frame; the door is 84..104
        box(x, x, 0, 0, 1, 39, "steel_d")
    box(4, W - 5, 0, 0, 36, 36, "steel_d"); box(4, 83, 0, 0, 1, 2, "steel"); box(105, W - 5, 0, 0, 1, 2, "steel")
    box(86, 102, 1, 6, 0, 0, "rubber")                         # door mat
    box(8, 20, 2, 2, 29, 34, "yel_b"); box(10, 18, 2, 2, 31, 32, "red_b")          # hanging sale cards
    box(46, 58, 2, 2, 29, 34, "red_b"); box(48, 56, 2, 2, 31, 32, "white")
    # till counter: register, a lit hot-snack warmer
    box(6, 30, 3, 7, 1, 13, "white"); box(6, 30, 3, 3, 8, 9, "mart_blue"); box(5, 31, 2, 7, 14, 14, "steel")
    box(9, 14, 4, 6, 15, 18, "desk"); screen(10, 13, 4, 16, 17, "screen_g", rnd)
    box(19, 28, 3, 6, 15, 21, "steel"); box(20, 27, 3, 3, 16, 20, "lamp_w")
    for x in (21, 23, 25):
        box(x, x, 3, 3, 17, 19, "broth")
    for x0, x1 in ((36, 62), (66, 82)):                       # gondola shelves: products face the street
        box(x0, x1, 10, 13, 1, 17, "steel_d")
        for zl in (1, 6, 11):
            box(x0, x1, 9, 9, zl, zl, "white")
            for x in range(x0, x1 + 1, 2):
                box(x, min(x + 1, x1), 9, 9, zl + 1, zl + rnd.randint(2, 4), rnd.choice(PRODUCTS))
        for x in range(x0, x1 + 1, 3):
            box(x, min(x + 2, x1), 10 + rnd.randint(0, 2), 12, 18, 17 + rnd.randint(1, 3), rnd.choice(PRODUCTS))
    box(8, 115, 20, 23, 1, 37, "steel")                       # drinks fridges along the back wall
    for x0 in range(9, 114, 12):
        for x in range(x0 + 1, x0 + 11):
            for z in range(2, 35):
                vox[(x, 20, z)] = "steel" if z % 6 == 1 else (rnd.choice(PRODUCTS[:5]) if x % 2 == 0 and z % 6 in (2, 3, 4) else "fridge")
        box(x0 + 9, x0 + 9, 19, 19, 16, 22, "steel_d")
    box(8, 115, 19, 19, 35, 37, "mart_blue")
    # sidewalk: ice chest, recycling bin, two capsule-toy machines
    box(104, 116, -9, -2, 0, 10, "white"); box(104, 116, -9, -9, 6, 7, "mart_blue"); box(103, 117, -10, -1, 11, 11, "steel")
    box(6, 12, -6, -2, 0, 11, "can_g"); box(5, 13, -7, -1, 12, 12, "rubber"); box(8, 10, -7, -7, 9, 10, "white")
    for gx, body in ((16, "red_b"), (24, "crate")):
        box(gx, gx + 6, -5, -1, 0, 8, body); box(gx, gx + 6, -5, -1, 16, 17, body); box(gx, gx + 6, -5, -1, 9, 15, "white")
        for x in range(gx + 1, gx + 6):
            for z in range(10, 15):
                vox[(x, -5, z)] = rnd.choice(FLOWERS)
        vox[(gx + 3, -6, 5)] = "steel"; box(gx + 2, gx + 4, -6, -6, 1, 2, "rubber")
    return W, D


GAMEBOX = ("can_r", "can_b", "can_y", "can_g", "snack_o", "fl_p", "mart_blue", "white", "vio_panel", "fl_o")
PAD = (("..#######.."), (".#.......#."), ("#..#...#..#"), ("#.###.#.#.#"), ("#..#...#..#"), ("##.......##"))   # gamepad icon


def cabinet(x0, y0, body, scr, rnd):
    """An arcade cabinet, 8 wide, 9 deep, 30 tall, facing the street: lit marquee, screen, control deck, stick, buttons."""
    box(x0, x0 + 7, y0, y0 + 8, 1, 30, body)
    box(x0 + 1, x0 + 6, y0, y0, 27, 29, "neon_pink")
    screen(x0 + 1, x0 + 6, y0, 16, 24, scr, rnd)
    box(x0, x0 + 7, y0 - 3, y0 - 1, 12, 13, body)
    box(x0 + 2, x0 + 2, y0 - 2, y0 - 2, 14, 17, "steel"); vox[(x0 + 2, y0 - 2, 18)] = "red_b"
    for i, c in enumerate(("yel_b", "fl_p", "can_g")):
        vox[(x0 + 4 + i, y0 - 2, 14)] = c
    box(x0, x0, y0, y0 + 8, 2, 26, "neon_cyan")


def games():
    """The hobby store (`games`): 6 m, the old lobby widened by 2 m taken from the low block (2026-11-04). Arcade cabinets,
    a trading-card counter, a wall of board games, a play table with two players, a spinner rack, a door aisle kept clear at
    x 18..42 (walker B comes out there), sidewalk A-board and bench kept clear of y -45..-1 for x < 60 (his route and the punk)."""
    W, D, rnd = 120, 44, random.Random(61)
    shell(W, D, "vio_panel", ("tile_b", "conc_d"))
    x0 = (W - 61) // 2                                        # gamepad icon, then GAME HUB
    for r, row in enumerate(PAD):
        for c, ch in enumerate(row):
            if ch == "#":
                vox[(x0 + c, -1, 47 - r)] = "neon_pink" if (c, r) in ((7, 2), (6, 3), (8, 3), (7, 4)) else "neon_yel"
    text("GAME HUB", x0 + 14, -1, 47, "neon_pink")
    for x in range(4, W - 4):
        vox[(x, -1, 39)] = "neon_cyan"                        # glowing lip over the opening
    for x in (17, 43, 64, 84, 104):                           # shopfront frame; the door aisle is 18..42
        box(x, x, 0, 0, 1, 38, "steel_d")
    box(4, W - 5, 0, 0, 36, 36, "steel_d")
    box(20, 40, 1, 6, 0, 0, "rubber")                         # door mat
    box(6, 14, 2, 2, 29, 34, "yel_b"); box(8, 12, 2, 2, 31, 32, "red_b")           # hanging sale cards
    cabinet(6, 12, "vio_panel", "screen_c", rnd)              # left of the door
    # trading-card counter: a lit display top of single cards, boosters standing on it, a till
    box(46, 78, 2, 8, 1, 13, "desk")
    for x in range(46, 79):
        vox[(x, 1, 13)] = "neon_vio"
        for y in range(3, 8):
            if 47 <= x <= 77:
                vox[(x, y, 13)] = rnd.choice(("white", "fl_r", "fl_y", "fl_p", "can_b", "can_g", "fl_o"))
    box(45, 79, 1, 8, 14, 14, "steel")
    for k in range(5):
        box(49 + k * 4, 50 + k * 4, 4, 5, 15, 21, rnd.choice(GAMEBOX))
    box(71, 75, 4, 6, 15, 19, "desk"); screen(72, 74, 4, 16, 18, "screen_g", rnd)
    cabinet(46, 14, "chair_k", "screen_g", rnd); cabinet(55, 14, "vio_panel", "screen_b", rnd)   # behind the counter
    # the wall of board games: boxes of different sizes, a label band on each, a lit top edge
    box(62, 115, 22, 23, 1, 39, "steel_d")
    for zl in (1, 11, 21, 31):
        box(62, 115, 18, 22, zl, zl, "steel")
        x = 63
        while x < 113:
            w, h = rnd.randint(3, 6), rnd.randint(6, 9)
            box(x, x + w - 1, 19, 21, zl + 1, zl + h, rnd.choice(GAMEBOX))
            box(x, x + w - 1, 19, 19, zl + h - 2, zl + h - 2, "white")
            x += w + 1
    box(62, 115, 18, 18, 39, 39, "neon_cyan")
    # play table with two players, cards, dice and miniatures, a lamp over it
    for lx, ly in ((82, 7), (105, 7), (82, 14), (105, 14)):
        box(lx, lx + 1, ly, ly + 1, 1, 13, "wood_d")
    box(82, 106, 7, 15, 14, 14, "wood_m"); box(84, 104, 8, 14, 15, 15, "awn_g")
    for cx, cy in ((86, 9), (90, 12), (100, 9)):
        box(cx, cx + 1, cy, cy + 2, 16, 16, "white")
    box(95, 96, 12, 13, 16, 17, "white"); vox[(95, 12, 17)] = "board"; box(97, 98, 10, 11, 16, 17, "red_b")
    for mx, my, c in ((91, 10, "can_r"), (92, 10, "can_r"), (99, 12, "can_b"), (98, 13, "can_b"), (93, 13, "can_g")):
        box(mx, mx, my, my, 16, 18, c)
    box(101, 102, 9, 10, 16, 18, "white")                     # a mug
    for cx, face, jacket, hair in ((76, 1, "jacket", "hair"), (108, -1, "chair_r", "wood_d")):
        box(cx, cx + 4, 9, 13, 8, 8, "chair_k"); box(cx + (0 if face > 0 else 4), cx + (0 if face > 0 else 4), 9, 13, 9, 16, "chair_k")
        box(cx, cx, 9, 9, 1, 7, "steel_d"); box(cx + 4, cx + 4, 13, 13, 1, 7, "steel_d")
        box(cx + 1, cx + 3, 10, 12, 9, 17, jacket); box(cx + 1, cx + 3, 10, 12, 18, 21, "cream"); box(cx + 1, cx + 3, 10, 12, 22, 22, hair)
        box(cx + 1 + face, cx + 3 + face, 10, 12, 7, 8, "steel_d")
    box(94, 94, 10, 10, 30, 45, "rubber"); box(90, 98, 8, 12, 28, 29, "steel_d"); box(91, 97, 9, 11, 27, 27, "lamp_w")
    # spinner rack of dice and sleeves at the right end
    cyl(112, 5, 1, 1, 24, "steel_d")
    for z in (8, 14, 20):
        box(110, 114, 3, 7, z, z + 3, rnd.choice(GAMEBOX)); box(110, 114, 3, 3, z + 4, z + 4, "white")
    # sidewalk: A-board for the week's events and a bench, clear of walker B and the punk
    box(66, 75, -6, -5, 0, 17, "wood_d"); box(67, 74, -7, -7, 3, 15, "board"); box(66, 75, -6, -5, 18, 18, "wood_l")
    box(68, 73, -7, -7, 12, 13, "neon_pink"); box(68, 72, -7, -7, 9, 9, "neon_cyan"); box(68, 73, -7, -7, 6, 6, "screen_w")
    box(86, 104, -8, -5, 5, 5, "wood_l"); box(86, 87, -8, -5, 0, 4, "steel_d"); box(103, 104, -8, -5, 0, 4, "steel_d")
    box(86, 104, -8, -8, 6, 12, "wood_m")
    box(0, 3, 0, 0, 15, 24, "white"); box(1, 2, 0, 0, 18, 20, "fl_p")                # flyer on the left pier
    box(W - 4, W - 1, 0, 0, 16, 25, "neon_vio"); box(W - 3, W - 2, 0, 0, 17, 24, "board")
    return W, D


def leafy(rnd, cx, cy, z, a, b, slope, cols, holes=False):
    """One flat leaf: an ellipse a x b voxels tilted by slope (z rise per voxel of y); holes = monstera splits."""
    for dx in range(-a, a + 1):
        for dy in range(-b, b + 1):
            r = (dx / a) ** 2 + (dy / b) ** 2
            if r <= 1 and not (holes and r > 0.35 and (dx + 2 * dy) % 4 == 0):
                vox[(cx + dx, cy + dy, z + round(dy * slope))] = rnd.choice(cols)


def palm(rnd, x, y, z, trunk, reach, droop=1.0):
    """droop < 1 keeps long fronds spread instead of hanging like a willow."""
    for k in range(trunk):
        box(x, x + 1, y, y + 1, z + k, z + k, "wood_d" if k % 3 == 0 else "wood_m")
    top = z + trunk
    for a in range(9):
        dx, dy = math.cos(a * 2 * math.pi / 9 + 0.2), math.sin(a * 2 * math.pi / 9 + 0.2)
        for t in range(1, reach):
            px, py, pz = x + round(dx * t), y + round(dy * t), top - int(t * t * droop / (reach + 2))
            vox[(px, py, pz)] = "leaf_l" if t % 3 else "leaf_m"
            if t > 2:   # leaflets either side of the frond
                vox[(px + round(-dy), py + round(dx), pz - 1)] = "leaf_m"
                vox[(px - round(-dy), py - round(dx), pz - 1)] = "leaf_d"


def monstera(rnd, cx, cy, z0):
    """White pot with six stems, each ending in a split leaf."""
    cyl(cx, cy, 4, z0, z0 + 6, "pvc", top="soil")
    for dx, dy, h, sl in ((-5, -4, 14, 0.5), (4, -5, 18, 0.4), (-6, 3, 20, -0.3), (5, 4, 16, -0.4), (0, -7, 11, 0.6), (1, 1, 24, 0.1)):
        for t in range(h):
            vox[(cx + dx * t // h, cy + dy * t // h, z0 + 7 + t)] = "leaf_m"
        leafy(rnd, cx + dx, cy + dy, z0 + 7 + h, 5, 4, sl, ("leaf_d", "leaf_m"), holes=True)


# ---- street plants (2026-11-03): the packs have none, so these are ours, built from the florist's helpers ----
def potted_palm():
    rnd = random.Random(61)
    box(-5, 4, -5, 4, 0, 9, "terra"); box(-5, 4, -5, 4, 7, 7, "wood_d"); box(-4, 3, -4, 3, 9, 9, "soil")
    palm(rnd, -1, -1, 10, 22, 13); return 10, 10


def potted_snake():
    rnd = random.Random(62)
    box(-3, 2, -3, 2, 0, 6, "bucket"); box(-3, 2, -3, 2, 3, 3, "steel")
    for x in range(-2, 2):
        for y in range(-2, 2):
            if rnd.random() < 0.8:
                h = rnd.randint(10, 20)
                box(x, x, y, y, 7, 6 + h, "leaf_d" if (x + y) % 2 else "leaf_l"); vox[(x, y, 7 + h)] = "fl_y"
    return 6, 6


def potted_monstera():
    monstera(random.Random(63), 0, 0, 0); return 9, 9


def street_tree():
    """A palm in a concrete planter with a glowing green band, for the curb."""
    rnd = random.Random(64)
    box(-10, 9, -10, 9, 0, 10, "conc"); box(-10, 9, -10, 9, 11, 12, "conc_d"); box(-9, 8, -9, 8, 12, 12, "soil")
    for k in range(-10, 10):
        vox[(k, -11, 4)] = vox[(k, 10, 4)] = vox[(-11, k, 4)] = vox[(10, k, 4)] = "neon_grn"
    for x, y in ((-6, -6), (5, -6), (-6, 5), (5, 5), (0, -7), (-7, 0)):
        plant(rnd, x, y, 13, rnd.randint(3, 5), ("leaf_m", "leaf_l"), "fl_p")
    for x, y in ((-8, -8), (7, 7)):
        vox[(x, y, 13)] = "lamp_w"                                  # uplights in the soil
    palm(rnd, -1, -1, 13, 40, 17, droop=0.45); return 20, 20


def street_tree_tall():
    """Twice the curb tree: a 5 m palm with a slight lean and coconuts, in a 1.2 m planter."""
    rnd = random.Random(68)
    box(-12, 11, -12, 11, 0, 11, "conc"); box(-12, 11, -12, 11, 12, 13, "conc_d"); box(-11, 10, -11, 10, 13, 13, "soil")
    for k in range(-12, 12):
        vox[(k, -13, 4)] = vox[(k, 12, 4)] = vox[(-13, k, 4)] = vox[(12, k, 4)] = "neon_grn"
    for x, y in ((-7, -7), (6, -7), (-7, 6), (6, 6), (0, -9), (-9, 0), (8, 0)):
        plant(rnd, x, y, 14, rnd.randint(3, 6), ("leaf_m", "leaf_l"), "fl_p")
    for x, y in ((-10, -10), (9, 9), (9, -10)):
        vox[(x, y, 14)] = "lamp_w"
    top = 14 + 86
    for k in range(86):                                         # trunk leans a little as it rises
        ox = round(2 * math.sin(k / 86 * math.pi / 2))
        box(-1 - ox, 0 - ox, -1, 0, 14 + k, 14 + k, "wood_d" if k % 4 == 0 else "wood_m")
    tx = -3                                                     # where the lean ends
    for dx, dy, dz in ((0, -2, -2), (2, 0, -2), (-1, 1, -3), (1, -1, -3)):
        box(tx + dx, tx + dx, -1 + dy, -1 + dy, top + dz, top + dz, "wood_d")   # coconuts
    palm(rnd, tx, -1, top, 0, 28, droop=0.4)
    palm(rnd, tx, -1, top + 1, 0, 20, droop=0.25)               # a younger inner crown, so the head reads full
    return 24, 24


def ledge_box():
    """A 2.4 m planter that sits on a ledge or roof edge (y 0..5) with greenery trailing down the wall below (y -1)."""
    rnd = random.Random(65)
    box(0, 47, 0, 5, 0, 5, "terra"); box(1, 46, 1, 4, 5, 5, "soil")
    for x in range(2, 46, 3):
        plant(rnd, x, 3, 6, rnd.randint(3, 7), ("leaf_m", "leaf_l", "leaf_d"), rnd.choice(("fl_p", "fl_w", "fl_r", None)))
    for x in range(1, 47, 2):
        if rnd.random() < 0.75:
            for z in range(-rnd.randint(4, 24), 6):
                vox[(x + (z % 3 == 0), -1, z)] = "leaf_l" if z % 2 else "leaf_m"
    return 48, 6


def hanging_basket():
    """Basket on a chain, 0.25 m off the wall (y -5); the chain's top voxel is local z 26."""
    rnd = random.Random(66)
    box(0, 0, -5, -5, 10, 26, "steel"); cyl(0, -5, 3, 6, 9, "terra")
    plant(rnd, 0, -5, 10, 3, ("leaf_m", "leaf_l"), "fl_p")
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)):
        for z in range(6 - rnd.randint(6, 18), 6):
            vox[(dx, -5 + dy, z)] = "leaf_l" if z % 2 else "leaf_m"
    return 7, 7


def bamboo_planter():
    rnd = random.Random(67)
    box(0, 29, 0, 7, 0, 7, "wood_d"); box(1, 28, 1, 6, 7, 7, "soil")
    for x in range(2, 28, 3):
        for y in (2, 5):
            if rnd.random() < 0.75:
                h = rnd.randint(30, 52)
                for z in range(8, 8 + h):
                    vox[(x, y, z)] = "leaf_d" if z % 6 == 0 else "leaf_l"
                for k in range(3):
                    leafy(rnd, x + rnd.choice((-2, 2)), y, 8 + h - rnd.randint(0, 10), 2, 1, 0.3, ("leaf_m", "leaf_l"))
    return 30, 8


def patio():
    """Second-floor balcony on the florist (same local frame: x along the facade, y 0 = wall line, street at -y).
    The deck is drawn at y 0..19 and then moved 1 m out over the sidewalk (y -20..-1, z 50). The shop sign sits on
    the balcony's front panel, since the camera looks down and a railing above the fascia would hide its letters.
    Outdoor stairs come down to the sidewalk past the florist's right end (x 120..171, y -21..-1)."""
    rnd, Z = random.Random(53), 50
    box(0, 119, 0, 19, Z, Z, lambda x, y, z: "wood_l" if (y // 2) % 2 else "wood_m")           # deck planks
    for x in range(0, 108):                                                                   # front railing, gap at the stairs
        vox[(x, 0, Z + 12)] = vox[(x, 0, Z + 6)] = "steel_d"
        if x % 9 == 0:
            box(x, x, 0, 0, Z + 1, Z + 12, "steel_d")
    for y in range(0, 20):
        vox[(0, y, Z + 12)] = vox[(0, y, Z + 6)] = "steel_d"
    for px in (1, 54, 107):                                                                   # pergola with string lights
        box(px, px + 1, 1, 2, Z + 1, Z + 40, "wood_d"); box(px, px + 1, 1, 19, Z + 40, Z + 41, "wood_d")
    box(0, 119, 1, 2, Z + 40, Z + 41, "wood_d")
    for x in range(2, 118, 6):
        box(x, x, 3, 19, Z + 42, Z + 42, "wood_m")
    for x in range(0, 118):
        z = Z + 38 - round(3 * math.sin(math.pi * (x % 27) / 27))
        vox[(x, 3, z)] = "lamp_w" if x % 4 == 0 else "rubber"
    # plants: a big palm, a monstera, a snake plant, a bird of paradise, a fern, pothos everywhere
    box(6, 14, 6, 14, Z + 1, Z + 9, "terra"); box(7, 13, 7, 13, Z + 9, Z + 9, "soil")
    palm(rnd, 9, 9, Z + 10, 26, 15)
    monstera(rnd, 30, 11, Z + 1)
    box(43, 49, 12, 17, Z + 1, Z + 6, "bucket")
    for x in range(44, 49):
        for y in range(13, 17):
            if rnd.random() < 0.6:
                h = rnd.randint(8, 17)
                box(x, x, y, y, Z + 7, Z + 6 + h, "leaf_d" if (x + y) % 2 else "leaf_l")
                vox[(x, y, Z + 7 + h)] = "fl_y"
    box(92, 99, 10, 17, Z + 1, Z + 8, "terra")
    for k in range(7):                                                                        # bird of paradise
        ang = k * 0.9
        lx, ly = round(math.cos(ang) * 4), round(math.sin(ang) * 3)
        for t in range(16 + k % 3 * 3):
            vox[(95 + lx * t // 18, 13 + ly * t // 18, Z + 9 + t)] = "leaf_m"
        leafy(rnd, 95 + lx, 13 + ly, Z + 26 + k % 3 * 3, 2, 4, 0.8, ("leaf_d", "leaf_m"))
    for fx, fz in ((93, Z + 30), (98, Z + 27)):
        box(fx, fx + 3, 12, 12, fz, fz, "fl_o"); box(fx + 3, fx + 4, 12, 12, fz - 1, fz, "can_b"); box(fx, fx, 12, 13, fz - 3, fz, "leaf_m")
    box(78, 82, 4, 8, Z + 1, Z + 10, "wood_d")                                                # fern on a plant stand
    for a in range(10):
        dx, dy = math.cos(a * 0.63), math.sin(a * 0.63)
        for t in range(1, 8):
            vox[(80 + round(dx * t), 6 + round(dy * t), Z + 13 - t * t // 10)] = "leaf_l" if t % 2 else "leaf_m"
    for x in list(range(2, 20, 2)) + list(range(98, 107, 2)):                               # pothos trailing over the railing,
        for z in range(Z + 12 - rnd.randint(8, 30), Z + 13):                                 # clear of the sign letters (x 22..96)
            vox[(x + (z % 3 == 0), -1, z)] = "leaf_l" if z % 2 else "leaf_m"
    for x0, x1 in ((2, 30), (60, 106)):
        box(x0, x1, 1, 3, Z + 1, Z + 4, "terra")
        for x in range(x0, x1, 2):
            vox[(x, 2, Z + 5)] = rnd.choice(("leaf_m", "leaf_l", "fl_p", "fl_w"))
    box(54, 55, 10, 11, Z + 26, Z + 39, "steel")                                              # hanging basket of pothos
    cyl(54, 10, 3, Z + 22, Z + 25, "terra")
    for dx in (-3, -1, 1, 3):
        for z in range(Z + 22 - rnd.randint(4, 14), Z + 22):
            vox[(54 + dx, 10 + (dx > 0) * 3 - 1, z)] = "leaf_l" if z % 2 else "leaf_m"
    box(62, 71, 8, 14, Z + 14, Z + 14, "wood_d"); box(66, 67, 10, 12, Z + 1, Z + 13, "steel_d")   # table and chairs
    for cx in (59, 73):
        box(cx - 1, cx + 1, 9, 13, Z + 8, Z + 8, "wood_m"); box(cx, cx, 11, 11, Z + 1, Z + 7, "steel_d")
        box(cx + (1 if cx < 66 else -1) * -1, cx + (1 if cx < 66 else -1) * -1, 9, 13, Z + 9, Z + 16, "wood_m")
    box(64, 65, 10, 10, Z + 15, Z + 17, "neon_yel")                                           # candle jar
    moved = {(x, y - 20, z): c for (x, y, z), c in vox.items()}                              # out over the sidewalk
    vox.clear(); vox.update(moved)
    box(0, 107, -20, -2, Z - 1, Z - 1, "conc_d")                                              # slab, clear of the fascia ledge
    for x in range(0, 108):                                                                   # hanging plank: wood, ragged lower edge
        lo = Z + 1 + (x * 7 + x // 3) % 3
        box(x, x, -20, -20, lo, Z + 8, "wood_d")
    for x in range(0, 108, 4):                                                                # lime glow strip along the top
        box(x, min(x + 2, 107), -21, -21, Z + 8, Z + 8, "neon_lime")
    leaf = ("....##.", "...###.", "..####.", ".#####.", ".####..", ".#.#...", "#......")
    for r, row in enumerate(leaf):
        for c, v in enumerate(row):
            if v == "#":
                vox[(22 + c, -21, Z + 8 - r)] = "neon_lime"
    text("HYDRO FLORA", 32, -21, Z + 8, "neon_lime")
    vr = random.Random(77)
    for x in range(1, 107, 3):                                                                # vines trailing from the plank, with leaves
        for z in range(Z + 1 - vr.randint(3, 13), Z + 2):
            vox[(x, -21, z)] = "leaf_l" if z % 3 else "leaf_m"
        if vr.random() < 0.5:
            vox[(x + 1, -21, Z - 2)] = "leaf_m"
    for bx in (1, 20, 99, 106):                                                               # brackets under the slab
        for t in range(18):
            vox[(bx, -19 + t, Z - 2 - t * 8 // 17)] = "steel_d"
    # stairs: landing beside the balcony, ten steps down to the sidewalk, stringers and a handrail
    box(108, 123, -21, -1, Z, Z, "steel"); box(123, 123, -21, -21, 0, Z - 1, "steel_d"); box(123, 123, -1, -1, 0, Z - 1, "steel_d")
    for y in range(-21, 0):
        vox[(108, y, Z + 12)] = "steel_d"
    for k in range(8):                                                                        # eight steps, 2026-11-04: the foot
        x0, zt = 124 + 5 * k, Z - Z * (k + 1) // 8                                            # must stop short of the drinks machine
        box(x0, x0 + 4, -20, -2, zt - 1, zt, "steel")
        vox[(x0, -20, zt)] = vox[(x0, -2, zt)] = "neon_yel"                                   # step-edge marker lights
    for x in range(124, 164):
        zl = Z - (x - 124) * 50 // 40
        box(x, x, -21, -21, max(zl - 4, 0), zl, "steel_d"); box(x, x, -1, -1, max(zl - 4, 0), zl, "steel_d")
        vox[(x, -21, zl + 12)] = "steel"
        if x % 10 == 4:
            box(x, x, -21, -21, zl + 1, zl + 11, "steel_d")
    box(108, 123, -21, -21, Z + 1, Z + 12, lambda x, y, z: "steel_d" if x % 5 == 3 or z == Z + 12 else None)
    for k in [k for k, v in vox.items() if v is None]:
        del vox[k]
    for x, y in ((112, -16), (118, -6)):                                                      # pots on the landing
        box(x - 2, x + 2, y - 2, y + 2, Z + 1, Z + 5, "terra"); plant(rnd, x, y, Z + 6, 5, ("leaf_m", "leaf_l"), "fl_p")
    return 164, 20


def block_low():
    """The 2 m low block between the florist and the far tower (2026-11-04: the hobby store took 2 m of the old 4 m one).
    Same frame as the shops: y 0 is the wall line, the body is behind it. Roof at 1.6 m, where the couch sits."""
    rnd = random.Random(71)
    box(0, 39, 0, 41, 0, 31, "conc")
    box(0, 39, 0, 41, 31, 31, "conc_d")
    for x in (0, 39):
        box(x, x, 0, 0, 0, 30, "seam")
    for z in (10, 20):
        box(0, 39, 0, 0, z, z, "seam")
    box(13, 26, 0, 0, 1, 24, "steel_d"); box(14, 25, 0, 0, 2, 23, "steel")        # a service door
    for z in (6, 12, 18):
        box(15, 24, 0, 0, z, z, "steel_d")
    box(11, 12, -1, -1, 22, 23, "neon_org")                                       # its lamp
    box(28, 36, 0, 0, 14, 21, "vio_panel")                                         # a vent grille
    for z in range(15, 21, 2):
        box(28, 36, 0, 0, z, z, "seam")
    return 40, 42


def level(zo, draw):
    """Draw into the voxel map as if on the ground floor, then lift what was drawn by zo voxels (an upper floor of a tall piece)."""
    saved = dict(vox); vox.clear()
    draw()
    layer = dict(vox); vox.clear(); vox.update(saved)
    for (x, y, z), c in layer.items():
        vox[(x, y, z + zo)] = c


def booth_row(W, rnd, k0=0, lit=("screen_c", "screen_b", "screen_g")):
    """Gaming booths along the back (the net cafe's), dividers with lit edges, a chair and a monitor each."""
    booths = list(range(7, W - 40, 16))
    for px in [b - 1 for b in booths] + [booths[-1] + 15]:
        box(px, px, 12, 23, 1, 25, "vio_panel"); box(px, px, 12, 12, 1, 25, "neon_vio"); box(px, px, 12, 23, 25, 25, "neon_vio")
    for k, bx in enumerate(booths):
        box(bx, bx + 14, 14, 23, 1, 11, "desk"); box(bx, bx + 14, 13, 23, 12, 12, "steel_d")
        box(bx + 2, bx + 12, 19, 21, 13, 22, "desk"); box(bx + 6, bx + 8, 20, 21, 13, 13, "steel")
        screen(bx + 3, bx + 11, 19, 14, 21, rnd.choice(lit), rnd)
        box(bx + 3, bx + 11, 19, 19, 21, 21, "screen_w")
        box(bx + 4, bx + 7, 19, 19, 15, 18, "screen_w" if k != 1 else "neon_yel")
        box(bx + 4, bx + 10, 15, 16, 13, 13, "rubber")
        for x in range(bx + 4, bx + 11):
            vox[(x, 15, 13)] = "neon_pink" if x % 2 else "neon_cyan"
        box(bx + 3, bx + 11, 9, 9, 1, 1, "steel_d"); box(bx + 7, bx + 7, 5, 13, 1, 1, "steel_d")
        box(bx + 6, bx + 8, 8, 10, 2, 6, "steel_d"); box(bx + 4, bx + 10, 7, 11, 7, 8, "chair_k")
        box(bx + 4, bx + 10, 6, 6, 9, 18, "chair_k"); box(bx + 6, bx + 6, 6, 6, 10, 17, "chair_r"); box(bx + 8, bx + 8, 6, 6, 10, 17, "chair_r")
        box(bx + 3, bx + 3, 7, 11, 11, 11, "chair_k"); box(bx + 11, bx + 11, 7, 11, 11, 11, "chair_k")
        if (k + k0) % 3 == 1:                                  # someone in this booth, headphones on
            box(bx + 4, bx + 10, 8, 11, 19, 21, "jacket"); box(bx + 5, bx + 9, 8, 12, 22, 26, "hair")
            box(bx + 4, bx + 4, 9, 11, 23, 25, "neon_pink"); box(bx + 10, bx + 10, 9, 11, 23, 25, "neon_pink")
            box(bx + 5, bx + 9, 10, 10, 27, 27, "rubber")


def loft_netcafe():
    """The net cafe (`jobs`) as a two-storey loft (layout job 4, 2026-11-04), 6 m x 2.2 m x 6 m. The bottom metre is a blank
    spandrel panel that carries the clinic's sign below (pack modules, placed by the corner script); then two floors of booths
    behind open glazing, the upper with a lounge, a mezzanine slab between them and NET CAFE across the top."""
    W, D, rnd = 120, 44, random.Random(23)
    SP = 20
    box(0, W - 1, 0, D - 1, 0, SP - 1, "conc"); box(0, W - 1, 0, D - 1, SP - 1, SP - 1, "conc_d")
    for x in range(0, W, 20):
        box(x, x, 0, 0, 0, SP - 2, "seam")
    def frame():
        box(0, 3, 0, D - 1, 0, 99, "conc"); box(W - 4, W - 1, 0, D - 1, 0, 99, "conc")
        box(4, W - 5, 24, 24, 1, 95, "wall_in")
        box(4, W - 5, 0, 23, 0, 0, lambda x, y, z: "tile_b" if (x // 4 + y // 4) % 2 else "desk")
        box(0, W - 1, 0, D - 1, 47, 50, "conc_d")
        box(0, W - 1, 0, 1, 44, 50, "sign_bg")                                       # lip over the lower floor
        for x in range(4, W - 4):
            vox[(x, -1, 46)] = "neon_vio"
    level(SP, frame)
    level(SP, lambda: booth_row(W, rnd))                                              # lower floor
    def rail():
        """A railing along each floor's open front (nobody falls out): posts, two rails, a violet edge light (2026-11-05)."""
        for x in range(5, W - 4, 12):
            box(x, x + 1, 0, 0, 1, 11, "steel_d")
        box(4, W - 5, 0, 0, 11, 11, "steel"); box(4, W - 5, 0, 0, 6, 6, "steel_d")
        for x in range(4, W - 4):
            vox[(x, -1, 12)] = "neon_vio"
    def counter():
        """A high counter with two monitors and stools on the lower floor's free right end, so the front is not just empty floor."""
        box(86, 114, 5, 8, 1, 10, "desk"); box(85, 115, 4, 8, 11, 11, "steel")
        monitor(88, 6, 12, 8, 7, rnd); monitor(100, 6, 12, 8, 7, rnd)
        for sx in (92, 104, 111):
            cyl(sx, 14, 2, 1, 6, "chair_k", top="chair_r")
    level(SP, rail); level(SP, counter)
    def upper():
        booth_row(W, random.Random(29), 1, ("screen_b", "screen_g", "screen_c"))
        box(8, 30, 2, 8, 1, 6, "chair_r"); box(8, 30, 2, 3, 7, 14, "chair_r")         # lounge sofa and low table, right of the booths
        box(36, 44, 3, 7, 1, 6, "desk"); box(37, 43, 4, 6, 7, 7, "neon_pink")
        for lx in (30, 78):
            box(lx, lx, 9, 9, 30, 45, "rubber"); box(lx - 3, lx + 3, 7, 11, 28, 29, "steel_d"); box(lx - 2, lx + 2, 8, 10, 27, 27, "lamp_w")
    level(SP + 50, upper)
    level(SP + 50, rail)
    def end_windows():
        """Lit windows on the end wall above the catwalk door (the face the camera sees), two panes with mullions."""
        for y0, y1 in ((5, 17), (27, 39)):
            box(W, W, y0 - 1, y1 + 1, 10, 42, "sign_bg"); box(W, W, y0, y1, 12, 40, "lamp_w")
            box(W, W, y0, y1, 26, 26, "sign_bg"); box(W, W, (y0 + y1) // 2, (y0 + y1) // 2 + 1, 12, 40, "sign_bg")
            box(W, W, y0 - 1, y1 + 1, 43, 43, "neon_vio")
    level(SP + 50, end_windows)
    def top():
        box(0, W - 1, 0, 1, 88, 99, "sign_bg")                                       # top band; the name moved to the vertical blade (Sign_NetCafe)
        for x in range(4, W - 4):
            vox[(x, -1, 87)] = "neon_vio"
        for x in range(W):
            vox[(x, -1, 99)] = "steel_d"
    level(SP, top)
    return W, D


def bodymods():
    """The ripperdoc clinic that took the net cafe's ground floor (layout job 4): a surgical chair under a lamp arm, glass
    cases of chrome limbs and eyes along the back, a counter. Its sign is made of pack modules on the loft's spandrel."""
    W, D, rnd = 120, 44, random.Random(33)
    shell(W, D, "sign_bg", ("tile_b", "conc_d"))
    for x in range(4, W - 4):
        vox[(x, -1, 39)] = "neon_grn"                              # green lip over the opening
    for x in (30, 90):
        box(x, x, 0, 0, 1, 38, "steel_d")
    box(4, W - 5, 0, 0, 36, 36, "steel_d")
    box(8, 28, 1, 6, 0, 0, "rubber")
    # surgical chair, tilted back, with a lamp arm and two robotic arms
    box(40, 62, 8, 18, 1, 3, "steel_d"); box(48, 54, 10, 16, 4, 12, "steel")
    box(40, 62, 9, 17, 13, 14, "chair_r"); box(40, 46, 9, 17, 15, 22, "chair_r"); box(56, 62, 11, 15, 15, 16, "chair_r")
    box(36, 38, 8, 8, 1, 40, "steel_d"); box(36, 52, 8, 8, 40, 41, "steel_d"); box(48, 56, 9, 17, 36, 37, "lamp_w")
    for ax, c in ((66, "red_glow"), (72, "neon_cyan")):
        box(ax, ax, 12, 12, 1, 24, "steel"); box(ax, ax - 8, 12, 12, 24, 25, "steel"); vox[(ax, 12, 24)] = c; vox[(ax - 8, 12, 25)] = c
    # glass cases along the back: chrome arms and legs, eyes in jars
    box(8, 112, 20, 23, 1, 36, "steel_d")
    for x0 in range(10, 108, 14):
        for z in range(3, 33, 11):
            box(x0, x0 + 11, 19, 19, z, z + 8, "fridge")
            kind = rnd.random()
            if kind < 0.4:
                box(x0 + 2, x0 + 9, 19, 19, z + 4, z + 5, "steel"); box(x0 + 8, x0 + 10, 19, 19, z + 3, z + 6, "lamp_w")
            elif kind < 0.8:
                box(x0 + 4, x0 + 7, 19, 19, z + 2, z + 6, "screen_c"); vox[(x0 + 5, 19, z + 4)] = "neon_pink"
            else:
                box(x0 + 5, x0 + 6, 19, 19, z + 1, z + 7, "steel"); box(x0 + 3, x0 + 8, 19, 19, z + 7, z + 7, "steel_d")
    box(96, 112, 3, 8, 1, 14, "desk"); box(95, 113, 2, 8, 15, 15, "steel_d"); screen(99, 106, 3, 16, 21, "screen_g", rnd)
    box(0, 3, 0, 0, 15, 24, "neon_grn"); box(1, 2, 0, 0, 17, 24, "board")      # small lit cross frame on the pier
    box(W - 4, W - 1, 0, 0, 16, 25, "red_glow"); box(W - 3, W - 2, 0, 0, 17, 24, "board")
    return W, D


def rm(x0, x1, y0, y1, z0, z1):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                vox.pop((x, y, z), None)


def ramen_shop():
    """The ramen shopfront (`daily`) on the corner building's ground floor (layout job 5, 2026-11-04), where the clinic was and
    the old street stand stood: a red noren valance, hanging lanterns, a wooden interior 2.1 m deep for the pack's bar counter,
    stools and kitchen props (placed by the corner script), a ticket machine on the left pier, a low stool for the diner."""
    W, D, rnd = 120, 44, random.Random(37)
    shell(W, D, "sign_bg", ("wood_m", "wood_d"))
    rm(4, W - 5, 24, 24, 1, 45)                                        # the shell's back wall is at 1.2 m: too shallow for the bar
    box(4, W - 5, 42, 42, 1, 45, "wood_m"); box(4, W - 5, 43, 43, 1, 45, "wood_d")
    for x in range(4, W - 4, 6):
        box(x, x, 42, 42, 12, 44, "wood_d")                            # wall boards
    box(4, W - 5, 41, 41, 30, 30, "neon_org")                          # a warm-orange shelf light on the back wall: kitchen, not street
    for x in range(4, W - 4):
        vox[(x, -1, 39)] = "red_glow"                                  # red lip over the opening
    for x in range(4, W - 13, 12):                                     # noren valance: red cloth strips with gaps, over the whole front
        box(x, x + 8, -1, -1, 31, 38, "red_b")
        box(x + 3, x + 5, -1, -1, 34, 36, "white")
    for x in (14, 38, 62, 86, 108):                                    # red paper lanterns on cords in front of the valance
        box(x - 3, x + 3, -5, -3, 22, 29, "red_glow"); box(x - 3, x + 3, -5, -3, 29, 29, "rubber"); box(x - 3, x + 3, -5, -3, 22, 22, "rubber")
        box(x, x, -4, -4, 30, 38, "rubber")
    box(0, 3, 0, 0, 14, 38, "red_b"); box(W - 4, W - 1, 0, 0, 14, 38, "red_b")                  # a red band down each pier
    box(6, 17, -3, -1, 8, 30, "steel_d")                                # ticket machine on the left: a lit panel and buttons
    box(7, 16, -3, -3, 16, 29, "board"); box(8, 15, -3, -3, 24, 28, "screen_w")
    for r in range(3):
        for c in range(3):
            vox[(9 + c * 3, -3, 17 + r * 2)] = "neon_org" if (r + c) % 2 else "neon_yel"
    box(60, 80, 1, 6, 0, 0, "rubber")                                  # door mat
    box(22, 22, 14, 14, 0, 0, "wood_d")
    box(24, 31, 5, 11, 1, 12, "steel_d")                                # the diner's low stool (seat at 0.65 m), at world x -4.7, y 0.4
    box(24, 31, 5, 11, 13, 13, "red_b")
    box(100, 108, -8, -6, 0, 14, "wood_d"); box(100, 108, -8, -8, 6, 13, "board")                # a small menu stand on the sidewalk
    box(101, 107, -8, -8, 10, 12, "neon_org")
    return W, D


def arcade_floor():
    """The arcade (`games`) on the hobby store's second storey (layout job 5): an open front on the side street, a back wall with
    neon-framed posters, a checker floor, hanging lamps and a magenta ceiling lip. The pack's claw machines and vending
    machine stand inside it (placed by the corner script)."""
    W, D, rnd = 120, 44, random.Random(43)
    box(0, 3, 0, D - 1, 0, 49, "conc"); box(W - 4, W - 1, 0, D - 1, 0, 49, "conc")
    box(0, W - 1, 0, D - 1, 46, 49, "conc_d")
    box(0, W - 1, 0, 1, 44, 49, "sign_bg")
    box(4, W - 5, 24, 24, 1, 45, "wall_in")
    box(4, W - 5, 0, 23, 0, 0, lambda x, y, z: "tile_b" if (x // 4 + y // 4) % 2 else "desk")
    for x in range(4, W - 4):
        vox[(x, -1, 44)] = "neon_pink"                              # magenta lip under the ceiling
    for px0, col in ((18, "neon_cyan"), (56, "neon_yel"), (94, "neon_pink")):      # posters on the back wall, neon-framed
        box(px0, px0 + 16, 23, 23, 14, 38, col); box(px0 + 1, px0 + 15, 23, 23, 15, 37, "board")
        for k in range(5):
            box(px0 + 3, px0 + 3 + rnd.randint(4, 10), 23, 23, 18 + k * 4, 19 + k * 4, col)
    for lx in (30, 60, 90):
        box(lx, lx, 9, 9, 30, 45, "rubber"); box(lx - 3, lx + 3, 7, 11, 28, 29, "steel_d"); box(lx - 2, lx + 2, 8, 10, 27, 27, "lamp_w")
    for z in (12, 24):
        box(4, W - 5, 24, 24, z, z, "seam")
    return W, D


def landing():
    """The corner landing of the catwalk (layout job 5): a platform at 3.5 m, level with the net cafe loft's floor, 1.6 m x 2.3 m,
    railed on the street end and the outer edge, four steps down to the 2.5 m deck, neon under it, a lit door frame and an EXIT
    plate on the end wall. Heights are absolute voxels (the piece is placed with z0 = 0). y 0 is the end wall, street at -y."""
    box(0, 45, -32, 0, 68, 69, "steel_d")
    box(0, 45, -32, -32, 67, 67, "neon_cyan")
    for x in (2, 43):
        box(x, x, -30, -2, 66, 66, "neon_pink")                      # magenta tubes under the platform, a neon shelter
    box(2, 43, -30, -30, 66, 66, "neon_pink")
    for y in (-32, -20, -8, -1):                                     # railing along the outer edge and the street end
        box(0, 0, y, y, 70, 91, "steel_d")
    for x in (0, 12, 24, 36, 45):
        box(x, x, -32, -32, 70, 91, "steel_d")
    box(0, 45, -32, -32, 91, 91, "neon_cyan"); box(0, 45, -32, -32, 80, 80, "steel_d")
    box(0, 0, -32, 0, 91, 91, "neon_cyan"); box(0, 0, -32, 0, 80, 80, "steel_d")
    for k in range(4):                                               # four steps down to the deck, rise 0.25 m
        x0, zt = 46 + 5 * k, 65 - 5 * k
        box(x0, x0 + 4, -20, -1, zt - 1, zt, "steel")
        vox[(x0, -20, zt)] = vox[(x0, -1, zt)] = "neon_cyan"
    for k in range(4):                                               # a handrail that steps down with them, on the outer side
        x0, zt = 46 + 5 * k, 65 - 5 * k
        box(x0, x0 + 4, -21, -21, zt + 20, zt + 20, "neon_cyan")
    box(46, 46, -21, -21, 66, 85, "steel_d"); box(61, 61, -21, -21, 51, 70, "steel_d")
    box(12, 12, -2, -2, 70, 118, "neon_cyan"); box(34, 34, -2, -2, 70, 118, "neon_cyan"); box(12, 34, -2, -2, 118, 118, "neon_cyan")   # door frame
    box(10, 36, -1, -1, 121, 121, "neon_pink")                      # a magenta strip over the door
    box(17, 29, -1, -1, 124, 128, "red_glow")                        # EXIT plate
    return 66, 33


def catwalk():
    """The catwalk deck (layout job 5): 1 m wide at 2.5 m, along the hobby store's arcade from the landing's steps (y 3.4) to the
    florist's balcony (y 8.4): cantilever brackets, a neon-lit rail, magenta and cyan string lights. y 0 is the wall."""
    box(0, 99, -21, 0, 48, 49, "steel_d")
    box(0, 99, -21, -21, 47, 47, "neon_cyan")
    for x in range(0, 100, 15):
        box(x, x, -21, -21, 50, 70, "steel_d")
    box(0, 99, -21, -21, 69, 70, "neon_cyan"); box(0, 99, -21, -21, 60, 60, "steel_d")
    for x in (10, 50, 90):
        for t in range(0, 19):
            vox[(x, -t, 30 + t)] = "steel_d"; vox[(x + 1, -t, 30 + t)] = "steel_d"
    for x in range(0, 100):
        z = 76 - round(5 * math.sin(math.pi * ((x % 25)) / 25))
        if x % 5 == 0:
            vox[(x, -23, z)] = "neon_pink" if (x // 5) % 2 else "neon_cyan"
            vox[(x, -22, z)] = "rubber"
    for x in range(0, 100, 25):
        box(x, x, -22, -21, 71, 81, "rubber")
    return 100, 22


def neon_pole():
    """A street pole at the curb with an arm toward the wall, for hung neon boxes (the pack's Neon_* signs hang from it)."""
    box(0, 4, 0, 4, 0, 99, "steel_d"); box(1, 3, 0, 0, 10, 90, "neon_pink")
    box(-50, 4, 1, 3, 94, 96, "steel_d")
    for x in (-45, -25):
        box(x, x, 2, 2, 80, 94, "rubber")
    return 55, 5


def roof_patio():
    """The rooftop patio on the arcade block's roof (layout job 5), seen from the street side: a plank deck, a low neon-topped rail
    with a gap where the couple sits, a bulkhead with a door, planters, a bench, magenta and cyan string lights.
    The roof edge is at local y -10 (0.5 m past the wall line, the block hangs out); the back is at y 29."""
    rnd = random.Random(59)
    box(0, 119, -10, 29, 0, 0, lambda x, y, z: "wood_l" if (x // 3) % 2 else "wood_m")
    for x in range(0, 120, 15):                                       # front rail with a gap where the couple sits (x 36 to 70)
        if x < 36 or x > 70:
            box(x, x, -10, -10, 1, 20, "steel_d")
    for x0, x1 in ((0, 35), (71, 119)):
        box(x0, x1, -10, -10, 19, 20, "neon_cyan"); box(x0, x1, -10, -10, 10, 10, "steel_d")
    for x in (0, 119):
        box(x, x, -10, 0, 19, 20, "steel_d"); box(x, x, -10, 0, 1, 18, "steel_d") if x == 0 else None
    box(86, 113, 12, 29, 1, 49, "wall_in"); box(85, 114, 11, 29, 49, 50, "tile_a")   # bulkhead and its roof, light enough to read against the dark wall
    box(94, 106, 12, 12, 1, 43, "steel_d"); box(95, 105, 11, 11, 1, 42, "steel")        # the door and its frame
    for z in (10, 20, 30):
        box(95, 105, 11, 11, z, z, "seam")
    box(93, 93, 11, 11, 1, 44, "neon_cyan"); box(107, 107, 11, 11, 1, 44, "neon_cyan"); box(93, 107, 11, 11, 44, 44, "neon_cyan")
    vox[(100, 11, 46)] = "neon_pink"; box(96, 104, 11, 11, 47, 47, "neon_pink")        # a lamp strip over the door
    box(88, 96, 20, 27, 51, 56, "steel_d")                             # an AC unit on the bulkhead roof
    for px in (6, 74):                                                 # planters with bushes
        box(px, px + 14, 16, 26, 1, 8, "terra"); box(px + 1, px + 13, 17, 25, 8, 8, "soil")
        plant(rnd, px + 7, 21, 9, 10, ("leaf_d", "leaf_m", "leaf_l"), "fl_p")
    box(56, 82, 26, 29, 1, 7, "wood_l"); box(56, 82, 29, 29, 8, 14, "wood_m")       # a bench along the back, right of the sign
    box(34, 36, 12, 14, 1, 11, "steel_d"); box(32, 38, 11, 15, 12, 12, "wood_m")     # a small side table
    for x in (0, 60, 119):
        box(x, x, -8, -8, 1, 32, "rubber")
    for x in range(1, 119):
        z = 32 - round(4 * math.sin(math.pi * ((x - 1) % 30) / 30))
        if x % 4 == 0:
            vox[(x, -8, z)] = "neon_pink" if (x // 4) % 2 else "neon_cyan"
    return 120, 40


def roof_patio_abandoned():
    """An abandoned rooftop patio for the foreground block (Andres 2026-11-05: deeper, "an abandoned rooftop patio", where the
    orphans' bags pile up): 6 m x 4.8 m, same frame as roof_patio (front edge y -10, 0.5 m before the wall line, back y 85).
    Then (same night, his notes): the dark bare roof back (no deck), a low parapet instead of the rail, the door closed, no string
    lights. Dark roofing with stains and a few weeds, a bulkhead with a closed door under one dying lamp, dead planters (one tipped
    over)."""
    rnd = random.Random(83)
    for x in range(0, 120):
        for y in range(-10, 86):
            vox[(x, y, 0)] = "conc_d" if rnd.random() < 0.12 else "chair_k"     # dark roofing, weathered patches
            if rnd.random() < 0.006:
                vox[(x, y, 1)] = "leaf_d"                                    # weeds
    box(0, 119, -10, -10, 1, 4, "conc_d"); box(119, 119, -10, 85, 1, 4, "conc_d")   # low parapet, front and right
    box(84, 113, 58, 85, 1, 49, "wall_in"); box(83, 114, 57, 85, 49, 50, "tile_a")   # bulkhead
    box(95, 105, 57, 57, 1, 42, "steel_d")                                   # the door, shut
    for z in (12, 24, 36):
        box(95, 105, 57, 57, z, z, "seam")
    box(94, 94, 56, 56, 1, 43, "steel"); box(106, 106, 56, 56, 1, 43, "steel"); box(94, 106, 56, 56, 43, 43, "steel")
    box(96, 104, 56, 56, 46, 46, "steel_d"); vox[(98, 56, 46)] = "neon_pink"  # the lamp strip, one bulb left
    box(88, 96, 66, 73, 51, 56, "steel_d")                                   # the dead AC unit on the bulkhead roof
    for px, py, tipped in ((6, 50, False), (58, 66, True)):                  # planters with dead shrubs, one tipped over
        if tipped:
            box(px, px + 14, py, py + 8, 1, 10, "terra"); box(px - 6, px, py - 2, py + 10, 1, 2, "soil")
        else:
            box(px, px + 14, py, py + 10, 1, 8, "terra"); box(px + 1, px + 13, py + 1, py + 9, 8, 8, "soil")
            plant(rnd, px + 7, py + 5, 9, 8, ("wood_d", "soil", "wood_m"))
    return 120, 96                                                           # (the old sofa under a torn tarp was removed, Andres 2026-11-05)


BOOKS = ("can_r", "can_b", "can_y", "can_g", "snack_o", "vio_panel", "wood_l", "white", "mart_blue", "fl_p")
BOOK_ICON = (".###.###.", "#...#...#", "#.#.#.#.#", "#...#...#", "#...#...#", ".###.###.")


def library():
    """The library (`library`), 4 m, on the far tower's ground floor (layout job 3, 2026-11-04): a wall of books with a ladder,
    two reading tables with lamps and a reader, hanging lamps, a book cart on the sidewalk. The left end (x < 29) is the
    sidewalk junk pile's side, so the best things are to the right."""
    W, D, rnd = 80, 44, random.Random(81)
    shell(W, D, "wood_d", ("wood_m", "wood_d"))
    x0 = 23                                                    # open-book icon, then LIBRARY, pushed right: the tall palm in
    for r, row in enumerate(BOOK_ICON):                        # front covers the left end of the fascia from the camera
        for c, ch in enumerate(row):
            if ch == "#":
                vox[(x0 + c, -1, 47 - r)] = "neon_org"
    text("LIBRARY", 36, -1, 47, "neon_yel")
    for x in range(4, W - 4):
        vox[(x, -1, 39)] = "neon_org"
    for x in (29, 45):
        box(x, x, 0, 0, 1, 38, "steel_d")
    box(4, W - 5, 0, 0, 36, 36, "steel_d"); box(31, 43, 1, 6, 0, 0, "rubber")
    box(4, W - 5, 22, 23, 1, 38, "wood_d")                      # the wall of books, five shelves
    for zl in (1, 8, 15, 22, 29):
        box(4, W - 5, 18, 22, zl, zl, "wood_l")
        x = 5
        while x < W - 6:
            w, h = rnd.choice((1, 2, 2, 3)), rnd.randint(4, 6)
            box(x, x + w - 1, 19, 21, zl + 1, zl + h, rnd.choice(BOOKS)); x += w
    for x in (38, 41):                                          # ladder
        box(x, x, 16, 16, 1, 34, "wood_l")
    for z in range(4, 34, 5):
        box(38, 41, 16, 16, z, z, "wood_l")
    for tx0, tx1 in ((6, 24), (50, 72)):                        # reading tables
        for lx in (tx0, tx1 - 1):
            for ly in (6, 12):
                box(lx, lx + 1, ly, ly + 1, 1, 11, "wood_d")
        box(tx0, tx1, 6, 13, 12, 12, "wood_m")
    box(14, 15, 8, 9, 13, 13, "steel_d"); box(14, 14, 8, 8, 14, 19, "steel_d"); box(13, 16, 7, 10, 20, 21, "lamp_w")
    box(8, 12, 9, 11, 13, 13, "white"); box(10, 10, 9, 11, 13, 13, "red_b")
    box(19, 22, 8, 11, 13, 15, "can_b"); box(19, 21, 8, 10, 16, 17, "can_r")
    box(58, 65, 10, 10, 13, 19, "desk"); screen(59, 64, 10, 14, 18, "screen_g", rnd); box(58, 65, 7, 9, 13, 13, "steel_d")
    box(57, 61, 2, 5, 8, 8, "chair_k"); box(57, 61, 2, 2, 9, 15, "chair_k")                    # the reader, seen from behind
    box(58, 60, 3, 4, 9, 17, "jacket"); box(58, 60, 3, 4, 18, 21, "cream"); box(58, 60, 3, 4, 22, 22, "hair")
    for lx in (16, 60):
        box(lx, lx, 9, 9, 28, 45, "rubber"); box(lx - 3, lx + 3, 7, 11, 26, 27, "steel_d"); box(lx - 2, lx + 2, 8, 10, 25, 25, "lamp_w")
    box(52, 68, -7, -3, 3, 3, "wood_m"); box(52, 68, -7, -3, 9, 9, "wood_m")                  # book cart on the sidewalk
    box(52, 53, -7, -3, 3, 12, "wood_d"); box(67, 68, -7, -3, 3, 12, "wood_d")
    for x in range(54, 67, 2):
        box(x, x + 1, -6, -4, 4, 8, rnd.choice(BOOKS)); box(x, x + 1, -6, -4, 10, 14, rnd.choice(BOOKS))
    for wx in (52, 68):
        box(wx, wx, -7, -7, 1, 2, "rubber")
    box(0, 3, 0, 0, 15, 24, "white"); box(1, 2, 0, 0, 18, 20, "yel_b")                       # flyer on the left pier
    return W, D


GOLD, GLASS = "neon_org", ("neon_vio", "neon_org", "neon_cyan", "neon_pink", "neon_vio", "neon_grn")


def pointed(xc, z0, hw):
    """Inside test for a pointed (equilateral) arch: straight jambs to z0, then two arcs that meet at a point."""
    def inside(x, z):
        if z < 0:
            return False
        ax = abs(x - xc)
        if z <= z0:
            return ax <= hw
        dz = z - z0
        return (4 * hw * hw - dz * dz) > 0 and ax <= (4 * hw * hw - dz * dz) ** 0.5 - hw
    return inside


def ashlar(x, y, z):
    """Dark brown-black coursed stone: courses 6 voxels tall, blocks 12 wide, joints staggered."""
    c = z // 6
    return "stone_m" if ((x + (c % 2) * 6) // 12 + c * 5) % 5 == 0 else "stone_k"


def ring(xc, z0, hw_in, hw_out, y, col, zmin=0, zmax=400):
    """A moulding: the band between two pointed arches, drawn one voxel proud of the wall."""
    a, b = pointed(xc, z0, hw_in), pointed(xc, z0, hw_out)
    for x in range(int(xc - hw_out) - 1, int(xc + hw_out) + 2):
        for z in range(zmin, min(zmax, int(z0 + hw_out * 1.8) + 2)):
            if b(x, z) and not a(x, z):
                vox[(x, y, z)] = col


def glazed(xc, z0, hw, zmin, zmax, bars_x=None, bars_z=(), depth=3):
    """Carve a pointed window and set stained glass at the back of it, with stone bars and a gold inner outline."""
    win, inner = pointed(xc, z0, hw), pointed(xc, z0, hw - 1.6)
    for x in range(int(xc - hw) - 1, int(xc + hw) + 2):
        for z in range(zmin, zmax):
            if win(x, z):
                rm(x, x, 0, depth - 1, z, z)
                bar = (bars_x and (x - int(xc - hw)) % bars_x == 0) or z in bars_z
                vox[(x, depth, z)] = "stone_m" if bar else GLASS[((x - int(xc - hw)) // 6 + (z - zmin) // 8) % len(GLASS)]
                if not inner(x, z):
                    vox[(x, 0, z)] = GOLD


def cathedral():
    """The library (`library`) after the Scott Monument (Edinburgh), concept v5 approved 2026-11-04: near-black coursed stone,
    pinnacle towers with niches, statues, winged gargoyles and street-facing lanterns, a crocketed gable with a rose window and
    spirelet, two tiers of arches, nested mouldings, a huge stained-glass window and the open double doors onto a lit hall."""
    W, D = 120, 44
    rnd = random.Random(101)
    box(0, W - 1, 0, D - 1, 0, 157, ashlar)
    for z in range(158, 201):                                                    # gable: apex at 200, base 54 each side
        hw = 54 - (z - 158) * 46 // 42
        x0, x1 = int(59.5 - hw), int(59.5 + hw)
        box(x0, x1, 0, 2, z, z, ashlar)
        box(x0, x1, 3, D - 1, z, z, "stone_m" if (z // 2) % 2 else "stone_k")
        vox[(x0, -1, z)] = vox[(x1, -1, z)] = "neon_cyan"
        if (z - 158) % 6 == 2:
            for xx in (x0, x1):
                box(xx - 1, xx + 1, -2, -1, z, z + 1, "stone_l")                # crockets
    for z in range(201, 212):                                                    # the finial, where the arches meet
        hw = max(0, 5 - (z - 201) * 5 // 11)
        box(59 - hw, 60 + hw, 0, 5, z, z, "stone_m" if (z // 3) % 2 else "stone_k")
        if (z - 201) % 3 == 1:
            box(59 - hw - 1, 59 - hw, -1, 0, z, z, "stone_l"); box(60 + hw, 60 + hw + 1, -1, 0, z, z, "stone_l")
    vox[(59, 0, 212)] = vox[(60, 0, 212)] = "neon_cyan"
    for px in (52, 67):                                                          # small pinnacles beside the finial
        box(px, px + 1, -1, 0, 201, 207, "stone_m"); vox[(px, -1, 208)] = "neon_org"
    for z in range(203, 208):
        vox[(59, -1, z)] = vox[(60, -1, z)] = "neon_cyan"                        # a lit slit in the finial

    def gargoyle(gx):
        """A winged gargoyle jutting 1.1 m from the tower: haunches, forelegs with claws, horns, brow, fangs, spine, tail, bat wings."""
        xc = gx + 2
        box(gx, gx + 4, -18, -6, 138, 143, "stone_m"); box(gx, gx + 4, -22, -18, 139, 144, "stone_l")   # body and head
        box(gx - 1, gx + 5, -12, -7, 136, 142, "stone_m")                                              # haunches
        box(gx, gx + 1, -17, -15, 133, 137, "stone_m"); box(gx + 3, gx + 4, -17, -15, 133, 137, "stone_m")  # forelegs
        for cxp in (gx, gx + 1, gx + 3, gx + 4):
            vox[(cxp, -18, 133)] = "stone_l"; vox[(cxp, -18, 134)] = "stone_l"                         # claws
        box(xc, xc, -17, -7, 144, 145, "stone_l")                                                      # spine ridge
        box(gx, gx, -21, -20, 145, 147, "stone_l"); box(gx + 4, gx + 4, -21, -20, 145, 147, "stone_l")  # horns
        box(gx, gx + 4, -23, -23, 143, 143, "stone_k")                                                  # brow
        box(gx + 1, gx + 1, -23, -23, 141, 142, "red_glow"); box(gx + 3, gx + 3, -23, -23, 141, 142, "red_glow")
        box(gx + 1, gx + 3, -24, -23, 139, 140, "stone_l"); vox[(gx + 1, -24, 138)] = vox[(gx + 3, -24, 138)] = "white"  # snout and fangs
        vox[(xc, -24, 139)] = "neon_pink"                                                              # tongue
        box(xc, xc, -7, -7, 126, 141, "stone_m"); box(xc + 1, xc + 1, -7, -7, 126, 128, "stone_m")     # tail curling down the tower
        box(gx + 1, gx + 3, -14, -8, 130, 135, "stone_k")                                              # its support
        for sgn in (-1, 1):                                                                            # wings: membrane, ribs, scalloped edge
            for dx in range(1, 8):
                top = 142 + int(dx * 1.5)
                low = 140 if dx % 3 == 0 else 143 if dx % 3 == 1 else 141
                for z in range(max(low, 139), top + 1):
                    vox[(xc + sgn * (dx + 1), -10, z)] = "stone_l" if (z == top or dx in (2, 4, 6) or z == low) else "stone_m"
                    vox[(xc + sgn * (dx + 1), -9, z)] = "stone_k"
            vox[(xc + sgn * 9, -10, 153)] = "stone_l"                                                  # wing tip claw
    # --- the two corner towers: niches with statues, lit slits, a pinnacle stage, a spire, cyan edge lines, gargoyles ---
    for bx, gx in ((0, 2), (106, 113)):
        cx = bx + 6
        box(bx, bx + 13, -6, 0, 0, 157, ashlar)
        box(bx, bx + 13, -7, -7, 66, 69, "stone_l"); box(bx, bx + 13, -7, -7, 154, 157, "stone_l")      # string courses
        for zn in (84, 112):
            rm(bx + 4, bx + 9, -6, -4, zn, zn + 14)
            box(bx + 4, bx + 9, -4, -4, zn, zn + 14, "stone_k")
            box(bx + 5, bx + 8, -5, -4, zn + 1, zn + 9, "stone_l"); box(bx + 5, bx + 8, -5, -4, zn + 10, zn + 12, "stone_l")   # a statue
            vox[(bx + 6, -6, zn + 15)] = vox[(bx + 7, -6, zn + 15)] = "stone_l"
        rm(bx + 5, bx + 8, -6, -5, 130, 148)
        for z in range(130, 149):
            vox[(bx + 5, -5, z)] = vox[(bx + 6, -5, z)] = vox[(bx + 7, -5, z)] = vox[(bx + 8, -5, z)] = GLASS[(z // 5) % len(GLASS)]
        box(bx + 2, bx + 11, -5, 3, 158, 176, ashlar)                            # pinnacle stage 1
        box(bx + 1, bx + 12, -6, -6, 158, 159, "stone_l")
        box(bx + 4, bx + 9, -3, 2, 177, 192, ashlar)                             # stage 2
        for z in range(193, 207):                                                # the spire
            hw = max(0, 3 - (z - 193) * 3 // 14)
            box(cx - hw, cx + 1 + hw, -2, 1, z, z, "stone_m" if (z // 3) % 2 else "stone_k")
            if (z - 193) % 4 == 1:
                box(cx - hw - 1, cx - hw, -2, -2, z, z, "stone_l"); box(cx + 1 + hw, cx + 2 + hw, -2, -2, z, z, "stone_l")
        vox[(cx, -1, 207)] = vox[(cx + 1, -1, 207)] = "neon_org"
        for z in range(177, 192, 4):
            box(bx + 5, bx + 8, -4, -4, z, z + 1, "neon_cyan")                  # lit bands on stage 2
        gargoyle(5 if bx == 0 else 111)
    box(0, 0, -7, -6, 0, 156, "neon_cyan"); box(W - 1, W - 1, -7, -6, 0, 156, "neon_cyan")
    # --- two tiers of arches: a low flying buttress on the gable face, and a high ogee arch from each tower top to meet at the finial ---
    for side in (0, 1):
        def mx(x):
            return 119 - x if side else x
        for t in range(0, 23):                                                   # tier B
            xx = 12 + t; zz = 166 + int(10 * (1 - (1 - t / 22.0) ** 2))
            box(mx(xx), mx(xx), -3, 0, zz, zz + 2, "stone_l")
            if t % 4 == 2:
                box(mx(xx), mx(xx), -3, -2, zz - 3, zz - 1, "stone_m")           # a hanging cusp
        for t in range(0, 47):                                                   # tier A: meets the finial at x 56
            xx = 10 + t; zz = 188 + int(15 * (1 - (1 - t / 46.0) ** 2))
            box(mx(xx), mx(xx), -3, 0, zz, zz + 2, "stone_l")
            vox[(mx(xx), -3, zz + 3)] = "neon_cyan"
            if t % 6 == 3:                                                       # tracery drops down to the gable
                box(mx(xx), mx(xx), -2, -1, zz - 5, zz - 1, "stone_m"); box(mx(xx) - 1, mx(xx) + 1, -2, -1, zz - 6, zz - 6, "stone_l")
            if t % 12 == 6:                                                      # a crocketed pinnacle on the arch
                box(mx(xx), mx(xx), -3, -2, zz + 3, zz + 9, "stone_m"); vox[(mx(xx), -3, zz + 10)] = "neon_org"
    # --- balustrade of quatrefoil posts and cornices ---
    box(14, 105, -2, 0, 157, 160, "stone_l")
    for x in range(14, 106, 6):
        box(x, x + 2, -1, 0, 146, 156, "stone_m")
    box(14, 105, -2, 0, 144, 145, "stone_l")
    # --- a lantern on each tower front beside the ground-floor lancets, hung forward from an iron arm, facing the street ---
    for c in (6, 112):
        box(c - 1, c + 2, -8, -7, 56, 66, "stone_k")                                                   # wall plate on the tower face
        box(c, c + 1, -13, -7, 62, 63, "stone_k"); box(c, c + 1, -10, -8, 58, 61, "stone_k")           # the arm and its brace
        box(c, c + 1, -14, -12, 59, 61, "stone_k")                                                     # chain
        box(c - 2, c + 3, -17, -10, 48, 57, "neon_org")                                                # the glow
        for cxp in (c - 2, c + 3):
            for cy in (-17, -10):
                box(cxp, cxp, cy, cy, 48, 57, "stone_k")                                               # corner posts
        for zb in (52, 53):
            for cy in (-17, -10):
                box(c - 2, c + 3, cy, cy, zb, zb, "stone_k")                                           # mid bands front and back
            box(c - 2, c - 2, -17, -10, zb, zb, "stone_k"); box(c + 3, c + 3, -17, -10, zb, zb, "stone_k")
        box(c - 3, c + 4, -18, -9, 58, 58, "stone_k"); box(c - 1, c + 2, -16, -11, 59, 59, "stone_k")  # cap
        box(c - 2, c + 3, -17, -10, 47, 47, "stone_k"); box(c, c + 1, -14, -13, 46, 46, "stone_k")     # base and drop
    # --- the great portal, three mouldings, a lit hall, two open leaves and a red runner ---
    ring(59.5, 38, 17, 20, -1, "stone_l", 0, 80); ring(59.5, 38, 20, 23, -2, "stone_m", 0, 80)
    door = pointed(59.5, 38, 17)
    for x in range(W):
        for z in range(0, 70):
            if door(x, z):
                rm(x, x, 0, 13, z, z)
    inner = pointed(59.5, 38, 15.4)
    for x in range(W):
        for z in range(0, 70):
            if door(x, z) and not inner(x, z):
                vox[(x, 0, z)] = GOLD
    box(36, 83, 14, 19, 0, 66, "wood_d")
    for zl in (1, 9, 17, 25, 33, 41, 49, 57):
        box(36, 83, 11, 14, zl, zl, "wood_l")
        x = 37
        while x < 82:
            w, h = rnd.choice((1, 2, 2, 3)), rnd.randint(5, 7)
            box(x, x + w - 1, 11, 13, zl + 1, zl + h, rnd.choice(BOOKS)); x += w
    box(40, 79, 0, 13, 0, 0, lambda x, y, z: "wood_m" if (x // 4 + y // 4) % 2 else "wood_d")
    box(58, 61, 5, 8, 44, 62, "rubber"); box(52, 67, 3, 10, 40, 42, "steel_d"); box(53, 66, 4, 9, 38, 39, "lamp_w")
    box(44, 75, -12, -1, 0, 0, "red_b")
    for lx in (41, 76):
        box(lx, lx + 1, -17, -1, 1, 40, "wood_d")
        for zz in (10, 22, 34):
            box(lx, lx + 1, -17, -1, zz, zz + 1, "steel_d")
        box(lx, lx + 1, -16, -15, 18, 22, "lamp_w")
    for lx in (30, 87):
        box(lx, lx + 2, -4, -3, 28, 36, "lamp_w"); box(lx + 1, lx + 1, -3, -3, 37, 44, "steel_d")
    # --- lit lancets either side of the portal, with hood mouldings; the book wall behind them ---
    for gx in (24, 95):
        ring(gx, 40, 5, 7.5, -1, "stone_l", 8, 70)
        lan = pointed(gx, 40, 5)
        for x in range(W):
            for z in range(10, 60):
                if lan(x, z):
                    rm(x, x, 0, 13, z, z)
        for x in range(W):
            for z in range(10, 60):
                if lan(x, z) and not pointed(gx, 40, 3.6)(x, z):
                    vox[(x, 0, z)] = GOLD
    box(14, 35, 14, 19, 0, 66, "wood_d"); box(84, 105, 14, 19, 0, 66, "wood_d")
    for zl in (1, 9, 17, 25, 33, 41, 49, 57):
        for x0, x1 in ((14, 35), (84, 105)):
            box(x0, x1, 11, 14, zl, zl, "wood_l")
            x = x0 + 1
            while x < x1 - 1:
                w, h = rnd.choice((1, 2, 2, 3)), rnd.randint(5, 7)
                box(x, x + w - 1, 11, 13, zl + 1, zl + h, rnd.choice(BOOKS)); x += w
    box(14, 35, 0, 13, 0, 0, "wood_m"); box(84, 105, 0, 13, 0, 0, "wood_m")
    box(14, 105, -2, 0, 66, 69, "stone_l")                                       # string course
    # --- a band of quatrefoils either side of the portal's mouldings ---
    for qx in (17, 26, 35, 84, 93, 102):
        for x in range(qx - 4, qx + 5):
            for z in range(71, 80):
                d2 = (x - qx) ** 2 + (z - 75) ** 2
                if d2 <= 16:
                    vox[(x, -1, z)] = "stone_l" if d2 >= 8 else "stone_k"
    # --- plaque and the huge stained-glass window with three mouldings ---
    box(34, 85, -1, 0, 80, 88, "sign_bg"); text("LIBRARY", 39, -2, 87, GOLD)
    ring(59.5, 114, 24, 27, -1, "stone_l", 90, 170); ring(59.5, 114, 27, 29.5, -2, "stone_m", 90, 170)
    glazed(59.5, 114, 24, 92, 160, bars_x=8, bars_z=(108, 124, 140, 150), depth=4)
    # --- two-light tracery windows with quatrefoil heads, either side ---
    for c2, (xa, xb) in ((22.5, (18, 27)), (96.5, (92, 101))):
        ring(c2, 124, 10, 12.5, -1, "stone_l", 94, 160)
        for xc in (xa, xb):
            glazed(xc, 118, 4, 96, 150, bars_x=4, bars_z=(110,), depth=3)
        for x in range(int(c2) - 6, int(c2) + 7):
            for z in range(130, 148):
                d2 = (x - c2) ** 2 + (z - 138) ** 2
                if d2 <= 25:
                    rm(x, x, 0, 2, z, z); vox[(x, 3, z)] = GLASS[(x + z) % len(GLASS)] if d2 < 17 else GOLD
    # --- the gable: a rose window with a moulding, two lancets either side ---
    rr = 9
    for x in range(W):
        for z in range(160, 195):
            d2 = (x - 59.5) ** 2 + (z - 176) ** 2
            if d2 <= (rr + 2.5) ** 2 and d2 > rr * rr:
                vox[(x, -1, z)] = "stone_l"
    for x in range(W):
        for z in range(160, 195):
            d2 = (x - 59.5) ** 2 + (z - 176) ** 2
            if d2 <= rr * rr:
                rm(x, x, 0, 2, z, z)
                ring_ = d2 >= (rr - 1.8) ** 2
                spoke = abs(x - 59.5) < 1 or abs(z - 176) < 1 or abs((x - 59.5) - (z - 176)) < 1.3 or abs((x - 59.5) + (z - 176)) < 1.3
                vox[(x, 3, z)] = "stone_m" if (ring_ or spoke) else GLASS[(x + z) % len(GLASS)]
                if d2 >= (rr - 0.6) ** 2:
                    vox[(x, 0, z)] = GOLD
    for gx2 in (38, 81):
        glazed(gx2, 166, 3, 160, 182, bars_x=None, bars_z=(172,), depth=3)
    # --- niches with statues in the taller gable: a pair above the rose, a pair low on the slopes, and two flanking the finial ---
    def niche(xc, z0, h, w=2):
        for z in range(z0, z0 + h):
            hw = w if z < z0 + h - 4 else max(0, w - (z - (z0 + h - 5)))
            rm(xc - hw, xc + hw, 0, 1, z, z)
            vox[(xc - hw - 1, -1, z)] = vox[(xc + hw + 1, -1, z)] = "stone_l"
            vox[(xc - hw, 2, z)] = vox[(xc + hw, 2, z)] = "stone_k"
        box(xc - 1, xc, 1, 2, z0 + 1, z0 + 6, "stone_l"); box(xc - 1, xc, 1, 2, z0 + 7, z0 + 8, "stone_l")   # a statue and its head
        vox[(xc, -1, z0 + h)] = vox[(xc - 1, -1, z0 + h)] = "stone_l"; vox[(xc, -1, z0 + h + 1)] = "neon_org"
    for nx in (50, 69):
        niche(nx, 187, 11, 2)
    for nx in (26, 93, 45, 74):
        niche(nx, 160, 9, 2)
    # --- the visible left end wall: two lancets ---
    for yy0 in (8, 24):
        end = pointed(yy0 + 4, 104, 4)
        for y in range(0, 40):
            for z in range(70, 140):
                if end(y, z):
                    vox[(0, y, z)] = "stone_m" if y % 4 == 0 else GLASS[(y + z) % len(GLASS)]
    return W, D


def konbini():
    """The mart (`mart`) as a Japanese-style convenience store, concept approved 2026-11-04: a bright white-lit interior, a striped
    blue/white/green fascia, a magazine rack in the window, a lit hot-food warmer, drinks fridges, a pole sign with 24H, a recycling bin."""
    W, D, rnd = 120, 48, random.Random(41)
    PRODUCTS = ("can_r", "can_b", "can_y", "can_g", "snack_o", "box_c", "white", "red_b")
    shell(W, D, "mart_blue", ("tile_a", "white"))
    box(0, W - 1, -2, -1, 40, 42, "awn_g"); box(0, W - 1, -2, -1, 43, 45, "white"); box(0, W - 1, -2, -1, 46, 49, "mart_blue")
    for x in range(4, W - 4):
        vox[(x, 2, 39)] = "fluor"
    shop_kanji = (("....#....."), (".#########"), (".#...#...."), (".#...#####"), (".#...#...."),
                  (".#..#####."), (".#..#...#."), (".#..#####."), ("#........."))
    box(8, 25, -5, -3, 41, 53, "neon_pink"); box(9, 24, -5, -4, 42, 52, "sign_bg")     # kanji light box, pink frame, proud of the band
    for r, row in enumerate(shop_kanji):
        for c, v in enumerate(row):
            if v == "#":
                vox[(12 + c, -5, 50 - r)] = "screen_b"
    for z in (43, 51):
        box(10, 11, -5, -5, z, z, "screen_b"); box(22, 23, -5, -5, z, z, "screen_b")
    box(34, 66, -4, -3, 42, 51, "white"); box(35, 65, -5, -4, 43, 50, "sign_bg")         # 24H plate: dark board, green edge ticks, white digits
    for x in range(35, 66, 4):
        box(x, x + 1, -5, -5, 43, 43, "neon_grn"); box(x, x + 1, -5, -5, 50, 50, "neon_grn")
    text("MART", 38, -6, 49, "white")                                              # MART, not 24H: the pole sign already says 24H
    for y in (10, 20, 32):
        box(8, W - 9, y, y, 45, 45, "fluor")                                    # ceiling light strips, bright
    for x in (24, 44, 64, 84, 104):
        box(x, x, 0, 0, 1, 38, "steel_d")
    box(4, W - 5, 0, 0, 36, 36, "steel_d"); box(86, 102, 1, 6, 0, 0, "rubber")
    box(6, 30, 3, 7, 1, 13, "white"); box(6, 30, 3, 3, 8, 9, "mart_blue"); box(5, 31, 2, 7, 14, 14, "steel")      # till counter
    box(9, 14, 4, 6, 15, 18, "desk"); screen(10, 13, 4, 16, 17, "screen_g", rnd)
    box(17, 29, 3, 6, 15, 21, "steel"); box(18, 28, 3, 3, 16, 20, "lamp_w")                                    # hot-food warmer, lit
    for x in (19, 22, 25):
        box(x, x, 3, 3, 17, 19, "broth")
    for x0, x1 in ((36, 62), (66, 82)):                                         # gondola shelves
        box(x0, x1, 10, 13, 1, 17, "steel_d")
        for zl in (1, 6, 11):
            box(x0, x1, 9, 9, zl, zl, "white")
            for x in range(x0, x1 + 1, 2):
                box(x, min(x + 1, x1), 9, 9, zl + 1, zl + rnd.randint(2, 4), rnd.choice(PRODUCTS))
        for x in range(x0, x1 + 1, 3):
            box(x, min(x + 2, x1), 10 + rnd.randint(0, 2), 12, 18, 17 + rnd.randint(1, 3), rnd.choice(PRODUCTS))
    box(8, 115, 20, 23, 1, 37, "steel")                                         # drinks fridges along the back wall
    for x0 in range(9, 114, 12):
        for x in range(x0 + 1, x0 + 11):
            for z in range(2, 35):
                vox[(x, 20, z)] = "steel" if z % 6 == 1 else (rnd.choice(PRODUCTS[:5]) if x % 2 == 0 and z % 6 in (2, 3, 4) else "fridge")
        box(x0 + 9, x0 + 9, 19, 19, 16, 22, "steel_d")
    box(8, 115, 19, 19, 35, 37, "mart_blue")
    box(107, 116, 2, 5, 1, 34, "steel_d")                                       # magazine rack in the right window
    for r in range(4):
        for c in range(3):
            box(108 + c * 3, 110 + c * 3, 1, 1, 5 + r * 7, 10 + r * 7, rnd.choice(("fl_p", "can_y", "can_b", "fl_r", "fl_o", "can_g", "white")))
            box(108 + c * 3, 110 + c * 3, 1, 1, 10 + r * 7, 10 + r * 7, "white")
    box(6, 12, -6, -2, 0, 11, "can_g"); box(5, 13, -7, -1, 12, 12, "rubber")    # recycling bin
    box(100, 101, -10, -9, 0, 74, "steel_d"); box(112, 113, -10, -9, 0, 74, "steel_d")       # pole sign on the sidewalk
    box(100, 113, -10, -9, 48, 74, "mart_blue"); box(100, 113, -11, -11, 74, 74, "awn_g"); box(100, 113, -11, -11, 73, 73, "white")
    for i, ch in enumerate("24H"):                                              # 24H stacked, white on the blue box
        for rr, row in enumerate(FONT[ch]):
            for cc, v in enumerate(row):
                if v == "#":
                    vox[(104 + cc, -11, 71 - i * 8 - rr)] = "white"
    return W, D


def big_dish():
    """The fleet uplink (`fleet`), a big painted dish on the florist stack's roof (2026-11-05, from Andres's reference), drawn directly
    in 0.1 m voxels (the main loop builds it with R.V = 0.1) to match the pack's chunky look: a slate-blue stepped base with pipes and a
    hazard band, a tilted segmented bowl 2.4 m across (radial ribs, three tone rings, a cyan rim ring), three white struts to a hazard-
    striped feed head, a central horn and two antenna whips with a red beacon. A roof plate keeps the footprint centred on the base."""
    R, f, el = 12, 7.0, math.radians(42)
    ph = math.radians(30)                                                         # turned 30 degrees from the main street toward the camera so the bowl shows
    n = (math.sin(ph) * math.cos(el), -math.cos(ph) * math.cos(el), math.sin(el))  # axis: up and toward the street
    e1 = (math.cos(ph), math.sin(ph), 0.0)                                        # perpendicular to the axis, level
    e2 = (n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2], n[0] * e1[1] - n[1] * e1[0])
    V0 = (0, 0, 17)
    ur = R * R / (4 * f)
    F = tuple(V0[k] + n[k] * f for k in range(3))

    def blob(p, r, col):
        px, py, pz = (round(v) for v in p)
        for x in range(px - r, px + r + 1):
            for y in range(py - r, py + r + 1):
                for z in range(pz - r, pz + r + 1):
                    if (x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2 <= r * r + 0.5:
                        vox[(x, y, z)] = col

    def line(p0, p1, r, col):
        d = math.dist(p0, p1)
        for i in range(int(d * 2) + 1):
            t = i / max(int(d * 2), 1)
            blob([p0[k] + (p1[k] - p0[k]) * t for k in range(3)], r, col)

    box(-10, 9, -10, 9, 0, 0, "roof_b")
    cyl(0, 0, 7, 1, 2, "steel_d"); cyl(0, 0, 6, 3, 9, "dish_b")
    cyl(0, 0, 4, 4, 4, "rubber"); cyl(0, 0, 6, 5, 5, "yel_b")                    # hazard band
    cyl(0, 0, 7, 10, 11, "steel_d"); cyl(0, 0, 5, 12, 14, "dish_t")
    box(7, 8, -1, 0, 1, 9, "pvc"); box(7, 10, -1, 0, 9, 9, "pvc"); box(10, 11, -1, 0, 2, 9, "pvc"); box(11, 13, -1, 1, 1, 2, "steel_d")   # side pipes
    line((0, 0, 14), (V0[0] - n[0] * 2, V0[1] - n[1] * 2, V0[2] - n[2] * 2), 1, "dish_t")                  # yoke to the dish back
    for x in range(-16, 17):                                                     # the bowl
        for y in range(-20, 14):
            for z in range(8, 42):
                dx, dy, dz = x - V0[0], y - V0[1], z - V0[2]
                a = dx * n[0] + dy * n[1] + dz * n[2]
                r2 = dx * dx + dy * dy + dz * dz - a * a
                if r2 > R * R:
                    continue
                r, u = r2 ** 0.5, r2 / (4 * f)
                if -1.2 <= a - u <= 0.5 + 0.4 * r / (2 * f) * 2:                 # a layer about one block thick, thicker on the steep outer slope
                    ang = math.atan2(dx * e2[0] + dy * e2[1] + dz * e2[2], dx * e1[0] + dy * e1[1] + dz * e1[2])
                    sector = int((ang + math.pi) / (math.pi / 4)) % 8
                    edge = abs(((ang + math.pi) % (math.pi / 4)) - math.pi / 8) > math.pi / 8 - 0.12
                    if r > R - 1.2:
                        vox[(x, y, z)] = "neon_cyan" if sector % 2 == 0 else "dish_l"          # rim ring, lit in alternating segments
                    elif r > 3 and edge:
                        vox[(x, y, z)] = "steel_d"                                              # rib lines between panels
                    else:
                        vox[(x, y, z)] = "dish_b" if r < 4 else ("dish_t" if r < 8 else "dish_l")
                elif r < 3.5 and u - 2.5 <= a < u - 1.2:
                    vox[(x, y, z)] = "steel_d"                                   # rear hub
    for th in (0.5, 0.5 + 2.094, 0.5 + 4.189):                                   # three white struts from the rim to the feed head
        P_ = tuple(V0[k] + n[k] * ur + (R - 0.5) * (math.cos(th) * e1[k] + math.sin(th) * e2[k]) for k in range(3))
        line(P_, F, 0, "white")
    line(V0, tuple(V0[k] + n[k] * 3 for k in range(3)), 1, "steel_d")             # central horn
    blob(tuple(V0[k] + n[k] * 2 for k in range(3)), 1, "yel_b")
    blob(F, 1, "steel_d"); blob(tuple(F[k] + n[k] * 1.5 for k in range(3)), 1, "yel_b")
    for off, ln in ((0.0, 8), (2.0, 4)):                                          # two antenna whips from the feed head
        a0 = tuple(F[k] + n[k] * 2 + e1[k] * off for k in range(3))
        a1 = tuple(a0[k] + n[k] * ln for k in range(3))
        line(a0, a1, 0, "steel")
        blob(a1, 1, "red_glow")
    return 20, 20                                                                 # built with R.V = 0.1 in the main loop


def netcafe_sign():
    """NET CAFE as a tall vertical blade (2026-11-05): a monitor icon, then NET and CAFE stacked letter by letter, electric blue on a dark
    board with a violet frame and violet bars between the words; 0.7 m x 3.7 m, for the corner script's blade()."""
    W, H = 14, 74
    box(0, W - 1, 0, 1, 0, H - 1, "sign_bg")
    for z in range(H):
        vox[(0, -1, z)] = vox[(W - 1, -1, z)] = "neon_vio"
    for x in range(W):
        vox[(x, -1, 0)] = vox[(x, -1, H - 1)] = "neon_vio"
    for x in range(3, 11):                                                        # monitor icon, 8 x 6
        for z in range(H - 9, H - 3):
            vox[(x, -1, z)] = "neon_vio" if x in (3, 10) or z in (H - 9, H - 4) else "board"
    vox[(6, -1, H - 10)] = vox[(7, -1, H - 10)] = "neon_vio"
    zt = H - 13
    for word in ("NET", "CAFE"):
        for ch in word:
            for r, row in enumerate(FONT[ch]):
                for c, v in enumerate(row):
                    if v == "#":
                        vox[(4 + c, -1, zt - r)] = "neon_blue"
            zt -= 8
        if word == "NET":
            box(2, W - 3, -1, -1, zt + 3, zt + 3, "neon_vio"); zt -= 3
    return W, 2


TOWER_WORDS = ("HOTEL", "BAR", "CLUB", "DISCO", "SHOP", "PHARMA", "CAFE", "TECH", "PUB", "24H")
TOWER_GLOW = ("neon_pink", "neon_cyan", "neon_yel", "neon_org", "neon_blue", "neon_grn")
TOWER_WIN = ("win_p", "win_c", "win_a", "win_c", "win_p")


def sky_tower(W, D, floors, seed, walls):
    """A city tower in the style of the monogon street reference (2026-11-05): floors of dark slit windows with random pink, cyan and amber
    lit panes, ledges, AC units and balcony rails, lit name signs, a glowing corner strip and a roof with an antenna and red beacon. Only the
    two faces the camera sees are built (front y 0 to 1 and right x W-2 to W-1), so it is a shell, not a solid; 50 voxels per floor."""
    rnd = random.Random(seed)
    FH, H = 50, floors * 50
    for f in range(floors):
        z0, wc = f * FH, walls[f % len(walls)]
        box(0, W - 1, 0, 1, z0, z0 + FH - 1, wc); box(W - 2, W - 1, 0, D - 1, z0, z0 + FH - 1, wc)
        box(0, W - 1, -2, -1, z0, z0 + 1, "steel_d"); box(W, W + 1, 0, D - 1, z0, z0 + 1, "steel_d")          # ledges
        for wx in range(6, W - 14, 20):                                                                       # front windows
            lit = rnd.random() < 0.75
            box(wx - 1, wx + 12, -1, -1, z0 + 19, z0 + 36, "board")
            box(wx, wx + 11, -1, -1, z0 + 21, z0 + 34, rnd.choice(TOWER_WIN) if lit else "board")
            if lit:
                box(wx + 5, wx + 6, -1, -1, z0 + 21, z0 + 34, "board")
        for wy in range(4, D - 12, 18):                                                                       # right-face windows
            lit = rnd.random() < 0.75
            box(W, W, wy - 1, wy + 11, z0 + 19, z0 + 36, "board")
            box(W, W, wy, wy + 10, z0 + 21, z0 + 34, rnd.choice(TOWER_WIN) if lit else "board")
        if rnd.random() < 0.5:                                                                                # AC unit
            ax = rnd.randint(4, W - 20)
            box(ax, ax + 9, -4, -1, z0 + 6, z0 + 14, "steel"); box(ax + 2, ax + 7, -4, -4, z0 + 8, z0 + 12, "steel_d")
        if rnd.random() < 0.35:                                                                               # balcony rail
            bx = rnd.randint(4, W - 30)
            box(bx, bx + 24, -5, -5, z0 + 9, z0 + 9, "steel"); box(bx, bx + 24, -5, -5, z0 + 4, z0 + 4, "steel_d")
            for px in range(bx, bx + 25, 8):
                box(px, px, -5, -5, z0 + 2, z0 + 9, "steel_d")
    for _ in range(max(2, floors // 2)):                                                                     # lit name signs
        word = rnd.choice(TOWER_WORDS)
        col = rnd.choice(TOWER_GLOW)
        wd = len(word) * 6
        x0 = rnd.randint(5, max(5, W - wd - 8))
        zt = rnd.randrange(1, floors) * FH - 12
        box(x0 - 2, x0 + wd + 1, -4, -3, zt - 9, zt + 2, "sign_bg")
        for x in range(x0 - 2, x0 + wd + 2):
            vox[(x, -5, zt + 2)] = vox[(x, -5, zt - 9)] = col
        text(word, x0, -5, zt, col)
    for z in range(30, H - 30):                                                                              # glowing corner strip in broken segments
        if (z // 22) % 2 == 0:
            vox[(W - 3, -2, z)] = vox[(W - 4, -2, z)] = TOWER_GLOW[seed % len(TOWER_GLOW)]
    box(0, W - 1, 0, D - 1, H, H + 1, "steel_d")                                                             # roof slab, parapet, kit on the roof, antenna
    box(0, W - 1, 0, 1, H + 2, H + 4, "steel_d"); box(W - 2, W - 1, 0, D - 1, H + 2, H + 4, "steel_d")
    box(W // 2 - 10, W // 2 + 10, 8, 26, H + 2, H + 12, "steel_d"); box(W // 2 - 10, W // 2 - 8, 8, 26, H + 13, H + 14, "steel")
    ax = W // 3
    box(ax, ax + 1, 4, 5, H + 2, H + 34, "steel"); box(ax - 1, ax + 2, 3, 6, H + 35, H + 37, "red_glow")
    return W, D


def hung_box(word, col):
    """A hung neon box for the side street (2026-11-05): a framed glowing word on a dark plate with two cables going up, for put(..., yaw=1)."""
    W, H = len(word) * 6 + 6, 14
    box(0, W - 1, 0, 2, 0, H - 1, "sign_bg")
    for x in range(W):
        vox[(x, -1, 0)] = vox[(x, -1, H - 1)] = col
    for z in range(H):
        vox[(0, -1, z)] = vox[(W - 1, -1, z)] = col
    text(word, 3, -1, H - 4, col)
    box(2, 2, 1, 1, H, H + 18, "steel_d"); box(W - 3, W - 3, 1, 1, H, H + 18, "steel_d")
    return W, 3


def karaoke():
    """A karaoke bar floor (2026-11-05) over the florist, in place of the pack block at 5 m: 6 m wide, 2 m deep, open to the side street.
    A stage (its singer is a Person_* placed by the corner script), a lyric screen on the back wall, a pink sofa and table, a disco ball, a KARAOKE marquee with
    chase lights, a 1 m deck with a rail, and a steel stair from the florist balcony's left end up 2.5 m to the deck (the second leg of
    a zig-zag with the street stair). Local z 0 is the karaoke floor."""
    rnd = random.Random(71)
    box(0, 119, 0, 39, 0, 1, "conc_d"); box(0, 119, 0, 39, 48, 49, "conc_d")
    box(0, 3, 0, 39, 0, 49, "conc"); box(116, 119, 0, 39, 0, 49, "conc")
    box(4, 115, 38, 39, 2, 47, lambda x, y, z: "vio_panel" if (x // 6 + z // 6) % 2 else "chair_k")           # padded back wall
    box(4, 115, 2, 37, 2, 2, lambda x, y, z: "chair_r" if (x // 4 + y // 4) % 2 else "vio_panel")              # carpet
    box(38, 82, 37, 37, 12, 42, "steel_d"); box(40, 80, 36, 36, 14, 40, "screen_b")                            # lyric screen
    for z, c, a, b in ((34, "neon_pink", 44, 76), (29, "white", 48, 72), (24, "neon_yel", 46, 74), (19, "white", 50, 70)):
        box(a, b, 35, 35, z, z + 1, c)
    box(6, 30, 20, 37, 3, 6, "wood_d"); box(6, 30, 19, 19, 3, 6, "neon_pink")                                 # stage (the singer is Person_Singer, placed by the corner script)
    box(86, 112, 26, 36, 3, 10, "chair_r"); box(86, 112, 33, 36, 11, 20, "chair_r")                          # sofa, table, drinks
    box(92, 106, 14, 20, 3, 8, "desk")
    for x, c in ((94, "neon_cyan"), (98, "neon_pink"), (103, "neon_yel")):
        box(x, x + 1, 16, 17, 9, 11, c)
    for dx in range(-3, 4):                                                                                    # disco ball on a cord
        for dy in range(-3, 4):
            for dz in range(-3, 4):
                if dx * dx + dy * dy + dz * dz <= 10:
                    vox[(60 + dx, 18 + dy, 40 + dz)] = "white" if (dx + dy + dz) % 2 else "steel"
    box(60, 60, 18, 18, 44, 47, "steel_d")
    for x in range(4, 116):
        vox[(x, 3, 46)] = "neon_pink" if x % 4 else "neon_vio"                                                 # ceiling strip
    box(0, 119, -2, -1, 38, 49, "sign_bg")                                                                    # marquee with chase lights
    for x in range(0, 120, 3):
        vox[(x, -3, 38)] = vox[(x, -3, 49)] = "neon_yel" if (x // 3) % 2 else "white"
    text("KARAOKE", 39, -3, 47, "neon_pink")
    box(0, 119, -20, -1, 0, 1, "steel_d")                                                                     # deck and rail
    box(0, 43, -20, -20, 12, 12, "steel"); box(58, 119, -20, -20, 12, 12, "steel")
    for x in list(range(0, 44, 8)) + list(range(58, 120, 8)):
        box(x, x, -20, -20, 2, 11, "steel_d")
    for x in range(0, 120):
        vox[(x, -21, 1)] = "neon_pink"
    # zig-zag (2026-11-05): the street stair climbs left to the florist balcony's right-end landing; you walk the balcony to its
    # left end, and this flight climbs back to the right, just outside the balcony edge, to the karaoke deck (foot at local x 0 to 8,
    # balcony level z -50; head at x 46 to 57, deck level z 0)
    box(0, 8, -33, -21, -51, -50, "steel")
    for k in range(9):                                                                                         # nine even 0.25 m risers
        x0, zt = 8 + 4 * k, -50 + 5 * (k + 1)
        box(x0, x0 + 3, -33, -22, zt - 1, zt, "steel")
        vox[(x0 + 3, -33, zt)] = vox[(x0 + 3, -22, zt)] = "neon_yel"
    box(44, 57, -33, -21, -1, 0, "steel")
    for x in range(0, 58):
        zl = -50 if x < 8 else (0 if x >= 44 else -50 + (x - 8) * 50 // 36)
        box(x, x, -34, -34, zl - 3, zl, "steel_d"); vox[(x, -34, zl + 12)] = "steel"
        if x % 8 == 0:
            box(x, x, -34, -34, zl + 1, zl + 11, "steel_d")
    return 120, 40


def kowloon():
    """Kowloon-style apartments on the mart's 2nd and 3rd floors (2026-11-05): 6 m wide, 5 m tall, a patchwork wall with mismatched
    windows behind security-grille cages, plants and junk in the cages, AC units everywhere, bamboo laundry poles with clothes, tangled
    cables, small dishes on the cages, drain pipes, neon scraps, a hazard-striped fuse box and a green ROOMS blade on the right edge.
    Only the front and right faces are built (a shell). Local y 0 is the wall line, street at -y."""
    rnd = random.Random(57)
    W, D, H = 120, 48, 100
    WALLS = ("tw_a", "tw_b", "tw_c", "conc", "conc_d")
    for x0 in range(0, W, 24):                                                                                 # patchwork wall panels
        for z0 in range(0, H, 25):
            box(x0, min(x0 + 23, W - 1), 0, 1, z0, z0 + 24, rnd.choice(WALLS))
    box(W - 2, W - 1, 0, D - 1, 0, H - 1, "tw_a"); box(0, W - 1, 0, D - 1, H - 2, H - 1, "steel_d")
    for z in (0, 49):
        box(0, W - 1, -2, -1, z, z + 1, "steel_d")                                                            # floor ledges
    LIT = ("win_a", "win_a", "win_c", "win_p", "lamp_w", "board", "chair_r", "screen_g")
    CLOTH = ("red_b", "yel_b", "can_b", "white", "fl_p", "awn_g", "fl_o")
    for f in range(2):
        z0 = f * 50
        for b in range(4):
            x0 = 4 + b * 29 + rnd.randint(-2, 2)
            ww, wh = rnd.choice(((22, 22), (18, 26), (24, 18), (20, 20)))
            zb = z0 + rnd.randint(10, 16)
            col = rnd.choice(LIT)
            box(x0 - 1, x0 + ww, -1, -1, zb - 1, zb + wh, "board"); box(x0, x0 + ww - 1, -1, -1, zb, zb + wh - 1, col)
            if col not in ("board", "chair_r"):
                box(x0 + ww // 2, x0 + ww // 2, -1, -1, zb, zb + wh - 1, "board")                              # mullion
            dep = rnd.choice((6, 8, 10))                                                                       # the grille cage
            box(x0 - 2, x0 + ww + 1, -dep, -2, zb - 2, zb - 2, "steel_d"); box(x0 - 2, x0 + ww + 1, -dep, -2, zb + wh + 1, zb + wh + 2, "copper" if rnd.random() < 0.4 else "steel_d")
            for x in range(x0 - 2, x0 + ww + 2, 3):
                box(x, x, -dep, -dep, zb - 1, zb + wh, "steel")
            for z in range(zb + 4, zb + wh, 7):
                box(x0 - 2, x0 + ww + 1, -dep, -dep, z, z, "steel")
            for _ in range(rnd.randint(1, 3)):                                                                 # plants and junk in the cage
                px = rnd.randint(x0, x0 + ww - 4)
                if rnd.random() < 0.6:
                    box(px, px + 3, -dep + 2, -3, zb - 1, zb + 1, "terra"); box(px, px + 3, -dep + 2, -3, zb + 2, zb + rnd.randint(4, 8), rnd.choice(("leaf_m", "leaf_l", "leaf_d")))
                else:
                    box(px, px + 4, -dep + 2, -3, zb - 1, zb + rnd.randint(2, 5), rnd.choice(("box_c", "can_b", "steel")))
            if rnd.random() < 0.5:                                                                             # small dish on the cage roof
                box(x0 + 2, x0 + 3, -dep + 2, -dep + 3, zb + wh + 3, zb + wh + 5, "steel_d"); box(x0, x0 + 5, -dep + 1, -dep + 1, zb + wh + 5, zb + wh + 9, "pvc")
            for _ in range(rnd.randint(1, 2)):                                                                 # AC units under and beside the cage
                ax = rnd.choice((x0 - 10, x0 + ww + 3, x0 + rnd.randint(0, ww - 9)))
                az = zb - 10 if ax in range(x0, x0 + ww) else zb + rnd.randint(0, wh - 8)
                if 0 <= ax <= W - 12:
                    box(ax, ax + 8, -5, -1, az, az + 6, "steel"); box(ax + 1, ax + 7, -5, -5, az + 1, az + 5, "steel_d")
                    vox[(ax + 4, -6, az + 3)] = "steel"
            if rnd.random() < 0.7:                                                                             # bamboo laundry pole with clothes
                px, pz = x0 + rnd.randint(2, ww - 3), zb + wh + 1
                box(px, px, -dep - 12, -dep, pz, pz, "wood_l")
                for gy in range(-dep - 11, -dep - 1, 4):
                    if rnd.random() < 0.8:
                        gw = rnd.choice((2, 3))
                        box(px - 1, px + 1, gy, gy + gw - 1, pz - rnd.randint(4, 8), pz - 1, rnd.choice(CLOTH))
    for k in range(5):                                                                                         # tangled sagging cables
        xa, xb, za, zb2 = rnd.randint(0, 40), rnd.randint(70, 119), rnd.randint(20, 95), rnd.randint(20, 95)
        for x in range(xa, xb):
            t = (x - xa) / max(xb - xa, 1)
            vox[(x, -3 - (k % 3), int(za + (zb2 - za) * t - 6 * math.sin(math.pi * t)))] = "rubber"
    box(2, 3, -3, -2, 0, H - 3, "steel_d"); box(56, 57, -3, -2, 0, H - 3, "steel_d")                          # drain pipes
    box(60, 70, -3, -1, 6, 14, lambda x, y, z: "yel_b" if (x + z) % 4 < 2 else "rubber")                       # fuse box, hazard stripes
    for nx, nz, c in ((10, 44, "neon_pink"), (40, 92, "neon_cyan"), (88, 46, "neon_grn"), (72, 90, "neon_yel")):   # neon scraps
        box(nx, nx + 8, -2, -2, nz, nz, c); box(nx + 2, nx + 2, -2, -2, nz - 4, nz, c)
    box(110, 119, -16, -14, 40, 92, "sign_bg")                     # ROOMS blade on the right edge (its blank lower 1.6 m hid the mart's 24H pole sign, cut 2026-11-05)
    for z in range(40, 93):
        vox[(110, -17, z)] = vox[(119, -17, z)] = "neon_grn"
    for i, ch in enumerate("ROOMS"):
        for rr, row in enumerate(FONT[ch]):
            for cc, v in enumerate(row):
                if v == "#":
                    vox[(112 + cc, -17, 86 - i * 9 - rr)] = "neon_grn"
    return W, D


def izakaya():
    """An izakaya on the mart building's top floor (2026-11-05): dark wood front with lit shoji screens, a noren over the door, a wooden
    balcony with a rail and a row of red paper lanterns under a black tiled eave, a red-lettered IZAKAYA board on the eave and a smoking
    vent on the roof (the steam is placed by the corner script). 6 m wide, 2.5 m tall. Local y 0 is the wall line, street at -y."""
    W, D = 120, 40
    box(0, W - 1, 0, 1, 0, 49, "wood_d"); box(W - 2, W - 1, 0, D - 1, 0, 49, "wood_d"); box(0, W - 1, 0, D - 1, 48, 49, "steel_d")
    for x0 in range(6, W - 20, 22):                                                                           # shoji screens
        box(x0, x0 + 17, -1, -1, 8, 38, "lamp_w")
        for x in range(x0, x0 + 18, 6):
            box(x, x, -1, -1, 8, 38, "wood_m")
        for z in range(8, 39, 6):
            box(x0, x0 + 17, -1, -1, z, z, "wood_m")
    for x in range(96, 112, 4):                                                                               # noren over the door
        box(x, x + 2, -2, -2, 26, 38, "red_b" if x % 8 else "indigo")
    box(0, W - 1, -10, -1, 0, 1, "wood_m")                                                                    # balcony and rail
    box(0, W - 1, -10, -10, 10, 11, "wood_l")
    for x in range(0, W, 10):
        box(x, x + 1, -10, -10, 2, 9, "wood_d")
    for k in range(4):                                                                                        # black tiled eave, stepped
        box(-2, W + 1, -12 + k * 3, -1, 42 + k * 2, 43 + k * 2, "rubber" if k % 2 else "steel_d")
    for x in range(-2, W + 2, 3):
        vox[(x, -13, 42)] = "steel_d"
    for x in range(8, W - 4, 14):                                                                             # red paper lanterns
        box(x, x, -8, -8, 33, 41, "rubber")
        box(x - 2, x + 2, -10, -6, 25, 32, "lantern"); box(x - 2, x + 2, -10, -6, 24, 24, "rubber"); box(x - 2, x + 2, -10, -6, 33, 33, "rubber")
    box(36, 85, -14, -13, 48, 58, "wood_l"); text("IZAKAYA", 39, -15, 56, "red_glow")                     # name board on the eave
    box(105, 112, 4, 11, 50, 66, "steel_d"); box(104, 113, 3, 12, 67, 68, "steel")                            # roof vent at the right end, where its smoke shows
    return W, D


def gap_wires():
    """Power lines across the gap between the izakaya and the net cafe tower (2026-11-05): three sagging cables 4 m long with a
    string of small bulbs on the lowest and a junction box hanging from the middle one. Local x 0..79 runs along the facade."""
    BULB = ("neon_yel", "neon_pink", "neon_cyan", "lamp_w")
    for k, (z0, sag, y) in enumerate(((24, 10, 0), (20, 14, -3), (27, 7, -5))):
        for x in range(0, 80):
            t = x / 79
            z = int(z0 - sag * math.sin(math.pi * t))
            vox[(x, y, z)] = "rubber"
            if k == 1 and x % 8 == 4:
                box(x, x + 1, y - 1, y, z - 2, z - 1, BULB[(x // 8) % len(BULB)])
    box(36, 42, -4, -2, 2, 8, "steel_d"); box(37, 41, -5, -5, 4, 6, "neon_grn"); box(39, 39, -3, -3, 9, 10, "rubber")
    return 80, 6


def cat(coat, pose):
    """A street cat (2026-11-05), about 0.55 m long and 0.6 m to the ears, nose toward -y (yaw 0 is the walkers' front), green eyes
    that glow. coat 'orange' is a tabby (orange with darker stripes, white chest and paws), 'calico' is white with orange and black
    patches. pose 0 and 2 are the two trot steps (diagonal leg pairs forward), 1 is standing; 3 and 4 sit with the tail swished
    left or right (a wag when swapped), 5 sits licking a raised front paw; night_shift_motion.py swaps them."""
    def fur(x, y, z):
        if coat == "orange":
            return "terra" if y % 3 == 0 and z >= 6 else "cat_o"      # cat_o glows faintly so the lime HYDRO FLORA neon under it can't wash it pale
        k = (x // 2 + (y + 8) // 3 * 3 + z // 3 * 7) % 5
        return ("fl_o", "white", "chair_k", "white", "fl_o")[k]

    if pose >= 3:                                                                                          # sitting: haunches down, chest up
        box(-2, 2, -1, 3, 0, 5, fur); box(-2, 2, -3, 0, 5, 9, fur)
        box(-1, -1, -4, -4, 0, 5, "white"); box(1, 1, -4, -4, 0, 5 if pose != 5 else 3, "white")              # front legs
        if coat == "orange":
            box(-1, 1, -4, -4, 6, 8, "white")                                                              # chest
        if pose == 5:                                                                                      # licking: head down to a raised paw
            box(-2, 2, -6, -2, 8, 12, fur); box(1, 2, -6, -5, 6, 8, "white"); vox[(0, -7, 9)] = "fl_p"
            box(-2, -2, -4, -4, 13, 14, fur); box(2, 2, -4, -4, 13, 14, fur)
            vox[(-1, -7, 11)] = vox[(1, -7, 11)] = "neon_grn"
        else:
            box(-2, 2, -6, -2, 9, 13, fur)
            box(-2, -2, -4, -4, 14, 15, fur); box(2, 2, -4, -4, 14, 15, fur)
            vox[(-1, -7, 12)] = vox[(1, -7, 12)] = "neon_grn"; vox[(0, -7, 11)] = "fl_p"; box(-1, 1, -7, -7, 10, 10, "white")
        side = 1 if pose == 4 else -1                                                                      # tail curled round on the rail
        for tx, ty, tz in ((0, 4, 1), (1, 5, 1), (2, 5, 2), (3, 4, 3)):
            vox[(side * tx, ty, tz)] = "terra" if coat == "orange" and tx % 2 else fur(side * tx, ty, tz)
        return 5, 13

    step = {0: 1, 1: 0, 2: -1}[pose]
    for lx, ly, s in ((-2, -3, step), (2, -3, -step), (-2, 3, -step), (2, 3, step)):                      # legs, diagonal pairs move together
        box(lx, lx, ly + s, ly + s, 0, 4, "white" if coat == "orange" and ly < 0 else fur(lx, ly, 2))
        vox[(lx, ly + s, 0)] = "white" if coat == "orange" else vox[(lx, ly + s, 0)]
    box(-2, 2, -3, 4, 4, 8, fur)                                                                           # body
    if coat == "orange":
        box(-1, 1, -4, -3, 4, 7, "white")                                                                  # chest
    box(-2, 2, -7, -4, 6, 10, fur)                                                                         # head, ears
    box(-2, -2, -5, -5, 11, 12, fur); box(2, 2, -5, -5, 11, 12, fur)
    vox[(-1, -8, 9)] = vox[(1, -8, 9)] = "neon_grn"                                                         # eyes, nose, muzzle
    vox[(0, -8, 8)] = "fl_p"; box(-1, 1, -8, -8, 7, 7, "white")
    for ty, tz in ((5, 8), (6, 9), (6, 10), (7, 11), (7, 12), (8, 13)):                                   # tail, curling up
        vox[(0, ty, tz)] = "terra" if coat == "orange" and tz % 2 else fur(0, ty, tz)
    return 5, 16


def window_tall():
    """A framed lit window, 0.7 x 1.6 m, 0.1 m thick, for bare wall strips (hung with the corner script's facade())."""
    box(0, 13, 0, 1, 0, 31, "sign_bg")
    box(2, 11, 0, 0, 2, 29, "lamp_w")
    box(6, 7, 0, 0, 2, 29, "sign_bg"); box(2, 11, 0, 0, 15, 16, "sign_bg")
    box(0, 13, 0, 0, 32, 32, "neon_vio")
    return 14, 2


def plain_wall(W, H):
    """A plain concrete wall piece, W x 42 voxels deep x H tall, front on the wall line (y 0): the far tower's pier and the
    new block's ground floor (layout job 3). Things are mounted on its face by other pieces."""
    box(0, W - 1, 0, 41, 0, H - 1, "conc"); box(0, W - 1, 0, 41, H - 1, H - 1, "conc_d")
    for z in range(10, H - 1, 10):
        box(0, W - 1, 0, 0, z, z, "seam")
    for x in range(0, W, 20):
        box(x, x, 0, 0, 0, H - 2, "seam")
    return W, 42


def flyer_board():
    """The flyer wall (`pins`): a header and a board plastered with flyers, mounted on a wall (y -1 to -3, street at -y)."""
    rnd = random.Random(91)
    box(0, 35, -1, -1, 0, 43, "wood_d"); box(0, 35, -2, -2, 44, 51, "sign_bg")
    text("PINS", 6, -3, 51, "neon_yel")
    for _ in range(16):
        w, h = rnd.randint(5, 10), rnd.randint(7, 13)
        x, z = rnd.randint(1, 36 - w - 1), rnd.randint(1, 44 - h - 1)
        box(x, x + w - 1, -2, -2, z, z + h - 1, rnd.choice(("white", "fl_y", "fl_p", "fl_o", "can_b", "can_g", "fl_r", "screen_w")))
        for k in range(2, h - 2, 2):
            box(x + 1, x + w - 2 - rnd.randint(0, 2), -3, -3, z + h - 1 - k, z + h - 1 - k, "board")
        vox[(x + w // 2, -3, z + h - 1)] = "steel"                                      # a pin
    return 36, 3


def lockers():
    """The inbox lockers (`inbox`): four columns of three doors under a lit INBOX header, standing against a wall (y -10 to -1)."""
    rnd = random.Random(93)
    box(0, 35, -9, -1, 0, 39, "steel_d"); box(0, 35, -10, -1, 40, 40, "conc_d"); box(0, 35, -10, -1, 41, 48, "sign_bg")
    text("INBOX", 3, -11, 47, "neon_cyan")
    for c in range(4):
        for r in range(3):
            dx, dz = 1 + c * 9, 2 + r * 13
            box(dx, dx + 7, -10, -10, dz, dz + 11, rnd.choice(("steel", "vio_panel", "mart_blue", "chair_k", "awn_g", "steel")))
            vox[(dx + 6, -11, dz + 10)] = rnd.choice(("neon_grn", "neon_grn", "red_glow", "neon_yel"))
            vox[(dx + 6, -11, dz + 5)] = "white"; box(dx + 2, dx + 5, -11, -11, dz + 9, dz + 9, "screen_w")
    return 36, 10


def mailbox():
    """A street mailbox (`email`), 0.6 m square, 1.5 m tall, with a lit slot and an envelope icon on the front (-y)."""
    box(2, 9, 2, 9, 0, 5, "steel_d"); box(1, 10, 1, 10, 6, 24, "mart_blue"); cyl(5, 5, 5, 25, 28, "mart_blue")
    box(2, 9, 1, 1, 18, 19, "board"); box(2, 9, 1, 1, 16, 16, "neon_cyan")
    box(3, 8, 1, 1, 9, 9, "neon_cyan"); box(3, 8, 1, 1, 13, 13, "neon_cyan"); box(3, 3, 1, 1, 9, 13, "neon_cyan"); box(8, 8, 1, 1, 9, 13, "neon_cyan")
    for x, z in ((4, 12), (5, 11), (6, 11), (7, 12)):
        vox[(x, 1, z)] = "neon_cyan"
    box(10, 12, 4, 5, 18, 22, "red_b")                           # the flag
    return 12, 12


def bench():
    """A bench 1.8 m long; the back is on the street side (y 0..1), so with a quarter turn it faces the wall."""
    box(0, 35, 2, 8, 7, 8, "wood_l"); box(0, 35, 0, 1, 9, 18, "wood_m")
    for x in (1, 33):
        box(x, x + 1, 2, 8, 0, 6, "steel_d")
    return 36, 10


def roof_tank():
    cyl(0, 0, 12, 10, 36, "steel", top="steel_d")
    for z in range(10, 37, 6):
        cyl(0, 0, 12, z, z, "steel_d")
    cyl(0, 0, 9, 37, 38, "steel_d"); cyl(0, 0, 3, 39, 40, "steel")
    for x, y in ((-8, -8), (8, -8), (-8, 8), (8, 8)):
        box(x, x + 1, y, y + 1, 0, 9, "steel_d")
    box(-9, 9, -9, 9, 9, 9, "steel_d")
    for x in (-3, 2):                                                                         # caged ladder on the street side
        box(x, x, -13, -13, 0, 40, "steel")
    for z in range(2, 40, 3):
        box(-3, 2, -13, -13, z, z, "steel")
    box(6, 7, -14, -13, 0, 12, "rubber"); return 25, 27


def beacon():
    box(0, 0, 0, 0, 0, 28, "steel_d"); box(-1, 1, -1, 1, 0, 1, "steel_d"); box(-1, 0, -1, 0, 29, 30, "red_glow"); return 3, 3


def manhole():
    """Round cast-iron cover, 0.75 m across, sitting proud of the road by one voxel."""
    for x in range(-7, 8):
        for y in range(-7, 8):
            r2 = x * x + y * y
            if r2 <= 56:
                ring = r2 > 42 or 12 < r2 <= 20
                vox[(x, y, 0)] = "steel_d" if ring or (x + y) % 3 == 0 and r2 > 4 else ("steel" if (x - y) % 3 else "rubber")
    return 15, 15


def curb_drain():
    """Small slotted drain in the gutter, 0.7 x 0.3 m."""
    box(0, 13, 0, 5, 0, 0, "steel_d")
    for x in range(1, 13, 2):
        box(x, x, 1, 4, 0, 0, "rubber")
    return 14, 6


P["red_glow"] = ((1.0, 0.08, 0.06), 1.5)
P["neon_lime"] = ((0.70, 1.0, 0.10), 1.4)
P["neon_blue"] = ((0.05, 0.22, 1.0), 0.9)   # bloom turns anything stronger lavender-white
P["cat_o"] = ((0.85, 0.15, 0.01), 0.3)       # the tabby's coat: red-orange with a faint glow, since AgX and the lime sign under it push orange to yellow
P.update({"tw_a": ((0.20, 0.20, 0.32), None), "tw_b": ((0.42, 0.22, 0.20), None), "tw_c": ((0.26, 0.28, 0.40), None),
          "win_p": ((1.0, 0.30, 0.75), 2.4), "win_c": ((0.35, 1.0, 0.95), 2.4), "win_a": ((1.0, 0.75, 0.35), 2.0)})   # bright enough to glow through the haze
P.update({"dish_b": ((0.16, 0.30, 0.50), 0.25), "dish_t": ((0.30, 0.48, 0.52), 0.3), "dish_l": ((0.58, 0.70, 0.74), 0.4)})   # a soft glow so it reads against the dark tower
P.update({"stone_k": ((0.040, 0.029, 0.025), None), "stone_m": ((0.078, 0.057, 0.044), None), "stone_l": ((0.145, 0.105, 0.075), None)})
SHOPS = {"Shop_Repair": repair, "Shop_NetCafe": netcafe, "Shop_Florist": florist, "Shop_Mart": konbini, "Shop_Games": games,
         "Shop_BodyMods": bodymods, "Loft_NetCafe": loft_netcafe, "Shop_Ramen": ramen_shop, "Arcade_GameHub": arcade_floor,
         "Landing": landing, "Catwalk": catwalk, "Neon_Pole": neon_pole, "Roof_Patio": roof_patio, "Roof_Patio_Abandoned": roof_patio_abandoned,"Block_Low": block_low, "Shop_Library": cathedral, "Wall_Pier": lambda: plain_wall(40, 100), "Wall_Row": lambda: plain_wall(120, 50),
         "Roof_Dish": big_dish, "Window_Tall": window_tall, "Sign_NetCafe": netcafe_sign,
         "Tower_Net": lambda: sky_tower(120, 44, 4, 4, ("tw_c", "tw_a")), "Tower_Sky_A": lambda: sky_tower(120, 44, 8, 1, ("tw_a", "tw_b", "tw_c")),
         "Tower_Sky_B": lambda: sky_tower(120, 44, 7, 2, ("tw_b", "tw_c", "tw_a")), "Tower_Sky_C": lambda: sky_tower(120, 44, 7, 3, ("tw_c", "tw_b")),
         "Hung_ARCADE": lambda: hung_box("ARCADE", "neon_pink"), "Karaoke": karaoke, "Kowloon": kowloon, "Izakaya": izakaya, "Gap_Wires": gap_wires,
         **{f"Cat_{c.capitalize()}{p}": (lambda c=c, p=p: cat(c, p)) for c, n in (("orange", 6), ("calico", 3)) for p in range(n)}, "Flyer_Board": flyer_board, "Lockers": lockers, "Mailbox": mailbox, "Bench": bench, "Patio_Florist": patio, "Roof_Tank": roof_tank, "Beacon": beacon, "Manhole": manhole, "CurbDrain": curb_drain,
         "Plant_Palm": potted_palm, "Plant_Snake": potted_snake, "Plant_Monstera": potted_monstera, "Plant_Tree": street_tree, "Plant_TreeTall": street_tree_tall,
         "Plant_LedgeBox": ledge_box, "Plant_Hanging": hanging_basket, "Plant_Bamboo": bamboo_planter}

if __name__ == "__main__":
    kc = bpy.data.collections.get("kit_custom") or bpy.data.collections.new("kit_custom")
    if kc.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(kc)
    for name, draw in SHOPS.items():
        old = bpy.data.collections.get(name)
        if old:
            for o in list(old.objects): bpy.data.objects.remove(o)
            bpy.data.collections.remove(old)
        c = bpy.data.collections.new(name); kc.children.link(c)
        size = {}
        vs = 0.1 if name == "Roof_Dish" else V                      # the dish is built with 0.1 m voxels (the pack's chunkier look)
        R.V = vs
        o = R.build_mesh(name, lambda: size.update(zip("WD", draw())), P)
        R.V = V
        ys = [y for _, y, _ in vox]
        o["facade_y"] = -(min(ys) + max(ys) + 1) / 2 * vs   # where local y = 0 (the wall line) sits after recentring
        # local voxel bounds in metres, so the corner can place a piece by its own origin (see night_shift_corner.local)
        o["vox_lo"] = [min(k[i] for k in vox) * vs for i in range(3)]
        o["vox_hi"] = [(max(k[i] for k in vox) + 1) * vs for i in range(3)]
        if name.startswith("Shop_") and name != "Shop_Library":   # the library's gargoyle wings overhang 0.1 m each side, symmetric
            assert abs(o.dimensions.x - size["W"] * V) < 1e-4, (name, o.dimensions.x)   # props must stay inside the width
        c.objects.link(o)
        print("SHOP", name, "W", size["W"] * V, "D", size["D"] * V, "facade_y", round(o["facade_y"], 3))
    bpy.ops.wm.save_mainfile()
    # preview: the four in a row on one wall line, lit from inside (not saved)
    s = bpy.context.scene
    for ob in bpy.data.objects:
        ob.hide_render = ob.name not in SHOPS and ob.type != "LIGHT"
    x = 0.0
    for name in SHOPS:
        ob = bpy.data.objects[name]
        x += ob.dimensions.x / 2
        ob.location = (x, -ob["facade_y"], 0)
        ld = bpy.data.lights.new(name + "_lamp", "AREA"); ld.energy, ld.size = 120, 2.0
        lo = bpy.data.objects.new(name + "_lamp", ld); lo.location = (x, 0.6, 2.2); s.collection.objects.link(lo)
        x += ob.dimensions.x / 2 + 0.6
    bpy.ops.mesh.primitive_plane_add(size=60, location=(x / 2, 0, 0))
    cam = bpy.data.objects["cam"]
    cam.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))
    cam.location = Vector((x / 2, 0, 1.3)) + cam.rotation_euler.to_matrix() @ Vector((0, 0, 80))
    cam.data.ortho_scale = x * 0.82
    cam.data.clip_end = 500
    s.render.resolution_x, s.render.resolution_y = 1920, 1080
    s.render.filepath = VAULT + r"\_attachments\previews\night-shift-3d-shops.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", s.render.filepath)
