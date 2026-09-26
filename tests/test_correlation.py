"""
Unit and integration tests for Bitstream Correlation and Frame Synchronization (Phase 4L).
Tests:
- Exact and noisy bit-pattern correlation
- Preamble detection across standard aerospace/coms sync words (CCSDS ASM, Barker)
- Header candidate detection and candidate length parsing
- Periodic frame and payload boundary estimation
"""

import numpy as np
import pytest

from core.correlation import (
    correlate_pattern,
    detect_preamble,
    detect_header_candidates,
    estimate_payload_boundaries,
    bit_similarity,
    find_common_sequence,
    STANDARD_PREAMBLES,
)


def test_correlate_pattern_exact_and_noisy():
    pattern = np.array([1, 1, 0, 0, 1, 0, 1, 0], dtype=np.uint8)
    
    # 1. Exact match embedded in noise
    noise_lead = np.zeros(20, dtype=np.uint8)
    noise_tail = np.ones(30, dtype=np.uint8)
    stream = np.concatenate([noise_lead, pattern, noise_tail])

    matches = correlate_pattern(stream, pattern, max_bit_errors=0)
    assert len(matches) >= 1
    best = matches[0]
    assert best["start_index"] == 20
    assert best["end_index"] == 28
    assert best["score"] == 1.0
    assert best["bit_errors"] == 0

    # 2. Noisy match (1 bit flipped in pattern)
    corrupted_pattern = pattern.copy()
    corrupted_pattern[3] ^= 1  # 1 bit error
    noisy_stream = np.concatenate([noise_lead, corrupted_pattern, noise_tail])

    # With max_bit_errors=0 -> no match
    assert len(correlate_pattern(noisy_stream, pattern, max_bit_errors=0, threshold=0.95)) == 0

    # With max_bit_errors=1 -> detected
    noisy_matches = correlate_pattern(noisy_stream, pattern, max_bit_errors=1, threshold=0.80)
    assert len(noisy_matches) >= 1
    assert noisy_matches[0]["start_index"] == 20
    assert noisy_matches[0]["bit_errors"] == 1
    assert noisy_matches[0]["score"] == 7.0 / 8.0


def test_detect_standard_preambles():
    np.random.seed(42)
    # Embed CCSDS ASM (32 bits)
    asm = STANDARD_PREAMBLES["CCSDS_ASM"]
    prefix = np.random.randint(0, 2, 50, dtype=np.uint8)
    suffix = np.random.randint(0, 2, 100, dtype=np.uint8)
    stream = np.concatenate([prefix, asm, suffix])

    detected = detect_preamble(stream)
    assert detected is not None
    assert detected["pattern_type"] == "CCSDS_ASM"
    assert detected["start_index"] == 50
    assert detected["score"] == 1.0


def test_header_candidate_detection():
    # Preamble + 32-bit header (Length = 0x0150 = 336 bytes big-endian) + payload
    preamble = STANDARD_PREAMBLES["BARKER_11"]
    header = np.array([
        0, 0, 0, 0, 0, 0, 0, 1,  # 0x01
        0, 1, 0, 1, 0, 0, 0, 0,  # 0x50
        1, 1, 1, 1, 0, 0, 0, 0,  # 0xF0
        1, 0, 1, 0, 0, 1, 0, 1,  # 0xA5
    ], dtype=np.uint8)
    payload = np.zeros(200, dtype=np.uint8)
    stream = np.concatenate([preamble, header, payload])

    p_match = {
        "start_index": 0,
        "end_index": len(preamble),
        "pattern_length": len(preamble),
    }

    hdr = detect_header_candidates(stream, p_match, header_length_bits=32)
    assert hdr is not None
    assert hdr["header_start"] == len(preamble)
    assert hdr["candidate_length_be"] == 0x0150
    assert hdr["header_hex"].startswith("0150")


def test_estimate_payload_boundaries():
    np.random.seed(42)
    # Generate 3 frames with 0xAA55 sync word and 100 bits payload
    sync = STANDARD_PREAMBLES["SYNC_AA55"]
    header_len = 16
    payload_len = 100
    frame_len = len(sync) + header_len + payload_len  # 16 + 16 + 100 = 132

    frames = []
    for _ in range(3):
        hdr = np.random.randint(0, 2, header_len, dtype=np.uint8)
        pld = np.random.randint(0, 2, payload_len, dtype=np.uint8)
        frames.append(np.concatenate([sync, hdr, pld]))

    stream = np.concatenate(frames)
    boundaries = estimate_payload_boundaries(stream, sync, header_length_bits=header_len)

    assert boundaries["frames_found"] == 3
    assert boundaries["estimated_frame_length"] == frame_len
    assert len(boundaries["payload_segments"]) == 3
    for seg in boundaries["payload_segments"]:
        assert seg["payload_length_bits"] == payload_len


def test_backward_compatibility_helpers():
    a = [1, 0, 1, 1, 0, 0]
    b = [1, 0, 1, 0, 0, 0]
    assert bit_similarity(a, b) == 5.0 / 6.0
    comm = find_common_sequence(a, b, min_length=3)
    assert comm is not None
    assert comm["start"] == 0
    assert comm["length"] == 3
