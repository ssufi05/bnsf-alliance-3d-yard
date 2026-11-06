#!/usr/bin/env python3
"""Rebuild container_spots, chassis_footprints and containers from parking_rows in your v2 GeoPackage.

Each parking_rows line is the CENTER of a row of angled (or straight) stalls.
Inputs per row (fields in parking_rows):
  stall_angle      degrees. 0 = straight-in (when stall_angle_ref = 'perpendicular')
  stall_angle_ref  'perpendicular' = angle measured from straight-in (90 deg to the row)  <- recommended
                   'row'           = angle measured from the row line itself (0 is not usable here)
  stall_side       'left' / 'right'. With a center line this just mirrors which way the stalls lean.
  spot_width_m     width across a stall. Default 3.353 (11 ft)
  spot_length_m    length of a stall along its own axis. Picks the unit size:
                     17.5 -> 53 ft,  16 -> 40 ft,  10 -> 20 ft   (nearest match; blank = 17.5)
  start_spot       first stall number of this segment. 1 or higher is honored exactly.
                   Blank / 0 / negative = continue after the previous segment of the same row.
  stall_count      is RECALCULATED = line length / pitch, pitch = width / sin(angle from row)
Also builds the 3D light poles (light_pole_parts) and the transmission line (power_line_parts)
from the light_poles layer and the kind='tower' points in props.
Usage:  python regen_spots.py Alliance_Project_Data_v2.gpkg
Close QGIS editing (save + toggle off) first, then reload the layers in QGIS afterwards."""

import math
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

GPKG = sys.argv[1] if len(sys.argv) > 1 else "Alliance_Project_Data_v2.gpkg"
UTM = 32614
FT = 0.3048
GAP = 0.15  # shrink each stall so neighbours show a gap (m)
UNIT_W = 8.5 * FT  # footprint width for all unit sizes
CHASSIS_TOP = 1.40  # deck height above ground (m)
CHASSIS_BOTTOM = 0.45
CONTAINER_H = 2.90  # 9 ft 6 in high-cube box (m); sits on the deck

# stall length (m) -> unit size (ft)
LENGTH_TO_SIZE = {17.5: 53, 16.0: 40, 10.0: 20}
# unit size -> footprint length (m)
UNIT_L = {53: 53 * FT, 40: 40 * FT, 20: 20 * FT}

# (owner key, size ft, container hex, percent of ALL units). Percents are normalised per size,
# so the 53/40/20 split itself comes from the spot_length_m of your rows, not from here.
DIST = [
    # 53 ft domestic
    ("jbhunt", 53, "#F2F0EA", 18),
    ("amazon", 53, "#232F3E", 5),
    ("schneider", 53, "#F36F21", 7),
    ("hubgroup", 53, "#0072CE", 6),
    ("emp", 53, "#006B45", 6),
    ("umax", 53, "#00529B", 5),
    ("swift", 53, "#003DA5", 4),
    ("other_domestic", 53, "#8A8F98", 19),
    # 40 ft international
    ("msc", 40, "#FFCC00", 4),
    ("maersk", 40, "#42B0D5", 3),
    ("cosco", 40, "#005BAC", 2),
    ("cmacgm", 40, "#003A70", 2),
    ("hapag", 40, "#FF7900", 1.5),
    ("one", 40, "#E5007D", 1),
    ("evergreen", 40, "#00843D", 1.5),
    ("other_ocean", 40, "#8A8F98", 5),
    # 20 ft international
    ("msc", 20, "#FFCC00", 2),
    ("cosco", 20, "#005BAC", 1.5),
    ("maersk", 20, "#42B0D5", 1),
    ("cmacgm", 20, "#003A70", 1),
    ("evergreen", 20, "#00843D", 0.5),
    ("hapag", 20, "#FF7900", 0.5),
    ("other_ocean", 20, "#8A8F98", 3.5),
]
BY_SIZE, VALID = {}, {}
for _o, _s, _h, _p in DIST:
    BY_SIZE.setdefault(_s, []).append((_o, _h, _p))
    VALID.setdefault(_s, set()).add((_o, _h))


