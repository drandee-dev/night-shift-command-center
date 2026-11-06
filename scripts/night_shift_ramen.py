# Original voxel ramen stand (yatai) at the Streets pack's scale, 0.05 m voxels.
# Run on the kit: "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-kit.blend --python scripts/night_shift_ramen.py
# Adds kit_custom/RamenStand to the kit .blend and renders _attachments/previews/night-shift-3d-ramen.png beside kit props for scale.
# Rerun after night_shift_kit.py, which rebuilds the kit from scratch.
import bpy, math, os
from mathutils import Vector, Euler

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...

V = 0.05
# palette: name -> (base colour, emission colour already scaled by strength)
P = {
    "wood_d": ((0.20, 0.11, 0.07), None), "wood_m": ((0.30, 0.17, 0.10), None), "wood_l": ((0.55, 0.36, 0.20), None),
    "lacquer": ((0.55, 0.06, 0.07), None), "gold": ((0.85, 0.62, 0.20), None), "cream": ((0.92, 0.86, 0.72), None),
    "steel": ((0.45, 0.48, 0.52), None), "steel_d": ((0.20, 0.22, 0.28), None), "rubber": ((0.06, 0.06, 0.07), None),
    "roof_a": ((0.30, 0.33, 0.40), None), "roof_b": ((0.22, 0.25, 0.31), None), "indigo": ((0.10, 0.10, 0.32), None),
    "white": ((0.90, 0.90, 0.88), None), "broth": ((0.62, 0.36, 0.14), None), "egg": ((0.98, 0.78, 0.20), None),
    "chop": ((0.45, 0.10, 0.08), None), "board": ((0.06, 0.06, 0.09), None), "crate": ((0.10, 0.35, 0.60), None),
    "red_b": ((0.75, 0.10, 0.10), None), "yel_b": ((0.90, 0.75, 0.10), None), "green": ((0.30, 0.55, 0.20), None),
    # glow = base colour x strength; kept near 1 so the hue survives, step 5's bloom adds the intensity
    "neon_pink": ((1.0, 0.15, 0.65), 1.3), "neon_cyan": ((0.15, 0.85, 1.0), 1.3), "neon_yel": ((1.0, 0.8, 0.15), 1.2),
    "lantern": ((1.0, 0.22, 0.08), 1.2), "menu_g": ((0.3, 1.0, 0.45), 1.0), "menu_w": ((0.85, 0.85, 1.0), 0.9),
    "steam": ((0.75, 0.85, 0.90), 0.35),
}
vox = {}


def box(x0, x1, y0, y1, z0, z1, c):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                vox[(x, y, z)] = c if not callable(c) else c(x, y, z)


