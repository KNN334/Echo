from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import Settings
from .core import ERROR_UNITS, UNITS, ServiceError
from .schemas import Contours, PatientDetail, PatientRow, ReportSummary, Study, StudyInfo, TrainingEpoch, VolumeCurve
from .services.patients import dra_cases, legacy_patients
from .services.reports import dra_results, legacy_results, load_file, training_history


@dataclass
class StudyReports:
    info: StudyInfo
    summary: ReportSummary | None
    history: list[TrainingEpoch] | None


class ReportRepository(Protocol):
    status: dict[str, str]

    def reports(self, study: Study) -> StudyReports: ...
    def patients(self, study: Study) -> dict[str, PatientRow]: ...
    def patient(self, study: Study, patient_id: str) -> PatientDetail: ...
    def overlay(self, patient_id: str) -> Path: ...


class InMemoryReports:
    def __init__(self, settings: Settings):
        self.status: dict[str, str] = {}
        self.assets = settings.camus_assets_dir
        legacy_dir = settings.reports_dir
        legacy_summary = load_file("summary.json", lambda: legacy_results(legacy_dir / "summary.json"), self.status)
        legacy_history = load_file("training_history.csv", lambda: training_history(legacy_dir / "training_history.csv", dra=False), self.status)
        self.legacy_rows = load_file("patient_features.csv", lambda: legacy_patients(legacy_dir / "patient_features.csv"), self.status)
        dra_summary = load_file("lvseg_ablation/results.json", lambda: dra_results(settings.dra_results_file), self.status)
        dra_history = load_file("dra-training-loss.json", lambda: training_history(self.assets / "dra-training-loss.json", dra=True), self.status)
        self.dra_rows = load_file("camus-cases.json", lambda: dra_cases(self.assets), self.status)
        self.studies: dict[Study, StudyReports] = {
            "legacy": StudyReports(StudyInfo(study="legacy", model="DeepLabV3-ResNet50（EchoNet 适配）", split="test",
                                              scope="CAMUS 测试集 · 专家标注相位"), legacy_summary, legacy_history),
            "dra": StudyReports(StudyInfo(study="dra", model="DRA-UNet", split="val",
                                           scope="CAMUS 验证集 · DTE 三种子均值"), dra_summary, dra_history),
        }

    def reports(self, study: Study) -> StudyReports:
        return self.studies[study]

    def patients(self, study: Study) -> dict[str, PatientRow]:
        if study == "legacy" and self.legacy_rows is not None:
            return self.legacy_rows
        if study == "dra" and self.dra_rows is not None:
            return {key: case[0] for key, case in self.dra_rows.items()}
        raise ServiceError(503, "该实验的病例报表暂不可用")

    def patient(self, study: Study, patient_id: str) -> PatientDetail:
        rows = self.patients(study)
        if patient_id not in rows:
            raise ServiceError(404, "该数据口径下找不到此公开病例")
        patient = rows[patient_id]
        contours = Contours(reason="历史报表未发布逐病例轮廓点列或叠加影像")
        curve = VolumeCurve(reason="历史报表仅含标注相位测量，未发布逐帧容积序列")
        if study == "dra" and self.dra_rows is not None:
            _, contours, curve = self.dra_rows[patient_id]
        differences = {}
        for key in UNITS:
            predicted, reference = getattr(patient, key), getattr(patient, f"ref_{key}")
            differences[key] = predicted - reference if predicted is not None and reference is not None else None
        return PatientDetail(**patient_info(self, study), patient=patient, error_units=ERROR_UNITS, contours=contours,
                             volume_curve=curve, signed_error=differences,
                             absolute_error={key: abs(value) if value is not None else None for key, value in differences.items()})

    def overlay(self, patient_id: str) -> Path:
        case = (self.dra_rows or {}).get(patient_id)
        if case is None or case[1].atlas_url is None:
            raise ServiceError(404, "该公开病例未发布叠加影像")
        path = self.assets / f"{patient_id}_2CH.webp"
        if not path.is_file():
            raise ServiceError(404, "该公开病例的叠加影像暂不可用")
        return path


def patient_info(repository: ReportRepository, study: Study) -> dict:
    info = repository.reports(study).info.model_dump()
    if study == "dra":
        info.update(split="test", scope="CAMUS 固定测试集 · A2C 公开回放子集 · 种子 2026")
    return info
