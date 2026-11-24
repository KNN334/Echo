from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, UUID4

from .core import DISCLAIMER, UNITS

Study = Literal["legacy", "dra"]
PatientID = Annotated[str, Field(pattern=r"^patient[0-9]{4}$")]


class Provenance(BaseModel):
    source: Literal["report", "uploaded"] = "report"
    disclaimer: str = DISCLAIMER


class StudyInfo(Provenance):
    study: Study
    model: str
    scope: str
    split: Literal["val", "test"]
    warnings: list[str] = Field(default_factory=list)


class Metric(BaseModel):
    metric: str
    value: FiniteFloat | None
    unit: str
    scope: str
    reason: str | None = None


class FunctionMetric(BaseModel):
    metric: str
    unit: str
    mae: FiniteFloat | None = None
    bias: FiniteFloat | None = None
    mae_ci95: tuple[FiniteFloat, FiniteFloat] | None = None
    limits_of_agreement: tuple[FiniteFloat, FiniteFloat] | None = None
    n_patients: int | None = None
    coverage: FiniteFloat | None = None
    reason: str | None = None


class SegmentationResult(StudyInfo):
    metrics: list[Metric]


class FunctionResult(StudyInfo):
    reference_scope: str
    metrics: list[FunctionMetric]


class ReportSummary(BaseModel):
    patients: int | None = Field(default=None, ge=0)
    labeled_frames: int | None = Field(default=None, ge=0)
    segmentation: list[Metric] = Field(default_factory=list)
    function_mae: list[FunctionMetric] = Field(default_factory=list)


class OverviewResult(StudyInfo, ReportSummary):
    workflow: list[str]


class TrainingEpoch(BaseModel):
    epoch: int = Field(ge=1)
    train_bce: FiniteFloat | None = None
    val_bce: FiniteFloat | None = None
    train_loss: FiniteFloat | None = None
    val_loss: FiniteFloat | None = None


class TrainingResult(StudyInfo):
    loss: str
    seed: int | None = None
    epochs: list[TrainingEpoch]


class PatientValues(BaseModel):
    EDV: FiniteFloat | None = None
    ESV: FiniteFloat | None = None
    SV: FiniteFloat | None = None
    EF: FiniteFloat | None = None
    HR: FiniteFloat | None = None
    CO: FiniteFloat | None = None


class PatientRow(PatientValues):
    patient_id: PatientID
    ref_EDV: FiniteFloat | None = None
    ref_ESV: FiniteFloat | None = None
    ref_SV: FiniteFloat | None = None
    ref_EF: FiniteFloat | None = None
    ref_HR: FiniteFloat | None = None
    ref_CO: FiniteFloat | None = None
    issues: list[str]
    reference_scope: str
    phase_selection: str
    missing_reasons: dict[str, str]


class PatientQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study: Study = "legacy"
    search: str = Field(default="", max_length=64)
    sort_by: Literal["patient_id", "EDV", "ESV", "SV", "EF", "HR", "CO", "ref_EDV", "ref_ESV", "ref_EF"] = "patient_id"
    order: Literal["asc", "desc"] = "asc"
    issue_filter: Literal["all", "has_issue", "missing_co", "review", "routine"] = "all"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=8, ge=1, le=100)


class PatientPage(StudyInfo):
    units: dict[str, str] = UNITS
    items: list[PatientRow]
    total: int
    page: int
    page_size: int
    page_count: int


Point = tuple[FiniteFloat, FiniteFloat]


class ContourFrame(BaseModel):
    frame: int = Field(ge=0)
    prediction: list[Point] | None = None
    reference: list[Point] | None = None


class Atlas(BaseModel):
    columns: int = Field(gt=0)
    rows: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class Contours(Provenance):
    source_file: str | None = None
    view: Literal["A2C"] | None = None
    atlas_url: str | None = None
    atlas: Atlas | None = None
    frames: dict[Literal["ED", "ES"], ContourFrame] = Field(default_factory=dict)
    reason: str


class VolumeFrame(BaseModel):
    index: int = Field(ge=0)
    time_s: FiniteFloat = Field(ge=0)
    volume_ml: FiniteFloat | None


class VolumeEvent(BaseModel):
    phase: Literal["ED", "ES"]
    frame: int = Field(ge=0)


class VolumeCurve(Provenance):
    source_file: str | None = None
    raw: list[VolumeFrame] | None = None
    smoothed: list[VolumeFrame] | None = None
    events: list[VolumeEvent] = Field(default_factory=list)
    time_unit: Literal["s"] = "s"
    volume_unit: Literal["mL"] = "mL"
    reason: str


class PatientDetail(StudyInfo):
    patient: PatientRow
    units: dict[str, str] = UNITS
    error_units: dict[str, str]
    signed_error: PatientValues
    absolute_error: PatientValues
    contours: Contours
    volume_curve: VolumeCurve


class Health(Provenance):
    status: Literal["ok", "degraded"]
    reports: dict[str, str]
    uploads_enabled: bool
    upload_max_bytes: int
    upload_formats: list[str]
    inference_enabled: bool = False
    inference_formats: list[str] = Field(default_factory=list)
    inference_max_frames: int


class UploadResult(Provenance):
    source: Literal["uploaded"] = "uploaded"
    case_id: UUID4
    saved: Literal[True] = True
    validation: Literal["basic_format_and_size_passed"] = "basic_format_and_size_passed"
    size_bytes: int
    inference_status: Literal["disabled", "ready"] = "disabled"


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID4 | None = None
    view: Literal["A2C", "A4C"] | None = None
    phase_selection: Literal["auto"] = "auto"


class InferenceResult(Provenance):
    source: Literal["uploaded"] = "uploaded"
    case_id: UUID4
    model: Literal["DRA-UNet"] = "DRA-UNet"
    seed: Literal[2026] = 2026
    view: Literal["A2C", "A4C"] | None = None
    frames: int = Field(gt=0)
    nonempty_masks: int = Field(ge=0)
    playback_fps: FiniteFloat | None = None
    atlas: Atlas
    sheet_urls: list[str]
    quality_flags: list[str]
    elapsed_s: FiniteFloat


class InferenceStatus(Provenance):
    source: Literal["uploaded"] = "uploaded"
    case_id: UUID4
    status: Literal["disabled", "ready", "queued", "processing", "done", "failed"]
    detail: str | None = None
    completed_frames: int | None = None
    total_frames: int | None = None
