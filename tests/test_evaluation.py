import numpy as np
import pytest

from ml.evaluation import confusion, evaluate, rates


def record(name="a", event="event-a", split="test"):
    return {
        "id": name, "event": event, "split": split,
        "probability": np.array([[0.9, 0.8], [0.2, 0.1]], dtype=float),
        "label": np.array([[1, 0], [1, 0]], dtype=np.int8),
        "valid": np.array([[1, 1], [1, 0]], dtype=bool),
    }


def test_confusion_and_metrics_ignore_invalid():
    c = confusion(record()["probability"], record()["label"], record()["valid"])
    assert c == {"tp": 1, "fp": 1, "fn": 1, "tn": 0, "valid_pixels": 3}
    assert rates(c)["iou"] == pytest.approx(1 / 3)
    assert rates(c)["dice_f1"] == pytest.approx(0.5)


def test_event_report_is_reproducible():
    rows = [record(), record("b", "event-b")]
    a = evaluate(rows, bootstrap=50, seed=12)
    b = evaluate(rows, bootstrap=50, seed=12)
    assert a == b
    assert a["event_count"] == 2
    assert a["scene_count"] == 2
    assert a["scope"] == "held_out_test_events"
    assert a["counts"]["valid_pixels"] == 6


def test_reject_training_and_duplicate_ids():
    with pytest.raises(ValueError, match="Only test"):
        evaluate([record(split="train")])
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate([record(), record()])


def test_reject_invalid_probabilities_and_labels():
    r = record()
    r["probability"][0, 0] = np.nan
    with pytest.raises(ValueError, match="probabilities"):
        evaluate([r])
    r = record()
    r["label"][0, 0] = 2
    with pytest.raises(ValueError, match="binary"):
        evaluate([r])


def test_empty_positive_class_reports_undefined_not_perfect():
    r = record()
    r["label"][:] = 0
    r["probability"][:] = 0
    report = evaluate([r], bootstrap=0)
    assert report["micro_metrics"]["iou"] is None
    assert report["micro_metrics"]["recall"] is None
    assert report["micro_metrics"]["specificity"] == 1
    assert report["event_bootstrap_95pct_ci"]["iou"] is None