def pick_unit(size, rng_):
    """weighted random (owner, container color) for this unit size"""
    items = BY_SIZE[size]
    p = np.array([i[2] for i in items], float)
    i = rng_.choice(len(items), p=p / p.sum())
    return items[i][0], items[i][1]


CHASSIS_BY_OWNER = {"jbhunt": "#F6442A"}  # everyone else gets a random one below
OTHER_CHASSIS = ["#1A1A1A", "#8FC1E3", "#F5B27A"]  # black, light blue, light orange
KEEP_OLD = False  # False = reroll every unit with the new distribution; set True afterwards so they stop reshuffling

rows_raw = gpd.read_file(GPKG, layer="parking_rows")
orig_crs = rows_raw.crs
rows = rows_raw.to_crs(UTM)
old = (
    gpd.read_file(GPKG, layer="container_spots")
    .drop(columns="geometry")
    .set_index("spot_id")
)
old = old[~old.index.duplicated(keep="first")]
if "spot_width_m" not in rows.columns:
    rows["spot_width_m"] = 11 * FT
if "spot_length_m" not in rows.columns:
    rows["spot_length_m"] = 17.5
rng, spots, chassis, boxes = np.random.default_rng(42), [], [], []
try:  # keep each unit's owner and colors on later runs so they don't reshuffle
    _oc = (
        gpd.read_file(GPKG, layer="containers")
        .drop(columns="geometry")
        .set_index("spot_id")
    )
    _oc = _oc[~_oc.index.duplicated(keep="first")]
    if "owner" not in _oc.columns:
        raise ValueError("old layout")
    old_own, old_box = _oc.owner.to_dict(), _oc.color.to_dict()
    # older runs had no size_ft column: everything was 53 ft
    old_size = (
        _oc.size_ft.to_dict()
        if "size_ft" in _oc.columns
        else {s: 53 for s in _oc.index}
    )
    old_ch = (
        gpd.read_file(GPKG, layer="chassis_footprints")
        .drop(columns="geometry")
        .set_index("spot_id")
        .color.to_dict()
    )
except Exception:
    old_own, old_box, old_ch, old_size = {}, {}, {}, {}

crng = np.random.default_rng(11)
next_free = {}  # (lot, row) -> next unused spot number
taken = {}  # (lot, row) -> set of spot numbers already assigned


def val(v, default):
    """Blank / NULL fields (a brand-new line in QGIS) come through as NaN -> use the default."""
    return default if v is None or pd.isna(v) else float(v)


def size_for(length_m):
    """Nearest known stall length -> unit size in ft."""
    best = min(LENGTH_TO_SIZE, key=lambda L: abs(L - length_m))
    return LENGTH_TO_SIZE[best], abs(best - length_m)


# ---------- 3D light poles + transmission line (looks, in metres) ----------
POLE_SEG = 10  # taper steps of the pole shaft
POLE_R_BASE, POLE_R_TOP = 0.9, 0.3  # shaft radius at the bottom / top
POLE_HEAD_A, POLE_HEAD_B = 3.0, 1.8  # oval head semi-axes
POLE_HEAD_ROT = 0.0  # oval rotation (radians)
LINE_MERGE = (
    40.0  # tower points closer than this count as one structure (fids 28/29/45)
)
LINE_N_SEG = 8  # lattice steps per tower
LINE_W_BASE, LINE_W_NECK = 2.4, 0.7  # tower half-width at ground / at the arm
LINE_ARM = 5.0  # conductor offset left/right of the tower centre
LINE_WIRE_W, LINE_WIRE_T = 0.7, 0.45  # wire width / thickness (exaggerated)
LINE_SAG = 0.025  # sag as a fraction of span length
LINE_INS = 2.0  # insulator length


def _ellipse(cx, cy, rx, ry, rot=0.0, n=12):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append(
            (
                cx + x * math.cos(rot) - y * math.sin(rot),
                cy + x * math.sin(rot) + y * math.cos(rot),
            )
        )
    return pts


