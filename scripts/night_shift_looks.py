# Cyberpunk lighting looks for the corner. One look per run, renders only (does not save the .blend):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-corner.blend --python scripts/night_shift_looks.py -- a
# Writes _attachments/previews/night-shift-3d-look-<a|b|c|d>.png. Looks: a neon rain, b violet haze, c sodium and teal,
# d = b with a's rain (the chosen look).
import bpy, sys, math, random, os
from mathutils import Vector

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...

LOOK = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "a"  # "-- b anim [first last]" renders the loop instead
LOOKS = {
    "a": dict(world=(0.004, 0.006, 0.02), moon=((0.5, 0.6, 1.0), 0.15), fog=((0.35, 0.4, 0.7), 0.012), rain=4000,
              windows=4.0, neon=6.0, wet=0.75, bloom=0.9,
              lights=[((-2.6, -4.0, 4.6), (1.0, 0.15, 0.7), 1800, 3.0), ((2.4, 8.4, 3.4), (0.1, 0.9, 1.0), 1500, 3.0),
                      ((-3.2, -2.5, 9.5), (0.2, 0.35, 1.0), 2500, 4.0), ((-10, -3, 3), (0.6, 0.1, 1.0), 1200, 4.0),
                      ((3.0, 2.0, 2.5), (1.0, 0.2, 0.5), 900, 2.5)]),
    "b": dict(world=(0.035, 0.012, 0.06), moon=((0.7, 0.4, 1.0), 0.25), fog=((0.55, 0.25, 0.85), 0.035), rain=0,
              windows=3.6, neon=5.0, wet=0.45, bloom=1.0,   # brighter sky, moon and windows (Andres: edges too dark)
              lights=[((3.0, -4.5, 4.6), (1.0, 0.1, 0.8), 2200, 3.0), ((2.4, 10.4, 3.4), (0.1, 1.0, 1.0), 1600, 3.0),
                      ((-3.2, -2.5, 9.5), (0.5, 0.2, 1.0), 2500, 4.0), ((-10, -3, 3), (1.0, 0.1, 0.6), 1500, 4.0),
                      ((3.0, 2.0, 2.5), (0.6, 0.2, 1.0), 1000, 2.5)]),
    "c": dict(world=(0.003, 0.012, 0.015), moon=((0.4, 0.9, 0.9), 0.2), fog=((0.3, 0.55, 0.55), 0.008), rain=2000,
              windows=3.5, neon=5.0, wet=0.8, bloom=0.8,
              lights=[((-6.0, -3.6, 4.0), (1.0, 0.45, 0.1), 1600, 2.0), ((1.0, -3.6, 4.0), (1.0, 0.45, 0.1), 1600, 2.0),
                      ((2.4, 4.0, 4.0), (1.0, 0.45, 0.1), 1400, 2.0), ((2.4, 11.0, 4.0), (1.0, 0.45, 0.1), 1400, 2.0),
                      ((-3.2, -2.5, 9.5), (0.1, 0.8, 0.8), 1500, 4.0)]),
}
LOOKS["d"] = {**LOOKS["b"], "rain": LOOKS["a"]["rain"]}  # Andres's pick, 2026-11-03: violet haze with neon-rain rain
L = LOOKS[LOOK]
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.eevee.taa_render_samples = 64
s.eevee.use_raytracing = True
s.eevee.ray_tracing_method = "SCREEN"
s.eevee.use_shadows = True
s.eevee.shadow_pool_size = "1024"  # the default 512 MB pool overflows with this many lights and instances
s.eevee.use_volumetric_shadows = True
s.eevee.volumetric_tile_size = "4"
s.eevee.use_volume_custom_range = True  # ortho camera sits 300 m out; only march the slab the city occupies
s.eevee.volumetric_start, s.eevee.volumetric_end = 260, 340
try:
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Punchy"
except TypeError:
    print("LOOK fallback", s.view_settings.view_transform, s.view_settings.look)

