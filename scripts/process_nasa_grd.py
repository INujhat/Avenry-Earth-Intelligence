"""Convert an authenticated NASA ASF Sentinel-1 GRD ZIP into model-shaped radar data.

Requires ESA SNAP with the 'gpt' executable installed and accessible. SNAP
performs orbit application, radiometric calibration, and Range-Doppler terrain
correction; this script does not treat uncalibrated GRD amplitude as backscatter.
The resulting radar is *input-compatible*, NOT validated for the trained model.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import rasterio

from scripts.prepare_nasa_radar import convert


def graph(source: Path, output: Path, spacing: float) -> str:
    # SNAP GPT processing graph: apply orbit -> calibrate -> terrain-correct -> GeoTIFF.
    src = escape(str(source.resolve()))
    dst = escape(str(output.resolve()))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<graph id="AvenrySentinel1GRD">
  <version>1.0</version>
  <node id="Read">
    <operator>Read</operator>
    <sources/>
    <parameters><file>{src}</file></parameters>
  </node>
  <node id="Orbit">
    <operator>Apply-Orbit-File</operator>
    <sources><sourceProduct refid="Read"/></sources>
    <parameters><orbitType>Sentinel Precise (Auto Download)</orbitType><polyDegree>3</polyDegree><continueOnFail>false</continueOnFail></parameters>
  </node>
  <node id="Calibration">
    <operator>Calibration</operator>
    <sources><sourceProduct refid="Orbit"/></sources>
    <parameters>
      <selectedPolarisations>VV,VH</selectedPolarisations>
      <outputSigmaBand>true</outputSigmaBand>
      <outputImageScaleInDb>false</outputImageScaleInDb>
    </parameters>
  </node>
  <node id="Terrain">
    <operator>Terrain-Correction</operator>
    <sources><sourceProduct refid="Calibration"/></sources>
    <parameters>
      <demName>Copernicus 30m Global DEM</demName>
      <pixelSpacingInMeter>{spacing}</pixelSpacingInMeter>
      <mapProjection>EPSG:4326</mapProjection>
      <nodataValueAtSea>false</nodataValueAtSea>
      <saveSelectedSourceBand>true</saveSelectedSourceBand>
    </parameters>
  </node>
  <node id="Write">
    <operator>Write</operator>
    <sources><sourceProduct refid="Terrain"/></sources>
    <parameters><file>{dst}</file><formatName>GeoTIFF</formatName></parameters>
  </node>
</graph>"""


def process(source: Path, output: Path, *, gpt: str = "gpt", spacing: float = 20, timeout: int = 3600):
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise ValueError("Input must be an existing Sentinel-1 GRD ZIP")
    if not 5 <= spacing <= 100:
        raise ValueError("Pixel spacing must be between 5 and 100 meters")
    executable = shutil.which(gpt)
    if not executable:
        raise RuntimeError("ESA SNAP Graph Processing Tool (gpt) is not installed or not on PATH")
    with tempfile.TemporaryDirectory(prefix="avenry-snap-") as temp:
        folder = Path(temp)
        intermediate = folder / "terrain_corrected.tif"
        xml = folder / "process.xml"
        xml.write_text(graph(source, intermediate, spacing))
        result = subprocess.run([executable, str(xml), "-c", "4G"], timeout=timeout,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, check=False)
        if result.returncode:
            raise RuntimeError("SNAP processing failed. Last output lines:\n" + "\n".join(result.stdout.splitlines()[-35:]))
        if not intermediate.is_file():
            raise RuntimeError("SNAP did not generate the terrain-corrected GeoTIFF")
        with rasterio.open(intermediate) as src:
            descriptions = [str(x or "").upper() for x in src.descriptions]
            # Refuse ambiguous channel order: otherwise false water masks can result.
            vv = [i+1 for i, name in enumerate(descriptions) if "VV" in name and "VH" not in name]
            vh = [i+1 for i, name in enumerate(descriptions) if "VH" in name]
            if len(vv) != 1 or len(vh) != 1:
                raise ValueError(f"Cannot safely identify VV/VH bands in SNAP output: {descriptions}")
            profile = src.profile.copy()
            profile.update(count=1)
            vv_path, vh_path = folder / "vv.tif", folder / "vh.tif"
            for index, path in [(vv[0], vv_path), (vh[0], vh_path)]:
                with rasterio.open(path, "w", **profile) as dst:
                    dst.write(src.read(index), 1)
                    dst.write_mask(src.read_masks(index))
        metadata = convert(vv_path, vh_path, output, units="linear")
        # Temporary VV/VH paths are deliberately not persisted.
        metadata.update(source_grd=source.name, processing="ESA SNAP orbit+calibration+terrain correction",
                        pixel_spacing_m=spacing,
                        model_validation="Not validated for transfer to new NASA ASF scenes")
        output.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
        return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grd", type=Path, required=True, help="NASA ASF Sentinel-1 GRD ZIP")
    parser.add_argument("--output", type=Path, default=Path("data/processed/nasa-radar.tif"))
    parser.add_argument("--gpt", default="gpt", help="ESA SNAP gpt executable")
    parser.add_argument("--pixel-spacing", type=float, default=20)
    args = parser.parse_args()
    print(json.dumps(process(args.grd, args.output, gpt=args.gpt, spacing=args.pixel_spacing), indent=2))


if __name__ == "__main__":
    main()
