import { SOURCES, CLICKABLE, LEGEND, SPOT_FRONT } from "./config.js";

// Camera: Google/Apple style. Opens at a 45 deg tilt, rotated -20 deg (north points up-right), and the 3D button toggles flat <-> tilted.
const TILT = 45,
  TILT_CLOSE = 58;
const CAM_BEARING = -20; // change this one number to rotate the whole view
const map = new maplibregl.Map({
  container: "map",
  pitch: TILT,
  bearing: CAM_BEARING,
  minPitch: 0,
  maxPitch: 70,
  center: [-97.348, 33.004],
  zoom: 16,
  dragRotate: true,
  touchPitch: true,
  antialias: true,
  style: {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {},
    layers: [
      {
        id: "bg",
        type: "background",
        paint: { "background-color": "#ebe7de" },
      },
    ],
  },
});
// right-drag / ctrl-drag rotates + tilts (like Google Maps); two-finger twist & drag on touch
map.touchZoomRotate.enableRotation();

const ex = (c, o) => ({
  "fill-extrusion-color": c,
  "fill-extrusion-height": ["get", "height_m"],
  "fill-extrusion-base": o || 0,
  "fill-extrusion-opacity": 1,
});
const exu = (c) => ({
  "fill-extrusion-color": c,
  "fill-extrusion-height": ["get", "top_m"],
  "fill-extrusion-base": ["get", "base_m"],
  "fill-extrusion-opacity": 1,
});
const zw = (a, b) => ["interpolate", ["linear"], ["zoom"], 13, a, 18, b];
const groundSize = (meters, imgPx) => [
  "interpolate",
  ["exponential", 2],
  ["zoom"],
  15,
  (0.4992 * meters) / imgPx,
  22,
  (63.9 * meters) / imgPx,
];
const LAYERS = [
  [
    "Yard pavement",
    {
      id: "yard",
      type: "fill",
      source: "yard_surface",
      paint: { "fill-color": "#d9d8d4" },
    },
  ],
  [
    "Grass",
    {
      id: "grass",
      type: "fill",
      source: "grass",
      paint: { "fill-color": "#cfe4b4" },
    },
  ],
  [
    "Water",
    {
      id: "water",
      type: "fill",
      source: "water",
      paint: { "fill-color": "#a8d3f0" },
    },
  ],

  [
    "Lots",
    {
      id: "lots-fill",
      type: "fill",
      source: "lots",
      paint: {
        "fill-opacity": 0.55,
        "fill-color": [
          "match",
          ["get", "lot_type"],
          "container",
          "#e6e6e2",
          "chassis",
          "#dfe3d2",
          "broken_chassis",
          "#e8d6d2",
          "#e0e0dc",
        ],
      },
    },
  ],
  [
    "Lots",
    {
      id: "lots-line",
      type: "line",
      source: "lots",
      paint: { "line-color": "#fff", "line-width": 1.5 },
    },
  ],
  [
    "Roads",
    {
      id: "roads",
      type: "fill",
      source: "roads",
      paint: { "fill-color": "#4a4d52" },
    },
  ],
  [
    "Roads",
    {
      id: "roads-edge",
      type: "line",
      source: "roads_outline",
      paint: { "line-color": "#3a3d41", "line-width": 0.6 },
    },
  ],
  [
    "Oil stains",
    {
      id: "oil-stain",
      type: "fill",
      source: "oil_stain",
      paint: {
        "fill-color": "#0a0a0b",
        "fill-opacity": ["match", ["get", "kind"], "drip", 0.2, 0.1],
        "fill-antialias": false,
      },
    },
  ],
  [
    "Tracks",
    {
      id: "tracks-bed",
      type: "line",
      source: "tracks",
      paint: {
        "line-color": "#5a5855",
        "line-width": zw(3.5, 8),
      },
    },
  ],
  [
    "Tracks",
    {
      id: "tracks-ties",
      type: "line",
      source: "tracks",
      paint: {
        "line-color": "#dcd6cb",
        "line-width": zw(2.5, 6),
        "line-dasharray": [0.8, 1.2],
      },
    },
  ],
  [
    "Tracks",
    {
      id: "tracks-left-rail",
      type: "line",
      source: "tracks",
      paint: {
        "line-color": "#1c1c1e",
        "line-width": zw(1, 2.2),
        "line-offset": -1.4,
      },
    },
  ],
  [
    "Tracks",
    {
      id: "tracks-right-rail",
      type: "line",
      source: "tracks",
      paint: {
        "line-color": "#1c1c1e",
        "line-width": zw(1, 2.2),
        "line-offset": 1.4,
      },
    },
  ],
  [
    "Gantry paths",
    {
      id: "gantry",
      type: "line",
      source: "gantry_paths",
      paint: { "line-color": "#f5a623", "line-width": 3 },
    },
  ],
  [
    "Switches / buffer stops",
    {
      id: "rail-pts",
      type: "circle",
      source: "rail_points",
      paint: {
        "circle-radius": 3.5,
        "circle-color": "#5b5b5b",
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1.2,
      },
    },
  ],
  [
    "Crossings",
    {
      id: "crossings",
      type: "circle",
      source: "crossings",
      paint: {
        "circle-radius": 3,
        "circle-color": "#ff9f0a",
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1,
      },
    },
  ],
  [
    "Parking stalls",
    {
      id: "stalls",
      type: "line",
      source: "spots",
      paint: { "line-color": "#fff", "line-width": 0.8 },
    },
  ],

  [
    "Road markings",
    {
      id: "crossing-icons",
      type: "symbol",
      source: "crossing_marks",
      minzoom: 16,
      layout: {
        "icon-image": "crossing_mark",
        "icon-size": groundSize(10, 160),
        "icon-rotate": ["get", "rotation_deg"],
        "icon-pitch-alignment": "map",
        "icon-rotation-alignment": "map",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
      },
    },
  ],
  [
    "Road markings",
    {
      id: "stop-icons",
      type: "symbol",
      source: "stop_text",
      minzoom: 16,
      layout: {
        "icon-image": "stop_mark",
        "icon-size": groundSize(1.6, 128),
        "icon-rotate": ["get", "rotation_deg"],
        "icon-pitch-alignment": "map",
        "icon-rotation-alignment": "map",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
      },
    },
  ],
  [
    "Buildings",
    {
      id: "buildings",
      type: "fill-extrusion",
      source: "buildings",
      paint: ex([
        "match",
        ["get", "source"],
        "digitized",
        "#f3d9a4",
        "#f1ede6",
      ]),
    },
  ],
  [
    "Gates, wells, towers",
    {
      id: "props",
      type: "fill-extrusion",
      source: "props",
      filter: ["!=", ["get", "kind"], "tower"],
      paint: ex([
        "match",
        ["get", "kind"],
        "gate",
        "#e57373",
        "lift_gate",
        "#e57373",
        "petroleum_well",
        "#9a9a96",
        "#bdbdb8",
      ]),
    },
  ],
  [
    "Trees (simulated)",
    {
      id: "trunks",
      type: "fill-extrusion",
      source: "trees",
      filter: ["==", ["get", "part"], "trunk"],
      paint: ex("#9b7b5a"),
    },
  ],
  [
    "Trees (simulated)",
    {
      id: "canopy",
      type: "fill-extrusion",
      source: "trees",
      filter: ["==", ["get", "part"], "canopy"],
      paint: ex(
        ["match", ["get", "shade"], 0, "#8fc47a", 1, "#7db86a", "#9fd088"],
        ["get", "base_m"],
      ),
    },
  ],
  [
    "Chassis",
    {
      id: "chassis",
      type: "fill-extrusion",
      source: "chassis",
      paint: exu(["coalesce", ["get", "color"], "#1a1a1a"]),
    },
  ],
  [
    "Containers (simulated)",
    {
      id: "containers",
      type: "fill-extrusion",
      source: "containers",
      paint: exu(["coalesce", ["get", "color"], "#bbb"]),
    },
  ],
  [
    "Power line",
    {
      id: "powerline",
      type: "fill-extrusion",
      source: "power_line",
      paint: exu(["get", "color"]),
    },
  ],
  [
    "Lot labels",
    {
      id: "lot-labels",
      type: "symbol",
      source: "lot_labels",
      layout: {
        "text-field": ["get", "lot_name"],
        "text-font": ["Open Sans Semibold"],
        "text-size": 13,
      },
      paint: {
        "text-color": "#555",
        "text-halo-color": "#fff",
        "text-halo-width": 1.5,
        "text-opacity": 0,
        "text-halo-width": 0,
      },
    },
  ],
];
LAYERS.find((l) => l[1].id === "trunks")[1].paint["fill-extrusion-height"] = [
  "get",
  "height_m",
];

