import numpy as np
import pytest
from PIL import Image

from backend.app.services.orientation import fan_rotation, sequence_rotation
from backend.app.services.segmenter import prepare_frames


def upright_fan():
    y, x = np.ogrid[:220, :320]
    depth = y - 18
    fan = (depth >= 0) & (abs(x - 160) <= 0.83 * depth) & ((x - 160)**2 + depth**2 <= 188**2)
    return np.where(fan, 140, 0).astype(np.uint8)


@pytest.mark.parametrize("source_turns", [0, -1, 1])
def test_sideways_input_uses_same_model_grid_and_undoes_rotation(tmp_path, source_turns):
    upright = upright_fan()
    input_frame = np.rot90(upright, source_turns)
    image = tmp_path / "fan.png"
    Image.fromarray(input_frame).save(image)
    frames, previews, fps, turns = prepare_frames(image, max_frames=1)
    assert turns == -source_turns and fps is None
    assert np.array_equal(previews[0], input_frame)
    expected = np.asarray(Image.fromarray(upright).resize((256, 192), Image.Resampling.BILINEAR))
    np.testing.assert_allclose(frames[0], expected, atol=1)
    binary = frames > 60
    inverse = np.rot90(binary, -turns, axes=(1, 2))
    assert inverse.shape[1:] == ((256, 192) if source_turns else (192, 256))


def test_orientation_requires_a_horizontal_fan_and_a_clip_majority():
    upright = upright_fan()
    left = np.rot90(upright, 1)
    right = np.rot90(upright, -1)
    assert fan_rotation(np.full((160, 220), 60, dtype=np.uint8)) == 0
    assert sequence_rotation([left, left, upright, left, right]) == -1
    assert sequence_rotation([left, right, upright, left, right]) == 0
