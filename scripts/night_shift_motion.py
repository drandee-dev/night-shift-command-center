# The animated dashboard loop: 8 s, 192 frames at 24 fps, seamless (frame 193 == frame 1). Not run directly:
# night_shift_looks.py execs it when called with "anim", after the lights are built, so it shares that script's scene:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-corner.blend --python scripts/night_shift_looks.py -- b anim
#   ... -- b anim 1 24      a test range: PNGs in _attachments/previews/night-shift-3d-motion-####.png, no video
# Adds, all keyed to repeat every 192 frames: a glow and a small light on every pack sign, flicker and buzz on some of
# them, a red blinking dot on each camera, swaying palms, idle bobbing, and two walkers who start off-frame and end at a
# door (night_shift_people.py builds their three gait poses). Writes _attachments/scenes/night-shift-3d-loop.webm.
import bpy, sys, math, random, os
from mathutils import Vector, Matrix

# run inside night_shift_looks.py, which sets VAULT; standalone, this file is <root>/scripts/...
VAULT = globals().get("VAULT") or os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRAMES = 192
args = sys.argv[sys.argv.index("anim") + 1:]
corner = bpy.data.collections["corner"]
pref = bpy.context.preferences.edit
rng = random.Random(41)
snap = lambda v, g=0.05: round(v / g) * g
s.frame_start, s.frame_end, s.render.fps = 1, FRAMES, 24


def wbox(inst):
    pts = [inst.matrix_world @ o.matrix_world @ Vector(c) for o in inst.instance_collection.objects if o.type == "MESH" for c in o.bound_box]
    return Vector(map(min, zip(*pts))), Vector(map(max, zip(*pts)))


def interp(blk, path, mode):
    """Set every key on blk's datablock whose curve ends in path to CONSTANT or LINEAR. (The new-key preference is not
    honoured for these slotted actions: the keys came out eased, which smoothed every flicker and every switch.)"""
    from bpy_extras import anim_utils
    ad = blk.id_data.animation_data
    if not ad or not ad.action: return
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in (cb.fcurves if cb else []):
        if fc.data_path.endswith(path):
            for kp in fc.keyframe_points: kp.interpolation = mode


def key_pattern(mult, targets):
    """Constant keys wherever the 192-frame multiplier changes. targets: (datablock, path, base value)."""
    pref.keyframe_new_interpolation_type = "CONSTANT"
    for f in range(FRAMES):
        if f == 0 or mult[f] != mult[f - 1]:
            for blk, path, base in targets:
                setattr(blk, path, base * mult[f]); blk.keyframe_insert(path, frame=f + 1)
    for blk, path, _ in targets: interp(blk, path, "CONSTANT")


# ---- 1. pack signs: glow in their own colour, plus a small light so the glow spills on the walls ----
signs = [o for o in corner.objects if o.instance_collection and o.name.startswith(("Billboard", "Neon_"))]
PALETTE = [(1.0, 0.15, 0.7), (0.1, 0.9, 1.0), (0.6, 0.25, 1.0), (0.2, 1.0, 0.4), (1.0, 0.2, 0.2), (1.0, 0.7, 0.2)]
NAMED = {"Blue": (0.2, 0.4, 1.0), "Red": (1.0, 0.1, 0.15), "Green": (0.2, 1.0, 0.4), "Turquoise": (0.1, 0.9, 0.9)}
glow, lights = {}, {}                                   # kit collection name -> emission sockets, light datablocks
for o in signs:
    cname = o.instance_collection.name
    strength = 3.0 if cname.startswith("Neon") else 1.2
    if cname not in glow:
        glow[cname] = []
        for m in {ms for ob in o.instance_collection.objects if ob.type == "MESH" for ms in ob.data.materials if ms}:
            b = m.node_tree.nodes["Principled BSDF"]
            if b.inputs["Base Color"].links:
                m.node_tree.links.new(b.inputs["Base Color"].links[0].from_socket, b.inputs["Emission Color"])
            else:
                b.inputs["Emission Color"].default_value = b.inputs["Base Color"].default_value
            b.inputs["Emission Strength"].default_value = strength
            glow[cname].append(b.inputs["Emission Strength"])
    lo, hi = wbox(o)
    ctr, size = (lo + hi) / 2, hi - lo
    col = next((c for k, c in NAMED.items() if k in cname), None) or PALETTE[sum(map(ord, cname)) % len(PALETTE)]
    ld = bpy.data.lights.new("signlight", "POINT"); ld.color = col; ld.use_shadow = False
    ld.energy = 25 + 6 * min(max(size.x, size.y) * size.z, 18); ld.shadow_soft_size = 0.4
    lo_ = bpy.data.objects.new("signlight", ld); lo_.location = ctr + Vector((0.7, -0.7, 0)); corner.objects.link(lo_)
    lights.setdefault(cname, []).append(ld)

FLICKER = ["Neon_Red_00", "Neon_Green_00", "Billboard_Open_00", "Neon_Blue_Small_00", "Billboard_Smoke_00"]
BUZZ = ["Billboard_Pharmacy_00", "Billboard_Drugs_A_00", "Billboard_Ring_00"]
# neon strips whose letters light one after another (cycles per loop, phase); the rest of the neon flickers or buzzes
CHASE_PACK = {"Neon_Turquoise_Long_00": (1, 0.0), "Neon_Turquoise_00": (2, 0.3), "Neon_Blue_00": (1, 0.55)}


def flicker_pattern():
    m = [1.0] * FRAMES
    for _ in range(rng.randint(4, 6)):                  # short bursts of irregular drops
        f0 = rng.randint(0, FRAMES - 8)
        for i in range(rng.randint(2, 5)):
            m[f0 + i] = rng.choice((0.1, 0.2, 0.3, 0.55, 1.0))
    return m


