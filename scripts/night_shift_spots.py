# Hotspot masks for the dashboard still. Run on the corner (same camera and size as the look renders):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-corner.blend --python scripts/night_shift_spots.py
# For each POI: a full-frame mask (white where the POI is visible, other geometry still occludes it) and its
# bounding box in % of the frame. Writes _attachments/scenes/night-shift-3d-mask-<id>.png and night-shift-3d-spots.json.
import bpy, json, os
import numpy as np

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
OUT = os.path.join(VAULT, "_attachments", "scenes")
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.eevee.taa_render_samples = 16
s.view_settings.view_transform = "Standard"
s.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
s.compositing_node_group = None

# everything renders black except the instance carrying poi_mask = 1 (read from the instancer empty)
m = bpy.data.materials.new("poi_mask"); nt = m.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
attr = nt.nodes.new("ShaderNodeAttribute"); attr.attribute_type = "INSTANCER"; attr.attribute_name = "poi_mask"
em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(attr.outputs["Fac"], em.inputs["Strength"])
nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
bpy.context.view_layer.material_override = m

groups = {}  # one POI can span several objects (the florist and its patio): they share one mask
for o in bpy.data.objects:
    if "poi" in o:
        groups.setdefault(o["poi"], []).append(o)
spots = {}
for poi, objs in groups.items():
    for o in objs:
        o["poi_mask"] = 1.0
    path = os.path.join(OUT, f"night-shift-3d-mask-{poi}.png")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in objs:
        del o["poi_mask"]
    img = bpy.data.images.load(path)
    w, h = img.size
    lum = np.array(img.pixels[:]).reshape(h, w, 4)[:, :, 0]
    bpy.data.images.remove(img)
    # rewrite as white with the mask in alpha: CSS mask-image reads alpha by default
    out = bpy.data.images.new("mask", w, h, alpha=True)
    rgba = np.ones((h, w, 4)); rgba[:, :, 3] = lum
    out.pixels = rgba.ravel(); out.filepath_raw = path; out.file_format = "PNG"; out.save()
    bpy.data.images.remove(out)
    a = lum[::-1] > 0.1  # Blender pixels start bottom-left
    ys, xs = np.nonzero(a)
    assert len(xs), f"{poi} is not visible from the camera"
    pad = 4
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, w - 1); y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, h - 1)
    spots[poi] = {"box": [round(100 * x0 / w, 2), round(100 * y0 / h, 2), round(100 * (x1 - x0) / w, 2), round(100 * (y1 - y0) / h, 2)],
                  "mask": f"_attachments/scenes/night-shift-3d-mask-{poi}.png", "pixels": int(a.sum())}
    print("SPOT", poi, len(objs), "objects", spots[poi]["box"], spots[poi]["pixels"])
with open(os.path.join(OUT, "night-shift-3d-spots.json"), "w") as f:
    json.dump(spots, f, indent=1)
print("WROTE", len(spots), "spots")
