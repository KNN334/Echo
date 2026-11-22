"""Overlap metrics for the frames that contain expert masks."""

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt


def overlap_metrics(prediction, reference, spacing_xy_mm=None) -> dict:
    prediction = np.asarray(prediction, dtype=bool)
    reference = np.asarray(reference, dtype=bool)
    if prediction.shape != reference.shape:
        raise ValueError("Predicted and reference masks must have equal shape")
    intersection = int(np.count_nonzero(prediction & reference))
    pred_area, ref_area = int(prediction.sum()), int(reference.sum())
    union = pred_area + ref_area - intersection
    background_intersection = int(np.count_nonzero(~prediction & ~reference))
    background_union = int(np.count_nonzero(~prediction | ~reference))
    iou = intersection / union if union else 1.0
    background_iou = (background_intersection / background_union
                      if background_union else 1.0)
    precision = (intersection / pred_area if pred_area else
                 (1.0 if ref_area == 0 else 0.0))
    recall = (intersection / ref_area if ref_area else
              (1.0 if pred_area == 0 else 0.0))
    if spacing_xy_mm is None:
        sampling = (1.0,) * prediction.ndim
        distance_unit = "pixel"
    else:
        spacing_x, spacing_y = map(float, spacing_xy_mm)
        if not np.isfinite([spacing_x, spacing_y]).all() or min(spacing_x, spacing_y) <= 0:
            raise ValueError("Pixel spacing must contain positive finite values")
        sampling = (spacing_y, spacing_x)
        distance_unit = "mm"

    if pred_area and ref_area:
        structure = np.ones((3,) * prediction.ndim, dtype=bool)
        pred_surface = prediction & ~binary_erosion(prediction, structure=structure)
        ref_surface = reference & ~binary_erosion(reference, structure=structure)
        distance_to_pred = distance_transform_edt(~pred_surface, sampling=sampling)
        distance_to_ref = distance_transform_edt(~ref_surface, sampling=sampling)
        pred_to_ref = distance_to_ref[pred_surface]
        ref_to_pred = distance_to_pred[ref_surface]
        hd95 = float(np.percentile(np.concatenate((pred_to_ref, ref_to_pred)), 95))
        asd = float((pred_to_ref.sum() + ref_to_pred.sum()) /
                    (len(pred_to_ref) + len(ref_to_pred)))
    else:
        hd95 = asd = None
    return {
        "iou": iou,
        "miou": (iou + background_iou) / 2.0,
        "dice": 2 * intersection / (pred_area + ref_area)
        if pred_area + ref_area else 1.0,
        "precision": precision,
        "recall": recall,
        "hd95": hd95,
        "asd": asd,
        "boundary_distance_unit": distance_unit,
    }
