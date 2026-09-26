import numpy as np

from scipy.signal import butter, sosfiltfilt, hilbert


def remove_dc(samples):
    """
    Remove DC component.
    """

    samples = np.asarray(samples)

    return samples - np.mean(samples)


def normalize_signal(samples):
    """
    Normalize a signal by its maximum magnitude.
    """

    samples = np.asarray(samples)

    peak = np.max(np.abs(samples))

    if peak == 0:
        return samples

    return samples / peak


def to_analytic_signal(samples):
    """
    Convert a real-valued signal into an analytic complex signal.

    Complex IQ input is returned unchanged.
    """

    samples = np.asarray(samples)

    if np.iscomplexobj(samples):
        return samples

    return hilbert(samples)


def bandpass_filter(
    samples,
    sample_rate,
    low_cut,
    high_cut,
    order=5
):

    nyquist = sample_rate / 2.0

    if not (0 < low_cut < high_cut < nyquist):
        raise ValueError(
            "Require 0 < low_cut < high_cut < Nyquist."
        )

    sos = butter(
        order,
        [
            low_cut / nyquist,
            high_cut / nyquist
        ],
        btype="bandpass",
        output="sos"
    )

    return sosfiltfilt(
        sos,
        samples
    )


def lowpass_filter(
    samples,
    sample_rate,
    cutoff,
    order=5
):

    nyquist = sample_rate / 2.0

    if not (0 < cutoff < nyquist):
        raise ValueError(
            "Cutoff must be between 0 and Nyquist."
        )

    sos = butter(
        order,
        cutoff / nyquist,
        btype="lowpass",
        output="sos"
    )

    return sosfiltfilt(
        sos,
        samples
    )