"""Compare deployed preprocessing with fan alignment on paired PNGs at source resolution."""

import argparse
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .app.config import Settings
from .app.model_spec import MODEL_HW
from .app.services.segmenter import DraSegmenter, prepare_frames, resized


def evaluate(segmenter, images: Path, labels: Path, mask_value: int):
    inputs = sorted(images.glob("*.png"))
    if not inputs or {p.name for p in inputs} != {p.name for p in labels.glob("*.png")}:
        raise ValueError("Expected one source mask for every PNG filename")
    scores = {"direct": [], "aligned": []}
    rotations = Counter()
    for path in inputs:
        with Image.open(labels / path.name) as image:
            truth = np.asarray(image.convert("L")) == mask_value
        with Image.open(path) as image:
            source = np.asarray(image.convert("L"))
        if source.shape != truth.shape or not truth.any():
            raise ValueError("Each image requires an aligned, nonempty LV cavity mask")
        frames, _, _, turns = prepare_frames(path, max_frames=1)
        rotations[turns] += 1
        original = resized(source, MODEL_HW[::-1])[None]
        old = segmenter.predict(original, lambda *_: None)[0]
        current = segmenter.predict(frames, lambda *_: None)[0] if turns else old
        for key, mask in (("direct", old), ("aligned", np.rot90(current, -turns))):
            prediction = cv2.resize(mask.astype(np.uint8), truth.shape[::-1], interpolation=cv2.INTER_NEAREST) > 0
            intersection = np.count_nonzero(prediction & truth)
            predicted = np.count_nonzero(prediction)
            scores[key].append((2 * intersection / (predicted + truth.sum()),
                                intersection / np.count_nonzero(prediction | truth)))
    for key, values in scores.items():
        dice, iou = np.asarray(values).T
        print(f"{key}: Dice={dice.mean():.4f} IoU={iou.mean():.4f} "
              f"median_Dice={np.median(dice):.4f} Dice<0.5={np.count_nonzero(dice < 0.5)}")
    print(f"images={len(inputs)}; rotations={dict(rotations)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("images", type=Path)
    parser.add_argument("masks", type=Path)
    parser.add_argument("--mask-value", type=int, required=True)
    args = parser.parse_args()
    evaluate(DraSegmenter(Settings(inference_checkpoint=args.checkpoint)), args.images, args.masks, args.mask_value)


if __name__ == "__main__":
    main()
