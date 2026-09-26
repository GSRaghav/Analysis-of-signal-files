"""
Receiver module for AutoSig-Intel.

Provides the central pipeline orchestrator connecting:
- Ingestion (WAV / IQ format handling)
- Preprocessing & Characterization
- Digital Signal Gating
- Symbol Timing Recovery
- Synchronization (Carrier CFO/phase & Timing)
- Demodulation & Bitstream Recovery
- Hypothesis Ranking & Evidence-Based Confidence Scoring
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import soundfile as sf
from scipy.signal import welch

from .signal_data import SignalData
from .signal_loader import load_wav, load_iq
from .timing import estimate_samples_per_symbol
from .synchronization import (
    estimate_frequency_offset,
    correct_frequency_offset,
    synchronize_psk,
    synchronize_qam,
    synchronize_fsk,
)
from .demodulation import (
    demodulate_bpsk,
    demodulate_qpsk,
    demodulate_16qam,
    demodulate_2fsk,
)
from .hypothesis import (
    build_hypothesis_report,
    analytic_signal,
)
from .frame import analyze_frame_hypotheses


# ============================================================
# FILE LOADING
# ============================================================

def load_signal_for_receiver(
    source: Union[str, Path, SignalData],
    sample_rate: Optional[float] = None,
    dtype: Any = np.int16,
    iq_order: str = "IQ",
) -> Dict[str, Any]:
    """
    Unified signal loader for receiver accepting:
    - SignalData object
    - Path to .wav file
    - Path to raw .iq / .bin / .raw file (requires sample_rate)
    """
    if isinstance(source, SignalData):
        sig_data = source
    else:
        path = Path(source)
        ext = path.suffix.lower()
        if ext == ".wav":
            sig_data = load_wav(path)
        elif ext in (".iq", ".bin", ".raw", ".dat") or sample_rate is not None:
            if sample_rate is None:
                raise ValueError("sample_rate must be specified when loading raw IQ files.")
            sig_data = load_iq(path, sample_rate=sample_rate, dtype=dtype, iq_order=iq_order)
        else:
            sig_data = load_wav(path)

    return {
        "samples": sig_data.samples,
        "sample_rate": int(sig_data.sample_rate),
        "num_samples": int(sig_data.num_samples),
        "duration_seconds": float(sig_data.duration or (sig_data.num_samples / sig_data.sample_rate)),
        "representation": sig_data.representation,
        "possible_iq": sig_data.possible_iq,
        "channel_correlation": sig_data.channel_correlation,
        "original_channels": sig_data.original_channels,
        "notes": sig_data.notes,
        "signal_data": sig_data,
        "filename": sig_data.filename,
    }


def load_wav_for_receiver(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a WAV file using the unified signal loader.
    Preserves channel interpretation (duplicate mono vs possible IQ).
    Delegates directly to load_signal_for_receiver.
    """
    return load_signal_for_receiver(path)


# ============================================================
# PREPROCESSING & CHARACTERIZATION
# ============================================================

def preprocess(samples: np.ndarray) -> np.ndarray:
    """
    Zero-mean and unit-power normalization.
    """
    samples = np.asarray(samples, dtype=np.complex64)
    if len(samples) == 0:
        return samples

    samples = samples - np.mean(samples)
    power = np.mean(np.abs(samples) ** 2)
    if power > 1e-12:
        samples = samples / np.sqrt(power)

    return samples.astype(np.complex64)


def representative_segment(
    samples: np.ndarray,
    sample_rate: float,
    seconds: float = 1.0,
    from_start: bool = True
) -> np.ndarray:
    """
    Extract a contiguous segment of bounded duration for efficient analysis.
    For packetized and burst transmissions, from_start=True preserves the critical
    initial preambles, sync words, and packet headers.
    """
    max_samples = int(sample_rate * seconds)
    if len(samples) <= max_samples:
        return samples

    if from_start:
        return samples[:max_samples]
    start = (len(samples) - max_samples) // 2
    return samples[start:start + max_samples]


