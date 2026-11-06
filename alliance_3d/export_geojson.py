#!/usr/bin/env python3
"""Export the Alliance GeoPackage to GeoJSON (EPSG:4326) for the MapLibre 3D viewer.
Usage (run from alliance_3d):  python export_geojson.py ..\\Alliance_Project_Data_v2.gpkg data
Re-run any time you edit the GeoPackage. Needs: pip install geopandas shapely pyogrio"""

import json
import os
import sys

import geopandas as gpd
import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

GPKG = sys.argv[1] if len(sys.argv) > 1 else "../Alliance_Project_Data_v2.gpkg"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data"
UTM = 32614  # all geometry work happens in meters, export is converted to 4326
os.makedirs(OUT, exist_ok=True)


def read(layer):
    try:
        return gpd.read_file(GPKG, layer=layer).to_crs(UTM)
    except Exception:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=UTM)


def save(gdf, name, cols=None):
    if len(gdf) == 0:
        open(f"{OUT}/{name}.geojson", "w").write(
            '{"type":"FeatureCollection","features":[]}'
        )
    else:
        gdf = gdf[
            (cols or [c for c in gdf.columns if c != "geometry"]) + ["geometry"]
        ].to_crs(4326)
        gdf.to_file(f"{OUT}/{name}.geojson", driver="GeoJSON", COORDINATE_PRECISION=7)
    print(f"{name:14s}{len(gdf):5d} features")


def bounds4326(gdf):
    b = gdf.to_crs(4326).total_bounds
    return [round(float(x), 6) for x in b]


# ---- lots: normalise the inconsistent lot_type spellings -------------------
lots = read("lots")


def lot_type(t):
    t = str(t).lower()
    return (
        "broken_chassis"
        if "broken" in t
        else "chassis"
        if "chassis" in t
        else "container"
        if "container" in t
        else "unknown"
    )


lots["lot_type"] = lots["lot_type"].map(lot_type)
save(lots, "lots", ["lot_id", "lot_name", "lot_type"])
labels = lots.dissolve("lot_id", aggfunc="first").reset_index()
labels["geometry"] = labels.geometry.representative_point()
save(labels, "lot_labels", ["lot_id", "lot_name"])

# ---- parking spots, chassis and containers: READ from the GeoPackage ---------------------
# These three layers are written by regen_spots.py. This script no longer regenerates them,
# so the web viewer always matches what you see in QGIS.
spots = read("container_spots")
save(
    spots,
    "spots",
    [
        c
        for c in [
            "spot_id",
            "lot_id",
            "row_num",
            "spot_num",
            "stack_levels",
            "height_m",
            "status",
            "is_sim",
        ]
        if c in spots.columns
    ],
)
chassis = read("chassis_footprints")
save(
    chassis,
    "chassis",
    [
        c
        for c in ["spot_id", "owner", "color", "base_m", "top_m"]
        if c in chassis.columns
    ],
)
containers = read("containers")
save(
    containers,
    "containers",
    [
        c
        for c in [
            "spot_id",
            "lot_id",
            "row_num",
            "status",
            "owner",
            "color",
            "base_m",
            "top_m",
            "is_sim",
        ]
        if c in containers.columns
    ],
)

# ---- tracks, gantry, crossings --------------------------------------------
tracks = read("tracks")
tracks["named"] = tracks.track_id.notna().astype(int)
save(tracks, "tracks", ["track_id", "track_name", "track_type", "named"])
paths = read("gantry_paths")
save(paths, "gantry_paths", ["track_id", "side"])
save(read("crossings"), "crossings", ["name", "crossing_id", "track_id"])

# ---- STOP signs + railroad-crossing pavement paint (flat on the ground) ----------
# rotation_deg = compass direction of TRAVEL through the marking (0 = north, 90 = east, ...)
# Local frame: +x = across the travel direction, +y = along it. Rotated clockwise by rotation_deg.

