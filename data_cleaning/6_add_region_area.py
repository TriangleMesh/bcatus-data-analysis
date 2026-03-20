import argparse
import json
import os
from typing import Dict, List, Optional, Tuple

import pandas as pd
from shapely.geometry import Point


REGION_DIR = os.path.join(os.path.dirname(__file__), "region_area")
REGION_FILES: Dict[str, List[str]] = {
    "Vancouver": ["metro_vancouver_Administrative_Boundaries.geojson"],
    "Okanagan": ["RDCO_Boundary.geojson", "Vernon_City_Boundary.geojson"],
}
REGION_COLUMN = "region_area"
# input = 'wave1/Wave 1.xlsx'
input = 'output/app_data_20250210_all_deleted_with_filled_purpose_with_adjusted_mode.xlsx'
# input = 'wave3_output/app_data_wave3_20251202_merged_deleted.xlsx'


# input = 'output/app_data_20250210_all_deleted_with_filled_purpose_with_adjusted_mode.xlsx'
# input = 'raw/app_data_20250210_all_with_routes.xlsx'
# input = 'wave3_raw/app_data_wave3_20251202.xlsx'

output = 'output/app_data_20250210_all_deleted_with_filled_purpose_with_adjusted_mode_region.xlsx'

def point_in_polygon(lat, lon, polygon_coords):
    """Simple ray casting algorithm to check if point is in polygon."""
    x, y = lon, lat
    n = len(polygon_coords)
    inside = False
    p1x, p1y = polygon_coords[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon_coords[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def load_region_shapes() -> Dict[str, List]:
    """Load GeoJSON polygons as coordinate lists (avoid Shapely.Polygon which causes segfault)."""
    shapes: Dict[str, List] = {k: [] for k in REGION_FILES}
    for region, files in REGION_FILES.items():
        for fname in files:
            path = os.path.join(REGION_DIR, fname)
            if not os.path.exists(path):
                print(f"[WARN] Region file missing: {path}")
                continue
            print(f"[INFO] Loading region file: {path}")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    print(f"[INFO] Reading JSON...")
                    gj = json.load(f)
                print(f"[INFO] JSON loaded, processing features...")
                feat_count = 0
                for feat_idx, feat in enumerate(gj.get("features", [])):
                    geom = feat.get("geometry")
                    if geom:
                        try:
                            geom_type = geom.get('type', '')
                            
                            if geom_type == 'Polygon':
                                coords = geom.get('coordinates', [])
                                if coords and len(coords) > 0:
                                    # Store exterior ring only
                                    shapes[region].append(coords[0])
                                    feat_count += 1
                            elif geom_type == 'MultiPolygon':
                                coords_list = geom.get('coordinates', [])
                                for coords in coords_list:
                                    if coords and len(coords) > 0:
                                        shapes[region].append(coords[0])
                                        feat_count += 1
                            
                        except Exception as e:
                            print(f"[WARN] Failed to load geometry: {e}")
                print(f"[INFO] Loaded {feat_count} shapes for region {region}")
            except Exception as e:
                print(f"[ERROR] Failed to load region file {path}: {e}")
                raise
    print(f"[INFO] Loaded {sum(len(v) for v in shapes.values())} total region shapes")
    return shapes


def detect_lat_lon_columns(df: pd.DataFrame, prefix: str = "start_") -> Tuple[Optional[str], Optional[str]]:
    """Find latitude/longitude columns. Prefer columns starting with given prefix."""
    lat_candidates = []
    lon_candidates = []
    for col in df.columns:
        lower = col.lower()
        if "lat" in lower:
            lat_candidates.append(col)
        if ("lon" in lower) or ("lng" in lower):
            lon_candidates.append(col)
    if not lat_candidates or not lon_candidates:
        return None, None

    def pick(cands: List[str]) -> str:
        for c in cands:
            if c.lower().startswith(prefix):
                return c
        return cands[0]

    return pick(lat_candidates), pick(lon_candidates)


def parse_coord_pair(value) -> Tuple[Optional[float], Optional[float]]:
    """Parse a string like "(49.12, -122.69)" into (lat, lon)."""
    if pd.isna(value):
        return None, None
    try:
        s = str(value).strip()
        s = s.strip("() ")
        parts = s.split(",")
        if len(parts) != 2:
            return None, None
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return lat, lon
    except Exception:
        return None, None


def classify_region(lat, lon, shapes: Dict[str, List]) -> str:
    try:
        if pd.isna(lat) or pd.isna(lon):
            return "Other"
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return "Other"

    # Check Vancouver
    for polygon_coords in shapes.get("Vancouver", []):
        if point_in_polygon(lat, lon, polygon_coords):
            return "Vancouver"
    
    # Check Okanagan
    for polygon_coords in shapes.get("Okanagan", []):
        if point_in_polygon(lat, lon, polygon_coords):
            return "Okanagan"
    
    return "Other"


def add_region_column(df: pd.DataFrame, shapes: Dict[str, List]) -> pd.DataFrame:
    df = df.copy()

    # 1) Try start_* columns first
    start_lat_col, start_lon_col = detect_lat_lon_columns(df, prefix="start_")
    # 2) Try end_* columns
    end_lat_col, end_lon_col = detect_lat_lon_columns(df, prefix="end_")
    # 3) Fallback: parse "End Coordinates" string like "(49.12, -122.69)"
    end_coord_col = None
    for c in df.columns:
        if c.lower().strip().replace(" ", "") == "endcoordinates":
            end_coord_col = c
            break

    if not start_lat_col or not start_lon_col:
        # If no start lat/lon, fall back to end_* if present
        if end_lat_col and end_lon_col:
            start_lat_col, start_lon_col = end_lat_col, end_lon_col
        elif end_coord_col:
            # will parse per-row later
            start_lat_col, start_lon_col = None, None
        else:
            raise ValueError("Latitude/longitude columns not found; expected start_* or end_* lat/lon, or 'End Coordinates'")

    def classify_row(row):
        # Try start coords if available
        if start_lat_col and start_lon_col:
            region = classify_region(row[start_lat_col], row[start_lon_col], shapes)
            if region != "Other":
                return region
        # Fallback to end_* if available
        if end_lat_col and end_lon_col:
            region2 = classify_region(row[end_lat_col], row[end_lon_col], shapes)
            if region2 != "Other":
                return region2
        # Fallback to End Coordinates parsed values
        if end_coord_col:
            lat_p, lon_p = parse_coord_pair(row[end_coord_col])
            region3 = classify_region(lat_p, lon_p, shapes)
            return region3
        return "Other"

    df[REGION_COLUMN] = df.apply(classify_row, axis=1)
    return df


def process_file(input_path: str, output_path: Optional[str] = None, force: bool = False) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    shapes = load_region_shapes()
    df = pd.read_excel(input_path)

    if REGION_COLUMN in df.columns and not force:
        print(f"[INFO] Column '{REGION_COLUMN}' already exists; skipping. Use --force to recompute.")
        if output_path is None:
            return input_path
        df.to_excel(output_path, index=False)
        return output_path

    df = add_region_column(df, shapes)

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_with_region{ext or '.xlsx'}"

    df.to_excel(output_path, index=False)
    print(f"[DONE] Saved with region column to: {output_path}")
    return output_path


def main():
    print("[INFO] Starting region classification...")
    print(f"[INFO] Input file: {input}")
    print(f"[INFO] Output file: {output}")
    try:
        process_file(input, output, force=False)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
