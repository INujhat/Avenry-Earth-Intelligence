"""One-command NASA ASF scene ingestion (search -> download -> SNAP -> radar chip).

Requirements:
- ESA SNAP Graph Processing Tool ('gpt') with Copernicus DEM access.
- NASA Earthdata token in EARTHDATA_TOKEN environment variable.
- Enough local disk for a full Sentinel-1 GRD archive and terrain correction.
- This does not deploy a model or produce a water prediction.
"""
import argparse
import json
import os
from pathlib import Path

from scripts.nasa_asf import download, search
from scripts.process_nasa_grd import process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", default="91.69,24.71,92.05,25.07")
    parser.add_argument("--start", default="2022-06-01")
    parser.add_argument("--end", default="2022-06-30")
    parser.add_argument("--scene-index", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/nasa-asf"))
    parser.add_argument("--gpt", default="gpt")
    args = parser.parse_args()
    token = os.environ.get("EARTHDATA_TOKEN", "")
    if not token:
        parser.error("EARTHDATA_TOKEN is required for NASA download; do not commit or paste it")
    results = search(args.bbox, args.start, args.end)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/"search.json").write_text(json.dumps(results, indent=2))
    features = results["features"]
    if not features:
        parser.error("No scenes found. Try another date range or bounding box.")
    if not 0 <= args.scene_index < len(features):
        parser.error(f"Scene index must be between 0 and {len(features)-1}")
    grd = download(features[args.scene_index], args.output_dir/"downloads", token)
    output = args.output_dir/"processed"/(grd.stem+".tif")
    metadata = process(grd, output, gpt=args.gpt)
    print(json.dumps({"radar":str(output),"metadata":metadata,
                      "next_step":"Train or provide a compatible, licensed U-Net checkpoint and validate transfer performance before public inference."}, indent=2))


if __name__ == "__main__":
    main()
