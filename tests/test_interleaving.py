"""
Unit and integration tests for Deinterleaving Architecture (Phases 4A - 4F).
Tests:
- Block interleaving round-trip (square and non-square matrices, trailing bits)
- Convolutional interleaving round-trip (Ramsey/Forney delay compensation)
- Diagonal interleaving round-trip
- Pseudo-random interleaving round-trip and seed sensitivity
- Interleaver hypothesis engine (evidence-driven validation vs. UNKNOWN fallback)
"""

import numpy as np
import pytest

from core.interleaving import (
    block_interleave,
    block_deinterleave,
    convolutional_interleave,
    convolutional_deinterleave,
    diagonal_interleave,
    diagonal_deinterleave,
    pseudo_random_interleave,
    pseudo_random_deinterleave,
    evaluate_interleaving_hypotheses,
)
from core.demodulation import calculate_ber


def test_block_interleaving_round_trip():
    np.random.seed(42)
    # Test multiple row/column configurations, including square and non-square
    test_configs = [
        (4, 4, 160),    # Exact multiple
        (4, 8, 200),    # Non-square
        (8, 16, 512),   # Medium block
        (7, 11, 300),   # Prime non-square with incomplete final block (300 % 77 != 0)
        (3, 5, 47),     # Small block with 2 trailing bits
    ]

    for rows, cols, length in test_configs:
        bits = np.random.randint(0, 2, length, dtype=np.uint8)
        interleaved = block_interleave(bits, rows, cols)
        assert len(interleaved) == length, f"Interleaved length {len(interleaved)} != {length}"
        
        # Interleaving must alter the order for non-trivial data
        if length > rows * cols:
            assert not np.array_equal(bits[:rows*cols], interleaved[:rows*cols])

        deinterleaved = block_deinterleave(interleaved, rows, cols)
        assert len(deinterleaved) == length
        ber = calculate_ber(bits, deinterleaved)
        assert ber == 0.0, f"Block ({rows}x{cols}, len={length}) round-trip failed: BER={ber}"


def test_convolutional_interleaving_round_trip():
    np.random.seed(42)
    branches = 4
    branch_delay = 2
    # End-to-end delay through Ramsey interleaver + deinterleaver
    total_delay = branches * (branches - 1) * branch_delay

    bits = np.random.randint(0, 2, 400, dtype=np.uint8)
    # Append flushing tail so all data symbols clear the shift registers
    flushed_bits = np.concatenate([bits, np.zeros(total_delay, dtype=np.uint8)])

    interleaved = convolutional_interleave(flushed_bits, branches=branches, branch_delay=branch_delay)
    deinterleaved = convolutional_deinterleave(interleaved, branches=branches, branch_delay=branch_delay)

    # Recovered bits appear after total_delay
    recovered = deinterleaved[total_delay:total_delay + len(bits)]
    ber = calculate_ber(bits, recovered)
    assert ber == 0.0, f"Convolutional (B={branches}, M={branch_delay}) failed: BER={ber}"


def test_diagonal_interleaving_round_trip():
    np.random.seed(42)
    configs = [
        (4, 4, 64),
        (5, 7, 105),
        (8, 12, 250),  # With incomplete final block
    ]

    for rows, cols, length in configs:
        bits = np.random.randint(0, 2, length, dtype=np.uint8)
        interleaved = diagonal_interleave(bits, rows, cols)
        assert len(interleaved) == length
        deinterleaved = diagonal_deinterleave(interleaved, rows, cols)
        assert len(deinterleaved) == length
        ber = calculate_ber(bits, deinterleaved)
        assert ber == 0.0, f"Diagonal ({rows}x{cols}) failed: BER={ber}"


def test_pseudo_random_interleaving_round_trip():
    np.random.seed(42)
    block_size = 64
    length = 200  # Non-exact multiple

    bits = np.random.randint(0, 2, length, dtype=np.uint8)
    
    # 1. Deterministic round trip with same seed
    interleaved = pseudo_random_interleave(bits, block_size=block_size, seed=123)
    deinterleaved = pseudo_random_deinterleave(interleaved, block_size=block_size, seed=123)
    assert calculate_ber(bits, deinterleaved) == 0.0

    # 2. Seed sensitivity: different seed produces distinct interleaving
    interleaved_diff = pseudo_random_interleave(bits, block_size=block_size, seed=999)
    assert not np.array_equal(interleaved, interleaved_diff)

    # 3. Wrong seed fails to deinterleave correctly
    wrong_deinterleaved = pseudo_random_deinterleave(interleaved, block_size=block_size, seed=999)
    assert calculate_ber(bits, wrong_deinterleaved) > 0.20

    # 4. Invalid parameter rejection
    with pytest.raises(ValueError, match="block_size must be >= 2"):
        pseudo_random_interleave(bits, block_size=1)


def test_interleaver_hypothesis_engine():
    np.random.seed(42)
    # 1. Test blind execution without validator -> must report UNKNOWN
    raw_bits = np.random.randint(0, 2, 256, dtype=np.uint8)
    hypotheses = evaluate_interleaving_hypotheses(raw_bits)
    top_hyp = hypotheses[0]
    assert top_hyp["type"] == "UNKNOWN"
    assert top_hyp["status"] == "INSUFFICIENT_EVIDENCE"
    assert top_hyp["score"] == 0.0

    # 2. Test execution with downstream validator (synthetic frame sync word validator)
    # Target bitstream: contains a known 16-bit sync word [1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0]
    sync_word = np.array([1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0], dtype=np.uint8)
    payload = np.random.randint(0, 2, 128 - 16, dtype=np.uint8)
    frame = np.concatenate([sync_word, payload])

    # Interleave frame using an 8x16 block interleaver
    transmitted = block_interleave(frame, rows=8, cols=16)

    # Validator searches for the sync word at start of candidate bits
    def sync_word_validator(cand_bits):
        if len(cand_bits) >= 16 and np.array_equal(cand_bits[:16], sync_word):
            return True, 1.0, {"sync_word_matched": True}
        return False, 0.0, {"sync_word_matched": False}

    validated_hyps = evaluate_interleaving_hypotheses(transmitted, validator_fn=sync_word_validator)
    best_hyp = validated_hyps[0]
    assert best_hyp["type"] == "block"
    assert best_hyp["parameters"]["rows"] == 8
    assert best_hyp["parameters"]["cols"] == 16
    assert best_hyp["status"] == "VALIDATED"
    assert best_hyp["score"] == 1.0
    assert np.array_equal(best_hyp["output_bits"][:16], sync_word)
