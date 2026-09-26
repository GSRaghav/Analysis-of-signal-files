import numpy as np

from scipy.signal import hilbert, welch


# ============================================================
# BASIC UTILITIES
# ============================================================

def normalize_signal(samples):
    samples = np.asarray(
        samples,
        dtype=np.complex64
    )

    if len(samples) == 0:
        return samples

    samples = samples - np.mean(samples)

    power = np.mean(
        np.abs(samples) ** 2
    )

    if power <= 1e-12:
        return samples

    return (
        samples / np.sqrt(power)
    ).astype(np.complex64)


def analytic_signal(samples):
    samples = np.asarray(
        samples,
        dtype=np.float32
    )

    if len(samples) == 0:
        return np.array(
            [],
            dtype=np.complex64
        )

    return hilbert(
        samples
    ).astype(np.complex64)


# ============================================================
# SPECTRAL FEATURES
# ============================================================

def spectral_features(
    samples,
    sample_rate,
    nperseg=4096
):
    samples = np.asarray(
        samples,
        dtype=np.complex64
    )

    if len(samples) < 64:
        return {
            "dominant_frequency_hz": 0.0,
            "occupied_bandwidth_hz": 0.0,
            "spectral_peak_ratio": 0.0,
            "spectral_flatness": 0.0,
            "spectral_entropy": 0.0,
        }

    nperseg = min(
        nperseg,
        len(samples)
    )

    frequencies, psd = welch(
        samples,
        fs=sample_rate,
        nperseg=nperseg,
        return_onesided=False,
        scaling="density"
    )

    frequencies = np.fft.fftshift(
        frequencies
    )

    psd = np.fft.fftshift(
        np.maximum(
            psd,
            0
        )
    )

    total = np.sum(psd)

    if total <= 1e-15:
        return {
            "dominant_frequency_hz": 0.0,
            "occupied_bandwidth_hz": 0.0,
            "spectral_peak_ratio": 0.0,
            "spectral_flatness": 0.0,
            "spectral_entropy": 0.0,
        }

    probability = (
        psd / total
    )

    peak_ratio = float(
        np.max(probability)
    )

    positive = psd[
        psd > 1e-20
    ]

    if len(positive):

        flatness = (
            np.exp(
                np.mean(
                    np.log(positive)
                )
            )
            /
            np.mean(positive)
        )

    else:
        flatness = 0.0

    entropy = (
        -np.sum(
            probability
            *
            np.log2(
                probability + 1e-20
            )
        )
        /
        np.log2(
            len(probability)
        )
    )

    dominant = int(
        np.argmax(psd)
    )

    # 99% occupied power.
    cumulative = np.cumsum(
        psd
    ) / total

    low_index = np.searchsorted(
        cumulative,
        0.005
    )

    high_index = np.searchsorted(
        cumulative,
        0.995
    )

    low_index = min(
        max(low_index, 0),
        len(frequencies) - 1
    )

    high_index = min(
        max(high_index, 0),
        len(frequencies) - 1
    )

    bandwidth = abs(
        frequencies[high_index]
        -
        frequencies[low_index]
    )

    return {
        "dominant_frequency_hz":
            float(
                frequencies[dominant]
            ),

        "occupied_bandwidth_hz":
            float(bandwidth),

        "spectral_peak_ratio":
            peak_ratio,

        "spectral_flatness":
            float(flatness),

        "spectral_entropy":
            float(entropy),
    }


# ============================================================
# ENVELOPE FEATURES
# ============================================================

def envelope_features(samples):

    envelope = np.abs(
        np.asarray(
            samples,
            dtype=np.complex64
        )
    )

    if len(envelope) == 0:
        return {
            "mean": 0.0,
            "std": 0.0,
            "cv": 0.0,
            "p10": 0.0,
            "p50": 0.0,
            "p90": 0.0,
        }

    mean = float(
        np.mean(envelope)
    )

    std = float(
        np.std(envelope)
    )

    return {
        "mean": mean,
        "std": std,
        "cv": float(
            std / max(
                mean,
                1e-12
            )
        ),
        "p10": float(
            np.percentile(
                envelope,
                10
            )
        ),
        "p50": float(
            np.percentile(
                envelope,
                50
            )
        ),
        "p90": float(
            np.percentile(
                envelope,
                90
            )
        ),
    }


# ============================================================
# PHASE FEATURES
# ============================================================

