import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

// Blender (x, y, z; Z up) -> three.js (x, z, -y; Y up), as done by the glTF exporter.
const B = (x, y, z) => new THREE.Vector3(x, z, -y);

const NOTES = {
  A: "Pods everywhere: 4 in the Konditori, 4 in Bageriovn, 8 in Bageri + Kontor. Daylight from the side.",
  B: "8 desks in one row facing the Bageri windows, console lounge with sofa + 65\" TV in the Gang by the shop.",
};

// Camera presets (Blender coordinates: camera position, target)
const VIEWS = {
  "Overview": [B(3.5, -13, 17), B(11.5, 3.6, 0)],
  "Plan": [B(11.5, 3.58, 31), B(11.5, 3.6, 0)],     // height is refitted to the screen in flyTo
  "Konditori": [B(6.8, 6.1, 8.5), B(2.4, 6.1, 0.3)],
  "Bageriovn": [B(11.3, 0.8, 8.0), B(11.3, 6.0, 0.3)],
  "Bageri": [B(13.4, 9.0, 9.5), B(13.4, 2.0, 0.3)],
  "Lounge": [B(17.8, 8.6, 6.5), B(14.7, 5.9, 0.4)],
  "Check-in & bar": [B(17.4, -2.2, 6.8), B(21.0, 3.6, 0.8)],
  "Street": [B(31, -13, 5), B(17, 2, 1.5)],
};

const state = { layout: "A", meas: true, labels: true, shop: true, roof: false, wall: false };

// ---------------------------------------------------------------- renderer + scene
const app = document.getElementById("app");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
app.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
Object.assign(labelRenderer.domElement.style, { position: "absolute", top: "0", left: "0", pointerEvents: "none" });
app.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
const bgColor = () => getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#e3e8ef";
scene.background = new THREE.Color(bgColor());
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  scene.background = new THREE.Color(bgColor());
});

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.05, 400);
camera.position.copy(VIEWS.Overview[0]);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(VIEWS.Overview[1]);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.screenSpacePanning = true;
controls.maxPolarAngle = Math.PI * 0.495;    // stay above the ground
controls.minDistance = 1.5;
controls.maxDistance = 90;
controls.keyPanSpeed = 25;
controls.listenToKeyEvents(window);

// light: soft sky + a sun from the south-east (the street corner)
scene.add(new THREE.HemisphereLight(0xf4f7ff, 0xb9b2a6, 1.6));
const sun = new THREE.DirectionalLight(0xfff6e8, 2.2);
sun.position.copy(B(30, -22, 30));
sun.target.position.copy(B(11.5, 3.6, 0));
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 20, bottom: -20, near: 1, far: 120 });
sun.shadow.bias = -0.0004;
scene.add(sun, sun.target);

