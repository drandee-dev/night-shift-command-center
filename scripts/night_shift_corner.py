# One street corner with the dashboard's POIs. Run after night_shift_kit.py, night_shift_ramen.py and night_shift_shops.py:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-kit.blend --python scripts/night_shift_corner.py
# Saves projects/night-shift-3d/night-shift-corner.blend and renders _attachments/previews/night-shift-3d-corner.png.
# Metres, Z up. The corner building's walls meet at the origin: front facade on Y=0 facing -Y (main road), side
# facade on X=0 facing +X (cross street). The camera looks from +X/-Y, so both facades face it.
import bpy, math, os
from mathutils import Vector, Matrix, Euler

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
s = bpy.context.scene
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name.startswith("kit_"):
        lc.exclude = True  # the kit is the library; only instances render
scene = bpy.data.collections.new("corner")
s.collection.children.link(scene)
KIT = {o.name: o for c in bpy.data.collections if c.name.startswith("kit_") for o in c.all_objects if o.type == "MESH"}


def dims(name, yaw=0):
    o = KIT[name]
    lo = Vector([min(c[i] for c in o.bound_box) for i in range(3)]); hi = Vector([max(c[i] for c in o.bound_box) for i in range(3)])
    d = hi - lo
    return (d.y, d.x, d.z) if yaw % 2 else (d.x, d.y, d.z)