# world and moonlight
s.world.use_nodes = True
bg = s.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (*L["world"], 1); bg.inputs["Strength"].default_value = 1.0
sun = bpy.data.objects["sun"]
sun.data.color, sun.data.energy = L["moon"]
sun.rotation_euler = (math.radians(35), 0, math.radians(-60))

# glow: windows and kit emissive maps, plus the ramen stand's neon
for m in bpy.data.materials:
    b = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if b and b.inputs["Emission Color"].links:
        b.inputs["Emission Strength"].default_value = L["neon"] if m.name.startswith(("RamenStand", "Shop_", "Patio_", "Person_", "Beacon", "Roof_", "Plant_")) or "GLOSSY" in m.name.upper() else L["windows"]
    if b and m.name.startswith("M_Buildings") and b.inputs["Emission Color"].links:
        # the atlas lights every window plain white; tint per building copy (amber, cool white, pink)
        nt = m.node_tree
        info = nt.nodes.new("ShaderNodeObjectInfo")
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.0, (1.0, 0.62, 0.3, 1)
        e[1].position, e[1].color = 0.55, (0.75, 0.9, 1.0, 1)
        e.new(0.85).color = (1.0, 0.45, 0.75, 1)
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
        nt.links.new(info.outputs["Random"], ramp.inputs["Fac"])
        nt.links.new(b.inputs["Emission Color"].links[0].from_socket, mul.inputs["A"])
        nt.links.new(ramp.outputs["Color"], mul.inputs["B"])
        nt.links.new(mul.outputs["Result"], b.inputs["Emission Color"])

# wet street: world-space noise puddles on the road and sidewalk material
for m in bpy.data.materials:
    if m.name.startswith("M_Roads"):
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.35; noise.inputs["Detail"].default_value = 3
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.5 - L["wet"] * 0.2; ramp.color_ramp.elements[0].color = (0.04, 0.04, 0.04, 1)  # puddle roughness
        ramp.color_ramp.elements[1].position = 0.6 - L["wet"] * 0.2; ramp.color_ramp.elements[1].color = (0.5, 0.5, 0.5, 1)
        nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Roughness"])
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 0.45
        nt.links.new(b.inputs["Base Color"].links[0].from_socket, mul.inputs["A"])
        mul.inputs["B"].default_value = (0.35, 0.38, 0.5, 1)  # wet asphalt is darker and cooler
        nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
        b.inputs["Specular IOR Level"].default_value = 0.8

