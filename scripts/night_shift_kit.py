# Run: "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python scripts/night_shift_kit.py
# Imports the three Cyberpunk packs into projects/night-shift-3d/night-shift-kit.blend (one collection per model,
# materials fixed) and renders one contact sheet per pack into _attachments/previews/.
import bpy, os, math, re
from mathutils import Vector, Matrix, Euler

ROOT = os.environ.get("NIGHT_SHIFT_PACKS") or os.path.join(os.path.expanduser("~"), "Downloads", "Cyberpunk Assets")   # the bought asset packs (never committed)
CITY = ROOT + r"\Cyberpunk City\FreeSample"
TX = CITY + "\\Textures\\"
VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
BLEND = VAULT + r"\projects\night-shift-3d\night-shift-kit.blend"
PREVIEWS = VAULT + r"\_attachments\previews"
CITY_MODELS = ["Advertising_5", "Advertising_6", "Advertising_7", "SateliteDish", "BuildingBlock_1", "BuildingBlock_2",
               "Building_3", "BuildingBlock_18", "BuildingBlock_19", "BuildingBlock_24", "Road_Chunk_5",
               "Sidewalk_Chunk_2", "Sidewalk_Tile_1"]
# Streets: the bought base pack (one FBX per model, 382 of them) replaces the free sample, which is a subset of it
STREETS = ROOT + r"\Voxel Cyberpunk Streets - BASE PACK\FBX"
PACKS = {"streets": sorted(os.path.join(STREETS, f) for f in os.listdir(STREETS) if f.lower().endswith(".fbx")),
         "b06": [ROOT + r"\Buildings\Free Sample\Building_06.fbx"],
         "chars": [ROOT + r"\CBP_character_sample\FreeSample\CyberpunkChar_0.fbx"]}
TEXDIRS = [TX, STREETS + "\\Texture\\", ROOT + "\\CBP_character_sample\\FreeSample\\"]
# contact sheets: the streets pack is split by family so the labels stay readable
SHEETS = {"streets-build": ("BuildingModule", "Entrance", "Door", "Awning", "GarageDoor", "Block", "TrimPiece", "Fence",
                            "Curtain", "Bar", "PavementTile", "GroundTile", "SewerGrid", "LightPole"),
          "streets-signs": ("Billboard", "Neon", "Screen", "TV")}


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes, seen = [], set()
    for o in new:
        if o.type == "MESH" and o.data not in seen:  # later objects sharing a mesh are placed instances, not new models
            seen.add(o.data); meshes.append(o)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)  # bake the importer's Y-up conversion and scale into the mesh, so every model is Z-up at scale 1
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o not in meshes:
            bpy.data.objects.remove(o)
    return meshes


def rebase(o):
    # Streets and Building_06 modules are centred on their origin; put the base on z=0, centred in x/y
    lo = Vector([min(v.co[i] for v in o.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in o.data.vertices) for i in range(3)])
    o.data.transform(Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))