def _box(u0, u1, v0, v1, th):
    """Rectangle in the tower frame (u along the line, v across), rotated by th."""
    c, s = math.cos(th), math.sin(th)
    return [
        (u * c - v * s, u * s + v * c)
        for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    ]


def _part(c, rings, base, top, color, kind):
    return {
        "rings": [[(c[0] + x, c[1] + y) for x, y in r] for r in rings],
        "part": kind,
        "base_m": round(float(base), 2),
        "top_m": round(float(top), 2),
        "color": color,
    }


def points_with_height(gdf):
    return [
        ((g.x, g.y), None if pd.isna(h) else float(h))
        for g, h in zip(gdf.geometry, gdf.height_m)
    ]


def build_light_poles(poles):
    """poles: [((x, y), height_m or None)] -> list of extrusion parts"""
    out = []
    for c, h in poles:
        H = h if h else 30.0
        top = H - 1.6
        for i in range(POLE_SEG):
            r = POLE_R_BASE + (POLE_R_TOP - POLE_R_BASE) * ((i + 0.5) / POLE_SEG)
            out.append(
                _part(
                    c,
                    [_ellipse(0, 0, r, r, 0, 10)],
                    i * top / POLE_SEG,
                    (i + 1) * top / POLE_SEG,
                    "#e4e4e6",
                    "shaft",
                )
            )
        out.append(
            _part(
                c,
                [_ellipse(0, 0, POLE_HEAD_A, POLE_HEAD_B, POLE_HEAD_ROT, 24)],
                H - 0.6,
                H,
                "#9a9a9e",
                "ring",
            )
        )
        for k in range(8):  # 8 luminaires around the oval
            a = 2 * math.pi * k / 8
            x, y = POLE_HEAD_A * math.cos(a), POLE_HEAD_B * math.sin(a)
            px = x * math.cos(POLE_HEAD_ROT) - y * math.sin(POLE_HEAD_ROT)
            py = x * math.sin(POLE_HEAD_ROT) + y * math.cos(POLE_HEAD_ROT)
            out.append(
                _part(
                    c,
                    [_ellipse(px, py, 0.6, 0.6, 0, 8)],
                    H - 1.6,
                    H - 0.6,
                    "#fff4c8",
                    "light",
                )
            )
    return out


