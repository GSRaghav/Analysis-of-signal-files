"""
Prepare Demonstration Dataset (Phase 6N).

Generates the 5 official SIH Jury Demonstration captures in samples/demo/:
- DEMO_01_BPSK_VITERBI
- DEMO_02_QPSK_RS
- DEMO_03_16QAM_CONCATENATED
- DEMO_04_2FSK_VITERBI
- DEMO_05_UNKNOWN_AUDIO (Audio recording from samples/wav/)
"""

import sys
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from core.test_signal_generator import generate_transmission

DEMO_DIR = Path(__file__).resolve().parents[1] / "samples" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("PREPARING OFFICIAL SIH DEMONSTRATION DATASET: samples/demo/")
print("=" * 80)

# -------------------------------------------------------------
# DEMO 01: BPSK + Block Interleaver + Viterbi K=7
# -------------------------------------------------------------
p1 = "SIH26147_DEMO_01_BPSK_VITERBI_RECONSTRUCTED_STREAM"
tx1 = generate_transmission(
    payload_bits=p1,
    modulation="BPSK",
    sps=8,
    sample_rate=48000.0,
    preamble_name="CCSDS_ASM",
    fec="convolutional",
    fec_parameters={"k": 7, "poly": [171, 133]},
    interleaver="block",
    interleaver_parameters={"rows": 8, "cols": 8},
    cfo_hz=30.0,
    phase_offset=0.20,
    timing_offset=2,
    snr_db=24.0,
    num_frames=4,
    random_seed=111,
)
tx1.to_wav(DEMO_DIR / "DEMO_01_BPSK_VITERBI.wav")
tx1.to_iq(DEMO_DIR / "DEMO_01_BPSK_VITERBI_f32.iq", dtype="float32")
tx1.to_json(DEMO_DIR / "DEMO_01_BPSK_VITERBI_truth.json")
print("  [+] Generated DEMO_01_BPSK_VITERBI (BPSK, SPS=8, CCSDS_ASM, Block, Viterbi K=7)")

# -------------------------------------------------------------
# DEMO 02: QPSK + Diagonal Interleaver + Reed-Solomon (nsym=6)
# -------------------------------------------------------------
p2 = "SIH26147_DEMO_02_QPSK_REED_SOLOMON_PAYLOAD_BURST"
tx2 = generate_transmission(
    payload_bits=p2,
    modulation="QPSK",
    sps=8,
    sample_rate=64000.0,
    preamble_name="CCSDS_ASM",
    fec="reed_solomon",
    fec_parameters={"nsym": 6},
    interleaver="diagonal",
    interleaver_parameters={"rows": 8, "cols": 8},
    cfo_hz=-35.0,
    phase_offset=-0.15,
    timing_offset=1,
    snr_db=26.0,
    num_frames=4,
    random_seed=222,
)
tx2.to_wav(DEMO_DIR / "DEMO_02_QPSK_RS.wav")
tx2.to_iq(DEMO_DIR / "DEMO_02_QPSK_RS_f32.iq", dtype="float32")
tx2.to_json(DEMO_DIR / "DEMO_02_QPSK_RS_truth.json")
print("  [+] Generated DEMO_02_QPSK_RS (QPSK, SPS=8, CCSDS_ASM, Diagonal, Reed-Solomon)")

# -------------------------------------------------------------
# DEMO 03: 16-QAM + Concatenated FEC (RS + Block + Viterbi)
# -------------------------------------------------------------
p3 = "SIH26147_DEMO_03_16QAM_CONCATENATED_CARRIER_LINK"
tx3 = generate_transmission(
    payload_bits=p3,
    modulation="16-QAM",
    sps=8,
    sample_rate=64000.0,
    preamble_name="CCSDS_ASM",
    fec="concatenated",
    fec_parameters={"rs_nsym": 4, "conv_k": 7, "interleaver_rows": 8},
    interleaver="none",
    cfo_hz=18.0,
    phase_offset=0.10,
    timing_offset=3,
    snr_db=28.0,
    num_frames=4,
    random_seed=333,
)
tx3.to_wav(DEMO_DIR / "DEMO_03_16QAM_CONCATENATED.wav")
tx3.to_iq(DEMO_DIR / "DEMO_03_16QAM_CONCATENATED_f32.iq", dtype="float32")
tx3.to_json(DEMO_DIR / "DEMO_03_16QAM_CONCATENATED_truth.json")
print("  [+] Generated DEMO_03_16QAM_CONCATENATED (16-QAM, SPS=8, CCSDS_ASM, Concatenated)")

# -------------------------------------------------------------
# DEMO 04: 2-FSK + Convolutional Interleaver + Viterbi
# -------------------------------------------------------------
p4 = "SIH26147_DEMO_04_2FSK_MIL_SENSOR_STREAM"
tx4 = generate_transmission(
    payload_bits=p4,
    modulation="2-FSK",
    sps=16,
    sample_rate=48000.0,
    preamble_name="CCSDS_ASM",
    fec="convolutional",
    fec_parameters={"k": 7, "poly": [171, 133], "freq_dev_hz": 1500.0},
    interleaver="block",
    interleaver_parameters={"rows": 8, "cols": 8},
    cfo_hz=12.0,
    phase_offset=0.0,
    timing_offset=0,
    snr_db=22.0,
    num_frames=4,
    random_seed=444,
)
tx4.to_wav(DEMO_DIR / "DEMO_04_2FSK_VITERBI.wav")
tx4.to_iq(DEMO_DIR / "DEMO_04_2FSK_VITERBI_f32.iq", dtype="float32")
tx4.to_json(DEMO_DIR / "DEMO_04_2FSK_VITERBI_truth.json")
print("  [+] Generated DEMO_04_2FSK_VITERBI (2-FSK, SPS=16, CCSDS_ASM, Block, Viterbi K=7)")

# -------------------------------------------------------------
# DEMO 05: UNKNOWN AUDIO (Real voice audio recording)
# -------------------------------------------------------------
src_wav = Path(__file__).resolve().parents[1] / "samples" / "wav" / "1.wav"
dst_wav = DEMO_DIR / "DEMO_05_UNKNOWN_AUDIO.wav"
shutil.copyfile(src_wav, dst_wav)

# Create evaluator ground truth for Demo 05
import json
demo5_truth = {
    "file": "DEMO_05_UNKNOWN_AUDIO.wav",
    "signal_nature": "Real-world analog voice / audio recording",
    "modulation": "UNKNOWN",
    "samples_per_symbol": None,
    "fec": "none",
    "interleaver": "none",
    "preamble": "none",
    "expected_result": "UNKNOWN",
    "expected_confidence": 0.0,
    "expected_status": "NON_DIGITAL_REJECTED",
    "note": "Evaluator ground truth: must reject as non-digital with 0.0% confidence."
}
with open(DEMO_DIR / "DEMO_05_UNKNOWN_AUDIO_truth.json", "w", encoding="utf-8") as f:
    json.dump(demo5_truth, f, indent=2)
print("  [+] Generated DEMO_05_UNKNOWN_AUDIO (Real audio, Expected=UNKNOWN, Conf=0.0%)")

print("=" * 80)
print(f"All 5 demonstration cases successfully prepared in {DEMO_DIR}")