def buzz_pattern(slot):
    # a stutter, a dark spell, then a stutter back: segments of (level, frames); slot spreads the spells over the loop
    segs = [(1.0, 1), (0.25, 2), (1.0, 2), (0.03, rng.randint(14, 34)), (1.0, rng.randint(1, 3)), (0.03, rng.randint(2, 4)),
            (1.0, rng.randint(2, 4)), (0.03, rng.randint(1, 3))]
    m, f = [1.0] * FRAMES, slot * (FRAMES // len(BUZZ)) + rng.randint(0, 8)
    for level, n in segs:
        for i in range(n):
            m[(f + i) % FRAMES] = level                 # wraps round the loop end, so the pattern stays periodic
        f += n
    return m


for k, cname in enumerate(FLICKER + BUZZ):
    if cname not in glow:
        print("MOTION skipped, not in the scene:", cname); continue
    mult = flicker_pattern() if k < len(FLICKER) else buzz_pattern(k - len(FLICKER))
    key_pattern(mult, [(sk, "default_value", sk.default_value) for sk in glow[cname]] + [(ld, "energy", ld.energy) for ld in lights[cname]])

# ---- 1b. the big billboards (bunny girls, the gas mask and guns banner, the gun signs): brighter and alive ----
# Each gets, inside its own materials: a bright bar sweeping down the sign, a heartbeat pulse, a slow hue drift, and bursts
# of horizontal glitch tearing (white-noise strips). All periodic in 192 frames; the spill light pulses with it.
# name: (glow strength, sweeps per loop, pulses per loop, hue drift, glitch bursts, spill light multiplier)
BIG = {"Billboard_Girl_B_00": (3.0, 1, 4, 0.03, 3, 3.0), "Billboard_Girl_A_00": (3.0, 1, 5, 0.03, 3, 3.0),
       "Billboard_RedCrime_00": (2.3, 2, 6, 0.012, 4, 3.5), "Billboard_TopGun_00": (3.0, 3, 8, 0.0, 3, 3.0),
       "Billboard_JapaneseGun_00": (3.0, 3, 6, 0.0, 3, 3.0),
       "Billboard_CatchADoll_00": (3.2, 2, 6, 0.02, 2, 3.0),                  # the arcade's frog and chick banner: bright, sweeping, pulsing (2026-11-05)
       "Billboard_Game_00": (3.4, 3, 8, 0.0, 6, 3.0)}                         # the GAME dice sign: extra glitch bursts, like dice rolling


def mn(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def drive(nt, expr):
    n = nt.nodes.new("ShaderNodeValue")
    d = n.outputs[0].driver_add("default_value").driver                  # simple expressions run without Python auto-exec
    d.type = "SCRIPTED"; d.expression = expr
    return n.outputs[0]


def chase_fx(m, size, axis, cycles, ph=0.0, lo=0.3, ztop=None):
    """A stepped chase along the mesh's own axis: pieces about 45 cm wide (letters) light one after another, all stay lit
    a while, then they reset. ztop limits it to the band above that share of the mesh's height (a storefront's fascia).
    size is the mesh's length along the axis in metres."""
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    base = b.inputs["Emission Strength"].default_value
    t = drive(nt, "(frame - 1) / 192")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
    n = max(3, round(size / 0.45))
    step = mn(nt, "DIVIDE", mn(nt, "FLOOR", mn(nt, "MULTIPLY", sep.outputs[axis], n)), n)
    reach = mn(nt, "MULTIPLY", mn(nt, "FRACT", mn(nt, "ADD", mn(nt, "MULTIPLY", t, cycles), ph)), 1.5)   # 0..1.5: lit, then held
    mult = mn(nt, "ADD", lo, mn(nt, "MULTIPLY", mn(nt, "LESS_THAN", step, reach), 1.3 - lo))
    if ztop is not None:
        inside = mn(nt, "GREATER_THAN", sep.outputs["Z"], ztop)
        mult = mn(nt, "ADD", 1.0, mn(nt, "MULTIPLY", inside, mn(nt, "SUBTRACT", mult, 1.0)))
    nt.links.new(mn(nt, "MULTIPLY", mult, base), b.inputs["Emission Strength"])


def mats_of(cname):
    return {ms for ob in bpy.data.collections[cname].objects if ob.type == "MESH" for ms in ob.data.materials if ms}


def longest(cname):                                                 # (length in metres, local axis) of the collection's mesh
    d = next(ob for ob in bpy.data.collections[cname].objects if ob.type == "MESH").dimensions
    return (d.x, "X") if d.x >= d.y else (d.y, "Y")


for cname, (cycles, ph) in CHASE_PACK.items():
    if cname in glow:
        size, axis = longest(cname)
        for m in mats_of(cname): chase_fx(m, size, axis, cycles, ph)
# our own storefronts: the fascia band chases (REPAIR, NET CAFE, 24H MART, HYDRO FLORA's shop), the ramen stand and the
# balcony chase gently as a whole
for k, (cname, ztop, lo) in enumerate((("Shop_Repair", 0.7, 0.3), ("Shop_BodyMods", 0.7, 0.3), ("Shop_Mart", 0.7, 0.3),
                                       ("Shop_Florist", 0.7, 0.3), ("RamenStand", None, 0.55), ("Patio_Florist", None, 0.55),
                                       ("Shop_Games", 0.7, 0.3), ("Shop_Library", 0.7, 0.3), ("Loft_NetCafe", 0.85, 0.3))):      # GAME HUB, LIBRARY: last so the others keep their phase
    if cname in bpy.data.collections:
        size, axis = longest(cname)
        for m in mats_of(cname): chase_fx(m, size, axis, 1 if k % 2 == 0 else 2, k * 0.17, lo, ztop)
# the claw machine and the drinks machine run their lights up the cabinet
for k, cname in enumerate(("Machine_CatchaDoll_00", "Machine_CatchaDoll_Glass_00", "Machine_DrinkDispenser_Glass_00")):
    if cname in bpy.data.collections:
        for m in mats_of(cname):
            if m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].links:
                chase_fx(m, 1.8, "Z", 3, k * 0.2, 0.45)
# every other billboard gets a milder version of the big signs' treatment
BIG.update({c: (1.8, 1, rng.randint(2, 5), 0.0, 1, 1.5) for c in glow
            if c.startswith("Billboard") and c not in BIG and c not in FLICKER + BUZZ and c not in CHASE_PACK})

for k, (cname, (boost, sweeps, pulses, hue, nburst, spill)) in enumerate(BIG.items()):
    if cname not in glow:
        print("MOTION skipped, not in the scene:", cname); continue
    bursts = [0.0] * FRAMES
    for _ in range(nburst):
        f0 = rng.randint(0, FRAMES - 8)
        for i in range(rng.randint(3, 6)): bursts[f0 + i] = 1.0
    ph = k * 0.23
    for m in {ms for ob in bpy.data.collections[cname].objects if ob.type == "MESH" for ms in ob.data.materials if ms}:
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        t = drive(nt, "(frame - 1) / 192")                                              # 0..1 over the loop
        z = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], z.inputs[0])
        tau = 2 * math.pi
        pos = mn(nt, "FRACT", mn(nt, "SUBTRACT", z.outputs["Z"], mn(nt, "ADD", mn(nt, "MULTIPLY", t, sweeps), ph)))
        band = mn(nt, "POWER", mn(nt, "SUBTRACT", 1.0, pos), 10.0)                      # a bright head with a fading trail
        beat = mn(nt, "ADD", 1.0, mn(nt, "MULTIPLY", mn(nt, "SINE", mn(nt, "MULTIPLY", t, tau * pulses)), 0.18))
        tear = nt.nodes.new("ShaderNodeTexWhiteNoise"); tear.noise_dimensions = "2D"
        row = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(mn(nt, "FLOOR", mn(nt, "MULTIPLY", z.outputs["Z"], 40.0)), row.inputs["X"])
        nt.links.new(mn(nt, "FLOOR", drive(nt, "(frame - 1) / 2")), row.inputs["Y"])
        nt.links.new(row.outputs[0], tear.inputs["Vector"])
        g = nt.nodes.new("ShaderNodeValue")
        key_pattern(bursts, [(g.outputs[0], "default_value", 1.0)])
        torn = mn(nt, "ADD", 1.0, mn(nt, "MULTIPLY", g.outputs[0], mn(nt, "SUBTRACT", mn(nt, "MULTIPLY", tear.outputs["Value"], 2.4), 1.0)))
        strength = mn(nt, "MULTIPLY", mn(nt, "MULTIPLY", mn(nt, "ADD", 1.0, mn(nt, "MULTIPLY", band, 2.2)), beat), mn(nt, "MULTIPLY", torn, boost))
        nt.links.new(strength, b.inputs["Emission Strength"])
        if hue:
            hs = nt.nodes.new("ShaderNodeHueSaturation")
            src = b.inputs["Emission Color"].links[0].from_socket if b.inputs["Emission Color"].links else None
            if src: nt.links.new(src, hs.inputs["Color"])
            else: hs.inputs["Color"].default_value = b.inputs["Emission Color"].default_value
            nt.links.new(mn(nt, "ADD", 0.5, mn(nt, "MULTIPLY", mn(nt, "SINE", mn(nt, "MULTIPLY", t, tau)), hue)), hs.inputs["Hue"])
            nt.links.new(hs.outputs["Color"], b.inputs["Emission Color"])
    pref.keyframe_new_interpolation_type = "LINEAR"
    for ld in lights[cname]:
        ld.energy *= spill; base = ld.energy
        for f in list(range(1, FRAMES + 1, 2)) + [FRAMES + 1]:
            ld.energy = base * (1 + 0.18 * math.sin(2 * math.pi * pulses * (f - 1) / FRAMES)) * (1 + 0.5 * bursts[min(f, FRAMES) - 1])
            ld.keyframe_insert("energy", frame=f)
        interp(ld, "energy", "LINEAR")