def build_power_line(towers):
    """towers: [((x, y), height_m or None)] chained south -> north"""
    raw = sorted(((c, h or 35.0) for c, h in towers), key=lambda t: t[0][1])
    T = []
    for c, h in raw:
        if T and math.hypot(c[0] - T[-1]["c"][0], c[1] - T[-1]["c"][1]) < LINE_MERGE:
            t = T[-1]
            t["n"] += 1
            t["c"] = (
                (t["c"][0] * (t["n"] - 1) + c[0]) / t["n"],
                (t["c"][1] * (t["n"] - 1) + c[1]) / t["n"],
            )
            t["h"] = max(t["h"], h)
        else:
            T.append({"c": c, "h": h, "n": 1})
    print(f"power line: {len(raw)} tower points -> {len(T)} structures")
    for i, t in enumerate(T):
        p0, p1 = T[max(0, i - 1)]["c"], T[min(len(T) - 1, i + 1)]["c"]
        t["th"] = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        t["nx"], t["ny"] = -math.sin(t["th"]), math.cos(t["th"])  # left-hand normal
        t["top"] = t["h"] * 0.85  # crossarm level
        t["att"] = t["top"] - 1.2 - LINE_INS  # wire attachment height

    out = []
    for t in T:
        th, c, top = t["th"], t["c"], t["top"]
        wd = lambda z: LINE_W_BASE + (LINE_W_NECK - LINE_W_BASE) * (z / top)
        for i in range(LINE_N_SEG):
            z0, z1 = i * top / LINE_N_SEG, (i + 1) * top / LINE_N_SEG
            wm = wd((z0 + z1) / 2)
            for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                out.append(
                    _part(
                        c,
                        [
                            _box(
                                su * wm - 0.25,
                                su * wm + 0.25,
                                sv * wm - 0.25,
                                sv * wm + 0.25,
                                th,
                            )
                        ],
                        z0,
                        z1,
                        "#b9bcc0",
                        "tower_leg",
                    )
                )
        for i in range(LINE_N_SEG + 1):
            z = i * top / LINE_N_SEG
            wo, wi = wd(z) + 0.25, wd(z) - 0.25
            out.append(
                _part(
                    c,
                    [_box(-wo, wo, -wo, wo, th), _box(-wi, wi, -wi, wi, th)],
                    z,
                    z + 0.35,
                    "#a4a7ab",
                    "tower_frame",
                )
            )
        out.append(
            _part(
                c,
                [_box(-0.25, 0.25, -0.25, 0.25, th)],
                top,
                t["h"],
                "#b9bcc0",
                "tower_peak",
            )
        )
        out.append(
            _part(
                c,
                [_box(-0.4, 0.4, -LINE_ARM - 0.6, LINE_ARM + 0.6, th)],
                top - 1.2,
                top - 0.6,
                "#8c8f94",
                "crossarm",
            )
        )
        for o in (-LINE_ARM, 0, LINE_ARM):
            out.append(
                _part(
                    c,
                    [_box(-0.2, 0.2, o - 0.2, o + 0.2, th)],
                    t["att"],
                    top - 1.2,
                    "#d8e2e8",
                    "insulator",
                )
            )

    for a, b in zip(T, T[1:]):  # 3 sagging conductors per span
        for o in (-LINE_ARM, 0, LINE_ARM):
            A = (a["nx"] * o, a["ny"] * o)
            B = (
                b["c"][0] - a["c"][0] + b["nx"] * o,
                b["c"][1] - a["c"][1] + b["ny"] * o,
            )
            dx, dy = B[0] - A[0], B[1] - A[1]
            L = math.hypot(dx, dy)
            ux, uy, hw = dx / L, dy / L, LINE_WIRE_W / 2
            S = max(8, math.ceil(L / 8))
            zf = lambda t: (
                a["att"] + (b["att"] - a["att"]) * t - LINE_SAG * L * 4 * t * (1 - t)
            )
            for s in range(S):
                t0, t1 = s / S, (s + 1) / S
                p0 = (A[0] + dx * t0, A[1] + dy * t0)
                p1 = (A[0] + dx * t1, A[1] + dy * t1)
                ring = [
                    (p0[0] - uy * hw, p0[1] + ux * hw),
                    (p0[0] + uy * hw, p0[1] - ux * hw),
                    (p1[0] + uy * hw, p1[1] - ux * hw),
                    (p1[0] - uy * hw, p1[1] + ux * hw),
                ]
                out.append(
                    _part(
                        a["c"],
                        [ring],
                        min(zf(t0), zf(t1)),
                        max(zf(t0), zf(t1)) + LINE_WIRE_T,
                        "#3b3b40",
                        "wire",
                    )
                )
    return out


def parts_to_gdf(parts):
    rows_ = [
        {
            **{k: v for k, v in p.items() if k != "rings"},
            "geometry": Polygon(p["rings"][0], p["rings"][1:]),
        }
        for p in parts
    ]
    return gpd.GeoDataFrame(rows_, geometry="geometry", crs=UTM)


