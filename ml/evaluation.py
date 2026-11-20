"""Reproducible, event-disjoint evaluation for binary surface-water predictions.

Use only held-out, labeled scenes. This module never claims a score without inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def confusion(probability, label, valid, threshold=0.5):
    p, y, v = np.asarray(probability), np.asarray(label), np.asarray(valid, dtype=bool)
    if p.shape != y.shape or p.shape != v.shape:
        raise ValueError("Probability, label and valid masks must share a shape")
    if not 0 < threshold < 1:
        raise ValueError("Threshold must be between zero and one")
    if not np.isfinite(p[v]).all() or np.any((p[v] < 0) | (p[v] > 1)):
        raise ValueError("Valid probabilities must be finite and in [0,1]")
    if not np.isin(y[v], [0, 1]).all():
        raise ValueError("Valid labels must be binary")
    predicted = p[v] >= threshold
    truth = y[v] == 1
    tp = int(np.count_nonzero(predicted & truth))
    fp = int(np.count_nonzero(predicted & ~truth))
    fn = int(np.count_nonzero(~predicted & truth))
    tn = int(np.count_nonzero(~predicted & ~truth))
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, valid_pixels=int(v.sum()))


def rates(c):
    tp, fp, fn, tn = (c[k] for k in ("tp", "fp", "fn", "tn"))
    def div(a, b):
        return a / b if b else None
    return {
        "iou": div(tp, tp + fp + fn),
        "dice_f1": div(2 * tp, 2 * tp + fp + fn),
        "precision": div(tp, tp + fp),
        "recall": div(tp, tp + fn),
        "specificity": div(tn, tn + fp),
        "balanced_accuracy": (
            (tp / (tp + fn) + tn / (tn + fp)) / 2
            if tp + fn and tn + fp else None
        ),
    }


def evaluate(records, threshold=0.5, bootstrap=1000, seed=42):
    """Each record: id, event, split, probability, label, valid arrays.

    Macro scores weight each held-out event equally; micro scores pool pixels.
    Bootstrap resamples EVENTS, not pixels, to avoid false precision.
    """
    records = list(records)
    if not records:
        raise ValueError("At least one labeled test scene is required")
    if any(r.get("split") != "test" for r in records):
        raise ValueError("Only test-split scenes can enter the held-out report")
    if any(not r.get("event") or not r.get("id") for r in records):
        raise ValueError("Every scene needs an id and event")
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate scene id")
    by_event = {}
    scene_rows = []
    for r in records:
        c = confusion(r["probability"], r["label"], r["valid"], threshold)
        if not c["valid_pixels"]:
            raise ValueError(f"No valid pixels for {r['id']}")
        v = np.asarray(r["valid"], dtype=bool)
        p = np.asarray(r["probability"])[v]
        y = np.asarray(r["label"])[v]
        brier = float(np.mean((p - y) ** 2))
        scene_rows.append({"scene_id": r["id"], "event": r["event"], "counts": c, "metrics": rates(c), "brier_score": brier})
        total = by_event.setdefault(r["event"], dict(tp=0, fp=0, fn=0, tn=0, valid_pixels=0))
        for k in total:
            total[k] += c[k]
    event_rows = [{"event": name, "counts": c, "metrics": rates(c)} for name, c in sorted(by_event.items())]
    totals = {k: sum(c[k] for c in by_event.values()) for k in ("tp", "fp", "fn", "tn", "valid_pixels")}
    macro = {k: float(np.mean(values)) if values else None for k in rates(totals)
             for values in [[e["metrics"][k] for e in event_rows if e["metrics"][k] is not None]]}
    ci = {}
    rng = np.random.default_rng(seed)
    event_counts = list(by_event.values())
    for metric in ("iou", "dice_f1", "precision", "recall"):
        samples = []
        for _ in range(bootstrap):
            sampled = rng.integers(0, len(event_counts), len(event_counts))
            values = [rates(event_counts[i])[metric] for i in sampled]
            values = [x for x in values if x is not None]
            if values:
                samples.append(float(np.mean(values)))
        ci[metric] = [float(x) for x in np.percentile(samples, [2.5, 97.5])] if samples else None
    return {
        "scope": "held_out_test_events",
        "threshold": threshold,
        "scene_count": len(scene_rows),
        "event_count": len(event_rows),
        "counts": totals,
        "micro_metrics": rates(totals),
        "macro_event_metrics": macro,
        "event_bootstrap_95pct_ci": ci,
        "bootstrap_samples": bootstrap,
        "seed": seed,
        "scenes": scene_rows,
        "events": event_rows,
        "limitations": [
            "Valid labeled pixels only; unlabeled pixels are excluded.",
            "Event bootstrap intervals may be unstable with few events.",
            "Surface-water segmentation does not establish new flooding or damage.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON with test scenes: id,event,split,probability,label,valid (.npy paths)")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation/report.json"))
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args()
    if args.bootstrap < 0 or args.bootstrap > 100000:
        parser.error("--bootstrap must be 0..100000")
    raw = args.manifest.read_bytes()
    manifest = json.loads(raw)
    root = args.manifest.parent
    records = []
    for row in manifest["scenes"]:
        record = {k: row[k] for k in ("id", "event", "split")}
        for k in ("probability", "label", "valid"):
            path = (root / row[k]).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Input paths must remain inside the manifest directory")
            record[k] = np.load(path, allow_pickle=False)
        records.append(record)
    report = evaluate(records, args.threshold, args.bootstrap)
    report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Evaluation written to {args.output} ({report['event_count']} held-out events)")


if __name__ == "__main__":
    main()
