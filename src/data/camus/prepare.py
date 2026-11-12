"""可选 CAMUS 原始数组处理；正常 prepare 入口只核查现有处理后数据。"""
from copy import deepcopy
import hashlib
import numpy as np
from scipy import ndimage

from ..metadata import audit_metadata
from ..transforms import Transform
from ...utils.io import write_json, write_npz


def left_ventricle_mask(labels):
    """CAMUS 官方标签：0 背景、1 左室腔、2 心肌、3 左房；取 1。"""
    labels = np.asarray(labels)
    if not np.isin(labels, [0, 1, 2, 3]).all():
        raise ValueError('CAMUS 标签必须为 0/1/2/3，不能将任意 ROI 当作左室腔。')
    return (labels == 1).astype(np.uint8)


def estimate_image_support(frames):
    """仅根据图像非零区域估计最大连通声窗，不读取专家标签。"""
    support = np.any(frames > 0, axis=0)
    components, count = ndimage.label(support)
    if not count:
        raise ValueError('影像没有非零信号，不能估计声窗。')
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    return ndimage.binary_fill_holes(components == sizes.argmax())


def prepare_case(frames, raw_masks, labeled, metadata, options=None):
    """返回处理后数组和审计元数据，保留原始专家 ED/ES 标签与索引。

    输入为 T×H×W 灰度及官方多类标签；metadata 必须携带患者、切面、
    phases 和来源。裁剪/排除框不可擦除专家左室标签；自动声窗如果会
    擦除标签则整体回退到显式保留区域，并记录该事实供人工复核。
    """
    options = deepcopy(options or {})
    frames, raw_masks = np.asarray(frames), np.asarray(raw_masks)
    labeled = np.asarray(labeled)
    if (frames.ndim != 3 or not len(frames) or raw_masks.shape != frames.shape or
            labeled.shape != (len(frames),) or labeled.dtype != np.bool_ or not labeled.any()):
        raise ValueError('影像/标签必须为 T×H×W，labeled 为非空布尔标注帧索引。')
    if not np.isfinite(frames).all():
        raise ValueError('影像含非有限像素。')
    meta = deepcopy(metadata)
    if not meta.get('patient_id') or not meta.get('view'):
        raise ValueError('必须提供患者编号和切面。')
    for name, index in meta.get('phases', {}).items():
        if not isinstance(index, int) or not 0 <= index < len(frames) or not labeled[index]:
            raise ValueError(f'{name} 必须指向实际专家标注帧。')
    masks = left_ventricle_mask(raw_masks)
    masks[~labeled] = 0
    n, height, width = frames.shape
    crop = tuple(options.get('crop_xyxy', [0, 0, width, height]))
    transform = Transform((height, width), crop, tuple(options.get('output_hw', [112, 112])))
    keep = np.ones((height, width), dtype=bool)
    for x0, y0, x1, y1 in options.get('exclude_boxes_xyxy', []):
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError('排除框超出图像范围。')
        keep[y0:y1, x0:x1] = False
    support_excluded = 0
    if options.get('auto_largest_support', True):
        support = estimate_image_support(frames)
        support_excluded = int(np.count_nonzero(masks[:, ~support]))
        if not support_excluded:
            keep &= support
    x0, y0, x1, y1 = crop
    crop_keep = np.zeros_like(keep)
    crop_keep[y0:y1, x0:x1] = True
    if np.any(masks[:, ~(keep & crop_keep)]):
        raise ValueError('裁剪或排除区域擦除了专家左室标签，请人工核查 ROI。')
    limits = np.asarray(options.get('intensity_range', [0, 255]), dtype=float)
    if limits.shape != (2,) or not np.isfinite(limits).all() or limits[1] <= limits[0]:
        raise ValueError('intensity_range 需要两个递增有限值。')
    scaled = np.clip((frames.astype(float) - limits[0]) / (limits[1] - limits[0]), 0, 1)
    scaled = np.rint(scaled * 255).astype(np.uint8)
    scaled[:, ~keep] = 0
    arrays = {
        'frames': np.stack([transform.image(frame) for frame in scaled]),
        'masks': np.stack([transform.image(mask, label=True) for mask in masks]),
        'labeled': labeled.copy(), 'original_gt': masks[labeled].copy(),
        'original_gt_indices': np.flatnonzero(labeled),
    }
    audit = audit_metadata(n, meta.get('spacing_xy_mm'), meta.get('fps'),
                           meta.get('timestamps_s'), meta.get('source'))
    reviewed = options.get('roi_reviewed', False)
    if not isinstance(reviewed, bool):
        raise ValueError('roi_reviewed 必须为布尔值。')
    audit.update(transform=transform.record(audit['spacing_xy_mm']), roi_reviewed=reviewed,
                 masking_method='explicit_exclusions+largest_image_support_without_labels',
                 keep_mask_sha256=hashlib.sha256(keep.tobytes()).hexdigest(),
                 retained_pixel_fraction=float(keep.mean()),
                 image_support_excludes_reference_foreground_pixels=support_excluded,
                 auto_support_applied=bool(options.get('auto_largest_support', True) and not support_excluded),
                 removed_foreground_label_pixels=0, cropped_reference_foreground_pixels=0)
    if support_excluded:
        audit['issues'].append('auto_support_disabled_to_preserve_expert_labels')
    if not reviewed:
        audit['issues'].append('roi_not_reviewed_text_removal_unverified')
    meta.update(audit=audit, preprocess_config=options, gt_scope='expert_labeled_frames_only')
    return arrays, meta


def save_case(output, case_id, arrays, metadata):
    """保存单病例；完整数据集的 manifest 由调用方在全部病例完成后建立。"""
    from pathlib import Path
    if not case_id or Path(case_id).name != case_id:
        raise ValueError('非法病例编号。')
    output = Path(output)
    if (output / (case_id + '.npz')).exists() or (output / (case_id + '.json')).exists():
        raise FileExistsError(f'病例已存在：{case_id}')
    write_npz(output / (case_id + '.npz'), **arrays)
    write_json(output / (case_id + '.json'), metadata)
