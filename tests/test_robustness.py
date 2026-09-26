"""
Phase 3 Robustness Validation and Receiver-Quality Test Suite.
Covers:
- Phase 3A: Independent Synthetic Matrix (BPSK, QPSK, 16-QAM, 2-FSK across SNR, CFO, Phase, Timing)
- Phase 3B: Modulation Classifier Stress Test & Confusion Matrix (12 signal types)
- Phase 3C: 4th-Moment Mathematical Verification (Theory vs Empirical)
- Phase 3D: FSK Physics across Modulation Indices & Nyquist Bound
- Phase 3E: Carrier & Timing Synchronization Stress & Capture Range
"""

from pathlib import Path
import numpy as np
import pytest
from scipy.signal import butter, sosfilt

from core.signal_data import SignalData
from core.reference_signals import (
    generate_bpsk,
    generate_qpsk,
    generate_16qam,
    generate_2fsk,
)
from core.synchronization import (
    apply_frequency_offset,
    apply_phase_offset,
    add_awgn,
    synchronize_psk,
    synchronize_qam,
    synchronize_fsk,
    _estimate_cfo_mth_power,
)
from core.demodulation import (
    demodulate_bpsk,
    demodulate_qpsk,
    demodulate_16qam,
    demodulate_2fsk,
    calculate_ber,
)
from core.receiver import (
    analyze_signal,
    test_fsk_hypothesis as evaluate_fsk_hypothesis,
    fsk_quality,
)


def _resolve_rotational_ambiguity_ber(bits, symbols, demod_fn, order=4):
    """
    Evaluate BER accounting for standard M-fold rotational symmetry in blind sync.
    For BPSK (order 2): rotations k * pi (k in {0, 1})
    For QPSK / 16QAM (order 4): rotations k * pi/2 (k in {0, 1, 2, 3})
    """
    n_rot = 2 if order == 2 else 4
    angle_step = np.pi if order == 2 else (np.pi / 2.0)
    best_ber = 1.0
    for k in range(n_rot):
        rot_syms = symbols * np.exp(-1j * k * angle_step)
        rec = demod_fn(rot_syms, 1, 0, 0)[:len(bits)]
        ber = calculate_ber(bits, rec)
        if ber < best_ber:
            best_ber = ber
    return best_ber


# ============================================================
# PHASE 3A: INDEPENDENT SYNTHETIC VALIDATION MATRIX
# ============================================================

@pytest.mark.parametrize("snr", [30, 20, 15, 10, 5])
@pytest.mark.parametrize("cfo", [0.0, 25.0, -50.0, 100.0])
def test_phase3a_bpsk_robustness(snr, cfo):
    np.random.seed(42)
    sps = 8
    fs = 8000.0
    sig, bits, _ = generate_bpsk(num_symbols=1500, samples_per_symbol=sps, noise_std=0.0, sample_rate=int(fs))
    
    # Test with timing offset and carrier phase
    timing_offset = 2
    delayed = np.concatenate([np.zeros(timing_offset, dtype=sig.dtype), sig])
    impaired = apply_frequency_offset(delayed, fs, cfo)
    impaired = apply_phase_offset(impaired, np.deg2rad(30.0))
    impaired = add_awgn(impaired, snr)

    sync = synchronize_psk(impaired, fs, sps, order=2)
    ber = _resolve_rotational_ambiguity_ber(bits, sync["symbols"], demodulate_bpsk, order=2)

    if snr >= 20:
        assert ber < 0.01, f"BPSK at SNR {snr} dB, CFO {cfo} Hz failed: BER={ber}"
    elif snr == 15:
        assert ber < 0.10, f"BPSK at SNR 15 dB failed: BER={ber}"
    else:
        # Graceful degradation at <= 10 dB: BER is bounded, receiver does not crash
        assert ber < 0.35, f"BPSK severe degradation at SNR {snr} dB: BER={ber}"


@pytest.mark.parametrize("snr", [30, 20, 15, 10, 5])
@pytest.mark.parametrize("cfo", [0.0, 25.0, -50.0, 100.0])
def test_phase3a_qpsk_robustness(snr, cfo):
    np.random.seed(42)
    sps = 8
    fs = 8000.0
    sig, bits, _ = generate_qpsk(num_symbols=1500, samples_per_symbol=sps, noise_std=0.0, sample_rate=int(fs))

    timing_offset = 3
    delayed = np.concatenate([np.zeros(timing_offset, dtype=sig.dtype), sig])
    impaired = apply_frequency_offset(delayed, fs, cfo)
    impaired = apply_phase_offset(impaired, np.deg2rad(45.0))
    impaired = add_awgn(impaired, snr)

    sync = synchronize_psk(impaired, fs, sps, order=4)
    ber = _resolve_rotational_ambiguity_ber(bits, sync["symbols"], demodulate_qpsk, order=4)

    if snr >= 20:
        assert ber < 0.01, f"QPSK at SNR {snr} dB, CFO {cfo} Hz failed: BER={ber}"
    elif snr == 15:
        assert ber < 0.10, f"QPSK at SNR 15 dB failed: BER={ber}"
    else:
        assert ber < 0.35, f"QPSK severe degradation at SNR {snr} dB: BER={ber}"


