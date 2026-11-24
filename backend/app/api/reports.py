from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from ..repositories import ReportRepository, StudyReports, patient_info
from ..schemas import FunctionResult, OverviewResult, PatientDetail, PatientID, PatientPage, PatientQuery, ReportSummary, SegmentationResult, Study, TrainingResult
from ..services.patients import select_patients
from ..services.reports import FUNCTION_SCOPE

router = APIRouter(prefix="/api", tags=["研究报表"])
WORKFLOW = ["患者级固定划分与预处理", "左心室分割", "空间标定与 Simpson 圆盘估算", "心功能计算与质量检查", "研究评价与可视化"]


def repository(request: Request) -> ReportRepository:
    return request.app.state.reports


Repo = Annotated[ReportRepository, Depends(repository)]


def report_info(study: StudyReports, available: bool, warning: str) -> dict:
    return {**study.info.model_dump(), "warnings": [] if available else [warning]}


@router.get("/overview", response_model=OverviewResult)
def overview(repo: Repo, study: Study = "legacy"):
    reports = repo.reports(study)
    summary = reports.summary or ReportSummary()
    return {**report_info(reports, reports.summary is not None, "概览报表暂不可用"),
            **summary.model_dump(), "workflow": WORKFLOW}


@router.get("/results/segmentation", response_model=SegmentationResult)
def segmentation(repo: Repo, study: Study = "legacy"):
    reports = repo.reports(study)
    return {**report_info(reports, reports.summary is not None, "分割报表暂不可用"),
            "metrics": reports.summary.segmentation if reports.summary else []}


@router.get("/results/function", response_model=FunctionResult)
def function(repo: Repo, study: Study = "legacy"):
    reports = repo.reports(study)
    return {**report_info(reports, reports.summary is not None, "心功能报表暂不可用"),
            "reference_scope": FUNCTION_SCOPE[study], "metrics": reports.summary.function_mae if reports.summary else []}


@router.get("/results/training-history", response_model=TrainingResult)
def training_history(repo: Repo, study: Study = "legacy"):
    reports = repo.reports(study)
    return {**report_info(reports, reports.history is not None, "训练日志暂不可用"),
            "loss": "BCE + Dice" if study == "dra" else "mean BCE",
            "seed": 2026 if study == "dra" else None, "epochs": reports.history or []}


@router.get("/patients", response_model=PatientPage)
def patients(repo: Repo, query: Annotated[PatientQuery, Query()]):
    return {**patient_info(repo, query.study), **select_patients(repo.patients(query.study).values(), query)}


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def detail(patient_id: PatientID, repo: Repo, study: Study = "legacy"):
    return repo.patient(study, patient_id)


@router.get("/patients/{patient_id}/overlay", response_class=FileResponse)
def overlay(patient_id: PatientID, repo: Repo):
    return FileResponse(repo.overlay(patient_id), media_type="image/webp")
