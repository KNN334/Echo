"""EDV/ESV 转换为 SV、EF；CO 需要可靠 HR。"""
import numpy as np


def functional(edv, esv, hr=None):
    """由 EDV/ESV 计算 SV、EF；仅有可靠心率时计算 CO。"""
    result = {"EDV": edv, "ESV": esv, "SV": None, "EF": None, "HR": hr, "CO": None, "issues": []}
    if edv is None or esv is None or not np.isfinite(edv) or not np.isfinite(esv) or not 0 <= esv < edv:
        result["issues"].append("invalid_or_missing_EDV_ESV")
        return result
    result.update(SV=float(edv - esv), EF=float(100 * (edv - esv) / edv))
    # SV 单位 mL，EF 单位 %；SV×HR / 1000 将 mL/min 转为 L/min。
    if hr is not None and np.isfinite(hr) and hr > 0:
        result["CO"] = float(result["SV"] * hr / 1000)
    else:
        result["issues"].append("missing_full_cycle_or_reference_HR_no_CO")
    return result