@pytest.mark.parametrize("snr", [30, 20, 15, 10, 5])
@pytest.mark.parametrize("cfo", [0.0, 25.0, -50.0, 100.0])
def test_phase3a_16qam_robustness(snr, cfo):
    np.random.seed(42)
    sps = 8
    fs = 8000.0
    sig, bits, _ = generate_16qam(num_symbols=1500, samples_per_symbol=sps, noise_std=0.0, sample_rate=int(fs))

    timing_offset = 1
    delayed = np.concatenate([np.zeros(timing_offset, dtype=sig.dtype), sig])
    impaired = apply_frequency_offset(delayed, fs, cfo)
    impaired = apply_phase_offset(impaired, np.deg2rad(20.0))
    impaired = add_awgn(impaired, snr)

    sync = synchronize_qam(impaired, fs, sps, order=16)
    ber = _resolve_rotational_ambiguity_ber(bits, sync["symbols"], demodulate_16qam, order=4)

    if snr >= 20:
        assert ber < 0.01, f"16-QAM at SNR {snr} dB, CFO {cfo} Hz failed: BER={ber}"
    elif snr == 15:
        assert ber < 0.12, f"16-QAM at SNR 15 dB failed: BER={ber}"
    else:
        assert ber < 0.40, f"16-QAM severe degradation at SNR {snr} dB: BER={ber}"


@pytest.mark.parametrize("snr", [30, 20, 15, 10, 5])
@pytest.mark.parametrize("cfo", [0.0, 25.0, -50.0, 100.0])
def test_phase3a_2fsk_robustness(snr, cfo):
    np.random.seed(42)
    sps = 16
    fs = 16000.0
    sig, bits, _ = generate_2fsk(num_symbols=1000, samples_per_symbol=sps, frequency_deviation=500.0, noise_std=0.0, sample_rate=int(fs))

    timing_offset = 4
    delayed = np.concatenate([np.zeros(timing_offset, dtype=sig.dtype), sig])
    impaired = apply_frequency_offset(delayed, fs, cfo)
    impaired = add_awgn(impaired, snr)

    sync = synchronize_fsk(impaired, fs, sps)
    rec = demodulate_2fsk(
        sync["frequency_corrected_signal"],
        fs,
        sps,
        timing_offset=sync["timing_offset"],
        frequency_threshold=0.0,
    )[:len(bits)]
    ber = calculate_ber(bits, rec)

    if snr >= 15:
        assert ber < 0.01, f"2-FSK at SNR {snr} dB, CFO {cfo} Hz failed: BER={ber}"
    elif snr == 10:
        assert ber < 0.05, f"2-FSK at SNR 10 dB failed: BER={ber}"
    else:
        assert ber < 0.15, f"2-FSK graceful degradation at SNR 5 dB: BER={ber}"


# ============================================================
# PHASE 3B: MODULATION CLASSIFIER CONFUSION STRESS TEST
# ============================================================

