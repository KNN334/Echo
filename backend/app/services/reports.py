import csv
import json
import logging
from pathlib import Path
from typing import Callable

from ..core import ERROR_UNITS, MISSING_CO, MISSING_LANDMARKS, SAME_GEOMETRY
from ..schemas import FunctionMetric, Metric, ReportSummary, TrainingEpoch

logger = logging.getLogger(__name__)
NO_RESULT = "该实验报表未提供此项"
FUNCTION_SCOPE = {
    "legacy": "A4C/A2C 双平面 20 圆盘 · " + SAME_GEOMETRY,
    "dra": "ED/ES 标注帧单平面 Simpson 圆盘 · " + SAME_GEOMETRY,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path, required: set[str]):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("missing columns")
        return list(reader)


def load_file(name: str, read: Callable, status: dict[str, str]):
    try:
        result = read()
    except (OSError, ValueError, KeyError, TypeError, StopIteration, AttributeError, csv.Error) as exc:
        status[name] = "missing" if isinstance(exc, FileNotFoundError) else "invalid"
        logger.warning("Report %s %s (%s)", name, status[name], type(exc).__name__)
        return None
    status[name] = "loaded"
    return result


def metric(name, value, unit, scope, reason=NO_RESULT):
    return Metric(metric=name, value=value, unit=unit, scope=scope, reason=reason if value is None else None)


def legacy_results(path: Path):
    raw = read_json(path)
    segmentation = [
        metric("Dice", raw["dice_patient_mean"], "1", "患者均值"),
        metric("ASSD", raw["assd_mm"], "mm", "对称平均边界距离"),
        metric("HD95", raw["hd95_mm"], "mm", "双向边界距离的第 95 百分位"),
        metric("轮廓派生关键点代理误差", raw["contour_derived_keypoint_error"], raw["keypoint_distance_unit"],
               "对预测与专家轮廓使用相同几何算法派生的代理"),
        metric("人工解剖关键点误差", raw["manual_keypoint_error"], raw["keypoint_distance_unit"],
               "独立人工解剖关键点评价", MISSING_LANDMARKS),
    ]
    geometry = raw["function"]["20_disks_shorter_axis"]
    function = []
    for key in ("EDV", "ESV", "SV", "EF", "CO"):
        group = geometry[key]
        function.append(FunctionMetric(metric=key, unit=ERROR_UNITS[key], mae=group["mae"],
                                       bias=group.get("bias"), mae_ci95=group.get("mae_ci95"),
                                       limits_of_agreement=group.get("patient_mean_limits_of_agreement"),
                                       n_patients=group["n_patients"], coverage=group["coverage_of_attempted_patients"],
                                       reason=(MISSING_CO if key == "CO" else NO_RESULT) if group["mae"] is None else None))
    return ReportSummary(patients=raw["patients"], labeled_frames=raw["labeled_frames"],
                         segmentation=segmentation, function_mae=function)


def dra_results(path: Path):
    raw = read_json(path)
    model = next(row for row in raw["models"] if row["variant"] == "DTE")
    validation = next(run["validation"] for run in raw["runs"] if run["variant"] == "DTE")
    segmentation = [
        metric("Dice", model["dice"], "1", "患者均值，跨种子等权平均"),
        metric("ASSD", model["asd"], "mm", "对称平均边界距离"),
        metric("HD95", model["hd95"], "mm", "双向边界距离的第 95 百分位"),
        metric("轮廓派生关键点代理误差", None, "mm", "轮廓派生的几何代理"),
        metric("人工解剖关键点误差", None, "mm", "独立人工解剖关键点评价", MISSING_LANDMARKS),
    ]
    function = [FunctionMetric(metric="标注帧容积估算", unit="mL", mae=model["volume_absolute_error_ml"],
                               reason="三种子标注帧容积 MAE 均值，合并一致性统计未发布")]
    function.extend(FunctionMetric(metric=key, unit=ERROR_UNITS[key], reason=NO_RESULT) for key in ("EDV", "ESV", "SV", "EF"))
    function.append(FunctionMetric(metric="CO", unit="L/min", reason=MISSING_CO))
    return ReportSummary(patients=validation["patients"], labeled_frames=validation["labeled_frames"],
                         segmentation=segmentation, function_mae=function)


def training_history(path: Path, *, dra: bool):
    if dra:
        rows = read_json(path)
        history = [TrainingEpoch(epoch=row["epoch"], train_loss=row["train"], val_loss=row["validation"]) for row in rows]
    else:
        rows = read_csv(path, {"epoch", "train_bce", "val_bce"})
        history = [TrainingEpoch(epoch=row["epoch"], train_bce=row["train_bce"], val_bce=row["val_bce"]) for row in rows]
    if not history or len({row.epoch for row in history}) != len(history):
        raise ValueError("empty or duplicate training epochs")
    return sorted(history, key=lambda row: row.epoch)