def fix_material(m):
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            n.interpolation = "Closest"  # texel atlases: linear filtering blends neighbouring colour patches
            if n.image.size[0] == 0:  # a texture path from the artist's machine; City ships its maps as "- 4K" copies
                base = os.path.basename(n.image.filepath.replace("\\", "/"))
                for cand in [d + nm for d in TEXDIRS for nm in (base, base.replace(".png", "- 4K.png"))]:
                    if os.path.exists(cand):
                        n.image.filepath = cand; n.image.reload(); break
                assert n.image.size[0] > 0, n.image.filepath
    b.inputs["Metallic"].default_value = 0.0
    emissive = bool(b.inputs["Emission Color"].links)
    if not emissive:
        b.inputs["Emission Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0 if emissive else 0.0
    name = m.name.upper()
    if "GLASS" in name:
        for l in list(b.inputs["Emission Color"].links):
            nt.links.remove(l)
        b.inputs["Emission Strength"].default_value = 0.0
        b.inputs["Roughness"].default_value = 0.05
        b.inputs["Alpha"].default_value = 0.35
        for l in list(b.inputs["Alpha"].links):
            nt.links.remove(l)
        m.surface_render_method = "BLENDED"
    elif "GLOSSY" in name:
        b.inputs["Roughness"].default_value = 0.15


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib = {}
    for name in CITY_MODELS:
        (o,) = import_fbx(CITY + "\\" + name + ".fbx")
        o.name = name
        lib.setdefault("city", []).append(o)
    for pack, paths in PACKS.items():
        for path in paths:
            for o in import_fbx(path):
                if pack != "chars":  # the character is one rigid voxel part per bone: keep the parts where they sit
                    rebase(o)
                o.name = re.sub(r"\.\d+$", "", o.name)
                lib.setdefault(pack, []).append(o)
    for m in bpy.data.materials:
        fix_material(m)
    for pack, obs in lib.items():
        parent = bpy.data.collections.new("kit_" + pack)
        bpy.context.scene.collection.children.link(parent)
        for o in obs:
            c = bpy.data.collections.get("CyberpunkChar_0") if pack == "chars" else None
            if not c:
                c = bpy.data.collections.new("CyberpunkChar_0" if pack == "chars" else o.name)
                parent.children.link(c)
            for uc in o.users_collection:
                uc.objects.unlink(o)
            c.objects.link(o)
    for sc in bpy.data.screens:  # open in Material Preview so the textures show, not Solid grey
        for a in sc.areas:
            if a.type == "VIEW_3D":
                a.spaces.active.shading.type = "MATERIAL"
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("SAVED", BLEND, {k: len(v) for k, v in lib.items()})
    return lib


ISO = Euler((math.radians(60), 0, math.radians(45)))  # 2:1 pixel iso in a true ortho camera: 30 degree elevation, 45 round


def sheet(pack, obs, y0):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.view_settings.view_transform = "Standard"  # show the atlas colours as painted
    s.render.resolution_x, s.render.resolution_y = 2400, 1500
    s.world = s.world or bpy.data.worlds.new("w")
    s.world.color = (0.12, 0.12, 0.14)
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3; sun.rotation_euler = Euler((math.radians(50), 0, math.radians(-30)))
        s.collection.objects.link(sun)
    for p, o in enumerate(o for c in s.collection.children for o in c.all_objects):
        o.hide_render = o not in obs
    # lay models out in rows along x, wrapping by total width
    sizes = [(o, max(o.dimensions.x, o.dimensions.y)) for o in obs]
    row_w = max(sum(w for _, w in sizes) / 3, max(w for _, w in sizes))
    x = 0.0; y = y0; row_h = 0.0; labels = []
    for o, w in sizes:
        if x > 0 and x + w > row_w:
            x = 0; y -= row_h + 2; row_h = 0
        cx = sum(c[0] for c in o.bound_box) / 8; cy = sum(c[1] for c in o.bound_box) / 8  # City origins sit on a corner
        o.location = (x + w / 2 - cx, y - cy, 0)
        o.users_collection[0].instance_offset = o.location  # instancing the collection still places the model at its own origin
        row_h = max(row_h, w)
        t = bpy.data.objects.new("lbl_" + o.name, bpy.data.curves.new("lbl_" + o.name, "FONT"))
        t.data.body = o.name; t.data.size = 0.35; t.data.align_x = "CENTER"
        t.location = (x + w / 2, y - w / 2 - 0.6, 0.01)
        bpy.data.collections["kit_" + pack.split("-")[0]].objects.link(t); labels.append(t)
        x += w + 1.5
    bpy.context.view_layer.update()  # matrix_world is stale after setting location until the depsgraph updates
    pts = [o.matrix_world @ Vector(c) for o in obs + labels for c in o.bound_box]
    cam = bpy.data.objects.get("cam") or bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    if cam.name not in s.collection.objects:
        s.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.rotation_euler = ISO
    rot = ISO.to_matrix()
    local = [rot.transposed() @ p for p in pts]
    xs, ys = [p.x for p in local], [p.y for p in local]
    centre = rot @ Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0))
    cam.location = centre + rot @ Vector((0, 0, 200))
    cam.data.clip_end = 1000
    cam.data.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * 2400 / 1500) * 1.05
    s.camera = cam
    s.render.filepath = os.path.join(PREVIEWS, f"night-shift-3d-sheet-{pack}.png")
    bpy.ops.render.render(write_still=True)
    print("SHEET", s.render.filepath)
    return y - row_h - 10  # next pack starts below this one


lib = build()
for o in lib["streets"]:
    print("STREETS", o.name, tuple(round(v, 2) for v in o.dimensions))
groups = {k: v for k, v in lib.items() if k not in ("streets", "chars")}  # the sheet would spread the character's parts apart
rest = list(lib["streets"])
for name, prefixes in SHEETS.items():
    groups[name] = [o for o in rest if o.name.startswith(prefixes)]
    rest = [o for o in rest if o not in groups[name]]
groups["streets-props"] = rest
y0 = 0.0
for name, obs in groups.items():
    y0 = sheet(name, obs, y0)
for o in bpy.context.scene.collection.all_objects:
    o.hide_render = False
bpy.ops.wm.save_mainfile()  # keep the spread-out layout in the file
print("SAVED LAYOUT", BLEND)