CROSSING_LEN = 7.0  # long side of yellow box (runs parallel to the tracks)
CROSSING_DEPTH = 3.2  # short side (in the direction of travel)
BORDER_WIDTH = 0.30  # yellow outline thickness
X_WIDTH = 0.30  # white X stroke thickness
SIGN_W, SIGN_H = 1.6, 0.9  # red STOP panel
BAR_H, BAR_GAP = 0.30, 0.25  # white stop bar ahead of the panel


def _n(v, default=None):
    try:
        f = float(v)
        return default if f != f else f
    except (TypeError, ValueError):
        return default


def place(geom, pt, heading):
    """Rotate a local-frame shape clockwise by compass heading, then move it onto the point."""
    return translate(rotate(geom, -heading, origin=(0, 0)), pt.x, pt.y)


def heading_of(row):
    return _n(row.get("rotation_deg"), 0.0) % 360


paint_rows = []

# ---- railroad crossings: yellow outline + white X ----
rc = read("railroad_crossings")
for _, r in rc.iterrows():
    if r.geometry is None or r.geometry.is_empty:
        continue
    pt, hd = r.geometry, heading_of(r)
    hx, hy = CROSSING_LEN / 2, CROSSING_DEPTH / 2
    outer = box(-hx, -hy, hx, hy)
    inner = box(
        -hx + BORDER_WIDTH, -hy + BORDER_WIDTH, hx - BORDER_WIDTH, hy - BORDER_WIDTH
    )
    ring = Polygon(outer.exterior.coords, [inner.exterior.coords])
    paint_rows.append({"part": "yellow_border", "geometry": place(ring, pt, hd)})

    m = BORDER_WIDTH * 2
    d1 = LineString([(-hx + m, -hy + m), (hx - m, hy - m)])
    d2 = LineString([(-hx + m, hy - m), (hx - m, -hy + m)])
    white_x = unary_union(
        [d1.buffer(X_WIDTH / 2, cap_style=2), d2.buffer(X_WIDTH / 2, cap_style=2)]
    )
    paint_rows.append({"part": "white_x", "geometry": place(white_x, pt, hd)})

# ---- STOP signs: red panel + white stop bar ahead of it ----
stop_signs = read("stop_signs")
for _, r in stop_signs.iterrows():
    if r.geometry is None or r.geometry.is_empty:
        continue
    pt, hd = r.geometry, heading_of(r)
    panel = box(-SIGN_W / 2, -SIGN_H / 2, SIGN_W / 2, SIGN_H / 2)
    y0 = SIGN_H / 2 + BAR_GAP
    bar = box(-SIGN_W / 2, y0, SIGN_W / 2, y0 + BAR_H)
    paint_rows.append({"part": "stop_panel", "geometry": place(panel, pt, hd)})
    paint_rows.append({"part": "stop_text", "geometry": place(bar, pt, hd)})

crossing_paint = (
    gpd.GeoDataFrame(paint_rows, geometry="geometry", crs=UTM)
    if paint_rows
    else gpd.GeoDataFrame({"part": []}, geometry="geometry", crs=UTM)
)
save(crossing_paint, "crossing_paint", ["part"])

cm = rc.copy()
cm["rotation_deg"] = [heading_of(r) for _, r in cm.iterrows()]
save(cm, "crossing_marks", ["rotation_deg"])

# Points for the flat "STOP" lettering (text can't be a polygon fill)
st = stop_signs.copy()
st["rotation_deg"] = [heading_of(r) for _, r in st.iterrows()]
st["text"] = "STOP"
save(st, "stop_text", ["text", "rotation_deg"])

# ---- cranes: one POINT per crane (+ heading etc.); the viewer draws the 3D .glb model at each point ----
import math

paths_ok = len(paths) > 0


def _s(v):
    return "" if v is None or v != v else str(v).strip().lower()


CAB_BEARING = {"north": 0, "east": 90, "south": 180, "west": 270}
TROLLEY_MAX = 2.2  # m each way: 40 ft spreader inside the 55 ft clear width

