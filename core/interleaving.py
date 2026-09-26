"""
Deinterleaving and Interleaving module for AutoSig-Intel.

Provides deterministic forward and inverse algorithms for:
- Block Interleaving (matrix row/column transposition)
- Convolutional Interleaving (Ramsey / Forney shift-register branches)
- Diagonal Interleaving (anti-diagonal matrix traversal)
- Pseudo-Random Interleaving (seeded permutation-based)
along with an evidence-driven Interleaver Hypothesis Engine.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
import numpy as np


# ============================================================
# BLOCK INTERLEAVING & DEINTERLEAVING
# ============================================================

def block_interleave(
    bits: np.ndarray,
    rows: int,
    cols: int
) -> np.ndarray:
    """
    Block interleaver.
    Transmitter writes bits row-wise into an (R x C) matrix
    and reads them out column-wise.

    Incomplete final blocks are preserved and appended at the end.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    rows = int(rows)
    cols = int(cols)
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1.")

    blk_size = rows * cols
    n_blocks = len(bits) // blk_size
    usable = n_blocks * blk_size

    out = []
    for i in range(n_blocks):
        block = bits[i * blk_size:(i + 1) * blk_size]
        matrix = block.reshape(rows, cols)
        out.extend(matrix.T.flatten())

    # Trailing bits from incomplete final block are preserved
    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


def block_deinterleave(
    bits: np.ndarray,
    rows: int,
    cols: int
) -> np.ndarray:
    """
    Block deinterleaver.
    Inverts block_interleave by writing received bits column-wise
    into an (R x C) matrix and reading them out row-wise.

    Incomplete final blocks are preserved and appended at the end.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    rows = int(rows)
    cols = int(cols)
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1.")

    blk_size = rows * cols
    n_blocks = len(bits) // blk_size
    usable = n_blocks * blk_size

    out = []
    for i in range(n_blocks):
        block = bits[i * blk_size:(i + 1) * blk_size]
        # Writing column-wise into (rows, cols) is equivalent to
        # reading row-wise into (cols, rows) and transposing.
        matrix = block.reshape(cols, rows)
        out.extend(matrix.T.flatten())

    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


# ============================================================
# CONVOLUTIONAL INTERLEAVING & DEINTERLEAVING
# ============================================================

def convolutional_interleave(
    bits: np.ndarray,
    branches: int = 4,
    branch_delay: int = 2
) -> np.ndarray:
    """
    Ramsey / Forney convolutional interleaver.
    Consists of B branches. Branch i has a shift register of length (i * M).
    Input bits are cyclically commutated across branches 0, 1, ..., B-1.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    branches = int(branches)
    branch_delay = int(branch_delay)
    if branches < 2:
        raise ValueError("branches must be >= 2.")
    if branch_delay < 1:
        raise ValueError("branch_delay must be >= 1.")

    n = len(bits)
    out = np.zeros(n, dtype=np.uint8)
    # Shift registers initialized with zeros
    regs = [list(np.zeros(i * branch_delay, dtype=np.uint8)) for i in range(branches)]

    for i in range(n):
        b = i % branches
        regs[b].append(int(bits[i]))
        out[i] = regs[b].pop(0)

    return out