def characterize(
    samples: np.ndarray,
    sample_rate: float
) -> Dict[str, float]:
    """
    Extract fundamental physical parameters: RMS, peak, DC, dominant frequency,
    and 99% occupied spectral bandwidth.
    """
    samples = np.asarray(samples, dtype=np.complex64)
    if len(samples) == 0:
        return {
            "rms": 0.0,
            "peak": 0.0,
            "dc": 0.0,
            "dominant_frequency_hz": 0.0,
            "occupied_bandwidth_hz": 0.0,
        }

    rms = float(np.sqrt(np.mean(np.abs(samples) ** 2)))
    peak = float(np.max(np.abs(samples)))
    dc = float(np.abs(np.mean(samples)))

    n = min(len(samples), 131072)
    x = samples[:n]

    frequencies, psd = welch(
        x,
        fs=sample_rate,
        nperseg=min(4096, n),
        return_onesided=False,
        scaling="density",
    )

    frequencies = np.fft.fftshift(frequencies)
    psd = np.fft.fftshift(psd)

    peak_index = int(np.argmax(psd))
    dominant_frequency = float(frequencies[peak_index])

    # 99% cumulative occupied power
    positive_power = np.maximum(psd, 0.0)
    total_power = np.sum(positive_power)

    if total_power > 1e-15:
        cum = np.cumsum(positive_power) / total_power
        low_idx = int(np.searchsorted(cum, 0.005))
        high_idx = int(np.searchsorted(cum, 0.995))
        low_idx = max(0, min(low_idx, len(frequencies) - 1))
        high_idx = max(0, min(high_idx, len(frequencies) - 1))
        occupied_bandwidth = float(abs(frequencies[high_idx] - frequencies[low_idx]))
    else:
        occupied_bandwidth = 0.0

    return {
        "rms": rms,
        "peak": peak,
        "dc": dc,
        "dominant_frequency_hz": dominant_frequency,
        "occupied_bandwidth_hz": occupied_bandwidth,
    }


# ============================================================
# EVIDENCE-BASED CONSTELLATION & MODULATION QUALITY
# ============================================================

def psk_quality(
    symbols: np.ndarray,
    order: int
) -> float:
    """
    Evidence-driven M-PSK quality evaluator.
    Evaluates:
    - Envelope constancy: CV = std(|s|) / mean(|s|) <= 0.25
    - Phase clustering at M angles
    - Balanced cluster occupancy across all M states
    - Residual distance to unit circle and constellation centers
    """
    symbols = np.asarray(symbols, dtype=np.complex64)
    if len(symbols) < 30:
        return 0.0

    # Power normalization
    power = np.mean(np.abs(symbols) ** 2)
    if power <= 1e-12:
        return 0.0
    x = symbols / np.sqrt(power)

    # 1. Envelope constancy test (PSK is constant envelope)
    amp = np.abs(x)
    amp_cv = float(np.std(amp) / (np.mean(amp) + 1e-12))
    envelope_score = max(0.0, 1.0 - amp_cv * 3.5)

    # 2. Phase clustering test via M-th power
    powered_mean = np.mean(x ** order)
    cluster_coherence = float(np.abs(powered_mean))

    # 3. Phase state distribution test
    if order == 2:
        # BPSK nominal angle is 0
        phase_offset = (np.angle(powered_mean) / 2.0 + np.pi / 2.0) % np.pi - np.pi / 2.0
        rotated = x * np.exp(-1j * phase_offset)

        # Points should lie on real axis with balanced positive and negative states
        pos = np.sum(np.real(rotated) > 0.3)
        neg = np.sum(np.real(rotated) < -0.3)
        total = len(rotated)
        balance = 2.0 * min(pos, neg) / max(1, pos + neg)
        imag_var = float(np.mean(np.imag(rotated) ** 2))
        compactness = max(0.0, 1.0 - imag_var / 0.15)
        score = envelope_score * cluster_coherence * compactness * balance
    elif order == 4:
        # QPSK nominal angle is pi (since (exp(j*pi/4))^4 = exp(j*pi) = -1)
        phi_base = (np.angle(powered_mean) - np.pi) / 4.0
        phase_offset = (phi_base + np.pi / 4.0) % (np.pi / 2.0) - np.pi / 4.0
        rotated = x * np.exp(-1j * phase_offset)

        ideal = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2.0)
        dists = np.min(np.abs(rotated[:, None] - ideal[None, :]), axis=1)
        var_est = float(np.mean(dists ** 2))
        compactness = max(0.0, 1.0 - var_est / 0.10)

        # Check occupancy across the 4 quadrants
        quads = [
            np.sum((np.real(rotated) > 0) & (np.imag(rotated) > 0)),
            np.sum((np.real(rotated) < 0) & (np.imag(rotated) > 0)),
            np.sum((np.real(rotated) < 0) & (np.imag(rotated) < 0)),
            np.sum((np.real(rotated) > 0) & (np.imag(rotated) < 0)),
        ]
        min_quad = min(quads) / len(rotated)
        balance = min(1.0, min_quad * 8.0)  # expect ~0.25 each
        score = envelope_score * cluster_coherence * compactness * balance
    else:
        score = 0.0

    return float(np.clip(score, 0.0, 1.0))


