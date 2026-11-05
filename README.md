# BNSF Alliance 3D Yard

An interactive, Apple Maps style 3D model of the BNSF Alliance intermodal rail yard. The yard is digitized in **QGIS**, stored in a single **GeoPackage**, processed with a few **Python** scripts, and rendered in the browser with **MapLibre GL JS**.

> Flat colors only, no satellite imagery. Buildings, containers, chassis, trees, light poles and cranes are extruded in 3D.

---

## Table of contents

- [BNSF Alliance 3D Yard](#bnsf-alliance-3d-yard)
  - [Table of contents](#table-of-contents)
  - [How it works](#how-it-works)
  - [Project structure](#project-structure)
  - [Requirements](#requirements)
  - [First-time setup (run once)](#first-time-setup-run-once)
  - [Everyday workflow](#everyday-workflow)
    - [One-command update (optional)](#one-command-update-optional)
  - [Drawing parking rows in QGIS](#drawing-parking-rows-in-qgis)
    - [Numbering rules](#numbering-rules)
    - [How many stalls fit on a line](#how-many-stalls-fit-on-a-line)
  - [How spots, chassis and containers are generated](#how-spots-chassis-and-containers-are-generated)
    - [Yard rules baked in](#yard-rules-baked-in)
    - [Stable between runs](#stable-between-runs)
  - [What is real and what is simulated](#what-is-real-and-what-is-simulated)
  - [The viewer](#the-viewer)
  - [Script reference](#script-reference)
  - [Troubleshooting](#troubleshooting)
  - [Roadmap](#roadmap)

---

## How it works

```
 QGIS (edit)                Python                         Browser
┌──────────────┐   ┌─────────────────────┐   ┌──────────────────────┐   ┌─────────────────┐
│ Alliance_    │   │ regen_spots.py      │   │ export_geojson.py    │   │ index.html      │
│ Project_Data │──▶│ rows → spots,       │──▶│ GeoPackage → GeoJSON │──▶│ MapLibre 3D     │
│ _v2.gpkg     │   │ chassis, containers │   │ (EPSG:4326)          │   │ viewer          │
└──────────────┘   └─────────────────────┘   └──────────────────────┘   └─────────────────┘
```

- The **GeoPackage** is the single source of truth. Everything is edited in QGIS.
- `regen_spots.py` turns the lines you draw (`parking_rows`) into individual stalls, chassis and containers.
- `export_geojson.py` converts the GeoPackage to GeoJSON files in `alliance_3d/data/`.
- `index.html` reads those files and draws the 3D scene.

The viewer **does not update on its own**. After you change anything you rerun the scripts and refresh the page (see [Everyday workflow](#everyday-workflow)).

---

## Project structure

```
rail-yard
├─ Alliance-Railyard-QGIS.qgz
├─ alliance_3d
│  ├─ Alliance_Data_Dictionary.md
│  ├─ data
│  │  ├─ barriers.geojson
│  │  ├─ buildings.geojson
│  │  ├─ chassis.geojson
│  │  ├─ containers.geojson
│  │  ├─ cranes.geojson
│  │  ├─ crossings.geojson
│  │  ├─ gantry_paths.geojson
│  │  ├─ grass.geojson
│  │  ├─ light_poles.geojson
│  │  ├─ lots.geojson
│  │  ├─ lot_labels.geojson
│  │  ├─ meta.json
│  │  ├─ props.geojson
│  │  ├─ rail_points.geojson
│  │  ├─ roads.geojson
│  │  ├─ spots.geojson
│  │  ├─ tracks.geojson
│  │  ├─ trees.geojson
│  │  ├─ water.geojson
│  │  └─ yard_surface.geojson
│  ├─ export_geojson.py
│  └─ index.html
├─ Alliance_Project_Data_v2.gpkg
├─ build_gpkg.py
├─ README.md
└─ regen_spots.py               (optional one-command update, see below)
```

| Path                            | What it is                                                                |
| ------------------------------- | ------------------------------------------------------------------------- |
| `Alliance_Project_Data_v2.gpkg` | The working GeoPackage. Edit this in QGIS.                                |
| `build_gpkg.py`                 | **Run once.** Builds the v2 GeoPackage from your original file.           |
| `regen_spots.py`                | Regenerates stalls, chassis and containers from `parking_rows`.           |
| `alliance_3d/export_geojson.py` | Exports the GeoPackage to GeoJSON for the viewer.                         |
| `alliance_3d/index.html`        | The MapLibre 3D viewer.                                                   |
| `alliance_3d/data/`             | Generated GeoJSON. Never edit by hand, it is overwritten on every export. |
| `Alliance_Data_Dictionary.md`   | Field-by-field description of every layer.                                |

---

## Requirements

- Python 3.10+
- QGIS (to edit the GeoPackage)
- A browser with WebGL (any modern one)

```powershell
pip install geopandas shapely pyogrio numpy pandas
```

---

## First-time setup (run once)

> **Run `build_gpkg.py` one time only.** It builds a brand-new v2 GeoPackage from your original file. Running it again would overwrite `Alliance_Project_Data_v2.gpkg` and **wipe every edit you have made in QGIS**.

```powershell
python build_gpkg.py Alliance_Project_Data.gpkg miscalleanous_nodes.gpkg Alliance_Project_Data_v2.gpkg
```

This script:

- copies your original file (the original is never modified)
- cleans the layers: one `lot_type` spelling, `LOTx` style ids, buildings reprojected to EPSG:32614
- adds the layers the viewer needs: `container_spots`, `trees`, `water`, `grass`, `props`, `rail_points`, `roads`

After that, all edits happen in `Alliance_Project_Data_v2.gpkg`. Keep it in the `rail-yard` folder next to `regen_spots.py`.

---

## Everyday workflow

1. **Edit in QGIS.** Save your edits and toggle editing **off** for every layer (the scripts cannot write to a locked layer).
2. **Regenerate the spots** (only needed if you changed `parking_rows`):
   ```powershell
   cd C:\Users\saada\rail-yard
   python regen_spots.py Alliance_Project_Data_v2.gpkg
   ```
3. **Export to GeoJSON:**
   ```powershell
   cd alliance_3d
   python export_geojson.py ..\Alliance_Project_Data_v2.gpkg data
   ```
4. **Serve the viewer** (leave this running in its own terminal; you only start it once):
   ```powershell
   python -m http.server 8000
   ```
5. Open <http://localhost:8000> and refresh. Use **Ctrl + F5** if the old version still shows, because browsers cache the GeoJSON.
6. **Reload the layers in QGIS** after running `regen_spots.py` so you see the new stalls.

The server does not need a restart, it serves whatever is on disk when the page loads. If you only changed something `regen_spots.py` does not touch (a building, a track), skip step 2.

### One-command update (optional)

Save this as `update.ps1` in `rail-yard` and run `.\update.ps1`:

```powershell
python regen_spots.py Alliance_Project_Data_v2.gpkg
cd alliance_3d
python export_geojson.py ..\Alliance_Project_Data_v2.gpkg data
cd ..
```

---

## Drawing parking rows in QGIS

Each feature in the `parking_rows` layer is the **center line** of one straight run of angled stalls. If a row has a break (a gap, a road, a track crossing), draw **one line per segment**.

| Field             | Meaning                                                                                 | If left blank                                              |
| ----------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `lot_id`          | Lot the row belongs to, in `LOTB` style                                                 | line is **skipped**                                        |
| `row_num`         | Row number                                                                              | line is **skipped**                                        |
| `stall_angle`     | Stall angle in degrees                                                                  | 30                                                         |
| `stall_angle_ref` | `perpendicular` (angle off straight-in, recommended) or `row` (angle from the row line) | `perpendicular`                                            |
| `stall_side`      | `left` or `right`; which way the stalls lean                                            | `left`                                                     |
| `spot_width_m`    | Width across one stall                                                                  | 3.353 m (11 ft)                                            |
| `spot_length_m`   | Length of one stall along its own axis                                                  | 17.5 m                                                     |
| `start_spot`      | First stall number of this segment                                                      | continues after the previous segment of the same row, or 1 |
| `stall_count`     | **Recalculated by the script.** Do not type it.                                         | n/a                                                        |
| `end_spot`        | **Written by the script**                                                               | n/a                                                        |

### Numbering rules

- A `start_spot` of **1 or higher is honored exactly**, regardless of which line you drew first.
- A blank, 0 or negative `start_spot` means "continue after the previous segment of this row".
- If two segments of a row end up sharing numbers, the script prints a `WARNING` so you can fix it.
- Example for a row split in two: set `start_spot = 1` on the first segment, and (first segment's stall count + 1) on the second.

### How many stalls fit on a line

```
pitch = spot_width_m / sin(angle from the row line)
stalls = round(line length / pitch)
```

The pitch is then stretched by under 0.5 percent so the stalls tile the line exactly.

---

## How spots, chassis and containers are generated

`regen_spots.py` writes three layers back into the GeoPackage:

| Layer                | One feature per | Purpose                                                        |
| -------------------- | --------------- | -------------------------------------------------------------- |
| `container_spots`    | stall           | The painted parking stall outline                              |
| `chassis_footprints` | stall           | 53 ft chassis footprint with owner, color, `base_m`, `top_m`   |
| `containers`         | stall           | 53 ft container footprint with owner, color, `base_m`, `top_m` |

**Spot ids** look like `LOTB-R14-001` (lot, row, number).

**Unit dimensions** (all in meters):

| Part      | Size                    | Height                                          |
| --------- | ----------------------- | ----------------------------------------------- |
| Chassis   | 53 ft long, 8.5 ft wide | from 0.45 m (above the wheels) to 1.40 m (deck) |
| Container | 53 ft long, 8.5 ft wide | from 1.40 m to 4.30 m (9 ft 6 in high-cube)     |

### Yard rules baked in

- **No stacking inside parking spots.** `stack_levels` is always 1.
- **A container in a spot is never on the ground.** It always sits on a chassis deck.
- Stacking containers and chassis in open ground between tracks (and the rare 3-high chassis stack) is real in the yard but is **not modeled yet**, see the [roadmap](#roadmap).

### Stable between runs

Each unit keeps its owner, colors and status from earlier runs, so rerunning the script does not reshuffle the yard. Every run also saves a timestamped backup of the GeoPackage next to the original (`..._backup_YYYYMMDD_HHMMSS.gpkg`). Delete old backups once you are happy.

---

## What is real and what is simulated

| Data                                                   | Status                                                                               |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Lots, tracks, crossings, light poles, yard surface     | **Real**, digitized in QGIS                                                          |
| Parking row geometry and stall positions               | **Real**, from your `parking_rows` lines                                             |
| Buildings you drew                                     | **Real** footprints and heights                                                      |
| Other buildings (OpenStreetMap)                        | Real footprints, **assumed heights** (levels x 3.5 m, or a default by type)          |
| Roads, fences, barriers                                | OpenStreetMap, widths and heights **assumed**                                        |
| Which spots hold a unit                                | **Placeholder**: every spot has one chassis with one container                       |
| Container owner (J.B. Hunt 65%, Amazon 20%, COSCO 15%) | **Simulated**                                                                        |
| Loaded / empty status                                  | **Simulated**                                                                        |
| Trees                                                  | **Simulated** (dense around water, sparse elsewhere, never on pavement or buildings) |
| Gantry cranes                                          | Layer is empty; the exporter assumes 30 m span and 18 m height when you add some     |

Simulated features carry `is_sim = 1` where the layer has that field.

---

## The viewer

`index.html` uses MapLibre GL JS 3.6 with flat colors and a soft light, no basemap tiles.

- **Layer panel** (top left): toggle grass, water, pavement, lots, roads, tracks, gantry paths, switches, crossings, stalls, barriers, buildings, gates and towers, trees, chassis, containers, light poles, cranes and lot labels.
- **View buttons**: whole yard, Lot B, buildings, pond.
- **Click** a container, chassis, building, prop, crossing, switch, lot or road to see its attributes.
- **Container colors** come straight from the GeoPackage:

| Owner     | Container | Chassis                           |
| --------- | --------- | --------------------------------- |
| J.B. Hunt | off-white | red                               |
| Amazon    | dark navy | black, light blue or light orange |
| COSCO     | blue      | black, light blue or light orange |

Controls: right-drag or two-finger drag to tilt and rotate, scroll to zoom.

---

## Script reference

| Script              | Run from      | Command                                                          | Reads               | Writes                                                                                    |
| ------------------- | ------------- | ---------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------- |
| `build_gpkg.py`     | `rail-yard`   | `python build_gpkg.py <original.gpkg> <nodes.gpkg> <v2.gpkg>`    | original GeoPackage | new v2 GeoPackage (**run once**)                                                          |
| `regen_spots.py`    | `rail-yard`   | `python regen_spots.py Alliance_Project_Data_v2.gpkg`            | `parking_rows`      | `container_spots`, `chassis_footprints`, `containers`, `parking_rows` (start, end, count) |
| `export_geojson.py` | `alliance_3d` | `python export_geojson.py ..\Alliance_Project_Data_v2.gpkg data` | the GeoPackage      | `data/*.geojson`, `data/meta.json`                                                        |

`export_geojson.py` reads spots, chassis and containers straight from the GeoPackage, so the web viewer always matches QGIS. It also builds simulated trees and the buffered road, barrier and prop shapes at export time.

---

## Troubleshooting

| Symptom                                       | Cause and fix                                                                                                               |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Viewer is blank or says it cannot load data   | You opened `index.html` by double-click. Run `python -m http.server 8000` in `alliance_3d` and use <http://localhost:8000>. |
| Changes in QGIS do not show in the viewer     | Rerun the export, then hard-refresh with Ctrl + F5.                                                                         |
| `SKIPPED a line with blank lot_id or row_num` | Fill both fields on that line in QGIS and rerun.                                                                            |
| `WARNING: row N spots X-Y are used twice`     | Two segments of a row share numbers. Fix `start_spot` on one of them.                                                       |
| `note: row N has no stall_angle -> using 30`  | Set `stall_angle` on that line.                                                                                             |
| Script cannot write to the GeoPackage         | QGIS still has it in edit mode. Save, toggle editing off, close the layer if needed.                                        |
| New stalls not visible in QGIS                | Reload the layers (right-click, Reload) after running `regen_spots.py`.                                                     |
| `rail_points` or `props` export 0 features    | The export must read them from the v2 GeoPackage (current version does). Rerun with the latest `export_geojson.py`.         |
| Every building shows as "yours"               | Use the latest `export_geojson.py`, which keeps the `source` column from v2.                                                |
| Running `build_gpkg.py` a second time         | Do not. It overwrites the v2 file. Restore from a `_backup_` copy.                                                          |

---

## Roadmap

- [ ] **Assignment script**: place containers and chassis realistically instead of one full unit in every stall (empty stalls, chassis only, the rare 3-high chassis stack, per-lot fill levels)
- [ ] Off-spot stacks in open ground between tracks
- [ ] Real gantry cranes on the rails
- [ ] Digitized barriers and fences to replace the OpenStreetMap ones
- [ ] Real container data (`container_number`, `length_ft`, `last_updated`) in place of simulated values
- [ ] Deploy the viewer online

---

See `alliance_3d/Alliance_Data_Dictionary.md` for the full field list of every layer.
