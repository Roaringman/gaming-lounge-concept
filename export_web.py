"""Export the bakery model for the three.js web viewer (docs/).

Run:  blender -b --python export_web.py
Writes docs/model.glb and docs/rooms.json.

Every exported object gets a glTF extra  {"grp": <group>}  so the viewer can toggle:
  building, roof, labels, layoutA, layoutB, shop,
  measRooms, measA, measB, measShop, removedWall
Text objects are converted to meshes (glTF has no text type).
"""
import bpy, os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_bakery as bb  # noqa: E402

OUT = os.path.join(HERE, "docs")

# collection name -> group tag (children inherit unless they have their own entry)
COLL_TAG = {
    "Bakery_Model": "building",
    "Roof": "roof",
    "Room_Labels": "labels",
    "Gaming_Stations": "layoutA",
    "Gaming_Stations_LayoutB": "layoutB",
    "Shop_CheckIn_Bar": "shop",
    "Measurements": "measRooms",
    "M_Rooms": "measRooms",
    "M_Desks": "measA",
    "M_Desks_LayoutB": "measB",
    "M_Shop": "measShop",
}


def tag_map():
    tags = {}

    def walk(c, tag):
        tag = COLL_TAG.get(c.name, tag)
        for ob in c.objects:
            tags.setdefault(ob.name, tag)
        for ch in c.children:
            walk(ch, tag)
    for c in bpy.context.scene.collection.children:
        walk(c, None)
    return tags


def unexclude(lc):
    lc.exclude = False
    lc.hide_viewport = False
    for ch in lc.children:
        unexclude(ch)


def text_to_mesh():
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in [o for o in bpy.data.objects if o.type == "FONT"]:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        if not me.materials:
            for m in ob.data.materials:
                me.materials.append(m)
        new = bpy.data.objects.new(ob.name + "__m", me)
        for c in ob.users_collection:
            c.objects.link(new)
        new.parent = ob.parent
        new.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
        new.location, new.rotation_euler, new.scale = ob.location, ob.rotation_euler, ob.scale
        name = ob.name
        bpy.data.objects.remove(ob)
        new.name = name


def rooms_json():
    rooms = []
    for name, poly, _ in bb.ROOMS:
        pts = [bb.P(*p) for p in poly]
        xs, ys = [p.x for p in pts], [p.y for p in pts]
        area = abs(sum(pts[k].x * pts[(k + 1) % len(pts)].y - pts[(k + 1) % len(pts)].x * pts[k].y
                       for k in range(len(pts)))) / 2
        rooms.append({"name": name, "w": round(max(xs) - min(xs), 2), "d": round(max(ys) - min(ys), 2),
                      "area": round(area, 1)})
    return rooms


def main():
    bb.main()
    unexclude(bpy.context.view_layer.layer_collection)
    tags = tag_map()
    text_to_mesh()
    for ob in bpy.data.objects:
        if ob.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(ob)
            continue
        ob.hide_viewport = False
        ob.hide_render = False
        ob.hide_set(False)
        grp = "removedWall" if "REMOVED" in ob.name else tags.get(ob.name, "building")
        ob["grp"] = grp
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, "model.glb"), export_format="GLB", export_extras=True,
        export_yup=True, use_visible=False, export_apply=True, export_lights=False,
        export_cameras=False)
    stations = {"A": len([o for o in bpy.data.objects if o.name.startswith("Station_")]),
                "B": len([o for o in bpy.data.objects if o.name.startswith("B_Station_")])}
    with open(os.path.join(OUT, "rooms.json"), "w", encoding="utf-8") as f:
        json.dump({"rooms": rooms_json(), "stations": stations,
                   "desk_cm": [round(bb.DESK_W * 100), round(bb.DESK_D * 100)],
                   "ceiling_m": bb.H}, f, ensure_ascii=False, indent=1)
    print("EXPORTED", stations, len(bpy.data.objects), "objects")


main()