for i, r in rows.iterrows():
    ln = r.geometry
    if ln is None or ln.is_empty:
        print(f"  SKIPPED a parking_rows feature with no geometry (fid {i})")
        continue
    if pd.isna(r.lot_id) or pd.isna(r.row_num):
        print(
            f"  SKIPPED a line with blank lot_id or row_num (length {ln.length:.0f} m): fill them in QGIS and rerun"
        )
        continue
    if ln.geom_type == "MultiLineString":
        ln = list(ln.geoms)[0]
    depth = val(r.spot_length_m, 17.5)
    size, miss = size_for(depth)
    if miss > 0.5:
        print(
            f"  note: row {int(r.row_num)} spot_length_m={depth} isn't 17.5/16/10 -> treated as {size} ft"
        )
    width = val(r.spot_width_m, 11 * FT)
    if pd.isna(r.stall_angle):
        print(
            f"  note: row {int(r.row_num)} has no stall_angle -> using 30 (perpendicular); set it in QGIS"
        )
    ang = val(r.stall_angle, 30.0)
    ref = "perpendicular" if pd.isna(r.stall_angle_ref) else str(r.stall_angle_ref)
    th = np.radians(ang if ref == "row" else 90 - ang)  # angle from the row line
    th = max(th, np.radians(10))  # guard against divide-by-~0
    sd = -1 if r.stall_side == "right" else 1
    pitch = width / np.sin(th)  # spacing along the line (= width when straight)
    n = max(1, round(ln.length / pitch))
    pitch = ln.length / n
    rows.loc[i, "stall_count"] = n
    key = (r.lot_id, int(r.row_num))
    sv = r.start_spot
    if pd.isna(sv) or sv < 1:
        start = next_free.get(key, 1)
    else:
        start = int(sv)
    used = taken.setdefault(key, set())
    clash = used & set(range(start, start + n))
    if clash:
        print(
            f"  WARNING: row {key[1]} spots {min(clash)}-{max(clash)} are used twice; check start_spot"
        )
    used.update(range(start, start + n))
    next_free[key] = max(next_free.get(key, 1), start + n)
    rows.loc[i, "start_spot"] = start
    print(
        f"row {int(r.row_num)}: {size} ft, {ln.length:.0f} m line, pitch {pitch:.2f} m -> {n} stalls, spots {start}-{start + n - 1} (was {r.stall_count})"
    )
    for k in range(n):
        a = np.array(ln.interpolate(k * pitch).coords[0])
        b = np.array(ln.interpolate((k + 1) * pitch).coords[0])
        u = (b - a) / np.linalg.norm(b - a)
        nrm = np.array([-u[1], u[0]]) * sd
        v = u * np.cos(th) + nrm * np.sin(th)  # stall axis (unit)
        h = v * depth / 2  # straddle the center line
        poly = Polygon([a - h, b - h, b + h, a + h]).buffer(-GAP, join_style=2)
        num = start + k
        sid = f"{r.lot_id}-R{int(r.row_num):02d}-{num:03d}"
        st = str(rng.choice(["loaded", "empty"]))
        keep = old.loc[sid] if sid in old.index else None
        spots.append(
            {
                "spot_id": sid,
                "lot_id": r.lot_id,
                "row_num": int(r.row_num),
                "spot_num": num,
                "size_ft": size,
                "stack_levels": 1,
                "height_m": round(CHASSIS_TOP + CONTAINER_H, 2),
                "status": keep.status if keep is not None else st,
                "is_sim": (
                    1
                    if keep is None
                    else (
                        1
                        if str(keep.is_sim).strip().lower() in ("true", "1", "yes")
                        else 0
                    )
                ),
                "geometry": poly,
            }
        )
        # PLACEHOLDER: one chassis with one container ON it, centered in the stall, long side along the stall axis
        c = (a + b) / 2
        w = np.array([-v[1], v[0]])
        L, W = v * UNIT_L[size] / 2, w * UNIT_W / 2
        fp = Polygon([c - L - W, c + L - W, c + L + W, c - L + W])

        same = KEEP_OLD and old_size.get(sid) == size
        o = old_own.get(sid) if same else None
        oc = old_box.get(sid) if same else None
        if (o, oc) in VALID[size]:
            own, col, reused = o, oc, True
        else:
            own, col = pick_unit(size, crng)
            reused = False
        ch_col = (
            (old_ch.get(sid) if reused else None)
            or CHASSIS_BY_OWNER.get(own)
            or str(crng.choice(OTHER_CHASSIS))
        )
        chassis.append(
            {
                "spot_id": sid,
                "size_ft": size,
                "owner": own,
                "color": ch_col,
                "base_m": CHASSIS_BOTTOM,
                "top_m": CHASSIS_TOP,
                "geometry": fp,
            }
        )
        boxes.append(
            {
                "spot_id": sid,
                "lot_id": r.lot_id,
                "row_num": int(r.row_num),
                "size_ft": size,
                "status": spots[-1]["status"],
                "owner": own,
                "color": col,
                "base_m": CHASSIS_TOP,
                "top_m": round(CHASSIS_TOP + CONTAINER_H, 2),
                "is_sim": spots[-1]["is_sim"],
                "geometry": fp,
            }
        )

