# Data provenance and handling

Run `python -m scripts.prepare_sample` from the repository root. It downloads
only the official Spain sample and event metadata at pinned upstream commit
`b9e460dabe70230111a3c3d36cd0c5ce03606ee9`, verifies the SHA-256 values in
`sample-sources.json`, validates alignment, and renders previews. No bucket sync.
Raw files, processed images, generated scene manifests, databases and outputs are
ignored by Git. The installed sample totals about 3.7 MB (excluding metadata).

Verified sample:

- Scene: `Spain_7370579`, bounds approximately −0.781894…−0.735900 longitude,
  38.082819…38.128813 latitude, EPSG:4326, 512 × 512 pixels.
- Sentinel-1: two Float32 channels, VV then VH, in dB; NaN no-data.
- Sentinel-2: 13 **Int16** channels in this actual sample, despite UInt16 in the
  general upstream README. Model inputs use radar only. RGB uses 1-based bands
  4, 3, 2, scaled by 10000, display stretch 0…0.3, gamma 1.8.
- Hand labels: Int16, −1 invalid (99 pixels), 0 non-water (192010), 1 water (70035).
- Radar event date: 2019-09-17. Optical event date: 2019-09-18, from upstream
  event metadata; event-level dates are not independent per-chip observations.
- Spatial alignment is checked on dimensions, CRS and affine transform.
- Inputs clip radar values to −30…5 dB and scale to 0…1. Nonfinite inputs and
  negative labels are excluded from loss, metrics and area estimates.

The sample is marked `demo`, never train/validation/test. Its checkpoint is an
in-sample workflow demonstration. It supplies no geographic generalization evidence.

## Larger research subset (downloaded and evaluated)

`python -m scripts.prepare_subset` reads the official train/valid/test CSV inventory
and selects at most two chips from each of four events. It **reassigns entire
events** to two train events, one validation event and one test event, excluding
Spain. This is a custom event-disjoint pilot split, not the official benchmark.
It records selected URLs, hashes and assignment in `data/subset-manifest.json`
without replacing the installed demo catalog. Inspect that manifest first.
The remote downloader completed in the updated environment. Eight scenes were
validated and used in the pilot: Ghana/India training, Mekong validation, Nigeria
testing. A test report is recorded in `docs/event-training-run.json`. Its URLs
follow the official notebook's v1.1 paths.

## Attribution and licensing

Source: https://github.com/cloudtostreet/Sen1Floods11

Bonafilia, D., Tellman, B., Anderson, T., Issenberg, E. (2020), *Sen1Floods11:
a georeferenced dataset to train and test deep learning flood algorithms for
Sentinel-1*, CVPR Workshops, pp. 210–211.

The official STAC source and hand-label collection metadata declares
**`license: proprietary`**. This was checked directly at:

- https://storage.googleapis.com/sen1floods11/v1.1/catalog/sen1floods11_hand_labeled_source/collection.json
- https://storage.googleapis.com/sen1floods11/v1.1/catalog/sen1floods11_hand_labeled_label/collection.json

The repository itself has no LICENSE file. Public availability does not override
this declaration. Keep data, labels, learned weights and data-derived screenshots
private until applicable redistribution rights are obtained. The GitHub branch
contains code and research documentation only; its private development setup
fetches the source data rather than bundling them in Git.
