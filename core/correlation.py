"""
Bitstream Correlation and Frame Synchronization module for AutoSig-Intel.

Provides:
- Exact and noisy bit-pattern correlation (Hamming-distance based)
- Preamble & Sync Word detection (CCSDS ASM, Barker-11/13, 0xAA55, custom)
- Header candidate detection and field extraction
- Periodic frame boundary and payload range estimation
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np


# ============================================================
# STANDARD PREAMBLES & SYNC WORDS
# ============================================================

STANDARD_PREAMBLES: Dict[str, np.ndarray] = {
    # CCSDS 32-bit Attached Sync Marker (0x1ACFFC1D)
    "CCSDS_ASM": np.array([
        0, 0, 0, 1, 1, 0, 1, 0,
        1, 1, 0, 0, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 0, 0,
        0, 0, 0, 1, 1, 1, 0, 1
    ], dtype=np.uint8),

    # 11-bit Barker code (IEEE 802.11 DSSS)
    "BARKER_11": np.array([1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0], dtype=np.uint8),

    # 13-bit Barker code
    "BARKER_13": np.array([1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8),

    # Alternating 16-bit Preamble Word (0xAA55)
    "SYNC_AA55": np.array([
        1, 0, 1, 0, 1, 0, 1, 0,
        0, 1, 0, 1, 0, 1, 0, 1
    ], dtype=np.uint8),

    # Standard High-Level Data Link Control (HDLC) Flag (0x7E: 01111110)
    "HDLC_FLAG": np.array([0, 1, 1, 1, 1, 1, 1, 0], dtype=np.uint8),
}


# ============================================================
# BASIC BIT SIMILARITY (Backward Compatibility)
# ============================================================

def bit_similarity(
    bits_a: Union[np.ndarray, list],
    bits_b: Union[np.ndarray, list]
) -> float:
    """
    Fraction of matching bits between two sequences over overlapping length.
    """
    a = np.asarray(bits_a, dtype=np.uint8).flatten()
    b = np.asarray(bits_b, dtype=np.uint8).flatten()
    n = min(len(a), len(b))
    if n == 0:
        return float("nan")
    return float(np.mean(a[:n] == b[:n]))


def find_common_sequence(
    bits_a: Union[np.ndarray, list],
    bits_b: Union[np.ndarray, list],
    min_length: int = 16
) -> Optional[Dict[str, int]]:
    """
    Find the longest common contiguous matching sequence beginning at corresponding positions.
    """
    a = np.asarray(bits_a, dtype=np.uint8).flatten()
    b = np.asarray(bits_b, dtype=np.uint8).flatten()
    n = min(len(a), len(b))
    if n < min_length:
        return None

    best_start = None
    best_length = 0
    current_start = None
    current_length = 0

    for i in range(n):
        if a[i] == b[i]:
            if current_start is None:
                current_start = i
            current_length += 1
        else:
            if current_length > best_length:
                best_start = current_start
                best_length = current_length
            current_start = None
            current_length = 0

    if current_length > best_length:
        best_start = current_start
        best_length = current_length

    if best_length < min_length:
        return None

    return {
        "start": int(best_start),
        "length": int(best_length),
    }


# ============================================================
# BITSTREAM CORRELATION & PATTERN SEARCH
# ============================================================

def correlate_pattern(
    bits: Union[np.ndarray, list],
    pattern: Union[np.ndarray, list, str],
    max_bit_errors: int = 0,
    threshold: float = 0.85,
    pattern_type: str = "custom"
) -> List[Dict[str, Any]]:
    """
    Search bitstream for occurrences of a bit pattern supporting noisy matching.
    
    Returns list of matches ordered by correlation score:
    {
        "found": True,
        "start_index": int,
        "end_index": int,
        "score": float (1.0 = exact match),
        "matched_bits": int,
        "bit_errors": int,
        "pattern_length": int,
        "pattern_type": str
    }
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    if isinstance(pattern, str):
        # Interpret string of '0' and '1'
        pattern = np.array([int(c) for c in pattern if c in "01"], dtype=np.uint8)
    else:
        pattern = np.asarray(pattern, dtype=np.uint8).flatten()

    p_len = len(pattern)
    n_bits = len(bits)
    if p_len == 0 or n_bits < p_len:
        return []

    matches = []
    # Slide pattern across bitstream
    for i in range(n_bits - p_len + 1):
        window = bits[i:i + p_len]
        diffs = int(np.sum(window != pattern))
        score = float((p_len - diffs) / p_len)

        if diffs <= max_bit_errors or score >= threshold:
            matches.append({
                "found": True,
                "start_index": int(i),
                "end_index": int(i + p_len),
                "score": float(score),
                "matched_bits": int(p_len - diffs),
                "bit_errors": int(diffs),
                "pattern_length": int(p_len),
                "pattern_type": pattern_type,
            })

    # Sort descending by score
    matches.sort(key=lambda m: (m["score"], -m["bit_errors"]), reverse=True)
    return matches


