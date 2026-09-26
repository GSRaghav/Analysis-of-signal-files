"""
End-to-End Blind Decoding Scorecard Test Suite (AutoSig-Intel Phase 5).

Verifies that AutoSig-Intel can automatically infer, select, and validate
the entire decoding path for unknown signals without metadata hints:
  MODULATION -> SPS -> SYNC -> DEMODULATION -> DE-INTERLEAVING -> FEC -> BITSTREAM CORRELATION -> PAYLOAD

Tests:
1. Capture A: BPSK + Block Interleaver + Viterbi (NASA K=7) + CCSDS_ASM
2. Capture B: QPSK + Diagonal Interleaver + Reed-Solomon + CCSDS_ASM
3. Capture C: QPSK + Pseudo-Random Interleaver + Viterbi (K=3) + CCSDS_ASM
4. Capture D: 16-QAM + Block Interleaver + Concatenated/RS + SYNC_AA55
5. Capture E: 2-FSK + Convolutional Interleaver + Viterbi (K=7) + SYNC_AA55
6. Negative Cases: Pure Sine, Two-Tone, Gaussian Noise (Must return UNKNOWN / 0.0 confidence)
7. Damaged Cases: Severely truncated capture, high CFO stress
"""

import json
from pathlib import Path
import numpy as np
import pytest

from core.receiver import analyze_signal
from core.signal_data import SignalData


SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "samples" / "synthetic"


def _require_file(filename: str) -> Path:
    p = SYNTHETIC_DIR / filename
    if not p.exists():
        pytest.skip(f"Synthetic capture file {filename} not found.")
    return p


# ============================================================
# 1. BLIND DECODING SCORECARD TESTS
# ============================================================

def test_blind_capture_a_bpsk():
    """Blind evaluation of Capture A: BPSK + Block + Viterbi K=7."""
    path = _require_file("capture_a_bpsk.wav")
    result = analyze_signal(path)

    best = result["best_hypothesis"]
    dec = result["decoding"]
    corr = dec["correlation"]
    inter = dec["interleaving"]
    fec = dec["fec"]

    assert best["modulation"] == "BPSK", f"Expected BPSK, got {best['modulation']}"
    assert best["samples_per_symbol"] == 8, f"Expected SPS=8, got {best['samples_per_symbol']}"
    assert corr["status"] == "VALIDATED", "Preamble must be validated"
    assert corr["preamble"]["pattern_type"] == "CCSDS_ASM", "Expected CCSDS_ASM preamble"
    assert inter["best_hypothesis"] == "block", f"Expected block interleaver, got {inter['best_hypothesis']}"
    assert fec["fec_valid"] is True, "FEC syndrome check must validate"
    assert "viterbi_k7" in fec["best_hypothesis"], f"Expected Viterbi K=7, got {fec['best_hypothesis']}"
    assert result["confidence"] >= 0.85, f"Expected HIGH CONFIDENCE (>=0.85), got {result['confidence']}"
    assert len(best.get("why_selected", "")) > 0, "Must provide why_selected reasoning"
    assert len(best.get("alternatives_tested", [])) > 0, "Must provide alternatives_tested list"


def test_blind_capture_b_qpsk():
    """Blind evaluation of Capture B: QPSK + Diagonal + Reed-Solomon."""
    path = _require_file("capture_b_qpsk.wav")
    result = analyze_signal(path)

    best = result["best_hypothesis"]
    dec = result["decoding"]
    corr = dec["correlation"]
    inter = dec["interleaving"]
    fec = dec["fec"]

    assert best["modulation"] == "QPSK", f"Expected QPSK, got {best['modulation']}"
    assert best["samples_per_symbol"] == 8, f"Expected SPS=8, got {best['samples_per_symbol']}"
    assert corr["status"] == "VALIDATED", "Preamble must be validated"
    assert corr["preamble"]["pattern_type"] == "CCSDS_ASM", "Expected CCSDS_ASM preamble"
    assert inter["best_hypothesis"] == "diagonal", f"Expected diagonal interleaver, got {inter['best_hypothesis']}"
    assert fec["fec_valid"] is True, "FEC syndrome check must validate"
    assert "reed_solomon" in fec["best_hypothesis"], f"Expected Reed-Solomon, got {fec['best_hypothesis']}"
    assert result["confidence"] >= 0.85, f"Expected HIGH CONFIDENCE (>=0.85), got {result['confidence']}"


def test_blind_capture_c_qpsk():
    """Blind evaluation of Capture C: QPSK + Pseudo-Random + Viterbi K=3."""
    path = _require_file("capture_c_qpsk.wav")
    result = analyze_signal(path)

    best = result["best_hypothesis"]
    dec = result["decoding"]
    corr = dec["correlation"]
    inter = dec["interleaving"]
    fec = dec["fec"]

    assert best["modulation"] == "QPSK", f"Expected QPSK, got {best['modulation']}"
    assert best["samples_per_symbol"] == 8, f"Expected SPS=8, got {best['samples_per_symbol']}"
    assert corr["status"] == "VALIDATED", "Preamble must be validated"
    assert corr["preamble"]["pattern_type"] == "CCSDS_ASM", "Expected CCSDS_ASM preamble"
    assert inter["best_hypothesis"] == "pseudo_random", f"Expected pseudo_random interleaver, got {inter['best_hypothesis']}"
    assert fec["fec_valid"] is True, "FEC syndrome check must validate"
    assert "viterbi_k3" in fec["best_hypothesis"], f"Expected Viterbi K=3, got {fec['best_hypothesis']}"
    assert result["confidence"] >= 0.85, f"Expected HIGH CONFIDENCE (>=0.85), got {result['confidence']}"