def cyl(cx, cy, r, z0, z1, c, top=None):
    for x in range(cx - r, cx + r + 1):
        for y in range(cy - r, cy + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r:
                for z in range(z0, z1 + 1):
                    vox[(x, y, z)] = top if (top and z == z1) else c


def design():
    # x 0..47 along the counter, y: low = customer side (-Y), z up
    plank = lambda x, y, z: "wood_m" if (x // 4) % 2 else "wood_d"
    box(2, 45, 8, 25, 2, 17, plank)                       # cabinet
    box(2, 45, 8, 25, 0, 1, "steel_d")                    # base trim
    box(4, 43, 8, 8, 3, 15, "lacquer")                    # red front panel
    for x in range(4, 44):
        vox[(x, 7, 3)] = vox[(x, 7, 15)] = "gold"
    for z in range(3, 16):
        vox[(4, 7, z)] = vox[(43, 7, z)] = "gold"
    for x in range(18, 30):                               # cream bowl emblem on the panel
        for z in range(6, 13):
            dx, dz = (x - 23.5) / 6, (z - 12) / 6
            if dz <= 0 and 0.55 < dx * dx + dz * dz <= 1.0 or z == 12:
                vox[(x, 7, z)] = "cream"
    for x0 in (1, 46):                                    # wheels
        for y in range(12, 22):
            for z in range(0, 10):
                d = (y - 16.5) ** 2 + (z - 4.5) ** 2
                if d <= 22:
                    vox[(x0, y, z)] = "steel" if d <= 3 else "rubber"
    box(0, 47, 4, 25, 18, 19, "wood_l")                   # counter top, overhangs the customer side
    for cx in (12, 22):                                   # stock pots with broth
        cyl(cx, 21, 3, 20, 27, "steel", top="broth")
        for z in range(29, 38, 2):                        # steam
            vox[(cx + (z // 2) % 3 - 1, 21, z)] = "steam"
    for z in range(20, 25):                               # stacked bowls
        box(31, 35, 19, 23, z, z, "red_b" if z % 2 else "white")
    for bx in (9, 23, 37):                                # served bowls with egg and chopsticks
        box(bx, bx + 4, 6, 9, 20, 21, "white")
        box(bx + 1, bx + 3, 7, 8, 21, 21, "broth")
        vox[(bx + 1, 7, 21)] = "egg"; vox[(bx + 3, 8, 21)] = "green"
        for x in range(bx - 1, bx + 6):
            vox[(x, 5, 22)] = "chop"
    box(27, 27, 12, 12, 20, 22, "red_b"); box(29, 29, 12, 12, 20, 22, "yel_b")   # condiments
    for px in (1, 45):                                    # posts with neon strips on the front pair
        for py in (4, 24):
            box(px, px + 1, py, py + 1, 20, 50, "steel_d")
        for z in range(22, 49):
            vox[(px, 3, z)] = "neon_pink"
    for y in range(0, 28):                                # corrugated roof, rising to the back
        zb = 50 + y * 4 // 27
        for x in range(-2, 50):
            for z in (zb, zb + 1):
                vox[(x, y, z)] = "roof_a" if (x // 2) % 2 else "roof_b"
    for x in range(-2, 50):
        vox[(x, -1, 50)] = "neon_cyan"                    # roof edge strip
    for i in range(4):                                    # noren curtains
        x0 = 3 + i * 11
        box(x0, x0 + 9, 1, 1, 41, 49, "indigo")
        box(x0, x0 + 9, 0, 0, 43, 43, "white")
        box(x0 + 4, x0 + 5, 0, 0, 45, 47, "white")
    for lx in (-2, 46):                                   # red paper lanterns
        box(lx, lx + 3, -1, 2, 39, 45, "lantern")
        box(lx + 1, lx + 2, 0, 1, 38, 38, "rubber"); box(lx + 1, lx + 2, 0, 1, 46, 49, "rubber")
    box(48, 48, 8, 22, 34, 48, "board")                   # menu board on the +X side
    for z in range(36, 47, 2):
        for y in range(10, 21):
            if (y + z) % 7:
                vox[(49, y, z)] = "menu_g" if z % 4 else "menu_w"
    box(10, 11, 13, 14, 54, 57, "steel_d"); box(36, 37, 13, 14, 54, 57, "steel_d")   # sign legs
    box(6, 41, 13, 14, 58, 74, "board")                   # neon sign: frame, bowl, chopsticks, steam
    for x in range(6, 42):
        vox[(x, 12, 58)] = vox[(x, 12, 74)] = "neon_pink"
    for z in range(58, 75):
        vox[(6, 12, z)] = vox[(41, 12, z)] = "neon_pink"
    for x in range(13, 35):
        for z in range(60, 68):
            dx, dz = (x - 23.5) / 10, (z - 67) / 7
            if dz <= 0 and 0.6 < dx * dx + dz * dz <= 1.0 or (z == 67 and 13 <= x <= 34):
                vox[(x, 12, z)] = "neon_pink"
    for i in range(10):
        vox[(26 + i, 12, 66 + i // 2)] = "neon_yel"; vox[(28 + i, 12, 66 + i // 2)] = "neon_yel"
    for sx in (17, 22, 27):
        for z in range(69, 73):
            vox[(sx + (z % 2), 12, z)] = "neon_cyan"
    for sx in (8, 22, 36):                                # stools on the customer side
        box(sx, sx + 3, -6, -3, 12, 13, "red_b")
        box(sx + 1, sx + 2, -5, -4, 0, 11, "steel")
        box(sx, sx + 3, -6, -3, 4, 4, "steel")
    for i, z0 in enumerate((0, 6)):                       # blue crates on the -X side
        box(-7, -2, 15 + i, 22 + i, z0, z0 + 5, lambda x, y, z: "crate" if (x + z) % 3 else "rubber")
        box(-6, -3, 16 + i, 21 + i, z0 + 5, z0 + 5, "green")   # cabbages
    # detail pass 2026-11-03: lantern string, side tarp, gas bottle, cooler, A-board menu, chopstick jar, bin
    for k, x in enumerate(range(5, 44, 6)):               # small lanterns strung under the roof edge
        z = 46 - (1 if 2 <= k <= 4 else 0)
        box(x, x + 2, -2, 0, z - 3, z, "lantern" if k % 2 else "neon_yel"); vox[(x + 1, -1, z + 1)] = "rubber"
    for x in range(1, 47):
        vox[(x, -1, 47 - (1 if 14 <= x <= 32 else 0))] = "rubber"
    for x in range(-15, -2):                              # striped tarp over the crates, on two poles
        for y in range(2, 28):
            vox[(x, y, 47 + (x + 15) // 5)] = "red_b" if (y // 3) % 2 else "white"
    for py in (3, 26):
        box(-15, -15, py, py, 0, 46, "steel_d")
    cyl(53, 23, 2, 0, 11, "steel", top="steel_d"); box(53, 53, 23, 23, 12, 13, "yel_b")   # gas bottle and hose
    for x in range(46, 53):
        vox[(x, 23, 13 - (x - 46) // 3)] = "rubber"
    box(-13, -6, 4, 9, 0, 6, "white"); box(-13, -6, 4, 9, 7, 7, "crate"); box(-13, -6, 4, 4, 3, 3, "crate")   # cooler
    box(51, 56, -7, -6, 0, 15, "wood_d")                  # A-board menu on the sidewalk
    for z in range(3, 14, 2):
        for x in range(52, 56):
            if (x + z) % 5:
                vox[(x, -8, z)] = "menu_g" if z % 4 == 1 else "menu_w"
    box(51, 56, -8, -8, 15, 15, "neon_pink")
    cyl(16, 12, 1, 20, 23, "wood_l")                      # chopstick jar
    for dx in (-1, 0, 1):
        box(16 + dx, 16 + dx, 12, 12, 24, 26, "chop")
    box(-6, -2, -5, -1, 0, 8, "steel_d"); box(-6, -2, -5, -1, 9, 9, "rubber")              # bin


def build_mesh(name, draw=design, pal=P):
    """draw() fills vox with palette names from pal; night_shift_shops.py reuses this with its own designs."""
    vox.clear()
    draw()
    names = sorted(pal)
    idx = {n: i for i, n in enumerate(names)}
    n = len(names)
    base = bpy.data.images.new(name + "_base", n, 1, float_buffer=True)
    emit = bpy.data.images.new(name + "_emit", n, 1, float_buffer=True)
    bp, ep = [], []
    for k in names:
        c, e = pal[k]
        bp += [*c, 1]; ep += [*(ch * (e or 0) for ch in c), 1]
    base.pixels = bp; emit.pixels = ep
    base.pack(); emit.pack()
    dirs = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
            ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
            ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    verts, faces, uvs = [], [], []
    for (x, y, z), c in vox.items():
        for (dx, dy, dz), corners in dirs:
            if (x + dx, y + dy, z + dz) in vox:
                continue                                   # hidden face
            i0 = len(verts)
            verts += [((x + a) * V, (y + b) * V, (z + d) * V) for a, b, d in corners]
            faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
            uvs.append(((idx[c] + 0.5) / n, 0.5))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for f, u in zip(me.polygons, uvs):
        for li in f.loop_indices:
            uv.data[li].uv = u
    lo = Vector([min(v[i] for v in verts) for i in range(3)]); hi = Vector([max(v[i] for v in verts) for i in range(3)])
    me.transform(__import__("mathutils").Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
    m = bpy.data.materials.new(name)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = base; tb.interpolation = "Closest"
    te = nt.nodes.new("ShaderNodeTexImage"); te.image = emit; te.interpolation = "Closest"
    nt.links.new(tb.outputs["Color"], b.inputs["Base Color"]); nt.links.new(te.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.7
    me.materials.append(m)
    print("VOXELS", len(vox), "FACES", len(faces), "SIZE", tuple(round(v, 2) for v in hi - lo))
    return bpy.data.objects.new(name, me)


if __name__ == "__main__":
    kc = bpy.data.collections.get("kit_custom") or bpy.data.collections.new("kit_custom")
    if kc.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(kc)
    old = bpy.data.collections.get("RamenStand")
    if old:
        for o in list(old.objects): bpy.data.objects.remove(o)
        bpy.data.collections.remove(old)
    c = bpy.data.collections.new("RamenStand"); kc.children.link(c)
    ramen = build_mesh("RamenStand"); c.objects.link(ramen)
    bpy.ops.wm.save_mainfile()
    # scale check render: the stand beside the Streets door and table
    s = bpy.context.scene
    show = {"RamenStand": (0, 0), "Door_D_00": (-2.4, 0), "Table_00": (2.4, -0.4)}
    for o in bpy.data.objects:
        o.hide_render = o.name not in show and o.type != "LIGHT"
    for nm, (x, y) in show.items():
        bpy.data.objects[nm].location = (x - sum(v[0] for v in bpy.data.objects[nm].bound_box) / 8,
                                         y - sum(v[1] for v in bpy.data.objects[nm].bound_box) / 8, 0)
    cam = bpy.data.objects["cam"]
    cam.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))
    cam.location = cam.rotation_euler.to_matrix() @ Vector((0, 1.6, 60))
    cam.data.ortho_scale = 7.5
    s.render.resolution_x, s.render.resolution_y = 1600, 1200
    s.render.filepath = os.path.join(VAULT, "_attachments", "previews", "night-shift-3d-ramen.png")
    bpy.ops.render.render(write_still=True)   # not saved: the kit layout positions stay as they were
    print("RENDERED", s.render.filepath)
