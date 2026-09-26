import numpy as np

from scipy.signal import (
    welch,
    stft,
    find_peaks,
)


def calculate_basic_parameters(
    samples,
    sample_rate
):
    samples = np.asarray(samples)

    if len(samples) == 0:
        raise ValueError(
            "Signal contains no samples."
        )

    magnitude = np.abs(samples)

    return {
        "sample_rate": float(sample_rate),

        "num_samples": int(len(samples)),

        "duration": float(
            len(samples) / sample_rate
        ),

        "rms": float(
            np.sqrt(
                np.mean(
                    magnitude ** 2
                )
            )
        ),

        "peak": float(
            np.max(magnitude)
        ),

        "dc_offset": float(
            abs(np.mean(samples))
        ),
    }


def calculate_psd(
    samples,
    sample_rate,
    nperseg=8192
):
    """
    Welch power spectral density.

    More suitable for long signals than taking
    one giant FFT of the entire recording.
    """

    samples = np.asarray(samples)

    nperseg = min(
        nperseg,
        len(samples)
    )

    frequencies, psd = welch(
        samples,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2,
        return_onesided=not np.iscomplexobj(samples),
        scaling="density"
    )

    psd_db = 10 * np.log10(
        psd + 1e-20
    )

    return frequencies, psd_db, psd


def calculate_spectrum(
    samples,
    sample_rate,
    nperseg=8192
):
    """
    Compatibility wrapper.
    """

    frequencies, psd_db, _ = calculate_psd(
        samples,
        sample_rate,
        nperseg
    )

    return frequencies, psd_db


def estimate_peak_frequency(
    samples,
    sample_rate
):

    frequencies, psd_db, _ = calculate_psd(
        samples,
        sample_rate
    )

    index = np.argmax(psd_db)

    return float(
        frequencies[index]
    )


def estimate_noise_floor(
    samples,
    sample_rate
):
    """
    Robust approximate noise-floor estimate.

    Uses the lower percentile of PSD values
    rather than simply taking the FFT minimum.
    """

    _, psd_db, _ = calculate_psd(
        samples,
        sample_rate
    )

    return float(
        np.percentile(psd_db, 20)
    )


def estimate_snr(
    samples,
    sample_rate
):
    """
    Approximate spectrum-based SNR estimate.

    This is a screening metric, not a calibrated
    RF measurement.
    """

    frequencies, psd_db, psd = calculate_psd(
        samples,
        sample_rate
    )

    noise_floor_db = estimate_noise_floor(
        samples,
        sample_rate
    )

    threshold_db = noise_floor_db + 6.0

    signal_mask = (
        psd_db >= threshold_db
    )

    if not np.any(signal_mask):
        return float("nan")

    signal_power = np.trapezoid(
        psd[signal_mask],
        frequencies[signal_mask]
    )

    noise_mask = ~signal_mask

    if np.any(noise_mask):

        noise_power = np.median(
            psd[noise_mask]
        ) * (
            frequencies[-1]
            - frequencies[0]
        )

    else:

        noise_power = 0.0

    if signal_power <= 0 or noise_power <= 0:
        return float("nan")

    return float(
        10 * np.log10(
            signal_power / noise_power
        )
    )


def estimate_bandwidth(
    samples,
    sample_rate,
    threshold_db=-20.0
):
    """
    Estimate occupied spectral span relative to
    the maximum PSD level.

    Returns the frequency span between the
    lower and upper threshold crossings.

    This is a preliminary occupied-span estimate,
    not a standards-based occupied-bandwidth measurement.
    """

    frequencies, psd_db, _ = calculate_psd(
        samples,
        sample_rate
    )

    peak_db = np.max(psd_db)

    mask = psd_db >= (
        peak_db + threshold_db
    )

    if not np.any(mask):
        return 0.0

    selected = frequencies[mask]

    lower = np.min(selected)
    upper = np.max(selected)

    return float(
        abs(upper - lower)
    )


def calculate_spectrogram(
    samples,
    sample_rate,
    nperseg=2048
):

    samples = np.asarray(samples)

    nperseg = min(
        nperseg,
        len(samples)
    )

    frequencies, times, zxx = stft(
        samples,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2,
        return_onesided=not np.iscomplexobj(samples)
    )

    power = np.abs(zxx) ** 2
    if np.iscomplexobj(samples):
        frequencies = np.fft.fftshift(frequencies)
        power = np.fft.fftshift(power, axes=0)

    power_db = 10 * np.log10(
        power + 1e-20
    )

    return frequencies, times, power_db


def analytic_features(samples, sample_rate):
    """
    Extract amplitude, phase and instantaneous-frequency
    statistics from a complex/analytic signal.
    """

    samples = np.asarray(samples)

    if not np.iscomplexobj(samples):
        raise ValueError(
            "analytic_features requires a complex "
            "or analytic signal."
        )

    amplitude = np.abs(samples)

    phase = np.unwrap(
        np.angle(samples)
    )

    frequency = (
        np.diff(phase)
        * sample_rate
        / (2 * np.pi)
    )

    return {
        "amplitude_mean": float(
            np.mean(amplitude)
        ),

        "amplitude_std": float(
            np.std(amplitude)
        ),

        "amplitude_median": float(
            np.median(amplitude)
        ),

        "phase_std": float(
            np.std(phase)
        ),

        "instantaneous_frequency_mean": float(
            np.mean(frequency)
        ),

        "instantaneous_frequency_std": float(
            np.std(frequency)
        ),

        "instantaneous_frequency_median": float(
            np.median(frequency)
        ),
    }


def spectral_peaks(
    samples,
    sample_rate,
    prominence_db=10.0
):

    frequencies, psd_db, _ = calculate_psd(
        samples,
        sample_rate
    )

    peaks, properties = find_peaks(
        psd_db,
        prominence=prominence_db
    )

    return {
        "frequencies": frequencies[peaks],
        "power_db": psd_db[peaks],
        "properties": properties,
    }