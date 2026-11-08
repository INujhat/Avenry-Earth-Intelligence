# NASA Sentinel-1 end-to-end ingestion

Avenry's live website can **search** NASA ASF Sentinel-1 scene metadata. Its browser-only Vercel deployment cannot currently download multi-GB authenticated GRD archives, run ESA SNAP terrain correction, or infer with a checkpoint that is not deployed. Do not describe metadata search as a successful AI analysis.

## Run the real NASA imagery pipeline on a computer with ESA SNAP

1. Install [ESA SNAP](https://step.esa.int/main/download/snap-download/) with the Sentinel-1 toolbox and ensure its `gpt` command is on your PATH. SNAP needs enough disk/RAM for a GRD ZIP, orbit data, and DEM. The DEM download requires network access.
2. Create a free [NASA Earthdata](https://urs.earthdata.nasa.gov/) account and generate an Earthdata token. Set `EARTHDATA_TOKEN` **locally** as an environment variable. Never put tokens in GitHub, Vercel's frontend, browser JavaScript, or public logs.
3. Install Avenry's Python dependencies using `python -m pip install -r requirements.txt`.
4. Run:

```bash
python -m scripts.run_nasa_pipeline \
  --bbox=91.69,24.71,92.05,25.07 \
  --start=2022-06-01 --end=2022-06-30 \
  --scene-index=0
```

This performs NASA ASF metadata search, authenticated source-product download, ESA SNAP orbit application, sigma0 VV/VH radiometric calibration, terrain correction, and reprojection to a 512×512 EPSG:4326 two-band dB GeoTIFF. Output is under `data/raw/nasa-asf/processed/`.

For step-by-step debugging:

```bash
python -m scripts.nasa_asf --bbox=91.69,24.71,92.05,25.07 --start=2022-06-01 --end=2022-06-30
python -m scripts.nasa_asf --bbox=91.69,24.71,92.05,25.07 --start=2022-06-01 --end=2022-06-30 --download-index=0
python -m scripts.process_nasa_grd --grd=data/raw/nasa-asf/downloads/SCENE_NAME.zip --output=data/processed/nasa-radar.tif
```

The last command requires a real file path. SNAP output band descriptions are checked before interpreting VV/VH, to prevent silently swapping radar channels.

## Model and public deployment blockers

- The repository does not contain the binary trained checkpoint or exported ONNX model. The existing `scripts.export_browser` generates it from a locally trained checkpoint and matching research scenes.
- The current model's training distribution is Sen1Floods11. A processed NASA ASF scene may be structurally compatible but **is not validated for generalization**. Do not present its prediction as reliable flood damage or hazard intelligence.
- The research dataset's official STAC metadata declares proprietary licensing. A public Vercel deployment must not redistribute the dataset, derived preview images, labels, or a model trained from it without confirming applicable rights.
- The `.github/workflows/verify-real-pipeline.yml` workflow is a private CI validation pipeline; it does not publish restricted data/model artifacts. Passing CI does not make the public application analysis-ready.

## Acceptance criteria for public one-click analysis

- [ ] Confirm redistributable training data and checkpoint rights.
- [ ] Validate a calibrated, terrain-corrected NASA scene against independently labeled water reference data.
- [ ] Make a licensed ONNX model available through an authenticated or appropriately licensed asset host.
- [ ] Deploy a secured processing service or a preprocessed public scene catalog; never expose Earthdata tokens in the browser.
- [ ] Confirm a user can choose a location/date, initiate processing, inspect a georeferenced overlay, and download a valid GeoTIFF.
- [ ] Test the actual production URL end to end, including failures and permissions.

This documentation intentionally separates **implemented code** from **verified production capabilities**.
