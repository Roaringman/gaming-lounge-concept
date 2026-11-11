"""Rough empty-shell model of a former bakery (ground floor).

Geometry is traced from Material/PlanDrawing.png (pixel coords, y down) and
scaled with the rough measures in Material/rough_measures.txt:
  Bageri 8 x 4 m  -> 228 x 124 px,  Kontor 2.5 x 4 m -> 70 x 124 px,
  Konditori 5.5 x 4 m -> ~144 x 128 px
=> SX ~ 28.5 px/m (east-west), SY ~ 31 px/m (north-south).
All other rooms are estimated from the drawing with the same scale.

Run:  blender -b --python build_bakery.py
Produces Bakery_Model.blend and renders/ next to this script.
"""
import bpy, bmesh, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SX, SY = 28.5, 31.0
X0, Y0 = 8, 442           # plan origin -> (0,0) = south-west corner of the plan
H = 3.0                   # ceiling height (older block, "full ceiling height")
SLAB = 0.30               # floor / roof slab thickness
T_EXT, T_INT = 0.40, 0.12


def P(px, py):
    return Vector(((px - X0) / SX, (Y0 - py) / SY, 0.0))


# ------------------------------------------------------------------ helpers
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def mat(name, rgba, rough=0.6, metal=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    if transmission:
        for key in ("Transmission Weight", "Transmission"):
            if key in b.inputs:
                b.inputs[key].default_value = transmission
                break
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    return m


def add_box(bm, a, b, t, z0, z1):
    """Oriented box along a->b (2D), thickness t, from z0 to z1."""
    d = (b - a)
    L = d.length
    if L < 1e-4 or z1 - z0 < 1e-4:
        return
    d.normalize()
    n = Vector((-d.y, d.x, 0)) * (t / 2)
    pts = [a - n, b - n, b + n, a + n]
    vs = [bm.verts.new((p.x, p.y, z0)) for p in pts] + \
         [bm.verts.new((p.x, p.y, z1)) for p in pts]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f])


def obj_from_bm(bm, name, collection, material):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    me.materials.append(material)
    return ob


# ------------------------------------------------------------------ data
# Outer footprint (clockwise in plan pixels).
FOOT = [(8, 190), (152, 190), (152, 172), (162, 165), (205, 165), (212, 172), (212, 190),
        (265, 190), (370, 193), (390, 213), (428, 205), (428, 157), (540, 157), (540, 235),
        (662, 235), (662, 405), (640, 442), (237, 442), (237, 342), (172, 342), (150, 318),
        (8, 318)]

# Openings on exterior edges: edge index -> list of (p0, p1, sill, head, kind)
# p0/p1 are plan pixel points on that edge.
SHOP, STD, OLD, DOOR, GDOOR = "shop", "std", "old", "door", "glassdoor"
OPEN = "open"   # doorway without a door leaf
EXT_OPEN = {
    0:  [((40, 190), (75, 190), 0.9, 2.5, STD), ((105, 190), (135, 190), 0.9, 2.5, STD)],  # Konditori, gaard
    3:  [((172, 165), (195, 165), 1.1, 2.4, STD)],                                         # stair 1
    6:  [((222, 190), (255, 190), 1.1, 2.4, STD)],                                         # fyrrum
    9:  [((394, 212), (424, 206), 0.9, 2.6, STD)],                                         # angled glazing
    10: [((428, 197), (428, 167), 1.1, 2.4, STD)],                                         # stair 2
    11: [((476, 157), (494, 157), 0.0, 2.1, DOOR), ((510, 157), (530, 157), 1.5, 2.3, STD)],  # yard door + bad
    # East street: two large display windows (exterior_2.jpg); no door
    14: [((662, 243), (662, 300), 0.5, 2.6, SHOP), ((662, 325), (662, 378), 0.5, 2.6, SHOP)],
    # 15: angled corner wall is blank (exterior_1/_2.jpg)
    # South street shop front (exterior_1.jpg): glass door + glass sidelight near the corner,
    # then a display window further west
    16: [((632, 442), (584, 442), 0.0, 2.6, GDOOR), ((578, 442), (541, 442), 1.0, 2.6, SHOP),
         ((528, 442), (478, 442), 0.9, 2.5, OLD),                                          # kontor
         ((455, 442), (418, 442), 0.9, 2.5, OLD), ((400, 442), (363, 442), 0.9, 2.5, OLD),
         ((345, 442), (308, 442), 0.9, 2.5, OLD), ((290, 442), (253, 442), 0.9, 2.5, OLD)],  # bageri
    21: [((8, 312), (8, 282), 0.9, 2.5, STD)],                                             # Konditori west
}

# Interior walls: (p0, p1, [openings as (q0, q1, sill, head, kind)])
INT_WALLS = [
    ((152, 190), (152, 245), []),                                        # Konditori | trappe
    ((152, 245), (212, 245), [((168, 245), (196, 245), 0, 2.1, DOOR)]),  # trappe bund
    # trappe | fyrrum wall (212,190)-(212,245) removed -> trappe opens into fyrrum
    ((212, 245), (212, 278), []),                                        # fyrrum vest (gang part)
    ((212, 278), (265, 278), [((224, 278), (250, 278), 0, 2.1, DOOR)]),  # fyrrum syd
    # fyrrum | bageriovn wall (265,190)-(265,278) removed -> fyrrum opens into bageriovn
    ((265, 278), (265, 318), []),                                        # bageriovn vest (gang part)
    # bageriovn | bageri: only between the oven room's corners (gang W opens straight
    # into the bageri, no stubs); oven room entered from the bageri, mid-wall
    ((265, 318), (388, 318), [((295, 318), (327, 318), 0, 2.2, OPEN)]),  # open doorway, no leaf
    ((388, 213), (388, 318), []),                                        # bageriovn oest (solid)
    ((468, 318), (468, 442), [], "Wall_Bageri_Kontor_REMOVED"),          # knocked down: kept, hidden
    ((468, 320), (538, 320), [((472, 320), (494, 320), 0, 2.1, DOOR)]),  # kontor nord
    ((538, 235), (538, 442), [((538, 262), (538, 302), 0, 2.2, DOOR),    # gang | bagerbutik
                              ((538, 355), (538, 392), 0, 2.2, OPEN)]),  # kontor | bagerbutik, open
    ((428, 207), (495, 207), [((440, 207), (470, 207), 0, 2.1, DOOR)]),  # trappe 2 bund
    ((495, 157), (495, 207), []),                                        # trappe 2 | bad
    ((495, 207), (540, 207), [((506, 207), (526, 207), 0, 2.1, DOOR)]),  # bad bund
]
PILLARS = [(148, 274), (208, 274)]

