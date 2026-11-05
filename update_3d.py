#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

GPKG = ROOT / "Alliance_Project_Data_v2.gpkg"
REGEN_SCRIPT = ROOT / "regen_spots.py"

ALLIANCE_3D = ROOT / "alliance_3d"
EXPORT_SCRIPT = ALLIANCE_3D / "export_geojson.py"
OUTPUT_DIR = ALLIANCE_3D / "data"


# ------------------------------------------------------------
# Check required files
# ------------------------------------------------------------

required_files = [
    (GPKG, "GeoPackage"),
    (REGEN_SCRIPT, "regen_spots.py"),
    (EXPORT_SCRIPT, "export_geojson.py"),
]

for path, description in required_files:
    if not path.exists():
        print(f"ERROR: {description} not found:")
        print(f"  {path}")
        sys.exit(1)


# ------------------------------------------------------------
# Step 1: Regenerate spots
# ------------------------------------------------------------

print()
print("=" * 60)
print("STEP 1/2: Regenerating spots, chassis, and containers")
print("=" * 60)
print()

result = subprocess.run(
    [sys.executable, str(REGEN_SCRIPT), str(GPKG)],
    cwd=ROOT
)

if result.returncode != 0:
    print()
    print("ERROR: regen_spots.py failed.")
    print("GeoJSON export was NOT run.")
    sys.exit(result.returncode)


# ------------------------------------------------------------
# Step 2: Export GeoJSON
# ------------------------------------------------------------

print()
print("=" * 60)
print("STEP 2/2: Exporting GeoJSON")
print("=" * 60)
print()

result = subprocess.run(
    [
        sys.executable,
        str(EXPORT_SCRIPT),
        str(GPKG),
        str(OUTPUT_DIR)
    ],
    cwd=ALLIANCE_3D
)

if result.returncode != 0:
    print()
    print("ERROR: export_geojson.py failed.")
    sys.exit(result.returncode)


# ------------------------------------------------------------
# Finished
# ------------------------------------------------------------

print()
print("=" * 60)
print("UPDATE COMPLETE")
print("=" * 60)
print()
print("Your 3D viewer data has been updated.")
print()