const $ = (id) => document.getElementById(id);
const sheet = $("sheet"),
  menu = $("menu");
const setSheet = (open) => {
  sheet.classList.toggle("open", open);
  menu.setAttribute("aria-expanded", open);
};
menu.onclick = () => setSheet(!sheet.classList.contains("open"));
document.addEventListener(
  "keydown",
  (e) => e.key === "Escape" && setSheet(false),
);

// Camera state management & Street View implementation
let isStreetView = false;
let lastOverviewState = {
  pitch: TILT,
  zoom: 14,
  center: [-97.348, 33.004],
};

const exitStreetView = () => {
  if (!isStreetView) return;
  isStreetView = false;
  $("street-view-bar").classList.remove("active");
  map.flyTo({
    center: map.getCenter(),
    zoom: 16,
    pitch: TILT,
    duration: 1000,
  });
};

const enterStreetView = (lngLat) => {
  lastOverviewState = {
    pitch: map.getPitch(),
    zoom: map.getZoom(),
    center: map.getCenter(),
  };
  isStreetView = true;
  $("street-view-bar").classList.add("active");

  // Ground-level camera pitch (82 deg gives ground person view looking up at cranes and towers)
  map.flyTo({
    center: lngLat,
    zoom: 18.8,
    pitch: 82,
    bearing: map.getBearing(),
    duration: 1200,
  });
};

// camera controls
$("zin").onclick = () => map.zoomIn({ duration: 300 });
$("zout").onclick = () => map.zoomOut({ duration: 300 });
$("compass").onclick = () => map.easeTo({ bearing: 0, duration: 500 });

// Pressing 2D/3D exits street view and resets tilt
$("tilt").onclick = () => {
  if (isStreetView) {
    exitStreetView();
  } else {
    map.easeTo({
      pitch: map.getPitch() > 5 ? 0 : map.getZoom() > 16 ? TILT_CLOSE : TILT,
      duration: 600,
    });
  }
};

$("exit-street-btn").onclick = exitStreetView;

// ---- Drone flight: a path built from real yard data, played frame by frame ----
const DRONE_SPEED = 3; // 1 = original pace, 2 = twice as fast, 0.5 = half speed

let DRONE_PATH = null;
let DRONE_END = 0;

const toRad = (d) => (d * Math.PI) / 180;
const toDeg = (r) => (r * 180) / Math.PI;

// Good-enough centroid: average every point of the outer ring.
const polygonCentroid = (geometry) => {
  const ring = geometry.coordinates[0];
  let lng = 0,
    lat = 0;
  for (const [x, y] of ring) {
    lng += x;
    lat += y;
  }
  return [lng / ring.length, lat / ring.length];
};

const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

// Compass bearing (degrees) from point a to point b, for pointing the
// camera at wherever the drone is headed next.
const bearingBetween = (a, b) => {
  const lat1 = toRad(a[1]),
    lat2 = toRad(b[1]);
  const dLng = toRad(b[0] - a[0]);
  const y = Math.sin(dLng) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
};

// Greedy nearest-neighbor tour: always hop to whichever unvisited stop is
// closest, so the flight sweeps naturally across the yard.
const nearestNeighborTour = (stops) => {
  const remaining = stops.slice();
  const tour = [remaining.shift()];
  while (remaining.length) {
    const last = tour[tour.length - 1];
    let bestIdx = 0;
    let bestDist = Infinity;
    remaining.forEach((stop, i) => {
      const d = distance(last.lnglat, stop.lnglat);
      if (d < bestDist) {
        bestDist = d;
        bestIdx = i;
      }
    });
    tour.push(remaining.splice(bestIdx, 1)[0]);
  }
  return tour;
};

