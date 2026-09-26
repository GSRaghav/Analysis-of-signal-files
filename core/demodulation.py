"""
Demodulation module for AutoSig-Intel.

Provides deterministic, evidence-driven demodulation for:
- BPSK
- QPSK
- 16-QAM
- 2-FSK
along with BER calculation utilities.
"""

from typing import Optional, Union
import numpy as np


def calculate_ber(
    reference_bits: Union[np.ndarray, list],
    recovered_bits: Union[np.ndarray, list]
) -> float:
    """
    Calculate Bit Error Rate (BER) between reference and recovered bitstreams.
    Robustly compares the overlapping sequence length.
    """
    ref = np.asarray(reference_bits, dtype=np.uint8).flatten()
    rec = np.asarray(recovered_bits, dtype=np.uint8).flatten()
    n = min(len(ref), len(rec))
    if n == 0:
        return 1.0
    return float(np.mean(ref[:n] != rec[:n]))


def bits_from_symbols(
    symbol_values: np.ndarray,
    threshold: float = 0.0
) -> np.ndarray:
    """
    Simple binary decision helper on real-valued symbol amplitudes.
    """
    symbol_values = np.asarray(symbol_values)
    return (symbol_values >= threshold).astype(np.uint8)


def _extract_symbols(
    samples: np.ndarray,
    samples_per_symbol: int = 1,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    Extract symbol-rate samples at a given timing offset and phase correction.
    """
    samples = np.asarray(samples)
    samples_per_symbol = max(1, int(samples_per_symbol))
    timing_offset = int(timing_offset) % samples_per_symbol

    symbols = samples[timing_offset::samples_per_symbol]
    if phase_offset != 0.0:
        symbols = symbols * np.exp(-1j * phase_offset)
    return symbols


def demodulate_bpsk(
    samples: np.ndarray,
    samples_per_symbol: int = 1,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    Hard-decision BPSK demodulation.
    Mapping (consistent with reference_signals.generate_bpsk):
        bit 0 -> -1
        bit 1 -> +1
    Decision:
        real(symbol) > 0 -> 1, else 0
    """
    symbols = _extract_symbols(samples, samples_per_symbol, timing_offset, phase_offset)
    return (np.real(symbols) > 0.0).astype(np.uint8)


def demodulate_qpsk(
    samples: np.ndarray,
    samples_per_symbol: int = 1,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    QPSK demodulation with quadrant decision.
    Mapping (consistent with reference_signals.generate_qpsk):
        (0, 0) -> +1 + 1j (Quadrant 1)
        (0, 1) -> -1 + 1j (Quadrant 2)
        (1, 1) -> -1 - 1j (Quadrant 3)
        (1, 0) -> +1 - 1j (Quadrant 4)

    Inversion rule:
        bit 0 = 1 if imag(s) < 0 else 0
        bit 1 = 1 if real(s) < 0 else 0
    """
    symbols = _extract_symbols(samples, samples_per_symbol, timing_offset, phase_offset)
    b0 = (np.imag(symbols) < 0.0).astype(np.uint8)
    b1 = (np.real(symbols) < 0.0).astype(np.uint8)

    bits = np.empty(len(symbols) * 2, dtype=np.uint8)
    bits[0::2] = b0
    bits[1::2] = b1
    return bits


def demodulate_16qam(
    samples: np.ndarray,
    samples_per_symbol: int = 1,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    16-QAM nearest-neighbor demodulation.
    Mapping (consistent with reference_signals.generate_16qam):
        4-PAM levels:
            (0, 0) -> -3
            (0, 1) -> -1
            (1, 1) -> +1
            (1, 0) -> +3
    Average power for {+/-1, +/-3} grid is 10.
    """
    symbols = _extract_symbols(samples, samples_per_symbol, timing_offset, phase_offset)
    if len(symbols) == 0:
        return np.array([], dtype=np.uint8)

    pwr = np.mean(np.abs(symbols) ** 2)
    scale = np.sqrt(10.0 / pwr) if pwr > 1e-12 else 1.0

    i = np.real(symbols) * scale
    q = np.imag(symbols) * scale

    # I branch (bits 0, 1)
    b0 = (i > 0.0).astype(np.uint8)
    b1 = (np.abs(i) < 2.0).astype(np.uint8)

    # Q branch (bits 2, 3)
    b2 = (q > 0.0).astype(np.uint8)
    b3 = (np.abs(q) < 2.0).astype(np.uint8)

    bits = np.empty(len(symbols) * 4, dtype=np.uint8)
    bits[0::4] = b0
    bits[1::4] = b1
    bits[2::4] = b2
    bits[3::4] = b3
    return bits


def demodulate_2fsk(
    samples: np.ndarray,
    sample_rate: float,
    samples_per_symbol: int = 16,
    timing_offset: int = 0,
    frequency_threshold: float = 0.0
) -> np.ndarray:
    """
    2-FSK demodulation via symbol-wise instantaneous frequency evaluation.
    Mapping (consistent with reference_signals.generate_2fsk):
        bit 0 -> -deviation
        bit 1 -> +deviation
    """
    samples = np.asarray(samples)
    samples_per_symbol = max(2, int(samples_per_symbol))
    timing_offset = int(timing_offset) % samples_per_symbol

    available = len(samples) - timing_offset
    num_symbols = available // samples_per_symbol
    if num_symbols == 0:
        return np.array([], dtype=np.uint8)

    bits = np.empty(num_symbols, dtype=np.uint8)
    for k in range(num_symbols):
        start = timing_offset + k * samples_per_symbol
        end = start + samples_per_symbol
        block = samples[start:end]
        if len(block) < 2:
            bits[k] = 0
            continue
        dtheta = np.angle(block[1:] * np.conj(block[:-1]))
        f_est = np.mean(dtheta) * sample_rate / (2.0 * np.pi)
        bits[k] = 1 if f_est > frequency_threshold else 0

    return bits


# ============================================================
# GENERIC WRAPPERS (Compatibility)
# ============================================================

def demodulate_psk(
    samples: np.ndarray,
    sample_rate: float,
    symbol_rate: float,
    order: int = 2,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    Generic PSK demodulator wrapper.
    """
    sps = max(1, int(round(sample_rate / symbol_rate)))
    if order == 2:
        return demodulate_bpsk(samples, sps, timing_offset, phase_offset)
    elif order == 4:
        return demodulate_qpsk(samples, sps, timing_offset, phase_offset)
    else:
        raise ValueError(f"Unsupported PSK order: {order}. Supported: 2, 4.")


def demodulate_qam(
    samples: np.ndarray,
    sample_rate: float,
    symbol_rate: float,
    order: int = 16,
    timing_offset: int = 0,
    phase_offset: float = 0.0
) -> np.ndarray:
    """
    Generic QAM demodulator wrapper.
    """
    sps = max(1, int(round(sample_rate / symbol_rate)))
    if order == 16:
        return demodulate_16qam(samples, sps, timing_offset, phase_offset)
    else:
        raise ValueError(f"Unsupported QAM order: {order}. Supported: 16.")


def demodulate_fsk(
    samples: np.ndarray,
    sample_rate: float,
    symbol_rate: float,
    timing_offset: int = 0,
    frequency_threshold: float = 0.0
) -> np.ndarray:
    """
    Generic 2-FSK demodulator wrapper.
    """
    sps = max(2, int(round(sample_rate / symbol_rate)))
    return demodulate_2fsk(samples, sample_rate, sps, timing_offset, frequency_threshold)