crane_rows = []
for fid, c in read("gantry_cranes").iterrows():
    if c.geometry is None or c.geometry.is_empty:
        continue

    pt = c.geometry.centroid
    cid = c.get("crane_id") if _s(c.get("crane_id")) else f"RTG-{len(crane_rows) + 1}"
    track, side, bearing = None, None, 0.0

    if paths_ok:
        k = paths.distance(pt).idxmin()
        p = paths.geometry[k]
        track, side = paths.track_id[k], paths.side[k]
        d = p.project(pt)
        a, b = p.interpolate(max(d - 1, 0)), p.interpolate(d + 1)
        bearing = math.degrees(math.atan2(b.x - a.x, b.y - a.y)) % 360

    bearing %= 180  # crane is symmetrical along its travel axis

    manual = _n(c.get("heading_deg"))
    if manual is not None:
        heading = manual % 360
    else:
        heading = bearing
        want = CAB_BEARING.get(_s(c.get("cab_end")))
        if want is not None:
            diff = lambda h: abs((h + 180 - want + 180) % 360 - 180)
            heading = min((bearing, bearing + 180), key=diff)

    # Crane shop orientation correction: RTG-15 through RTG-21
    if cid in {f"RTG-{i}" for i in range(15, 22)}:
        heading = (heading + 90) % 360

    crane_rows.append(
        {
            "crane_id": cid,
            "model": c.get("model") if _s(c.get("model")) else "mj1200r",
            "heading_deg": round(heading, 1),
            "trolley_offset_m": max(
                -TROLLEY_MAX, min(TROLLEY_MAX, _n(c.get("trolley_offset_m"), 0.0))
            ),
            "track_id": track,
            "side": side,
            "geometry": pt,
        }
    )


cr = (
    gpd.GeoDataFrame(crane_rows, geometry="geometry", crs=UTM)
    if crane_rows
    else read("gantry_cranes").iloc[0:0]
)
save(
    cr,
    "cranes",
    ["crane_id", "model", "heading_deg", "trolley_offset_m", "track_id", "side"]
    if crane_rows
    else None,
)

# ---- light poles + transmission line: READ from the GeoPackage (written by regen_spots.py) ----
lp = read("light_pole_parts")
save(
    lp,
    "light_poles",
    [c for c in ["part", "base_m", "top_m", "color"] if c in lp.columns],
)
pl = read("power_line_parts")
save(
    pl,
    "power_line",
    [c for c in ["part", "base_m", "top_m", "color"] if c in pl.columns],
)

# ---- locomotives: READ from the GeoPackage (written by regen_spots.py) ----
loco = read("locomotives")
save(
    loco,
    "locomotives",
    [
        c
        for c in ["track_id", "unit", "train_end", "heading_deg", "model"]
        if c in loco.columns
    ],
)

# ---- well cars: READ from the GeoPackage (written by regen_spots.py) ----
# regen_spots.py stores one LINE per 3-car block; here it becomes a point + compass bearing in lon/lat,
# using the same meters-per-degree math as index.html so the blocks line up with the tracks on screen.
wc = read("well_cars")
wc_rows = []
for tid, idx, owner, color, g in (
    zip(
        wc.to_crs(4326).track_id,
        wc.to_crs(4326).idx,
        wc.to_crs(4326).owner,
        wc.to_crs(4326).color,
        wc.to_crs(4326).geometry,
    )
    if len(wc)
    else []
):
    (x0, y0), (x1, y1) = g.coords[0][:2], g.coords[-1][:2]
    mlng = 111320.0 * math.cos(math.radians((y0 + y1) / 2))
    brg = math.degrees(math.atan2((x1 - x0) * mlng, (y1 - y0) * 111320.0)) % 360
    wc_rows.append(
        {
            "track_id": tid,
            "idx": int(idx),
            "bearing_deg": round(brg, 2),
            "owner": owner,
            "color": color,
            "geometry": Point((x0 + x1) / 2, (y0 + y1) / 2),
        }
    )