// ground (pavement) for context
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(160, 160),
  new THREE.MeshStandardMaterial({ color: 0xd2d0cb, roughness: 1 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.31;
ground.receiveShadow = true;
scene.add(ground);

// ---------------------------------------------------------------- model
const groups = {};   // grp -> [Object3D]
const pickables = [];

new GLTFLoader().load(
  "./model.glb",
  (gltf) => {
    const root = gltf.scene;
    root.traverse((o) => {
      const grp = o.userData && o.userData.grp;
      if (grp) (groups[grp] ||= []).push(o);
      if (o.isMesh) {
        const isText = /^(Dim_|Label_|B_Dim_|Shop_Dim_|CheckIn_Sign)/.test(o.name) ||
                       /^(Dim_|Label_|B_Dim_|Shop_Dim_)/.test(o.parent?.name || "");
        o.castShadow = !isText && !/Glass|Floor_|Rug/.test(o.name);
        o.receiveShadow = true;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of mats) {
          if (m.transparent) { m.depthWrite = false; m.side = THREE.DoubleSide; }
        }
        if (!isText) pickables.push(o);
      }
    });
    scene.add(root);
    applyState();
    document.getElementById("loading").classList.add("done");
  },
  (ev) => {
    if (ev.total) document.getElementById("loading").textContent =
      `Loading model… ${Math.round((ev.loaded / ev.total) * 100)}%`;
  },
  (err) => {
    document.getElementById("loading").textContent = "Could not load model.glb – serve this folder over http(s).";
    console.error(err);
  }
);

function show(grp, on) { (groups[grp] || []).forEach((o) => { o.visible = on; }); }

function applyState() {
  const A = state.layout === "A";
  show("building", true);
  show("roof", state.roof);
  show("labels", state.labels);
  show("layoutA", A);
  show("layoutB", !A);
  show("shop", state.shop);
  show("measRooms", state.meas);
  show("measA", state.meas && A);
  show("measB", state.meas && !A);
  show("measShop", state.meas && state.shop);
  show("removedWall", state.wall);
  document.getElementById("layA").setAttribute("aria-pressed", String(A));
  document.getElementById("layB").setAttribute("aria-pressed", String(!A));
  document.getElementById("layoutNote").textContent = NOTES[state.layout];
}

// ---------------------------------------------------------------- UI wiring
document.getElementById("layA").onclick = () => { state.layout = "A"; applyState(); };
document.getElementById("layB").onclick = () => { state.layout = "B"; applyState(); };
for (const [id, key] of [["tMeas", "meas"], ["tLabels", "labels"], ["tShop", "shop"], ["tRoof", "roof"], ["tWall", "wall"]]) {
  const el = document.getElementById(id);
  el.checked = state[key];
  el.onchange = () => { state[key] = el.checked; applyState(); };
}

const panel = document.getElementById("panel");
const togglePanel = document.getElementById("togglePanel");
togglePanel.onclick = () => {
  const collapsed = panel.classList.toggle("collapsed");
  togglePanel.setAttribute("aria-expanded", String(!collapsed));
};

// views with a short camera flight
let flight = null;
function flyTo(name) {
  const [pos, tgt] = viewFor(name);
  flight = { t0: performance.now(), dur: 900,
             p0: camera.position.clone(), p1: pos.clone(), q0: controls.target.clone(), q1: tgt.clone() };
  if (name !== "Street" && name !== "Overview" && state.roof) {
    state.roof = false; document.getElementById("tRoof").checked = false; applyState();
  }
}
// Wide views are pulled back on narrow (portrait) screens so the whole building fits.
function viewFor(name) {
  let [pos, tgt] = VIEWS[name];
  const vis = visibleWidth() / window.innerHeight;
  if (name === "Overview" || name === "Street") {
    const k = Math.max(1, 1.35 / vis);
    pos = tgt.clone().add(pos.clone().sub(tgt).multiplyScalar(k));
  }
  if (name === "Plan") {   // fit the 24 m x 9 m footprint into the visible area
    const half = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const h = Math.max(27 / vis, 11) / (2 * half);
    pos = B(11.5, 3.6 - h * 0.002, h);
  }
  return [pos, tgt];
}
const viewsEl = document.getElementById("views");
for (const name of Object.keys(VIEWS)) {
  const b = document.createElement("button");
  b.className = "btn";
  b.textContent = name;
  b.onclick = () => flyTo(name);
  viewsEl.appendChild(b);
}

// rooms table
fetch("./rooms.json").then((r) => r.json()).then((data) => {
  const tb = document.querySelector("#rooms tbody");
  const merged = {};
  for (const r of data.rooms) {
    const m = (merged[r.name] ||= { name: r.name, area: 0, w: r.w, d: r.d, n: 0 });
    m.area += r.area; m.n++;
  }
  let total = 0;
  for (const r of Object.values(merged)) {
    total += r.area;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.name}${r.n > 1 ? ` ×${r.n}` : ""}</td>` +
      `<td class="n">${r.n > 1 ? "" : `${r.w.toFixed(1)} × ${r.d.toFixed(1)} m`}</td>` +
      `<td class="n">${r.area.toFixed(1)} m²</td>`;
    tb.appendChild(tr);
  }
  document.querySelector("#rooms tfoot").innerHTML =
    `<tr><td>Total</td><td class="n">ceiling ${data.ceiling_m} m</td><td class="n">${total.toFixed(0)} m²</td></tr>` +
    `<tr><td colspan="3" style="font-weight:400;color:var(--muted);padding-top:6px">` +
    `${data.stations.A} stations per layout · desks ${data.desk_cm[0]} × ${data.desk_cm[1]} cm · sizes are estimates</td></tr>`;
}).catch(() => {});

// ---------------------------------------------------------------- measure tool
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const measureGroup = new THREE.Group();
scene.add(measureGroup);
const measureOut = document.getElementById("measureOut");
const mToolBtn = document.getElementById("mTool");
let measuring = false;
let firstPoint = null;
let total = 0;
const dotGeo = new THREE.SphereGeometry(0.05, 16, 12);
const dotMat = new THREE.MeshBasicMaterial({ color: 0xb3241b, depthTest: false });
const lineMat = new THREE.LineBasicMaterial({ color: 0xb3241b, depthTest: false });

function setMeasuring(on) {
  measuring = on;
  firstPoint = null;
  mToolBtn.classList.toggle("on", on);
  mToolBtn.textContent = on ? "Measuring… (Esc to stop)" : "Measure distance";
  renderer.domElement.style.cursor = on ? "crosshair" : "";
  measureOut.textContent = on ? "Click the first point." : "Click two points in the model.";
}
mToolBtn.onclick = () => setMeasuring(!measuring);
document.getElementById("mClear").onclick = () => {
  measureGroup.children.slice().forEach((c) => { measureGroup.remove(c); if (c.element) c.element.remove(); });
  measureGroup.traverse((c) => { if (c.element) c.element.remove(); });
  firstPoint = null; total = 0;
  measureOut.textContent = measuring ? "Click the first point." : "Click two points in the model.";
};
window.addEventListener("keydown", (e) => { if (e.key === "Escape" && measuring) setMeasuring(false); });

function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
  const hits = raycaster.intersectObjects(pickables, false).filter((h) => isShown(h.object));
  return hits.length ? hits[0].point : null;
}
function isShown(o) { for (; o; o = o.parent) if (!o.visible) return false; return true; }

let down = null;
renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener("pointerup", (e) => {
  if (!measuring || !down || e.button !== 0) return;
  if (Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;   // was a drag
  const p = pick(e);
  if (!p) return;
  const dot = new THREE.Mesh(dotGeo, dotMat);
  dot.position.copy(p);
  dot.renderOrder = 10;
  measureGroup.add(dot);
  if (!firstPoint) { firstPoint = p; measureOut.textContent = "Click the second point."; return; }
  const geo = new THREE.BufferGeometry().setFromPoints([firstPoint, p]);
  const line = new THREE.Line(geo, lineMat);
  line.renderOrder = 10;
  measureGroup.add(line);
  const d = firstPoint.distanceTo(p);
  const dh = Math.hypot(p.x - firstPoint.x, p.z - firstPoint.z);
  const el = document.createElement("div");
  el.className = "mlabel";
  el.textContent = `${d.toFixed(2)} m`;
  const lbl = new CSS2DObject(el);
  lbl.position.copy(firstPoint).lerp(p, 0.5);
  measureGroup.add(lbl);
  measureOut.textContent = `${d.toFixed(2)} m (horizontal ${dh.toFixed(2)} m, height ${Math.abs(p.y - firstPoint.y).toFixed(2)} m). Click to measure again.`;
  firstPoint = null;
});

// ---------------------------------------------------------------- loop
const hint = document.getElementById("hint");
controls.addEventListener("start", () => { hint.style.opacity = "0"; });

// On wide screens the control panel covers the left side: shift the projection so the
// model is centred in the free area to the right of it.
const PANEL_W = 332;
const desktop = () => window.innerWidth > 720;
function visibleWidth() { return desktop() ? window.innerWidth - PANEL_W : window.innerWidth; }
function onResize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  if (desktop()) camera.setViewOffset(w, h, -PANEL_W / 2, 0, w, h);
  else camera.clearViewOffset();
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  labelRenderer.setSize(w, h);
}
window.addEventListener("resize", onResize);
onResize();
{ // start in the overview, fitted to this screen
  const [p, t] = viewFor("Overview");
  camera.position.copy(p);
  controls.target.copy(t);
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
renderer.setAnimationLoop((now) => {
  if (flight) {
    const t = Math.min(1, (now - flight.t0) / flight.dur);
    const k = ease(t);
    camera.position.lerpVectors(flight.p0, flight.p1, k);
    controls.target.lerpVectors(flight.q0, flight.q1, k);
    if (t >= 1) flight = null;
  }
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
});
