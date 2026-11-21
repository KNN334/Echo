"""Compact FCN-32 style segmentation model for the patch image branch."""


def fcn32(in_channels=3, num_classes=1, base_channels=32):
    """Build an encoder with a single 32x decoder upsample."""
    import torch

    if in_channels != 3 or num_classes != 1:
        raise ValueError("the current image contract requires 3 input channels and 1 logit")
    c = int(base_channels)
    if c < 4:
        raise ValueError("base_channels must be at least 4")
    encoder = torch.nn.Sequential(
        torch.nn.Conv2d(in_channels, c, 3, padding=1),
        torch.nn.BatchNorm2d(c),
        torch.nn.ReLU(inplace=True),
        torch.nn.MaxPool2d(2),
        torch.nn.Conv2d(c, c * 2, 3, padding=1),
        torch.nn.BatchNorm2d(c * 2),
        torch.nn.ReLU(inplace=True),
        torch.nn.MaxPool2d(2),
        torch.nn.Conv2d(c * 2, c * 4, 3, padding=1),
        torch.nn.BatchNorm2d(c * 4),
        torch.nn.ReLU(inplace=True),
        torch.nn.MaxPool2d(2),
        torch.nn.Conv2d(c * 4, c * 8, 3, padding=1),
        torch.nn.BatchNorm2d(c * 8),
        torch.nn.ReLU(inplace=True),
        torch.nn.MaxPool2d(2),
        torch.nn.Conv2d(c * 8, c * 8, 3, padding=1),
        torch.nn.ReLU(inplace=True),
        torch.nn.MaxPool2d(2),
        torch.nn.Conv2d(c * 8, num_classes, 1),
    )

    class FCN32(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = encoder

        def forward(self, image):
            logits = self.encoder(image)
            logits = torch.nn.functional.interpolate(
                logits, size=image.shape[-2:], mode="bilinear", align_corners=False
            )
            return {"out": logits}

    return FCN32()