ROOMS = [  # name, polygon (plan px), floor tint
    ("Konditori", [(8, 190), (152, 190), (152, 318), (8, 318)], (0.80, 0.78, 0.74, 1)),
    ("Trappe", [(152, 172), (162, 165), (205, 165), (212, 172), (212, 245), (152, 245)], (0.70, 0.70, 0.70, 1)),
    ("Fyrrum", [(212, 190), (265, 190), (265, 278), (212, 278)], (0.62, 0.62, 0.64, 1)),
    ("Gang", [(152, 245), (212, 245), (212, 278), (265, 278), (265, 318), (237, 318),
              (237, 342), (172, 342), (150, 318)], (0.76, 0.75, 0.72, 1)),
    ("Bageriovn", [(265, 190), (370, 193), (388, 213), (388, 318), (265, 318)], (0.72, 0.68, 0.62, 1)),
    ("Gang", [(388, 213), (428, 207), (538, 207), (538, 320), (468, 320), (468, 318), (388, 318)],
     (0.76, 0.75, 0.72, 1)),
    ("Bageri", [(237, 318), (468, 318), (468, 442), (237, 442)], (0.78, 0.74, 0.66, 1)),
    ("Kontor", [(468, 320), (538, 320), (538, 442), (468, 442)], (0.74, 0.76, 0.80, 1)),
    ("Trappe", [(428, 157), (495, 157), (495, 207), (428, 207)], (0.70, 0.70, 0.70, 1)),
    ("Bad", [(495, 157), (540, 157), (540, 207), (495, 207)], (0.72, 0.80, 0.82, 1)),
    ("Bagerbutik", [(538, 235), (662, 235), (662, 405), (640, 442), (538, 442)], (0.84, 0.82, 0.78, 1)),
]


# ------------------------------------------------------------------ builders
def build_wall(bm, a_px, b_px, t, openings, z0=0.0, z1=H):
    a, b = P(*a_px), P(*b_px)
    d = (b - a)
    L = d.length
    d.normalize()
    spans = []
    for q0, q1, sill, head, kind in openings:
        s0 = (P(*q0) - a).dot(d)
        s1 = (P(*q1) - a).dot(d)
        s0, s1 = sorted((max(0, s0), min(L, s1)))
        spans.append((s0, s1, sill, head, kind))
    spans.sort()
    cur = 0.0
    for s0, s1, sill, head, kind in spans:
        add_box(bm, a + d * cur, a + d * s0, t, z0, z1)       # solid pier
        add_box(bm, a + d * s0, a + d * s1, t, z0, sill)      # parapet
        add_box(bm, a + d * s0, a + d * s1, t, head, z1)      # lintel
        cur = s1
    add_box(bm, a + d * cur, b, t, z0, z1)
    return [(a + d * s0, a + d * s1, sill, head, kind, t) for s0, s1, sill, head, kind in spans]


def build_window(bm_glass, bm_frame, a, b, sill, head, kind, t):
    fw = 0.06 if kind in (SHOP, GDOOR) else 0.08     # frame width
    ft = 0.10                                         # frame depth
    d = (b - a).normalized()
    if kind == OPEN:   # open doorway: nothing to build
        return
    if kind == DOOR:   # solid door leaf, slightly recessed
        add_box(bm_frame, a, b, 0.05, 0.0, head)
        return
    # glass pane in the wall centre plane
    add_box(bm_glass, a + d * fw, b - d * fw, 0.02, sill + fw, head - fw)
    # outer frame
    add_box(bm_frame, a, b, ft, sill, sill + fw)
    add_box(bm_frame, a, b, ft, head - fw, head)
    add_box(bm_frame, a, a + d * fw, ft, sill, head)
    add_box(bm_frame, b - d * fw, b, ft, sill, head)
    w = (b - a).length
    if kind == OLD or kind == STD:   # traditional Danish casement: mullion + transom
        mid = a + d * (w / 2)
        add_box(bm_frame, mid - d * fw / 2, mid + d * fw / 2, ft, sill, head)
        tz = sill + (head - sill) * 0.62
        add_box(bm_frame, a, b, ft, tz - fw / 2, tz + fw / 2)
    elif kind == SHOP:               # large display window with a top light
        tz = head - 0.45
        add_box(bm_frame, a, b, ft, tz - fw / 2, tz + fw / 2)
    elif kind == GDOOR:              # full-height glass door + fixed glass sidelight
        mid = a + d * (w / 2)
        add_box(bm_frame, mid - d * fw / 2, mid + d * fw / 2, ft, sill, head)


def polygon_slab(name, poly_px, z0, z1, collection, material):
    bm = bmesh.new()
    pts = [P(*p) for p in poly_px]
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
               for i in range(len(pts))) / 2
    if area < 0:
        pts.reverse()
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    ob = obj_from_bm(bm, name, collection, material)
    return ob, abs(area)