gpd.GeoDataFrame(spots, geometry="geometry", crs=UTM).to_file(
    GPKG, layer="container_spots", driver="GPKG"
)
gpd.GeoDataFrame(chassis, geometry="geometry", crs=UTM).to_file(
    GPKG, layer="chassis_footprints", driver="GPKG"
)
gpd.GeoDataFrame(boxes, geometry="geometry", crs=UTM).to_file(
    GPKG, layer="containers", driver="GPKG"
)
# 3D light poles + transmission line: read your points, write extrusion parts
_lp = gpd.read_file(GPKG, layer="light_poles").to_crs(UTM)
_tw = gpd.read_file(GPKG, layer="props").to_crs(UTM)
_tw = _tw[_tw.kind == "tower"]
_pole_parts = build_light_poles(points_with_height(_lp))
_line_parts = build_power_line(points_with_height(_tw))
parts_to_gdf(_pole_parts).to_file(GPKG, layer="light_pole_parts", driver="GPKG")
parts_to_gdf(_line_parts).to_file(GPKG, layer="power_line_parts", driver="GPKG")
print(
    f"Light poles: {len(_lp)} -> {len(_pole_parts)} parts. Power line: {len(_tw)} towers -> {len(_line_parts)} parts."
)

# ---------- locomotives parked at the ends of the named tracks ----------
LOCO_LEN = 21.7  # metres, one SD60M
LOCO_GAP = 1.2  # coupler gap between units (m)
LOCO_UNITS = 2  # locomotives per train
LOCO_INSET = 15.0  # distance from the track end to the first unit (m)
LOCO_CROSS_BUF = 8.0  # keep this far from any crossing (m)


def _poly_len(c):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(c, c[1:]))


def _poly_pt(c, d):
    d = max(0.0, d)
    for a, b in zip(c, c[1:]):
        s = math.hypot(b[0] - a[0], b[1] - a[1])
        if d <= s or (a, b) == (c[-2], c[-1]):
            t = 0.0 if s == 0 else min(d / s, 1.0)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d -= s
    return c[-1]


def _poly_project(c, p):
    """distance along the line to the closest point, and how far p is from the line"""
    best, run = (0.0, 1e18), 0.0
    for a, b in zip(c, c[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        s2 = dx * dx + dy * dy
        t = (
            0.0
            if s2 == 0
            else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / s2))
        )
        dist = math.hypot(p[0] - (a[0] + dx * t), p[1] - (a[1] + dy * t))
        if dist < best[1]:
            best = (run + t * math.sqrt(s2), dist)
        run += math.sqrt(s2)
    return best


