"""Small, inspectable building blocks for patch ultrasound reconstruction.

These functions are numerical primitives, not a claim that a device-specific
RF/IQ pipeline is complete. Array geometry, event timing, sound speed and
calibration must come from the acquisition record.
"""

import numpy as np
from scipy.signal import hilbert


def wide_beam_angles(start_deg=-37.5, stop_deg=37.5, count=97):
    """Return an explicit coherent-compounding angle schedule in degrees."""
    if not isinstance(count, int) or count < 2 or not np.isfinite([start_deg, stop_deg]).all():
        raise ValueError("angle schedule requires a finite range and at least two angles")
    if stop_deg <= start_deg:
        raise ValueError("stop_deg must be greater than start_deg")
    return np.linspace(float(start_deg), float(stop_deg), count)


def delay_and_sum(channel_data, sample_times_s, pixel_delays_s, apodization=None):
    """Interpolate channel signals at pixel delays and sum them coherently.

    ``channel_data`` has shape ``(channels, samples)`` and ``pixel_delays_s``
    has shape ``(pixels, channels)``. Values outside the sampled time range are
    zero rather than extrapolated.
    """
    signal = np.asarray(channel_data)
    times = np.asarray(sample_times_s, dtype=float)
    delays = np.asarray(pixel_delays_s, dtype=float)
    if signal.ndim != 2 or times.ndim != 1 or delays.ndim != 2:
        raise ValueError("expected channel_data [C,S], sample_times [S], delays [P,C]")
    if not np.issubdtype(signal.dtype, np.number):
        raise ValueError("channel_data must contain numeric RF or IQ samples")
    if signal.shape[1] != len(times) or signal.shape[0] != delays.shape[1]:
        raise ValueError("channel and time dimensions do not agree")
    if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError("sample_times_s must be finite and strictly increasing")
    weights = np.ones(signal.shape[0], dtype=float) if apodization is None else np.asarray(apodization, float)
    if weights.shape != (signal.shape[0],) or not np.all(np.isfinite(weights)):
        raise ValueError("apodization must contain one finite weight per channel")
    sampled = np.empty(delays.shape, dtype=np.result_type(signal.dtype, np.float64))
    for channel in range(signal.shape[0]):
        values = signal[channel]
        if np.iscomplexobj(values):
            sampled[:, channel] = (
                np.interp(delays[:, channel], times, values.real, left=0.0, right=0.0)
                + 1j * np.interp(
                    delays[:, channel], times, values.imag, left=0.0, right=0.0
                )
            )
        else:
            sampled[:, channel] = np.interp(
                delays[:, channel], times, values, left=0.0, right=0.0
            )
    return (sampled * weights[None, :]).sum(axis=1)


def envelope(signal, axis=-1):
    """Return the analytic-signal envelope along one axis."""
    values = np.asarray(signal)
    if values.size == 0:
        raise ValueError("signal must not be empty")
    if not np.issubdtype(values.dtype, np.number):
        raise ValueError("signal must contain numeric samples")
    if np.iscomplexobj(values):
        return np.abs(values)
    return np.abs(hilbert(values, axis=axis))


def log_compress(amplitude, dynamic_range_db=60.0, reference=None, output_max=255):
    """Map amplitudes to an integer-like log-compressed display range."""
    values = np.asarray(amplitude, dtype=float)
    if not np.isfinite(dynamic_range_db) or dynamic_range_db <= 0:
        raise ValueError("dynamic_range_db must be positive")
    if reference is None:
        reference = float(np.nanmax(np.abs(values)))
    if not np.isfinite(reference) or reference <= 0:
        raise ValueError("reference amplitude must be positive")
    db = 20.0 * np.log10(np.maximum(np.abs(values), np.finfo(float).tiny) / reference)
    scaled = (np.clip(db, -dynamic_range_db, 0.0) + dynamic_range_db) / dynamic_range_db
    return np.rint(scaled * output_max).astype(np.uint8)


def rms_pressure(samples, axis=-1):
    """Compute RMS pressure for an acoustic simulation or recorded trace."""
    values = np.asarray(samples)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("samples must be finite and non-empty")
    return np.sqrt(np.mean(np.abs(values) ** 2, axis=axis))