def detect_preamble(
    bits: Union[np.ndarray, list],
    preambles: Optional[Dict[str, np.ndarray]] = None,
    max_bit_errors: int = 1,
    threshold: float = 0.85
) -> Optional[Dict[str, Any]]:
    """
    Test bitstream against standard or supplied preambles and return the best match.
    """
    if preambles is None:
        preambles = STANDARD_PREAMBLES

    best_match = None
    best_rank = (-1.0, 0, -999)

    for name, pattern in preambles.items():
        candidates = correlate_pattern(
            bits,
            pattern,
            max_bit_errors=max_bit_errors,
            threshold=threshold,
            pattern_type=name
        )
        if candidates:
            top = candidates[0]
            # Prioritize score and pattern length: (score, pattern_length, -bit_errors)
            # A 32-bit ASM with score 1.0 must always beat an 8-bit flag with score 1.0
            rank = (float(top["score"]), int(top["pattern_length"]), -int(top["bit_errors"]))
            if rank > best_rank:
                best_rank = rank
                best_match = top

    return best_match


# ============================================================
# FRAME BOUNDARY & HEADER ESTIMATION
# ============================================================

def detect_header_candidates(
    bits: Union[np.ndarray, list],
    preamble_match: Dict[str, Any],
    header_length_bits: int = 32
) -> Optional[Dict[str, Any]]:
    """
    Extract candidate header bits immediately following a validated preamble.
    Extracts potential frame length / sequence fields.
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    end_idx = preamble_match["end_index"]

    if len(bits) < end_idx + header_length_bits:
        return None

    header_bits = bits[end_idx:end_idx + header_length_bits]
    header_bytes = np.packbits(header_bits)

    # Candidate 16-bit length (big-endian and little-endian hypotheses)
    len_be = int(header_bytes[0]) << 8 | int(header_bytes[1]) if len(header_bytes) >= 2 else 0
    len_le = int(header_bytes[1]) << 8 | int(header_bytes[0]) if len(header_bytes) >= 2 else 0

    return {
        "header_start": int(end_idx),
        "header_end": int(end_idx + header_length_bits),
        "header_bits": header_bits,
        "header_bytes": header_bytes.tolist(),
        "header_hex": "".join(f"{b:02X}" for b in header_bytes),
        "candidate_length_be": len_be,
        "candidate_length_le": len_le,
    }


def estimate_payload_boundaries(
    bits: Union[np.ndarray, list],
    preamble_pattern: Union[np.ndarray, list],
    header_length_bits: int = 32,
    max_bit_errors: int = 1
) -> Dict[str, Any]:
    """
    Estimate frame period and payload boundaries using periodic preamble occurrences.
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    all_preambles = correlate_pattern(bits, preamble_pattern, max_bit_errors=max_bit_errors, threshold=0.85)

    if not all_preambles:
        return {
            "frames_found": 0,
            "estimated_frame_length": None,
            "payload_segments": [],
        }

    # Extract start indices of preambles
    indices = sorted([m["start_index"] for m in all_preambles])
    p_len = len(preamble_pattern)

    # Estimate frame period from inter-preamble intervals
    if len(indices) >= 2:
        diffs = np.diff(indices)
        est_frame_len = int(np.median(diffs))
    else:
        est_frame_len = None

    payload_segments = []
    for i, start_idx in enumerate(indices):
        payload_start = start_idx + p_len + header_length_bits
        if i + 1 < len(indices):
            payload_end = indices[i + 1]
        elif est_frame_len is not None:
            payload_end = min(len(bits), start_idx + est_frame_len)
        else:
            payload_end = len(bits)

        if payload_end > payload_start:
            payload_segments.append({
                "frame_index": i,
                "payload_start": int(payload_start),
                "payload_end": int(payload_end),
                "payload_length_bits": int(payload_end - payload_start),
            })

    return {
        "frames_found": len(indices),
        "estimated_frame_length": est_frame_len,
        "preamble_indices": indices,
        "payload_segments": payload_segments,
    }