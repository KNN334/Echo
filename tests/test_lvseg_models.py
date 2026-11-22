import csv
import json

import numpy as np
import torch

from lvseg.data.dataset import LabeledFrames
from lvseg.evaluate import evaluate_model
from lvseg.models import MODEL_NAMES, build_model
from lvseg.visualization.comparison import plot_mask_comparison
from lvseg.data import prepare_echonet as echonet_preparation


def test_each_requested_baseline_returns_single_channel_segmentation_logits():
    image = torch.zeros((1, 1, 64, 96))
    for name in MODEL_NAMES:
        model = build_model(name, base_channels=8).eval()
        with torch.inference_mode():
            prediction = model(image)
        assert prediction.shape == (1, 1, 64, 96), name


def test_training_dataset_contains_only_frames_with_expert_masks(tmp_path):
    frames = np.arange(4 * 32 * 32, dtype=np.uint8).reshape(4, 32, 32)
    masks = np.zeros_like(frames)
    masks[1, 8:20, 8:20] = 1
    masks[3, 6:18, 6:18] = 1
    np.savez_compressed(tmp_path / "case.npz", frames=frames, masks=masks,
                        labeled=np.array([False, True, False, True]))
    (tmp_path / "train.json").write_text(
        '{"split":"train","dataset_root":".","cases":[{"case_id":"case",'
        '"patient_id":"p1","split":"train"}]}', encoding="utf-8")
    dataset = LabeledFrames(tmp_path / "train.json")
    assert len(dataset) == 2
    assert np.array_equal(dataset.frames, frames[[1, 3]])
    assert np.array_equal(dataset.masks, masks[[1, 3]])


def test_final_inference_processes_unlabeled_frames_and_compares_labeled_ones(tmp_path):
    case_id = "p003_4CH"
    frames = np.zeros((5, 64, 64), dtype=np.uint8)
    masks = np.zeros_like(frames)
    labels = np.zeros_like(frames)
    for index, width in enumerate((24, 21, 18, 15, 12)):
        masks[index, 12:52, 32 - width // 2:32 + width // 2] = 1
    labels[[0, 4]] = masks[[0, 4]]
    labeled = np.array([True, False, False, False, True])
    np.savez_compressed(tmp_path / f"{case_id}.npz", frames=frames, masks=masks,
                        labeled=labeled, original_shape=np.array([64, 64]),
                        original_gt=labels[labeled], original_gt_indices=[0, 4])
    metadata = {"patient_id": "p003", "view": "4CH", "original_hw": [64, 64],
                "spacing_xy_mm": [1.0, 1.0], "fps": 50.0,
                "timestamps_s": (np.arange(5) / 50).tolist(),
                "sequence_type": "half_sequence", "complete_cycle_verified": False,
                "phases": {"ED": 0, "ES": 4}}
    (tmp_path / f"{case_id}.json").write_text(json.dumps(metadata), encoding="utf-8")
    case = {"case_id": case_id, "patient_id": "p003", "view": "4CH", "split": "test"}
    manifest = tmp_path / "test.json"
    manifest.write_text(json.dumps({"split": "test", "dataset_root": ".", "cases": [case]}),
                        encoding="utf-8")
    model = build_model("UNet-mini", base_channels=8)
    checkpoint = {"model": "UNet-mini", "model_config": {"in_channels": 1, "base_channels": 8},
                  "state_dict": model.state_dict(), "normalization": {"mean": 0, "std": 1},
                  "run": {"train_patients": ["p001"], "val_patients": ["p002"]}}
    checkpoint_path = tmp_path / "best.pt"
    torch.save(checkpoint, checkpoint_path)

    summary = evaluate_model(checkpoint_path, manifest, tmp_path / "result", device="cpu")
    assert summary["inference_frames"] == 5
    assert summary["labeled_frames"] == 2
    assert summary["unlabeled_inference_frames"] == 3
    assert summary["events_with_hr_estimate"] == 0
    assert summary["events_with_calibrated_co"] == 0
    result_rows = (tmp_path / "result" / "all_frame_volumes.csv").read_text(encoding="utf-8-sig")
    assert result_rows.count("p003_4CH") == 5
    assert (tmp_path / "result" / "phase_events.csv").is_file()
    figure = plot_mask_comparison(manifest, tmp_path / "result",
                                  tmp_path / "result" / "mask_comparison_example.png")
    assert figure.is_file()


def test_echonet_preparation_keeps_full_video_and_unavailable_calibration(monkeypatch, tmp_path):
    raw = tmp_path / "raw"
    videos = raw / "Videos"
    videos.mkdir(parents=True)
    (videos / "study.avi").write_bytes(b"test fixture")
    with (raw / "FileList.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["FileName", "FPS", "Split", "PatientID"])
        writer.writeheader()
        writer.writerow({"FileName": "study.avi", "FPS": 20, "Split": "test",
                         "PatientID": "patient-a"})
    with (raw / "VolumeTracings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["FileName", "Frame", "X1", "Y1", "X2", "Y2"])
        writer.writeheader()
        for frame in (0, 3):
            for row in ((10, 10, 20, 10), (20, 10, 20, 20),
                        (20, 20, 10, 20), (10, 20, 10, 10)):
                writer.writerow(dict(zip(("FileName", "Frame", "X1", "Y1", "X2", "Y2"),
                                         ("study.avi", frame, *row))))
    monkeypatch.setattr(echonet_preparation, "_read_video",
                        lambda _: (np.zeros((4, 32, 32), dtype=np.uint8), 20.0))

    result = echonet_preparation.prepare_echonet(raw, tmp_path / "prepared",
                                                  image_hw=(32, 32))
    metadata = json.loads((tmp_path / "prepared" / "echonet_study.json").read_text(
        encoding="utf-8"))
    assert result["complete"]
    assert metadata["sequence_type"] == "full_video"
    assert metadata["complete_cycle_verified"]
    assert metadata["spacing_xy_mm"] is None
    assert metadata["labeled_frames"] == [0, 3]
