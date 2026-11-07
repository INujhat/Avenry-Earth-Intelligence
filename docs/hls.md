# NASA HLS workflow (separate from radar inference)

Official access documentation: https://hls.gsfc.nasa.gov/data-access-and-tools/

NASA CMR search has now passed in this environment: the documented Spain
region/date query returned two real HLS scenes. Protected asset download still
requires an Earthdata token and has not been validated. Local Fmask and
band-alignment tests pass. HLS is kept separate from radar inference.

1. Search by WGS84 region and inclusive date range (no login required by the CMR
   metadata endpoint). Run from the project root, with the Python environment active:

   ```bash
   python -m scripts.hls search --bbox=-0.8,38.0,-0.7,38.2 \
     --start 2024-09-01 --end 2024-09-05 --sensor HLSS30
   ```

   This resolves the HLS v2 collection through NASA CMR and saves metadata/asset
   links in `data/raw/hls-search.json`. It does not download whole scenes.

2. For selected protected assets, create a free NASA Earthdata account, authorize
   LP DAAC access as required, and supply `EARTHDATA_TOKEN` securely through your
   local environment or cloud environment settings. Never paste a token in chat,
   commit it, or put it in documentation. Only the supported direct HTTPS LP DAAC
   host receives the authorization header. Unexpected redirects are refused.

   ```bash
   python -m scripts.hls download --url 'SELECTED_DIRECT_HTTPS_LP_DAAC_ASSET_URL' \
     --output data/raw/hls/red.tif
   ```

   Repeat for green, blue and Fmask assets from the **same granule**. Each selected
   download is bounded to 1 GiB, written atomically and checked as a georeferenced
   raster. No giant model or full archive is downloaded.

3. For HLS v2 reflectance, use B04 red, B03 green and B02 blue for both S30 and L30.
   Obtain matching Fmask, then run:

   ```bash
   python -m scripts.hls preview --red data/raw/hls/red.tif \
     --green data/raw/hls/green.tif --blue data/raw/hls/blue.tif \
     --fmask data/raw/hls/Fmask.tif --output data/processed/hls-rgb.png
   ```

   Grids must align. Reflectance uses scale 0.0001, fill −9999, and Fmask fill 255.
   Bits 0–4 (cirrus, cloud, adjacent cloud, shadow, snow/ice) are masked; water bit
   5 is deliberately retained. Aerosol quality is not currently used to reject
   additional pixels. RGB gets a display stretch and gamma; this is visualization,
   not analysis normalization. Review current HLS product metadata before new use.

The HLS CLI does not register radar-compatible scenes or enable model inference.
A compatible optical model and held-out validation are required first.