const buildDronePath = async () => {
  const [lots, tracks] = await Promise.all([
    fetch("data/lots.geojson").then((r) => r.json()),
    fetch("data/tracks.geojson").then((r) => r.json()),
  ]);

  // One stop per lot_id — some lots (A, G, J) are split into several
  // polygons, so average those centroids into a single stop per lot.
  const lotCentroids = {};
  lots.features.forEach((f) => {
    const id = f.properties.lot_id;
    const c = polygonCentroid(f.geometry);
    if (!lotCentroids[id]) {
      lotCentroids[id] = {
        sum: [0, 0],
        n: 0,
        name: f.properties.lot_name || id,
      };
    }
    lotCentroids[id].sum[0] += c[0];
    lotCentroids[id].sum[1] += c[1];
    lotCentroids[id].n++;
  });
  const lotStops = Object.values(lotCentroids).map((entry) => ({
    lnglat: [entry.sum[0] / entry.n, entry.sum[1] / entry.n],
    zoom: 15.6,
    pitch: 52, // wide, establishing-shot angle — catches nearby locomotives/cranes too
  }));

  const lotTour = nearestNeighborTour(lotStops);

  // ---- Tracks sweep: one pass along the whole corridor, not stop-by-stop ----
  // Only the named mainline tracks (7201-7209); the many unnamed short
  // connector segments aren't worth individually targeting.
  const namedTrackCoords = tracks.features
    .filter((f) => f.properties.track_id)
    .flatMap((f) => f.geometry.coordinates);

  const lats = namedTrackCoords.map((c) => c[1]);
  const lngs = namedTrackCoords.map((c) => c[0]);
  const bounds = {
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats),
    centerLng: (Math.min(...lngs) + Math.max(...lngs)) / 2,
  };

  // Tracks run roughly north-south here, so sweep along latitude at a
  // zoom wide enough to keep the whole bundle of tracks in frame.
  const TRACK_SWEEP_ZOOM = 15.2;
  const TRACK_SWEEP_PITCH = 58;
  const trackSweepStops = [
    {
      lnglat: [bounds.centerLng, bounds.maxLat],
      zoom: TRACK_SWEEP_ZOOM,
      pitch: TRACK_SWEEP_PITCH,
    },
    {
      lnglat: [bounds.centerLng, (bounds.maxLat + bounds.minLat) / 2],
      zoom: TRACK_SWEEP_ZOOM,
      pitch: TRACK_SWEEP_PITCH,
    },
    {
      lnglat: [bounds.centerLng, bounds.minLat],
      zoom: TRACK_SWEEP_ZOOM,
      pitch: TRACK_SWEEP_PITCH,
    },
  ];

  const tour = [...lotTour, ...trackSweepStops];

  // Turn the ordered tour into timestamped waypoints, with each camera
  // bearing pointed toward the next stop.
  const SECONDS_PER_STOP = 4.5;
  const path = tour.map((stop, i) => {
    const next = tour[i + 1] || stop;
    return [
      i * SECONDS_PER_STOP,
      stop.lnglat[0],
      stop.lnglat[1],
      stop.zoom,
      stop.pitch,
      bearingBetween(stop.lnglat, next.lnglat),
    ];
  });

  DRONE_PATH = path;
  DRONE_END = path[path.length - 1][0];
};

buildDronePath();

// smooth curve through the waypoints
const droneCam = (t) => {
  const P = DRONE_PATH,
    n = P.length;
  t = Math.max(P[0][0], Math.min(DRONE_END, t));
  let i = 0;
  while (i < n - 2 && t > P[i + 1][0]) i++;
  const p1 = P[i],
    p2 = P[i + 1];
  const p0 = P[i - 1] || p1,
    p3 = P[i + 2] || p2;
  const u = (t - p1[0]) / (p2[0] - p1[0]);
  const cr = (a, b, c, d) =>
    0.5 *
    (2 * b +
      (-a + c) * u +
      (2 * a - 5 * b + 4 * c - d) * u * u +
      (-a + 3 * b - 3 * c + d) * u * u * u);
  const v = [1, 2, 3, 4, 5].map((k) => cr(p0[k], p1[k], p2[k], p3[k]));
  return {
    center: [v[0], v[1]],
    zoom: v[2],
    pitch: Math.min(85, Math.max(0, v[3])),
    bearing: v[4],
  };
};

// ---- Cinematic drone camera controller ----

let droneOn = false;
let droneRaf = 0;
let droneRunId = 0;

const droneButton = $("drone");
const NORMAL_MAX_PITCH = 70;
const DRONE_MAX_PITCH = 85;

const stopDrone = () => {
  if (!droneOn) return;

  droneOn = false;
  droneRunId++;

  cancelAnimationFrame(droneRaf);
  droneRaf = 0;

  // Stop any currently running camera transition.
  map.stop();

  // Restore the normal camera limits.
  map.setMaxPitch(NORMAL_MAX_PITCH);

  droneButton.classList.remove("on");
};

const startDrone = () => {
  if (droneOn) return;

  if (!DRONE_PATH) {
    return;
  }

  // Exit ground-level view first.
  if (isStreetView) {
    isStreetView = false;
    $("street-view-bar").classList.remove("active");
  }

  // Cancel any previous camera movement.
  map.stop();

  droneOn = true;
  const currentRun = ++droneRunId;

  droneButton.classList.add("on");

  map.setMaxPitch(DRONE_MAX_PITCH);

  // Start the cinematic flight at its first waypoint.
  const beginFlight = () => {
    if (!droneOn || currentRun !== droneRunId) return;

    const startTime = performance.now();

    const tick = (now) => {
      if (!droneOn || currentRun !== droneRunId) return;

      const elapsed = ((now - startTime) / 1000) * DRONE_SPEED;

      if (elapsed >= DRONE_END) {
        stopDrone();
        return;
      }

      // Interpolate the camera position.
      const camera = droneCam(elapsed);

      map.jumpTo(camera);

      droneRaf = requestAnimationFrame(tick);
    };

    droneRaf = requestAnimationFrame(tick);
  };

  // Register the listener BEFORE starting the transition.
  // This prevents missing the moveend event.
  let flightStarted = false;
  const tryBeginFlight = () => {
    if (flightStarted) return;
    flightStarted = true;
    beginFlight();
  };

  map.once("moveend", tryBeginFlight);

  // Fallback: moveend never fires if the camera is already at the
  // starting waypoint (no movement occurs), so force the flight to
  // begin once the easeTo duration has elapsed regardless.
  setTimeout(tryBeginFlight, 1600);

  // Glide to the starting camera position.
  map.easeTo({
    ...droneCam(0),
    duration: 1500,
    essential: true,
  });
};

// Manual map interaction interrupts the cinematic flight.
["mousedown", "wheel", "touchstart"].forEach((eventName) => {
  map.on(eventName, () => {
    if (droneOn) {
      stopDrone();
    }
  });
});

const sync = () => {
  $("needle").style.transform = `rotate(${-map.getBearing()}deg)`;
  $("needle").style.transformOrigin = "12px 12px";
  const on = map.getPitch() > 5;
  $("tilt").textContent = on ? "2D" : "3D";
  $("tilt").classList.toggle("on", on);
};
map.on("rotate", sync);
map.on("pitch", sync);
sync();

// Drag and Drop Locomotive Pegman Logic
const streetBtn = $("loco-street-btn");
const dragAvatar = $("loco-drag-avatar");
let isDraggingLoco = false;

const onPointerMove = (e) => {
  if (!isDraggingLoco) return;
  dragAvatar.style.left = e.clientX + "px";
  dragAvatar.style.top = e.clientY + "px";
};

const onPointerUp = (e) => {
  if (!isDraggingLoco) return;
  isDraggingLoco = false;
  dragAvatar.style.display = "none";
  document.removeEventListener("pointermove", onPointerMove);
  document.removeEventListener("pointerup", onPointerUp);

  // Calculate map coordinates at drop site
  const rect = map.getCanvas().getBoundingClientRect();
  if (
    e.clientX >= rect.left &&
    e.clientX <= rect.right &&
    e.clientY >= rect.top &&
    e.clientY <= rect.bottom
  ) {
    const point = [e.clientX - rect.left, e.clientY - rect.top];
    const lngLat = map.unproject(point);
    enterStreetView(lngLat);
  }
};

streetBtn.addEventListener("pointerdown", (e) => {
  isDraggingLoco = true;
  dragAvatar.style.left = e.clientX + "px";
  dragAvatar.style.top = e.clientY + "px";
  dragAvatar.style.display = "block";
  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);
});

