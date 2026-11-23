import numpy as np

from lvseg.visualization import mask_panels


def test_six_model_grid_saves_labeled_ed_still_and_renders_full_video(monkeypatch, tmp_path):
    images = np.zeros((4, 32, 32), dtype=np.uint8)
    labels = np.zeros_like(images)
    labels[0, 8:24, 8:24] = 1
    labels[3, 12:20, 12:20] = 1
    labeled = [True, False, False, True]
    metadata = {"original_hw": (32, 32), "phases": {"ED": 0, "ES": 3},
                "case_id": "example_2CH", "fps": 25}
    predictions = {f"model {index}": np.zeros_like(images) for index in range(6)}
    stills = []

    def capture_still(fig, output, **kwargs):
        expert = np.asarray(fig.axes[1].images[0].get_array())[:256, :, 0]
        stills.append((fig.texts[0].get_text(), expert.copy()))

    monkeypatch.setattr(mask_panels, "save_mask_plate", capture_still)

    frames = mask_panels.export_mask_grid(images, labels, labeled, predictions,
                                          metadata, tmp_path / "comparison.png")

    assert len(frames) == len(images)
    assert len(stills) == 1
    footer, expert = stills[0]
    assert "frame 0/3" in footer and footer.endswith("expert label: ED")
    np.testing.assert_array_equal(expert, mask_panels.square_panel(labels[0], (32, 32), mask=True))
