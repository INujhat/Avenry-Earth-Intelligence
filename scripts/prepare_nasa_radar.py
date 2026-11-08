"""Prepare already calibrated and terrain-corrected Sentinel-1 VV/VH GeoTIFFs.

Input requirements: co-registered linear-power sigma0/gamma0 backscatter, not
raw GRD amplitude. Does not perform SNAP calibration or terrain correction.
Produces 512x512 north-up EPSG:4326 radar chips with model-compatible dB values.
The current U-Net was trained on a different dataset: outputs are exploratory
and must not be treated as validated flood detection.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject, transform_bounds


def convert(vv_path: Path, vh_path: Path, output: Path, *, units: str, size: int = 512):
    if units not in {"linear", "db"}:
        raise ValueError("Specify units='linear' or units='db' explicitly")
    if size != 512:
        raise ValueError("Current browser ONNX model requires 512x512 inputs")
    with rasterio.open(vv_path) as vv, rasterio.open(vh_path) as vh:
        if vv.crs is None or vh.crs is None or vv.count != 1 or vh.count != 1:
            raise ValueError("Expected one-band georeferenced VV and VH rasters")
        if vv.crs != vh.crs or vv.shape != vh.shape or not vv.transform.almost_equals(vh.transform):
            raise ValueError("VV and VH must have identical CRS, dimensions, and grid")
        bounds = transform_bounds(vv.crs, "EPSG:4326", *vv.bounds, densify_pts=21)
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            raise ValueError("Invalid geographic bounds")
        # Preserve square-ish geographic pixels by cropping a centered square
        # in the original raster before reprojection. No synthetic upsampling claim.
        window_size = min(vv.width, vv.height)
        from rasterio.windows import Window
        window = Window((vv.width-window_size)//2, (vv.height-window_size)//2, window_size, window_size)
        source_transform = vv.window_transform(window)
        source_bounds = rasterio.windows.bounds(window, vv.transform)
        dest_bounds = transform_bounds(vv.crs, "EPSG:4326", *source_bounds, densify_pts=21)
        dst_transform = from_bounds(*dest_bounds, size, size)
        bands = []
        valid = np.ones((size,size), dtype=bool)
        for src in (vv,vh):
            raw = src.read(1, window=window, masked=True).astype("float32")
            data = raw.filled(np.nan)
            source_valid = (~np.ma.getmaskarray(raw) & np.isfinite(data)).astype("uint8")
            dest = np.full((size,size), np.nan, dtype="float32")
            reproject(source=data, destination=dest, src_transform=source_transform,
                      src_crs=src.crs, dst_transform=dst_transform, dst_crs="EPSG:4326",
                      src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.bilinear)
            dest_valid = np.zeros((size,size), dtype="uint8")
            reproject(source=source_valid, destination=dest_valid, src_transform=source_transform,
                      src_crs=src.crs, dst_transform=dst_transform, dst_crs="EPSG:4326",
                      src_nodata=0, dst_nodata=0, resampling=Resampling.nearest)
            if units == "linear":
                valid &= dest > 0
                with np.errstate(divide="ignore", invalid="ignore"):
                    dest = 10 * np.log10(dest)
            valid &= (dest_valid > 0) & np.isfinite(dest)
            bands.append(dest)
        if not valid.any():
            raise ValueError("No valid radar pixels in the selected chip")
        stacked = np.stack(bands).astype("float32")
        stacked[:,~valid] = -30
        output.parent.mkdir(parents=True, exist_ok=True)
        profile = dict(driver="GTiff",width=size,height=size,count=2,dtype="float32",
                       crs="EPSG:4326",transform=dst_transform,compress="deflate",nodata=None)
        with rasterio.open(output,"w",**profile) as dst:
            dst.write(stacked)
            dst.write_mask((valid*255).astype("uint8"))
            dst.set_band_description(1,"VV dB")
            dst.set_band_description(2,"VH dB")
            dst.update_tags(source_vv=str(vv_path),source_vh=str(vh_path),input_units=units,
                            preprocessing="reprojected from externally calibrated RTC inputs",
                            warning="Not validated for the existing Sen1Floods11-trained U-Net")
        metadata={"output":str(output),"width":size,"height":size,"crs":"EPSG:4326",
                  "bounds":list(dest_bounds),"valid_pixels":int(valid.sum()),
                  "bands":["VV dB","VH dB"],"model_compatibility":"input shape only; domain shift unvalidated",
                  "required_prior_processing":"radiometric calibration and terrain correction"}
        output.with_suffix(".json").write_text(json.dumps(metadata,indent=2))
        return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vv",type=Path,required=True,help="Calibrated, terrain-corrected VV GeoTIFF")
    parser.add_argument("--vh",type=Path,required=True,help="Co-registered VH GeoTIFF")
    parser.add_argument("--units",choices=["linear","db"],required=True)
    parser.add_argument("--output",type=Path,default=Path("data/processed/nasa-radar.tif"))
    args=parser.parse_args()
    print(json.dumps(convert(args.vv,args.vh,args.output,units=args.units),indent=2))


if __name__=="__main__":
    main()