// Locomotives: SD60M model by OUTPISTON (CC BY-NC-SA 4.0), drawn with three.js
// ---- 3D models (locomotives, cranes) drawn with three.js: one .glb cloned at every point of a geojson ----
const poseCrane = (o, p) => {
  o.rotation.y = -THREE.MathUtils.degToRad(Number(p.heading_deg) || 0);
  const dx = Number(p.trolley_offset_m) || 0; // slide the trolley assembly across the span
  if (dx)
    [
      "trolley",
      "operator_cab",
      "cab_glass",
      "hoist_ropes",
      "spreader",
      "trolley_details",
    ].forEach((n) => {
      const part = o.getObjectByName(n);
      if (part) part.position.x += dx;
    });
};

async function addModelLayer({ id, glb, data, toggle, pose }) {
  let fc;
  try {
    fc = await (await fetch(data)).json();
  } catch (e) {
    console.warn(data + " not loaded", e);
    return;
  }
  if (!fc.features.length) return;
  const origin = fc.features[0].geometry.coordinates;
  const mc = maplibregl.MercatorCoordinate.fromLngLat(origin, 0);
  const sc = mc.meterInMercatorCoordinateUnits();
  const mLat = 111320,
    mLng = 111320 * Math.cos((origin[1] * Math.PI) / 180);
  const layer = {
    id,
    type: "custom",
    renderingMode: "3d",
    visible: true,
    onAdd(m, gl) {
      this.camera = new THREE.Camera();
      this.scene = new THREE.Scene();
      this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a8a, 1.0));
      const sun = new THREE.DirectionalLight(0xffffff, 0.8);
      sun.position.set(-40, 100, 60);
      this.scene.add(sun);
      this.renderer = new THREE.WebGLRenderer({
        canvas: m.getCanvas(),
        context: gl,
        antialias: true,
      });
      this.renderer.autoClear = false;
      this.renderer.outputEncoding = THREE.sRGBEncoding;
      new THREE.GLTFLoader().load(glb, (gltf) => {
        fc.features.forEach((f) => {
          const [lng, lat] = f.geometry.coordinates;
          const o = gltf.scene.clone(true);
          o.position.set(
            (lng - origin[0]) * mLng,
            0,
            -(lat - origin[1]) * mLat,
          );
          pose(o, f.properties);
          this.scene.add(o);
        });
        m.triggerRepaint();
      });
    },
    render(gl, matrix) {
      if (!this.visible) return;
      const l = new THREE.Matrix4()
        .makeTranslation(mc.x, mc.y, mc.z)
        .scale(new THREE.Vector3(sc, -sc, sc))
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      this.camera.projectionMatrix = new THREE.Matrix4()
        .fromArray(matrix)
        .multiply(l);
      this.renderer.resetState();
      this.renderer.render(this.scene, this.camera);
    },
  };
  map.addLayer(layer);
  sheet.addEventListener("change", (e) => {
    if (e.target.id === toggle) {
      layer.visible = e.target.checked;
      map.triggerRepaint();
    }
  });
  return layer;
}

// One .glb drawn at many points, fast: merges the model's meshes by material, then draws every copy as an instance
async function addInstancedLayer({ id, glb, data, toggle, pose, filter }) {
  let fc;
  try {
    fc = await (await fetch(data + "?v=" + Date.now())).json();
  } catch (e) {
    console.warn(data + " not loaded", e);
    return;
  }
  if (filter) fc.features = fc.features.filter(filter);
  if (!fc.features.length) return;
  const origin = fc.features[0].geometry.coordinates;
  const mc = maplibregl.MercatorCoordinate.fromLngLat(origin, 0);
  const sc = mc.meterInMercatorCoordinateUnits();
  const mLat = 111320,
    mLng = 111320 * Math.cos((origin[1] * Math.PI) / 180);
  let rebuildVisibleInstances = null;
  const layer = {
    id,
    type: "custom",
    renderingMode: "3d",
    visible: true,
    onAdd(m, gl) {
      this.camera = new THREE.Camera();
      this.scene = new THREE.Scene();
      this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a8a, 1.0));
      const sun = new THREE.DirectionalLight(0xffffff, 0.8);
      sun.position.set(-40, 100, 60);
      this.scene.add(sun);
      this.renderer = new THREE.WebGLRenderer({
        canvas: m.getCanvas(),
        context: gl,
        antialias: true,
      });
      this.renderer.autoClear = false;
      this.renderer.outputEncoding = THREE.sRGBEncoding;
      const dracoLoader = new THREE.DRACOLoader();

      dracoLoader.setDecoderPath(
        "https://www.gstatic.com/draco/versioned/decoders/1.5.6/",
      );

      const loader = new THREE.GLTFLoader();
      loader.setDRACOLoader(dracoLoader);

      loader.load(glb, (gltf) => {
        // 1. Merge the GLB geometry by material ONCE
        gltf.scene.updateMatrixWorld(true);

        // Find the midpoint along the well car's longitudinal X axis.
        // This becomes the rotation pivot instead of the original GLB origin.
        const modelBounds = new THREE.Box3().setFromObject(gltf.scene);

        const pivotX = (modelBounds.min.x + modelBounds.max.x) / 2;

        const CONTAINER_MATERIAL_NAMES = ["container_paint"];
        const groups = new Map();

        gltf.scene.traverse((n) => {
          if (!n.isMesh) return;

          const g = n.geometry.clone();

          for (const k of Object.keys(g.attributes)) {
            if (
              k !== "position" &&
              k !== "uv" &&
              k !== "normal" &&
              k !== "color"
            ) {
              g.deleteAttribute(k);
            }
          }

          if (!g.attributes.normal) g.computeVertexNormals();

          g.applyMatrix4(n.matrixWorld);

          if (!groups.has(n.material)) groups.set(n.material, []);
          groups.get(n.material).push(g);
        });

        // Keep reusable geometry/material templates
        const templates = [];

        groups.forEach((geoms, material) => {
          const merged = THREE.BufferGeometryUtils.mergeBufferGeometries(
            geoms,
            false,
          );

          // Release temporary geometries after merging
          geoms.forEach((g) => g.dispose());

          if (!merged) {
            console.warn(id + ": could not merge " + material.name);
            return;
          }

          // Move geometry so the midpoint between the two ends
          // becomes the rotation origin.
          merged.translate(-pivotX, 0, 0);

          const isContainer = CONTAINER_MATERIAL_NAMES.includes(material.name);

          let mat = material;

          if (isContainer) {
            mat = material.clone();
            mat.vertexColors = true;
          }

          templates.push({
            geometry: merged,
            material: mat,
            isContainer,
          });
        });

        // 2. Create persistent InstancedMeshes with capacity for the entire yard
        this.wellMeshes = [];

        templates.forEach((t) => {
          const im = new THREE.InstancedMesh(
            t.geometry,
            t.material,
            fc.features.length,
          );

          // Start with zero active instances
          im.count = 0;
          im.frustumCulled = false;
          im.userData.isContainer = t.isContainer;

          this.wellMeshes.push(im);
          this.scene.add(im);
        });

        // Track which GeoJSON features have already been rendered
        const renderedFeatures = new Map();
        let activeCount = 0;

        const dummy = new THREE.Object3D();
        const col = new THREE.Color();

        // Add newly visible features without removing existing ones
        rebuildVisibleInstances = (removeOutside = false) => {
          const canvas = m.getCanvas();
          const width = canvas.clientWidth;
          const height = canvas.clientHeight;
          const margin = 160;

          // When movement ends, reset and rebuild using only the current viewport
          if (removeOutside) {
            renderedFeatures.clear();
            activeCount = 0;

            this.wellMeshes.forEach((im) => {
              im.count = 0;
            });
          }

          let added = 0;

          fc.features.forEach((f, index) => {
            const [lng, lat] = f.geometry.coordinates;
            const point = map.project([lng, lat]);

            const isVisible =
              point.x >= -margin &&
              point.x <= width + margin &&
              point.y >= -margin &&
              point.y <= height + margin;

            // Ignore features outside the viewport
            if (!isVisible) return;

            // Never add the same well car twice
            if (renderedFeatures.has(index)) return;

            const slot = activeCount;

            dummy.position.set(
              (lng - origin[0]) * mLng,
              0,
              -(lat - origin[1]) * mLat,
            );

            dummy.rotation.set(0, 0, 0);
            pose(dummy, f.properties);
            dummy.updateMatrix();

            // Add this well car to every material batch
            this.wellMeshes.forEach((im) => {
              im.setMatrixAt(slot, dummy.matrix);

              if (im.userData.isContainer) {
                col.set(f.properties.color || "#bbbbbb");
                im.setColorAt(slot, col);
              }
            });

            renderedFeatures.set(index, slot);
            activeCount++;
            added++;
          });

          // Update active instance counts and GPU buffers
          this.wellMeshes.forEach((im) => {
            im.count = activeCount;
            im.instanceMatrix.needsUpdate = true;

            if (im.instanceColor) {
              im.instanceColor.needsUpdate = true;
            }
          });

          if (added > 0 || removeOutside) {
            m.triggerRepaint();
          }
        };

        // Initial viewport load
        rebuildVisibleInstances(true);
      });
    },
    render(gl, matrix) {
      if (!this.visible) return;
      const l = new THREE.Matrix4()
        .makeTranslation(mc.x, mc.y, mc.z)
        .scale(new THREE.Vector3(sc, -sc, sc))
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      this.camera.projectionMatrix = new THREE.Matrix4()
        .fromArray(matrix)
        .multiply(l);
      this.renderer.resetState();
      this.renderer.render(this.scene, this.camera);
    },
  };
  map.addLayer(layer);
  // Progressively add newly visible well cars while moving
  let lastProgressiveBuild = 0;

  map.on("move", () => {
    if (!layer.visible || !rebuildVisibleInstances) return;

    const now = performance.now();

    // Limit viewport scans to approximately 10 per second
    if (now - lastProgressiveBuild < 100) return;

    lastProgressiveBuild = now;

    // Add newly visible cars; keep all previously rendered cars
    rebuildVisibleInstances(false);
  });

  // Once movement stops, remove everything outside the viewport
  map.on("moveend", () => {
    if (layer.visible && rebuildVisibleInstances) {
      rebuildVisibleInstances(true);
    }
  });
  sheet.addEventListener("change", (e) => {
    if (e.target.id === toggle) {
      layer.visible = e.target.checked;

      if (layer.visible && rebuildVisibleInstances) {
        rebuildVisibleInstances(true);
      }

      map.triggerRepaint();
    }
  });
  return layer;
}