def build_locomotives(tracks, crossings, ends_override, inset_override=None):
    """tracks: [(track_id, [(x, y), ...])]  crossings: [(x, y)]
    ends_override: {track_id: 'north' | 'south' | 'both' | 'none'} (blank = default pattern)
    inset_override: {track_id: metres from the track end} (blank = LOCO_INSET)"""
    out = []
    inset_override = inset_override or {}
    tracks = sorted(tracks, key=lambda t: t[0])
    for i, (tid, coords) in enumerate(tracks):
        # default pattern: one 'both' in the middle, the rest alternate north / south
        default = (
            "both" if i == len(tracks) // 2 else ("north" if i % 2 == 0 else "south")
        )
        mode = ends_override.get(tid, default)
        if mode == "none":
            continue
        L = _poly_len(coords)
        north_is_start = coords[0][1] >= coords[-1][1]
        cross_along = [
            a for a, dd in (_poly_project(coords, c) for c in crossings) if dd < 12.0
        ]
        span = LOCO_UNITS * LOCO_LEN + (LOCO_UNITS - 1) * LOCO_GAP
        for end in ("north", "south"):
            if mode not in (end, "both"):
                continue
            at_start = (end == "north") == north_is_start
            sign, s0 = (1, 0.0) if at_start else (-1, L)
            from_end = [abs(a - s0) for a in cross_along]
            d, moved = inset_override.get(tid, LOCO_INSET), True
            while moved and d < L - span:
                moved = False
                for dc in from_end:
                    if d - LOCO_CROSS_BUF < dc < d + span + LOCO_CROSS_BUF:
                        d, moved = dc + LOCO_CROSS_BUF + 0.5, True
            for k in range(LOCO_UNITS):
                pos = s0 + sign * (d + LOCO_LEN / 2 + k * (LOCO_LEN + LOCO_GAP))
                x, y = _poly_pt(coords, pos)
                a, b = _poly_pt(coords, pos - sign), _poly_pt(coords, pos + sign)
                # the front faces the end of the track; heading is a compass bearing
                hd = math.degrees(math.atan2(a[0] - b[0], a[1] - b[1])) % 360
                out.append(
                    {
                        "x": x,
                        "y": y,
                        "track_id": tid,
                        "train_end": end,
                        "unit": k + 1,
                        "heading_deg": round(hd, 1),
                        "model": "sd60m",
                    }
                )
    return out


# --- read from the GeoPackage and write the 'locomotives' layer ---
_tk = gpd.read_file(GPKG, layer="tracks").to_crs(UTM)
_tk = _tk[_tk.track_id.notna()]
_cx = gpd.read_file(GPKG, layer="crossings").to_crs(UTM)
_tracks = []
for _tid, _g in zip(_tk.track_id, _tk.geometry):
    if _g is None or _g.is_empty:
        continue
    if _g.geom_type == "MultiLineString":
        _g = list(_g.geoms)[0]
    _tracks.append((str(_tid), list(_g.coords)))
_ends = {}
if "train_ends" in _tk.columns:  # optional field you can add in QGIS
    for _tid, _v in zip(_tk.track_id, _tk.train_ends):
        if not pd.isna(_v) and str(_v).strip().lower() in (
            "north",
            "south",
            "both",
            "none",
        ):
            _ends[str(_tid)] = str(_v).strip().lower()
_insets = {}
if "train_inset_m" in _tk.columns:  # optional field you can add in QGIS
    for _tid, _v in zip(_tk.track_id, _tk.train_inset_m):
        if not pd.isna(_v) and float(_v) >= 0:
            _insets[str(_tid)] = float(_v)
_locos = build_locomotives(
    _tracks,
    [(g.x, g.y) for g in _cx.geometry if g is not None and not g.is_empty],
    _ends,
    _insets,
)
if _locos:
    from shapely.geometry import Point

    gpd.GeoDataFrame(
        [{k: v for k, v in r.items() if k not in ("x", "y")} for r in _locos],
        geometry=[Point(r["x"], r["y"]) for r in _locos],
        crs=UTM,
    ).to_file(GPKG, layer="locomotives", driver="GPKG")
print(
    f"Locomotives: {len(_locos)} units on {len(set(r['track_id'] for r in _locos))} tracks."
)

# ---------- well cars: 3-car blocks (well_cars.glb) lined up behind each train ----------
WELL_BLOCK = 64.8  # length of one well_cars.glb = 3 cars (m)
WELL_HALF = WELL_BLOCK / 2  # half the length of the car bodies in that block (m)
WELL_MAX = 65  # most blocks on one track (65 x 3 = 195 well cars)
WELL_END_MARGIN = 15.0  # stop this far before the end of the track (m)
WELL_AVOID_CROSSINGS = (
    False  # True = leave blocks empty where they would sit on a crossing
)
WELL_CROSS_BUF = 8.0  # extra clearance around a crossing (m)
WELL_BLOCKS = {}  # e.g. {"7203": 30} -> only 30 blocks on track 7203
WELL_SKIP = {}  # e.g. {"7203": [10, 11]} -> leave blocks 10 and 11 empty on 7203