def phase_features(samples):

    samples = np.asarray(
        samples,
        dtype=np.complex64
    )

    if len(samples) < 2:
        return {
            "phase_increment_std": 0.0,
            "phase_increment_mean": 0.0,
        }

    phase_increment = np.angle(
        samples[1:]
        *
        np.conj(
            samples[:-1]
        )
    )

    return {
        "phase_increment_std":
            float(
                np.std(
                    phase_increment
                )
            ),
        "phase_increment_mean":
            float(
                np.mean(
                    phase_increment
                )
            ),
    }


# ============================================================
# MOMENT FEATURES
# ============================================================

def moment_features(samples):

    x = normalize_signal(
        samples
    )

    if len(x) < 20:
        return {
            "m2": 0.0,
            "m4": 0.0,
            "m2_abs": 0.0,
            "m4_abs": 0.0,
        }

    magnitude_squared = (
        np.abs(x) ** 2
    )

    m2 = np.mean(
        x ** 2
    )

    m4 = np.mean(
        x ** 4
    )

    m2_abs = np.mean(
        magnitude_squared
    )

    m4_abs = np.mean(
        magnitude_squared ** 2
    )

    return {
        "m2":
            float(abs(m2)),
        "m4":
            float(abs(m4)),
        "m2_abs":
            float(abs(m2_abs)),
        "m4_abs":
            float(abs(m4_abs)),
    }


# ============================================================
# SINGLE-TONE DETECTION
# ============================================================

def single_tone_score(
    samples,
    sample_rate
):

    features = spectral_features(
        samples,
        sample_rate
    )

    bandwidth_ratio = (
        features[
            "occupied_bandwidth_hz"
        ]
        /
        max(
            sample_rate,
            1.0
        )
    )

    peak_ratio = features[
        "spectral_peak_ratio"
    ]

    entropy = features[
        "spectral_entropy"
    ]

    # Tone-like characteristics.
    narrowband_score = np.clip(
        1.0
        -
        bandwidth_ratio * 5.0,
        0.0,
        1.0
    )

    peak_score = np.clip(
        peak_ratio * 20.0,
        0.0,
        1.0
    )

    low_entropy_score = np.clip(
        1.0
        -
        entropy,
        0.0,
        1.0
    )

    score = (
        0.45 * narrowband_score
        +
        0.35 * peak_score
        +
        0.20 * low_entropy_score
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0
        )
    )


# ============================================================
# DIGITAL SIGNAL GATE
# ============================================================

