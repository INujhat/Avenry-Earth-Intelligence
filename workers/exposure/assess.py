"""Potential mapped-facility exposure from georeferenced water-change polygons.

Requires shapely and pyproj. Uses *spatial overlap* only, never asserts damage.
Input GeoJSON from change_detection/analyze.py; facility JSON array of
{name, lat, lon, kind, source}. Do not use for emergency response.
"""
import argparse
import json
from pathlib import Path
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union
from pyproj import Transformer


def assess(change_geojson: dict, facilities: list[dict], buffer_m: float = 0) -> dict:
    if not 0 <= buffer_m <= 10000:
        raise ValueError("buffer_m must be between 0 and 10000")
    polygons = [shape(f["geometry"]) for f in change_geojson.get("features", [])
                if f.get("properties", {}).get("change") == "water_gained"]
    if not polygons:
        return {"potentially_exposed": [], "facility_count": len(facilities),
                "limitations": ["No gained-water polygons provided; this is not a safety finding."]}
    geometry = unary_union(polygons)
    # EPSG:3857 distances are distorted; use a local azimuthal equidistant projection.
    center = geometry.centroid
    transformer = Transformer.from_crs("EPSG:4326",
        f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m +no_defs",
        always_xy=True)
    projected = transform(transformer.transform, geometry)
    results = []
    for facility in facilities:
        lat, lon = float(facility["lat"]), float(facility["lon"])
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            continue
        point = transform(transformer.transform, Point(lon, lat))
        d = float(projected.distance(point))
        if d <= buffer_m:
            results.append({"name": str(facility.get("name", "Unnamed facility")),
                            "kind": str(facility.get("kind", "unknown")),
                            "source": str(facility.get("source", "unspecified")),
                            "distance_to_detected_gain_m": round(d, 1),
                            "overlaps_detected_gain": d == 0})
    return {"potentially_exposed": results, "facility_count": len(facilities),
            "buffer_m": buffer_m, "method": "Geometric intersection or proximity to supplied gained-water polygons",
            "limitations": ["Mapped location may be inaccurate or incomplete.",
                            "Water gain may be seasonal or misclassified; not necessarily flooding.",
                            "Proximity does not prove facility damage, closure, or operational status.",
                            "No population exposure or emergency safety determination."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--changes", type=Path, required=True)
    parser.add_argument("--facilities", type=Path, required=True)
    parser.add_argument("--buffer-m", type=float, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess(json.loads(args.changes.read_text()), json.loads(args.facilities.read_text()), args.buffer_m)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"potentially_exposed_count": len(result["potentially_exposed"])}))