# ---- 1d. the bunny girls and the gas mask banner come alive ----
# These signs are real voxel geometry (greedy-merged quads coloured from a shared atlas), so there is no sprite to
# repaint. Each gets its own mesh copy; overlay quads (eyes, mouth, lenses, muzzle flashes) sit just in front of the
# face and show or hide through their material's alpha; shape keys tilt the head and flick the ears, or breathe.
# Positions are in the sign's local metres (x across from its centre, z up from its bottom), read off a front render.
import bmesh
FRONT = -0.065                                                      # overlays float this far in front (-y is the sign's front)


def sign_copy(cname):
    inst = next(o for o in corner.objects if o.instance_collection and o.instance_collection.name == cname)
    src = next(ob for ob in inst.instance_collection.objects if ob.type == "MESH")
    ob = bpy.data.objects.new(inst.name + "_anim", src.data.copy())
    ob.matrix_world = inst.matrix_world @ Matrix.Translation(-inst.instance_collection.instance_offset) @ src.matrix_world   # as the instance places it
    corner.objects.link(ob); inst.hide_render = True
    print("MOTION sign copy", cname, tuple(round(v, 2) for v in ob.matrix_world.translation), "dims", tuple(round(d, 2) for d in ob.dimensions),
          "polys", len(ob.data.polygons), "mats", len(ob.data.materials))
    return inst, ob


def spans(frames, shift=0):                                         # 1.0 on the (first, last) 1-based frame spans, else 0.0
    m = [0.0] * FRAMES
    for a, b in frames:
        for f in range(a, b + 1): m[(f - 1 + shift) % FRAMES] = 1.0
    return m


def overlay(me, groups):
    """groups: (name, rgb, emission strength, alpha pattern, layer, rects[(x0, x1, z0, z1)]); one material per group."""
    bm = bmesh.new(); bm.from_mesh(me)
    for name, rgb, strength, alpha, layer, rects in groups:
        mat = bpy.data.materials.new(name); b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = strength
        mat.surface_render_method = "BLENDED"
        key_pattern(alpha, [(b.inputs["Alpha"], "default_value", 1.0)])
        me.materials.append(mat); mi = len(me.materials) - 1
        for x0, x1, z0, z1 in rects:
            vs = [bm.verts.new((x, FRONT - 0.004 * layer, z)) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
            bm.faces.new(vs).material_index = mi
    bm.to_mesh(me); bm.free()


def shape(ob, name, fn):                                            # fn(position, vertex index) -> the position for the key at 1.0
    sk = ob.shape_key_add(name=name); sk.slider_min, sk.slider_max = -1.0, 1.0
    for i, v in enumerate(ob.data.vertices): sk.data[i].co = fn(Vector(v.co), i)
    return sk


def figure_verts(me):
    """Vertices of faces that belong to the picture, not the sign's striped background (magenta or red: strong red, almost no
    green in the atlas colour under the face)."""
    import numpy as np
    img = me.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].links[0].from_node.image
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    uv = me.uv_layers.active.data
    fig = set()
    for p in me.polygons:
        u = sum(uv[l].uv[0] for l in p.loop_indices) / p.loop_total; v = sum(uv[l].uv[1] for l in p.loop_indices) / p.loop_total
        r, g, _, _ = px[min(h - 1, int(v * h)), min(w - 1, int(u * w))]
        if not (g < 0.08 and r > 0.3): fig.update(p.vertices)
    return fig


def rot(co, pivot, deg, w=1.0):                                     # turn co about pivot (x, z) in the sign's plane, w of the way
    a = math.radians(deg) * w; px, pz = pivot
    dx, dz = co.x - px, co.z - pz
    return Vector((px + dx * math.cos(a) - dz * math.sin(a), co.y, pz + dx * math.sin(a) + dz * math.cos(a)))


def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def key_values(ob, values):                                         # values: shape key name -> fn(frame) -> value, linear keys
    pref.keyframe_new_interpolation_type = "LINEAR"
    for name, fn in values.items():
        kb = ob.data.shape_keys.key_blocks[name]
        for f in list(range(1, FRAMES + 1, 2)) + [FRAMES + 1]:
            kb.value = fn(f); kb.keyframe_insert("value", frame=f)
        interp(kb, "value", "LINEAR")