def test_phase3b_12_signal_classifier_stress():
    fs = 48000.0
    duration = 1.0
    n_samples = int(fs * duration)
    t = np.arange(n_samples) / fs

    # 1. Pure sine wave
    pure_sine = np.sin(2 * np.pi * 1000.0 * t).astype(np.float32)
    res_sine = analyze_signal(SignalData(samples=pure_sine, sample_rate=fs, source_type="MEMORY", representation="real", filename="pure_sine"))
    assert res_sine["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_sine["confidence"] == 0.0

    # 2. Two-tone signal
    two_tone = (0.5 * np.sin(2 * np.pi * 1000.0 * t) + 0.5 * np.sin(2 * np.pi * 2500.0 * t)).astype(np.float32)
    res_twotone = analyze_signal(SignalData(samples=two_tone, sample_rate=fs, source_type="MEMORY", representation="real", filename="two_tone"))
    assert res_twotone["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_twotone["confidence"] == 0.0

    # 3. Real WGN
    wgn = np.random.normal(0, 0.5, n_samples).astype(np.float32)
    res_wgn = analyze_signal(SignalData(samples=wgn, sample_rate=fs, source_type="MEMORY", representation="real", filename="real_wgn"))
    assert res_wgn["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_wgn["confidence"] == 0.0

    # 4. Colored noise
    sos = butter(4, [2000.0, 6000.0], btype="bandpass", fs=fs, output="sos")
    colored = sosfilt(sos, np.random.normal(0, 1.0, n_samples)).astype(np.float32)
    res_colored = analyze_signal(SignalData(samples=colored, sample_rate=fs, source_type="MEMORY", representation="real", filename="colored_noise"))
    assert res_colored["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_colored["confidence"] == 0.0

    # 5. BPSK
    bpsk_wave, _, _ = generate_bpsk(1000, 8, 0.01, sample_rate=int(fs))
    res_bpsk = analyze_signal(SignalData(samples=bpsk_wave, sample_rate=fs, source_type="MEMORY", representation="complex_iq", filename="bpsk"))
    assert res_bpsk["best_hypothesis"]["modulation"] == "BPSK"
    assert res_bpsk["confidence"] > 0.50

    # 6. QPSK
    qpsk_wave, _, _ = generate_qpsk(1000, 8, 0.01, sample_rate=int(fs))
    res_qpsk = analyze_signal(SignalData(samples=qpsk_wave, sample_rate=fs, source_type="MEMORY", representation="complex_iq", filename="qpsk"))
    assert res_qpsk["best_hypothesis"]["modulation"] == "QPSK"
    assert res_qpsk["confidence"] > 0.50

    # 7. 16-QAM
    qam_wave, _, _ = generate_16qam(1000, 8, 0.01, sample_rate=int(fs))
    res_qam = analyze_signal(SignalData(samples=qam_wave, sample_rate=fs, source_type="MEMORY", representation="complex_iq", filename="16qam"))
    assert res_qam["best_hypothesis"]["modulation"] == "16-QAM"
    assert res_qam["confidence"] > 0.50

    # 8. 2-FSK
    fsk_wave, _, _ = generate_2fsk(1000, 16, 1000, 0.01, sample_rate=int(fs))
    res_fsk = analyze_signal(SignalData(samples=fsk_wave, sample_rate=fs, source_type="MEMORY", representation="complex_iq", filename="2fsk"))
    assert res_fsk["best_hypothesis"]["modulation"] == "2-FSK"
    assert res_fsk["confidence"] > 0.50

    # 9. AM broadcast audio
    am_wave = ((1.0 + 0.7 * np.cos(2 * np.pi * 400.0 * t)) * np.cos(2 * np.pi * 10000.0 * t)).astype(np.float32)
    res_am = analyze_signal(SignalData(samples=am_wave, sample_rate=fs, source_type="MEMORY", representation="real", filename="am"))
    assert res_am["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_am["confidence"] == 0.0

    # 10. FM audio
    fm_wave = np.cos(2 * np.pi * 10000.0 * t + 3.0 * np.sin(2 * np.pi * 400.0 * t)).astype(np.float32)
    res_fm = analyze_signal(SignalData(samples=fm_wave, sample_rate=fs, source_type="MEMORY", representation="real", filename="fm"))
    assert res_fm["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_fm["confidence"] == 0.0

    # 11. Complex Gaussian noise
    c_wgn = (np.random.normal(0, 0.5, n_samples) + 1j * np.random.normal(0, 0.5, n_samples)).astype(np.complex64)
    res_cwgn = analyze_signal(SignalData(samples=c_wgn, sample_rate=fs, source_type="MEMORY", representation="complex_iq", filename="complex_wgn"))
    assert res_cwgn["best_hypothesis"]["modulation"] == "UNKNOWN"
    assert res_cwgn["confidence"] == 0.0

    # 12. Real audio file if present
    for real_path in [Path("samples/wav/1.wav"), Path("data/1.wav")]:
        if real_path.exists():
            res_real = analyze_signal(real_path)
            assert res_real["best_hypothesis"]["modulation"] == "UNKNOWN"
            assert res_real["confidence"] == 0.0
            break


# ============================================================
# PHASE 3C: 4TH-MOMENT MATHEMATICAL VERIFICATION
# ============================================================

def test_phase3c_fourth_moment_ratios():
    """
    Mathematical proof verification of E[|s|^4] / (E[|s|^2])^2:
    - BPSK: theoretical = 1.0000
    - QPSK: theoretical = 1.0000
    - 16-QAM: theoretical = 132 / 100 = 1.3200
    - Complex Gaussian Noise: theoretical = 2.0000
    """
    n_symbols = 50000

    # 1. BPSK
    bpsk_syms = np.random.choice([-1.0, 1.0], size=n_symbols).astype(np.complex64)
    bpsk_ratio = float(np.mean(np.abs(bpsk_syms) ** 4) / (np.mean(np.abs(bpsk_syms) ** 2) ** 2))
    assert np.isclose(bpsk_ratio, 1.0000, atol=1e-5)

    # 2. QPSK
    qpsk_levels = np.array([-1.0 - 1j, -1.0 + 1j, 1.0 - 1j, 1.0 + 1j]) / np.sqrt(2.0)
    qpsk_syms = np.random.choice(qpsk_levels, size=n_symbols)
    qpsk_ratio = float(np.mean(np.abs(qpsk_syms) ** 4) / (np.mean(np.abs(qpsk_syms) ** 2) ** 2))
    assert np.isclose(qpsk_ratio, 1.0000, atol=1e-5)

    # 3. 16-QAM
    levels = np.array([-3, -1, 1, 3])
    qam_grid = (levels[:, None] + 1j * levels[None, :]).flatten()
    qam_syms = np.random.choice(qam_grid, size=n_symbols)
    qam_ratio = float(np.mean(np.abs(qam_syms) ** 4) / (np.mean(np.abs(qam_syms) ** 2) ** 2))
    assert np.isclose(qam_ratio, 1.3200, atol=0.015)

    # 4. Complex Gaussian Noise
    cn = (np.random.normal(0, 1, n_symbols) + 1j * np.random.normal(0, 1, n_symbols))
    cn_ratio = float(np.mean(np.abs(cn) ** 4) / (np.mean(np.abs(cn) ** 2) ** 2))
    assert np.isclose(cn_ratio, 2.0000, atol=0.04)


# ============================================================
# PHASE 3D: FSK PHYSICS ACROSS DEVIATIONS
# ============================================================

def test_phase3d_fsk_physics_across_deviations():
    fs = 48000.0
    sps = 16
    symbol_rate = fs / sps  # 3000 Baud
    nyquist = fs / 2.0      # 24000 Hz

    # 1. Narrowband / MSK regime: h = 0.5 -> Delta_f = 0.25 * Rs = 750 Hz (sep = 1500 Hz = 0.5 * Rs)
    sig_msk, _, _ = generate_2fsk(1000, sps, frequency_deviation=750, noise_std=0.01, sample_rate=int(fs))
    hyp_msk = evaluate_fsk_hypothesis(sig_msk, fs, sps)
    assert hyp_msk["score"] > 0.50

    # 2. Standard Orthogonal FSK: h = 1.0 -> Delta_f = 0.5 * Rs = 1500 Hz (sep = 3000 Hz = 1.0 * Rs)
    sig_std, _, _ = generate_2fsk(1000, sps, frequency_deviation=1500, noise_std=0.01, sample_rate=int(fs))
    hyp_std = evaluate_fsk_hypothesis(sig_std, fs, sps)
    assert hyp_std["score"] > 0.50

    # 3. Wideband FSK: h = 2.0 -> Delta_f = 1.0 * Rs = 3000 Hz (sep = 6000 Hz = 2.0 * Rs)
    sig_wide, _, _ = generate_2fsk(1000, sps, frequency_deviation=3000, noise_std=0.01, sample_rate=int(fs))
    hyp_wide = evaluate_fsk_hypothesis(sig_wide, fs, sps)
    assert hyp_wide["score"] > 0.50

    # 4. Physical rejection: Nyquist violation (Delta_f >= Fs/2)
    # Beyond Nyquist, discrete instantaneous frequency aliases and cannot maintain orthogonal states
    aliased_wave = np.exp(1j * 2 * np.pi * (nyquist + 1000.0) * np.arange(2000) / fs).astype(np.complex64)
    q_aliased = fsk_quality(aliased_wave, fs, sps=16, timing_offset=0)
    assert q_aliased == 0.0


# ============================================================
# PHASE 3E: SYNCHRONIZATION STRESS & CAPTURE RANGE
# ============================================================

def test_phase3e_synchronization_capture_range():
    fs = 48000.0
    # For M-th power estimator, unambiguous capture range is |Delta_f| < Fs / (2 * M)
    # BPSK (M=2): |Delta_f| < 12000 Hz
    # QPSK (M=4): |Delta_f| < 6000 Hz
    sps = 8
    sig_bpsk, _, _ = generate_bpsk(1000, sps, 0.0, sample_rate=int(fs))
    sig_qpsk, _, _ = generate_qpsk(1000, sps, 0.0, sample_rate=int(fs))

    # Test BPSK at large offsets within capture range: 500, 1500, 3000 Hz
    for cfo in [500.0, 1500.0, -3000.0]:
        imp = apply_frequency_offset(sig_bpsk, fs, cfo)
        est = _estimate_cfo_mth_power(imp, fs, order=2)
        assert np.isclose(est, cfo, atol=10.0), f"BPSK CFO estimation failed at {cfo} Hz: got {est}"

    # Test QPSK at large offsets within capture range: 400, 1000, -2000 Hz
    for cfo in [400.0, 1000.0, -2000.0]:
        imp = apply_frequency_offset(sig_qpsk, fs, cfo)
        est = _estimate_cfo_mth_power(imp, fs, order=4)
        assert np.isclose(est, cfo, atol=10.0), f"QPSK CFO estimation failed at {cfo} Hz: got {est}"