def build_well_cars(tracks, locos, crossings, rng_):
    """One LINE per 3-car block, from its first to its last car, placed end to end behind the rear
    locomotive of each train. Returns [{track_id, idx, owner, color, geometry}] (UTM metres)."""
    from shapely.geometry import LineString

    by_track = {}
    for r in locos:
        by_track.setdefault(r["track_id"], {}).setdefault(r["train_end"], []).append(r)
    out = []
    for tid, coords in tracks:
        ends = by_track.get(tid)
        if not ends:
            continue  # no train on this track -> no cars
        L = _poly_len(coords)
        trains = []  # (distance along the track of the REAR unit, direction the cars run)
        for units in ends.values():
            ss = [_poly_project(coords, (u["x"], u["y"]))[0] for u in units]
            at_start = min(ss) < L / 2
            trains.append((max(ss) if at_start else min(ss), 1 if at_start else -1))
        trains.sort()
        mine = trains[0] if trains[0][1] == 1 else trains[-1]
        rear, d = mine
        gap = (
            LOCO_LEN / 2 + LOCO_GAP
        )  # from the rear unit's centre to the first car body
        first = rear + d * (gap + WELL_HALF)
        if len(trains) > 1:  # a train on the other end too (e.g. 7205): stop before it
            other = trains[-1] if mine == trains[0] else trains[0]
            limit = other[0] - d * gap
        else:
            limit = L - WELL_END_MARGIN if d == 1 else WELL_END_MARGIN
        cross_along = [
            s for s, dd in (_poly_project(coords, c) for c in crossings) if dd < 12.0
        ]
        k = 0
        while k < WELL_BLOCKS.get(tid, WELL_MAX):
            c = first + d * k * WELL_BLOCK
            far = c + d * WELL_HALF
            if (d == 1 and far > limit) or (d == -1 and far < limit):
                break
            lo, hi = c - WELL_HALF, c + WELL_HALF
            blocked = WELL_AVOID_CROSSINGS and any(
                lo - WELL_CROSS_BUF < s < hi + WELL_CROSS_BUF for s in cross_along
            )
            if k not in WELL_SKIP.get(tid, []) and not blocked:
                a, b, m = (
                    _poly_pt(coords, lo),
                    _poly_pt(coords, hi),
                    _poly_pt(coords, c),
                )
                sx = (m[0] - (a[0] + b[0]) / 2) / 2
                sy = (m[1] - (a[1] + b[1]) / 2) / 2
                owner, color = pick_unit(
                    53, rng_
                )  # well cars run 53 ft intermodal boxes
                out.append(
                    {
                        "track_id": tid,
                        "idx": k,
                        "owner": owner,
                        "color": color,
                        "geometry": LineString(
                            [(a[0] + sx, a[1] + sy), (b[0] + sx, b[1] + sy)]
                        ),
                    }
                )
            k += 1
    return out


_wells = build_well_cars(
    _tracks,
    _locos,
    [(g.x, g.y) for g in _cx.geometry if g is not None and not g.is_empty],
    crng,  # reuse the same owner/color rng as the parked containers
)
(
    gpd.GeoDataFrame(_wells, geometry="geometry", crs=UTM)
    if _wells
    else gpd.GeoDataFrame({"track_id": [], "idx": []}, geometry=[], crs=UTM)
).to_file(GPKG, layer="well_cars", driver="GPKG")
print(
    f"Well cars: {len(_wells)} blocks ({len(_wells) * 3} well cars) on {len(set(w['track_id'] for w in _wells))} tracks."
)

rows["end_spot"] = (
    rows.start_spot.fillna(0) + rows.stall_count.fillna(0).astype(int) - 1
)
rows.to_crs(orig_crs).to_file(GPKG, layer="parking_rows", driver="GPKG")

print(f"Done: {len(spots)} spots. GeoPackage updated successfully.")
