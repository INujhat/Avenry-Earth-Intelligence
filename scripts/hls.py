"""NASA HLS search, authenticated selected-asset access, and masked RGB preparation."""

import argparse
import json
import os
from datetime import date
from pathlib import Path

from backend.app.services.hls import download_asset, preview_hls, search_hls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("--bbox", required=True, help="west,south,east,north (use --bbox=-1,38,0,39)")
    search.add_argument("--start", required=True, type=date.fromisoformat)
    search.add_argument("--end", required=True, type=date.fromisoformat)
    search.add_argument("--sensor", choices=["HLSS30", "HLSL30"], default="HLSS30")
    search.add_argument("--output", type=Path, default=Path("data/raw/hls-search.json"))
    download = commands.add_parser("download")
    download.add_argument("--url", required=True)
    download.add_argument("--output", required=True, type=Path)
    preview = commands.add_parser("preview")
    for key in ["red", "green", "blue", "fmask", "output"]:
        preview.add_argument(f"--{key}", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "search":
        result = search_hls(list(map(float, args.bbox.split(","))), args.start, args.end, args.sensor)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"Found {len(result['items'])} scenes; metadata saved to {args.output}")
    elif args.command == "download":
        download_asset(args.url, args.output, os.environ.get("EARTHDATA_TOKEN", ""))
        print("Selected asset downloaded and validated")
    else:
        print(json.dumps(preview_hls(args.red, args.green, args.blue, args.fmask, args.output)))


if __name__ == "__main__":
    main()
