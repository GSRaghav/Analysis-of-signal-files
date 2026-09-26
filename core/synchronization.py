"""
Synchronization module for AutoSig-Intel.

Provides carrier frequency, carrier phase, and symbol timing synchronization
primitives for digital communication signals (BPSK, QPSK, 16-QAM, 2-FSK).
"""

from typing import Dict, Any, Optional
import numpy as np

from .timing import _detect_fsk_transitions, _detect_signal_transitions


# ============================================================
# IMPAIRMENT GENERATORS (for testing and simulation)
# ============================================================

def apply_frequency_offset(
    samples: np.ndarray,
    sample_rate: float,
    frequency_offset: float
) -> np.ndarray:
    """
    Apply carrier frequency offset to signal:
    y[n] = x[n] * exp(j * 2 * pi * f_offset * n / Fs)
    """
    samples = np.asarray(samples)
    t = np.arange(len(samples)) / float(sample_rate)
    return samples * np.exp(1j * 2.0 * np.pi * frequency_offset * t)


def apply_phase_offset(
    samples: np.ndarray,
    phase_offset_rad: float
) -> np.ndarray:
    """
    Apply carrier phase offset to signal:
    y[n] = x[n] * exp(j * phase_offset_rad)
    """
    samples = np.asarray(samples)
    return samples * np.exp(1j * phase_offset_rad)


def add_awgn(
    samples: np.ndarray,
    snr_db: float
) -> np.ndarray:
    """
    Add complex zero-mean Gaussian white noise at specified SNR (dB).
    """
    samples = np.asarray(samples)
    signal_power = np.mean(np.abs(samples) ** 2)
    snr_linear = 10.0 ** (float(snr_db) / 10.0)
    noise_power = signal_power / max(snr_linear, 1e-15)
    noise_std = np.sqrt(noise_power / 2.0)

    noise = (
        np.random.normal(0.0, noise_std, len(samples))
        + 1j * np.random.normal(0.0, noise_std, len(samples))
    )
    return samples + noise


# ============================================================
# BASE CARRIER FREQUENCY RECOVERY
# ============================================================

def estimate_frequency_offset(
    samples: np.ndarray,
    sample_rate: float
) -> float:
    """
    Carrier frequency-offset estimate from median instantaneous phase derivative.
    Suitable for unmodulated carrier or continuous-phase balanced FSK.
    """
    samples = np.asarray(samples)
    if not np.iscomplexobj(samples):
        raise ValueError("Frequency-offset estimation requires a complex signal.")

    phase = np.unwrap(np.angle(samples))
    if len(phase) < 2:
        return 0.0

    instantaneous_frequency = np.diff(phase) * sample_rate / (2.0 * np.pi)
    return float(np.median(instantaneous_frequency))


def correct_frequency_offset(
    samples: np.ndarray,
    sample_rate: float,
    frequency_offset: float
) -> np.ndarray:
    """
    Mix signal with complex conjugate of carrier frequency offset:
    y[n] = x[n] * exp(-j * 2 * pi * f_offset * n / Fs)
    """
    samples = np.asarray(samples)
    time = np.arange(len(samples)) / float(sample_rate)
    correction = np.exp(-1j * 2.0 * np.pi * frequency_offset * time)
    return samples * correction


def _estimate_cfo_mth_power(
    samples: np.ndarray,
    sample_rate: float,
    order: int,
    n_fft: int = 65536
) -> float:
    """
    Viterbi & Viterbi / Power-of-M carrier frequency offset estimator.
    Raising M-PSK or square QAM to the M-th power eliminates modulation,
    concentrating energy at M * Delta_f.
    """
    samples = np.asarray(samples)
    order = int(order)
    n = min(len(samples), 262144)
    x = samples[:n] ** order

    n_fft = max(n_fft, min(n, 65536))
    spec = np.fft.fft(x, n=n_fft)
    freqs = np.fft.fftfreq(n_fft, d=1.0 / sample_rate)

    peak_idx = int(np.argmax(np.abs(spec)))
    f_peak = float(freqs[peak_idx])
    return f_peak / order


# ============================================================
# MODULATION SYNCHRONIZERS
# ============================================================

def synchronize_psk(
    samples: np.ndarray,
    sample_rate: float,
    samples_per_symbol: int,
    order: int = 2
) -> Dict[str, Any]:
    """
    Full carrier and timing synchronization for M-PSK (BPSK or QPSK).

    Returns:
        dict containing:
            - 'symbols': synchronized symbol-spaced complex samples
            - 'frequency_offset_hz': estimated CFO
            - 'timing_offset': best symbol sample index
            - 'phase_offset_rad': estimated carrier phase
    """
    samples = np.asarray(samples, dtype=np.complex64)
    sps = max(1, int(samples_per_symbol))
    order = int(order)

    # 1. Frequency Offset Recovery (M-th power spectrum)
    f_offset = _estimate_cfo_mth_power(samples, sample_rate, order)
    corrected = correct_frequency_offset(samples, sample_rate, f_offset)

    # 2. Symbol Timing Recovery (transition alignment with compactness fallback)
    best_timing = 0
    if sps > 1:
        transitions = _detect_signal_transitions(corrected)
        if len(transitions) >= 3:
            min_err = float("inf")
            for offset in range(sps):
                aligned = transitions - offset
                aligned = aligned[aligned >= 0]
                if len(aligned) < 3:
                    continue
                rem = np.mod(aligned, sps)
                circ = np.minimum(rem, sps - rem)
                err = float(np.median(circ))
                if err < min_err:
                    min_err = err
                    best_timing = (offset + 1) % sps
        else:
            best_score = -1.0
            for k in range(sps):
                cand_syms = corrected[k::sps]
                if len(cand_syms) < 10:
                    continue
                score = float(np.abs(np.mean(cand_syms ** order)))
                if score > best_score:
                    best_score = score
                    best_timing = k

    symbols = corrected[best_timing::sps]

    # 3. Carrier Phase Recovery
    if order == 2:
        # BPSK: average of s^2 has angle 2 * phi
        ang = np.angle(np.mean(symbols ** 2))
        phi = ang / 2.0
        # Wrap to principal interval [-pi/2, pi/2]
        best_phi = (phi + np.pi / 2.0) % np.pi - np.pi / 2.0
    elif order == 4:
        # QPSK: ideal points are exp(j * (pi/4 + k*pi/2)), so s^4 has nominal angle pi.
        # angle(mean(s^4)) - pi = 4 * phi
        ang = np.angle(np.mean(symbols ** 4))
        phi_base = (ang - np.pi) / 4.0
        # Wrap to principal quadrant [-pi/4, pi/4]
        best_phi = (phi_base + np.pi / 4.0) % (np.pi / 2.0) - np.pi / 4.0
    else:
        best_phi = 0.0

    synchronized_symbols = symbols * np.exp(-1j * best_phi)

    return {
        "symbols": synchronized_symbols,
        "frequency_offset_hz": float(f_offset),
        "timing_offset": int(best_timing),
        "phase_offset_rad": float(best_phi),
    }