save(
    gpd.GeoDataFrame(wc_rows, geometry="geometry", crs=4326) if wc_rows else wc,
    "well_cars",
    ["track_id", "idx", "bearing_deg", "owner", "color"],
)

# ---- buildings: yours + OSM context (assumed heights) -----------------------
b = read("buildings")
if "source" not in b.columns:
    b["source"] = "digitized"  # v2 already labels digitized vs OSM buildings
bq = bq_all = read("building_query")
bq = bq[bq.building.notna()].copy()
bq = bq[
    ~bq.geometry.intersects(b.geometry.union_all())
]  # drop OSM duplicates of your own
dflt = {"warehouse": 12, "industrial": 12, "roof": 6, "yes": 8}
lv = bq["building:levels"].astype(float)
bq["height_m"] = np.where(lv.notna(), lv * 3.5, bq.building.map(dflt).fillna(8))
bq["bldg_type"], bq["source"] = bq.building, "osm_assumed_height"
bq = bq.explode(index_parts=False)
import pandas as pd

keep = ["name", "bldg_type", "height_m", "source", "geometry"]
save(
    gpd.GeoDataFrame(pd.concat([b[keep], bq[keep]], ignore_index=True), crs=UTM),
    "buildings",
    ["name", "bldg_type", "height_m", "source"],
)

# ---- roads (buffered to true width) and barriers (from OSM until you digitise) ----
rq = read("roads_query")
rd = rq[rq.highway.notna()].copy()
w = {
    "secondary": 10,
    "secondary_link": 8,
    "tertiary": 9,
    "unclassified": 8,
    "residential": 7,
    "service": 6,
}
ROAD_WIDTH_SCALE = 1.5  # make every road this many times wider
rd["width_m"] = rd.highway.map(w).fillna(6)
rd.loc[rd.service == "parking_aisle", "width_m"] = 5
rd["width_m"] = rd["width_m"] * ROAD_WIDTH_SCALE
rd["geometry"] = rd.geometry.buffer(
    rd.width_m / 2, cap_style=1
)  # round caps so joints connect cleanly
save(
    rd,
    "roads",
    [
        "name",
        "highway",
        "service",
        "surface",
        "maxspeed",
        "oneway",
        "access",
        "width_m",
    ],
)
# One merged outline for ALL roads, so the edge line only follows the outer boundary
road_outline = gpd.GeoDataFrame(
    {"kind": ["road"]}, geometry=[unary_union(rd.geometry)], crs=UTM
)
save(road_outline, "roads_outline", ["kind"])
bar = rq[rq.barrier.notna()].copy()
bar["height_m"] = bar.barrier.map({"fence": 2.4, "jersey_barrier": 0.8}).fillna(1.0)
bar["geometry"] = bar.geometry.buffer(0.2, cap_style=2)
bar["source"] = "osm"
save(bar, "barriers", ["barrier", "height_m", "source"])
save(read("yard_surface"), "yard_surface", ["name", "surface_type"])

# ---- rail points and props (gates, wells, towers, masts): READ from the v2 GeoPackage ----------
# build_gpkg.py already filtered these OSM nodes into the "rail_points" and "props" layers.
import pandas as pd
import shapely

yard = read("yard_surface").union_all()
rp = read("rail_points")
save(rp, "rail_points", ["kind"])
props = read("props")
if len(props):
    props["geometry"] = [
        g.buffer(float(s) if s == s else 1.0, cap_style=3)
        for g, s in zip(props.geometry, props.get("size_m", [1.0] * len(props)))
    ]
save(props, "props", ["kind", "height_m"])

