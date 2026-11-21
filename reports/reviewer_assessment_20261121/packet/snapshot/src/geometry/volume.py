"""单平面面积长轴法和双平面椭圆盘法；缺少标定不输出 mL。"""
import numpy as np


def single_plane_volume(area, length, calibrated=True):
    """面积长轴近似；标定时输入 mm²/mm 输出 mL，否则输出 pixel³。"""
    if not np.isfinite(area) or not np.isfinite(length) or area <= 0 or length <= 0:
        return None
    value = 8 * area**2 / (3 * np.pi * length)
    return float(value / 1000 if calibrated else value)


def biplane_volume(a, b):
    """用双平面椭圆盘法合并两个切面的直径估算容积。"""
    if not a.get("valid") or not b.get("valid") or a.get("diameters_mm") is None or b.get("diameters_mm") is None:
        return None
    d1, d2 = np.array(a["diameters_mm"]), np.array(b["diameters_mm"])
    if len(d1) != len(d2):
        raise ValueError("biplane disk counts differ")
    # 两切面在归一化长轴位置上配对盘径，盘厚按较短长轴计算；mm³ / 1000 = mL。
    length = min(a["long_axis_mm"], b["long_axis_mm"])
    return float(np.sum(np.pi * d1 * d2 / 4) * length / len(d1) / 1000)