async function addBarrierModels() {
  const data = "data/barriers.geojson";
  const glb = "data/models/k_wall.glb";

  // Dimensions in meters
  const BARRIER_LENGTH = 3.6576; // 12 feet
  const MIN_GAP = 0.3048; // 1 foot
  const TARGET_HEIGHT = 0.81; // 81 cm

  let fc;

  try {
    fc = await (await fetch(data + "?v=" + Date.now())).json();
  } catch (e) {
    console.warn("Barrier GeoJSON not loaded", e);
    return;
  }

  const features = fc.features.filter(
    (f) =>
      f.geometry?.type === "LineString" &&
      (f.properties.barrier_type === "jersey" ||
        f.properties.barrier_type == null),
  );

  if (!features.length) {
    console.warn("No Jersey barrier LineStrings found");
    return;
  }

  const origin = features[0].geometry.coordinates[0];
  const mc = maplibregl.MercatorCoordinate.fromLngLat(origin, 0);
  const sc = mc.meterInMercatorCoordinateUnits();

  const mLat = 111320;
  const mLng = 111320 * Math.cos((origin[1] * Math.PI) / 180);

  const layer = {
    id: "barriers-3d",
    type: "custom",
    renderingMode: "3d",
    visible: true,

    onAdd(m, gl) {
      this.camera = new THREE.Camera();
      this.scene = new THREE.Scene();

      this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a8a, 1));

      const sun = new THREE.DirectionalLight(0xffffff, 0.8);
      sun.position.set(-40, 100, 60);
      this.scene.add(sun);

      this.renderer = new THREE.WebGLRenderer({
        canvas: m.getCanvas(),
        context: gl,
        antialias: true,
      });

      this.renderer.autoClear = false;
      this.renderer.outputEncoding = THREE.sRGBEncoding;

      new THREE.GLTFLoader().load(
        glb,
        (gltf) => {
          const template = gltf.scene;

          template.updateMatrixWorld(true);

          const bounds = new THREE.Box3().setFromObject(template);
          const size = new THREE.Vector3();
          bounds.getSize(size);

          // The model's long axis is local Z.
          const modelLength = size.z;
          const modelHeight = size.y;

          if (!modelLength || !modelHeight) {
            console.warn("K-wall model has invalid dimensions");
            return;
          }

          // Scale the model to 12 feet long and 81 cm high.
          const scaleZ = BARRIER_LENGTH / modelLength;
          const scaleY = TARGET_HEIGHT / modelHeight;

          // Center the model's original bounding box around its origin.
          const centerX = (bounds.min.x + bounds.max.x) / 2;
          const centerZ = (bounds.min.z + bounds.max.z) / 2;

          // Convert a coordinate to the local Three.js yard coordinate system.
          const toLocal = (coord) => ({
            x: (coord[0] - origin[0]) * mLng,
            z: -(coord[1] - origin[1]) * mLat,
          });

          // Place barriers along every segment of each LineString.
          features.forEach((f) => {
            const coords = f.geometry.coordinates;

            if (coords.length < 2) return;

            // Build the complete line in local meter coordinates.
            const points = coords.map(toLocal);

            let totalLength = 0;

            const segments = [];

            for (let i = 0; i < points.length - 1; i++) {
              const a = points[i];
              const b = points[i + 1];

              const dx = b.x - a.x;
              const dz = b.z - a.z;
              const length = Math.hypot(dx, dz);

              if (length < 0.001) continue;

              segments.push({
                a,
                b,
                dx,
                dz,
                length,
                start: totalLength,
              });

              totalLength += length;
            }

            if (totalLength < BARRIER_LENGTH) {
              console.warn(
                "Barrier line is shorter than one 12-foot K-wall:",
                f.properties.id,
              );
              return;
            }

            // Fit the maximum number of 12-foot barriers while
            // maintaining at least a 1-foot gap.
            const count = Math.floor(
              (totalLength + MIN_GAP) / (BARRIER_LENGTH + MIN_GAP),
            );

            if (count < 1) return;

            // Distribute all remaining space evenly.
            // This also centers the group along the line.
            const gap =
              count > 1
                ? (totalLength - count * BARRIER_LENGTH) / (count - 1)
                : 0;

            // Do not allow the calculated gap to fall below 1 foot.
            if (count > 1 && gap < MIN_GAP - 0.001) {
              console.warn("Calculated K-wall gap is too small");
              return;
            }

            const getPointAtDistance = (distance) => {
              const d = Math.max(0, Math.min(distance, totalLength));

              const segment =
                segments.find((s) => d >= s.start && d <= s.start + s.length) ||
                segments[segments.length - 1];

              const t = Math.max(
                0,
                Math.min(1, (d - segment.start) / segment.length),
              );

              return {
                x: segment.a.x + segment.dx * t,
                z: segment.a.z + segment.dz * t,
                dx: segment.dx,
                dz: segment.dz,
              };
            };

            for (let i = 0; i < count; i++) {
              const centerDistance =
                BARRIER_LENGTH / 2 + i * (BARRIER_LENGTH + gap);

              const p = getPointAtDistance(centerDistance);

              const o = template.clone(true);

              // Rotate the model's local Z axis to follow the line.
              o.rotation.y = Math.atan2(p.dx, p.dz);

              o.scale.set(scaleZ, scaleY, scaleZ);

              // Correct for the GLB's off-center original geometry.
              const offset = new THREE.Vector3(
                -centerX,
                -bounds.min.y,
                -centerZ,
              );

              offset.multiply(o.scale);
              offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), o.rotation.y);

              o.position.set(p.x + offset.x, 0, p.z + offset.z);

              this.scene.add(o);
            }
          });

          m.triggerRepaint();
        },
        undefined,
        (error) => {
          console.error("Failed to load K-wall model", error);
        },
      );
    },

    render(gl, matrix) {
      if (!this.visible) return;

      const l = new THREE.Matrix4()
        .makeTranslation(mc.x, mc.y, mc.z)
        .scale(new THREE.Vector3(sc, -sc, sc))
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));

      this.camera.projectionMatrix = new THREE.Matrix4()
        .fromArray(matrix)
        .multiply(l);

      this.renderer.resetState();
      this.renderer.render(this.scene, this.camera);
    },
  };

  map.addLayer(layer);

  sheet.addEventListener("change", (e) => {
    if (e.target.id === "barriers-t") {
      layer.visible = e.target.checked;
      map.triggerRepaint();
    }
  });
}