# ---- water, grass and scattered trees --------------------------------------------
water = list(bq_all[bq_all.natural == "water"].geometry.explode(index_parts=False))
water += [
    Polygon(g.coords) for g in rq[rq.man_made == "reservoir"].geometry if g.is_closed
]
water += list(rq[rq.waterway.notna()].geometry.buffer(3))
water_u = unary_union(water)
save(
    gpd.GeoDataFrame({"kind": ["water"] * len(water)}, geometry=water, crs=UTM),
    "water",
    ["kind"],
)
# ---- grass: use the hand-edited 'grass' layer if it has features, else derive from OSM ----
g_user = read("grass")
if len(g_user):
    if "kind" in g_user.columns:
        k = g_user["kind"].fillna("meadow").astype(str)
    else:
        k = pd.Series(["meadow"] * len(g_user), index=g_user.index)
    belt = (
        unary_union(g_user[k == "water_belt"].geometry)
        if (k == "water_belt").any()
        else Polygon()
    )
    meadow = unary_union(g_user[k != "water_belt"].geometry)
    save(g_user.assign(kind=k), "grass", ["kind"])
else:
    belt = water_u.buffer(40).difference(water_u)
    meadow = unary_union(bq_all[bq_all.landuse == "meadow"].geometry).difference(belt)
    save(
        gpd.GeoDataFrame(
            {"kind": ["water_belt", "meadow"]}, geometry=[belt, meadow], crs=UTM
        ),
        "grass",
        ["kind"],
    )

# Trees are SIMULATED: dense in the water belt, medium in meadows, sparse elsewhere; never on pavement,
# roads, tracks, lots or buildings. Edit spacing / MAX_TREES to taste.
MAX_TREES = 1200
blocked = unary_union(
    [
        yard,
        rd.geometry.union_all(),
        tracks.buffer(8).union_all(),
        lots.buffer(5).union_all(),
        b.geometry.union_all().buffer(3),
        bq_all.geometry.union_all().buffer(3),
        water_u,
    ]
)
win = shapely.box(*lots.total_bounds).buffer(500)
rest = win.difference(belt).difference(meadow)
tr = np.random.default_rng(7)
xy = []
for zone, sp in [(belt, 14), (meadow, 45), (rest, 110)]:
    z = zone.difference(blocked)
    if z.is_empty:
        continue
    x0, y0, x1, y1 = z.bounds
    X, Y = np.meshgrid(np.arange(x0, x1, sp), np.arange(y0, y1, sp))
    X, Y = (
        X.ravel() + tr.uniform(-0.4, 0.4, X.size) * sp,
        Y.ravel() + tr.uniform(-0.4, 0.4, Y.size) * sp,
    )
    m = shapely.contains_xy(z, X, Y)
    xy += list(zip(X[m], Y[m]))
if len(xy) > MAX_TREES:
    xy = [xy[i] for i in tr.choice(len(xy), MAX_TREES, replace=False)]
trees = []
for x, y in xy:
    h, r, shade = tr.uniform(6, 10), tr.uniform(2.2, 3.6), int(tr.integers(0, 3))
    trees.append(
        {
            "part": "trunk",
            "base_m": 0,
            "height_m": round(h * 0.4, 1),
            "shade": shade,
            "geometry": Point(x, y).buffer(0.4, resolution=1),
        }
    )
    trees.append(
        {
            "part": "canopy",
            "base_m": round(h * 0.35, 1),
            "height_m": round(h, 1),
            "shade": shade,
            "geometry": Point(x, y).buffer(r, resolution=2),
        }
    )
save(
    gpd.GeoDataFrame(trees, geometry="geometry", crs=UTM) if trees else rd.iloc[0:0],
    "trees",
    ["part", "base_m", "height_m", "shade"],
)

# ---- camera presets for the viewer ------------------------------------------
c = lambda g: [
    round((bounds4326(g)[0] + bounds4326(g)[2]) / 2, 6),
    round((bounds4326(g)[1] + bounds4326(g)[3]) / 2, 6),
]
json.dump(
    {
        "yard": bounds4326(lots),
        "spots": c(spots),
        "buildings": c(b),
        "water": c(gpd.GeoDataFrame(geometry=water[:1], crs=UTM)),
    },
    open(f"{OUT}/meta.json", "w"),
)
print("done ->", OUT)