def bunny(cname, shift, phase):
    if cname not in glow: return
    inst, ob = sign_copy(cname); me = ob.data
    fig, n0 = figure_verts(me), len(me.vertices)                    # overlay vertices added below are part of the figure too
    head = lambda c, i: smooth((c.z - 0.62) / 0.3) * (1.0 if (i in fig or i >= n0) and (c.x > -0.4 or c.z > 1.7) and c.z < 2.6 and abs(c.x) < 1.4 else 0.0)
    for v in me.vertices:                                           # the head floats a hair in front so it can turn over the background
        v.co.y -= 0.012 * head(v.co, v.index)
    blink = [(37, 40), (92, 95), (96, 98), (150, 153)]              # the eyes open between these
    open_eyes = [1.0 - x for x in spans(blink, shift)]
    look_a = spans([(1, 55), (101, 150)], shift); look_b = [1.0 - x for x in look_a]
    pupil = lambda w: [o * w[i] for i, o in enumerate(open_eyes)]
    talk = spans([(20, 23), (26, 29), (32, 34), (38, 41), (100, 103), (107, 110), (113, 116), (121, 124)], shift)
    skin, iris, dark = (0.93, 0.97, 1.0), (0.0, 0.75, 0.85), (0.04, 0.04, 0.10)
    eyes = lambda cx, cz: dict(white=(cx - 0.11, cx + 0.11, cz - 0.07, cz + 0.07), iris=(cx - 0.05, cx + 0.05, cz - 0.07, cz + 0.07),
                               pa=(cx - 0.05, cx, cz - 0.04, cz + 0.04), pb=(cx, cx + 0.05, cz - 0.04, cz + 0.04))
    L, R = eyes(0.19, 1.07), eyes(0.58, 1.09)
    overlay(me, [("eye_white", skin, 1.6, open_eyes, 1, [L["white"], R["white"]]), ("eye_iris", iris, 2.2, open_eyes, 2, [L["iris"], R["iris"]]),
                 ("pupil_a", dark, 1.0, pupil(look_a), 3, [L["pa"], R["pa"]]), ("pupil_b", dark, 1.0, pupil(look_b), 3, [L["pb"], R["pb"]]),
                 ("mouth_open", (0.35, 0.03, 0.10), 2.0, talk, 1, [(0.29, 0.40, 0.78, 0.89)]),
                 ("tongue", (1.0, 0.45, 0.55), 2.5, talk, 2, [(0.32, 0.37, 0.78, 0.82)])])
    ob.shape_key_add(name="Basis")
    neck = (0.35, 0.63)
    shape(ob, "tilt", lambda c, i: rot(c, neck, 3.0, head(c, i)))
    ear = lambda base, lo, hi: (lambda c, i: rot(c, base, 9.0, 1.0 if (i in fig or i >= n0) and lo < c.x < hi and 1.75 < c.z < 2.6 else 0.0))
    shape(ob, "earL", ear((-0.04, 1.9), -1.0, 0.1)); shape(ob, "earR", ear((0.56, 1.9), 0.45, 1.4))
    flick = lambda a, b: (lambda f: (lambda g: math.sin(math.pi * (g - a) / (b - a)) if a <= g <= b else 0.0)((f - 1 - shift) % FRAMES + 1))
    key_values(ob, {"tilt": lambda f: math.sin(2 * math.pi * ((f - 1) / FRAMES + phase)),
                    "earL": lambda f: max(flick(60, 68)(f), flick(140, 148)(f)), "earR": lambda f: max(flick(66, 74)(f), flick(152, 160)(f))})


def hair_verts(me):
    """Vertices of faces whose atlas colour is green (Girl_B's hair)."""
    import numpy as np
    img = me.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].links[0].from_node.image
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    uv = me.uv_layers.active.data
    hair = set()
    for p in me.polygons:
        u = sum(uv[l].uv[0] for l in p.loop_indices) / p.loop_total; v = sum(uv[l].uv[1] for l in p.loop_indices) / p.loop_total
        r, g, b, _ = px[min(h - 1, int(v * h)), min(w - 1, int(u * w))]
        if g > 0.25 and g > 1.6 * r and g > 1.6 * b: hair.update(p.vertices)
    return hair


def girl_b():
    """Billboard_Girl_B_00 (the green-haired girl over the mart, 3 x 2.85 m, 0.05 m voxels). Positions read off a front render
    (scratch script girlb_front.py in the session scratchpad): face centre x 0.2, z 1.65; red lips x 0.15 to 0.25, z 1.5 to 1.6;
    pale eye pixels at z 1.75 to 1.85. She talks (dark mouth over the lips), her eyes flash cyan, her head tilts a little and her
    hair sways."""
    cname = "Billboard_Girl_B_00"
    if cname not in glow: return
    inst, ob = sign_copy(cname); me = ob.data
    fig, n0, hair = figure_verts(me), len(me.vertices), hair_verts(me)
    head = lambda c, i: smooth((c.z - 1.35) / 0.2) * (1.0 if i in fig or i >= n0 else 0.0)
    talk = spans([(28, 31), (34, 37), (40, 42), (118, 121), (125, 128), (131, 134), (138, 140)])
    glint = spans([(60, 66), (68, 70), (150, 156)])
    overlay(me, [("eye_glint", (0.0, 0.85, 1.0), 5.0, glint, 2, [(0.102, 0.15, 1.75, 1.85), (0.25, 0.302, 1.75, 1.80)]),
                 ("mouth_open", (0.35, 0.03, 0.10), 2.0, talk, 1, [(0.17, 0.24, 1.52, 1.58)])])
    ob.shape_key_add(name="Basis")
    shape(ob, "tilt", lambda c, i: rot(c, (0.2, 1.35), 4.0, head(c, i)))
    shape(ob, "sway", lambda c, i: Vector((c.x + 0.09 * max(0.0, (1.5 - c.z) / 1.5) ** 1.2, c.y, c.z)) if i in hair and c.z < 1.5 else c)
    key_values(ob, {"tilt": lambda f: math.sin(2 * math.pi * (f - 1) / FRAMES),
                    "sway": lambda f: math.sin(2 * math.pi * 2 * (f - 1) / FRAMES + 1.0)})


girl_b()
bunny("Billboard_Girl_A_00", 0, 0.0)                                             # the bunny girl is back in the scene (2026-11-05)


