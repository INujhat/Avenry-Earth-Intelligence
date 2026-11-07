"""Small U-Net with two encoder levels and explicit two-band input."""

import torch
from torch import nn
from torch.nn import functional as F


def block(a, b):
    return nn.Sequential(
        nn.Conv2d(a, b, 3, padding=1),
        nn.ReLU(),
        nn.Conv2d(b, b, 3, padding=1),
        nn.ReLU(),
    )


class UNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc1, self.enc2 = block(2, 8), block(8, 16)
        self.bridge = block(16, 32)
        self.dec2, self.dec1 = block(48, 16), block(24, 8)
        self.head = nn.Conv2d(8, 1, 1)

    def forward(self, x):
        a = self.enc1(x)
        b = self.enc2(F.max_pool2d(a, 2))
        c = self.bridge(F.max_pool2d(b, 2))
        d = self.dec2(
            torch.cat(
                [
                    F.interpolate(c, size=b.shape[-2:], mode="bilinear", align_corners=False),
                    b,
                ],
                1,
            )
        )
        return self.head(
            self.dec1(
                torch.cat(
                    [
                        F.interpolate(d, size=a.shape[-2:], mode="bilinear", align_corners=False),
                        a,
                    ],
                    1,
                )
            )
        )
