# Free hosted browser application

The user selected browser inference after Hugging Face rejected Docker Spaces
with HTTP 402 (PRO is required for compute-backed Spaces). Static Spaces are
served without paid compute. The Space is private under `NujAMred`.

## Architecture

The same React/MapLibre interface has two explicit modes:

- Native/Docker: FastAPI, SQL database, PyTorch worker and server-side files.
- Hosted static: ONNX Runtime WebAssembly, IndexedDB device history and client
  downloads. It has no hosted FastAPI endpoint, database server or server-side jobs.

The original FastAPI backend remains available in this repository. The static
mode is an explicit hosting adaptation, not a claim that Python runs on static
hosting. No paid inference API is called. Raw scene inputs remain static files;
analyses and results execute and stay in the user's browser.

## Real model and data

`scripts/export_browser.py` exports the existing trained U-Net, verifies its
checksum and checks the ONNX graph. All eight exported scenes were compared
against PyTorch: maximum logit difference was below 0.000005 and there were zero
water/non-water threshold disagreements. See `browser-conversion-validation.json`.
The normalization, invalid mask and 0.5 probability threshold are unchanged.

Data include verified radar input tensors, optical/radar/reference previews,
labels and validity, WGS84 geodesic per-row pixel areas, and an uncompressed
GeoTIFF template. The browser fills the template's actual image strips, preserving
CRS, affine transform and nodata 255. SHA-256 checks protect downloaded model,
scene data and WebAssembly chunks. The runtime uses one thread so it does not
require cross-origin-isolation headers or shared memory.

The first analysis downloads the runtime and selected scene. Browser performance
varies by device. Keep the tab open during a run; unfinished history is marked
failed after reload. History and Blob outputs are stored in IndexedDB on the
current browser, not synchronized across devices. Clearing site storage removes
those results. Export files you want to keep.

## Rebuild

From the project root, after preparing the real dataset and checkpoint:

```bash
.venv/bin/python -m pip install -r requirements-browser-export.txt
npm ci --prefix frontend
npm run build:browser --prefix frontend
.venv/bin/python -m scripts.export_browser --output frontend/browser-dist
.venv/bin/python -m scripts.deploy_static
```

The deploy command requires the securely configured `HF_TOKEN`, checks the
account and existing private static Space, and never requests paid hardware.
It sends bounded asset batches and updates the entry point last. No token is
included in the frontend or uploaded files.

## Actual local browser validation

Chromium ran real ONNX inference with zero Python API requests and no JavaScript
errors. Layer controls, GeoTIFF/JSON downloads, history after reload and mobile
width checks passed. The browser-generated Nigeria mask matched Python pixel
for pixel; all metrics, geodesic area, CRS, affine transform and nodata matched.
This was verified using actual downloaded files, not hardcoded displayed values.
Recheck downloaded outputs with:

```bash
.venv/bin/python -m scripts.verify_browser_result \
  --mask /path/to/avenry-water-mask.tif --metadata /path/to/avenry-result.json
```

Hosted file integrity and Space status must also be checked after upload before
sharing a live link. This is still a small, uneven research model, not proof of
new flooding or emergency suitability. Official dataset STAC declares proprietary
terms; the Space remains private pending applicable redistribution rights.

## Current delivery blocker

The free private static Space exists, but the application upload is not complete.
Hugging Face requires binary assets to use its supported LFS storage. The signed
upload destination is `hf-hub-lfs-us-east-1.s3-accelerate.amazonaws.com`, currently
blocked by the cloud outbound policy. This exact domain and the provider-returned
static hostname `nujamred-avenry-earth-intelligence.static.hf.space` were added to
the draft, preserving existing domains. The token is valid and needs no change.
The deploy script uses supported basic LFS uploads and regular text commits;
it does not print signed URLs or send the HF token to object storage.

After environment access is saved, rerun the static deployment and verify the
committed asset hashes and live private preview. Do not mistake the starter
Space page for the completed Avenry website.
