"""Explicit image-only ROI and label-independent transforms; pixel centers are integer coordinates."""
from dataclasses import dataclass, asdict
import hashlib
import numpy as np
from PIL import Image, ImageDraw
from .metadata import audit_metadata


@dataclass
class Transform:
    original_hw: tuple
    crop_xyxy: tuple
    output_hw: tuple

    def __post_init__(self):
        h, w = self.original_hw
        x0, y0, x1, y1 = self.crop_xyxy
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError("crop outside source image")
        if min(self.output_hw) < 1:
            raise ValueError("invalid output size")

    @property
    def matrix(self):
        x0, y0, x1, y1 = self.crop_xyxy
        oh, ow = self.output_hw
        sx, sy = ow / (x1 - x0), oh / (y1 - y0)
        return np.array([[sx, 0, sx * (0.5 - x0) - 0.5],
                         [0, sy, sy * (0.5 - y0) - 0.5], [0, 0, 1.]])

    def points(self, xy, inverse=False):
        a = np.asarray(xy, float)
        matrix = np.linalg.inv(self.matrix) if inverse else self.matrix
        return (np.c_[a.reshape(-1, 2), np.ones(a.size // 2)] @ matrix.T)[:, :2].reshape(a.shape)

    def image(self, image, label=False):
        x0, y0, x1, y1 = self.crop_xyxy
        oh, ow = self.output_hw
        return np.asarray(Image.fromarray(image[y0:y1, x0:x1]).resize(
            (ow, oh), Image.Resampling.NEAREST if label else Image.Resampling.BILINEAR))

    def restore_mask(self, mask):
        x0, y0, x1, y1 = self.crop_xyxy
        out = np.zeros(self.original_hw, np.uint8)
        out[y0:y1, x0:x1] = np.asarray(Image.fromarray(mask.astype(np.uint8)).resize(
            (x1 - x0, y1 - y0), Image.Resampling.NEAREST))
        return out

    def record(self, spacing):
        r = asdict(self)
        r.update(original_to_processed=self.matrix.tolist(), processed_to_original=np.linalg.inv(self.matrix).tolist(),
                 coordinate_convention="integer_pixel_centers_half_pixel_resize")
        if spacing is not None:
            r["processed_spacing_xy_mm"] = [spacing[0] / self.matrix[0, 0], spacing[1] / self.matrix[1, 1]]
        return r


def process(frames, config, metadata, labels=None):
    """Text removal is by reviewed ROI/keep polygon/exclusion boxes, not brightness thresholding."""
    frames = np.asarray(frames)
    if frames.ndim == 4 and frames.shape[-1] == 3:
        frames = np.rint(frames @ np.array([.299, .587, .114])).astype(np.uint8)
    if frames.ndim != 3 or not np.all(np.isfinite(frames)):
        raise ValueError("frames must be finite T,H,W grayscale or T,H,W,3 RGB")
    n, h, w = frames.shape
    transform = Transform((h, w), tuple(config.get("crop_xyxy", [0, 0, w, h])), tuple(config.get("output_hw", [112, 112])))
    keep = np.ones((h, w), bool)
    if config.get("auto_largest_support", False):
        from scipy import ndimage
        support = np.max(frames, axis=0) > config.get("support_threshold", 0)
        components, n_components = ndimage.label(support)
        if not n_components:
            raise ValueError("no nonzero ultrasound support")
        sizes = np.bincount(components.ravel()); sizes[0] = 0
        keep &= ndimage.binary_fill_holes(components == sizes.argmax())
    if config.get("keep_polygon_xy"):
        canvas = Image.new("L", (w, h))
        ImageDraw.Draw(canvas).polygon([tuple(x) for x in config["keep_polygon_xy"]], fill=1)
        keep &= np.array(canvas).astype(bool)
    for x0, y0, x1, y1 in config.get("exclude_boxes_xyxy", []):
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError("exclusion box outside source image")
        keep[y0:y1, x0:x1] = False
    finite = frames.astype(np.float32)
    # CAMUS byte images remain unchanged; other ranges need an explicit linear mapping.
    scale = config.get("intensity_range", [0, 255])
    if scale[1] <= scale[0]:
        raise ValueError("invalid intensity range")
    finite = np.clip((finite - scale[0]) * 255 / (scale[1] - scale[0]), 0, 255).astype(np.uint8)
    output = np.stack([transform.image(np.where(keep, f, 0).astype(np.uint8)) for f in finite])
    label_output = None
    if labels is not None:
        # Image support is not anatomical truth: dark myocardium/cavity can have expert labels.
        # Labels follow only geometric crop/resize, never an intensity-derived exclusion mask.
        label_output = np.stack([transform.image(m.astype(np.uint8), label=True) for m in labels])
    audit = audit_metadata(n, metadata.get("spacing_xy_mm"), metadata.get("fps"), metadata.get("timestamps_s"), metadata.get("source"))
    audit["transform"] = transform.record(audit["spacing_xy_mm"])
    audit["roi_reviewed"] = bool(config.get("roi_reviewed", False))
    audit["masking_method"] = "explicit_keep_polygon_and_exclusion_boxes"
    if config.get("auto_largest_support", False):
        audit["masking_method"] += "+largest_image_support_no_labels"
    audit["keep_mask_sha256"] = hashlib.sha256(np.packbits(keep).tobytes()).hexdigest()
    audit["retained_pixel_fraction"] = float(keep.mean())
    if labels is not None:
        removed = int(np.count_nonzero(np.asarray(labels)[:, ~keep]))
        audit["image_support_excludes_reference_foreground_pixels"] = removed
        x0,y0,x1,y1=transform.crop_xyxy
        cropped=int(np.count_nonzero(labels)-np.count_nonzero(np.asarray(labels)[:,y0:y1,x0:x1]))
        audit["cropped_reference_foreground_pixels"] = cropped
        audit["removed_foreground_label_pixels"] = cropped
        if removed:
            audit["issues"].append("image_support_excludes_reference_foreground_review_required")
    if not audit["roi_reviewed"]:
        audit["issues"].append("roi_not_reviewed_text_removal_unverified")
    return output, label_output, audit
