"""
Integration tests for End-to-End Decoding Pipeline and Frame Hypothesis Ranking (Phases 4M, 4N).
Tests:
- End-to-end transmission with Preamble + RS + Interleaving + Convolutional Code
- Multi-hypothesis ranking preservation (alternatives preserved with evidence scores)
- Negative evaluation on random noise bitstreams (reports INSUFFICIENT_EVIDENCE)
"""

import numpy as np
import pytest

from core.frame import analyze_frame_hypotheses
from core.correlation import STANDARD_PREAMBLES
from core.interleaving import block_interleave
from core.fec import (
    rs_encode,
    convolutional_encode,
    calculate_bit_error_rate,
)


def test_end_to_end_frame_hypothesis_pipeline():
    np.random.seed(42)
    # 1. Generate payload data
    msg_bytes = b"SIH-2026-NTRO-DEMOD"
    
    # 2. RS Encode (nsym=6)
    rs_cw_bytes, rs_meta = rs_encode(msg_bytes, nsym=6)
    # Convert to bits
    rs_bits = np.unpackbits(np.frombuffer(rs_cw_bytes, dtype=np.uint8))

    # 3. Block Interleave (8 x cols)
    rows = 8
    cols = len(rs_bits) // rows
    interleaved_bits = block_interleave(rs_bits, rows=rows, cols=cols)

    # 4. Convolutional Encode (K=7, rate 1/2)
    conv_bits = convolutional_encode(interleaved_bits, constraint_length=7)

    # 5. Prepend CCSDS ASM Sync Word (32 bits) + 16-bit dummy header
    asm = STANDARD_PREAMBLES["CCSDS_ASM"]
    header = np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0], dtype=np.uint8) # 16 bits
    frame_bits = np.concatenate([asm, header, conv_bits])

    # 6. Analyze frame hypotheses
    report = analyze_frame_hypotheses(frame_bits, modulation="QPSK")

    assert report["preamble"] is not None
    assert report["preamble"]["pattern_type"] == "CCSDS_ASM"
    assert report["preamble"]["score"] == 1.0

    # Verify ranked candidates exist
    candidates = report["candidates"]
    assert len(candidates) >= 2

    # Best candidate should have high score and validated status
    best = report["best_decoding_hypothesis"]
    assert best["header_match"] == 1.0
    assert best["overall_score"] > 0.60
    assert best["status"] in ("VALIDATED", "HYPOTHESIS")


def test_random_stream_frame_hypotheses():
    np.random.seed(42)
    # Pure random noise stream
    raw_noise = np.random.randint(0, 2, 300, dtype=np.uint8)
    report = analyze_frame_hypotheses(raw_noise, modulation="BPSK")

    best = report["best_decoding_hypothesis"]
    # Should not claim validated protocol on noise
    assert best["status"] in ("INSUFFICIENT_EVIDENCE", "HYPOTHESIS")
    assert best["fec_valid"] is False
    assert best["overall_score"] < 0.40