def synchronize_qam(
    samples: np.ndarray,
    sample_rate: float,
    samples_per_symbol: int,
    order: int = 16
) -> Dict[str, Any]:
    """
    Full carrier and timing synchronization for 16-QAM.

    Returns:
        dict containing:
            - 'symbols': synchronized symbol-spaced complex samples
            - 'frequency_offset_hz': estimated CFO
            - 'timing_offset': best symbol sample index
            - 'phase_offset_rad': estimated carrier phase
    """
    samples = np.asarray(samples, dtype=np.complex64)
    sps = max(1, int(samples_per_symbol))

    # 1. Frequency Offset Recovery (4th power spectrum)
    f_offset = _estimate_cfo_mth_power(samples, sample_rate, 4)
    corrected = correct_frequency_offset(samples, sample_rate, f_offset)

    # 2. Symbol Timing Recovery (transition alignment with compactness fallback)
    best_timing = 0
    if sps > 1:
        transitions = _detect_signal_transitions(corrected)
        if len(transitions) >= 3:
            min_err = float("inf")
            for offset in range(sps):
                aligned = transitions - offset
                aligned = aligned[aligned >= 0]
                if len(aligned) < 3:
                    continue
                rem = np.mod(aligned, sps)
                circ = np.minimum(rem, sps - rem)
                err = float(np.median(circ))
                if err < min_err:
                    min_err = err
                    best_timing = (offset + 1) % sps
        else:
            best_score = -1.0
            for k in range(sps):
                cand_syms = corrected[k::sps]
                if len(cand_syms) < 10:
                    continue
                score = float(np.abs(np.mean(cand_syms ** 4)))
                if score > best_score:
                    best_score = score
                    best_timing = k

    symbols = corrected[best_timing::sps]

    # 3. Carrier Phase Recovery
    ang = np.angle(np.mean(symbols ** 4))
    phi_base = (ang - np.pi) / 4.0
    # Wrap to principal quadrant [-pi/4, pi/4]
    phi_wrapped = (phi_base + np.pi / 4.0) % (np.pi / 2.0) - np.pi / 4.0

    synchronized_symbols = symbols * np.exp(-1j * phi_wrapped)

    return {
        "symbols": synchronized_symbols,
        "frequency_offset_hz": float(f_offset),
        "timing_offset": int(best_timing),
        "phase_offset_rad": float(phi_wrapped),
    }


def synchronize_fsk(
    samples: np.ndarray,
    sample_rate: float,
    samples_per_symbol: int
) -> Dict[str, Any]:
    """
    Frequency and timing synchronization for 2-FSK.

    Returns:
        dict containing:
            - 'frequency_corrected_signal': continuous CFO-corrected waveform
            - 'frequency_offset_hz': estimated carrier offset
            - 'timing_offset': estimated symbol boundary offset
            - 'fsk_decision_threshold_hz': 0.0 (centered decision)
            - 'symbols': downsampled symbol representations
    """
    samples = np.asarray(samples, dtype=np.complex64)
    sps = max(2, int(samples_per_symbol))

    # 1. Carrier Frequency Offset Recovery from balanced instantaneous frequency
    dtheta = np.angle(samples[1:] * np.conj(samples[:-1]))
    f_offset = float(np.mean(dtheta) * sample_rate / (2.0 * np.pi))
    corrected = correct_frequency_offset(samples, sample_rate, f_offset)

    # 2. Symbol Boundary Detection
    transitions = _detect_fsk_transitions(corrected, sample_rate)
    if len(transitions) >= 3:
        best_trans_offset = 0
        min_err = float("inf")
        for offset in range(sps):
            aligned = transitions - offset
            aligned = aligned[aligned >= 0]
            if len(aligned) < 3:
                continue
            rem = np.mod(aligned, sps)
            circ = np.minimum(rem, sps - rem)
            err = float(np.median(circ))
            if err < min_err:
                min_err = err
                best_trans_offset = offset
        # Symbol starts immediately after the transition sample
        symbol_start = (best_trans_offset + 1) % sps
    else:
        symbol_start = 0

    return {
        "frequency_corrected_signal": corrected,
        "frequency_offset_hz": float(f_offset),
        "timing_offset": int(symbol_start),
        "fsk_decision_threshold_hz": 0.0,
        "symbols": corrected[symbol_start::sps],
    }