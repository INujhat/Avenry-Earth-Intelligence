# Validation evidence

## Free browser version

The user selected free static hosting. Browser ONNX inference passed with no
Python API calls, no JavaScript errors, working GeoTIFF/JSON downloads, retained
IndexedDB history after reload and no mobile horizontal overflow. Exported ONNX
matched PyTorch decisions on all eight scenes. An actual browser-downloaded mask,
metrics, geodesic area, CRS, affine transform and nodata matched Python exactly.
The original 15 backend/deployment tests still passed. Upload of the private
hosted application is pending access to Hugging Face's binary storage hostname;
no hosted end-to-end readiness claim is made. See `browser-hosting.md`.

## Current update

The data domains are now enabled. Eight real event-disjoint scenes downloaded
and validated; the baseline was trained and evaluated on two held-out Nigeria
chips. Actual results are in `event-training-run.json`, including weak transfer
on one chip. NASA CMR search also passed and returned two scenes. Protected HLS
download is still unverified because an Earthdata token is not configured.

After branding and event-baseline integration, 13 tests, Ruff checks and the
production frontend build passed. GitHub Codespaces setup has been added; its
startup command is tested locally, but an actual Codespace has not been provisioned.

Official STAC metadata declares the dataset proprietary, so imagery, weights
and derived screenshots are excluded from Git. The historical observations below
remain a record of the earlier single-scene stage; their network blockers have
since been resolved for public dataset download and NASA search.

## Earlier single-scene validation


These observations are from actual commands in the managed Linux x86_64 cloud
machine (Python 3.12.14, Node 24.22.1, two training CPU threads). They do not
establish Mac compatibility or fresh-machine restoration beyond the checks stated.

| Check | Observed result |
| --- | --- |
| `python -m pytest -q` | 13 tests passed; no skipped tests in the prepared environment. |
| Ruff lint and format checks | Passed. |
| `python -m pip check` | No broken requirements. |
| `npm run build --prefix frontend` | TypeScript and Vite production build passed. MapLibre remains a large lazy-loaded chunk. |
| Official sample | Four pinned source files verified by SHA-256; image/label alignment and valid encoding checked. |
| Demo training | 35 deterministic CPU epochs, seed 42; real checkpoint and same-scene scores recorded. |
| Independent repeat training | Identical loss history, metrics and checkpoint SHA-256. |
| Live API | Real scene analysis completed; prediction, JSON and georeferenced GeoTIFF downloaded. |
| Chromium desktop | Catalog, map, run, layer toggles, history, methodology and GeoTIFF request passed; zero page JavaScript errors. |
| Chromium mobile 390×844 | No document horizontal overflow; actual screenshot inspected. |
| Native startup | `bash scripts/start.sh` starts the production UI/API; SQLite completed history persisted across restart. |
| Repeat setup | `bash scripts/bootstrap.sh` completed against existing data/checkpoint; build and 13 tests passed. |
| PostGIS | PostgreSQL 16 / PostGIS 3.5; catalog insert and ST_Intersects query returned the Spain region. |
| Fresh migration cycle | PostgreSQL upgrade → downgrade → upgrade passed with the final migration. |
| Docker image | Multi-stage image built with TLS verification and configured CA; native imports checked. |
| Docker app + PostGIS | Real background analysis and GeoTIFF request passed; completed job persisted across app-container restart. |
| Docker Compose | Configuration parsed successfully with a temporary validation-only variable; full `compose up` was not separately executed. Equivalent image/database containers were exercised directly. |
| GitHub Actions | Workflow written; not run on GitHub because changes have not been pushed. |

The installed baseline predicts approximately **4.955067 km²** of surface water
for the Spain sample at threshold 0.5, using geodesic valid-pixel area. This is a
model output, not verified flood extent. The same-scene metrics in
`sample-training-run.json` are not a generalization benchmark.

Expected/remaining warnings:

- Starlette currently emits a deprecation warning for its HTTPX test-client path.
  Tests work; no assertions or verification were disabled.
- Vite warns about MapLibre's large chunk. The map is lazy-loaded, so the initial
  dashboard bundle is smaller. No arbitrary warning threshold was raised.

Container testing identified and corrected restricted copied-file permissions and
missing `libexpat1`; the corrected image passed the full smoke test.

## External blockers and unrun work

- `storage.googleapis.com`: proxy CONNECT denied (403). No multi-event subset
  download or held-out experiment completed. The subset command remains unverified
  against remote files in this environment.
- NASA documentation and CMR hosts: HTTP 403 through current network policy.
  Live search and authenticated asset downloads were not validated. Earthdata
  credentials are not currently configured. Local mask/alignment tests passed.
- The official dataset repository contains no explicit license file. Verify
  dataset/imagery terms before public redistribution of data-derived artifacts.
- No Prithvi weights downloaded or comparison experiment run.
- No public hosted app, GitHub push, MacBook execution, production authentication,
  multi-worker durable queue, or new-task snapshot restoration was verified.

Network-domain requirements were saved to the environment draft. A draft save
neither activates access nor publishes an application. Configuration review is
needed to enable the blocked destinations; no public deployment was performed.
