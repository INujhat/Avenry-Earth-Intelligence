"""Train a baseline; demo mode deliberately makes no held-out performance claim."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from ml.geospatial import NORMALIZATION, metrics, normalize, read_pair
from ml.model import UNet


def load_records(manifest, split):
    records = [r for r in manifest["scenes"] if r["split"] == split]
    arrays = []
    for r in records:
        x, y, valid, _ = read_pair(Path(r["radar"]), Path(r["label"]))
        if not valid.any():
            raise ValueError(f"Scene {r['id']} has no valid labeled radar pixels")
        arrays.append((normalize(x), y, valid))
    return records, arrays


def predict(model, x):
    model.eval()
    with torch.inference_mode():
        return torch.sigmoid(model(torch.from_numpy(x[None])))[0, 0].numpy()


def train(manifest_path, output, epochs=30, seed=42, demo=False):
    if not 1 <= epochs <= 1000:
        raise ValueError("Epochs must be between 1 and 1000")
    torch.set_num_threads(2)
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    manifest = json.loads(Path(manifest_path).read_text())
    split = "demo" if demo else "train"
    records, arrays = load_records(manifest, split)
    if not records:
        raise ValueError(f"No {split} scenes available")
    validation, va = load_records(manifest, "validation")
    testing, ta = load_records(manifest, "test")
    if demo:
        validation, va, testing, ta = [], [], [], []
    if not demo:
        groups = [{r["event"] for r in rs} for rs in [records, validation, testing]]
        if not all(groups) or any(groups[i] & groups[j] for i in range(3) for j in range(i)):
            raise ValueError("Require nonempty event-disjoint train/validation/test groups")
    patches = []
    for x, y, valid in arrays:
        for row in range(0, y.shape[0] - 127, 128):
            for col in range(0, y.shape[1] - 127, 128):
                v = valid[row : row + 128, col : col + 128]
                if v.any():
                    patches.append(
                        (
                            x[:, row : row + 128, col : col + 128],
                            np.maximum(y[row : row + 128, col : col + 128], 0),
                            v,
                        )
                    )
    if not patches:
        raise ValueError("No valid training patches")
    model = UNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    history, best, best_state = [], float("inf"), None
    for epoch in range(epochs):
        model.train()
        losses = []
        for indices in np.array_split(np.random.permutation(len(patches)), max(1, (len(patches) + 3) // 4)):
            xx = torch.from_numpy(np.stack([patches[i][0] for i in indices]))
            yy = torch.from_numpy(np.stack([patches[i][1] for i in indices])).float()
            vv = torch.from_numpy(np.stack([patches[i][2] for i in indices]))
            optimizer.zero_grad()
            loss = F.binary_cross_entropy_with_logits(model(xx)[:, 0][vv], yy[vv])
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        val_loss = None
        if va:
            model.eval()
            with torch.inference_mode():
                vals = []
                for x, y, v in va:
                    logits = model(torch.from_numpy(x[None]))[0, 0]
                    vals.append(
                        F.binary_cross_entropy_with_logits(logits[v], torch.from_numpy(y[v]).float()).item()
                    )
                val_loss = float(np.mean(vals))
        score = val_loss if val_loss is not None else float(np.mean(losses))
        if score < best:
            best = score
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": float(np.mean(losses)),
                "validation_loss": val_loss,
            }
        )
        print(json.dumps(history[-1]), flush=True)
    model.load_state_dict(best_state)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
    info = {
        "version": f"unet-{'demo' if demo else 'baseline'}-{digest[:8]}-seed{seed}-e{epochs}",
        "architecture": "two-level U-Net (2 input channels, 8 base channels)",
        "seed": seed,
        "epochs": epochs,
        "normalization": NORMALIZATION,
        "dataset_version": manifest["version"],
        "manifest_sha256": digest,
        "training_scene_ids": [r["id"] for r in records],
        "training_event_ids": sorted({r["event"] for r in records}),
        "validation_scene_ids": [r["id"] for r in validation],
        "validation_event_ids": sorted({r["event"] for r in validation}),
        "test_scene_ids": [r["id"] for r in testing],
        "evaluation_scope": "in_sample_demo" if demo else "held_out_events",
        "warning": "Trained and evaluated on the same scene. Not a generalization benchmark."
        if demo
        else "Small event-disjoint subset; not a full-dataset benchmark.",
        "history": history,
    }
    torch.save({"state_dict": best_state, "metadata": info}, output / "model.pt")
    evaluation = []
    for r, (x, y, v) in zip(records if demo else testing, arrays if demo else ta):
        evaluation.append({"scene_id": r["id"], **metrics(predict(model, x) >= 0.5, y, v)})
    info["evaluation"] = evaluation
    info["checkpoint_sha256"] = hashlib.sha256((output / "model.pt").read_bytes()).hexdigest()
    (output / "model.json").write_text(json.dumps(info, indent=2))
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/manifest.json")
    parser.add_argument("--output", default="artifacts/baseline")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    train(args.manifest, args.output, args.epochs, args.seed, args.demo)
