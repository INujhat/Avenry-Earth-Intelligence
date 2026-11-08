"""Search NASA ASF Sentinel-1 GRD scenes and download a selected original product.

This is an ingestion utility, NOT an inference pipeline. Sentinel-1 GRD
measurements require radiometric calibration, terrain correction, and validation
before use with Avenry's existing two-band U-Net.
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_URL = "https://api.daac.asf.alaska.edu/services/search/param"
ALLOWED_HOSTS = {"datapool.asf.alaska.edu", "api.daac.asf.alaska.edu"}
SCENE_ID = re.compile(r"^S1[ABC]_[A-Z0-9_]{15,120}$")


def search(bbox, start, end, limit=25):
    west, south, east, north = map(float, bbox.split(","))
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Expected bbox west,south,east,north in geographic coordinates")
    if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end) and start <= end):
        raise ValueError("Dates must be YYYY-MM-DD and start must precede end")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    polygon = f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"
    query = urllib.parse.urlencode({
        "platform": "Sentinel-1", "processingLevel": "GRD_HD",
        "intersectsWith": polygon, "start": start, "end": end,
        "output": "geojson", "maxResults": limit,
    })
    with urllib.request.urlopen(SEARCH_URL + "?" + query, timeout=60) as response:
        result = json.load(response)
    if not isinstance(result.get("features"), list):
        raise ValueError("NASA ASF returned an unexpected response")
    return result


def download(feature, destination, token):
    properties = feature.get("properties", {})
    scene = str(properties.get("sceneName") or properties.get("fileID") or "")
    if not SCENE_ID.fullmatch(scene):
        raise ValueError("Invalid Sentinel-1 scene identifier")
    url = str(properties.get("url", ""))
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Refusing a download outside NASA ASF's approved data hosts")
    if not token:
        raise ValueError("Set EARTHDATA_TOKEN in your environment before downloading")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / (scene + ".zip")
    if target.exists():
        raise FileExistsError(f"Already downloaded: {target}")
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "Avenry-Earth-Intelligence/0.2"})
    temporary = target.with_suffix(".partial")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
            if response.geturl().startswith("http://"):
                raise ValueError("Download was redirected to an insecure URL")
            import shutil
            shutil.copyfileobj(response, out)
        if temporary.stat().st_size < 10000:
            raise ValueError("Downloaded file is unexpectedly small")
        import zipfile
        if not zipfile.is_zipfile(temporary):
            raise ValueError("Downloaded content is not a valid Sentinel-1 ZIP product")
        temporary.replace(target)
        (destination / (scene + ".json")).write_text(json.dumps(feature, indent=2))
        return target
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", default="91.69,24.71,92.05,25.07", help="west,south,east,north; default Sylhet, Bangladesh")
    parser.add_argument("--start", default="2022-06-01")
    parser.add_argument("--end", default="2022-06-30")
    parser.add_argument("--output", type=Path, default=Path("data/raw/nasa-asf/search.json"))
    parser.add_argument("--download-index", type=int, default=None, help="Download a scene from the search result by zero-based index")
    args = parser.parse_args()
    result = search(args.bbox, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"NASA ASF: {len(result['features'])} matching scenes saved to {args.output}")
    for i, f in enumerate(result["features"]):
        p = f.get("properties", {})
        print(f"{i}: {p.get('sceneName', p.get('fileID', 'Unknown'))} — {p.get('startTime', 'Unknown date')}")
    if args.download_index is not None:
        if not 0 <= args.download_index < len(result["features"]):
            parser.error("Download index is outside the result list")
        path = download(result["features"][args.download_index], args.output.parent / "downloads", os.environ.get("EARTHDATA_TOKEN", ""))
        print(f"Original NASA product downloaded to {path}. Preprocessing is still required.")


if __name__ == "__main__":
    main()
