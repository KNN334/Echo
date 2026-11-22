import csv
import json

import numpy as np
import pytest


def test_prepare_echonet_materializes_auditable_case(tmp_path, monkeypatch):
    from src.data import echonet

    raw = tmp_path / "raw"
    (raw / "Videos").mkdir(parents=True)
    (raw / "Videos" / "sample.avi").write_bytes(b"video")
    (raw / "VolumeTracings.csv").write_text("FileName,X1,Y1,X2,Y2,Frame\n", encoding="utf-8")
    with (raw / "FileList.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["FileName", "EF", "EDV", "ESV", "FPS", "Split"])
        writer.writeheader()
        writer.writerow({"FileName": "sample.avi", "EF": "60", "EDV": "100", "ESV": "40",
                         "FPS": "50", "Split": "TEST"})

    frames = np.zeros((4, 20, 30), dtype=np.uint8)
    masks = np.zeros_like(frames)
    masks[1, 5:16, 8:22] = 1
    masks[3, 7:14, 10:20] = 1
    monkeypatch.setattr(echonet, "read_video", lambda path: (frames, {"fps": 50.0}))
    monkeypatch.setattr(echonet, "echonet_traces", lambda *args: (masks, np.array([False, True, False, True])))

    result = echonet.prepare_echonet(raw, tmp_path / "processed")
    assert result["cases"] == 1 and result["split_unit"] == "study_proxy"
    meta = __import__("json").loads((tmp_path / "processed" / "echonet_sample.json").read_text(encoding="utf-8"))
    assert meta["phases"] == {"ED": 1, "ES": 3}
    assert meta["reference"]["EF"] == 60.0
    assert meta["audit"]["spacing_xy_mm"] is None
    with np.load(tmp_path / "processed" / "echonet_sample.npz") as archive:
        assert archive["frames"].shape == (4, 112, 112)
        assert archive["original_gt_indices"].tolist() == [1, 3]


@pytest.mark.parametrize("labeled", [np.array([False, False, False, False]),
                                      np.array([False, True, False, False])])
def test_prepare_echonet_keeps_video_with_fewer_than_two_traced_frames(
        tmp_path, monkeypatch, labeled):
    from src.data import echonet

    raw = tmp_path / "raw"
    (raw / "Videos").mkdir(parents=True)
    (raw / "Videos" / "sample.avi").write_bytes(b"video")
    (raw / "VolumeTracings.csv").write_text("FileName,X1,Y1,X2,Y2,Frame\n", encoding="utf-8")
    with (raw / "FileList.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["FileName", "Split"])
        writer.writeheader()
        writer.writerow({"FileName": "sample.avi", "Split": "TEST"})

    frames = np.zeros((4, 20, 30), dtype=np.uint8)
    masks = np.zeros_like(frames)
    masks[1, 5:16, 8:22] = 1
    monkeypatch.setattr(echonet, "read_video", lambda path: (frames, {"fps": 50.0}))
    monkeypatch.setattr(echonet, "echonet_traces", lambda *args: (masks, labeled))

    result = echonet.prepare_echonet(raw, tmp_path / "processed")
    assert result["cases"] == 1 and result["failures"] == 0
    metadata = json.loads((tmp_path / "processed" / "echonet_sample.json").read_text(encoding="utf-8"))
    assert metadata["phases"] == {}
    with np.load(tmp_path / "processed" / "echonet_sample.npz") as archive:
        assert archive["frames"].shape[0] == 4
        assert int(archive["labeled"].sum()) == int(labeled.sum())
        assert len(archive["original_gt_indices"]) == int(labeled.sum())


def test_evidence_status_preserves_missing_calibration_and_independent_co():
    from src.metrics.evidence import case_stage_status

    status = case_stage_status({
        "dataset_kind": "echonet_dynamic",
        "patient_id": "study_x",
        "audit": {"spacing_xy_mm": None, "timestamps_s": [0.0, 0.02]},
        "full_cycle_verified": False,
        "gt_scope": "expert_traced_frames_only",
        "reference": {"EF": 60.0, "EDV": 100.0, "ESV": 40.0, "HR": None, "CO": None},
    })
    assert status["edv_esv"]["status"] == "unavailable"
    assert status["edv_esv"]["reason"] == "missing_spatial_calibration"
    assert status["co"]["status"] == "unavailable"
    assert status["patient_level_split"]["status"] == "unavailable"
    assert status["ef"]["status"] == "available"


def test_function_pairs_keeps_reference_sources_separate_and_aggregates_by_patient():
    from src.visualization.public_baseline import function_pairs

    rows = [
        {"patient_id": "p1", "method": "pixel_proxy", "reference_scope": "dataset_ef", "view": "A4C",
         "EF": 50, "ref_EF": 55},
        {"patient_id": "p1", "method": "pixel_proxy", "reference_scope": "dataset_ef", "view": "A4C",
         "EF": 60, "ref_EF": 55},
        {"patient_id": "p1", "method": "same_geometry", "reference_scope": "expert_contour", "view": "A4C",
         "EF": 70, "ref_EF": 65},
    ]
    pairs = function_pairs(rows)
    assert len(pairs) == 2
    source = next(row for row in pairs if row["method"] == "pixel_proxy")
    assert source["prediction"] == 55 and source["reference"] == 55
    assert source["difference"] == 0


@pytest.mark.parametrize("labeled_indices", [[], [0]])
def test_evaluator_uses_all_video_frames_for_pixel_proxy_ef(tmp_path, monkeypatch, labeled_indices):
    from src.data.transforms import Transform
    from src.models import build as model
    from src.engine.evaluator import evaluate
    from src.utils.io import write_json
    from src.visualization.analysis import read_csv

    root = tmp_path / "processed"
    root.mkdir()
    case_id = "echonet_study1"
    frames = np.zeros((4, 64, 64), dtype=np.uint8)
    labels = np.zeros_like(frames)
    y, x = np.ogrid[:64, :64]
    masks = np.stack([(((x - 32) / radius) ** 2 + ((y - 32) / 22) ** 2 <= 1)
                      for radius in (18, 15, 11, 8)]).astype(np.uint8)
    frames[masks.astype(bool)] = 100
    labels[labeled_indices] = masks[labeled_indices]
    transform = Transform((64, 64), (0, 0, 64, 64), (64, 64))
    np.savez_compressed(root / (case_id + ".npz"), frames=frames, masks=labels,
                        labeled=np.isin(np.arange(len(frames)), labeled_indices),
                        original_gt=labels[labeled_indices], original_gt_indices=labeled_indices)
    metadata = {
        "dataset": "EchoNet-Dynamic", "dataset_kind": "echonet_dynamic",
        "patient_id": "study_1", "patient_identity_scope": "study_proxy", "view": "A4C",
        "split": "test", "phases": {},
        "sequence_type": "sequence_unverified", "full_cycle_verified": False,
        "gt_scope": "expert_traced_frames_only",
        "reference": {"scope": "EchoNet_dataset_labels", "EF": 55.0, "EDV": 120.0,
                      "ESV": 54.0, "HR": None, "CO": None},
        "config": {"EF": 55.0},
        "audit": {"transform": transform.record(None), "spacing_xy_mm": None,
                  "timestamps_s": None, "fps": 50.0, "roi_reviewed": True,
                  "n_frames": 4, "issues": []},
    }
    write_json(root / (case_id + ".json"), metadata)
    case = {"case_id": case_id, "patient_id": "study_1", "view": "A4C", "split": "test"}
    write_json(root / "manifest.json", {"dataset_kind": "echonet_dynamic", "cases": [case], "failures": []})
    test_manifest = root / "test.json"
    write_json(test_manifest, {"schema_version": 1, "split": "test", "dataset_root": ".",
                               "cases": [case], "patients": ["study_1"]})
    weights = tmp_path / "checkpoint.pt"
    weights.write_bytes(b"stub")
    monkeypatch.setattr(model, "load_checkpoint", lambda *args: (None, {"mean": [0, 0, 0], "std": [1, 1, 1]}))
    monkeypatch.setattr(model, "predict", lambda *args: masks.astype(np.float32) * .98 + .01)

    output = tmp_path / "results"
    summary = evaluate(test_manifest, weights, output, device="cpu", adapter="prepared")
    rows = read_csv(output / "function.csv")
    inferred = next(row for row in rows if row["method"] == "single_plane_pixel_proxy_auto_extrema")
    assert summary["frames"] == 4 and summary["labeled_frames"] == len(labeled_indices)
    assert inferred["EF"] not in ("", None)
    assert inferred["EDV"] == "" and inferred["ESV"] == "" and inferred["SV"] == ""
    assert inferred["ref_EF"] == "55.0"
    assert summary["evidence_status"]["physical_geometry"]["status"] == "unavailable"
    assert summary["evidence_status"]["ef"]["status"] == "available"
    with (output / "frames.csv").open(encoding="utf-8-sig", newline="") as stream:
        frame_rows = list(csv.DictReader(stream))
    assert all(row["analysis_volume_pixel3_proxy"] for row in frame_rows)


def test_supervised_dataset_uses_only_traced_frames():
    from src.data.base import AnnotatedFrameDataset

    frames = np.arange(8, dtype=np.uint8).reshape(4, 2, 1)
    masks = np.zeros_like(frames)
    labeled = np.array([False, True, False, True])

    class Adapter:
        cases = [{"case_id": "study"}]

        def load_case(self, case):
            return {"frames": frames, "masks": masks, "labeled": labeled}, {}

    dataset = AnnotatedFrameDataset(Adapter(), description="test annotated-frame selection")
    assert len(dataset) == 2
    assert np.array_equal(dataset.frames, frames[labeled])
