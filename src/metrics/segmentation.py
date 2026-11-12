"""Dice、ASSD、HD95 和关键点欧氏距离。"""
import numpy as np
from scipy import ndimage


def segmentation_metrics(pred, truth, spacing_xy=None):
    """计算 Dice、平均对称边界距离及 Hausdorff 距离。"""
    p, g = np.asarray(pred, bool), np.asarray(truth, bool)
    if p.shape != g.shape:
        raise ValueError("mask dimensions differ")
    total = p.sum() + g.sum()
    dice = float(2 * (p & g).sum() / total) if total else None
    result = {"dice": dice, "assd": None, "hd95": None, "hd_max": None,
              "distance_unit": "mm" if spacing_xy is not None else "pixel",
              "distance_status": "ok"}
    if not p.any() or not g.any():
        result["distance_status"] = "empty_prediction_or_reference"
        return result
    ps = p & ~ndimage.binary_erosion(p)
    gs = g & ~ndimage.binary_erosion(g)
    sampling = tuple(spacing_xy[::-1]) if spacing_xy is not None else (1., 1.)
    # NumPy 数组轴为 y,x，因此将元数据的 x,y 间距反转后传给距离变换。
    p2g = ndimage.distance_transform_edt(~gs, sampling=sampling)[ps]
    g2p = ndimage.distance_transform_edt(~ps, sampling=sampling)[gs]
    d = np.concatenate([p2g, g2p])
    # 合并预测→参考和参考→预测的边界距离，得到对称距离统计量。
    result.update(assd=float(d.mean()), hd95=float(np.percentile(d, 95)), hd_max=float(d.max()))
    return result

def landmark_errors(pred, truth, spacing_xy=None):
    """计算心尖和左右基底点的欧氏误差，单位随标定而定。"""
    if pred is None or truth is None:
        return None
    spacing = np.array(spacing_xy if spacing_xy is not None else [1., 1.])
    return {key: float(np.linalg.norm((np.asarray(pred[key]) - np.asarray(truth[key])) * spacing))
            for key in ("apex", "base_left", "base_right")}
