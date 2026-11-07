import numpy as np
import pytest
import torch

from ml.model import UNet
from ml.train import train


def test_model_preserves_odd_spatial_shape_and_backpropagates():
    torch.set_num_threads(2)
    model = UNet()
    x = torch.zeros(2, 2, 35, 47)
    output = model(x)
    assert output.shape == (2, 1, 35, 47)
    output.mean().backward()
    assert model.head.weight.grad is not None
    assert np.isfinite(model.head.weight.grad.numpy()).all()


def test_no_demo_scene_used_as_real_training(tmp_path):
    import json

    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"scenes": [{"split": "demo"}]}))
    with pytest.raises(ValueError, match="No train scenes"):
        train(path, tmp_path / "output", epochs=1)
