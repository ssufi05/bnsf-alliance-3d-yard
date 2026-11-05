#!/usr/bin/env python3
"""Build a new GeoPackage that contains every table the 3D viewer uses (your original file is never modified).
Usage:  python build_gpkg.py Alliance_Project_Data.gpkg miscalleanous_nodes.gpkg Alliance_Project_Data_v2.gpkg
Copies the original, cleans your layers, and adds container_spots, trees, water, grass, props, rail_points and roads.
Run it once. After that, edit v2 in QGIS and use export_geojson.py for the viewer."""
import sys, shutil, numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

SRC, MISC, DST = sys.argv[1:4]
UTM = 32614
shutil.copy(SRC, DST)

def read(layer, path=SRC):
    return gpd.read_file(path, layer=layer).to_crs(UTM)

def put(gdf, name):
    gdf.reset_index(drop=True).to_file(DST, layer=name, driver="GPKG")
    print(f"{name:16s}{len(gdf):5d} rows")

# ---- lots: one lot_type spelling, lot_id parts, container length, capacity ----------------
lots = read("lots")
raw = lots.lot_type.astype(str).str.lower()
lots["container_length_ft"] = pd.to_numeric(raw.str.extract(r"(\d+)\s*'")[0]).astype("Int64")
lots["lot_type"] = np.where(raw.str.contains("broken"), "broken_chassis", np.where(raw.str.contains("chassis"), "chassis",
                   np.where(raw.str.contains("container"), "container", "unknown")))
lots["part_id"] = lots.groupby("lot_id").cumcount() + 1

# ---- parking_rows: lot_id matches lots, explicit side/angle reference, full numbering -----
rows = read("parking_rows")
rows["lot_id"] = rows.lot_id.map(lambda x: x if str(x).startswith("LOT") else f"LOT{x}")
rows["segment_id"] = [f"{l}-R{int(n):02d}-{'abcdefgh'[i]}" for l, n, i in zip(rows.lot_id, rows.row_num, rows.groupby(["lot_id", "row_num"]).cumcount())]
lot_u = lots.geometry.union_all()
def side(r):  # stalls go on the side of the row with more lot area (ties: left)
    d = float(r.spot_length_m or 18) / 2
    return "left" if r.geometry.offset_curve(d).intersection(lot_u).length >= r.geometry.offset_curve(-d).intersection(lot_u).length else "right"
rows["stall_side"] = rows.apply(side, axis=1)
rows["stall_angle_ref"] = "row"          # 'row' = angle from the row line; 'perpendicular' = angle off straight-in
nxt, starts = {}, []
for _, r in rows.iterrows():             # spots are numbered along a row, continuing across its segments
    key = (r.lot_id, int(r.row_num))
    if pd.notna(r.start_spot): nxt[key] = int(r.start_spot)
    starts.append(nxt.get(key, 1)); nxt[key] = starts[-1] + int(r.stall_count)
rows["start_spot"] = starts
rows["end_spot"] = rows.start_spot + rows.stall_count.astype(int) - 1

# ---- container_spots: generated from parking_rows (status / height are SIMULATED, is_sim = 1) ------
rng, spots = np.random.default_rng(42), []
for _, r in rows.iterrows():
    ln, n, depth = r.geometry, int(r.stall_count), float(r.spot_length_m or 18.0)
    ang = float(r.stall_angle or 90)
    th = np.radians(ang if r.stall_angle_ref == "row" else 90 - ang)
    sd, pitch = (1 if r.stall_side == "left" else -1), ln.length / n
    for k in range(n):
        a, b = np.array(ln.interpolate(k * pitch).coords[0]), np.array(ln.interpolate((k + 1) * pitch).coords[0])
        u = (b - a) / np.linalg.norm(b - a); nrm = np.array([-u[1], u[0]]) * sd
        v = u * np.cos(th) + nrm * np.sin(th)
        poly = Polygon([a, b, b + v * depth, a + v * depth]).buffer(-0.15, join_style=2)
        num, lv = int(r.start_spot) + k, int(rng.choice([1, 2, 3, 4], p=[.35, .3, .2, .15]))
        spots.append({"spot_id": f"{r.lot_id}-R{int(r.row_num):02d}-{num:03d}", "lot_id": r.lot_id, "row_num": int(r.row_num), "spot_num": num,
                      "stack_levels": lv, "height_m": round(2.6 * lv, 1), "status": str(rng.choice(["loaded", "empty"])), "is_sim": 1, "geometry": poly})
spots = gpd.GeoDataFrame(spots, geometry="geometry", crs=UTM)
cen = spots.copy(); cen["geometry"] = cen.centroid
cnt = gpd.sjoin(cen, lots[["geometry"]], predicate="within").groupby("index_right").size()
lots["capacity"] = pd.array([cnt.get(i, pd.NA) for i in lots.index], dtype="Int64")
put(lots, "lots"); put(rows, "parking_rows"); put(spots, "container_spots")

# ---- tracks, light poles ---------------------------------------------------------------------
tracks = read("tracks"); tracks["length_m"] = tracks.length.round(1); tracks["gauge_mm"] = 1435
put(tracks, "tracks")
lp = read("light_poles"); lp["light_id"] = [f"LP-{i + 1:02d}" for i in range(len(lp))]
put(lp, "light_poles")