def test_blind_capture_d_16qam():
    """Blind evaluation of Capture D: 16-QAM + Block + Concatenated/RS."""
    path = _require_file("capture_d_16qam.wav")
    result = analyze_signal(path)

    best = result["best_hypothesis"]
    dec = result["decoding"]
    corr = dec["correlation"]
    inter = dec["interleaving"]
    fec = dec["fec"]

    assert best["modulation"] == "16-QAM", f"Expected 16-QAM, got {best['modulation']}"
    assert corr["status"] == "VALIDATED", "Preamble must be validated"
    assert corr["preamble"]["pattern_type"] == "SYNC_AA55", "Expected SYNC_AA55 preamble"
    assert inter["best_hypothesis"] == "block", f"Expected block interleaver, got {inter['best_hypothesis']}"
    assert fec["fec_valid"] is True, "FEC syndrome check must validate"
    assert result["confidence"] >= 0.85, f"Expected HIGH CONFIDENCE (>=0.85), got {result['confidence']}"


def test_blind_capture_e_2fsk():
    """Blind evaluation of Capture E: 2-FSK + Convolutional + Viterbi K=7."""
    path = _require_file("capture_e_2fsk.wav")
    result = analyze_signal(path)

    best = result["best_hypothesis"]
    dec = result["decoding"]
    corr = dec["correlation"]
    inter = dec["interleaving"]
    fec = dec["fec"]

    assert best["modulation"] == "2-FSK", f"Expected 2-FSK, got {best['modulation']}"
    assert best["samples_per_symbol"] == 16, f"Expected SPS=16, got {best['samples_per_symbol']}"
    assert corr["status"] == "VALIDATED", "Preamble must be validated"
    assert corr["preamble"]["pattern_type"] == "SYNC_AA55", "Expected SYNC_AA55 preamble"
    assert inter["best_hypothesis"] == "convolutional", f"Expected convolutional interleaver, got {inter['best_hypothesis']}"
    assert fec["fec_valid"] is True, "FEC syndrome check must validate"
    assert "viterbi_k7" in fec["best_hypothesis"], f"Expected Viterbi K=7, got {fec['best_hypothesis']}"
    assert result["confidence"] >= 0.85, f"Expected HIGH CONFIDENCE (>=0.85), got {result['confidence']}"


# ============================================================
# 2. NEGATIVE TESTS (Pure Tones, Speech, Noise)
# ============================================================

def test_negative_pure_sine():
    """Pure sine wave tone must be rejected as non-digital with 0.0 confidence."""
    path = _require_file("negative_pure_sine.wav")
    result = analyze_signal(path)

    assert result["status"] in ("NON_DIGITAL_REJECTED", "UNKNOWN", "INSUFFICIENT_EVIDENCE")
    assert result["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert result["confidence"] == 0.0
    assert result["decoding"]["demodulation_status"] in ("NOT_RUN", "FAILED")


def test_negative_two_tone():
    """Dual-tone signal must be rejected as non-digital with 0.0 confidence."""
    path = _require_file("negative_two_tone.wav")
    result = analyze_signal(path)

    assert result["status"] in ("NON_DIGITAL_REJECTED", "UNKNOWN", "INSUFFICIENT_EVIDENCE")
    assert result["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert result["confidence"] == 0.0


def test_negative_gaussian_noise():
    """Gaussian noise must return INSUFFICIENT_EVIDENCE with 0.0 confidence."""
    path = _require_file("negative_gaussian_noise.wav")
    result = analyze_signal(path)

    assert result["status"] in ("INSUFFICIENT_EVIDENCE", "UNKNOWN", "NON_DIGITAL_REJECTED")
    assert result["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert result["confidence"] == 0.0


# ============================================================
# 3. DAMAGED CAPTURE ROBUSTNESS TESTS
# ============================================================

def test_damaged_capture_truncated():
    """Receiver must gracefully handle heavily truncated signals."""
    sig_data = SignalData(
        samples=np.random.randn(300).astype(np.float32) + 1j * np.random.randn(300).astype(np.float32),
        sample_rate=48000.0,
        source_type="IQ",
        filename="truncated_test.iq",
    )
    result = analyze_signal(sig_data)
    assert result is not None
    assert result["confidence"] == 0.0
    assert result["best_hypothesis"]["modulation"] == "UNKNOWN"


def test_damaged_capture_extreme_cfo():
    """Receiver must gracefully handle signals with extreme uncorrected frequency offset."""
    t = np.arange(1000) / 48000.0
    huge_cfo_tone = np.exp(1j * 2 * np.pi * 18000.0 * t).astype(np.complex64)
    sig_data = SignalData(
        samples=huge_cfo_tone,
        sample_rate=48000.0,
        source_type="IQ",
        filename="extreme_cfo_test.iq",
    )
    result = analyze_signal(sig_data)
    assert result is not None
    assert result["confidence"] == 0.0
