# Seamless rain and steam loop to lay over the dashboard still (look b). Run on the corner:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-corner.blend --python scripts/night_shift_rain.py
# Renders only the rain on a transparent background; the corner renders as holdout, so buildings still hide
# the rain behind them. Writes _attachments/scenes/night-shift-3d-rain.mp4 (H.264 on black, 48 frames, 24 fps). Not alpha
# VP9: that decodes in software, about 35% of a core, where H.264 and the loop's VP9 decode on the GPU (2026-11-04 test).
import bpy, random, time, os
from mathutils import Vector, Matrix

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
Matrix_T = Matrix.Translation

OUT = os.path.join(VAULT, "_attachments", "scenes", "night-shift-3d-rain.mp4")
FRAMES, BAND, COUNT = 48, 16.0, 4400  # the layer falls one BAND per loop, so frame 49 == frame 1
WIND = 0.35  # sideways metres per metre of fall, toward screen left: about 22 degrees off vertical on screen
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.eevee.taa_render_samples = 8
s.render.film_transparent = True
s.view_settings.view_transform = "AgX"
s.view_settings.look = "AgX - Punchy"
s.compositing_node_group = None
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == "corner":
        lc.holdout = True

# streaks: same spread, size and material as night_shift_looks.py, generated in one band and repeated 3 times
cam = s.camera
right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
flat_right = Vector((right.x, right.y, 0)).normalized()
fall = Vector((0, 0, -1)) - flat_right * WIND          # per metre of drop: down and toward screen left
step = -fall * BAND                                     # one band up the slant; copies stack along it
R = random.Random(7)
verts, faces = [], []
# wider spread than the view: the layer slides BAND * WIND sideways per loop
band = [(Vector((R.uniform(-20, 16), R.uniform(-16, 22), R.uniform(0, BAND))), R.uniform(0.35, 0.7)) for _ in range(COUNT)]
for k in range(3):
    for p, ln in band:
        p = p + step * k
        down = fall.normalized() * ln
        w = right * 0.03  # wide enough to stay one solid pixel at half resolution
        i = len(verts); verts += [p - w, p + w, p + w + down, p - w + down]; faces.append((i, i + 1, i + 2, i + 3))
me = bpy.data.meshes.new("rain"); me.from_pydata(verts, [], faces)
ro = bpy.data.objects.new("rain", me); s.collection.objects.link(ro)
mat = bpy.data.materials.new("rain"); b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.7, 0.8, 1, 1); b.inputs["Alpha"].default_value = 0.18
b.inputs["Emission Color"].default_value = (0.6, 0.75, 1, 1); b.inputs["Emission Strength"].default_value = 0.25
mat.surface_render_method = "BLENDED"
me.materials.append(mat)
# slide one band down the slant over FRAMES frames; simple-expression drivers need no Python auto-run
for axis in range(3):
    d = ro.driver_add("location", axis).driver
    d.type = "SCRIPTED"; d.expression = f"-(frame - 1) * {step[axis] / FRAMES:.6f}"

# steam: chunky voxel puffs rising from every steam source the corner placed (ramen pots, sewer grates, roof
# vents). Each puff lives one loop, phases are staggered, and a puff is invisible when it wraps, so the loop is
# seamless. Positions and sizes snap to the 5 cm voxel grid and keys are constant, so puffs step like pixel art.
import bmesh, math
bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
bm = bmesh.new()
for (ox, oy, oz) in ((0, 0, 0), (0.5, 0, 0.2), (-0.4, 0.3, 0.1), (0.1, -0.4, 0.35), (0, 0.2, 0.55)):
    bmesh.ops.create_cube(bm, size=0.6, matrix=Matrix_T((ox, oy, oz)))
puff_me = bpy.data.meshes.new("puff"); bm.to_mesh(puff_me); bm.free()
pm = bpy.data.materials.new("steam"); nt = pm.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
info, em, tr, mix = (nt.nodes.new(t) for t in ("ShaderNodeObjectInfo", "ShaderNodeEmission", "ShaderNodeBsdfTransparent", "ShaderNodeMixShader"))
em.inputs["Color"].default_value = (0.74, 0.66, 1.0, 1); em.inputs["Strength"].default_value = 1.2   # violet, like the haze
nt.links.new(info.outputs["Alpha"], mix.inputs["Fac"]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
pm.surface_render_method = "BLENDED"
puff_me.materials.append(pm)
snap = lambda v, g=0.05: round(v / g) * g
SR = random.Random(11)
sources = [o for o in bpy.data.objects if "steam" in o]
for src in sources:
    size = src["steam"]
    # each source keeps its own rhythm: 1 to 3 puff cycles per loop (whole numbers keep the loop seamless), its own
    # puff count, and a breathing strength that swells and fades once per loop from its own starting point
    cycles, K, breath = SR.choice((1, 2, 2, 3)), SR.randint(4, 11), SR.random()
    for i in range(K):
        phase, ox, oy = i / K + SR.uniform(-0.05, 0.05), SR.uniform(-0.12, 0.12), SR.uniform(-0.12, 0.12)
        grow = SR.uniform(0.6, 1.5)                          # some puffs small and quick, some big and lazy
        rise = SR.uniform(1.2, 2.2) / cycles ** 0.5
        ob = bpy.data.objects.new("puff", puff_me); ob.visible_shadow = False; s.collection.objects.link(ob)
        for f in range(1, FRAMES + 1):
            g = (f - 1) / FRAMES
            u = (g * cycles + phase) % 1
            p = src.location + Vector((ox, oy, rise * size * u)) - flat_right * (0.45 * size * u)
            p.x += 0.07 * math.sin(2 * math.pi * (2 * u + i / K))
            ob.location = [snap(c) for c in p]
            ob.scale = [max(snap(size * grow * (0.18 + 0.5 * u)), 0.05)] * 3
            swell = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(2 * math.pi * (g + breath)))
            ob.color = (1, 1, 1, min(1, u / 0.1) * (1 - u) ** 1.2 * 0.65 * swell)
            for path in ("location", "scale", "color"):
                ob.keyframe_insert(path, frame=f)
print("STEAM", len(sources), "sources")

# half resolution, shown scaled up with pixelated edges: chunkier streaks that suit the voxels, and a
# quarter of the pixels to decode (full-res diagonal rain cost 123% of one core in Obsidian)
s.render.resolution_percentage = 50
s.frame_start, s.frame_end = 1, FRAMES
s.render.fps = 24
s.render.image_settings.media_type = "VIDEO"
s.render.image_settings.file_format = "FFMPEG"
s.render.ffmpeg.format = "MPEG4"
s.render.ffmpeg.codec = "H264"
s.render.image_settings.color_mode = "RGB"      # rain over black: the dashboard lays it with mix-blend-mode: screen
s.render.ffmpeg.constant_rate_factor = "HIGH"
s.render.filepath = OUT
t0 = time.time()
bpy.ops.render.render(animation=True)
print("RAIN", OUT, f"{time.time() - t0:.1f}s for {FRAMES} frames")
s.frame_set(24)                                         # one frame as a PNG, to check the overlay without a player
s.render.image_settings.media_type = "IMAGE"; s.render.image_settings.file_format = "PNG"
s.render.filepath = os.path.join(VAULT, "_attachments", "previews", "night-shift-3d-overlay-frame.png")
bpy.ops.render.render(write_still=True)
