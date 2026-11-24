"""Export the verified DRA-UNet checkpoint for private CPU inference."""

import argparse
from pathlib import Path

import onnx
import torch

from lvseg.models import build_model

from .app.model_spec import CONTEXT_FRAMES, MODEL_HW, SOURCE_SHA256, sha256


class SegmentationGraph(torch.nn.Module):
    def __init__(self, checkpoint):
        super().__init__()
        self.model = build_model("DRA-UNet", base_channels=checkpoint["model_config"]["base_channels"])
        self.model.load_state_dict(checkpoint["state_dict"], strict=True)
        self.mean = checkpoint["normalization"]["mean"]
        self.std = checkpoint["normalization"]["std"]

    def forward(self, clip, lengths):
        x = (clip.float() / 255.0 - self.mean) / self.std
        return self.model(x, lengths)[:, 0] >= 0  # sigmoid threshold 0.5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if sha256(args.checkpoint) != SOURCE_SHA256:
        parser.error("checkpoint SHA-256 differs from the published DRA-UNet seed 2026 checkpoint")
    if args.output.suffix != ".onnx" or args.output.exists():
        parser.error("output must be a new .onnx file")
    torch.set_num_threads(2)
    with torch.serialization.safe_globals([torch.torch_version.TorchVersion]):
        checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    graph = SegmentationGraph(checkpoint).eval()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(graph, (torch.zeros(1, CONTEXT_FRAMES, 1, *MODEL_HW, dtype=torch.uint8), torch.tensor([1])),
                      args.output, input_names=["clip", "lengths"], output_names=["mask"], opset_version=17, dynamo=False)
    model = onnx.load(args.output)
    onnx.helper.set_model_props(model, {"checkpoint_sha256": SOURCE_SHA256, "model": "DRA-UNet", "seed": "2026"})
    onnx.checker.check_model(model)
    onnx.save(model, args.output)
    print(f"SHA256 {sha256(args.output)}")


if __name__ == "__main__":
    main()
