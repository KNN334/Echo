import numpy as np
import pytest

from src.patch.beamforming import (
    delay_and_sum,
    envelope,
    log_compress,
    rms_pressure,
    wide_beam_angles,
)


def test_wide_beam_angles_are_explicit_and_ordered():
    angles = wide_beam_angles(-10, 10, 5)

    assert np.allclose(angles, [-10, -5, 0, 5, 10])


def test_delay_and_sum_interpolates_channels_and_zeroes_outside_range():
    times = np.arange(5, dtype=float)
    channel_data = np.stack([times, 2 * times])
    delays = np.array([[1.5, 1.5], [-1.0, 1.0], [8.0, 8.0]])

    result = delay_and_sum(channel_data, times, delays)

    assert np.allclose(result, [4.5, 2.0, 0.0])


def test_delay_and_sum_preserves_complex_iq_phase():
    times = np.arange(3, dtype=float)
    channel_data = np.array([[1 + 1j, 2 + 2j, 3 + 3j]])
    delays = np.array([[0.5]])

    result = delay_and_sum(channel_data, times, delays)

    assert np.allclose(result, [1.5 + 1.5j])


def test_signal_primitives_preserve_shape_and_display_range():
    time = np.linspace(0, 2 * np.pi, 128, endpoint=False)
    signal = np.sin(time)[None, :]

    analytic = envelope(signal)
    compressed = log_compress(analytic, reference=1.0)

    assert analytic.shape == signal.shape
    assert np.all(analytic >= 0)
    assert compressed.dtype == np.uint8
    assert int(compressed.max()) == 255


def test_complex_iq_envelope_returns_magnitude():
    iq = np.array([1 + 1j, 3 + 4j])

    assert np.allclose(envelope(iq), [np.sqrt(2), 5])


def test_rms_pressure_rejects_nonfinite_samples():
    assert np.isclose(rms_pressure(np.array([3.0, 4.0])), 3.5355339)
    with pytest.raises(ValueError, match="finite"):
        rms_pressure(np.array([1.0, np.nan]))
