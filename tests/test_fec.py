"""
Unit and integration tests for FEC Architecture (Phases 4G - 4K).
Tests:
- Convolutional Encoding + Viterbi Decoding (K=7, K=3; clean, 1-bit, multi-bit errors)
- Reed-Solomon Codec (clean, correctable, uncorrectable errors)
- Concatenated FEC Pipeline (RS + Block Interleaver + Viterbi)
- LDPC (12, 6) Codec and blind hypothesis disclosure
- FEC Hypothesis Engine
"""

import numpy as np
import pytest

from core.fec import (
    convolutional_encode,
    viterbi_decode,
    rs_encode,
    rs_decode,
    concatenated_encode,
    concatenated_decode,
    ldpc_encode,
    ldpc_decode,
    try_ldpc,
    evaluate_fec_hypotheses,
    calculate_bit_error_rate,
)


def test_viterbi_k7_clean_and_impaired():
    np.random.seed(42)
    # 1. Clean round trip (K=7, rate 1/2)
    bits = np.random.randint(0, 2, 200, dtype=np.uint8)
    encoded = convolutional_encode(bits, constraint_length=7, generators=(171, 133))
    decoded, metrics = viterbi_decode(encoded, original_length=len(bits), constraint_length=7)
    assert calculate_bit_error_rate(bits, decoded) == 0.0
    assert metrics["final_metric"] == 0.0
    assert metrics["valid"] is True

    # 2. Injected single-bit error
    noisy_1 = encoded.copy()
    noisy_1[25] ^= 1
    dec_1, met_1 = viterbi_decode(noisy_1, original_length=len(bits), constraint_length=7)
    ber_before_1 = calculate_bit_error_rate(encoded, noisy_1)
    ber_after_1 = calculate_bit_error_rate(bits, dec_1)
    assert ber_before_1 > 0.0
    assert ber_after_1 == 0.0
    assert met_1["final_metric"] == 1.0

    # 3. Injected multi-bit scattered errors
    noisy_multi = encoded.copy()
    error_indices = [10, 45, 90, 150]
    for idx in error_indices:
        noisy_multi[idx] ^= 1
    dec_m, met_m = viterbi_decode(noisy_multi, original_length=len(bits), constraint_length=7)
    ber_before_m = float(len(error_indices) / len(encoded))
    ber_after_m = calculate_bit_error_rate(bits, dec_m)
    assert ber_before_m > 0.0
    assert ber_after_m == 0.0
    assert met_m["final_metric"] == len(error_indices)


def test_viterbi_k3_fast_mode():
    np.random.seed(42)
    bits = np.random.randint(0, 2, 120, dtype=np.uint8)
    encoded = convolutional_encode(bits, constraint_length=3, generators=(7, 5))
    decoded, metrics = viterbi_decode(encoded, original_length=len(bits), constraint_length=3, generators=(7, 5))
    assert calculate_bit_error_rate(bits, decoded) == 0.0
    assert metrics["valid"] is True


def test_reed_solomon_clean_and_impaired():
    np.random.seed(42)
    # Test with byte data
    msg_bytes = b"AutoSig-Intel SIH 2026 FEC Verification"
    nsym = 10  # Can correct up to 5 byte errors

    # 1. Clean encode and decode
    cw_bytes, meta = rs_encode(msg_bytes, nsym=nsym)
    dec_bytes, status = rs_decode(cw_bytes, nsym=nsym)
    assert dec_bytes == msg_bytes
    assert status["status"] == "VALIDATED"
    assert status["corrected_symbols"] == 0

    # 2. Correctable errors (4 corrupted bytes <= 5)
    corrupted = bytearray(cw_bytes)
    corrupted[1] ^= 0x55
    corrupted[5] ^= 0xAA
    corrupted[12] ^= 0xFF
    corrupted[18] ^= 0x12
    dec_corr, status_corr = rs_decode(corrupted, nsym=nsym)
    assert dec_corr == msg_bytes
    assert status_corr["status"] == "VALIDATED"
    assert status_corr["corrected_symbols"] == 4

    # 3. Uncorrectable errors (8 corrupted bytes > 5)
    uncorr = bytearray(cw_bytes)
    for i in range(8):
        uncorr[i * 3] ^= 0xFF
    dec_uncorr, status_uncorr = rs_decode(uncorr, nsym=nsym)
    assert dec_uncorr is None
    assert status_uncorr["status"] == "UNCORRECTABLE"

    # 4. Bit-array mode
    bits = np.random.randint(0, 2, 80, dtype=np.uint8)
    cw_bits, meta_bits = rs_encode(bits, nsym=6)
    dec_bits, status_bits = rs_decode(cw_bits, nsym=6, pad_count=meta_bits["pad_count"])
    assert calculate_bit_error_rate(bits, dec_bits) == 0.0


def test_concatenated_fec_round_trip():
    np.random.seed(42)
    bits = np.random.randint(0, 2, 160, dtype=np.uint8)
    
    # Encode with Concatenated FEC
    enc_bits, meta = concatenated_encode(
        bits,
        rs_nsym=8,
        conv_k=7,
        interleaver_rows=8,
    )

    # Inject burst errors into convolutional domain (within Viterbi + RS correction range)
    noisy_enc = enc_bits.copy()
    noisy_enc[15] ^= 1
    noisy_enc[50] ^= 1
    noisy_enc[120] ^= 1

    dec_bits, dec_meta = concatenated_decode(
        noisy_enc,
        original_bit_length=len(bits),
        rs_nsym=8,
        conv_k=7,
        interleaver_rows=8,
    )

    assert dec_bits is not None
    assert dec_meta["status"] == "VALIDATED"
    ber = calculate_bit_error_rate(bits, dec_bits)
    assert ber == 0.0


def test_ldpc_codec_and_blind_disclosure():
    np.random.seed(42)
    # Systematic (12, 6) LDPC Code
    msg = np.array([1, 0, 1, 1, 0, 0], dtype=np.uint8)
    codeword = ldpc_encode(msg)
    assert len(codeword) == 12

    # 1. Clean decode
    dec_clean, meta_clean = ldpc_decode(codeword)
    assert np.array_equal(dec_clean, msg)
    assert meta_clean["syndrome_zero"] is True

    # 2. Injected 1-bit error
    corrupted = codeword.copy()
    corrupted[4] ^= 1
    dec_corr, meta_corr = ldpc_decode(corrupted)
    assert np.array_equal(dec_corr, msg)
    assert meta_corr["syndrome_zero"] is True

    # 3. Blind disclosure
    blind_res = try_ldpc(codeword)
    assert blind_res["status"] == "NOT_IMPLEMENTED"
    assert "NP-hard" in blind_res["reason"]


def test_fec_hypothesis_engine():
    np.random.seed(42)
    # 1. Raw random noise -> no FEC passes
    raw = np.random.randint(0, 2, 200, dtype=np.uint8)
    hyps = evaluate_fec_hypotheses(raw)
    assert len(hyps) >= 3

    # 2. Convolutional K=7 valid codeword
    msg = np.random.randint(0, 2, 80, dtype=np.uint8)
    conv_cw = convolutional_encode(msg, constraint_length=7)
    hyps_conv = evaluate_fec_hypotheses(conv_cw)
    top_conv = hyps_conv[0]
    assert top_conv["type"] == "convolutional_viterbi_k7"
    assert top_conv["status"] == "VALIDATED"
    assert top_conv["score"] > 0.80
