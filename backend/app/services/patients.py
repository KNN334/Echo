from pathlib import Path

from ..core import MISSING_CO, MISSING_CYCLE, SAME_GEOMETRY, UNITS, ServiceError
from ..schemas import Atlas, ContourFrame, Contours, PatientQuery, PatientRow, VolumeCurve, VolumeEvent, VolumeFrame
from .reports import FUNCTION_SCOPE, read_csv, read_json

ROUTINE_ISSUE = "incomplete_cycle"
VALUE_KEYS = (*UNITS, *(f"ref_{key}" for key in UNITS))


def missing_reasons(values: dict) -> dict[str, str]:
    return {key: reason for key, reason in {
        **dict.fromkeys(UNITS, "缺少可用测量"),
        **{f"ref_{key}": "缺少配对参考值" for key in UNITS},
        "HR": MISSING_CYCLE, "CO": f"{MISSING_CYCLE}，无法计算 CO",
        "ref_HR": "缺少独立参考心率", "ref_CO": MISSING_CO,
    }.items() if values.get(key) is None}


def legacy_patients(path: Path):
    rows = read_csv(path, {
        "patient_id", "issues", "reference_scope", "phase_selection", *(key for key in VALUE_KEYS if key != "ref_HR"),
    })
    patients = {}
    for row in rows:
        values = {key: row.get(key) or None for key in VALUE_KEYS}
        issues = [issue for issue in row["issues"].split(";") if issue]
        patients[row["patient_id"]] = PatientRow(
            patient_id=row["patient_id"], **values, missing_reasons=missing_reasons(values),
            issues=[ROUTINE_ISSUE if code == "missing_full_cycle_or_reference_HR_no_CO" else code for code in issues],
            reference_scope=FUNCTION_SCOPE["legacy"] if row["reference_scope"] == "same_geometry_from_expert_ED_ES_contours" else row["reference_scope"],
            phase_selection="专家 ED/ES 标注帧，用于隔离分割误差" if row["phase_selection"] == "reference_ED_ES_for_segmentation_error_isolation" else row["phase_selection"],
        )
    if not patients or len(patients) != len(rows):
        raise ValueError("empty or duplicate patients")
    return patients


def volumes(edv, esv):
    sv = edv - esv if edv is not None and esv is not None and edv > esv else None
    return {"EDV": edv, "ESV": esv, "SV": sv, "EF": sv / edv * 100 if sv is not None and edv > 0 else None}


def dra_cases(assets: Path):
    rows = read_json(assets / "camus-cases.json")
    cases = {}
    for row in rows:
        case_id = row["patient_id"]
        raw = [VolumeFrame.model_validate(frame) for frame in row["frames"]]
        if not raw or any(right.time_s <= left.time_s for left, right in zip(raw, raw[1:])):
            raise ValueError("empty or unordered volume curve")
        indices = {frame.index for frame in raw}
        event = next(iter(row["events"]), None)
        markers = [VolumeEvent(phase=phase, frame=item[key]) for item in row["events"]
                   for phase, key in (("ED", "ed_frame"), ("ES", "es_frame"))]
        prediction = volumes(event["EDV"], event["ESV"]) if event else {}
        references = volumes(row["expert_volumes_ml"].get("ED"), row["expert_volumes_ml"].get("ES"))
        values = {**prediction, **{f"ref_{key}": value for key, value in references.items()}}
        issues = [ROUTINE_ISSUE] if not row["complete_cycle_verified"] else []
        if not event:
            issues.append("missing_phase")
        if references["SV"] is None:
            issues.append("missing_reference")
        if any(frame.volume_ml is None for frame in raw):
            issues.append("invalid_geometry")
        patient = PatientRow(patient_id=case_id, **values, issues=issues, missing_reasons=missing_reasons(values),
                             reference_scope="单平面 Simpson · " + SAME_GEOMETRY,
                             phase_selection=f"预测 ED 峰在帧 {event['ed_frame']}，ES 谷在帧 {event['es_frame']}" if event else "缺少有效预测峰谷")
        phases = {phase: ContourFrame(frame=index) for phase, index in row["expert_phases"].items()}
        if [frame.index for frame in raw] != list(range(len(raw))) or any(marker.frame not in indices for marker in markers) or any(
            frame.frame not in indices for frame in phases.values()
        ):
            raise ValueError("invalid frame index")
        atlas_file = f"{patient.patient_id}_2CH.webp"
        atlas = Atlas.model_validate(row["atlas"])
        has_atlas = row["atlas_file"] == atlas_file and (assets / atlas_file).is_file()
        contours = Contours(view=row["view"], atlas=atlas if has_atlas else None, frames=phases, source_file=atlas_file if has_atlas else None,
                            atlas_url=f"/api/patients/{patient.patient_id}/overlay" if has_atlas else None,
                            reason="发布资产提供专家 ED/ES 的叠加影像，缺少独立轮廓点列" if has_atlas else "缺少叠加影像和轮廓点列")
        curve = VolumeCurve(raw=raw, events=markers, source_file="camus-cases.json", reason="发布资产提供原始逐帧容积，未提供平滑序列")
        cases[patient.patient_id] = (patient, contours, curve)
    if not cases or len(cases) != len(rows):
        raise ValueError("empty or duplicate patients")
    return cases


def select_patients(patients, query: PatientQuery):
    search = query.search.strip().casefold()
    rows = []
    for patient in patients:
        if search not in patient.patient_id.casefold():
            continue
        review = any(issue != ROUTINE_ISSUE for issue in patient.issues)
        if not {
            "all": True, "has_issue": bool(patient.issues), "missing_co": patient.CO is None,
            "review": review, "routine": not review,
        }[query.issue_filter]:
            continue
        rows.append(patient)
    rows.sort(key=lambda patient: patient.patient_id)
    present = [row for row in rows if getattr(row, query.sort_by) is not None]
    present.sort(key=lambda row: getattr(row, query.sort_by), reverse=query.order == "desc")
    ordered = present + [row for row in rows if getattr(row, query.sort_by) is None]
    count = max(1, (len(rows) + query.page_size - 1) // query.page_size)
    if query.page > count:
        raise ServiceError(422, "页码超过当前查询结果的范围")
    offset = (query.page - 1) * query.page_size
    return {"items": ordered[offset:offset + query.page_size], "total": len(rows), "page": query.page,
            "page_size": query.page_size, "page_count": count}
