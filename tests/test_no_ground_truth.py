"""
Strict No-Ground-Truth Receiver Test Suite (Phase 6D & 6E).

This test validates that AutoSig-Intel autonomously discovers the complete transmission
path (Modulation, SPS, Interleaver, FEC, Preamble, and Payload) without receiving ANY
ground-truth hints or parameters from the caller.

The receiver receives ONLY the file path. All assertions compare receiver inferences
against independent external ground truth.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from core.receiver import analyze_signal


SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "samples" / "synthetic"


def load_truth(name: str):
    with open(SYNTHETIC_DIR / f"{name}_truth.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestNoGroundTruthReceiver:
    """Receiver must receive ONLY the file path."""

    def test_blind_capture_a_bpsk(self):
        wav_path = SYNTHETIC_DIR / "capture_a_bpsk.wav"
        truth = load_truth("capture_a_bpsk")

        # Receiver gets ONLY the file path
        result = analyze_signal(wav_path)

        # 1. Physical Parameter Inferences
        assert result["modulation"] == truth["modulation"] == "BPSK"
        assert result["samples_per_symbol"] == truth["samples_per_symbol"] == 8
        assert result["confidence"] >= 0.85
        assert result["status"] == "ANALYSIS_COMPLETE"
        assert result["best_hypothesis"]["confidence_tier"] == "HIGH CONFIDENCE"

        # 2. Preamble & Framing Inferences
        decoding = result.get("decoding", {})
        preamble = decoding.get("correlation", {}).get("preamble", {})
        assert preamble.get("pattern_type") == truth["preamble"]["name"] == "CCSDS_ASM"
        assert preamble.get("score") == 1.0

        # 3. FEC & Interleaver Inferences
        fec = decoding.get("fec", {})
        assert "viterbi_k7" in fec.get("best_hypothesis", "")
        assert fec.get("status") == "VALIDATED"
        assert decoding.get("interleaving", {}).get("best_hypothesis") == "block"

        # 4. End-to-End Payload Recovery
        rec_payload = decoding.get("frame", {}).get("decoded_bits")
        assert rec_payload is not None
        true_payload = np.array(truth["payload_bits"], dtype=np.uint8)
        assert len(rec_payload) == len(true_payload)
        ber = float(np.mean(rec_payload != true_payload))
        assert ber == 0.0, f"Payload BER was {ber} (expected 0.0)"

    def test_blind_capture_b_qpsk(self):
        wav_path = SYNTHETIC_DIR / "capture_b_qpsk.wav"
        truth = load_truth("capture_b_qpsk")

        result = analyze_signal(wav_path)

        assert result["modulation"] == truth["modulation"] == "QPSK"
        assert result["samples_per_symbol"] == truth["samples_per_symbol"] == 8
        assert result["confidence"] >= 0.85
        assert result["status"] == "ANALYSIS_COMPLETE"
        assert result["best_hypothesis"]["confidence_tier"] == "HIGH CONFIDENCE"

        decoding = result.get("decoding", {})
        preamble = decoding.get("correlation", {}).get("preamble", {})
        assert preamble.get("pattern_type") == truth["preamble"]["name"] == "CCSDS_ASM"

        fec = decoding.get("fec", {})
        assert "reed_solomon" in fec.get("best_hypothesis", "")
        assert fec.get("status") == "VALIDATED"
        assert decoding.get("interleaving", {}).get("best_hypothesis") == "diagonal"

        rec_payload = decoding.get("frame", {}).get("decoded_bits")
        assert rec_payload is not None
        true_payload = np.array(truth["payload_bits"], dtype=np.uint8)
        # Verify first len(true_payload) bits match with 0 BER
        cmp_len = len(true_payload)
        ber = float(np.mean(rec_payload[:cmp_len] != true_payload))
        assert ber == 0.0, f"Payload BER was {ber} (expected 0.0)"

    def test_blind_capture_c_qpsk(self):
        wav_path = SYNTHETIC_DIR / "capture_c_qpsk.wav"
        truth = load_truth("capture_c_qpsk")

        result = analyze_signal(wav_path)

        assert result["modulation"] == truth["modulation"] == "QPSK"
        assert result["samples_per_symbol"] == truth["samples_per_symbol"] == 8
        assert result["confidence"] >= 0.85
        assert result["status"] == "ANALYSIS_COMPLETE"
        assert result["best_hypothesis"]["confidence_tier"] == "HIGH CONFIDENCE"

        decoding = result.get("decoding", {})
        preamble = decoding.get("correlation", {}).get("preamble", {})
        assert preamble.get("pattern_type") == truth["preamble"]["name"] == "CCSDS_ASM"

        fec = decoding.get("fec", {})
        assert "viterbi_k3" in fec.get("best_hypothesis", "")
        assert fec.get("status") == "VALIDATED"
        assert decoding.get("interleaving", {}).get("best_hypothesis") == "pseudo_random"

        rec_payload = decoding.get("frame", {}).get("decoded_bits")
        assert rec_payload is not None
        true_payload = np.array(truth["payload_bits"], dtype=np.uint8)
        assert len(rec_payload) == len(true_payload)
        ber = float(np.mean(rec_payload != true_payload))
        assert ber == 0.0, f"Payload BER was {ber} (expected 0.0)"

    def test_blind_capture_d_16qam(self):
        wav_path = SYNTHETIC_DIR / "capture_d_16qam.wav"
        truth = load_truth("capture_d_16qam")

        result = analyze_signal(wav_path)

        assert result["modulation"] == truth["modulation"] == "16-QAM"
        assert result["confidence"] >= 0.85
        assert result["status"] == "ANALYSIS_COMPLETE"
        assert result["best_hypothesis"]["confidence_tier"] == "HIGH CONFIDENCE"

        decoding = result.get("decoding", {})
        preamble = decoding.get("correlation", {}).get("preamble", {})
        assert preamble.get("pattern_type") == truth["preamble"]["name"] == "SYNC_AA55"

    def test_blind_capture_e_2fsk(self):
        wav_path = SYNTHETIC_DIR / "capture_e_2fsk.wav"
        truth = load_truth("capture_e_2fsk")

        result = analyze_signal(wav_path)

        assert result["modulation"] == truth["modulation"] == "2-FSK"
        assert result["samples_per_symbol"] == truth["samples_per_symbol"] == 16
        assert result["confidence"] >= 0.85
        assert result["status"] == "ANALYSIS_COMPLETE"
        assert result["best_hypothesis"]["confidence_tier"] == "HIGH CONFIDENCE"

        decoding = result.get("decoding", {})
        preamble = decoding.get("correlation", {}).get("preamble", {})
        assert preamble.get("pattern_type") == truth["preamble"]["name"] == "SYNC_AA55"

    def test_negative_screening_rejections(self):
        """Negative non-digital signals must return UNKNOWN with 0.0% confidence."""
        for neg_name in ["negative_pure_sine.wav", "negative_two_tone.wav", "negative_gaussian_noise.wav"]:
            wav_path = SYNTHETIC_DIR / neg_name
            result = analyze_signal(wav_path)
            assert result["modulation"] == "UNKNOWN", f"{neg_name} was not identified as UNKNOWN"
            assert result["confidence"] == 0.0, f"{neg_name} confidence was {result['confidence']}"
            assert result["status"] in ("NON_DIGITAL_REJECTED", "INSUFFICIENT_EVIDENCE")