def qam16_quality(
    symbols: np.ndarray
) -> float:
    """
    Evidence-driven 16-QAM quality evaluator.
    Evaluates:
    1. Cluster compactness against 16 ideal normalized grid points.
    2. Cluster occupancy diversity & entropy (all 16 points must be visited).
    3. Fourth-moment alignment: E[|s|^4] / (E[|s|^2])^2 must match theoretical 1.32.
    """
    symbols = np.asarray(symbols, dtype=np.complex64)
    if len(symbols) < 50:
        return 0.0

    pwr = np.mean(np.abs(symbols) ** 2)
    if pwr <= 1e-12:
        return 0.0
    x = symbols / np.sqrt(pwr)

    # 1. 4th moment test: ideal 16-QAM has E[|s|^4] = 1.32.
    m4 = float(np.mean(np.abs(x) ** 4))
    if m4 < 1.10 or m4 > 1.70:
        return 0.0
    m4_score = float(np.exp(-((m4 - 1.32) / 0.25) ** 2))

    # 2. Grid distance and cluster assignment
    levels = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float32)
    reference = np.array([complex(i, q) for i in levels for q in levels], dtype=np.complex64) / np.sqrt(10.0)

    best_var = 1e9
    best_rot = x
    for angle in np.linspace(0.0, np.pi / 2.0, 24, endpoint=False):
        rot = x * np.exp(-1j * angle)
        dists = np.min(np.abs(rot[:, None] - reference[None, :]), axis=1)
        var_est = float(np.mean(dists ** 2))
        if var_est < best_var:
            best_var = var_est
            best_rot = rot

    # 3. Compactness score (uniform random spread gives var ~ 0.065)
    compactness = max(0.0, 1.0 - best_var / 0.050)
    if compactness <= 0.0:
        return 0.0

    # 4. Cluster occupancy and entropy
    dists = np.abs(best_rot[:, None] - reference[None, :])
    assignments = np.argmin(dists, axis=1)
    counts = np.bincount(assignments, minlength=16)
    probs = counts / len(symbols)
    occupied = np.sum(probs > 0.015)
    if occupied < 12:
        return 0.0

    entropy = -np.sum(probs[probs > 0] * np.log2(probs[probs > 0])) / np.log2(16.0)
    if entropy < 0.80:
        return 0.0

    score = compactness * (occupied / 16.0) * float(entropy) * m4_score
    return float(np.clip(score, 0.0, 1.0))


