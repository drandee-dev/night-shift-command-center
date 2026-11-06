# Our own voxel people for the corner, built on the proportions of the Cyberpunk Characters free sample
# (CBP_character_sample: 0.05 m voxels, 33 tall: feet 2, legs 12, hips 4, waist 3, chest 6, head 7, arms 2x2).
# Style reference: maxparata.itch.io/cyberpunkcharacters (techwear, glowing trims, visors, bags). Run on the kit after
# night_shift_shops.py:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b projects/night-shift-3d/night-shift-kit.blend --python scripts/night_shift_people.py
# Adds kit_custom/Person_* (front faces -y, feet on z = 0) and renders _attachments/previews/night-shift-3d-people.png.
import bpy, sys, math, os
from mathutils import Vector, Euler

VAULT = os.environ.get("NIGHT_SHIFT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this file is <root>/scripts/...
sys.path.insert(0, VAULT + r"\scripts")
import night_shift_ramen as R
import night_shift_shops as S
from night_shift_ramen import box, vox

P = {**S.P,
     "skin_a": ((0.86, 0.64, 0.50), None), "skin_b": ((0.52, 0.35, 0.24), None), "skin_c": ((0.95, 0.80, 0.68), None),
     "eye": ((0.04, 0.04, 0.06), None), "hair_b": ((0.55, 0.30, 0.12), None), "hair_w": ((0.85, 0.85, 0.90), None),
     "coat": ((0.10, 0.11, 0.16), None), "coat_r": ((0.45, 0.06, 0.10), None), "coat_y": ((0.80, 0.62, 0.10), None),
     "denim": ((0.14, 0.18, 0.32), None), "pants_k": ((0.06, 0.06, 0.08), None), "apron": ((0.15, 0.38, 0.22), None),
     "shoe": ((0.85, 0.85, 0.85), None), "umb": ((0.55, 0.70, 0.85), None),
     "hair_v": ((0.78, 0.66, 1.0), None), "coat_c": ((0.12, 0.12, 0.16), None), "coat_o": ((0.95, 0.42, 0.08), None),
     "patch_t": ((0.08, 0.55, 0.55), None), "stubble": ((0.55, 0.42, 0.52), None),
     "coat_g": ((0.08, 0.32, 0.28), None), "coat_p": ((0.42, 0.18, 0.52), None),
     }
GLOW = {"c": "neon_cyan", "p": "neon_pink", "v": "neon_vio", "y": "neon_yel", "o": "neon_org", "g": "neon_grn", "w": "fluor"}


# leg and forearm shifts along y per pose (left, right; -y is forward). walk0/walk1/walk2 are the frames of a gait cycle
# (night_shift_motion.py plays 0, 1, 2, 1); the arm opposite each forward leg swings forward with it.
LEG = {"walk": (-2, 1), "walk0": (-3, 2), "walk1": (0, 0), "walk2": (2, -3)}
ARM = {"walk0": (2, -2), "walk1": (0, 0), "walk2": (-2, 2)}


def person(skin, hair, top, pants, shoes, pose="stand", trim=None, extra=()):
    """One figure, x -3..2 wide, front face at y -3. Poses: stand, walk, walk0-2, sit (seat at z 13), phone, umbrella, water."""
    if pose.startswith("sit"):                                 # thighs forward on the seat, calves down
        for lx in (-3, 1):
            if pose == "sit_knee" and lx == -3:                # right knee drawn up, foot flat on the seat
                for t in range(6):
                    box(lx, lx + 1, -t, -t, 12 + t, 13 + t, pants)
                box(lx, lx + 1, -7, -6, 12, 18, pants); box(lx, lx + 1, -8, -6, 12, 13, shoes)
                continue
            box(lx, lx + 1, -7, 0, 12, 13, pants); box(lx, lx + 1, -7, -6, 2, 11, pants); box(lx, lx + 1, -8, -6, 0, 1, shoes)
    else:
        for lx, dy in zip((-3, 1), LEG.get(pose, (0, 0))):
            box(lx, lx + 1, -1 + dy, 0 + dy, 2, 13, pants); box(lx, lx + 1, -2 + dy, 0 + dy, 0, 1, shoes)
            box(lx, lx + 1, -2 + dy, -2 + dy, 0, 0, "rubber")
    box(-3, 2, -2, 1, 14, 17, pants); box(-3, 2, -3, -3, 17, 17, "steel_d")      # hips and belt
    box(-2, 1, -2, 1, 18, 20, top); box(-3, 2, -3, 1, 21, 26, top)              # waist, chest
    box(-3, 2, -3, -3, 26, 26, "steel_d")                                       # collar
    if trim:
        box(-1, -1, -4, -4, 18, 25, trim)                                       # glowing zip line
        box(-3, -3, -3, -3, 21, 26, trim)
    # arms: upper arms hang at the sides; the right forearm changes with the pose
    for ax in (-5, 3):
        box(ax, ax + 1, -1, 0, 19, 25, top)
    if pose in ("phone", "umbrella"):
        box(-5, -4, -6, -1, 18, 19, top); box(-5, -4, -8, -7, 18, 20, skin)
    elif pose == "sit_knee":                                   # right arm rests over the raised knee, left hand on the seat
        box(-5, -4, -6, -1, 19, 20, top); box(-5, -4, -7, -6, 18, 19, skin)
        box(3, 4, -1, 0, 13, 18, top); box(3, 4, -1, 0, 12, 12, skin)
    elif pose == "sit":
        for ax in (-5, 3):
            box(ax, ax + 1, -7, -1, 19, 20, top); box(ax, ax + 1, -9, -8, 19, 20, skin)
    else:
        al = ARM.get(pose, (0, 0))[0]
        box(-5, -4, -1 + al, 0 + al, 14, 18, top); box(-5, -4, -1 + al, 0 + al, 12, 13, skin)
    if pose == "water":
        box(3, 4, -6, -1, 18, 19, top); box(3, 4, -8, -7, 18, 19, skin)
        box(3, 7, -12, -8, 14, 18, "can_g"); box(5, 5, -16, -13, 18, 19, "can_g"); box(4, 6, -8, -8, 19, 20, "steel")
    elif not pose.startswith("sit"):
        ar = ARM.get(pose, (0, 0))[1]
        box(3, 4, -1 + ar, 0 + ar, 14, 18, top); box(3, 4, -1 + ar, 0 + ar, 12, 13, skin)
    if pose == "phone":
        box(-5, -4, -9, -9, 19, 22, "screen_c")
    if pose == "umbrella":                                     # clear umbrella with a neon rim, held in the right hand
        box(-5, -5, -8, -8, 21, 44, "steel")
        for dx in range(-14, 15):
            for dy in range(-14, 15):
                r2 = dx * dx + dy * dy
                if r2 <= 196:
                    vox[(-5 + dx, -8 + dy, 45 - r2 // 40)] = "neon_cyan" if r2 > 170 else "umb"
    # head: face at y -3, hair over the top and back
    box(-3, 2, -3, 2, 27, 33, skin)
    box(-3, 2, -3, 2, 33, 34, hair); box(-3, 2, 1, 2, 27, 34, hair); box(-3, -3, -3, 2, 30, 34, hair); box(2, 2, -3, 2, 30, 34, hair)
    box(-3, 2, -4, -4, 32, 33, hair)                                            # fringe
    vox[(-2, -4, 30)] = vox[(1, -4, 30)] = "eye"
    vox[(-1, -4, 28)] = vox[(0, -4, 28)] = "skin_b" if skin != "skin_b" else "eye"
    for e in extra:
        if e == "visor":
            box(-3, 2, -5, -5, 30, 30, "neon_pink")
        if e == "headphones":
            box(-4, -4, -1, 1, 29, 31, "rubber"); box(3, 3, -1, 1, 29, 31, "rubber")
            vox[(-4, -2, 30)] = vox[(3, -2, 30)] = "neon_cyan"; box(-3, 2, 0, 0, 35, 35, "rubber")
        if e == "mohawk":
            box(-1, 0, -3, 2, 35, 38, "neon_pink")
            for y in range(-3, 3):
                vox[(-1, y, 39 - (y + 3) % 2)] = "neon_pink"
        if e == "beanie":
            box(-3, 2, -4, 2, 33, 36, "coat_r"); box(-3, 2, -4, -4, 33, 33, "white")
        if e == "bag":
            box(3, 5, 0, 3, 14, 20, "coat_y"); box(3, 3, -2, 0, 21, 26, "coat_y")
        if e == "cyberarm":                                      # left arm in chrome with glowing joints
            box(3, 4, -1, 0, 12, 25, "steel"); vox[(4, -2, 19)] = vox[(4, -2, 14)] = "neon_cyan"
        if e == "longcoat":
            box(-3, 2, -3, 1, 8, 16, top)
        if e == "undercut":                                     # shaved sides, long top swept down over the right side
            box(-3, -3, -3, 2, 27, 31, "stubble"); box(2, 2, -3, 2, 27, 29, "stubble")
            box(-3, 3, -4, 2, 34, 35, hair); box(2, 3, -4, 1, 24, 33, hair); box(-2, 2, -5, -4, 31, 33, hair)
        if e == "neckport":                                     # glowing jack at the nape, cable down to a deck on the hip
            vox[(-1, 3, 26)] = vox[(0, 3, 26)] = "neon_vio"
            for z in range(16, 26):
                vox[(-1 + (z % 3 == 0), 2, z)] = "neon_vio"
            box(3, 5, -1, 1, 14, 16, "desk"); box(4, 5, -2, -2, 15, 15, "screen_c")
        if e == "spiky":
            for x, y in ((-3, -2), (-1, -1), (1, -2), (2, 0), (-2, 1), (0, 1)):
                box(x, x, y, y, 35, 36 + (x + y) % 2, hair)
        if e == "goggles":
            box(-3, 2, -4, 2, 33, 33, "rubber"); box(-3, -2, -5, -5, 33, 34, "fl_o"); box(1, 2, -5, -5, 33, 34, "fl_o")
        if e == "patches":
            for x, y, z in ((-2, -4, 24), (1, -4, 20), (-3, -1, 22), (3, -2, 23), (0, 2, 19)):
                box(x, x + 1, y, y, z, z + 1, "patch_t")
        if e == "cyberlimbs":                                   # chrome arms with glowing joints
            for ax in (-5, 3):
                for (x, y, z), c in list(vox.items()):
                    if ax <= x <= ax + 1 and 12 <= z <= 25 and c not in ("neon_cyan",):
                        vox[(x, y, z)] = "steel"
            vox[(-5, -2, 19)] = vox[(4, -2, 19)] = "neon_cyan"
        if e == "apron":
            box(-2, 1, -4, -4, 10, 24, "apron"); box(-2, 1, -4, -4, 24, 24, "white")
    # the couple's movements (night_shift_motion.py swaps these in): x is along the roof edge, her -x is toward him
    def shift(zlo, zhi, dx, dy=0):
        moved = {(x + dx, y + dy, z): c for (x, y, z), c in vox.items() if zlo <= z <= zhi}
        for k in [k for k in vox if zlo <= k[2] <= zhi]:
            del vox[k]
        vox.update(moved)

    def clear(xlo, xhi, ylo, yhi, zlo, zhi, colours):         # take out part of an arm so a raised one can replace it
        for k, c in list(vox.items()):
            if xlo <= k[0] <= xhi and ylo <= k[1] <= yhi and zlo <= k[2] <= zhi and c in colours:
                del vox[k]
    for e in extra:
        if e.startswith("lean"):                               # shoulders then head lean over, the top of the head furthest
            chest, head = {"lean1": (1, 2), "lean2": (3, 6)}[e]
            shift(33, 40, -head - (e == "lean2")); shift(27, 32, -head); shift(21, 26, -chest)
        if e == "nod":                                         # head dips forward (front is -y)
            shift(27, 40, 0, -1)
        if e == "wave":                                        # right hand up in greeting
            clear(3, 4, -1, 0, 12, 18, (top, skin))
            box(3, 4, -1, 0, 26, 29, top); box(3, 4, -1, 0, 30, 31, skin)
        if e == "slurp":                                       # a bowl raised to the mouth in the left hand
            clear(-5, -4, -9, -1, 19, 20, (top, skin))
            box(-5, -4, -5, -4, 20, 26, top); box(-7, -2, -8, -4, 26, 27, "white"); box(-6, -3, -7, -5, 28, 28, "white")
        if e == "turn":                                        # looks across at her
            shift(27, 40, 1)
        if e == "glance":                                      # the street people's head turns: 10 cm, to show at dashboard size
            shift(27, 40, 2)
        if e == "glanceL":
            shift(27, 40, -2)
        if e == "armaround":                                   # the arm toward her goes behind her shoulders, in chrome
            for k in [k for k in vox if 3 <= k[0] <= 4 and k[1] <= -2 and 19 <= k[2] <= 20]:
                del vox[k]
            box(3, 10, -1, 0, 22, 23, "steel"); box(11, 11, -1, 0, 22, 23, "steel"); vox[(7, -2, 22)] = "neon_cyan"
        # activity poses (2026-11-05): arms change, so they run after the base arms are drawn; order in extras matters
        if e in ("rail", "stretch"):                           # both forearms forward on a rail or a machine / both arms up
            for ax in (-5, 3):
                clear(ax, ax + 1, -9, 2, 12, 25 if e == "stretch" else 20, (top, skin))
                if e == "rail":
                    box(ax, ax + 1, -1, 0, 19, 25, top); box(ax, ax + 1, -7, -1, 19, 20, top); box(ax, ax + 1, -9, -8, 19, 20, skin)
                else:
                    box(ax, ax + 1, -1, 0, 26, 37, top); box(ax, ax + 1, -1, 0, 38, 39, skin)
            if e == "rail":
                shift(21, 40, 0, -1)                           # shoulders and head lean over a little
        if e in ("cig", "can", "mic", "snack", "chop"):        # right hand up at the mouth, with what it holds
            clear(-5, -4, -9, 2, 12, 20, (top, skin))
            box(-5, -4, -1, 0, 19, 25, top); box(-5, -4, -4, -2, 19, 20, top); box(-4, -3, -5, -4, 21, 25, top)
            box(-3, -2, -6, -5, 26, 27, skin)
            if e == "cig":
                vox[(-1, -5, 28)] = vox[(-1, -6, 28)] = "white"; vox[(-1, -7, 28)] = "neon_org"
            if e == "can":
                box(-2, -1, -7, -6, 27, 30, "screen_c")
            if e == "mic":
                box(-2, -1, -6, -6, 23, 27, "steel"); box(-2, -1, -7, -6, 28, 29, "neon_pink")
            if e == "snack":
                box(-2, -1, -7, -6, 27, 29, "snack_o")
            if e == "chop":
                vox[(-2, -7, 27)] = vox[(-2, -8, 26)] = "steel"
        if e == "hold_box":                                    # left forearm out, a takeaway box in the hand
            clear(3, 4, -9, 2, 12, 20, (top, skin))
            box(3, 4, -1, 0, 19, 25, top); box(3, 4, -6, -1, 18, 19, top); box(3, 4, -8, -7, 18, 19, skin)
            box(0, 4, -11, -8, 20, 22, "white"); box(0, 4, -11, -11, 21, 21, "neon_org")
        if e == "tablet":                                      # seated, a glowing tablet held up in both hands
            box(-4, 3, -10, -10, 20, 25, "screen_c")
        if e == "can_lap":                                     # a lit can in the hand resting on the raised knee (below the lean's shift)
            box(-5, -4, -8, -8, 17, 20, "screen_c")
        if e == "cig_sit":                                     # a cigarette between the fingers of the forward right hand
            vox[(-5, -10, 20)] = "white"; vox[(-5, -11, 20)] = "neon_org"
    # cyber parts (Andres 2026-11-05: glowing parts on everyone), recolours done last so every pose gets them:
    # soles_X lights the shoe soles, cuffs_X rings the wrists, eyes_X is a lit eye bar, implant_X two lit dots at the temple
    for e in extra:
        g = GLOW.get(e.rsplit("_", 1)[-1])
        if e.startswith("soles_"):
            for k in [k for k, c in vox.items() if k[2] == 0 and c == shoes]:
                vox[k] = g
        if e.startswith("cuffs_"):
            hands = [k for k, c in vox.items() if c == skin and not (-3 <= k[0] <= 2 and -4 <= k[1] <= 2 and k[2] >= 27)]
            for x, y, z in hands:
                for n in ((x, y, z + 1), (x, y + 1, z), (x, y - 1, z), (x, y, z - 1)):
                    if vox.get(n) == top:
                        vox[n] = g
        if e.startswith("eyes_"):
            box(-3, 2, -5, -5, 30, 30, g)
        if e.startswith("implant_"):
            vox[(-4, -1, 30)] = vox[(-4, 0, 29)] = vox[(3, -1, 30)] = g


CAST = {   # name: (skin, hair, top, pants, shoes, pose, trim, extras)
    "Person_Umbrella": ("skin_c", "hair_w", "coat", "pants_k", "pants_k", "umbrella", "neon_cyan", ("longcoat",)),
    "Person_Punk": ("skin_a", "eye", "coat_r", "denim", "shoe", "walk", "neon_pink", ("mohawk", "headphones", "bag", "soles_p", "cuffs_c")),
    "Person_Phone": ("skin_b", "hair", "jacket", "pants_k", "shoe", "phone", "neon_yel", ("visor", "cyberarm")),
    "Person_Diner": ("skin_a", "hair_b", "coat_y", "denim", "pants_k", "sit", "neon_org", ("beanie", "eyes_c", "cuffs_o", "chop")),
    "Person_Florist": ("skin_c", "hair_b", "white", "denim", "shoe", "water", None, ("apron", "implant_g", "cuffs_g", "soles_w")),
    # an original pair (Andres, 2026-11-03): a netrunner with light violet hair and a street-kid edgerunner
    "Person_Netrunner": ("skin_c", "hair_v", "coat_c", "pants_k", "pants_k", "sit_knee", "neon_vio", ("longcoat", "undercut", "neckport", "can_lap")),
    "Person_Edgerunner": ("skin_a", "hair", "coat_o", "denim", "shoe", "sit", "neon_cyan", ("spiky", "goggles", "patches", "cyberlimbs", "cig_sit", "soles_c")),
    # the people around the floors and landings (Andres 2026-11-05: busy with something, cyber parts on everyone)
    "Person_Cook": ("skin_b", "hair", "white", "pants_k", "shoe", "stand", "neon_org", ("apron", "beanie", "rail", "implant_c", "cuffs_o")),
    "Person_Claw": ("skin_c", "hair_w", "jacket", "pants_k", "shoe", "stand", "neon_pink", ("headphones", "rail", "soles_p", "cuffs_c")),
    "Person_Drinker": ("skin_a", "hair_b", "coat_g", "denim", "shoe", "stand", "neon_grn", ("cyberarm", "can", "eyes_c", "soles_w")),
    "Person_Smoker": ("skin_c", "hair", "coat", "pants_k", "pants_k", "stand", "neon_vio", ("longcoat", "undercut", "rail", "cig", "implant_v")),
    "Person_Singer": ("skin_b", "hair_v", "coat_p", "pants_k", "shoe", "stand", "neon_pink", ("spiky", "mic", "soles_p", "cuffs_p")),
    "Person_Sofa": ("skin_a", "hair_w", "coat_r", "denim", "shoe", "sit", "neon_yel", ("can", "eyes_y", "cuffs_y")),
    "Person_PatioSit": ("skin_c", "hair_b", "coat_c", "denim", "shoe", "sit", "neon_cyan", ("beanie", "can", "cuffs_c", "soles_c")),
    "Person_PatioStand": ("skin_b", "hair", "coat_o", "pants_k", "shoe", "stand", "neon_org", ("headphones", "can", "soles_o", "implant_o")),
    "Person_Reader": ("skin_a", "hair_v", "jacket", "pants_k", "shoe", "sit", "neon_cyan", ("undercut", "tablet", "cuffs_c", "soles_w")),
    "Person_Eater": ("skin_c", "hair_b", "coat_p", "denim", "shoe", "stand", "neon_pink", ("goggles", "hold_box", "chop", "soles_p")),
    "Person_Rider": ("skin_b", "hair_w", "coat_g", "pants_k", "shoe", "phone", "neon_cyan", ("visor", "cyberarm", "bag", "soles_c")),
    "Person_Shopper": ("skin_a", "hair", "coat_y", "pants_k", "shoe", "walk", "neon_yel", ("bag", "snack", "headphones", "soles_y")),
}
# the couple on the lobby roof: she leans her head over to him, he turns and puts an arm around her
for n in (1, 2):
    CAST[f"Person_NetrunnerL{n}"] = (*CAST["Person_Netrunner"][:7], CAST["Person_Netrunner"][7] + (f"lean{n}",))
CAST["Person_EdgerunnerT"] = (*CAST["Person_Edgerunner"][:7], CAST["Person_Edgerunner"][7] + ("turn",))
CAST["Person_EdgerunnerA"] = (*CAST["Person_Edgerunner"][:7], CAST["Person_Edgerunner"][7] + ("turn", "armaround"))
# the punk greets and nods to walker B, and the diner lifts his bowl (night_shift_motion.py)
CAST["Person_PunkN"] = (*CAST["Person_Punk"][:7], CAST["Person_Punk"][7] + ("nod",))
CAST["Person_PunkW"] = (*CAST["Person_Punk"][:7], CAST["Person_Punk"][7] + ("wave",))
CAST["Person_DinerS"] = (*CAST["Person_Diner"][:7], CAST["Person_Diner"][7] + ("slurp",))
# glances: the umbrella walker, the phone user and the florist turn their heads now and then (night_shift_motion.py)
for base, tag in (("Person_Umbrella", "T"), ("Person_Phone", "T"), ("Person_Florist", "T")):
    CAST[base + tag] = (*CAST[base][:7], CAST[base][7] + ("glance",))
for base, tag, g in (("Person_Diner", "G", "glance"), ("Person_Netrunner", "G", "glance"), ("Person_Edgerunner", "G", "glanceL")):   # seated: look away in the gaps
    CAST[base + tag] = (*CAST[base][:7], CAST[base][7] + (g,))
CAST["Person_FloristL"] =(*CAST["Person_Florist"][:7], CAST["Person_Florist"][7] + ("glanceL",))
# loop poses for the busy people (2026-11-05, night_shift_motion.py): the diner's chopsticks down, the smoker's cigarette resting
# on the rail, the reader standing up (T) and stretching (U), the tablet put down
CAST["Person_DinerD"] = (*CAST["Person_Diner"][:7], tuple(e for e in CAST["Person_Diner"][7] if e != "chop"))
CAST["Person_SmokerL"] = (*CAST["Person_Smoker"][:7], tuple("cig_sit" if e == "cig" else e for e in CAST["Person_Smoker"][7]))
_rd = tuple(e for e in CAST["Person_Reader"][7] if e != "tablet")
CAST["Person_ReaderT"] = (*CAST["Person_Reader"][:5], "stand", CAST["Person_Reader"][6], _rd)
CAST["Person_ReaderU"] = (*CAST["Person_Reader"][:5], "stand", CAST["Person_Reader"][6], _rd + ("stretch",))
# two walkers for the animated loop, three gait poses each (Person_WalkA0..2, Person_WalkB0..2)
for k in range(3):
    CAST[f"Person_WalkA{k}"] = ("skin_b", "hair_b", "jacket", "pants_k", "shoe", f"walk{k}", "neon_pink", ("headphones", "bag", "soles_p", "cuffs_p"))
    CAST[f"Person_WalkB{k}"] = ("skin_a", "hair_w", "coat_c", "denim", "shoe", f"walk{k}", "neon_cyan", ("visor", "bag", "soles_c", "implant_c"))

if __name__ == "__main__":
    kc = bpy.data.collections["kit_custom"]
    for name, spec in CAST.items():
        old = bpy.data.collections.get(name)
        if old:
            for o in list(old.objects): bpy.data.objects.remove(o)
            bpy.data.collections.remove(old)
        c = bpy.data.collections.new(name); kc.children.link(c)
        o = R.build_mesh(name, lambda: person(*spec[:6], trim=spec[6], extra=spec[7]), P)
        o["vox_lo"] = [min(k[i] for k in vox) * R.V for i in range(3)]
        o["vox_hi"] = [(max(k[i] for k in vox) + 1) * R.V for i in range(3)]
        c.objects.link(o)
        print("PERSON", name, tuple(round(v, 2) for v in o.dimensions))
    bpy.ops.wm.save_mainfile()
    s = bpy.context.scene                                      # preview, not saved
    for ob in bpy.data.objects:
        ob.hide_render = ob.name not in CAST and ob.type != "LIGHT"
    for i, name in enumerate(list(CAST) + ["CyberpunkChar_0"]):
        obs = [bpy.data.objects[name]] if name in CAST else list(bpy.data.collections[name].objects)
        for ob in obs:
            ob.hide_render = False
            ob.location = (i * 1.8, 0, 0)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(4, 0, 0))
    cam = bpy.data.objects["cam"]
    cam.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))
    cam.location = Vector((4.5, 0, 0.9)) + cam.rotation_euler.to_matrix() @ Vector((0, 0, 60))
    cam.data.ortho_scale = 9.5
    s.render.resolution_x, s.render.resolution_y = 1600, 900
    s.render.filepath = VAULT + r"\_attachments\previews\night-shift-3d-people.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", s.render.filepath)