// ---- Spot number labels: black square + bold yellow number, placed 1.5m
// past the stall's front edge (set per lot/row in SPOT_FRONT in config.js),
// rotated to match the stall's orientation, and painted underneath the
// containers layer so a parked container correctly occludes its own label. ----
async function addSpotLabels() {
  const spots = await fetch("data/spots.geojson").then((r) => r.json());

  const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  const missingRows = new Set();

  // Distance the number sits past the front edge of the stall
  const OFFSET_M = 1.5;
  const mLat = 111320; // meters per degree of latitude

  const labelFeatures = spots.features.flatMap((f) => {
    const { lot_id, row_num, spot_num } = f.properties;

    // Which end gets the number: "rise" (east) or "set" (west), from config.js
    const side = SPOT_FRONT[lot_id]?.[row_num] ?? SPOT_FRONT[lot_id]?.all;
    if (side !== "rise" && side !== "set") {
      missingRows.add(`${lot_id} row ${row_num}`);
      return [];
    }

    const [p0, p1, p2, p3] = f.geometry.coordinates[0];
    const mLng = mLat * Math.cos((p0[1] * Math.PI) / 180);

    // East/north distance in meters from point a to point b
    const toMeters = (a, b) => [(b[0] - a[0]) * mLng, (b[1] - a[1]) * mLat];
    const dist = (a, b) => Math.hypot(...toMeters(a, b));

    // The short edges are the two ends of the stall.
    const shortIsP0P1 = dist(p0, p1) < dist(p1, p2);
    const endA = shortIsP0P1 ? mid(p0, p1) : mid(p1, p2);
    const endB = shortIsP0P1 ? mid(p2, p3) : mid(p3, p0);

    // Larger longitude = farther east
    const [eastEnd, westEnd] = endA[0] > endB[0] ? [endA, endB] : [endB, endA];
    const frontMid = side === "rise" ? eastEnd : westEnd;
    const backMid = side === "rise" ? westEnd : eastEnd;

    // Push the label OFFSET_M past the front edge, along the stall's long axis.
    const [east, north] = toMeters(backMid, frontMid);
    const len = Math.hypot(east, north) || 1;
    const labelPoint = [
      frontMid[0] + ((east / len) * OFFSET_M) / mLng,
      frontMid[1] + ((north / len) * OFFSET_M) / mLat,
    ];

    // Bearing of the stall's long axis, so the label rotates to match the stall.
    const [axisEast, axisNorth] = toMeters(
      shortIsP0P1 ? p1 : p0,
      shortIsP0P1 ? p2 : p1,
    );
    const bearingDeg = (Math.atan2(axisEast, axisNorth) * 180) / Math.PI;

    return [
      {
        type: "Feature",
        properties: { label: String(spot_num), bearing: bearingDeg },
        geometry: { type: "Point", coordinates: labelPoint },
      },
    ];
  });

  if (missingRows.size) {
    console.warn(
      "No spot number side set in SPOT_FRONT for:",
      [...missingRows].join(", "),
    );
  }

  // Each distinct spot number gets its own baked icon (square + bold yellow
  // digits drawn together in one bitmap), so the number can never scale
  // independently of the square — they're literally the same image.
  const SIZE = 64;
  const uniqueLabels = [
    ...new Set(labelFeatures.map((f) => f.properties.label)),
  ];

  uniqueLabels.forEach((label) => {
    const name = `spot_square_${label}`;
    if (map.hasImage(name)) return;

    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = SIZE;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#000";
    ctx.fillRect(2, 2, SIZE - 4, SIZE - 4);

    ctx.fillStyle = "#f5d90a";
    ctx.font = `bold ${Math.round(SIZE * 0.42)}px "Arial", sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, SIZE / 2, SIZE / 2 + 1);

    map.addImage(name, ctx.getImageData(0, 0, SIZE, SIZE));
  });

  map.addSource("spot_labels", {
    type: "geojson",
    data: { type: "FeatureCollection", features: labelFeatures },
  });

  map.addLayer(
    {
      id: "spot-label-bg",
      type: "symbol",
      source: "spot_labels",
      minzoom: 17,
      layout: {
        "icon-image": ["concat", "spot_square_", ["get", "label"]],
        "icon-size": groundSize(1.0, SIZE),
        "icon-rotate": ["get", "bearing"],
        "icon-rotation-alignment": "map",
        "icon-pitch-alignment": "map",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
      },
    },
    "containers",
  );
}

// ---- Light poles: commercial_lights.glb drawn at every pole position ----
const LIGHT_HEIGHT_M = 30; // finished height of one light, in meters
const LIGHT_ROTATION_DEG = 0; // turns every light; positive = clockwise

async function addLightModels() {
  let poles;
  try {
    const fc = await (
      await fetch("data/light_poles.geojson?v=" + Date.now())
    ).json();
    // Each pole has one oval "ring" part; its center is the pole position.
    poles = fc.features
      .filter((f) => f.properties.part === "ring")
      .map((f) => {
        const pts = f.geometry.coordinates[0].slice(0, -1); // drop repeated end point
        return [0, 1].map(
          (i) => pts.reduce((t, p) => t + p[i], 0) / pts.length,
        );
      });
  } catch (e) {
    console.warn("light_poles.geojson not loaded", e);
    return;
  }
  if (!poles.length) return;

  const origin = poles[0];
  const mc = maplibregl.MercatorCoordinate.fromLngLat(origin, 0);
  const sc = mc.meterInMercatorCoordinateUnits();
  const mLat = 111320,
    mLng = 111320 * Math.cos((origin[1] * Math.PI) / 180);

  const layer = {
    id: "light-models",
    type: "custom",
    renderingMode: "3d",
    visible: true,
    onAdd(m, gl) {
      this.camera = new THREE.Camera();
      this.scene = new THREE.Scene();
      this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a8a, 1.0));
      const sun = new THREE.DirectionalLight(0xffffff, 0.8);
      sun.position.set(-40, 100, 60);
      this.scene.add(sun);
      this.renderer = new THREE.WebGLRenderer({
        canvas: m.getCanvas(),
        context: gl,
        antialias: true,
      });
      this.renderer.autoClear = false;
      this.renderer.outputEncoding = THREE.sRGBEncoding;

      const dracoLoader = new THREE.DRACOLoader();
      dracoLoader.setDecoderPath(
        "https://www.gstatic.com/draco/versioned/decoders/1.5.6/",
      );
      const loader = new THREE.GLTFLoader();
      loader.setDRACOLoader(dracoLoader);

      loader.load(
        "data/models/commercial_lights.glb",
        (gltf) => {
          gltf.scene.updateMatrixWorld(true);

          // Measure the model, then center it, set its base on the ground and size it
          const box = new THREE.Box3().setFromObject(gltf.scene);
          const size = box.getSize(new THREE.Vector3());
          const center = box.getCenter(new THREE.Vector3());
          const s = LIGHT_HEIGHT_M / size.y;
          const normalize = new THREE.Matrix4()
            .makeScale(s, s, s)
            .multiply(
              new THREE.Matrix4().makeTranslation(
                -center.x,
                -box.min.y,
                -center.z,
              ),
            );

          const dummy = new THREE.Object3D();
          const matrix = new THREE.Matrix4();

          // One instanced copy per mesh in the model, so 91 lights stay fast
          gltf.scene.traverse((n) => {
            if (!n.isMesh) return;
            const im = new THREE.InstancedMesh(
              n.geometry,
              n.material,
              poles.length,
            );
            im.frustumCulled = false;

            poles.forEach(([lng, lat], i) => {
              dummy.position.set(
                (lng - origin[0]) * mLng,
                0,
                -(lat - origin[1]) * mLat,
              );
              dummy.rotation.y = -THREE.MathUtils.degToRad(LIGHT_ROTATION_DEG);
              dummy.updateMatrix();
              matrix
                .copy(dummy.matrix)
                .multiply(normalize)
                .multiply(n.matrixWorld);
              im.setMatrixAt(i, matrix);
            });

            this.scene.add(im);
          });
          m.triggerRepaint();
        },
        undefined,
        (e) => console.error("commercial_lights.glb failed to load", e),
      );
    },
    render(gl, matrix) {
      if (!this.visible) return;
      const l = new THREE.Matrix4()
        .makeTranslation(mc.x, mc.y, mc.z)
        .scale(new THREE.Vector3(sc, -sc, sc))
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      this.camera.projectionMatrix = new THREE.Matrix4()
        .fromArray(matrix)
        .multiply(l);
      this.renderer.resetState();
      this.renderer.render(this.scene, this.camera);
    },
  };
  map.addLayer(layer);

  sheet.addEventListener("change", (e) => {
    if (e.target.id === "lights-t") {
      layer.visible = e.target.checked;
      map.triggerRepaint();
    }
  });
}

function addModels() {
  addModelLayer({
    id: "locomotives",
    glb: "data/models/sd60m.glb",
    data: "data/locomotives.geojson",
    toggle: "loco-t",
    pose: (o, p) => {
      o.rotation.y = -THREE.MathUtils.degToRad(p.heading_deg);
    },
  });
  addModelLayer({
    id: "cranes-3d",
    glb: "data/models/mj1200r_rtg.glb",
    data: "data/cranes.geojson",
    toggle: "crane-t",
    pose: poseCrane,
  });
  // Well cars and spine cars share one data file; car_type picks the model.
  const railCarPose = (o, p) => {
    // bearing_deg is the compass direction of the track; the model's long axis is X
    o.rotation.y = THREE.MathUtils.degToRad(90 - p.bearing_deg);
  };
  addInstancedLayer({
    id: "well-cars",
    glb: "data/models/well_cars.glb",
    data: "data/well_cars.geojson",
    toggle: "wells-t",
    pose: railCarPose,
    filter: (f) => f.properties.car_type !== "spine",
  });
  addInstancedLayer({
    id: "spine-cars",
    glb: "data/models/spine_car.glb",
    data: "data/well_cars.geojson",
    toggle: "wells-t",
    pose: railCarPose,
    filter: (f) => f.properties.car_type === "spine",
  });

  addBarrierModels();
  addLightModels();
}

map.on("load", async () => {
  map.setLight({
    anchor: "viewport",
    color: "#fff",
    intensity: 0.45,
    position: [1.4, 210, 40],
  });
  // Load pavement marking images
  const loadImg = (url) =>
    new Promise((resolve, reject) => {
      const r = map.loadImage(url, (err, img) =>
        err ? reject(err) : resolve(img),
      );
      if (r && typeof r.then === "function")
        r.then((x) => resolve(x?.data ?? x), reject);
    });
  for (const n of ["crossing_mark", "stop_mark"]) {
    try {
      const image = await loadImg(`data/icons/${n}.png`);
      if (map.hasImage(n)) map.removeImage(n);
      map.addImage(n, image);
    } catch (error) {
      console.error(`Failed to load pavement marking: ${n}`, error);
    }
  }

  SOURCES.forEach((s) =>
    map.addSource(s, {
      type: "geojson",
      data: `data/${s}.geojson?v=${Date.now()}`,
    }),
  );
  LAYERS.forEach(([, spec]) => map.addLayer(spec));
  // Floating lot name tags: HTML markers lifted above each lot's label point
  try {
    const lotPts = await (await fetch("data/lot_labels.geojson")).json();
    const tags = [];
    for (const f of lotPts.features) {
      const c = f.geometry.coordinates;
      const el = document.createElement("div");
      el.className = "fl";
      const inner = document.createElement("div");
      inner.className = "fl-in";
      const tag = document.createElement("div");
      tag.className = "fl-tag";
      tag.textContent = f.properties.lot_name;
      const stem = document.createElement("div");
      stem.className = "fl-stem";
      inner.append(tag, stem);
      el.append(inner);
      tag.onclick = () =>
        map.flyTo({
          center: c,
          zoom: Math.max(map.getZoom(), 17.5),
          speed: 0.8,
        });
      new maplibregl.Marker({
        element: el,
        anchor: "bottom",
        offset: [0, 4],
      })
        .setLngLat(c)
        .addTo(map);
      tags.push([el, inner]);
    }
    let lastKey = "";
    const syncTags = () => {
      const z = map.getZoom();
      const show =
        map.getLayoutProperty("lot-labels", "visibility") !== "none" &&
        !isStreetView &&
        z >= 14.5;
      const s = Math.min(1.15, Math.max(0.7, 0.7 + (z - 15) * 0.15));
      const key = `${show}|${s.toFixed(2)}`;
      if (key === lastKey) return;
      lastKey = key;
      for (const [el, inner] of tags) {
        el.classList.toggle("off", !show);
        inner.style.transform = `scale(${s})`;
      }
    };
    map.on("render", syncTags);
    syncTags();
  } catch (err) {
    console.error("Failed to build floating lot labels", err);
  }
  map.addLayer({
    id: "crane-pts",
    type: "circle",
    source: "cranes",
    paint: {
      "circle-radius": 18,
      "circle-color": "#f85d13",
      "circle-opacity": 0.01,
    },
  });
  addModels();
  addSpotLabels();
  const groups = [...new Set(LAYERS.map((l) => l[0]))];
  sheet.innerHTML =
    '<div class="sec"><h4>Layers</h4><button class="link" id="all"></button></div>' +
    groups
      .map(
        (g, i) =>
          `<label class="row"><span>${g}</span><span class="sw-t"><input type="checkbox" data-g="${i}" checked><i></i></span></label>`,
      )
      .join("") +
    '<label class="row"><span>Locomotives</span><span class="sw-t"><input type="checkbox" id="loco-t" checked><i></i></span></label>' +
    '<label class="row"><span>Cranes</span><span class="sw-t"><input type="checkbox" id="crane-t" checked><i></i></span></label>' +
    '<label class="row"><span>Well cars</span><span class="sw-t"><input type="checkbox" id="wells-t" checked><i></i></span></label>' +
    '<label class="row"><span>Light poles</span><span class="sw-t"><input type="checkbox" id="lights-t" checked><i></i></span></label>' +
    '<label class="row"><span>Jersey barriers</span><span class="sw-t"><input type="checkbox" id="barriers-t" checked><i></i></span></label>' +
    "<hr><div class='sec'><h4>Go to</h4></div>" +
    '<div class="chips"><button class="chip" data-v="yard">Whole yard</button><button class="chip" data-v="spots">Lot B</button><button class="chip" data-v="buildings">Buildings</button><button class="chip" data-v="water">Pond</button></div>' +
    "<hr><div class='sec'><h4>Legend</h4></div>" +
    LEGEND.map(
      ([c, t]) =>
        `<div class="row leg"><span class="sw" style="background:${c}"></span>${t}</div>`,
    ).join("");

  sheet.addEventListener("change", (e) => {
    if (e.target.id === "crane-t")
      map.setLayoutProperty(
        "crane-pts",
        "visibility",
        e.target.checked ? "visible" : "none",
      );
  });

  const boxes = [...sheet.querySelectorAll("input[data-g]")];
  const apply = (i, on) =>
    LAYERS.filter((l) => l[0] === groups[i]).forEach(([, s]) =>
      map.setLayoutProperty(s.id, "visibility", on ? "visible" : "none"),
    );
  const allBtn = $("all");
  const label = () =>
    (allBtn.textContent = boxes.every((b) => b.checked)
      ? "Hide all"
      : "Show all");
  label();
  sheet.onchange = (e) => {
    if (e.target.dataset.g !== undefined) {
      apply(+e.target.dataset.g, e.target.checked);
      label();
    }
  };
  allBtn.onclick = () => {
    const on = !boxes.every((b) => b.checked);
    boxes.forEach((b, i) => {
      b.checked = on;
      apply(i, on);
    });
    label();
  };

  const meta = await (await fetch("data/meta.json")).json(); // written by export_geojson.py
  const fly = (c) =>
    map.flyTo({
      center: c,
      zoom: 17.3,
      pitch: TILT_CLOSE,
      bearing: CAM_BEARING,
    });
  const go = {
    yard: () =>
      map.fitBounds(
        [
          [meta.yard[0], meta.yard[1]],
          [meta.yard[2], meta.yard[3]],
        ],
        { padding: 60, pitch: TILT, bearing: CAM_BEARING },
      ),
    spots: () => fly(meta.spots),
    buildings: () => fly(meta.buildings),
    water: () =>
      map.flyTo({
        center: meta.water,
        zoom: 16,
        pitch: TILT_CLOSE,
        bearing: 0,
      }),
  };
  sheet.addEventListener("click", (e) => {
    const v = e.target.dataset.v;
    if (v) {
      go[v]();
      if (innerWidth <= 600) setSheet(false);
    }
  });
  $("home").onclick = go.yard;

  map.on("click", (e) => {
    const f = map.queryRenderedFeatures(e.point, {
      layers: CLICKABLE,
    })[0];
    if (!f) {
      if (innerWidth <= 600) setSheet(false);
      return;
    }
    const rows = Object.entries(f.properties)
      .filter(([, v]) => v !== null && v !== "null" && v !== "")
      .map(([k, v]) => `<tr><td>${k}</td><td><b>${v}</b></td></tr>`)
      .join("");
    new maplibregl.Popup({ maxWidth: "280px" })
      .setLngLat(e.lngLat)
      .setHTML(
        `<table class="pop"><tr><th colspan="2">${f.layer.id}</th></tr>${rows}</table>`,
      )
      .addTo(map);
  });
  CLICKABLE.forEach((id) => {
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
  });
});
