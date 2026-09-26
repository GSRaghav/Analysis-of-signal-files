"""
Frame Analysis and Multi-Hypothesis Decoding Orchestrator for AutoSig-Intel.

Connects:
Recovered bits -> Preamble search -> Candidate frame boundary ->
Header candidate -> Payload candidate -> Interleaver hypotheses ->
FEC hypotheses -> Validation -> Ranked decoding hypotheses.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np

from .correlation import (
    detect_preamble,
    detect_header_candidates,
    estimate_payload_boundaries,
    STANDARD_PREAMBLES,
)
from .interleaving import evaluate_interleaving_hypotheses
from .fec import evaluate_fec_hypotheses


def analyze_frame_hypotheses(
    bits: np.ndarray,
    modulation: str = "UNKNOWN",
    preambles: Optional[Dict[str, np.ndarray]] = None,
    header_length_bits: int = 32
) -> Dict[str, Any]:
    """
    Execute multi-hypothesis frame synchronization, deinterleaving, and FEC analysis.
    Preserves multiple alternative decoding hypotheses ranked by physical evidence.
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    if len(bits) == 0:
        return {
            "preamble": None,
            "frame_structure": None,
            "candidates": [],
            "best_decoding_hypothesis": {
                "modulation": modulation,
                "interleaver": "none",
                "fec": "none",
                "header_match": 0.0,
                "fec_valid": False,
                "overall_score": 0.0,
                "status": "INSUFFICIENT_DATA",
            }
        }

    # 1. Preamble Search
    preamble_match = detect_preamble(bits, preambles=preambles, max_bit_errors=2, threshold=0.80)

    candidates = []

    if preamble_match is not None and preamble_match["found"]:
        # Extract frame and header
        header_candidate = detect_header_candidates(
            bits,
            preamble_match,
            header_length_bits=header_length_bits
        )
        preamble_pattern = (
            preambles[preamble_match["pattern_type"]]
            if preambles and preamble_match["pattern_type"] in preambles
            else STANDARD_PREAMBLES.get(preamble_match["pattern_type"], np.array([], dtype=np.uint8))
        )
        boundaries = estimate_payload_boundaries(
            bits,
            preamble_pattern,
            header_length_bits=header_length_bits
        )

        # Extract payload bits (either from first detected frame or remaining bits)
        if boundaries["payload_segments"]:
            first_seg = boundaries["payload_segments"][0]
            payload_bits = bits[first_seg["payload_start"]:first_seg["payload_end"]]
        else:
            payload_bits = bits[preamble_match["end_index"]:]

        frame_info = {
            "preamble": preamble_match,
            "header": header_candidate,
            "boundaries": boundaries,
        }

        # 2. Test candidate payload start alignments (offset 0, 16, 32 after preamble)
        # Allows discovering whether a frame has no header, a 16-bit header, or a 32-bit header.
        cand_payload_segments = []
        p_end = preamble_match["end_index"]
        
        # If multiple preambles exist, limit payload length to one frame
        if boundaries["payload_segments"]:
            first_seg = boundaries["payload_segments"][0]
            max_p_len = first_seg["payload_end"] - p_end
        else:
            max_p_len = len(bits) - p_end

        for hdr_off in (0, 16, 32):
            if p_end + hdr_off < len(bits):
                start = p_end + hdr_off
                end = min(len(bits), p_end + max_p_len) if max_p_len > hdr_off else len(bits)
                if end - start >= 32:
                    cand_payload_segments.append((hdr_off, bits[start:end]))

        # Define downstream FEC validator to evaluate interleaver hypotheses
        def fec_validator(b):
            f_hyps = evaluate_fec_hypotheses(b)
            best_f = f_hyps[0] if f_hyps else None
            if best_f and best_f["status"] == "VALIDATED":
                return True, float(best_f["score"]), {"fec": best_f, "fec_hyps": f_hyps}
            return False, float(best_f["score"] if best_f else 0.0), {"fec": best_f, "fec_hyps": f_hyps}

        validated_found = False
        for hdr_off, payload_bits in cand_payload_segments:
            deint_hyps = evaluate_interleaving_hypotheses(payload_bits, validator_fn=fec_validator)

            for d_hyp in deint_hyps[:6]:
                fec_hyps = d_hyp.get("evidence", {}).get("fec_hyps")
                if not fec_hyps:
                    cand_bits = d_hyp["output_bits"]
                    fec_hyps = evaluate_fec_hypotheses(cand_bits)

                for f_hyp in fec_hyps[:4]:
                    p_gain = min(1.0, float(preamble_match["pattern_length"]) / 16.0)
                    h_score = float(preamble_match["score"]) * p_gain
                    f_score = float(f_hyp["score"])
                    fec_valid = f_hyp["status"] == "VALIDATED"
                    d_score = float(d_hyp["score"])

                    # If both interleaver and FEC validate, boost overall confidence
                    if fec_valid and d_hyp["status"] == "VALIDATED":
                        overall = 0.35 * h_score + 0.45 * f_score + 0.20 * d_score
                        is_validated = True
                        validated_found = True
                    elif fec_valid:
                        overall = 0.35 * h_score + 0.45 * f_score + 0.20 * max(0.5, d_score)
                        is_validated = True
                        validated_found = True
                    else:
                        overall = 0.50 * h_score + 0.35 * f_score + 0.15 * d_score
                        is_validated = h_score >= 0.95 and preamble_match["pattern_length"] >= 16

                    candidates.append({
                        "modulation": modulation,
                        "header_offset": hdr_off,
                        "interleaver": d_hyp["type"],
                        "interleaver_params": d_hyp["parameters"],
                        "fec": f_hyp["type"],
                        "fec_params": f_hyp["parameters"],
                        "header_match": h_score,
                        "fec_valid": fec_valid,
                        "overall_score": float(np.clip(overall, 0.0, 1.0)),
                        "status": "VALIDATED" if is_validated else "HYPOTHESIS",
                        "decoded_bits": f_hyp["output_bits"],
                    })

            if validated_found:
                break
    else:
        # No preamble detected -> evaluate raw stream directly with baseline FEC
        frame_info = None
        eval_bits = bits[:600] if len(bits) > 600 else bits
        fec_hyps = evaluate_fec_hypotheses(eval_bits)
        for f_hyp in fec_hyps[:3]:
            fec_valid = f_hyp["status"] == "VALIDATED"
            f_score = float(f_hyp["score"])
            candidates.append({
                "modulation": modulation,
                "header_offset": 0,
                "interleaver": "none",
                "interleaver_params": {},
                "fec": f_hyp["type"],
                "fec_params": f_hyp["parameters"],
                "header_match": 0.0,
                "fec_valid": fec_valid,
                "overall_score": float(np.clip(0.60 * f_score if fec_valid else 0.20 * f_score, 0.0, 1.0)),
                "status": "VALIDATED" if fec_valid else "INSUFFICIENT_EVIDENCE",
                "decoded_bits": f_hyp["output_bits"],
            })

    # Sort candidates descending by overall score
    candidates.sort(key=lambda c: c["overall_score"], reverse=True)
    best_candidate = candidates[0] if candidates else {
        "modulation": modulation,
        "interleaver": "none",
        "fec": "none",
        "header_match": 0.0,
        "fec_valid": False,
        "overall_score": 0.0,
        "status": "INSUFFICIENT_EVIDENCE",
    }

    return {
        "preamble": preamble_match,
        "frame_structure": frame_info,
        "candidates": candidates,
        "best_decoding_hypothesis": best_candidate,
    }
