import json

import numpy as np
import torch

import lvseg.ablation_experiment as experiment
from lvseg.data.temporal import LabeledClips, causal_clip
from lvseg.evaluate import _predict
from lvseg.losses import segmentation_boundary_loss
from lvseg.models import build_model


def test_disabled_modules_reproduce_attention_unet_exactly():
    torch.manual_seed(15)
    baseline = build_model("Attention-UNet", base_channels=8).eval()
    torch.manual_seed(15)
    ablation = build_model("LV-Ablation", base_channels=8).eval()
    image = torch.randn(2, 1, 32, 48)
    assert set(baseline.state_dict()) == set(ablation.state_dict())
    with torch.inference_mode():
        assert torch.equal(baseline(image), ablation(image))


def test_all_module_paths_backpropagate_including_the_auxiliary_edge_head():
    model = build_model("LV-Ablation", base_channels=8, ablation={
        "se": True, "dilated_residual": True, "temporal": True, "edge": True})
    image = torch.randn(2, 3, 1, 32, 48)
    target = torch.zeros(2, 1, 32, 48)
    target[:, :, 6:25, 10:30] = 1
    logits, edges = model.forward_with_aux(image, torch.tensor([1, 3]))
    loss, parts = segmentation_boundary_loss(logits, target, edges)
    loss.backward()
    for name in ("gates.0.weights.1.weight", "encoders.0.body.3.weight",
                 "fusion.gates.weight", "edge_head.0.weight", "head.weight"):
        gradient = dict(model.named_parameters())[name].grad
        assert gradient is not None and torch.isfinite(gradient).all() and gradient.abs().sum() > 0
    assert set(parts) == {"segmentation", "edge", "sobel"}


def test_temporal_padding_is_ignored_and_inference_cannot_read_future_frames():
    model = build_model("LV-Ablation", base_channels=8, ablation={"temporal": True}).eval()
    image = torch.randn(1, 3, 1, 32, 48)
    alternate = image.clone()
    alternate[:, :2] = 100
    with torch.inference_mode():
        assert torch.equal(model(image, torch.tensor([1])), model(alternate, torch.tensor([1])))
    frames = np.random.default_rng(3).integers(0, 255, (5, 32, 48), dtype=np.uint8)
    original = _predict(model, frames, 0.2, 0.3, "cpu", batch_size=2)
    frames[3:] = 0
    changed = _predict(model, frames, 0.2, 0.3, "cpu", batch_size=1)
    assert np.array_equal(original[:3], changed[:3])


def test_clips_use_real_history_and_only_labeled_targets(tmp_path):
    frames = np.stack([np.full((16, 16), index * 20, dtype=np.uint8) for index in range(5)])
    masks = np.zeros_like(frames)
    masks[0, 3:10, 3:10] = 1
    masks[4, 4:9, 4:9] = 1
    np.savez_compressed(tmp_path / "case.npz", frames=frames, masks=masks,
                        labeled=[True, False, False, False, True])
    (tmp_path / "case.json").write_text(json.dumps({"timestamps_s": [0, .1, .2, .3, .4]}))
    (tmp_path / "train.json").write_text(json.dumps({"split": "train", "dataset_root": ".",
        "cases": [{"case_id": "case", "patient_id": "p1", "split": "train"}]}))
    dataset = LabeledClips(tmp_path / "train.json")
    assert len(dataset) == 2
    assert [sample[1] for sample in dataset.samples] == [0, 4]
    first, _, first_length = dataset[0]
    last, target, last_length = dataset[1]
    assert (first_length, last_length) == (1, 3)
    np.testing.assert_allclose(last[-1, 0].numpy(), (frames[4] / 255 - dataset.mean) / dataset.std,
                               rtol=1e-5)
    clip, length = causal_clip(frames, 4, 3)
    assert length == 3 and np.array_equal(clip, frames[2:5])
    assert target.sum() == 25


def test_training_resume_continues_from_the_last_completed_epoch(tmp_path, monkeypatch):
    class TinyLabeledClips(torch.utils.data.Dataset):
        patient_ids = ["train-patient"]
        mean, std = 0.2, 0.3

        def __len__(self):
            return 2

        def __getitem__(self, index):
            image = torch.full((1, 1, 16, 16), 0.1 + 0.1 * index)
            target = torch.zeros(1, 16, 16)
            target[:, 4:12, 5:11] = 1
            return image, target, 1

    training = {"base_channels": 8, "context_frames": 1, "amp": False,
                "batch_size": 2, "workers": 0, "learning_rate": 0.001,
                "weight_decay": 0.0, "epochs": 2, "early_stopping_patience": 5,
                "horizontal_flip": False, "edge_weight": 0.1, "sobel_weight": 0.1}
    config = {"training": training}
    options = {"se": False, "dilated_residual": False, "temporal": False, "edge": False}
    train_set = TinyLabeledClips()
    val_set = TinyLabeledClips()
    val_set.patient_ids = ["val-patient"]
    original_validate = experiment.validate_loss
    calls = 0

    def interrupt_on_second_epoch(model, loader, device, amp):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated interruption after the first epoch was saved")
        return original_validate(model, loader, device, amp)

    monkeypatch.setattr(experiment, "validate_loss", interrupt_on_second_epoch)
    output = tmp_path / "resume-test"
    try:
        experiment.train_variant("B", options, 2026, config, train_set, val_set, output, "cpu")
    except RuntimeError as error:
        assert "simulated interruption" in str(error)
    else:
        raise AssertionError("The simulated interruption did not occur")
    saved = torch.load(output / "resume.pt", map_location="cpu", weights_only=False)
    assert saved["next_epoch"] == 2
    monkeypatch.setattr(experiment, "validate_loss", original_validate)
    completed = experiment.train_variant("B", options, 2026, config, train_set, val_set,
                                         output, "cpu")
    assert completed["epochs_completed"] == 2
    assert len(json.loads((output / "history.json").read_text())) == 2
    assert (output / "complete.json").is_file()
