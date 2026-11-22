"""Overlap metrics for the frames that contain expert masks."""

import numpy as np


def overlap_metrics(prediction, reference) -> dict:
    prediction = np.asarray(prediction, dtype=bool)
    reference = np.asarray(reference, dtype=bool)
    if prediction.shape != reference.shape:
        raise ValueError("Predicted and reference masks must have equal shape")
    intersection = int(np.count_nonzero(prediction & reference))
    pred_area, ref_area = int(prediction.sum()), int(reference.sum())
    union = pred_area + ref_area - intersection
    return {"iou": intersection / union if union else 1.0,
            "dice": 2 * intersection / (pred_area + ref_area)
            if pred_area + ref_area else 1.0}