def convolutional_deinterleave(
    bits: np.ndarray,
    branches: int = 4,
    branch_delay: int = 2
) -> np.ndarray:
    """
    Complementary convolutional deinterleaver.
    Branch i has a shift register of length ((B - 1 - i) * M).
    Total end-to-end delay through interleaver + deinterleaver is
    branches * (branches - 1) * branch_delay bits.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    branches = int(branches)
    branch_delay = int(branch_delay)
    if branches < 2:
        raise ValueError("branches must be >= 2.")
    if branch_delay < 1:
        raise ValueError("branch_delay must be >= 1.")

    n = len(bits)
    out = np.zeros(n, dtype=np.uint8)
    regs = [list(np.zeros((branches - 1 - i) * branch_delay, dtype=np.uint8)) for i in range(branches)]

    for i in range(n):
        b = i % branches
        regs[b].append(int(bits[i]))
        out[i] = regs[b].pop(0)

    return out


# ============================================================
# DIAGONAL INTERLEAVING & DEINTERLEAVING
# ============================================================

def _diagonal_permutation(rows: int, cols: int) -> np.ndarray:
    """
    Constructs the 1D index permutation corresponding to
    diagonal traversal of an (R x C) matrix.
    Diagonals d = r + c from 0 to R + C - 2.
    """
    indices = []
    for d in range(rows + cols - 1):
        for r in range(max(0, d - cols + 1), min(rows, d + 1)):
            c = d - r
            indices.append(r * cols + c)
    return np.asarray(indices, dtype=np.int64)


def diagonal_interleave(
    bits: np.ndarray,
    rows: int,
    cols: int
) -> np.ndarray:
    """
    Diagonal interleaver.
    Writes bits into an (R x C) matrix row-wise, and reads them
    out along anti-diagonals (r + c = constant).
    """
    bits = np.asarray(bits, dtype=np.uint8)
    rows = int(rows)
    cols = int(cols)
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1.")

    blk_size = rows * cols
    n_blocks = len(bits) // blk_size
    usable = n_blocks * blk_size
    perm = _diagonal_permutation(rows, cols)

    out = []
    for i in range(n_blocks):
        block = bits[i * blk_size:(i + 1) * blk_size]
        out.extend(block[perm])

    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


def diagonal_deinterleave(
    bits: np.ndarray,
    rows: int,
    cols: int
) -> np.ndarray:
    """
    Diagonal deinterleaver.
    Inverts diagonal_interleave using the inverse diagonal permutation.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    rows = int(rows)
    cols = int(cols)
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1.")

    blk_size = rows * cols
    n_blocks = len(bits) // blk_size
    usable = n_blocks * blk_size
    perm = _diagonal_permutation(rows, cols)
    inv_perm = np.argsort(perm)

    out = []
    for i in range(n_blocks):
        block = bits[i * blk_size:(i + 1) * blk_size]
        out.extend(block[inv_perm])

    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


# ============================================================
# PSEUDO-RANDOM INTERLEAVING & DEINTERLEAVING
# ============================================================

def pseudo_random_interleave(
    bits: np.ndarray,
    block_size: int = 64,
    seed: int = 42
) -> np.ndarray:
    """
    Pseudo-random interleaver using a deterministic pseudo-random permutation.
    Same seed produces the identical permutation; different seeds produce
    distinct permutations.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    block_size = int(block_size)
    if block_size < 2:
        raise ValueError("block_size must be >= 2.")

    rng = np.random.RandomState(seed)
    perm = rng.permutation(block_size)
    n_blocks = len(bits) // block_size
    usable = n_blocks * block_size

    out = []
    for i in range(n_blocks):
        block = bits[i * block_size:(i + 1) * block_size]
        out.extend(block[perm])

    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


def pseudo_random_deinterleave(
    bits: np.ndarray,
    block_size: int = 64,
    seed: int = 42
) -> np.ndarray:
    """
    Pseudo-random deinterleaver.
    Inverts pseudo_random_interleave using the exact inverse permutation.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    block_size = int(block_size)
    if block_size < 2:
        raise ValueError("block_size must be >= 2.")

    rng = np.random.RandomState(seed)
    perm = rng.permutation(block_size)
    inv_perm = np.argsort(perm)
    n_blocks = len(bits) // block_size
    usable = n_blocks * block_size

    out = []
    for i in range(n_blocks):
        block = bits[i * block_size:(i + 1) * block_size]
        out.extend(block[inv_perm])

    if usable < len(bits):
        out.extend(bits[usable:])

    return np.asarray(out, dtype=np.uint8)


# ============================================================
# INTERLEAVER HYPOTHESIS ENGINE
# ============================================================