def gas_mask():
    cname = "Billboard_RedCrime_00"
    if cname not in glow: return
    inst, ob = sign_copy(cname); me = ob.data
    lens = [(-0.26, 4.25), (0.15, 4.25)]
    glow_a = spans([(1, 12), (19, 36), (43, 60), (67, 84), (91, 108), (115, 132), (139, 156), (163, 180)])    # lenses throb
    bar = lambda k: spans([(1 + 8 * i + 0, 8 * i + 8) for i in range(k, 24, 3)])                                # a scanning bar, three stops
    left = [(34, 35), (50, 51), (104, 105), (141, 142)]; right = [(42, 43), (58, 59), (112, 113), (145, 146)]    # shots, alternating
    star = lambda x, z: [(x - 0.14, x + 0.14, z - 0.03, z + 0.03), (x - 0.03, x + 0.03, z - 0.14, z + 0.14), (x - 0.07, x + 0.07, z - 0.07, z + 0.07)]
    overlay(me, [("lens_glow", (1.0, 0.18, 0.06), 6.0, [0.45 + 0.55 * a for a in glow_a], 1, [(x - 0.085, x + 0.085, z - 0.07, z + 0.07) for x, z in lens]),
                 ("lens_scan_0", (1.0, 0.9, 0.5), 9.0, bar(0), 2, [(x - 0.075, x - 0.045, z - 0.07, z + 0.07) for x, z in lens]),
                 ("lens_scan_1", (1.0, 0.9, 0.5), 9.0, bar(1), 2, [(x - 0.015, x + 0.015, z - 0.07, z + 0.07) for x, z in lens]),
                 ("lens_scan_2", (1.0, 0.9, 0.5), 9.0, bar(2), 2, [(x + 0.045, x + 0.075, z - 0.07, z + 0.07) for x, z in lens]),
                 ("flash_l", (1.0, 0.85, 0.4), 12.0, spans(left), 3, star(-1.0, 3.99)), ("flash_r", (1.0, 0.85, 0.4), 12.0, spans(right), 3, star(1.0, 4.0)),
                 ("bars_top", (1.0, 0.85, 0.1), 7.0, spans([(1 + 48 * i, 24 + 48 * i) for i in range(4)]), 1, [(-0.39, 0.39, 6.38, 6.50)]),
                 ("bars_bottom", (1.0, 0.85, 0.1), 7.0, spans([(25 + 48 * i, 48 + 48 * i) for i in range(4)]), 1, [(-0.40, 0.40, 0.55, 0.67)])])
    for x, shots in ((-1.0, left), (1.0, right)):                   # each shot lights the wall red for a moment
        ld = bpy.data.lights.new("muzzle", "POINT"); ld.color = (1.0, 0.45, 0.2); ld.use_shadow = False; ld.shadow_soft_size = 0.15; ld.energy = 0
        lo_ = bpy.data.objects.new("muzzle", ld); lo_.location = inst.matrix_world @ Vector((x, -0.9, 4.0)); corner.objects.link(lo_)
        key_pattern(spans(shots), [(ld, "energy", 260.0)])
    ob.shape_key_add(name="Basis")
    centre = Vector((-0.06, 4.2))                                   # the mask breathes: it swells a few percent and settles
    swell = lambda c: 0.05 * smooth(1 - math.hypot(c.x - centre.x, c.z - centre.y) / 0.6)
    shape(ob, "breathe", lambda c, i: Vector((c.x + (c.x - centre.x) * swell(c), c.y, c.z + (c.z - centre.y) * swell(c))))
    key_values(ob, {"breathe": lambda f: 0.5 - 0.5 * math.cos(2 * math.pi * 2 * (f - 1) / FRAMES)})


gas_mask()