# ---- buildings: reprojected to 32614, yours + OSM (assumed heights), same schema ---------------
b = read("buildings"); b["source"], b["levels"], b["osm_id"] = "digitized", pd.array([pd.NA] * len(b), dtype="Int64"), None
bq_all = read("building_query"); bq = bq_all[bq_all.building.notna()].copy()
bq = bq[~bq.geometry.intersects(b.geometry.union_all())].explode(index_parts=False)
lv = pd.to_numeric(bq["building:levels"], errors="coerce")
bq["height_m"] = np.where(lv.notna(), lv * 3.5, bq.building.map({"warehouse": 12, "industrial": 12, "roof": 6, "yes": 8}).fillna(8))
bq["bldg_type"], bq["levels"], bq["source"] = bq.building, lv.astype("Int64"), "osm_assumed_height"
keep = ["name", "bldg_type", "levels", "height_m", "source", "osm_id", "geometry"]
allb = pd.concat([b[keep], bq[keep]], ignore_index=True); allb.insert(0, "building_id", [f"B-{i + 1:02d}" for i in range(len(allb))])
put(gpd.GeoDataFrame(allb, crs=UTM), "buildings")

# ---- roads and barriers from the raw OSM lines ----------------------------------------------
rq = read("roads_query")
rd = rq[rq.highway.notna()].copy()
rd["width_m"] = rd.highway.map({"secondary": 10, "secondary_link": 8, "tertiary": 9, "unclassified": 8, "residential": 7, "service": 6}).fillna(6)
rd.loc[rd.service == "parking_aisle", "width_m"] = 5
put(rd[["osm_id", "name", "ref", "highway", "service", "surface", "maxspeed", "lanes", "oneway", "access", "bridge", "layer", "width_m", "geometry"]], "roads")
bar = rq[rq.barrier.notna()].copy()
bar["barrier_id"] = [f"BR-{i + 1:03d}" for i in range(len(bar))]
bar["barrier_type"] = bar.barrier.map({"fence": "fence", "jersey_barrier": "jersey"})
bar["height_m"] = bar.barrier.map({"fence": 2.4, "jersey_barrier": 0.8}).fillna(1.0); bar["width_m"], bar["source"] = 0.4, "osm"
put(bar[["barrier_id", "barrier_type", "height_m", "width_m", "source", "geometry"]], "barriers")

# ---- extra OSM points: rail switches, gates, wells, towers, masts -----------------------------
pts = read("miscalleanous_nodes", MISC)
near, yard = lots.union_all().buffer(500), read("yard_surface").union_all()
def pick(col, vals, area):
    d = pts[pts[col].isin(vals)]; return d[d.within(area)].copy()
rp = pick("railway", ["switch", "buffer_stop"], near); rp["kind"] = rp.railway
put(rp[["kind", "osm_id", "geometry"]], "rail_points")
props = []
for col, vals, area, h, sz in [("barrier", ["gate", "lift_gate"], near, 1.8, 1.2), ("man_made", ["petroleum_well"], yard, 4.0, 1.5),
                               ("power", ["tower"], near, 35.0, 1.5), ("man_made", ["mast"], near, 30.0, 1.0)]:
    d = pick(col, vals, area); d["kind"], d["height_m"], d["size_m"] = d[col], h, sz; props.append(d[["kind", "height_m", "size_m", "osm_id", "geometry"]])
put(pd.concat(props, ignore_index=True).pipe(lambda d: gpd.GeoDataFrame(d, crs=UTM)), "props")

# ---- water and grass ---------------------------------------------------------------------------
water, kinds = [], []
for g in bq_all[bq_all.natural == "water"].geometry.explode(index_parts=False): water.append(g); kinds.append("pond")
for g in rq[rq.man_made == "reservoir"].geometry:
    if g.is_closed: water.append(Polygon(g.coords)); kinds.append("reservoir")
for g in rq[rq.waterway.notna()].geometry.buffer(3): water.append(g); kinds.append("river")
water_u = unary_union(water)
put(gpd.GeoDataFrame({"kind": kinds}, geometry=water, crs=UTM), "water")
belt = water_u.buffer(40).difference(water_u)
meadow = unary_union(bq_all[bq_all.landuse == "meadow"].geometry).difference(belt)
put(gpd.GeoDataFrame({"kind": ["water_belt", "meadow"]}, geometry=[belt, meadow], crs=UTM), "grass")

# ---- trees: SIMULATED points. Dense in the water belt, medium in meadows, sparse elsewhere --------
MAX_TREES = 1200
blocked = unary_union([yard, rd.geometry.buffer(rd.width_m / 2).union_all(), tracks.buffer(8).union_all(), lots.buffer(5).union_all(),
                       b.geometry.union_all().buffer(3), bq_all.geometry.union_all().buffer(3), water_u])
rest = shapely.box(*lots.total_bounds).buffer(500).difference(belt).difference(meadow)
tr, xy = np.random.default_rng(7), []
for zone, sp in [(belt, 14), (meadow, 45), (rest, 110)]:
    z = zone.difference(blocked)
    if z.is_empty: continue
    x0, y0, x1, y1 = z.bounds
    X, Y = np.meshgrid(np.arange(x0, x1, sp), np.arange(y0, y1, sp))
    X, Y = X.ravel() + tr.uniform(-.4, .4, X.size) * sp, Y.ravel() + tr.uniform(-.4, .4, Y.size) * sp
    m = shapely.contains_xy(z, X, Y); xy += list(zip(X[m], Y[m]))
if len(xy) > MAX_TREES: xy = [xy[i] for i in tr.choice(len(xy), MAX_TREES, replace=False)]
trees = [{"tree_id": f"T-{i + 1:04d}", "height_m": round(tr.uniform(6, 10), 2), "canopy_r_m": round(tr.uniform(2.2, 3.6), 2),
          "shade": int(tr.integers(0, 3)), "is_sim": 1, "geometry": Point(x, y)} for i, (x, y) in enumerate(xy)]
put(gpd.GeoDataFrame(trees, geometry="geometry", crs=UTM), "trees")
print("done ->", DST)