# coloured neon lights, one on the hex tower roof, and one inside each storefront (repair, mart, net cafe, florist)
SHOP_LIGHTS = [((-4.5, 4.5, 17.5), (0.3, 1.0, 0.8), 400, 2.0),
               ((-8, 0.6, 2.2), (1.0, 0.6, 0.3), 150, 1.5), ((-13, 0.6, 2.2), (0.85, 0.95, 1.0), 220, 2.5),
               ((-3.0, 0.6, 2.2), (1.0, 0.28, 0.12), 190, 2.5), ((-3.0, 0.6, 5.0), (0.6, 0.3, 1.0), 260, 2.5),     # ramen shop (red-orange); net cafe loft, lower floor
               ((-0.8, 5.4, 4.3), (1.0, 0.4, 0.9), 200, 3.0),                                                    # the arcade, magenta (shadows off)
               ((-3.0, 0.6, 7.5), (0.5, 0.35, 1.0), 220, 2.5), ((-0.6, 11.4, 2.2), (1.0, 0.35, 0.85), 200, 2.5),
               ((1.0, 11.4, 3.6), (1.0, 0.75, 0.45), 150, 2.5),                                    # warm light on the balcony
               ((-0.6, 5.4, 2.2), (0.85, 0.3, 1.0), 200, 2.5),                                     # inside the hobby store
               ((-13.0, 0.5, 1.7), (0.95, 1.0, 1.0), 1100, 4.0), ((-13.0, -1.2, 3.0), (0.2, 0.9, 0.5), 200, 3.0),   # the konbini's white light spilling out; green fascia wash
               ((-11.4, -1.5, 1.2), (0.95, 1.0, 1.0), 260, 3.0),                                   # a white pool in front of the door
               # the library's eight lights moved with it (the corner's LIB_DX -0.5, LIB_DY -1.0, 2026-11-05)
               ((-1.0, 18.4, 1.7), (1.0, 0.72, 0.32), 900, 4.0), ((1.3, 18.4, 0.9), (1.0, 0.7, 0.35), 320, 4.0),   # the library hall, from inside the great doors; gold over the runner
               ((-1.1, 18.4, 5.6), (0.65, 0.35, 1.0), 520, 4.0), ((1.1, 18.4, 8.6), (0.3, 0.9, 1.0), 360, 3.0),     # behind the stained glass; cyan on the gable
               ((0.6, 15.2, 2.65), (1.0, 0.7, 0.35), 110, 0.6), ((0.6, 21.6, 2.65), (1.0, 0.7, 0.35), 110, 0.6),   # the two tower lanterns
               ((1.1, 16.2, 6.0), (1.0, 0.75, 0.4), 220, 3.0), ((1.1, 20.6, 6.0), (1.0, 0.75, 0.4), 220, 3.0),     # gold rim on each tower
               ((-17.4, -1.2, 2.4), (0.3, 0.9, 1.0), 90, 1.5),                                     # the lockers' lit header (lockers left of the mart since 2026-11-05)
               ((-0.8, 11.4, 6.3), (1.0, 0.3, 0.8), 260, 2.5),                                     # inside the karaoke bar, pink (shadows off)
               ((1.8, 11.4, 9.2), (1.0, 0.5, 0.85), 260, 3.0),                                     # a wash on the bunny girl over the karaoke (shadows off)
               ((-8.0, -1.0, 12.0), (0.45, 0.8, 1.0), 320, 2.5),                                   # the repair roof's AC units and cabinets, cool (shadows off)
               ((1.9, 11.7, 3.9), (1.0, 0.6, 0.3), 70, 1.2)]                                       # warm on the tabby's stretch of balcony rail, against the lime sign (shadows off)
# the outer and upper parts of the frame: two street lamps (heads at 5.3 m) and colour washes on the far facades
OUTER_LIGHTS = [((-15.5, -4.5, 5.2), (0.7, 0.85, 1.0), 700, 0.8), ((4.5, 14.6, 5.2), (0.7, 0.85, 1.0), 700, 0.8),
                ((4.5, 23.0, 5.2), (0.7, 0.85, 1.0), 700, 0.8),
                ((-10.25, -0.7, 1.5), (0.5, 0.85, 1.0), 120, 0.5),                               # ATM glow (the one on the mart's right pier)
                ((1.6, 6.3, 9.4), (0.8, 0.6, 1.0), 160, 1.5),                                   # the pair on the lobby roof
                ((-14, -4.0, 10.0), (1.0, 0.2, 0.7), 1600, 5.0), ((-22, -3.0, 6.0), (0.3, 0.6, 1.0), 1300, 5.0),
                ((3.0, 19.0, 8.0), (0.6, 0.3, 1.0), 1600, 5.0), ((14, -3.0, 6.0), (0.2, 0.9, 0.9), 1100, 4.0),
                ((-5.0, 2.0, 15.0), (0.4, 0.5, 1.0), 1400, 5.0)]
