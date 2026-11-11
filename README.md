# Gaming lounge concept

Rough 3D model of the former bakery (ground floor, ~154 m²) with three
gaming-station layouts (A: pods, B: window row + lounge, C: maximum capacity with
wall rows), plus a browser viewer that can be hosted on GitHub Pages.

## Files

| Path | What |
|---|---|
| `build_bakery.py` | Builds the Blender model (`Bakery_Model.blend`) and the renders in `renders/` |
| `export_web.py` | Rebuilds the model and exports `docs/model.glb` + `docs/rooms.json` for the viewer |
| `docs/` | The web viewer (three.js, no build step): `index.html`, `main.js`, `model.glb`, `rooms.json` |
| `Material/` | Source material (plan drawing, photos, rough measures) – kept local, not in the repository |

## Update the viewer after changing the model

```bash
"C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python export_web.py
```

Every exported object carries a glTF extra `grp` (`building`, `roof`, `labels`, `layoutA`,
`layoutB`, `layoutC`, `shop`, `measRooms`, `measA`, `measB`, `measC`, `measShop`, `removedWall`) that the viewer
uses for its toggles.

## Run the viewer locally

The page loads `model.glb` with `fetch`, so it must be served over http (opening the file
directly won't work). Any static server works, e.g.:

```bash
npx http-server docs -p 8765
```

## Host on GitHub Pages

1. Push this folder to a GitHub repository (the `docs/` folder must be on the default branch).
2. In the repository: **Settings → Pages → Build and deployment → Deploy from a branch**,
   branch `main`, folder **`/docs`**.
3. The viewer is then live at `https://<user>.github.io/<repo>/`.

`docs/.nojekyll` makes Pages serve the files as-is. three.js is loaded from jsDelivr
(pinned to 0.170.0), so there is nothing to build.

## Viewer controls

- **Layout A / B / C** switch, toggles for measurements, room names, check-in & bar, roof and the
  removed Bageri/Kontor wall.
- Preset views (Overview, Plan, rooms, Lounge, Check-in & bar, Street).
- Rotate: left-drag · Pan: right-drag, Shift+drag, two fingers or arrow keys · Zoom: wheel / pinch.
- **Measure tool**: click two points to get the distance (total, horizontal and height).

All sizes are estimates: only Konditori (5.5 × 4 m), Bageri (4 × 8 m) and Kontor (4 × 2.5 m)
come from rough measurements; everything else is scaled from the plan drawing.