def label(text, poly_px, collection, material, size=0.38):
    pts = [P(*p) for p in poly_px]
    c = sum(pts, Vector()) / len(pts)
    cu = bpy.data.curves.new(f"lbl_{text}", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.005
    ob = bpy.data.objects.new(f"Label_{text}", cu)
    ob.location = (c.x, c.y, 0.02)
    collection.objects.link(ob)
    cu.materials.append(material)
    return ob


# ------------------------------------------------------------------ gaming stations
# Concept: adult gamers in light, open surroundings. Light oak + white desks, pale
# grey chairs, low sage felt dividers. Pods are back-to-back with players facing
# east/west, so daylight comes from the side (no glare on screens, no backs to windows).
DESK_W, DESK_D, DESK_H = 1.20, 0.75, 0.74
CHAIR_ZONE = 0.75
POD_DEPTH = 2 * (DESK_D + CHAIR_ZONE)      # 3.0 m across the pod

# room -> pods as (centre x, centre y, stations per side) in metres; facing axis = X
PODS = {
    "Konditori": [(2.60, 6.07, 2)],                  # 4 stations, walkway to the Gang on the east
    "Bageriovn": [(11.30, 6.20, 2)],                 # 4 stations, clear of the open doorway to the Bageri
    "Bageri": [(10.70, 1.60, 2),                     # 4 stations, west; Gang W + oven-room doorway clear
               (15.90, 1.60, 2)],                    # 4 stations, east in the former Kontor space;
                                                     # ~2.2 m open floor between the pods
}


def make_part(name, boxes, material, collection, parent, matrix):
    bm = bmesh.new()
    for (x0, y0, z0), (x1, y1, z1) in boxes:
        add_box(bm, Vector((x0, (y0 + y1) / 2, 0)), Vector((x1, (y0 + y1) / 2, 0)), y1 - y0, z0, z1)
    ob = obj_from_bm(bm, name, collection, material)
    ob.parent = parent
    ob.matrix_parent_inverse.identity()
    return ob


def build_station(idx, origin, facing_deg, collection, mats, prefix=""):
    """Station in local space: desk centred at origin, player looks along local +Y."""
    root = bpy.data.objects.new(f"{prefix}Station_{idx:02d}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.3
    root.location = origin
    root.rotation_euler = (0, 0, math.radians(facing_deg))
    collection.objects.link(root)
    hw, hd = DESK_W / 2, DESK_D / 2
    m = None
    tag = f"{prefix}{idx:02d}"
    make_part(f"S{tag}_DeskTop", [((-hw, -hd, DESK_H - 0.03), (hw, hd, DESK_H))], mats["oak"], collection, root, m)
    make_part(f"S{tag}_DeskFrame", [((-hw + 0.01, -hd + 0.03, 0), (-hw + 0.05, hd - 0.03, DESK_H - 0.03)),
                                        ((hw - 0.05, -hd + 0.03, 0), (hw - 0.01, hd - 0.03, DESK_H - 0.03)),
                                        ((-hw + 0.05, hd - 0.05, DESK_H - 0.12), (hw - 0.05, hd - 0.03, DESK_H - 0.03))],
              mats["white"], collection, root, m)
    # 27" monitor on a stand, near the back edge, facing the player
    make_part(f"S{tag}_Monitor", [((-0.31, 0.14, DESK_H + 0.12), (0.31, 0.17, DESK_H + 0.49)),
                                      ((-0.02, 0.17, DESK_H), (0.02, 0.21, DESK_H + 0.20)),
                                      ((-0.12, 0.10, DESK_H), (0.12, 0.26, DESK_H + 0.015))],
              mats["black"], collection, root, m)
    make_part(f"S{tag}_Keyboard_Mouse", [((-0.24, -0.25, DESK_H), (0.20, -0.11, DESK_H + 0.02)),
                                             ((0.27, -0.24, DESK_H), (0.33, -0.14, DESK_H + 0.03))],
              mats["black"], collection, root, m)
    # PC tower under the desk, right side
    make_part(f"S{tag}_PC", [((hw - 0.30, -0.10, 0.02), (hw - 0.08, 0.35, 0.49))], mats["white"], collection, root, m)
    # chair (seat centre ~0.75 m in front of the desk centre)
    cy = -hd - 0.38
    make_part(f"S{tag}_Chair", [
        ((-0.30, cy - 0.03, 0.0), (0.30, cy + 0.03, 0.05)),            # base cross
        ((-0.03, cy - 0.30, 0.0), (0.03, cy + 0.30, 0.05)),
        ((-0.03, cy - 0.03, 0.05), (0.03, cy + 0.03, 0.42)),           # gas column
        ((-0.26, cy - 0.25, 0.42), (0.26, cy + 0.25, 0.50)),           # seat
        ((-0.25, cy - 0.33, 0.50), (0.25, cy - 0.26, 1.30)),           # backrest
        ((-0.29, cy - 0.15, 0.50), (-0.26, cy + 0.15, 0.68)),          # armrests
        ((0.26, cy - 0.15, 0.50), (0.29, cy + 0.15, 0.68)),
    ], mats["chair"], collection, root, m)
    return root


def gs_mats():
    def get(name, rgba, rough):
        return bpy.data.materials.get(name) or mat(name, rgba, rough)
    return {
        "oak": get("GS_Oak", (0.78, 0.62, 0.44, 1), 0.45),
        "white": get("GS_White", (0.95, 0.95, 0.94, 1), 0.4),
        "black": get("GS_Black", (0.04, 0.04, 0.05, 1), 0.3),
        "chair": get("GS_Chair_PaleGrey", (0.80, 0.80, 0.78, 1), 0.8),
        "felt": get("GS_Felt_Sage", (0.55, 0.66, 0.57, 1), 0.95),
        "sofa": get("GS_Sofa_WarmGrey", (0.70, 0.68, 0.64, 1), 0.9),
        "rug": get("GS_Rug_OffWhite", (0.90, 0.88, 0.82, 1), 1.0),
    }


def build_pod(rc, room, p, cx, cy, n, idx, mats, prefix=""):
    """Back-to-back pod along Y, players facing east/west. Returns next station index."""
    span = n * DESK_W
    bm = bmesh.new()   # low acoustic divider between the back-to-back desks
    add_box(bm, Vector((cx, cy - span / 2, 0)), Vector((cx, cy + span / 2, 0)), 0.03, DESK_H, DESK_H + 0.40)
    obj_from_bm(bm, f"{prefix}GS_{room}_Pod{p + 1}_Divider", rc, mats["felt"])
    for side in (-1, 1):                     # -1: west row facing east, +1: east row facing west
        for k in range(n):
            y = cy - span / 2 + DESK_W * (k + 0.5)
            x = cx + side * DESK_D / 2
            build_station(idx, (x, y, 0), -90 if side < 0 else 90, rc, mats, prefix)
            idx += 1
    return idx


def add_gaming_stations():
    """Layout A: pods everywhere."""
    top = coll("Gaming_Stations")          # separate top-level group: toggle all off here
    mats = gs_mats()
    idx = 1
    for room, pods in PODS.items():
        rc = coll(f"GS_{room}", top)
        for p, (cx, cy, n) in enumerate(pods):
            idx = build_pod(rc, room, p, cx, cy, n, idx, mats)
    return idx - 1


# Layout B: Konditori + Bageriovn pods as in A; in the Bageri (incl. former Kontor) all
# desks in one row against the facade, facing the windows; console/couch lounge in the
# east Gang by the Bagerbutik.
B_ROW_N, B_ROW_GAP = 8, 0.08
B_ROW_X0 = P(237, 442).x + 0.20 + 0.07         # inner face of the Bageri west wall + margin
B_ROW_Y = 0.20 + DESK_D / 2                     # desk back against the facade's inner face
# lounge (east Gang): TV on the Bageriovn east wall, sofa facing it
LNG_TV_X = P(388, 0).x + T_INT / 2              # wall face
LNG_CY = 6.00
LNG_SOFA_X = 15.90                              # sofa centre (depth along X)
LNG_SOFA_L, LNG_SOFA_D = 2.20, 0.95


def build_lounge(rc, mats):
    tvx, cy = LNG_TV_X, LNG_CY
    def part(name, boxes, m):
        bm = bmesh.new()
        for (x0, y0, z0), (x1, y1, z1) in boxes:
            add_box(bm, Vector((x0, (y0 + y1) / 2, 0)), Vector((x1, (y0 + y1) / 2, 0)), y1 - y0, z0, z1)
        return obj_from_bm(bm, f"B_Lounge_{name}", rc, m)
    # 65" TV wall-mounted + low media console with a games console on it
    part("TV", [((tvx, cy - 0.73, 0.95), (tvx + 0.05, cy + 0.73, 1.78))], mats["black"])
    part("MediaConsole", [((tvx, cy - 0.90, 0.0), (tvx + 0.42, cy + 0.90, 0.45))], mats["oak"])
    part("GamesConsole", [((tvx + 0.08, cy - 0.45, 0.45), (tvx + 0.36, cy - 0.10, 0.53))], mats["white"])
    # rug + coffee table
    part("Rug", [((tvx + 0.70, cy - 1.40, 0.0), (LNG_SOFA_X + 0.30, cy + 1.40, 0.012))], mats["rug"])
    part("CoffeeTable", [((14.55, cy - 0.55, 0.0), (15.10, cy + 0.55, 0.40))], mats["oak"])
    # 3-seat sofa facing west (towards the TV)
    sx0, sx1 = LNG_SOFA_X - LNG_SOFA_D / 2, LNG_SOFA_X + LNG_SOFA_D / 2
    y0, y1 = cy - LNG_SOFA_L / 2, cy + LNG_SOFA_L / 2
    part("Sofa", [((sx0, y0, 0.0), (sx1, y1, 0.42)),                     # base + seat
                  ((sx1 - 0.22, y0, 0.42), (sx1, y1, 0.85)),             # back
                  ((sx0, y0, 0.42), (sx1 - 0.22, y0 + 0.18, 0.62)),      # arms
                  ((sx0, y1 - 0.18, 0.42), (sx1 - 0.22, y1, 0.62))], mats["sofa"])
    part("SofaCushions", [((sx0 + 0.05, y0 + 0.2, 0.42), (sx1 - 0.25, cy - 0.37, 0.50)),
                          ((sx0 + 0.05, cy - 0.33, 0.42), (sx1 - 0.25, cy + 0.33, 0.50)),
                          ((sx0 + 0.05, cy + 0.37, 0.42), (sx1 - 0.25, y1 - 0.2, 0.50))], mats["felt"])


def add_layout_b():
    top = coll("Gaming_Stations_LayoutB")
    mats = gs_mats()
    idx = 1
    for room in ("Konditori", "Bageriovn"):
        rc = coll(f"GSB_{room}", top)
        for p, (cx, cy, n) in enumerate(PODS[room]):
            idx = build_pod(rc, room, p, cx, cy, n, idx, mats, prefix="B_")
    rc = coll("GSB_Bageri_WindowRow", top)
    for k in range(B_ROW_N):
        x = B_ROW_X0 + DESK_W / 2 + k * (DESK_W + B_ROW_GAP)
        build_station(idx, (x, B_ROW_Y, 0), 180, rc, mats, prefix="B_")   # facing the windows (south)
        idx += 1
    build_lounge(coll("GSB_Lounge_Gang", top), mats)
    return idx - 1


# ------------------------------------------------------------------ shop: check-in + tap bar
# Inspired by the current Bagerbutik setup (interior_store*.jpg): one long counter island
# running north-south through the shop with an angled end at the front holding the POS.
# Here: the angled south end is the CHECK-IN facing the entrance door; the rest of the
# island is the BAR with a tap tower and stools. Staff work on the window (east) side with a
# back counter + glass-front fridges; guests keep a clear walkway along the west wall to the
# doorways into the Kontor/Bageri (gaming) and the Gang (lounge).
SH_ISL_X0, SH_ISL_X1 = 20.55, 21.20       # island, customer face / staff face (staff aisle ~0.95 m)
SH_ISL_Y0, SH_ISL_Y1 = 1.60, 5.40         # south (check-in) end / north end
SH_CI_X1, SH_CI_Y1 = 21.75, 2.25          # check-in L wraps across the staff side
SH_BAR_Y0 = 3.20                          # bar section (with overhang + stools) starts here
SH_BACK_X0, SH_BACK_X1 = 22.15, 22.75     # back counter along the east street wall
SH_TOP = 1.04                             # counter height


def mpoly_slab(name, pts, z0, z1, collection, material):
    bm = bmesh.new()
    pts = [Vector((x, y, 0)) for x, y in pts]
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
               for i in range(len(pts))) / 2
    if area < 0:
        pts.reverse()
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    return obj_from_bm(bm, name, collection, material)


def boxes_obj(name, boxes, material, collection):
    bm = bmesh.new()
    for (x0, y0, z0), (x1, y1, z1) in boxes:
        add_box(bm, Vector((x0, (y0 + y1) / 2, 0)), Vector((x1, (y0 + y1) / 2, 0)), y1 - y0, z0, z1)
    return obj_from_bm(bm, name, collection, material)


def add_shop():
    top = coll("Shop_CheckIn_Bar")            # separate top-level group: toggle all off here
    c_ci = coll("Shop_CheckIn", top)
    c_bar = coll("Shop_Bar", top)
    mats = gs_mats()
    m_steel = bpy.data.materials.get("Shop_Steel") or mat("Shop_Steel", (0.80, 0.80, 0.82, 1), 0.25, metal=1.0)
    m_glass = bpy.data.materials["Glass"]
    x0, x1, y0, y1 = SH_ISL_X0, SH_ISL_X1, SH_ISL_Y0, SH_ISL_Y1
    # island footprint: angled corner towards the entrance (like the current counter)
    foot = [(x0, y0 + 0.40), (x0 + 0.40, y0), (SH_CI_X1, y0), (SH_CI_X1, SH_CI_Y1),
            (x1, SH_CI_Y1), (x1, y1), (x0, y1)]
    mpoly_slab("Counter_Body", foot, 0.0, SH_TOP - 0.04, c_ci, mats["white"])
    mpoly_slab("Counter_Top", [(x - 0.0, y) for x, y in foot], SH_TOP - 0.04, SH_TOP, c_ci, mats["oak"])
    # sage felt front panel on the check-in face (soft accent, as on the desk dividers)
    boxes_obj("CheckIn_FrontPanel", [((x0 + 0.42, y0 - 0.02, 0.10), (SH_CI_X1 - 0.08, y0, SH_TOP - 0.12))],
              mats["felt"], c_ci)
    # POS: staff screen facing north, customer display + card terminal facing the guest
    boxes_obj("CheckIn_POS", [((21.25, 1.92, SH_TOP), (21.60, 1.95, SH_TOP + 0.26)),       # staff screen
                              ((21.40, 1.95, SH_TOP), (21.44, 2.02, SH_TOP + 0.12)),        # stand
                              ((20.90, 1.72, SH_TOP), (21.20, 1.75, SH_TOP + 0.18)),        # customer display
                              ((21.62, 1.70, SH_TOP), (21.70, 1.86, SH_TOP + 0.05))],       # card terminal
              mats["black"], c_ci)
    # upright CHECK-IN lettering on the felt panel, facing the entrance
    cu = bpy.data.curves.new("CheckIn_Sign", "FONT")
    cu.body = "CHECK-IN"
    cu.size = 0.16
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude = 0.004
    sign = bpy.data.objects.new("CheckIn_Sign", cu)
    sign.location = ((x0 + 0.42 + SH_CI_X1 - 0.08) / 2, y0 - 0.03, 0.62)
    sign.rotation_euler = (math.radians(90), 0, 0)
    c_ci.objects.link(sign)
    cu.materials.append(mats["white"])

    # bar: customer-side overhang for knee room + 4 stools
    boxes_obj("Bar_Overhang", [((x0 - 0.28, SH_BAR_Y0, SH_TOP - 0.04), (x0, y1, SH_TOP))], mats["oak"], c_bar)
    stools = []
    for k in range(4):
        sy = SH_BAR_Y0 + 0.35 + k * 0.55
        sx = x0 - 0.45
        stools += [((sx - 0.20, sy - 0.20, 0.0), (sx + 0.20, sy + 0.20, 0.03)),      # base
                   ((sx - 0.03, sy - 0.03, 0.03), (sx + 0.03, sy + 0.03, 0.72)),     # column
                   ((sx - 0.17, sy - 0.17, 0.30), (sx + 0.17, sy + 0.17, 0.32)),     # foot ring
                   ((sx - 0.19, sy - 0.19, 0.72), (sx + 0.19, sy + 0.19, 0.78))]     # seat
    boxes_obj("Bar_Stools", stools, mats["chair"], c_bar)
    # tap tower (T-tower, 6 taps) + drip tray, spouts over the staff side
    ty, tx = 4.30, x0 + 0.30
    tower = [((tx - 0.04, ty - 0.04, SH_TOP), (tx + 0.04, ty + 0.04, 1.42)),
             ((tx - 0.05, ty - 0.40, 1.36), (tx + 0.05, ty + 0.40, 1.44))]
    handles = []
    for k in range(6):
        hy = ty - 0.33 + k * 0.132
        tower.append(((tx + 0.05, hy - 0.015, 1.37), (tx + 0.13, hy + 0.015, 1.40)))       # spout
        handles.append(((tx + 0.03, hy - 0.018, 1.44), (tx + 0.07, hy + 0.018, 1.60)))     # handle
    boxes_obj("Bar_TapTower", tower, m_steel, c_bar)
    boxes_obj("Bar_TapHandles", handles, mats["black"], c_bar)
    boxes_obj("Bar_DripTray", [((tx + 0.02, ty - 0.42, SH_TOP), (x1 - 0.02, ty + 0.42, SH_TOP + 0.02))],
              m_steel, c_bar)
    # back counter along the east street wall + glass-front fridges (bar part)
    boxes_obj("Bar_BackCounter_Body", [((SH_BACK_X0, y0, 0.0), (SH_BACK_X1, 6.40, 0.88))], mats["white"], c_bar)
    boxes_obj("Bar_BackCounter_Top", [((SH_BACK_X0 - 0.02, y0, 0.88), (SH_BACK_X1, 6.40, 0.92))], mats["oak"], c_bar)
    bm = bmesh.new()
    for fy in (3.30, 4.00, 4.70):
        add_box(bm, Vector((SH_BACK_X0 - 0.01, fy, 0)), Vector((SH_BACK_X0 - 0.01, fy + 0.62, 0)), 0.02, 0.10, 0.80)
    obj_from_bm(bm, "Bar_Fridge_GlassDoors", c_bar, m_glass)


# ------------------------------------------------------------------ measurements
def text_obj(name, body, loc, rot_z, size, collection, material, parent=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    collection.objects.link(ob)
    cu.materials.append(material)
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse.identity()
    return ob


def dim_line(bm, p0, p1, z=0.012, w=0.025, tick=0.18):
    """Flat dimension line p0->p1 with end ticks, lying on the floor."""
    add_box(bm, p0, p1, w, z - 0.004, z)
    d = (p1 - p0).normalized()
    n = Vector((-d.y, d.x, 0))
    for p in (p0, p1):
        add_box(bm, p - n * tick / 2, p + n * tick / 2, w, z - 0.004, z)


def add_measurements():
    top = coll("Measurements")             # separate top-level group: toggle all off here
    c_rooms = coll("M_Rooms", top)
    c_desks = coll("M_Desks", top)
    m_dim = mat("Dimension_Red", (0.70, 0.08, 0.06, 1), 0.6)
    inset = 0.38

    # rooms: width along the top wall, depth along the west wall, area with the width
    bm = bmesh.new()
    for i, (name, poly, _) in enumerate(ROOMS):
        pts = [P(*p) for p in poly]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        w, d = x1 - x0, y1 - y0
        area = abs(sum(pts[k].x * pts[(k + 1) % len(pts)].y - pts[(k + 1) % len(pts)].x * pts[k].y
                       for k in range(len(pts)))) / 2
        small = min(w, d) < 2.2
        ins = 0.22 if small else inset
        size = 0.15 if small else 0.22
        yl = y1 - ins
        dim_line(bm, Vector((x0, yl, 0)), Vector((x1, yl, 0)))
        text_obj(f"Dim_{name}_{i}_W", f"{w:.1f} m   ({area:.0f} m²)" if not small else f"{w:.1f} m",
                 (x0 + w / 2, yl - 0.2, 0.015), 0, size, c_rooms, m_dim)
        xl = x0 + ins
        dim_line(bm, Vector((xl, y0, 0)), Vector((xl, y1, 0)))
        text_obj(f"Dim_{name}_{i}_D", f"{d:.1f} m", (xl + 0.2, y0 + d / 2, 0.015), math.radians(90),
                 size, c_rooms, m_dim)
    # combined Bageri + Kontor (wall between them is knocked down)
    a, b = P(237, 442), P(538, 442)
    yl = a.y + 0.28
    dim_line(bm, Vector((a.x, yl, 0)), Vector((b.x, yl, 0)))
    text_obj("Dim_Bageri+Kontor_W", f"Bageri + Kontor: {(b - a).length:.1f} m",
             (13.3, yl + 0.17, 0.015), 0, 0.15, c_rooms, m_dim)   # sits in the gap between the pods
    obj_from_bm(bm, "Dim_Lines_Rooms", c_rooms, m_dim)

    # desks: size printed on each desktop, in front of the keyboard, readable from the chair
    for ob in [o for o in bpy.data.objects if o.name.startswith("Station_")]:
        text_obj(f"Dim_{ob.name}", f"{DESK_W * 100:.0f} × {DESK_D * 100:.0f} cm",
                 (0, -DESK_D / 2 + 0.06, DESK_H + 0.002), 0, 0.06, c_desks, m_dim, parent=ob)
    # pods: overall footprint incl. chair space, on the floor at the free end of each pod
    bm = bmesh.new()
    for room, pods in PODS.items():
        for p, (cx, cy, n) in enumerate(pods):
            span = n * DESK_W
            # north end in the Bageri (south end is against the facade), south end elsewhere
            # (north end there collides with the room width line)
            sgn = 1 if room == "Bageri" else -1
            ye = cy + sgn * (span / 2 + 0.22)
            dim_line(bm, Vector((cx - POD_DEPTH / 2, ye, 0)), Vector((cx + POD_DEPTH / 2, ye, 0)), tick=0.12)
            text_obj(f"Dim_Pod_{room}_{p + 1}", f"pod {POD_DEPTH:.1f} × {span:.1f} m (incl. chairs)",
                     (cx, ye + sgn * 0.14, 0.015), 0, 0.11, c_desks, m_dim)
    obj_from_bm(bm, "Dim_Lines_Pods", c_desks, m_dim)

    # ---- Layout B labels
    c_b = coll("M_Desks_LayoutB", top)
    for ob in [o for o in bpy.data.objects if o.name.startswith("B_Station_")]:
        text_obj(f"Dim_{ob.name}", f"{DESK_W * 100:.0f} × {DESK_D * 100:.0f} cm",
                 (0, -DESK_D / 2 + 0.06, DESK_H + 0.002), 0, 0.06, c_b, m_dim, parent=ob)
    bm = bmesh.new()
    for room in ("Konditori", "Bageriovn"):
        for p, (cx, cy, n) in enumerate(PODS[room]):
            span = n * DESK_W
            ye = cy - (span / 2 + 0.22)
            dim_line(bm, Vector((cx - POD_DEPTH / 2, ye, 0)), Vector((cx + POD_DEPTH / 2, ye, 0)), tick=0.12)
            text_obj(f"B_Dim_Pod_{room}_{p + 1}", f"pod {POD_DEPTH:.1f} × {span:.1f} m (incl. chairs)",
                     (cx, ye - 0.14, 0.015), 0, 0.11, c_b, m_dim)
    # window row: overall length + depth incl. chairs
    rx0 = B_ROW_X0
    rx1 = B_ROW_X0 + B_ROW_N * DESK_W + (B_ROW_N - 1) * B_ROW_GAP
    ry = 0.20 + DESK_D + CHAIR_ZONE + 0.25
    dim_line(bm, Vector((rx0, ry, 0)), Vector((rx1, ry, 0)), tick=0.12)
    text_obj("B_Dim_WindowRow", f"window row: {B_ROW_N} desks, {rx1 - rx0:.1f} m long, "
             f"{DESK_D + CHAIR_ZONE:.1f} m deep incl. chairs   ·   free floor behind: "
             f"{3.94 - ry:.1f} m", ((rx0 + rx1) / 2, ry + 0.16, 0.015), 0, 0.13, c_b, m_dim)
    # lounge: viewing distance TV -> sofa front, sofa size
    sofa_front = LNG_SOFA_X - LNG_SOFA_D / 2
    yl = LNG_CY - LNG_SOFA_L / 2 - 0.18          # south side (north side collides with the Gang width)
    dim_line(bm, Vector((LNG_TV_X, yl, 0)), Vector((sofa_front, yl, 0)), tick=0.12)
    text_obj("B_Dim_Lounge_View", f"viewing distance {sofa_front - LNG_TV_X:.1f} m (65\" TV)",
             ((LNG_TV_X + sofa_front) / 2, yl - 0.14, 0.015), 0, 0.11, c_b, m_dim)
    text_obj("B_Dim_Lounge_Sofa", f"sofa {LNG_SOFA_L * 100:.0f} × {LNG_SOFA_D * 100:.0f} cm",
             (LNG_SOFA_X + LNG_SOFA_D / 2 + 0.2, LNG_CY, 0.015), math.radians(90), 0.11, c_b, m_dim)
    obj_from_bm(bm, "B_Dim_Lines", c_b, m_dim)

    # ---- Shop: check-in + bar
    c_s = coll("M_Shop", top)
    bm = bmesh.new()
    def hdim(xa, xb, y, txt, ty_off=0.14):
        dim_line(bm, Vector((xa, y, 0)), Vector((xb, y, 0)), tick=0.12)
        text_obj(f"Shop_Dim_{txt[:14]}", txt, ((xa + xb) / 2, y + ty_off, 0.015), 0, 0.10, c_s, m_dim)
    def vdim(x, ya, yb, txt):
        dim_line(bm, Vector((x, ya, 0)), Vector((x, yb, 0)), tick=0.12)
        text_obj(f"Shop_Dim_{txt[:14]}", txt, (x - 0.14, (ya + yb) / 2, 0.015), math.radians(90), 0.10, c_s, m_dim)
    wall_w = P(538, 0).x + T_INT / 2
    vdim(19.05, SH_ISL_Y0, SH_ISL_Y1, f"counter island {SH_ISL_Y1 - SH_ISL_Y0:.1f} m long, {SH_TOP:.2f} m high")
    hdim(wall_w, SH_ISL_X0 - 0.73, 2.75, f"guest walkway {SH_ISL_X0 - 0.73 - wall_w:.1f} m")
    hdim(SH_ISL_X1, SH_BACK_X0, 5.80, f"staff aisle {SH_BACK_X0 - SH_ISL_X1:.1f} m")
    hdim(SH_ISL_X0 - 0.40, SH_CI_X1, SH_ISL_Y0 - 0.45, f"check-in {SH_CI_X1 - SH_ISL_X0 + 0.0:.1f} m wide", -0.14)
    obj_from_bm(bm, "Shop_Dim_Lines", c_s, m_dim)


def layer_coll(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.name == name:
        return lc
    for ch in lc.children:
        r = layer_coll(name, ch)
        if r:
            return r
    return None


def show_layout(which):
    """Tick/untick the collection checkboxes: 'A' (pods) or 'B' (window row + lounge)."""
    for name, layout in (("Gaming_Stations", "A"), ("M_Desks", "A"),
                         ("Gaming_Stations_LayoutB", "B"), ("M_Desks_LayoutB", "B")):
        layer_coll(name).exclude = (layout != which)


# ------------------------------------------------------------------ main
def main():
    reset_scene()
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"

    root = coll("Bakery_Model")
    c_floor = coll("Floors", root)
    c_walls = coll("Walls", root)
    c_win = coll("Windows_Doors", root)
    c_roof = coll("Roof", root)
    c_lbl = coll("Room_Labels", root)

    m_terrazzo = mat("Terrazzo", (0.62, 0.60, 0.56, 1), 0.35)
    m_plaster = mat("Plaster_White", (0.92, 0.91, 0.88, 1), 0.85)
    m_roof = mat("Roof_Slab", (0.36, 0.36, 0.38, 1), 0.9)
    m_glass = mat("Glass", (0.65, 0.82, 0.90, 1), 0.05, alpha=0.25, transmission=0.9)
    m_shopframe = mat("Frame_Black", (0.03, 0.03, 0.03, 1), 0.4)
    m_oldframe = mat("Frame_Green", (0.25, 0.38, 0.30, 1), 0.5)
    m_door = mat("Door", (0.40, 0.30, 0.22, 1), 0.6)
    m_text = mat("Label", (0.10, 0.10, 0.12, 1), 0.8)

    # floors: base slab + per-room tinted terrazzo
    polygon_slab("Floor_Slab", FOOT, -SLAB, -0.001, c_floor, m_terrazzo)
    areas = {}
    for i, (name, poly, tint) in enumerate(ROOMS):
        m = mat(f"Floor_{name}_{i}", tint, 0.35)
        _, a = polygon_slab(f"Floor_{name}_{i}", poly, -0.001, 0.0, c_floor, m)
        areas[name] = areas.get(name, 0) + a
        label(name.upper(), poly, c_lbl, m_text, 0.30 if a < 6 else 0.38)

    # walls
    bm_ext, bm_int = bmesh.new(), bmesh.new()
    openings = []
    n = len(FOOT)
    for i in range(n):
        openings += build_wall(bm_ext, FOOT[i], FOOT[(i + 1) % n], T_EXT, EXT_OPEN.get(i, []))
    hidden_walls = []
    for a, b, ops, *hidden in INT_WALLS:
        if hidden:   # knocked-down wall: own object, hidden in viewport + render
            bm_h = bmesh.new()
            build_wall(bm_h, a, b, T_INT, ops)
            hidden_walls.append((hidden[0], bm_h))
            continue
        openings += build_wall(bm_int, a, b, T_INT, ops)
    for name, bm_h in hidden_walls:
        ob = obj_from_bm(bm_h, name, c_walls, m_plaster)
        ob.hide_viewport = True
        ob.hide_render = True
        ob.hide_set(True)
    for px, py in PILLARS:
        c = P(px, py)
        add_box(bm_int, c - Vector((0.18, 0, 0)), c + Vector((0.18, 0, 0)), 0.36, 0, H)
    obj_from_bm(bm_ext, "Walls_Exterior", c_walls, m_plaster)
    obj_from_bm(bm_int, "Walls_Interior", c_walls, m_plaster)

    # windows / doors
    bm_glass, bm_shop, bm_old, bm_door = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    counts = {}
    for a, b, sill, head, kind, t in openings:
        counts[kind] = counts.get(kind, 0) + 1
        frame = {SHOP: bm_shop, GDOOR: bm_shop, OLD: bm_old, STD: bm_old, DOOR: bm_door, OPEN: bm_door}[kind]
        build_window(bm_glass, frame, a, b, sill, head, kind, t)
    obj_from_bm(bm_glass, "Glass", c_win, m_glass)
    obj_from_bm(bm_shop, "Frames_Shopfront", c_win, m_shopframe)
    obj_from_bm(bm_old, "Frames_Casement", c_win, m_oldframe)
    obj_from_bm(bm_door, "Doors", c_win, m_door)

    # roof / ceiling slab (ground floor of an older block: flat deck above)
    polygon_slab("Roof_Slab", FOOT, H, H + SLAB, c_roof, m_roof)

    add_gaming_stations()
    add_layout_b()
    add_shop()
    add_measurements()

    # light + world
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 3.5
    sun.angle = math.radians(8)
    so = bpy.data.objects.new("Sun", sun)
    so.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    root.objects.link(so)
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.82, 0.86, 0.92, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    scn.world = world

    total = sum(areas.values())
    return areas, total, counts


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(path, cam_loc, target, ortho=None, hide_roof=False, hide_labels=False):
    scn = bpy.context.scene
    cam = bpy.data.objects.get("Camera")
    if cam is None:
        cd = bpy.data.cameras.new("Camera")
        cam = bpy.data.objects.new("Camera", cd)
        scn.collection.objects.link(cam)
    scn.camera = cam
    cam.location = cam_loc
    look_at(cam, target)
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.lens = 28
    for name, hide in (("Roof", hide_roof), ("Room_Labels", hide_labels)):
        c = bpy.data.collections[name]
        c.hide_render = hide
    # render to a temp file, then swap it in (an image viewer/thumbnailer may briefly lock the target)
    import time
    tmp = os.path.join(os.path.dirname(path), "_tmp_" + os.path.basename(path))
    scn.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    for _ in range(40):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.25)
    print(f"WARNING could not replace locked {path}; new render left at {tmp}")


if __name__ == "__main__":
    areas, total, counts = main()
    scn = bpy.context.scene
    try:
        scn.render.engine = "BLENDER_EEVEE"
    except Exception:
        scn.render.engine = "BLENDER_EEVEE_NEXT"
    scn.render.resolution_x, scn.render.resolution_y = 1600, 1000
    scn.render.film_transparent = False
    try:
        scn.view_settings.view_transform = "Standard"
    except Exception:
        pass

    out = os.path.join(HERE, "renders")
    os.makedirs(out, exist_ok=True)
    cx, cy = P(335, 300).x, P(335, 300).y
    show_layout("A")
    render(os.path.join(out, "01_exterior_SE.png"), (cx + 14, cy - 17, 13), (cx, cy, 0.5), hide_labels=True)
    render(os.path.join(out, "02_cutaway_plan.png"), (cx, cy, 40), (cx, cy, 0), ortho=25, hide_roof=True)
    render(os.path.join(out, "03_cutaway_iso.png"), (cx - 10, cy - 18, 16), (cx, cy, 0), hide_roof=True)
    render(os.path.join(out, "04_gaming_bageri.png"), (13.4, 9.0, 11.5), (13.4, 2.6, 0.3), hide_roof=True, hide_labels=True)
    render(os.path.join(out, "05_gaming_konditori.png"), (6.5, 6.1, 8.5), (2.4, 6.1, 0.3), hide_roof=True, hide_labels=True)
    show_layout("B")
    render(os.path.join(out, "06_layoutB_plan.png"), (cx, cy, 40), (cx, cy, 0), ortho=25, hide_roof=True)
    render(os.path.join(out, "07_layoutB_bageri_lounge.png"), (13.0, 12.0, 12.5), (13.6, 3.2, 0.3),
           hide_roof=True, hide_labels=True)
    render(os.path.join(out, "08_layoutB_lounge.png"), (17.6, 8.6, 7.5), (14.7, 5.9, 0.4),
           hide_roof=True, hide_labels=True)
    render(os.path.join(out, "09_shop_checkin_bar.png"), (17.4, -2.2, 6.8), (21.0, 3.6, 0.8),
           hide_roof=True, hide_labels=True)
    render(os.path.join(out, "10_shop_from_north.png"), (20.6, 10.0, 7.0), (20.9, 2.6, 0.6),
           hide_roof=True, hide_labels=True)
    show_layout("A")   # file opens with Layout A ticked; tick Gaming_Stations_LayoutB to switch
    # leave the roof visible in the saved file
    bpy.data.collections["Roof"].hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "Bakery_Model.blend"))
    print("AREAS", {k: round(v, 1) for k, v in areas.items()}, "TOTAL", round(total, 1))
    print("OPENINGS", counts)
