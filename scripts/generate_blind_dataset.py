#!/usr/bin/env python3
"""
Generate blind evaluation captures for AutoSig-Intel Phase 5.

Produces unknown captures in samples/synthetic/:
- Capture A: BPSK + Block interleaver + Viterbi (NASA K=7)
- Capture B: QPSK + Diagonal interleaver + Reed-Solomon
- Capture C: QPSK + Pseudo-Random interleaver + Convolutional (K=3)
- Capture D: 16-QAM + Block interleaver + Concatenated FEC
- Capture E: 2-FSK + Convolutional interleaver + Viterbi
- Negative Cases: Pure Sine, Two-Tone, Gaussian Noise, Short Random Noise

Saves IQ captures (.wav and .iq) and independent ground-truth JSON files.
"""

import sys
from pathlib import Path
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.test_signal_generator import generate_transmission


OUTPUT_DIR = PROJECT_ROOT / "samples" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_blind_dataset():
    print("[*] Generating Phase 5 Blind Decoding Captures in samples/synthetic/...")

    # -------------------------------------------------------------
    # Capture A: BPSK + Block Interleaver + Viterbi (K=7 NASA)
    # -------------------------------------------------------------
    payload_a = "AUTOSIG_INTEL_PHASE5_CAPTURE_A_BPSK_VITERBI_VALIDATED"
    tx_a = generate_transmission(
        payload_bits=payload_a,
        modulation="BPSK",
        sps=8,
        sample_rate=48000.0,
        preamble_name="CCSDS_ASM",
        fec="convolutional",
        fec_parameters={"k": 7, "poly": [171, 133]},
        interleaver="block",
        interleaver_parameters={"rows": 8, "cols": 8},
        cfo_hz=35.0,
        phase_offset=0.35,
        timing_offset=3,
        snr_db=22.0,
        num_frames=4,
        random_seed=101,
    )
    tx_a.to_wav(OUTPUT_DIR / "capture_a_bpsk.wav")
    tx_a.to_iq(OUTPUT_DIR / "capture_a_bpsk_f32.iq", dtype="float32")
    tx_a.to_json(OUTPUT_DIR / "capture_a_bpsk_truth.json")
    print("  [+] Capture A generated: BPSK + Block + Viterbi")

    # -------------------------------------------------------------
    # Capture B: QPSK + Diagonal Interleaver + Reed-Solomon
    # -------------------------------------------------------------
    payload_b = "NTRO_SIH_CAPTURE_B_QPSK_REED_SOLOMON_PAYLOAD"
    tx_b = generate_transmission(
        payload_bits=payload_b,
        modulation="QPSK",
        sps=8,
        sample_rate=64000.0,
        preamble_name="CCSDS_ASM",
        fec="reed_solomon",
        fec_parameters={"nsym": 6},
        interleaver="diagonal",
        interleaver_parameters={"rows": 8, "cols": 8},
        cfo_hz=-42.0,
        phase_offset=-0.25,
        timing_offset=2,
        snr_db=25.0,
        num_frames=4,
        random_seed=202,
    )
    tx_b.to_wav(OUTPUT_DIR / "capture_b_qpsk.wav")
    tx_b.to_iq(OUTPUT_DIR / "capture_b_qpsk_f32.iq", dtype="float32")
    tx_b.to_json(OUTPUT_DIR / "capture_b_qpsk_truth.json")
    print("  [+] Capture B generated: QPSK + Diagonal + Reed-Solomon")

    # -------------------------------------------------------------
    # Capture C: QPSK + Pseudo-Random Interleaver + Viterbi (K=3)
    # -------------------------------------------------------------
    payload_c = "TACTICAL_LINK_CAPTURE_C_QPSK_PR_CONV_TELEMETRY"
    tx_c = generate_transmission(
        payload_bits=payload_c,
        modulation="QPSK",
        sps=8,
        sample_rate=64000.0,
        preamble_name="CCSDS_ASM",
        fec="convolutional",
        fec_parameters={"k": 3, "poly": [7, 5]},
        interleaver="pseudo_random",
        interleaver_parameters={"block_size": 64, "seed": 42},
        cfo_hz=28.0,
        phase_offset=0.18,
        timing_offset=4,
        snr_db=24.0,
        num_frames=4,
        random_seed=303,
    )
    tx_c.to_wav(OUTPUT_DIR / "capture_c_qpsk.wav")
    tx_c.to_iq(OUTPUT_DIR / "capture_c_qpsk_f32.iq", dtype="float32")
    tx_c.to_json(OUTPUT_DIR / "capture_c_qpsk_truth.json")
    print("  [+] Capture C generated: QPSK + Pseudo-Random + Viterbi K=3")

    # -------------------------------------------------------------
    # Capture D: 16-QAM + Block Interleaver + Concatenated FEC
    # -------------------------------------------------------------
    payload_d = "16QAM_CONCATENATED_HIGH_EFFICIENCY_CARRIER_DATA"
    tx_d = generate_transmission(
        payload_bits=payload_d,
        modulation="16-QAM",
        sps=8,
        sample_rate=64000.0,
        preamble_name="SYNC_AA55",
        fec="concatenated",
        fec_parameters={"rs_nsym": 4, "conv_k": 7, "interleaver_rows": 8},
        interleaver="block",
        interleaver_parameters={"rows": 8, "cols": 8},
        cfo_hz=20.0,
        phase_offset=0.12,
        timing_offset=1,
        snr_db=28.0,
        num_frames=4,
        random_seed=404,
    )
    tx_d.to_wav(OUTPUT_DIR / "capture_d_16qam.wav")
    tx_d.to_iq(OUTPUT_DIR / "capture_d_16qam_f32.iq", dtype="float32")
    tx_d.to_json(OUTPUT_DIR / "capture_d_16qam_truth.json")
    print("  [+] Capture D generated: 16-QAM + Block + Concatenated")

    # -------------------------------------------------------------
    # Capture E: 2-FSK + Convolutional Interleaver + Viterbi
    # -------------------------------------------------------------
    payload_e = "FSK_SUB_GHZ_TACTICAL_MIL_SENSOR_BURST"
    tx_e = generate_transmission(
        payload_bits=payload_e,
        modulation="2-FSK",
        sps=16,
        sample_rate=48000.0,
        preamble_name="SYNC_AA55",
        fec="convolutional",
        fec_parameters={"k": 7, "poly": [171, 133], "freq_dev_hz": 1500.0},
        interleaver="convolutional",
        interleaver_parameters={"branches": 4, "branch_delay": 2},
        cfo_hz=15.0,
        phase_offset=0.0,
        timing_offset=0,
        snr_db=22.0,
        num_frames=4,
        random_seed=505,
    )
    tx_e.to_wav(OUTPUT_DIR / "capture_e_2fsk.wav")
    tx_e.to_iq(OUTPUT_DIR / "capture_e_2fsk_f32.iq", dtype="float32")
    tx_e.to_json(OUTPUT_DIR / "capture_e_2fsk_truth.json")
    print("  [+] Capture E generated: 2-FSK + Convolutional Interleaver + Viterbi")

    # -------------------------------------------------------------
    # Negative Captures (Must return UNKNOWN / NON_DIGITAL)
    # -------------------------------------------------------------
    fs_neg = 48000.0
    t_neg = np.arange(int(fs_neg * 1.5)) / fs_neg

    # 1. Pure Sine (1 kHz tone)
    sine_samples = (0.7 * np.exp(1j * (2.0 * np.pi * 1000.0 * t_neg))).astype(np.complex64)
    if sf is not None:
        sf.write(str(OUTPUT_DIR / "negative_pure_sine.wav"), np.column_stack([np.real(sine_samples), np.imag(sine_samples)]), int(fs_neg))
    print("  [+] Negative Case 1: Pure Sine (1 kHz)")

    # 2. Two-Tone Carrier (1.2 kHz and 2.4 kHz)
    two_tone = (0.4 * np.exp(1j * 2 * np.pi * 1200 * t_neg) + 0.4 * np.exp(1j * 2 * np.pi * 2400 * t_neg)).astype(np.complex64)
    if sf is not None:
        sf.write(str(OUTPUT_DIR / "negative_two_tone.wav"), np.column_stack([np.real(two_tone), np.imag(two_tone)]), int(fs_neg))
    print("  [+] Negative Case 2: Two-Tone")

    # 3. Gaussian Noise (Pure AWGN)
    noise_samples = ((np.random.normal(0, 0.3, len(t_neg)) + 1j * np.random.normal(0, 0.3, len(t_neg)))).astype(np.complex64)
    if sf is not None:
        sf.write(str(OUTPUT_DIR / "negative_gaussian_noise.wav"), np.column_stack([np.real(noise_samples), np.imag(noise_samples)]), int(fs_neg))
    print("  [+] Negative Case 3: Gaussian Noise")

    print("[*] All blind captures generated successfully!")


if __name__ == "__main__":
    generate_blind_dataset()
