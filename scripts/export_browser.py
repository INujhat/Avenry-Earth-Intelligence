"""Export the real checkpoint and geospatial data for private browser inference."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import rasterio
import tifffile
import torch

from ml.geospatial import area_km2, normalize, prepare_scene, read_pair
from ml.model import UNet

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = output / "data"
    data.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    info = json.loads((ROOT / "artifacts/baseline/model.json").read_text())
    checkpoint_path = ROOT / "artifacts/baseline/model.pt"
    if sha(checkpoint_path) != info["checkpoint_sha256"]:
        raise ValueError("Checkpoint checksum mismatch")
    model = UNet()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    torch.set_num_threads(2)
    model_path = data / "water-unet.onnx"
    torch.onnx.export(
        model,
        torch.zeros(1, 2, 512, 512),
        str(model_path),
        input_names=["radar"],
        output_names=["logits"],
        opset_version=17,
        dynamo=False,
        external_data=False,
    )
    onnx.checker.check_model(onnx.load(model_path))
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
    scenes, checks = [], []
    for scene in sorted(
        manifest["scenes"],
        key=lambda r: ({"test": 0, "validation": 1, "train": 2}.get(r["split"], 3), r["id"]),
    ):
        folder = data / "scenes" / scene["id"]
        folder.mkdir(parents=True, exist_ok=True)
        image, label, optical = [ROOT / scene[k] for k in ["radar", "label", "optical"]]
        x, y, valid, profile = read_pair(image, label)
        if (
            x.shape != (2, 512, 512)
            or str(profile["crs"]) != "EPSG:4326"
            or profile["transform"].b
            or profile["transform"].d
        ):
            raise ValueError("Browser model requires 512x512 north-up EPSG:4326 two-band scenes")
        normalized = normalize(x)
        normalized.astype("<f4").tofile(folder / "radar.f32")
        y.astype("int8").tofile(folder / "labels.i8")
        valid.astype("uint8").tofile(folder / "valid.u8")
        weights = []
        for row in range(y.shape[0]):
            one = np.zeros(y.shape, dtype=bool)
            one[row, 0] = True
            weights.append(area_km2(one, profile))
        np.asarray(weights, dtype="<f8").tofile(folder / "pixel-area-km2.f64")
        prepare_scene(image, label, optical, folder)
        tiff_profile = profile.copy()
        for key in ["blockxsize", "blockysize", "compress", "interleave"]:
            tiff_profile.pop(key, None)
        tiff_profile.update(driver="GTiff", dtype="uint8", count=1, nodata=255, tiled=False)
        with rasterio.open(folder / "mask-template.tif", "w", **tiff_profile) as dst:
            dst.write(np.full(y.shape, 255, dtype="uint8"), 1)
            dst.update_tags(
                classes="0=non-water,1=water,255=invalid", interpretation="detected surface water"
            )
        with tifffile.TiffFile(folder / "mask-template.tif") as tif:
            page = tif.pages[0]
            strips = [
                {"offset": int(o), "length": int(n)} for o, n in zip(page.dataoffsets, page.databytecounts)
            ]
            assert sum(s["length"] for s in strips) == y.size
        prefix = f"./data/scenes/{scene['id']}/"
        public = {k: v for k, v in scene.items() if k not in {"radar", "label", "optical"}}
        public.update(
            dataset_version=manifest["version"],
            assets={k: prefix + f"{k}.png" for k in ["radar", "optical", "label"]},
            browser_assets={
                k: prefix + v
                for k, v in {
                    "radar": "radar.f32",
                    "labels": "labels.i8",
                    "valid": "valid.u8",
                    "area": "pixel-area-km2.f64",
                    "template": "mask-template.tif",
                }.items()
            },
            tiff_strips=strips,
        )
        public["checksums"] = {
            name: sha(path)
            for name, url in public["browser_assets"].items()
            if (path := folder / url.split("/")[-1]).is_file()
        }
        scenes.append(public)
        with torch.inference_mode():
            pytorch = model(torch.from_numpy(normalized[None])).numpy()
        converted = session.run(None, {"radar": normalized[None]})[0]
        diff = float(np.max(np.abs(pytorch - converted)))
        if diff > 0.0002:
            raise ValueError(f"ONNX conversion error {diff} in {scene['id']}")
        flips = int(((pytorch >= 0) != (converted >= 0)).sum())
        checks.append(
            {"scene_id": scene["id"], "max_logit_difference": diff, "threshold_disagreements": flips}
        )
    runtime = output / "runtime"
    runtime.mkdir(exist_ok=True)
    distribution = ROOT / "frontend/node_modules/onnxruntime-web/dist"
    shutil.copyfile(distribution / "ort-wasm-simd-threaded.mjs", runtime / "ort-wasm-simd-threaded.mjs")
    binary = (distribution / "ort-wasm-simd-threaded.wasm").read_bytes()
    chunks = []
    for start in range(0, len(binary), 3 * 1024 * 1024):
        path = runtime / f"wasm-{len(chunks)}.bin"
        path.write_bytes(binary[start : start + 3 * 1024 * 1024])
        chunks.append({"path": f"./runtime/{path.name}", "sha256": sha(path)})
    catalog = {
        "scenes": scenes,
        "model": info,
        "onnx": {"path": "./data/water-unet.onnx", "sha256": sha(model_path)},
        "runtime": {"chunks": chunks, "mjs": "./runtime/ort-wasm-simd-threaded.mjs"},
        "conversion_validation": checks,
    }
    (data / "catalog.json").write_text(json.dumps(catalog, indent=2))
    (ROOT / "docs/browser-conversion-validation.json").write_text(json.dumps(checks, indent=2))
    print(f"Exported {len(scenes)} real scenes and checkpoint; all PyTorch/ONNX comparisons passed")
    print(json.dumps(checks))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="frontend/browser-dist")
    export(parser.parse_args().output)