SHOP_LIGHTS += OUTER_LIGHTS
for i, (pos, col, watts, size) in enumerate(L["lights"] + SHOP_LIGHTS):
    ld = bpy.data.lights.new(f"neon_{i}", "AREA"); ld.color = col; ld.energy = watts; ld.size = size
    if (pos[:2] == (-3.0, 0.6) and pos[2] > 4) or pos in ((-0.8, 5.4, 4.3), (-0.8, 11.4, 6.3), (1.8, 11.4, 9.2), (-8.0, -1.0, 12.0), (1.9, 11.7, 3.9)) or (15 < pos[1] < 22 and -1.5 < pos[0] < 1.5) or (-14 < pos[0] < -11 and pos[1] < 1 and pos[2] < 3.1 and pos != (-13, 0.6, 2.2)):   # the library's lights: shadows off, as in the concept
        ld.use_shadow = False  # the net cafe loft's two interior glows: with them shadowed the shadow buffer overflows (4256 of 4096)
    if size >= 5.0:
        ld.use_shadow = False  # the big distant colour washes: the towers and new floors (2026-11-05) pushed the buffer to 4265 of 4096 again
    lo = bpy.data.objects.new(f"neon_{i}", ld); lo.location = pos
    target = Vector((pos[0] - 1.5 if pos[0] > 0 else pos[0], pos[1] + 2.5 if pos[1] < 0 else pos[1], 0.5))
    lo.rotation_euler = (target - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    s.collection.objects.link(lo)

# fog: a volume box around the corner
bpy.ops.mesh.primitive_cube_add(size=1, location=(-2, 3, 10))
fog = bpy.context.active_object; fog.name = "fog"; fog.scale = (70, 70, 22)
fm = bpy.data.materials.new("fog"); fnt = fm.node_tree
fnt.nodes.remove(fnt.nodes["Principled BSDF"])
vol = fnt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (*L["fog"][0], 1); vol.inputs["Density"].default_value = L["fog"][1]
fnt.links.new(vol.outputs["Volume"], fnt.nodes["Material Output"].inputs["Volume"])
fog.data.materials.append(fm)

# rain: camera-facing streaks in one mesh
cam = s.camera
right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
R = random.Random(7)
verts, faces = [], []
for i in range(L["rain"]):
    p = Vector((R.uniform(-14, 10), R.uniform(-10, 16), R.uniform(0, 16)))
    down = Vector((0.04, 0.02, -1)).normalized() * R.uniform(0.35, 0.7)
    w = right * 0.012
    k = len(verts); verts += [p - w, p + w, p + w + down, p - w + down]; faces.append((k, k + 1, k + 2, k + 3))
if verts:
    rm = bpy.data.meshes.new("rain"); rm.from_pydata(verts, [], faces)
    ro = bpy.data.objects.new("rain", rm); s.collection.objects.link(ro)
    mat = bpy.data.materials.new("rain"); b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.7, 0.8, 1, 1); b.inputs["Alpha"].default_value = 0.18
    b.inputs["Emission Color"].default_value = (0.6, 0.75, 1, 1); b.inputs["Emission Strength"].default_value = 0.25
    mat.surface_render_method = "BLENDED"
    rm.materials.append(mat)

# bloom in the compositor (Blender 5: a node group on the scene)
ng = bpy.data.node_groups.new("post", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = ng.nodes.new("CompositorNodeRLayers")
gl = ng.nodes.new("CompositorNodeGlare")
gl.inputs["Type"].default_value = "Bloom"; gl.inputs["Quality"].default_value = "High"
gl.inputs["Threshold"].default_value = 1.0; gl.inputs["Strength"].default_value = L["bloom"]; gl.inputs["Size"].default_value = 0.7
out = ng.nodes.new("NodeGroupOutput")
ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], out.inputs["Image"])
s.compositing_node_group = ng

if "anim" in sys.argv:  # the 8 s loop: night_shift_motion.py adds the motion and renders the video (or a test range)
    exec(compile(open(os.path.join(VAULT, "scripts", "night_shift_motion.py")).read(), "night_shift_motion.py", "exec"))
    sys.exit(0)
s.render.filepath = os.path.join(VAULT, "_attachments", "previews", f"night-shift-3d-look-{LOOK}.png")
print("VIEW", s.view_settings.view_transform, s.view_settings.look)
bpy.ops.render.render(write_still=True)
print("RENDERED", s.render.filepath)
if LOOK == "b":  # the dashboard scene is d without baked rain; night_shift_rain.py lays moving rain over it
    import shutil
    shutil.copy(s.render.filepath, os.path.join(VAULT, "_attachments", "scenes", "night-shift-3d.png"))
    print("SCENE", r"_attachments\scenes\night-shift-3d.png")
