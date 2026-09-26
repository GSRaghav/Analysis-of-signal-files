from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .signal_analysis import (
    calculate_psd,
    calculate_spectrogram,
)
from .preprocessing import to_analytic_signal


def _downsample_for_plot(
    samples,
    max_points=100_000
):

    samples = np.asarray(samples)

    if len(samples) <= max_points:
        return samples

    step = int(
        np.ceil(
            len(samples) / max_points
        )
    )

    return samples[::step]


def save_waveform(
    samples,
    sample_rate,
    output_path,
    title
):

    output_path = Path(output_path)

    plot_samples = _downsample_for_plot(
        samples
    )

    time = np.arange(
        len(plot_samples)
    )

    # Estimate effective spacing after downsampling
    original_length = len(samples)

    step = max(
        1,
        int(
            np.ceil(
                original_length
                / len(plot_samples)
            )
        )
    )

    time = (
        np.arange(len(plot_samples))
        * step
        / sample_rate
    )

    plt.figure(figsize=(12, 4))

    plt.plot(
        time,
        np.real(plot_samples)
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(title)
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150
    )
    plt.close()


def save_spectrum(
    samples,
    sample_rate,
    output_path,
    title
):

    frequencies, psd_db, _ = calculate_psd(
        samples,
        sample_rate
    )

    plt.figure(figsize=(12, 4))

    plt.plot(
        frequencies,
        psd_db
    )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("PSD (dB/Hz)")
    plt.title(title)
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150
    )
    plt.close()


def save_spectrogram(
    samples,
    sample_rate,
    output_path,
    title
):

    frequencies, times, power_db = (
        calculate_spectrogram(
            samples,
            sample_rate
        )
    )

    plt.figure(figsize=(12, 5))

    plt.pcolormesh(
        times,
        frequencies,
        power_db,
        shading="auto"
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.title(title)

    plt.colorbar(
        label="Power (dB)"
    )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150
    )
    plt.close()


def save_constellation(
    samples,
    output_path,
    title,
    max_points=50_000
):

    complex_signal = (
        to_analytic_signal(samples)
    )

    if len(complex_signal) > max_points:

        indices = np.linspace(
            0,
            len(complex_signal) - 1,
            max_points,
            dtype=int
        )

        complex_signal = (
            complex_signal[indices]
        )

    plt.figure(figsize=(6, 6))

    plt.scatter(
        np.real(complex_signal),
        np.imag(complex_signal),
        s=2,
        alpha=0.4
    )

    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.title(title)

    plt.grid(True)
    plt.axis("equal")

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150
    )
    plt.close()


def save_instantaneous_frequency(
    samples,
    sample_rate,
    output_path,
    title,
    max_points=100_000
):

    complex_signal = (
        to_analytic_signal(samples)
    )

    phase = np.unwrap(
        np.angle(complex_signal)
    )

    frequency = (
        np.diff(phase)
        * sample_rate
        / (2 * np.pi)
    )

    if len(frequency) > max_points:

        step = int(
            np.ceil(
                len(frequency)
                / max_points
            )
        )

        frequency = frequency[::step]
        time = (
            np.arange(len(frequency))
            * step
            / sample_rate
        )

    else:

        time = (
            np.arange(len(frequency))
            / sample_rate
        )

    plt.figure(figsize=(12, 4))

    plt.plot(
        time,
        frequency
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Instantaneous Frequency (Hz)")
    plt.title(title)
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150
    )
    plt.close()