def digital_signal_screen(
    samples,
    sample_rate
):

    samples = normalize_signal(
        samples
    )

    if len(samples) < 1000:
        return {
            "decision":
                "INSUFFICIENT_DATA",
            "digital_likelihood":
                0.0,
            "single_tone_score":
                1.0,
        }

    spectral = spectral_features(
        samples,
        sample_rate
    )

    envelope = envelope_features(
        samples
    )

    moments = moment_features(
        samples
    )

    tone_score = single_tone_score(
        samples,
        sample_rate
    )

    bandwidth_ratio = (
        spectral[
            "occupied_bandwidth_hz"
        ]
        /
        sample_rate
    )

    # --------------------------------------------------------
    # Broad/structured spectrum evidence
    # --------------------------------------------------------

    bandwidth_evidence = np.clip(
        bandwidth_ratio * 5.0,
        0.0,
        1.0
    )

    entropy_evidence = np.clip(
        spectral[
            "spectral_entropy"
        ],
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Amplitude structure
    # --------------------------------------------------------

    amplitude_variation = np.clip(
        envelope["cv"],
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Higher-order moment structure
    # --------------------------------------------------------

    moment_structure = np.clip(
        moments["m4"],
        0.0,
        1.0
    )

    digital_likelihood = (
        0.35 * (1.0 - tone_score)
        +
        0.25 * bandwidth_evidence
        +
        0.20 * entropy_evidence
        +
        0.10 * amplitude_variation
        +
        0.10 * moment_structure
    )

    if tone_score >= 0.70:

        decision = (
            "NON_DIGITAL_LIKELY"
        )

        reason = (
            "Signal is strongly dominated "
            "by narrow spectral structure."
        )

    elif digital_likelihood >= 0.45:

        decision = (
            "DIGITAL_SIGNAL_PLAUSIBLE"
        )

        reason = (
            "Signal contains sufficient "
            "structured spectral/statistical "
            "evidence for modulation testing."
        )

    else:

        decision = "AMBIGUOUS"

        reason = (
            "Signal does not provide enough "
            "evidence for reliable automatic "
            "digital-modulation inference."
        )

    return {
        "decision":
            decision,

        "digital_likelihood":
            float(
                np.clip(
                    digital_likelihood,
                    0.0,
                    1.0
                )
            ),

        "single_tone_score":
            float(tone_score),

        "bandwidth_ratio":
            float(bandwidth_ratio),

        "spectral_entropy":
            float(
                spectral[
                    "spectral_entropy"
                ]
            ),

        "amplitude_variation":
            float(
                amplitude_variation
            ),

        "moment_structure":
            float(
                moment_structure
            ),

        "reason":
            reason,
    }


# ============================================================
# MODULATION EVIDENCE
# ============================================================

def modulation_evidence(
    samples,
    sample_rate
):
    """
    Produce comparable pre-synchronization evidence.

    This is deliberately conservative. It does not try
    to assign a modulation label by itself.
    """

    x = normalize_signal(
        samples
    )

    envelope = envelope_features(
        x
    )

    spectral = spectral_features(
        x,
        sample_rate
    )

    moments = moment_features(
        x
    )

    phase = phase_features(
        x
    )

    amplitude_cv = envelope[
        "cv"
    ]

    phase_std = phase[
        "phase_increment_std"
    ]

    # --------------------------------------------------------
    # Constant-envelope evidence
    # --------------------------------------------------------

    constant_envelope = np.clip(
        1.0
        -
        amplitude_cv * 4.0,
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # QAM amplitude evidence
    # --------------------------------------------------------

    qam_amplitude = np.clip(
        amplitude_cv * 3.0,
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Broad spectral evidence
    # --------------------------------------------------------

    broad_spectrum = np.clip(
        (
            spectral[
                "occupied_bandwidth_hz"
            ]
            /
            sample_rate
        ) * 4.0,
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Candidate family evidence
    #
    # These are not final classification scores.
    # --------------------------------------------------------

    bpsk = (
        0.55 * constant_envelope
        +
        0.20 * broad_spectrum
        +
        0.25 * np.clip(
            moments["m2"],
            0.0,
            1.0
        )
    )

    qpsk = (
        0.45 * constant_envelope
        +
        0.25 * broad_spectrum
        +
        0.30 * (
            1.0
            -
            np.clip(
                moments["m2"],
                0.0,
                1.0
            )
        )
    )

    qam16 = (
        0.55 * qam_amplitude
        +
        0.25 * broad_spectrum
        +
        0.20 * np.clip(
            moments["m4"],
            0.0,
            1.0
        )
    )

    fsk = (
        0.60 * constant_envelope
        +
        0.20 * broad_spectrum
        +
        0.20 * np.clip(
            phase_std,
            0.0,
            1.0
        )
    )

    scores = {
        "BPSK": float(
            np.clip(
                bpsk,
                0.0,
                1.0
            )
        ),
        "QPSK": float(
            np.clip(
                qpsk,
                0.0,
                1.0
            )
        ),
        "16-QAM": float(
            np.clip(
                qam16,
                0.0,
                1.0
            )
        ),
        "2-FSK": float(
            np.clip(
                fsk,
                0.0,
                1.0
            )
        ),
    }

    return {
        "scores": scores,

        "constant_envelope_evidence":
            float(
                constant_envelope
            ),

        "qam_amplitude_evidence":
            float(
                qam_amplitude
            ),

        "broad_spectrum_evidence":
            float(
                broad_spectrum
            ),
    }


# ============================================================
# COMPLETE REPORT
# ============================================================

def build_hypothesis_report(
    samples,
    sample_rate,
    representation="unknown"
):

    x = normalize_signal(
        samples
    )

    # Limit analysis size to representative continuous segment (prevents aliasing)
    if len(x) > 100000:
        start_idx = max(0, (len(x) - 100000) // 2)
        x = x[start_idx:start_idx + 100000]

    spectral = spectral_features(
        x,
        sample_rate
    )

    envelope = envelope_features(
        x
    )

    phase = phase_features(
        x
    )

    moments = moment_features(
        x
    )

    screen = digital_signal_screen(
        x,
        sample_rate
    )

    evidence = modulation_evidence(
        x,
        sample_rate
    )

    return {
        "representation":
            representation,

        "spectral":
            spectral,

        "envelope":
            envelope,

        "phase":
            phase,

        "moments":
            moments,

        "screen":
            screen,

        "modulation_evidence":
            evidence,

        "recommended_action": (
            "STOP"
            if screen[
                "decision"
            ]
            in (
                "NON_DIGITAL_LIKELY",
                "INSUFFICIENT_DATA"
            )
            else
            "CONTINUE"
        ),
    }