def put(name, cx, cy, z=0.0, yaw=0, poi=None, tilt=0):
    """Footprint centre (cx, cy), base at z, yaw in quarter turns. tilt turns the piece a quarter about its own Y
    first, so a duct segment lying along X stands upright."""
    o = KIT[name]
    rot = Matrix.Rotation(math.radians(90 * yaw), 4, "Z") @ Matrix.Rotation(math.radians(90 * tilt), 4, "Y")
    pts = [rot @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    e = bpy.data.objects.new(poi or name, None)
    e.instance_type = "COLLECTION"; e.instance_collection = o.users_collection[0]
    e.matrix_world = Matrix.Translation(Vector((cx, cy, z)) - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) @ rot
    if poi:
        e["poi"] = poi  # dashboard panel this object opens; exported to GLB as extras
    scene.objects.link(e)
    return e


def put_scaled(name, cx, cy, z, k, yaw=0):
    """put() for a pack sign shrunk uniformly by k (the 12 m banner is too wide for a 6 m block): footprint centre (cx, cy), base at z."""
    o = KIT[name]
    rot = Matrix.Rotation(math.radians(90 * yaw), 4, "Z") @ Matrix.Scale(k, 4)
    pts = [rot @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"; e.instance_collection = o.users_collection[0]
    e.matrix_world = Matrix.Translation(Vector((cx, cy, z)) - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) @ rot
    scene.objects.link(e)
    return e


# Parked scooters kit-bashed from the Streets pack's parts (they come apart, each centred on its own origin): (part, x, y, z, yaw)
# in the scooter's frame, forward +X: body with seat and tail light (E big / D small), front fender with the green headlight
# (F / E), battery box, two wheels, and the tall twin-post handlebar (Scooter_Big_C / Small_B) standing over the front wheel,
# its bar across the deck (Andres's reference, the Cyberpunk Characters pack's kick scooters, 2026-11-05; it was a dock post before)
SCOOTERS = {"big": [("Scooter_Big_Wheel_00", -0.45, 0, 0, 1), ("Scooter_Big_Wheel_00", 0.6, 0, 0, 1), ("Scooter_Big_F_00", 0.6, 0, 0.15, 0),
                    ("Scooter_Big_E_00", -0.05, 0, 0.2, 0), ("Scooter_Big_D_00", -0.05, 0, 0.05, 0), ("Scooter_Big_C_00", 0.6, 0, 0.0, 1)],
            "small": [("Scooter_Small_Wheel_00", -0.33, 0, 0, 1), ("Scooter_Small_Wheel_00", 0.45, 0, 0, 1), ("Scooter_Small_E_00", 0.45, 0, 0.1, 0),
                      ("Scooter_Small_D_00", 0.0, 0, 0.15, 0), ("Scooter_Small_C_00", 0.0, 0, 0.03, 0), ("Scooter_Small_B_00", 0.45, 0, 0.0, 1)]}
LEAN = 7                                                                            # degrees over onto the kickstand
SCOOTER_K = 0.75                                                                    # the pack's 1.6 m handlebar stood head-high beside a person; 1.2 m reads as a kick scooter


def scooter(kind, x, y, heading):
    """A parked scooter at (x, y) on the ground, nose toward heading (degrees, 0 = +X)."""
    frame = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(heading), 4, "Z") @ Matrix.Rotation(math.radians(LEAN), 4, "X") @ Matrix.Scale(SCOOTER_K, 4)
    for name, px, py, pz, yaw in SCOOTERS[kind]:
        o = KIT[name]
        rot = Matrix.Rotation(math.radians(90 * yaw), 4, "Z")
        pts = [rot @ Vector(c) for c in o.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
        e = bpy.data.objects.new(name, None)
        e.instance_type = "COLLECTION"; e.instance_collection = o.users_collection[0]
        e.matrix_world = frame @ Matrix.Translation(Vector((px, py, pz)) - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) @ rot
        scene.objects.link(e)


def stack(names, along, front, side, z=0.0):
    """Stack blocks with their front flush on a facade. side 'front' = Y=front facing -Y; 'side' = X=front facing +X."""
    for n in names:
        if side == "front":
            put(n, along, front + dims(n)[1] / 2, z)
        else:
            put(n, front - dims(n, 1)[0] / 2, along, z, yaw=1)
        z += dims(n)[2]
    return z


def shop(name, along, side, poi=None):
    """A night_shift_shops.py storefront as a ground floor, its wall line on the facade (facade_y is set by that script)."""
    f = KIT[name]["facade_y"]
    return put(name, along, -f, 0, 0, poi) if side == "front" else put(name, f, along, 0, 1, poi)


def facade(name, along, z, side, poi=None, flip=False, wall=0.0):
    """Hang a flat item (sign, screen, TV) on a facade, its thin axis turned to the wall normal. wall moves the wall
    line toward the street (> 0) or back (< 0), for set-back and cantilevered floors."""
    thin_x = dims(name)[0] < dims(name)[1]
    yaw = (1 if thin_x else 0) if side == "front" else (0 if thin_x else 1)
    yaw += 2 if flip else 0
    t = min(dims(name)[:2])
    if side == "front":
        return put(name, along, -wall - t / 2 - 0.02, z, yaw, poi)
    return put(name, wall + t / 2 + 0.02, along, z, yaw, poi)


def blade(name, along, z, side, out=0.1, flip=False):
    """Hang a flat sign at right angles to the wall, sticking out over the sidewalk."""
    d = dims(name); thin_x = d[0] < d[1]; w = max(d[0], d[1])
    if side == "front":
        return put(name, along, -out - w / 2, z, (0 if thin_x else 1) + (2 if flip else 0))
    return put(name, out + w / 2, along, z, (1 if thin_x else 0) + (2 if flip else 0))


def duct(side, along, z0, z1, run=True):
    """A ribbed duct riser up a wall from z0 to the roof at z1 (Streets pack Vent_Module segments stood upright, 0.6 m
    off the wall), and with run=True one more segment lying on the roof, leading in from the edge."""
    z = z0
    while z1 - z > 1.85:
        name = "Vent_Module_J_00"
        put(name, along if side == "front" else 0.3, -0.3 if side == "front" else along, z, 0 if side == "front" else 1, tilt=1)
        z += dims(name)[0]
    if z1 - z > 0.3:   # top it off with the shortest segment that reaches the roof line
        name = "Vent_Module_D_00" if z1 - z > 0.8 else "Vent_Module_C_00"
        put(name, along if side == "front" else 0.3, -0.3 if side == "front" else along, z, 0 if side == "front" else 1, tilt=1)
    if run:
        put("Vent_Module_J_00", along if side == "front" else -0.95, 0.95 if side == "front" else along, z1, 1 if side == "front" else 0)


def local(name, side, along0, z0=0.0, poi=None):
    """Place a night_shift_shops.py piece by its own frame: local x runs along the facade from along0, y 0 is the
    wall line with the street at -y (vox_lo / vox_hi are the piece's local bounds in metres)."""
    lo, hi = KIT[name]["vox_lo"], KIT[name]["vox_hi"]
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    if side == "front":
        return put(name, along0 + cx, cy, z0 + lo[2], 0, poi)
    return put(name, -cy, along0 + cx, z0 + lo[2], 1, poi)


# ---- ground: 2 m cells; main road Y in [-10,-4], cross road X in [4,10], sidewalk everywhere else ----
# The curb rows next to the roads use the Streets pack's pavement tiles (0.25 m thick, sunk 5 cm to meet the 0.2 m
# sidewalk). Cross-street road tiles turn a quarter so their lane marks run along that street.
PAVE = ["PavementTile_A_00", "PavementTile_B_00", "PavementTile_C_00", "PavementTile_F_00", "PavementTile_G_00",
        "PavementTile_H_00", "PavementTile_I_00", "PavementTile_J_00", "PavementTile_K_00", "PavementTile_L_00"]
for i in range(-12, 12):
    for j in range(-12, 15):                                                          # to y 30: the new block's sidewalk
        x, y = i * 2 + 1, j * 2 + 1
        main, cross = -10 < y < -4, 4 < x < 10
        if main or cross:
            put("Road_Chunk_5", x, y, yaw=1 if cross and not main else 0)
        elif (y == -3 and x < 3) or (x == 3 and y > -3):
            put(PAVE[(i * 7 + j * 3) % len(PAVE)], x, y, -0.05, yaw=1 if x == 3 else 0)
        else:
            put("Sidewalk_Chunk_2", x, y)


def steam(x, y, z, size=1.0):
    """A steam source for night_shift_rain.py, which animates puffs rising from every empty named steam*."""
    e = bpy.data.objects.new("steam", None); e.location = (x, y, z); e["steam"] = size
    scene.objects.link(e)

# ---- the corner block (X < 0, Y > 0) ----
# Heights and depths vary per building (the Voxel Cyberpunk City pack's look): a low corner between tall neighbours,
# cantilevered floors, set-back tops. stack()'s front: on the main road > 0 sets a floor back, < 0 hangs it over the
# sidewalk; on the cross street it is the other way round.
# The corner building (layout job 4, 2026-11-04): a ripperdoc clinic on the ground floor, and above it the net cafe as a 6 m
# two-storey loft (`jobs`) on a 1 m blank panel that carries the clinic's sign. The roof, with the news screen on it, is 3.5 m higher.
# Layout job 5 (2026-11-04): the clinic is pinned for later (`Shop_BodyMods` stays in the kit) and the ground floor is a ramen shop
# (`daily`, the old street stand's button), with the pack's own RAMEN sign on the blank panel; the street corner is clear.
shop("Shop_Ramen", -3, "front", poi="daily")                                      # corner ground floor, 6 m wide
local("Loft_NetCafe", "front", -6.0, 2.5, poi="jobs")
top_corner = 2.5 + 6.0
# the net cafe tower (2026-11-05): four more floors above the loft, 10 m, so the big news screen hangs on its face and the name is a
# vertical blade on its left edge
top_net = top_corner + 10.0
local("Tower_Net", "front", -6.0, top_corner)                                       # custom lit tower, 10 m (was pack blocks)
blade("Sign_NetCafe", -0.3, 3.6, "front", out=0.05)                                 # the vertical name sign on the loft's right edge, at the corner nearest the camera (on the left edge something hid its top)
def tint(name, hues, sat=1.2):
    """Recolour a pack piece: its own copy of each material, hue turned by a Hue/Saturation node (0.5 = unchanged), one hue per slot."""
    for _i, _slot in enumerate(KIT[name].material_slots):
        _m = _slot.material.copy(); _slot.material = _m; _nt = _m.node_tree; _b = _nt.nodes["Principled BSDF"]
        for _inp in ("Base Color", "Emission Color"):
            _hs = _nt.nodes.new("ShaderNodeHueSaturation"); _hs.inputs["Hue"].default_value = hues[min(_i, len(hues) - 1)]; _hs.inputs["Saturation"].default_value = sat
            if _b.inputs[_inp].links:
                _nt.links.new(_b.inputs[_inp].links[0].from_socket, _hs.inputs["Color"])
            else:
                _hs.inputs["Color"].default_value = _b.inputs[_inp].default_value
            _nt.links.new(_hs.outputs["Color"], _b.inputs[_inp])


facade("Billboard_Ramen_00", -3.0, 2.55, "front")                                 # 2.3 x 0.9 m on the 1 m panel, recoloured red below to match the shop (2026-11-05)
tint("Billboard_Ramen_00", (0.1,))                                                 # cyan to red/orange
# Net Cafe's violet kanji (his 11-04 direction: electric blue and violet kanji): three pack glyphs stacked on the bare strip
# left of the loft, the blue NET CAFE blade on its right edge (concept 2026-11-05)
for _g, _gz in (("O", 6.0), ("L", 5.3), ("K", 4.6)):
    tint(f"BillboardModule_ChineseSymbol_{_g}_00", (0.28,))                         # red to violet
    facade(f"BillboardModule_ChineseSymbol_{_g}_00", -6.4, _gz, "front", wall=0.6)   # out level with the repair banner's face, which hid them flat on the wall
# the ramen shop's interior, from the pack: bar counter, stools, oven, pan, dish, board, noren curtains at the door (x -3 to -2)
put("Bar_00", -3.6, 1.35, 0.0)
for sx in (-5.4, -3.9, -3.2):
    put("Stool_00", sx, 0.4, 0.0)
put("Oven_00", -2.2, 1.35, 1.15); put("FryingPan_00", -3.3, 1.3, 1.15); put("Dish_00", -4.3, 1.0, 1.15); put("CuttingWood_00", -5.0, 1.4, 1.15)
put("Curtain_A_00", -2.85, 0.05, 0.0); put("Curtain_B_00", -2.35, 0.05, 0.0)
# four storefronts take the ground floors (same width and depth as the blocks they replace, 2.5 m tall)
shop("Shop_Repair", -8, "front", poi="tooling")                                   # fixing and updating tools
z = stack(["BuildingBlock_19"], -8, 0, "front", 2.5)
z = stack(["BuildingBlock_18"], -8, -0.5, "front", z)                             # cantilevered floor
top_repair = stack(["BuildingBlock_19"], -8, 0, "front", z)
shop("Shop_Mart", -13, "front", poi="mart")                                       # spare slot: no panel yet
local("Kowloon", "front", -16.0, 2.5)                                            # 2nd and 3rd floors: Kowloon-style apartments (2026-11-05, was two pack blocks)
z = 7.5
z = stack(["BuildingBlock_1"], -13, 0.6, "front", z)                              # set back above a ledge (Girl_B hangs on it)
_lo, _hi = KIT["Izakaya"]["vox_lo"], KIT["Izakaya"]["vox_hi"]                      # the top floor is an izakaya (2026-11-05), on the same set-back line
put("Izakaya", -16.0 + (_lo[0] + _hi[0]) / 2, 0.6 + (_lo[1] + _hi[1]) / 2, z + _lo[2], 0)
top_left = z + 2.5
stack(["BuildingBlock_24", "BuildingBlock_18", "BuildingBlock_19"], -18, 0, "front")
stack(["BuildingBlock_19"] * 3, -22, 0, "front")
# The side street, from the corner (y 2.4): the hobby store GAME HUB (6 m, was a 4 m lobby), the florist, a 2 m low block, the
# far tower. The store took 2 m from the low block (2026-11-04), so everything up to the block moved 2 m along the street.
SHIFT = 2.0
shop("Shop_Games", 5.4, "side", poi="games")                                      # hobbies; walker B's door is at y 3.8
local("Arcade_GameHub", "side", 2.4, 2.5, poi="games")                            # second floor: the arcade, open to the side street
top_cafe = stack(["BuildingBlock_2"], 5.4, 0.5, "side", 5.0)                      # hangs over the street, to 7.5 m
local("Roof_Patio", "side", 2.4, top_cafe)                                         # the couple's rooftop patio (deck, rail, door, planters)
# the arcade's contents, from the pack: claw machines, a drinks machine (both moved up from the street), the banner on the block's
# face at half size (12 m x 2 m is too wide for 6 m), the GAME dice sign at three quarters size
for _y in (3.6, 5.0, 6.4):
    put("Machine_CatchaDoll_00", -1.2, _y, 2.5, yaw=1)
put("Machine_DrinkDispenser_00", -1.5, 7.55, 2.5, yaw=1)
put_scaled("Billboard_CatchADoll_00", 0.55, 5.4, 6.45, 0.5, yaw=1)                # the frog and chick banner, 6 m x 1 m, top of the block's face
put_scaled("Billboard_Game_00", 0.55, 7.55, 5.05, 0.75, yaw=1)                    # the GAME dice sign, 1.5 x 1.3 m, below it
# the catwalk (concept signed off 2026-11-04): a landing at the loft's floor level (3.5 m) at the corner, four steps down to a 1 m
# deck at 2.5 m along the arcade, joining the florist's balcony; street poles with hung neon boxes
local("Landing", "side", 0.1, 0.0)
local("Catwalk", "side", 3.4, 0.0)
put("Neon_Pole", 2.45, 6.4, 0.0)                                                  # one street gantry (the second, 2.8 m away at y 4.2, was removed 2026-11-05); at y 7.0 its post hid the H of HYDRO FLORA
# hung neon box naming what is under it (2026-11-05): ARCADE off the pole by the Game Hub (NOODLE was tried at the ramen corner: it hid the RAMEN sign)
put("Hung_ARCADE", 2.45, 6.2, 3.4, yaw=0)                                          # hangs under the gantry's crossbar, facing the main road
# the Game Hub's ground-floor sign (his 11-04 direction: the pixel crab in hot colours): the pack's crab board at 0.6 as a blade
# under the catwalk deck, out of walker B's way (his door is y 3.8, he turns at x 2.2)
tint("BillboardModule_Crab_00", (0.42,), sat=1.4)                                  # the crab alone (the board says 海鮮, seafood), red to hot magenta
_k = 1.1 / dims("BillboardModule_Crab_00")[0]                                      # 1.1 m wide
put_scaled("BillboardModule_Crab_00", 0.55 + 0.1 + 0.55, 4.6, 1.2, _k, yaw=0)
# the loft's end wall: a real door, a camera, two AC units (the EXIT plate and the frame are in the Landing piece)
facade("Door_B_00", 1.25, 3.52, "side"); facade("Camera_B_00", 2.05, 5.55, "side")
facade("Vent_D_00", 0.8, 6.6, "side"); facade("Vent_E_00", 1.9, 7.1, "side")
local("Flyer_Board", "side", 0.2, 0.3, poi="pins")                                  # the pinned posters moved to the corner, under the landing
shop("Shop_Florist", 9.4 + SHIFT, "side", poi="projects")                         # seed, growing, evergreen
local("Patio_Florist", "side", 6.4 + SHIFT, 0.0, poi="projects")                  # second-floor balcony and stairs: same panel
stack(["BuildingBlock_2"], 9.4 + SHIFT, 0, "side", 2.5)
local("Karaoke", "side", 6.4 + SHIFT, 5.0)                                         # karaoke bar on the 3rd level, its stair comes down to the florist balcony's landing (2026-11-05)
top_side = stack(["BuildingBlock_2"], 9.4 + SHIFT, 0, "side", 7.5)
facade("Billboard_TopGun_00", 12.4, top_side, "side", wall=-1.0)                  # Top Gun is a rooftop sign now, on the florist stack
# far tower (layout job 3, 2026-11-04): the library, and a plain-walled block continuing past it. 2026-11-05 (Andres: closer
# to the florist block and pushed back a touch, so more of it is in frame): the whole far block slid LIB_DY along the street
# into the low couch block's slot (Block_Low removed) and set back LIB_DX; night_shift_looks.py moves the library's lights to match
LIB_DY, LIB_DX = -1.0, -0.5                                                         # -2.0 put the florist stairs and palm in front of its left door
shop("Shop_Library", 19.4 + LIB_DY, "side", poi="library").location.x += LIB_DX  # the Scott Monument front (concept v5), y 15.4 to 21.4, peak 10.6 m
local("Wall_Row", "side", 22.4 + LIB_DY, 0.0).location.x += LIB_DX                 # ground floor of the next block, y 21.4 to 27.4
top_row = stack(["BuildingBlock_1", "BuildingBlock_2"], 25.4 + LIB_DY, LIB_DX, "side", 2.5)   # two floors above it, to 7.5 m
local("Lockers", "front", -18.3, 0.0, poi="inbox")                                 # storage lockers, moved 2026-11-05 from the far right (cut off at pitch 75) to right beside the mart
# skyline behind: a Building_06 hex tower and two City towers
b06_top = 0.0
for n in ["Module_Door_B_02", "Module_Windows_Unlit_E_00", "Module_Windows_Unlit_I_00", "Module_Windows_Unlit_G_00", "Rooftop_A_01"]:
    put(n, -5.4, 6.5, b06_top); b06_top += dims(n)[2]
put("Building_3", -13, 5)
put("Building_3", -20, 9)
# skyscrapers behind the street buildings (2026-11-05): tall stacks of the pack's blocks fill the dark gap above the roofs
# (custom Tower_Sky_* pieces, lit and signed like the monogon reference; they run past the frame on purpose, it reads as a big city)
for _tn, _tx, _ty in (("Tower_Sky_A", -20.5, 3.2), ("Tower_Sky_B", -12.2, 3.2), ("Tower_Sky_C", -8.2, 12.6)):
    _lo, _hi = KIT[_tn]["vox_lo"], KIT[_tn]["vox_hi"]
    put(_tn, _tx + (_lo[0] + _hi[0]) / 2, _ty + (_lo[1] + _hi[1]) / 2, _lo[2], 0)
# across the cross street, fronts on the main road
# the foreground block, bottom right (Andres 2026-11-05: "down a touch, a building not a lego piece", then "a little bigger, extend
# more to the right, a door as if it's a rooftop patio", then "deeper, an abandoned rooftop patio"): 6 m wide from x 15.5 (its left
# edge where it was on screen), 1.5 m nearer the camera than the old slab, 4.8 m deep (two rows of blocks), the abandoned patio
# on top (shops' roof_patio_abandoned); the patio's front edge is local y -0.5, so its wall line sits 0.5 m behind the block's front
top_fg = stack(["BuildingBlock_1", "BuildingBlock_1"], 18.5, -1.5, "front")
stack(["BuildingBlock_1", "BuildingBlock_1"], 18.5, 0.9, "front")
_lo, _hi = KIT["Roof_Patio_Abandoned"]["vox_lo"], KIT["Roof_Patio_Abandoned"]["vox_hi"]
put("Roof_Patio_Abandoned", 15.5 + (_lo[0] + _hi[0]) / 2, -1.0 + (_lo[1] + _hi[1]) / 2, top_fg + _lo[2], 0)
put("Vent_A_00", 16.5, 0.4, top_fg + 0.05); put("Vent_A_00", 19.8, 0.6, top_fg + 0.05)   # the AC units back on the roof (his note)
stack(["BuildingBlock_18"], 22, 0, "front")

# ---- the other POIs (panel map confirmed by Andres 2026-11-03) ----
# poi values are the SPOTS ids in night-shift-dashboard.md. An id with no SPOTS entry (email, mart) gets a mask but no
# button, so a new panel only needs its SPOTS entry.
facade("Screen_A_02", -2.9, top_corner + 0.15, "front", poi="news", flip=True)    # the big news screen, brought down onto the tower's face; flip: its display faces +X natively
put("Roof_Dish", -1.0, 9.9, top_side, poi="fleet")                              # uplink to the fleet box: the big dish on the florist stack's roof (2026-11-05; the small one left the corner roof)
put("Fan_D_03", -6.4, 6.0, b06_top)
for k, (sx, sy) in enumerate(((-4.2, 5.2), (-4.2, 6.4), (-4.2, 7.6))):
    put("SolarPanel_15", sx, sy, b06_top)
# the orphans: trash bags on the foreground block's roof (Andres 2026-11-05; the pile at the library's left end covered the library)
put("Trash_A_00", 16.1, -1.05, top_fg + 0.05, poi="orphans")                    # on the patio deck (0.05 m), front left
# State layers for the orphans pile (control-room job 7): NS_JUNK=1..3 adds that level and the ones below it, for a still that
# night_shift_concepts/state_layer.py cuts against the plain still. 1 a few bags, 2 a heap into the rail's gap, 3 piled high with
# bins. Front row y -1.05, second row y -0.45 (the patio's planters and sofa are at the back, the rail's posts are missing
# around x 17.75 to 20); z is above the deck.
JUNK = int(os.environ.get("NS_JUNK", "0"))
JUNK_LEVELS = (
    [("Trash_B_00", 16.8, -1.05, 0, 0), ("Trash_G_00", 16.3, -0.45, 0, 0)],
    [("Trash_F_00", 18.3, -1.05, 0, 0), ("Trash_C_00", 17.1, -0.45, 0, 0), ("Trash_H_00", 17.8, -0.45, 0, 0)],
    [("Trash_G_00", 18.3, -1.05, 0.45, 1), ("Trash_A_00", 16.4, -0.85, 0.4, 1), ("Trash_D_00", 19.4, -1.05, 0, 0),
     ("Trash_E_00", 18.5, -0.45, 0, 0)])
for _lvl in JUNK_LEVELS[:JUNK]:
    for _n, _x, _y, _z, _yaw in _lvl:
        put(_n, _x, _y, top_fg + 0.05 + _z, yaw=_yaw)

# ---- signs: big and many (every pack sign is allowed, Andres 2026-11-03) ----
# blades stick out toward the camera and hide what stands behind them, so tall ones sit flat on the wall instead
facade("Billboard_RedCrime_00", -8, 3.0, "front", wall=0.55)                     # 7 m banner over the repair shop's floors
# (the green pharmacy cross blade was removed 2026-11-05: out of place beside the mart; the clinic idea is pinned)
facade("Billboard_Girl_B_00", -13, 7.6, "front", wall=-0.6)                      # on the set-back floors above the capsule hotel (animated in night_shift_motion.py)
facade("Billboard_Girl_A_00", 9.4 + SHIFT, 7.55, "side")                          # the bunny girl, back (2026-11-05): over the karaoke bar, under the dish
# (the kanji "24" light box over the fascia was removed 2026-11-05: the mart's own fascia has a kanji box and a 24H plate now;
#  the DRUGS sign sits in its place, see the "more of the bought Streets pack" block)
# the hobby store has its own lit fascia and no doorframe; RAMEN is gone from this wall (the stand is the ramen, signage
# audit 2026-11-04). OPEN stays, centred over the store and right of y 3.9, where the DRUGS blade stops covering the wall
# (Neon_Turquoise_Long_00 on the florist stack at 7.7 m gave its place to the bunny girl, 2026-11-05)
for _wz in (8.1,):                                                               # a lit window on the strip above the net cafe blade (the lower two clipped the blade, removed 2026-11-05)
    facade("Window_Tall", -6.55, _wz, "front")
# (Billboard_News_00, the "24" board over the mart, removed 2026-11-05: a third "24" beside the pole sign; the upper floors are open for a redesign)
# (Billboard_KoreanOK_00 on the patio's back edge was cut 2026-11-05: the rail and bulkhead hid half of it)
facade("Neon_Blue_Small_00", -8.2, 2.8, "front")
# outer buildings get their own signs, so the edges of the frame read as more city, not dark fog
# (since the pitch-75 camera only DVD is in frame; Neon_Turquoise_00, the Sachio_A blade and TVCity at -19.9 to -22 were cut
#  2026-11-05, and the crab board moved to the Game Hub)
facade("Billboard_DVD_00", -18, 2.7, "front")
facade("Billboard_Herb_00", 17.1, 2.4, "front", wall=1.5); facade("Billboard_Ring_00", 19.9, 2.4, "front", wall=1.5)   # on the foreground block's new face (1.5 m out, 6 m wide from x 15.5)
facade("Neon_Blue_00", 18.5, 1.8, "front", wall=1.5); facade("Billboard_Game_00", 22, 0.4, "front")
put("LightPole_B_00", -15.5, -3.7)                                               # neon-strip street lamps, lit in night_shift_looks.py
# (the lamp at y 14.6 was removed in layout job 3: its pole hid the library's sign; its cables and fuse box went with it)
put("LightPole_B_00", 3.7, 23.0, yaw=1)
# fences along the curb, cables over the pavement and up the walls, fuse boxes, tech strips, cameras (Streets pack)
put("Fence_A_00", -10.35, -3.6); put("Fence_B_00", -8.05, -3.6); put("Fence_A_00", 3.6, 19.0, yaw=1)   # clear of the tall palm
# Cables run only where something needs power from a wall, from the thing to a fuse box:
# the ramen stand to a box on the corner end wall, the claw machine to a box on the mart's pier, and a box on the far
# tower with its cable running up to the AC unit above it
facade("FuseBox_B_00", -16.2, 0.5, "front")                                      # (the stand's and the claw machine's cables went with them)
# more ground cables (Andres): chained pieces from a fuse box on the wall across the pavement to a unit at the curb
for box_along, box_side, pieces in (
        (-6.3, "front", (("Cable_L_00", -6.3, -0.65, 0), ("Cable_V_00", -6.4, -1.9, 0), ("Cable_U_00", -6.45, -3.1, 0))),    # parking meter
        (None, None, (("Cable_H_00", -15.9, -1.2, 0), ("Cable_R_00", -15.6, -2.7, 0))),                                      # lamp, from the mart's box
        (6.6 + SHIFT, "side", (("Cable_N_00", 0.9, 6.9 + SHIFT, 1), ("Cable_Q_00", 2.1, 8.2 + SHIFT, 1), ("Cable_J_00", 3.0, 9.1 + SHIFT, 1))),   # parking meter
        (None, None, (("Cable_S_00", 0.75, 17.0, 1),))):                                                                     # electronics on the table
    if box_along is not None:
        facade("FuseBox_B_00", box_along, 0.4, box_side)
    for n, x, y, yaw in pieces:
        put(n, x, y, 0.2, yaw)
# ---- street plants (night_shift_shops.py): beside doors, at the curbs, on ledges and roofs, under the overhang ----
put("Plant_Palm", 0.45, 5.6)                                                    # by the store's doorway, under the catwalk (the monstera went: the landing's steps start there)
put("Plant_Monstera", -5.5, -0.4)                                               # by the cafe's left pier
# tall curb palms: a 5 m canopy hides the wall about 3.5 m behind it from this camera, so they stand where that is
# the mart's lower left (no button) and the side street past the stairs (drinks machine), clear of signs and spots
put("Plant_TreeTall", -17.6, -3.35); put("Plant_TreeTall", 3.35, 12.3); put("Plant_Tree", 18.6, -3.2)   # the first moved left of the konbini, it hid the front
local("Plant_LedgeBox", "front", -15.8, 7.5)                                    # on the mart's set-back ledge
local("Plant_Hanging", "side", 3.3, 0.45)                                       # hangs from the catwalk's underside by the store door
put("Plant_Bamboo", -1.3, 2.7, top_cafe + 0.05, yaw=1)                          # on the patio, back left corner
# ribbed duct risers up bare wall to the roofs (Streets pack Vent_Module segments)
# (the end wall's duct riser was removed in layout job 4: Top Gun hangs there now)
duct("side", 14.65, 3.2, top_side)                                       # florist stack, into the roof by the tank
duct("front", -16.6, 2.6, 7.5, run=False)                                       # mart, up to the set-back ledge (left end, clear of the 24H pole sign, 2026-11-05)
put("Vent_Module_J_00", -17.6, 0.3, 7.5)                                        # and along the ledge
for n, along, zz, side in (("Camera_C_00", -16.25, 2.1, "front"),):                        # mart's left pier, clear of its sign (the far-right ATM left with the lockers)
    facade(n, along, zz, side)
# steam: ramen pots, sewer grates, roof vents (animated by night_shift_rain.py)
put("Manhole", -8.6, -6.6, 0.1); put("Manhole", 6.4, 11.6, 0.1)                  # round covers in the road; the grate stays at the curb
# each source sits on something the camera sees (checked by projecting it, 2026-11-05): ramen counter, curb grate,
# the left manhole (the right one is behind the foreground block), the karaoke duct riser top, the florist duct
# riser top, and the exhaust pipe right of the izakaya
for x, y, z, size in ((-3.3, -0.5, 1.2, 0.6), (-0.9, -4.17, 0.12, 0.9), (-8.6, -6.6, 0.12, 1.4),
                      (-1.0, 7.2, 10.65, 0.9), (0.3, 14.65, 9.95, 0.9), (-9.5, 2.0, 12.15, 0.8)):
    steam(x, y, z, size)

# ---- more of the bought Streets pack (Andres: use as much of the paid content as possible) ----
# (JapaneseGun, Drugs_A, the Screen_A module and an electronics plate at -20.8 to -22 were cut 2026-11-05: out of frame)
for n, along, zz, side, wall in (("Camera_A_00", -0.4, 2.9, "front", 0),
                                 ("Camera_B_00", 12.2 + SHIFT, 2.2, "side", 0),  ("Machine_ATM_00", -10.25, 0.0, "front", 0)):   # the second ATM is on the konbini's right pier
    facade(n, along, zz, side, wall=wall)
blade("Billboard_Sachio_B_00", -10.0, 5.3, "front")
for n, x, y, z, yaw in (("Machine_DrinkDispenser_00", -15.55, -0.35, 0, 0), ("Trash_Container_B_00", -22.6, -0.8, 0, 0),
                        ("Garbage_A_00", -21.4, -1.9, 0, 0), ("Garbage_B_00", 3.1, 24.0, 0, 1), ("Trash_B_00", -15.7, -0.5, 0, 0),
                        ("Trash_C_00", 0.35, 12.9 + SHIFT, 0, 0),("Trash_F_00", -10.3, -0.45, 0, 0),         # bags under the stairs, between shops ("Trash_G_00", -2.2, 10.0, 1.6, 0),
                        ("TrashCan_00", 3.8, -0.5, 0, 0), ("DrinkCan_Waste_A_00", 3.4, -3.4, 0, 0), ("CigaretteButt_A_00", 2.9, 6.8, 0, 0),
                        ("Machine_Parkmeter_00", -6.5, -3.6, 0, 0), ("Machine_Parkmeter_00", 3.7, 9.4 + SHIFT, 0, 1),
                        ("CurbDrain", -0.9, -4.17, 0.1, 0)):                       # (the couch and stool left with the low block, 2026-11-05)
    put(n, x, y, z, yaw)
# the pack's own posed people, alongside ours
# checked at dashboard size (2026-11-03): each stands where the camera sees it, none behind the tall palms, facing the
# street (yaw 0 faces -y) unless busy with something
# The pack's 13 characters are only five designs in different poses (by hair: pink A B M N, purple C D E F G, mint H L,
# green K, dark teal J), so one of each, never two of a design in one scene
# (Character_A at the mart door was removed 2026-11-05, Andres: the mart's glare made her a pink blob)
for n, x, y, yaw in (("Character_G_00", 2.5, 10.6 + SHIFT, 0), ("Character_J_00", 2.9, 2.2, 0),   # off walker B's route (x 0.5 to 2.2 along y 3.8, then to y 5.0)
                     ("Character_K_00", -16.4, -2.2, 0), ("Character_L_00", 2.9, 0.4, 0)):
    put(n, x, y, 0, yaw)
put("Advertising_6", -12.0, 1.6, top_left)
put("Advertising_5", -14.6, 1.6, top_left)

# ---- wall and roof clutter: AC units, a water tank, dishes, beacons ----
# AC units sit on bare wall, never on a sign: left of the girl poster above the Pill sign, beside the news board,
for along, zz, side, wall in ((-10.6, 8.6, "front", -0.6),):                     # (the one on the mart wall went: the capsule pods carry their own)
    facade(["Vent_C_00", "Vent_D_00", "Vent_E_00", "Vent_G_00"][int(abs(along)) % 4], along, zz, side, wall=wall)
put("Roof_Tank", -1.9, 11.2 + SHIFT, top_side)
put("Beacon", -0.3, 2.6, top_cafe); put("Beacon", -6.3, 0.4, top_net); put("Beacon", -10.2, 0.8, top_repair)
put("Vent_Module_J_00", -1.0, 7.2, top_cafe + 2.45, yaw=1)                      # on the patio bulkhead's roof, out of the couple's way
put("Vent_Module_C_00", -5.2, 1.2, top_net)
put("SateliteDish", -9.0, 1.4, top_repair)
# the repair roof between the izakaya and the net cafe tower (visual pass 2026-11-05): stacked AC units with a neon tube, a server
# cabinet with a dish, a power cabinet, a fuse box, an exhaust fan, a pipe, cable runs on the roof, and power lines across the gap
put("Vent_A_00", -8.0, 0.45, top_repair); put("Vent_F_00", -8.1, 0.45, top_repair + 0.7)
put("Neon_Turquoise_NoCable_00", -8.1, 0.15, top_repair + 1.42)
put("Device_K_00", -6.5, 0.4, top_repair); put("Dish_00", -6.5, 0.4, top_repair + 1.85); put("Device_G_00", -7.05, 0.4, top_repair)
put("FuseBox_A_00", -9.6, 1.9, top_repair); put("Fan_B_20", -6.6, 1.6, top_repair); put("Pipe_00", -9.5, 2.0, top_repair)
put("Cable_H_00", -8.6, 1.3, top_repair); put("Cable_Q_00", -7.2, 1.45, top_repair)
_lo, _hi = KIT["Gap_Wires"]["vox_lo"], KIT["Gap_Wires"]["vox_hi"]
put("Gap_Wires", -10.0 + (_lo[0] + _hi[0]) / 2, 0.5 + (_lo[1] + _hi[1]) / 2, 10.6, 0)

# ---- street ----
# parked scooters at the street corner where the ramen stand was (his 11-04 answer "parked scooters, or more space for people"):
# three backed in to the side-street curb, noses to the corner building, clear of walker A (x < -0.6) and the pack people at y 0.4
scooter("big", 2.75, -2.7, 180); scooter("small", 2.85, -1.9, 180); scooter("big", 2.75, -1.1, 180)
# (the claw machine and the drinks machine moved up into the arcade)
put("Trash_A_00", 3.0, 22.9)
# the far-right block's street life (layout job 3): mailbox and bench on the sidewalk, a plant by the library door
put("Mailbox", -14.4, -3.6, yaw=0, poi="email")                                    # 2026-11-05 (Andres): out to the curb so more of the lockers show; x + y kept, so it stays as far from the frame edge
put("Bench", 1.6, 21.4 + LIB_DY, yaw=3)                                            # sitters face the street (2026-11-05, was the wall: the reader's tablet shows)
put("Plant_Monstera", 0.5 + LIB_DX, 20.15 + LIB_DY)

# ---- people (night_shift_people.py), scenery only ----
put("Person_Diner", -4.65, 0.4, 0.0, yaw=2)                                     # on the low stool at the ramen bar
put("Person_Florist", 0.7, 9.0 + SHIFT, 2.55)                                         # watering the balcony plants, in front of them
put("Person_Punk", 2.6, 6.0)
put("Cat_Orange3", 1.1, 10.8, 3.15); put("Cat_Calico1", 1.6, 8.0, yaw=2)        # the cats at their loop starts: the tabby sitting on the florist balcony's top rail, the calico on the side street (the loop animates its own copies, 2026-11-05)
# (the umbrella walker and the phone user by the lockers were removed 2026-11-05, Andres)
# Busy people on the floors and landings (Andres 2026-11-05). put() centres the footprint: a seated figure's hips are 0.175 m
# behind its centre (its hands reach forward), and its thighs sit 0.6 m above its feet, so z = seat top - 0.6.
# (a ramen cook, Person_Cook, was tried behind the bar and at the shop's right end: the lanterns and noren hide him in both)
put("Person_Claw", -0.35, 5.0, 2.5, yaw=3)                                       # arcade: leaning into the middle claw machine
put("Person_Drinker", -0.4, 7.15, 2.5, yaw=1)                                    # arcade: a can from the drinks machine, facing the street
put("Person_Smoker", 0.6, 0.9, 3.5, yaw=1)                                       # catwalk landing: on the rail, smoking, watching the street
put("Person_Singer", -1.3, 6.4 + SHIFT + 2.2, 5.1, yaw=1)                          # karaoke: in front of the lyric screen (the stage itself is hidden behind the arcade block)
put("Person_Sofa", -1.325, 6.4 + SHIFT + 4.95, 5.55 - 0.6, yaw=1)                  # karaoke: on the pink sofa, drinking
put("Person_PatioSit", -1.175, 2.4 + 3.45, top_cafe + 0.4 - 0.6, yaw=1)          # roof patio: on the back bench, drinking
put("Person_PatioStand", -0.4, 2.4 + 1.1, top_cafe + 0.05, yaw=1)               # roof patio: by the rail on the left, drinking
put("Person_Reader", 1.775, 20.0 + LIB_DY + 1.0, 0.45 - 0.6, yaw=1)               # library bench: reading a tablet
put("Person_Eater", 2.4, 18.0, 0.0, yaw=1)                                       # left of the bench (at y 21 he was past the frame edge), eating from a takeaway box
put("Person_Rider", 1.6, -3.0, 0.0)                                           # just off a scooter, checking the phone
put("Person_Shopper", -13.4, -0.9, 0.0)                                          # out of the mart with a bag and a snack
# cigarette smoke: small steam sources (the rain overlay puffs them) at the catwalk smoker's mouth and the edgerunner's cigarette tip;
# placed last so the older sources keep their random rhythm in night_shift_rain.py
steam(0.68, 0.9, 4.9, 0.25); steam(0.78, 4.18, 7.95, 0.2)
# the netrunner and the edgerunner sit together on the edge of the roof over the lobby (7.5 m), bamboo behind them,
# legs hanging just clear of the Chinese sign (the low roof by the couch is hidden behind the tall side palm)
# Sitting on an edge puts the knees at the edge (x 0.5) and the hips 0.35 m back on the roof; thighs rest on it
# (seat at local z 12). He sits nearer the camera, she a little farther along, so neither hides the other.
put("Person_Edgerunner", 0.45, 4.4, top_cafe + 0.05 - 0.6, yaw=1); put("Person_Netrunner", 0.45, 5.5, top_cafe + 0.05 - 0.6, yaw=1)   # legs hang over the banner

# ---- camera: frame the corner (roads, ramen stand, both facades, skyline) ----
cam = bpy.data.objects["cam"]
cam.rotation_euler = Euler((math.radians(75), 0, math.radians(45)))               # pitch 75 (was 60) since 2026-11-05: more of the shop interiors
rot = cam.rotation_euler.to_matrix()
region = [Vector((x, y, z)) for x in (-8.2, 5) for y in (-4, 10) for z in (0, 12)]  # the original framing, 1.2 m wider on the left so the lockers show: close; the tall towers run out of the top on purpose
local = [rot.transposed() @ p for p in region]
xs, ys = [p.x for p in local], [p.y for p in local]
cam.location = rot @ Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 300))
s.render.resolution_x, s.render.resolution_y = 1920, 1080
cam.data.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * 1920 / 1080)
cam.data.clip_end = 2000
s.render.filepath = VAULT + r"\_attachments\previews\night-shift-3d-corner.png"
print("INSTANCES", len(scene.objects), "POIS", sorted(o["poi"] for o in scene.objects if "poi" in o))
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("NS_CORNER_OUT") or VAULT + r"\projects\night-shift-3d\night-shift-corner.blend")   # NS_CORNER_OUT: a scratch copy (state layers)
bpy.ops.render.render(write_still=True)
print("RENDERED", s.render.filepath)