def fsk_quality(
    samples: np.ndarray,
    sample_rate: float,
    sps: int = 16,
    timing_offset: int = 0
) -> float:
    """
    Evidence-driven 2-FSK quality evaluator.
    Evaluates instantaneous frequency over the center half of symbols
    (avoiding transition boundary artifacts) to distinguish genuine FSK
    from PSK phase jumps.
    """
    samples = np.asarray(samples, dtype=np.complex64)
    sps = max(2, int(sps))
    available = len(samples) - timing_offset
    num_symbols = available // sps
    if num_symbols < 20:
        return 0.0

    # 1. Envelope constancy
    amp = np.abs(samples)
    amp_cv = float(np.std(amp) / (np.mean(amp) + 1e-12))
    envelope_score = max(0.0, 1.0 - amp_cv * 3.0)

    # 2. Symbol center instantaneous frequency
    margin = max(1, sps // 4)
    sym_freqs = []
    intra_stds = []
    for k in range(num_symbols):
        start = timing_offset + k * sps
        mid_blk = samples[start + margin:start + sps - margin]
        if len(mid_blk) < 2:
            mid_blk = samples[start:start + sps]
        dt = np.angle(mid_blk[1:] * np.conj(mid_blk[:-1]))
        sym_freqs.append(np.mean(dt) * sample_rate / (2.0 * np.pi))
        if len(dt) > 1:
            intra_stds.append(float(np.std(dt)))

    # Genuine FSK maintains a steady frequency tone within symbol center;
    # phase jumps (PSK transitions) create sharp intra-symbol variance spikes.
    if intra_stds and float(np.mean(intra_stds)) > 0.25:
        return 0.0

    sym_freqs = np.asarray(sym_freqs)
    f_low = float(np.percentile(sym_freqs, 20))
    f_high = float(np.percentile(sym_freqs, 80))
    sep = f_high - f_low

    symbol_rate = sample_rate / float(sps)
    nyquist = sample_rate / 2.0
    # Separation must respect physical modulation bounds:
    # 2 * Delta_f >= 0.35 * R_s (minimum orthogonal bound) and <= 0.85 * Nyquist
    if sep < max(50.0, 0.35 * symbol_rate) or sep > 0.85 * nyquist:
        return 0.0

    # State balance: symbols classified by midpoint
    mid = (f_low + f_high) / 2.0
    p1 = np.mean(sym_freqs < mid)
    p2 = np.mean(sym_freqs >= mid)
    balance = min(p1, p2) / max(p1, p2, 1e-12)

    # Compactness of the two states
    spread1 = float(np.std(sym_freqs[sym_freqs < mid])) if np.sum(sym_freqs < mid) > 2 else sep
    spread2 = float(np.std(sym_freqs[sym_freqs >= mid])) if np.sum(sym_freqs >= mid) > 2 else sep
    avg_spread = (spread1 + spread2) / 2.0
    compactness = max(0.0, min(1.0, (sep / max(avg_spread, 1e-6)) / 4.0))

    score = envelope_score * compactness * min(1.0, balance * 2.0)
    return float(np.clip(score, 0.0, 1.0))


# ============================================================
# HYPOTHESIS TESTING AT SYMBOL CANDIDATES
# ============================================================

def test_psk_hypothesis(
    samples: np.ndarray,
    sample_rate: float,
    sps: int,
    order: int
) -> Dict[str, Any]:
    modulation = "BPSK" if order == 2 else "QPSK"
    try:
        sync = synchronize_psk(samples, sample_rate, sps, order)
        quality = psk_quality(sync["symbols"], order)
        return {
            "modulation": modulation,
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": float(quality),
            "frequency_offset_hz": float(sync["frequency_offset_hz"]),
            "timing_offset": int(sync["timing_offset"]),
            "phase_offset_rad": float(sync["phase_offset_rad"]),
            "symbol_count": int(len(sync["symbols"])),
            "symbols": sync["symbols"],
        }
    except Exception as exc:
        return {
            "modulation": modulation,
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": 0.0,
            "error": str(exc),
        }


test_psk_hypothesis.__test__ = False


def test_qam_hypothesis(
    samples: np.ndarray,
    sample_rate: float,
    sps: int
) -> Dict[str, Any]:
    try:
        sync = synchronize_qam(samples, sample_rate, sps, order=16)
        quality = qam16_quality(sync["symbols"])
        return {
            "modulation": "16-QAM",
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": float(quality),
            "frequency_offset_hz": float(sync["frequency_offset_hz"]),
            "timing_offset": int(sync["timing_offset"]),
            "phase_offset_rad": float(sync["phase_offset_rad"]),
            "symbol_count": int(len(sync["symbols"])),
            "symbols": sync["symbols"],
        }
    except Exception as exc:
        return {
            "modulation": "16-QAM",
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": 0.0,
            "error": str(exc),
        }


test_qam_hypothesis.__test__ = False


def test_fsk_hypothesis(
    samples: np.ndarray,
    sample_rate: float,
    sps: int
) -> Dict[str, Any]:
    try:
        sync = synchronize_fsk(samples, sample_rate, sps)
        quality = fsk_quality(
            sync["frequency_corrected_signal"],
            sample_rate,
            sps,
            sync["timing_offset"],
        )
        return {
            "modulation": "2-FSK",
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": float(quality),
            "frequency_offset_hz": float(sync["frequency_offset_hz"]),
            "timing_offset": int(sync["timing_offset"]),
            "phase_offset_rad": 0.0,
            "symbol_count": int(len(sync["symbols"])),
            "symbols": sync["symbols"],
            "frequency_corrected_signal": sync["frequency_corrected_signal"],
        }
    except Exception as exc:
        return {
            "modulation": "2-FSK",
            "samples_per_symbol": int(sps),
            "symbol_rate_hz": float(sample_rate / sps),
            "score": 0.0,
            "error": str(exc),
        }


test_fsk_hypothesis.__test__ = False


# ============================================================
# MAIN RECEIVER ORCHESTRATOR
# ============================================================

def analyze_signal(
    path: Union[str, Path, SignalData],
    max_segment_seconds: float = 0.5,
    max_sps_candidates: int = 5,
    sample_rate: Optional[float] = None,
    dtype: Any = np.int16,
    iq_order: str = "IQ",
) -> Dict[str, Any]:
    """
    Automated signal analysis and progressive recovery pipeline.
    Accepts path to WAV file, path to raw IQ file (with sample_rate), or SignalData object.
    """
    t_start = time.perf_counter()
    file_info = load_signal_for_receiver(
        path,
        sample_rate=sample_rate,
        dtype=dtype,
        iq_order=iq_order,
    )
    t_ingest = time.perf_counter() - t_start

    fs = file_info["sample_rate"]
    raw_samples = file_info["samples"]

    if isinstance(path, SignalData):
        file_name = path.filename or "in_memory"
        file_path = "in_memory"
    else:
        file_name = Path(path).name
        file_path = str(Path(path).resolve())

    # Preprocessing
    t_char_start = time.perf_counter()
    samples = preprocess(raw_samples)
    segment = representative_segment(samples, fs, max_segment_seconds)

    # 1. Digital Signal Gate
    hypothesis_report = build_hypothesis_report(
        segment,
        fs,
        representation=file_info["representation"]
    )
    characterization = characterize(segment, fs)
    t_char = time.perf_counter() - t_char_start

    # Check for early tone/noise rejection
    gate_decision = hypothesis_report.get("screen", {}).get("decision", "AMBIGUOUS")
    gate_reason = hypothesis_report.get("screen", {}).get("reason", "")

    if gate_decision in ("NON_DIGITAL_LIKELY", "INSUFFICIENT_DATA"):
        best_hypothesis = {
            "modulation": "UNKNOWN",
            "samples_per_symbol": None,
            "symbol_rate_hz": None,
            "score": 0.0,
            "confidence": 0.0,
            "status": gate_decision,
            "reason": gate_reason or "Non-digital or pure tone signal rejected by screen.",
        }
        t_total = time.perf_counter() - t_start
        return {
            "file": file_name,
            "path": file_path,
            "sample_rate_hz": fs,
            "num_samples": file_info["num_samples"],
            "duration_seconds": file_info["duration_seconds"],
            "representation": file_info["representation"],
            "possible_iq": file_info["possible_iq"],
            "channel_correlation": file_info["channel_correlation"],
            "characterization": characterization,
            "hypothesis_report": hypothesis_report,
            "timing_candidates": [],
            "tested_sps": [],
            "modulation_hypotheses": [],
            "best_hypothesis": best_hypothesis,
            "modulation": "UNKNOWN",
            "samples_per_symbol": None,
            "symbol_rate_hz": None,
            "cfo_est_hz": None,
            "confidence": 0.0,
            "status": "NON_DIGITAL_REJECTED",
            "decoding": {
                "demodulation_status": "NOT_RUN",
                "recovered_bits_count": 0,
                "deinterleaving_status": "NOT_RUN",
                "fec_status": "NOT_RUN",
                "correlation_status": "NOT_RUN",
            },
            "execution_times": {
                "ingestion_time_seconds": round(t_ingest, 4),
                "characterization_time_seconds": round(t_char, 4),
                "modulation_inference_time_seconds": 0.0,
                "demodulation_time_seconds": 0.0,
                "decoding_time_seconds": 0.0,
                "total_time_seconds": round(t_total, 4),
            },
            "recovered_bits": None,
            "bitstream": None,
        }

    # 2. Timing Recovery
    t_mod_start = time.perf_counter()
    eval_signal = segment.astype(np.complex64)
    timing_candidates = estimate_samples_per_symbol(
        eval_signal,
        fs,
        min_symbol_rate=max(50.0, fs / 128.0),
        max_symbol_rate=fs / 2.0,
    )

    sps_values = []
    for cand in timing_candidates:
        val = int(round(cand["samples_per_symbol"]))
        if val >= 2 and val not in sps_values:
            sps_values.append(val)
        if len(sps_values) >= max_sps_candidates:
            break

    # Add standard fallback candidates
    for fb in [4, 8, 16]:
        if fb not in sps_values:
            sps_values.append(fb)
        if len(sps_values) >= max_sps_candidates + 2:
            break

    # 3. Test Modulation Hypotheses at Candidate SPS
    hypotheses = []
    for sps in sps_values:
        hypotheses.append(test_psk_hypothesis(eval_signal, fs, sps, order=2))
        hypotheses.append(test_psk_hypothesis(eval_signal, fs, sps, order=4))
        hypotheses.append(test_qam_hypothesis(eval_signal, fs, sps))
        hypotheses.append(test_fsk_hypothesis(eval_signal, fs, sps))

    # Rank modulation hypotheses by raw quality score
    hypotheses.sort(key=lambda h: h.get("score", 0.0), reverse=True)
    t_mod = time.perf_counter() - t_mod_start

    # 4. Cross-Stage Hypothesis Ranking (Modulation + Sync + Deinterleaving + FEC)
    # Collect viable candidates (quality score >= 0.40) for downstream cross-stage validation
    viable_candidates = [h for h in hypotheses if h.get("score", 0.0) >= 0.40][:6]

    t_demod_total = 0.0
    t_decode_total = 0.0
    cross_stage_evaluations = []
    for cand in viable_candidates:
        c_mod = cand["modulation"]
        c_sps = cand["samples_per_symbol"]
        c_mscore = float(cand.get("score", 0.0))

        t_demod_cand_start = time.perf_counter()
        c_bits = None
        try:
            if c_mod == "BPSK":
                c_bits = demodulate_bpsk(cand["symbols"], samples_per_symbol=1, timing_offset=0, phase_offset=0.0)
            elif c_mod == "QPSK":
                c_bits = demodulate_qpsk(cand["symbols"], samples_per_symbol=1, timing_offset=0, phase_offset=0.0)
            elif c_mod == "16-QAM":
                c_bits = demodulate_16qam(cand["symbols"], samples_per_symbol=1, timing_offset=0, phase_offset=0.0)
            elif c_mod == "2-FSK":
                c_bits = demodulate_2fsk(
                    cand.get("frequency_corrected_signal", eval_signal),
                    sample_rate=fs,
                    samples_per_symbol=c_sps,
                    timing_offset=cand.get("timing_offset", 0),
                    frequency_threshold=0.0
                )
        except Exception:
            c_bits = None
        t_demod_total += (time.perf_counter() - t_demod_cand_start)

        t_dec_cand_start = time.perf_counter()
        if c_bits is not None and len(c_bits) >= 16:
            f_rep = analyze_frame_hypotheses(c_bits, modulation=c_mod)
        else:
            f_rep = analyze_frame_hypotheses(np.array([], dtype=np.uint8), modulation=c_mod)
        t_decode_total += (time.perf_counter() - t_dec_cand_start)

        b_dec = f_rep.get("best_decoding_hypothesis", {})
        p_match = f_rep.get("preamble")
        p_len = p_match.get("pattern_length", 0) if p_match else 0
        p_score = (float(p_match.get("score", 0.0)) * min(1.0, float(p_len) / 16.0)) if p_match else 0.0
        fec_valid = bool(b_dec.get("fec_valid", False))
        fec_score = float(b_dec.get("overall_score", 0.0))

        # Composite Scoring across Modulation, Preamble, and FEC
        if fec_valid and p_len >= 16:
            cross_score = 0.30 * c_mscore + 0.35 * p_score + 0.35 * fec_score + 0.30
            conf = float(np.clip(0.85 + 0.15 * c_mscore, 0.0, 1.0))
            tier = "HIGH CONFIDENCE"
            why_sel = (
                f"Full cross-stage validation: {c_mod} (SPS={c_sps}), {p_match.get('pattern_type')} "
                f"preamble match ({p_len} bits, PSR > 4.0), and {b_dec.get('fec')} zero-syndrome check."
            )
        elif fec_valid:
            cross_score = 0.35 * c_mscore + 0.40 * fec_score + 0.25
            conf = float(np.clip(0.70 + 0.15 * c_mscore, 0.0, 0.84))
            tier = "MEDIUM CONFIDENCE"
            why_sel = f"FEC validated ({b_dec.get('fec')}) on {c_mod} (SPS={c_sps}), but preamble partial or unconfirmed."
        elif p_len >= 16 and p_score >= 0.90:
            cross_score = 0.45 * c_mscore + 0.45 * p_score + 0.10
            conf = float(np.clip(0.60 + 0.20 * c_mscore, 0.0, 0.84))
            tier = "MEDIUM CONFIDENCE"
            why_sel = f"Frame preamble confirmed ({p_match.get('pattern_type')}) on {c_mod} (SPS={c_sps}), but FEC unconfirmed."
        elif c_mscore >= 0.55:
            cross_score = c_mscore * 0.60
            conf = float(np.clip(c_mscore * 0.70, 0.0, 0.75))
            tier = "MEDIUM CONFIDENCE" if conf >= 0.50 else "INSUFFICIENT_EVIDENCE"
            why_sel = f"Constellation clustering meets threshold for {c_mod} (SPS={c_sps}), downstream sync/FEC unconfirmed."
        else:
            cross_score = c_mscore * 0.30
            conf = 0.0
            tier = "INSUFFICIENT_EVIDENCE"
            why_sel = f"Weak evidence for {c_mod} (SPS={c_sps})."

        cross_stage_evaluations.append({
            "modulation_hypothesis": cand,
            "modulation": c_mod,
            "samples_per_symbol": c_sps,
            "symbol_rate_hz": cand.get("symbol_rate_hz"),
            "score": c_mscore,
            "cross_score": float(np.clip(cross_score, 0.0, 2.0)),
            "confidence": conf,
            "confidence_tier": tier,
            "why_selected": why_sel,
            "recovered_bits": c_bits,
            "frame_report": f_rep,
            "best_decoding": b_dec,
            "fec_valid": fec_valid,
            "preamble_len": p_len,
        })

    # Sort cross-stage candidates descending by overall cross_score
    cross_stage_evaluations.sort(key=lambda e: e["cross_score"], reverse=True)
    top_eval = cross_stage_evaluations[0] if cross_stage_evaluations else None

    # Decision Gate: Accept candidate only if confidence >= 0.50 or raw modulation score >= 0.55
    if top_eval is not None and (top_eval["confidence"] >= 0.50 or top_eval["score"] >= 0.55):
        top_cand = top_eval["modulation_hypothesis"]
        best_mod = top_eval["modulation"]
        best_sps = top_eval["samples_per_symbol"]
        best_score = top_eval["score"]
        confidence = top_eval["confidence"]
        status = "ANALYSIS_COMPLETE"

        # Build explainability: Why selected & Alternatives tested
        why_selected = top_eval["why_selected"]
        alternatives_tested = []
        for alt in cross_stage_evaluations[1:]:
            alt_mod = alt["modulation"]
            alt_sps = alt["samples_per_symbol"]
            alt_score = alt["score"]
            if top_eval["fec_valid"] and not alt["fec_valid"]:
                rej = f"Rejected: Failed downstream FEC syndrome check (score={alt['cross_score']:.2f})."
            elif top_eval["preamble_len"] >= 16 and alt["preamble_len"] < 16:
                rej = f"Rejected: No validated frame preamble (pattern length < 16)."
            else:
                rej = f"Rejected: Lower composite score ({alt['cross_score']:.2f} vs {top_eval['cross_score']:.2f})."
            alternatives_tested.append({
                "candidate": f"{alt_mod} (SPS={alt_sps})",
                "cross_score": alt["cross_score"],
                "modulation_score": alt_score,
                "rejection_reason": rej,
            })

        best_hypothesis = {
            "modulation": best_mod,
            "samples_per_symbol": best_sps,
            "symbol_rate_hz": top_cand.get("symbol_rate_hz"),
            "score": best_score,
            "cross_score": top_eval["cross_score"],
            "confidence": confidence,
            "confidence_tier": top_eval["confidence_tier"],
            "frequency_offset_hz": top_cand.get("frequency_offset_hz"),
            "timing_offset": top_cand.get("timing_offset"),
            "phase_offset_rad": top_cand.get("phase_offset_rad", 0.0),
            "status": status,
            "why_selected": why_selected,
            "alternatives_tested": alternatives_tested,
            "reason": why_selected,
        }

        recovered_bits = top_eval["recovered_bits"]
        frame_report = top_eval["frame_report"]
        best_decoding = top_eval["best_decoding"]

        decoding = {
            "demodulation": {
                "status": "VALIDATED" if recovered_bits is not None else "FAILED",
                "modulation": best_mod,
                "recovered_bits_count": int(len(recovered_bits)) if recovered_bits is not None else 0,
                "samples_per_symbol": best_sps,
                "symbol_rate_hz": top_cand.get("symbol_rate_hz"),
            },
            "correlation": {
                "status": "VALIDATED" if frame_report.get("preamble") else "NO_KNOWN_PREAMBLE",
                "preamble": frame_report.get("preamble"),
                "frame_structure": frame_report.get("frame_structure"),
            },
            "interleaving": {
                "status": "VALIDATED" if best_decoding.get("interleaver") not in ("none", "UNKNOWN") and best_decoding.get("status") == "VALIDATED" else "HYPOTHESIS_RANKED",
                "best_hypothesis": best_decoding.get("interleaver", "UNKNOWN"),
                "parameters": best_decoding.get("interleaver_params", {}),
            },
            "fec": {
                "status": "VALIDATED" if best_decoding.get("fec_valid") else "HYPOTHESIS_RANKED",
                "best_hypothesis": best_decoding.get("fec", "none"),
                "parameters": best_decoding.get("fec_params", {}),
                "fec_valid": best_decoding.get("fec_valid", False),
            },
            "frame": {
                "status": best_decoding.get("status", "HYPOTHESIS"),
                "overall_score": float(best_decoding.get("overall_score", 0.0)),
                "candidates": [
                    {k: v for k, v in c.items() if k != "decoded_bits"}
                    for c in frame_report.get("candidates", [])[:5]
                ],
                "decoded_bits": best_decoding.get("decoded_bits"),
            },
            # Flat compatibility keys
            "demodulation_status": "VALIDATED" if recovered_bits is not None else "FAILED",
            "recovered_bits_count": int(len(recovered_bits)) if recovered_bits is not None else 0,
            "deinterleaving_status": "VALIDATED" if best_decoding.get("status") == "VALIDATED" else "HYPOTHESIS_RANKED",
            "fec_status": "VALIDATED" if best_decoding.get("fec_valid") else "HYPOTHESIS_RANKED",
            "correlation_status": "VALIDATED" if frame_report.get("preamble") else "NO_KNOWN_PREAMBLE",
        }

        evidence_profile = {
            "modulation_evidence": {
                "modulation": best_mod,
                "quality_score": best_score,
                "cross_score": top_eval["cross_score"],
            },
            "timing_evidence": {
                "samples_per_symbol": best_sps,
                "symbol_rate_hz": top_cand.get("symbol_rate_hz"),
                "timing_offset": top_cand.get("timing_offset"),
            },
            "synchronization_residual": {
                "frequency_offset_hz": top_cand.get("frequency_offset_hz"),
                "phase_offset_rad": top_cand.get("phase_offset_rad", 0.0),
            },
            "correlation_evidence": {
                "preamble_found": frame_report.get("preamble") is not None,
                "preamble_type": frame_report.get("preamble", {}).get("pattern_type") if frame_report.get("preamble") else None,
                "preamble_score": frame_report.get("preamble", {}).get("score", 0.0) if frame_report.get("preamble") else 0.0,
            },
            "interleaver_evidence": {
                "best_type": best_decoding.get("interleaver"),
                "status": best_decoding.get("status"),
            },
            "fec_evidence": {
                "best_type": best_decoding.get("fec"),
                "fec_valid": best_decoding.get("fec_valid", False),
            },
        }
    else:
        recovered_bits = None
        confidence = 0.0
        best_hypothesis = {
            "modulation": "UNKNOWN",
            "samples_per_symbol": None,
            "symbol_rate_hz": None,
            "score": float(top_eval["score"]) if top_eval else (float(hypotheses[0]["score"]) if hypotheses else 0.0),
            "confidence": 0.0,
            "confidence_tier": "INSUFFICIENT_EVIDENCE",
            "status": "INSUFFICIENT_EVIDENCE",
            "why_selected": "None: Insufficient evidence to validate digital communication hypothesis.",
            "alternatives_tested": [
                {
                    "candidate": f"{h['modulation']} (SPS={h['samples_per_symbol']})",
                    "score": float(h.get("score", 0.0)),
                    "rejection_reason": "Score below digital modulation threshold (0.55) and no protocol structure found.",
                }
                for h in hypotheses[:5]
            ],
            "reason": "Signal features and cluster compactness do not meet thresholds for supported digital modulations.",
        }
        decoding = {
            "demodulation": {"status": "NOT_RUN", "recovered_bits_count": 0},
            "interleaving": {"status": "NOT_RUN"},
            "fec": {"status": "NOT_RUN"},
            "correlation": {"status": "NOT_RUN"},
            "frame": {"status": "NOT_RUN", "candidates": []},
            "demodulation_status": "NOT_RUN",
            "recovered_bits_count": 0,
            "deinterleaving_status": "NOT_RUN",
            "fec_status": "NOT_RUN",
            "correlation_status": "NOT_RUN",
        }
        evidence_profile = {
            "modulation_evidence": {"modulation": "UNKNOWN", "quality_score": 0.0},
            "timing_evidence": {},
            "synchronization_residual": {},
            "correlation_evidence": {"preamble_found": False},
            "interleaver_evidence": {},
            "fec_evidence": {},
        }

    t_total = time.perf_counter() - t_start

    return {
        "file": file_name,
        "path": file_path,
        "sample_rate_hz": fs,
        "num_samples": file_info["num_samples"],
        "duration_seconds": file_info["duration_seconds"],
        "representation": file_info["representation"],
        "possible_iq": file_info["possible_iq"],
        "channel_correlation": file_info["channel_correlation"],
        "characterization": characterization,
        "timing_candidates": timing_candidates[:10],
        "tested_sps": sps_values,
        "modulation_hypotheses": [
            {k: v for k, v in h.items() if k not in ("symbols", "frequency_corrected_signal")}
            for h in hypotheses[:10]
        ],
        "best_hypothesis": best_hypothesis,
        "modulation": best_hypothesis["modulation"],
        "samples_per_symbol": best_hypothesis.get("samples_per_symbol"),
        "symbol_rate_hz": best_hypothesis.get("symbol_rate_hz"),
        "cfo_est_hz": best_hypothesis.get("frequency_offset_hz"),
        "confidence": confidence,
        "evidence_profile": evidence_profile,
        "status": best_hypothesis["status"],
        "decoding": decoding,
        "execution_times": {
            "ingestion_time_seconds": round(t_ingest, 4),
            "characterization_time_seconds": round(t_char, 4),
            "modulation_inference_time_seconds": round(t_mod, 4),
            "demodulation_time_seconds": round(t_demod_total, 4),
            "decoding_time_seconds": round(t_decode_total, 4),
            "total_time_seconds": round(t_total, 4),
        },
        "recovered_bits": recovered_bits,
        "bitstream": "".join(str(int(b)) for b in recovered_bits) if recovered_bits is not None else None,
    }


# ============================================================
# EXPORT HELPERS
# ============================================================

def save_result_json(result: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """
    Save complete analysis result to JSON file with numpy serialization.
    """
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=2,
            default=lambda obj: (
                obj.tolist() if isinstance(obj, np.ndarray)
                else obj.item() if isinstance(obj, np.generic)
                else str(obj)
            )
        )


def summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return small UI-friendly summary dictionary.
    """
    best = result.get("best_hypothesis") or {}
    return {
        "file": result.get("file", "unknown"),
        "sample_rate_hz": result.get("sample_rate_hz"),
        "representation": result.get("representation"),
        "digital_status": best.get("status", "UNKNOWN"),
        "modulation": best.get("modulation", "UNKNOWN"),
        "samples_per_symbol": best.get("samples_per_symbol"),
        "symbol_rate_hz": best.get("symbol_rate_hz"),
        "confidence": result.get("confidence", 0.0),
    }