"""
Interleaver & FEC Ambiguity and Limitation Tests (Phase 6H & 6I).

Validates honest scientific boundaries:
- When bitstreams have no downstream protocol, preamble, or FEC evidence,
  blind interleaver identification must return 'UNKNOWN' or 'INSUFFICIENT_EVIDENCE',
  rather than fabricating false certainty.
- When unencoded noise is fed to the FEC hypothesis engine, it must return
  'none' or 'UNKNOWN' and not falsely declare FEC validation.
"""

import numpy as np
import pytest

from core.interleaving import evaluate_interleaving_hypotheses
from core.fec import evaluate_fec_hypotheses


class TestAmbiguityBoundaries:
    """Scientific boundary tests for indistinguishable structures."""

    def test_blind_interleaver_without_downstream_evidence(self):
        """
        Without downstream FEC or frame sync word evidence,
        blind de-interleaving cannot distinguish Block vs Diagonal vs PR.
        Must report UNKNOWN with status INSUFFICIENT_EVIDENCE.
        """
        np.random.seed(123)
        raw_bits = np.random.randint(0, 2, 256, dtype=np.uint8)

        # Evaluate interleaver hypotheses with no validator
        hyps = evaluate_interleaving_hypotheses(raw_bits, validator_fn=None)

        # Top candidate must honestly state UNKNOWN / INSUFFICIENT_EVIDENCE
        top = hyps[0]
        assert top["type"] == "UNKNOWN"
        assert top["status"] == "INSUFFICIENT_EVIDENCE"
        assert top["score"] == 0.0
        assert "cannot be resolved" in top["evidence"]["reason"]

    def test_fec_on_unencoded_random_bits(self):
        """
        When arbitrary unencoded bits are presented to the FEC engine,
        no code family should validate as a genuine transmission.
        """
        np.random.seed(456)
        noise_bits = np.random.randint(0, 2, 512, dtype=np.uint8)

        fec_hyps = evaluate_fec_hypotheses(noise_bits)

        # Ensure no FEC falsely reports VALIDATED
        validated_codes = [h for h in fec_hyps if h["status"] == "VALIDATED"]
        assert len(validated_codes) == 0, (
            f"False positive FEC validation on random bits: {[c['type'] for c in validated_codes]}"
        )

    def test_viterbi_trellis_metric_on_noise_exceeds_threshold(self):
        """
        Hard-decision Viterbi on noise has path metric ~0.15 - 0.20,
        which must exceed the validation threshold tau = 0.08.
        """
        from core.fec import viterbi_decode
        np.random.seed(789)
        noise_bits = np.random.randint(0, 2, 300, dtype=np.uint8)
        dec, met = viterbi_decode(noise_bits, constraint_length=7)
        assert met["valid"] is False
        assert met["normalized_metric"] > 0.08