# ---- 2. cameras: a red dot that blinks, 24 frames on and 24 off, each camera in its own phase ----
CAM_DOTS = False     # Andres 2026-11-03: the dots bloom into pink squares that look out of place; set True to bring them back
cams = [o for o in corner.objects if o.instance_collection and o.name.startswith("Camera_")] if CAM_DOTS else []
for i, o in enumerate(cams):
    lo, hi = wbox(o)
    front = o.matrix_world.translation.y < 0.5 and o.matrix_world.translation.x < 0.3     # on the main road facade, else the side one
    pos = Vector(((lo.x + hi.x) / 2, lo.y - 0.02, hi.z - 0.07)) if front else Vector((hi.x + 0.02, (lo.y + hi.y) / 2, hi.z - 0.07))
    dot = bpy.data.objects.new("camdot", bpy.data.meshes.new("camdot"))
    dot.data.from_pydata([(x * 0.04, y * 0.04, z * 0.04) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], [],
                         [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    dot.location = pos; corner.objects.link(dot)
    mat = bpy.data.materials.new(f"camdot{i}"); em = mat.node_tree.nodes["Principled BSDF"]
    em.inputs["Base Color"].default_value = (0, 0, 0, 1); em.inputs["Emission Color"].default_value = (1, 0.05, 0.05, 1)
    em.inputs["Emission Strength"].default_value = 12.0; dot.data.materials.append(mat)
    ld = bpy.data.lights.new("camlight", "POINT"); ld.color = (1, 0.1, 0.1); ld.energy = 6; ld.use_shadow = False; ld.shadow_soft_size = 0.1
    lo_ = bpy.data.objects.new("camlight", ld); lo_.location = pos + Vector((0.05, -0.05, 0)); corner.objects.link(lo_)
    phase = i * 12
    mult = [1.0 if ((f + phase) // 24) % 2 == 0 else 0.0 for f in range(FRAMES)]
    key_pattern(mult, [(em.inputs["Emission Strength"], "default_value", 12.0), (ld, "energy", 6.0)])

# ---- 3. palms: the crown sways on its own mesh copy; shape keys keep the planter still ----
SWAY = {"Plant_TreeTall": (0.35, 0.28), "Plant_Tree": (0.25, 0.3), "Plant_Palm": (0.08, 0.3)}   # crown shift in m, share of height that stays still
pref.keyframe_new_interpolation_type = "LINEAR"
for n, inst in enumerate([o for o in corner.objects if o.instance_collection and o.instance_collection.name in SWAY]):
    amp, still = SWAY[inst.instance_collection.name]
    src = next(ob for ob in inst.instance_collection.objects if ob.type == "MESH")
    ob = bpy.data.objects.new(inst.name + "_sway", src.data.copy())
    ob.matrix_world = inst.matrix_world @ src.matrix_world
    corner.objects.link(ob); inst.hide_render = True
    me = ob.data
    zs = [v.co.z for v in me.vertices]; z0, z1 = min(zs), max(zs)
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices); cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    rmax = max(math.hypot(v.co.x - cx, v.co.y - cy) for v in me.vertices) or 1.0
    ob.shape_key_add(name="Basis")
    for name in ("swayX", "swayY", "flutter"):
        sk = ob.shape_key_add(name=name); sk.slider_min, sk.slider_max = -1.0, 1.0
        for i, v in enumerate(me.vertices):
            t = max(0.0, ((v.co.z - z0) / (z1 - z0) - still) / (1 - still))          # 0 at the planter, 1 at the crown
            r = math.hypot(v.co.x - cx, v.co.y - cy) / rmax
            leaf = t * min(1.0, max(0.0, (r - 0.1) / 0.35))                          # 0 on the trunk, 1 out on the fronds
            move = amp * (0.12 * t * t + 0.5 * leaf)                                  # the trunk barely leans, the fronds sway
            d = Vector(v.co)
            if name == "swayX": d.x += move
            elif name == "swayY": d.y += move
            else: d.z += 0.25 * amp * leaf * r                                       # outer fronds lift and droop a little
            sk.data[i].co = d
    cyc, ph = (1, 2, 1, 1, 2)[n % 5], rng.random()                  # slow: 4 to 8 s a sway
    for f in list(range(1, FRAMES + 1, 2)) + [FRAMES + 1]:           # frame 193 closes the loop
        a = 2 * math.pi * (cyc * (f - 1) / FRAMES + ph)
        for name, val in (("swayX", math.sin(a)), ("swayY", math.cos(a)), ("flutter", math.sin(4 * (f - 1) / FRAMES * 2 * math.pi + ph))):
            ob.data.shape_keys.key_blocks[name].value = val
            ob.data.shape_keys.key_blocks[name].keyframe_insert("value", frame=f)
    interp(ob.data.shape_keys.key_blocks["swayX"], "value", "LINEAR")

# ---- 4. people ----
pref.keyframe_new_interpolation_type = "CONSTANT"
for inst in [o for o in corner.objects if o.instance_collection and o.name.startswith(("Person_", "Character_"))]:
    if inst.instance_collection.name in ("Person_Diner", "Person_Edgerunner", "Person_Netrunner", "Person_Punk", "Person_Florist",
                                         "Person_Smoker", "Person_Reader", "Person_Sofa", "Person_PatioSit"):
        continue                                                    # seated, or moved by pose swaps below (the glancers get their bob there)
    period, ph, z = rng.choice((96, 64, 48)), rng.randint(0, 95), inst.location.z      # a voxel of breathing; periods divide 192
    for f in range(FRAMES):
        up = ((f + ph) // (period // 2)) % 2
        if f == 0 or up != ((f - 1 + ph) // (period // 2)) % 2:
            inst.location.z = z + 0.05 * up; inst.keyframe_insert("location", index=2, frame=f + 1)
    interp(inst, "location", "CONSTANT")
phone =next((o for o in corner.objects if o.name.startswith("Person_Phone")), None)
if phone:                                                           # the screen's glow flickers on his face
    ld = bpy.data.lights.new("phoneglow", "POINT"); ld.color = (0.3, 0.9, 1.0); ld.use_shadow = False; ld.shadow_soft_size = 0.1; ld.energy = 5
    lo_ = bpy.data.objects.new("phoneglow", ld); lo_.location = phone.location + Vector((0, 0, 1.1)); corner.objects.link(lo_)   # follows him (he moved to the lockers 2026-11-05)
    key_pattern([(0.5, 1.0, 1.0, 1.6)[(f // 6 * 7) % 4] for f in range(FRAMES)], [(ld, "energy", 5.0)])

# The couple on the lobby roof edge: she scoots over and leans her head to him, he turns and puts an arm around her,
# they hold it for a few seconds, then ease apart. Poses are the Person_NetrunnerL1/L2 and Person_EdgerunnerT/A variants.
# Each variant is an instance at the base one's matrix; they swap by visibility, and her scoot is keyed on all of hers.
def swap_poses(base, variants, stage, scoot=None, move=None):
    """Swap pose instances by visibility. build_mesh recentres every pose on its own footprint, so each variant is shifted by the
    difference of the centres (from vox_lo/vox_hi) and every unmoved voxel stays put (2026-11-05; before, a pose whose outline
    differed slid by half the difference). move: {variant: (x, y, z)} extra metres in the person's own frame (-y is forward)."""
    inst = next(o for o in corner.objects if o.instance_collection and o.instance_collection.name == base)
    objs = [inst]

    def centre(name):
        lo, hi = bpy.data.objects[name]["vox_lo"], bpy.data.objects[name]["vox_hi"]
        return Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    for vn in variants:
        e = bpy.data.objects.new(vn, None); e.instance_type = "COLLECTION"; e.instance_collection = bpy.data.collections[vn]
        shift = centre(vn) - centre(base) + Vector((move or {}).get(vn, (0, 0, 0)))
        e.matrix_world = inst.matrix_world @ Matrix.Translation(shift); corner.objects.link(e); objs.append(e)
    y0s, prev, prev_dy = [o.location.y for o in objs], None, None
    for f in range(1, FRAMES + 1):
        st = stage(f)
        if st != prev:
            for k, o in enumerate(objs):
                o.hide_render = k != st; o.keyframe_insert("hide_render", frame=f)
            prev = st
        if scoot and scoot(f) != prev_dy:
            prev_dy = scoot(f)
            for o, y0 in zip(objs, y0s):
                o.location.y = y0 + prev_dy; o.keyframe_insert("location", index=1, frame=f); interp(o, "location", "CONSTANT")
    return objs


def scoot(f):                                                        # metres toward him: seven 5 cm steps over, then back
    if f < 25: return 0.0
    if f < 150: return -0.05 * min(7, (f - 25) // 2 + 1)
    return -0.35 + 0.05 * min(7, (f - 150) // 2 + 1) if f < 165 else 0.0


pref.keyframe_new_interpolation_type = "CONSTANT"
# (stage 3 is a head turn away, in the gaps before and after the embrace)
swap_poses("Person_Netrunner", ["Person_NetrunnerL1", "Person_NetrunnerL2", "Person_NetrunnerG"],
           lambda f: 1 if 41 <= f <= 48 or 134 <= f <= 141 else 2 if 49 <= f <= 133 else 3 if 4 <= f <= 14 or 176 <= f <= 188 else 0, scoot)
swap_poses("Person_Edgerunner", ["Person_EdgerunnerT", "Person_EdgerunnerA", "Person_EdgerunnerG"],
           lambda f: 1 if 45 <= f <= 56 or 130 <= f <= 145 else 2 if 57 <= f <= 129 else 3 if 12 <= f <= 24 or 168 <= f <= 180 else 0)

CYCLE, SPEED = (0, 1, 2, 1), 0.085                                 # gait poses, metres a frame (about 2 m/s)


def route(start, steps, speed=SPEED):
    """Per-frame (x, y, yaw degrees, pose) for a walker from start: ("go", x, y) walks there and turns toward it
    (15 degrees a frame), ("wait", frames, yaw) stands and turns to face that way. -y is yaw 0 (the person's front).
    speed is metres a frame (the cats trot slower than people walk)."""
    x, y = start
    yaw, out, stride = None, [], 0

    def turn(want):
        d = (want - yaw + 180) % 360 - 180
        return yaw + max(-15, min(15, d))

    for step in steps:
        if step[0] == "go":
            dx, dy = step[1] - x, step[2] - y
            n, want = max(1, round(math.hypot(dx, dy) / speed)), math.degrees(math.atan2(dx, -dy))
            yaw = want if yaw is None else yaw
            for i in range(1, n + 1):
                yaw = turn(want); stride += 1
                out.append((x + dx * i / n, y + dy * i / n, yaw, CYCLE[(stride // 4) % 4]))
            x, y = step[1], step[2]
        else:
            yaw = step[2] if yaw is None else yaw
            for _ in range(step[1]):
                yaw = turn(step[2]); out.append((x, y, yaw, 1))
    return out


# Round trips: each walker leaves a doorway and goes back in through the same one, so the loop closes while they are
# out of sight, and being inside between visits makes sense.
# A leaves the net cafe, queues at the ramen stand, looks the cafe's window over on the way back, and goes in again.
# B leaves the lobby, stops to talk to the punk on the side street (who greets and nods), then goes back in.
WALKERS = (("A", (-2.5, -0.9), 0, [("go", -2.5, -2.4), ("go", -0.6, -2.4), ("wait", 30, 0), ("go", -5.0, -2.4), ("wait", 14, 180),
                                    ("go", -2.5, -2.4), ("go", -2.5, -0.9)]),
           ("B", (0.5, 3.8), 40, [("go", 2.2, 3.8), ("go", 2.2, 5.0), ("wait", 56, 158), ("go", 2.2, 3.8), ("go", 0.5, 3.8)]))
# B's wait begins at frame 40 + 20 + 14 = 74 and ends at 130; the punk's reactions are timed to it
PUNK = lambda f: 2 if 70 <= f <= 80 or 118 <= f <= 128 else 1 if 88 <= f <= 91 or 100 <= f <= 103 or 110 <= f <= 113 else 0
DINER = lambda f: (1 if 30 <= f <= 46 or 96 <= f <= 112 or 150 <= f <= 164 else 2 if 60 <= f <= 74 or 120 <= f <= 132
                   else 0 if f % 16 < 8 else 3)                     # between, the chopsticks go up to his mouth and down again
swap_poses("Person_Punk", ["Person_PunkN", "Person_PunkW"], PUNK)
swap_poses("Person_Diner", ["Person_DinerS", "Person_DinerG", "Person_DinerD"], DINER)
# the people around the floors (2026-11-05): the catwalk smoker draws on his cigarette (the still's pose) twice a loop and
# otherwise rests it on the rail; the library reader stands, stretches and sits back down once; the singer's mic light pulses
swap_poses("Person_Smoker", ["Person_SmokerL"], lambda f: 0 if 20 <= f <= 34 or 116 <= f <= 130 else 1)
READER = lambda f: 1 if 88 <= f <= 95 or 124 <= f <= 131 else 2 if 96 <= f <= 123 else 0
swap_poses("Person_Reader", ["Person_ReaderT", "Person_ReaderU"], READER,
           move={"Person_ReaderT": (0, -0.35, 0.15), "Person_ReaderU": (0, -0.35, 0.15)})   # up off the bench (seated feet sit 0.15 m low)
singer = next((o for o in corner.objects if o.instance_collection and o.instance_collection.name == "Person_Singer"), None)
if singer:
    ld = bpy.data.lights.new("micglow", "POINT"); ld.color = (1.0, 0.3, 0.8); ld.use_shadow = False; ld.shadow_soft_size = 0.1
    lo_ = bpy.data.objects.new("micglow", ld); lo_.location = singer.matrix_world @ Vector((0.0, -0.4, 1.45)); corner.objects.link(lo_)
    key_pattern([(1.0, 2.2, 1.4, 2.6)[(f // 6) % 4] for f in range(FRAMES)], [(ld, "energy", 6.0)])   # on the beat, 4 frames a step
# Head turns: a few seconds each, at different times so nobody turns together. Each pose copy gets the same breathing
# bob as its base (a copy without it would drop 5 cm while it shows).
GLANCES = {"Person_Florist": (["Person_FloristT", "Person_FloristL"], lambda f: 1 if 20 <= f <= 34 else 2 if 90 <= f <= 110 else 0)}
for base, (variants, stage) in GLANCES.items():
    objs = swap_poses(base, variants, stage)
    period, ph, z = rng.choice((96, 64, 48)), rng.randint(0, 95), objs[0].location.z
    for f in range(FRAMES):
        up = ((f + ph) // (period // 2)) % 2
        if f == 0 or up != ((f - 1 + ph) // (period // 2)) % 2:
            for o in objs:
                o.location.z = z + 0.05 * up; o.keyframe_insert("location", index=2, frame=f + 1); interp(o, "location", "CONSTANT")
for wid, start, off, steps in WALKERS:
    path = route(start, steps)
    assert len(path) <= FRAMES - 4, (wid, len(path))               # leave a few frames out of sight to close the loop
    p1 = bpy.data.objects[f"Person_Walk{wid}1"]
    lo, hi = Vector(p1["vox_lo"]), Vector(p1["vox_hi"])
    root = bpy.data.objects.new(f"walker{wid}", None); corner.objects.link(root)
    wl = bpy.data.lights.new("walklight", "POINT"); wl.energy = 40; wl.use_shadow = False; wl.shadow_soft_size = 0.3
    wl.color = (1.0, 0.5, 0.85) if wid == "A" else (0.5, 0.9, 1.0)   # a street-light spill that travels with them
    wo = bpy.data.objects.new("walklight", wl); wo.parent = root; wo.location = (0, 0, 1.4); corner.objects.link(wo)
    poses = []
    for k in range(3):
        e = bpy.data.objects.new(f"Person_Walk{wid}{k}", None)
        e.instance_type = "COLLECTION"; e.instance_collection = bpy.data.collections[f"Person_Walk{wid}{k}"]
        e.parent = root; e.location = (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z); corner.objects.link(e); poses.append(e)
    prev = None
    for f in range(FRAMES):
        t = (f - off) % FRAMES
        on = t < len(path)
        state = path[t][3] if on else -1
        if on:
            root.location = (snap(path[t][0]), snap(path[t][1]), 0.0)
            root.rotation_euler.z = math.radians(path[t][2])
            root.keyframe_insert("location", frame=f + 1); root.keyframe_insert("rotation_euler", index=2, frame=f + 1)
        if state != prev:
            for k, e in enumerate(poses):
                e.hide_render = k != state; e.keyframe_insert("hide_render", frame=f + 1)
            wl.energy = 0.0 if state == -1 else 40.0; wl.keyframe_insert("energy", frame=f + 1); interp(wl, "energy", "CONSTANT")
            prev = state

# The two street cats (2026-11-05): each trots a round trip and is back where it started on frame 192, so it is always in sight.
# The orange tabby lives on the florist balcony's top rail (x 1.1, z 3.15, above the HYDRO FLORA sign): it sits wagging its tail,
# licks a paw, walks 2 m along the rail, turns, walks back and sits again (poses 3 and 4 sit with the tail left and right, 5 licks).
# The calico patrols the side street in front of the florist and stops to look around. The corner script's still copy of each cat
# is hidden in the loop.
CAT_SPEED = 0.06
RX, RZ, R0, R1 = 1.1, 3.15, 10.8, 12.6                                             # at y 10.0 the gantry's pink post hid it


def rail_path():
    out = [(RX, R0, 0.0, 3 if (f // 6) % 2 == 0 else 4) for f in range(36)]                      # sit and wag
    out += [(RX, R0, 0.0, 5 if (f // 5) % 2 == 0 else 3) for f in range(30)]                     # lick, lick
    out += [(RX, R0, 30.0 * (k + 1), 1) for k in range(6)]                                       # turn to walk along +y
    out += [(RX, R0 + (R1 - R0) * (k + 1) / 50, 180.0, CYCLE[(k // 4) % 4]) for k in range(50)]
    out += [(RX, R1, 180.0 + 30.0 * (k + 1), 1) for k in range(6)]                               # turn back
    out += [(RX, R1 - (R1 - R0) * (k + 1) / 50, 360.0, CYCLE[(k // 4) % 4]) for k in range(50)]
    out += [(RX, R0, 360.0, 3 if (f // 6) % 2 == 0 else 4) for f in range(14)]                   # sit and wag till the loop wraps
    assert len(out) == FRAMES, len(out)
    return out


CATS = (("Orange", rail_path(), RZ, 6),
        ("Calico", route((1.6, 8.0), [("go", 1.6, 11.0), ("wait", 50, 270), ("wait", 20, 0), ("go", 1.6, 8.0)], CAT_SPEED), 0.0, 3))   # stops short of the parking meter, which hid her at y 12.4
for name, path, cz, npose in CATS:
    assert len(path) <= FRAMES, (name, len(path))
    path = path + [(path[0][0], path[0][1], path[-1][2], 1)] * (FRAMES - len(path))   # stand at the start until the loop wraps
    for o in corner.objects:
        if o.instance_collection and o.instance_collection.name.startswith(f"Cat_{name}") and o.parent is None:
            o.hide_render = True                                     # the still's copy
    root = bpy.data.objects.new(f"cat{name}", None); corner.objects.link(root)
    poses = []
    for k in range(npose):
        pk = bpy.data.objects[f"Cat_{name}{k}"]
        lo, hi = Vector(pk["vox_lo"]), Vector(pk["vox_hi"])
        e = bpy.data.objects.new(f"Cat_{name}{k}_walk", None)
        e.instance_type = "COLLECTION"; e.instance_collection = bpy.data.collections[f"Cat_{name}{k}"]
        e.parent = root; e.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)    # each pose's mesh was recentred on its own bounds
        corner.objects.link(e); poses.append(e)
    prev = None
    for f in range(FRAMES):
        x, y, yaw, state = path[f]
        root.location = (snap(x), snap(y), cz); root.rotation_euler.z = math.radians(yaw)
        root.keyframe_insert("location", frame=f + 1); root.keyframe_insert("rotation_euler", index=2, frame=f + 1)
        if state != prev:
            for k, e in enumerate(poses):
                e.hide_render = k != state; e.keyframe_insert("hide_render", frame=f + 1)
            prev = state

# Puddle ripples: a ring grows from a point in each ~0.8 m cell (Voronoi feature point), radius stepped in 5 cm voxels,
# fading as it spreads. Only where the road is wet (the puddle roughness ramp is low). Cells start at random phases,
# 3 drops per cell per loop, so the pattern repeats exactly every 192 frames. Bump (normals) only: it moves the reflections.
RIPPLE_CYCLES, RIPPLE_STEPS, RIPPLE_MAX = 3, 7, 0.75    # the frame is about 3 cm a pixel, so smaller rings are lost
for m in bpy.data.materials:
    if not m.name.startswith("M_Roads"): continue
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    wet = b.inputs["Roughness"].links[0].from_socket                    # the puddle ramp the looks script added
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.voronoi_dimensions = "2D"; vor.inputs["Scale"].default_value = 0.55
    pos = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    nt.links.new(pos, vor.inputs["Vector"])
    phase = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vor.outputs["Color"], phase.inputs[0])
    p = mn(nt, "FRACT", mn(nt, "ADD", mn(nt, "MULTIPLY", drive(nt, "(frame - 1) / 192"), RIPPLE_CYCLES), phase.outputs["Red"]))
    r = mn(nt, "MULTIPLY", mn(nt, "DIVIDE", mn(nt, "FLOOR", mn(nt, "MULTIPLY", p, RIPPLE_STEPS)), RIPPLE_STEPS), RIPPLE_MAX)
    d = mn(nt, "ABSOLUTE", mn(nt, "SUBTRACT", vor.outputs["Distance"], r))
    ring = mn(nt, "MAXIMUM", mn(nt, "SUBTRACT", 1.0, mn(nt, "MULTIPLY", d, 6.0)), 0.0)    # a ridge about 15 cm either side of the radius
    h = mn(nt, "MULTIPLY", mn(nt, "MULTIPLY", ring, mn(nt, "SUBTRACT", 1.0, p)), mn(nt, "LESS_THAN", wet, 0.3))
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 0.1
    nt.links.new(h, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # a dark puddle reflects almost nothing, so the tilt alone does not show: the ring also catches a little cool light
    b.inputs["Emission Color"].default_value = (0.45, 0.6, 1.0, 1)
    nt.links.new(mn(nt, "MULTIPLY", h, 0.1), b.inputs["Emission Strength"])

# ---- check ----
for fr in (30, 34, 100):
    s.frame_set(fr)
    print("MOTION alpha", fr, {n: round(bpy.data.materials[n].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value, 2)
                               for n in ("flash_l", "flash_r", "eye_white", "eye_iris", "pupil_a", "mouth_open", "lens_glow") if n in bpy.data.materials})

# ---- render ----
if len(args) >= 2:
    s.frame_start, s.frame_end = int(args[0]), int(args[1])
    s.render.image_settings.media_type = "IMAGE"; s.render.image_settings.file_format = "PNG"
    s.render.filepath = os.path.join(VAULT, "_attachments", "previews", "night-shift-3d-motion-")
else:
    s.render.image_settings.media_type = "VIDEO"; s.render.image_settings.file_format = "FFMPEG"
    s.render.ffmpeg.format = "WEBM"; s.render.ffmpeg.codec = "WEBM"; s.render.ffmpeg.constant_rate_factor = "MEDIUM"
    s.render.image_settings.color_mode = "RGB"
    s.render.filepath = os.path.join(VAULT, "_attachments", "scenes", "night-shift-3d-loop.webm")
_n = s.frame_end - s.frame_start + 1
# one "frame N/TOTAL" line per frame, so the task-eta mod (and any log reader) knows the size from the first frame
bpy.app.handlers.render_post.append(lambda sc, *_: print(f"MOTION frame {sc.frame_current - s.frame_start + 1}/{_n}", flush=True))
print(f"MOTION frame 0/{_n}", flush=True)
bpy.ops.render.render(animation=True)
print("MOTION rendered", s.render.filepath, s.frame_start, s.frame_end)


def strip_tags(path):
    """Blender writes the .blend's full local path and the render date into the webm's tags; the public repo must not carry them.
    Rewrites the file with all metadata dropped (stream copy, no re-encode). ffmpeg: Gyan.FFmpeg from winget (2026-11-05); a Blender
    started from a shell opened before that install has no ffmpeg on PATH, so the winget package folder is searched too."""
    import glob, os, shutil, subprocess
    exe = shutil.which("ffmpeg") or next(iter(sorted(glob.glob(os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\*\bin\ffmpeg.exe")), reverse=True)), None)
    if not exe:
        print("MOTION tags NOT stripped: ffmpeg not found"); return
    tmp = path + ".clean.webm"
    r = subprocess.run([exe, "-v", "error", "-y", "-i", path, "-map", "0", "-c", "copy", "-map_metadata", "-1", "-map_chapters", "-1",
                        "-fflags", "+bitexact", tmp], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        print("MOTION tags NOT stripped:", r.stderr.strip()[-300:]); return
    os.replace(tmp, path)
    print("MOTION tags stripped", path)


if len(args) < 2:
    strip_tags(s.render.filepath)