def build_interleaver_candidate(
    interleaver_type: str,
    output_bits: np.ndarray,
    parameters: Dict[str, Any],
    input_bits: np.ndarray,
    score: float = 0.0,
    status: str = "HYPOTHESIS",
    evidence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standardized deinterleaver hypothesis report format.
    """
    return {
        "type": interleaver_type,
        "status": status,
        "parameters": parameters,
        "input_bits": np.asarray(input_bits, dtype=np.uint8),
        "output_bits": np.asarray(output_bits, dtype=np.uint8),
        "score": float(score),
        "evidence": evidence or {},
    }


def evaluate_interleaving_hypotheses(
    bits: np.ndarray,
    validator_fn: Optional[Callable[[np.ndarray], Tuple[bool, float, Dict[str, Any]]]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate candidate deinterleaver hypotheses.
    
    Evaluates:
    - Pass-through ('none')
    - Standard Block matrices: (8x8, 16x8, 8x16, 16x16, 32x8)
    - Convolutional deinterleaver: (B=4, M=2)
    - Diagonal deinterleaver: (8x8, 16x8)
    - Pseudo-random deinterleaver: (N=64, seed=42)

    If a downstream validator (e.g. FEC syndrome check or preamble match) is provided,
    hypotheses are scored by validation evidence.
    If no evidence distinguishes candidates, the top hypothesis reports type='UNKNOWN'
    with status='INSUFFICIENT_EVIDENCE'.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    if len(bits) == 0:
        return [build_interleaver_candidate("none", bits, {}, bits, score=0.0, status="INSUFFICIENT_DATA")]

    candidate_specs = [
        ("none", lambda b: b, {}),
        ("block", lambda b: block_deinterleave(b, 8, 8), {"rows": 8, "cols": 8}),
        ("block", lambda b: block_deinterleave(b, 16, 8), {"rows": 16, "cols": 8}),
        ("block", lambda b: block_deinterleave(b, 8, 16), {"rows": 8, "cols": 16}),
        ("block", lambda b: block_deinterleave(b, 16, 16), {"rows": 16, "cols": 16}),
        ("convolutional", lambda b: convolutional_deinterleave(b, 4, 2), {"branches": 4, "branch_delay": 2}),
        ("diagonal", lambda b: diagonal_deinterleave(b, 8, 8), {"rows": 8, "cols": 8}),
        ("pseudo_random", lambda b: pseudo_random_deinterleave(b, 64, 42), {"block_size": 64, "seed": 42}),
    ]

    results = []
    has_validation = False

    for itype, deint_fn, params in candidate_specs:
        try:
            out_bits = deint_fn(bits)
            if validator_fn is not None:
                is_valid, val_score, val_evidence = validator_fn(out_bits)
                if is_valid:
                    has_validation = True
                status = "VALIDATED" if is_valid else "EVALUATED"
                score = val_score
                evidence = val_evidence
            else:
                status = "HYPOTHESIS"
                score = 0.0
                evidence = {"reason": "No downstream protocol or FEC validator provided"}

            results.append(
                build_interleaver_candidate(
                    interleaver_type=itype,
                    output_bits=out_bits,
                    parameters=params,
                    input_bits=bits,
                    score=score,
                    status=status,
                    evidence=evidence,
                )
            )
        except Exception as exc:
            results.append(
                build_interleaver_candidate(
                    interleaver_type=itype,
                    output_bits=bits,
                    parameters=params,
                    input_bits=bits,
                    score=0.0,
                    status="FAILED",
                    evidence={"error": str(exc)},
                )
            )

    # Rank hypotheses by score
    results.sort(key=lambda h: h["score"], reverse=True)

    # If no evidence distinguishes candidates, report UNKNOWN
    if not has_validation:
        results.insert(
            0,
            build_interleaver_candidate(
                interleaver_type="UNKNOWN",
                output_bits=bits,
                parameters={},
                input_bits=bits,
                score=0.0,
                status="INSUFFICIENT_EVIDENCE",
                evidence={"reason": "Blind de-interleaving cannot be resolved without downstream FEC or frame sync word evidence."}
            )
        )

    return results


# Backward compatibility alias
test_interleaving_hypotheses = evaluate_interleaving_hypotheses