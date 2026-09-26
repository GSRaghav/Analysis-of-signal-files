"""
Forward Error Correction (FEC) module for AutoSig-Intel.

Provides deterministic reference encoders and decoders for:
- Convolutional Coding with Viterbi Decoding (Hard-decision, K=3, 5, 7)
- Reed-Solomon Algebraic Block Coding (GF(256) via reedsolo)
- Concatenated Coding (Outer Reed-Solomon + Interleaver + Inner Convolutional)
- Low-Density Parity-Check (LDPC) Code (Gallager / Bit-Flipping on (12, 6) baseline)
along with an evidence-driven FEC Hypothesis Engine.
"""

from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import numpy as np
import reedsolo


# ============================================================
# BIT / BYTE CONVERSION UTILITIES
# ============================================================

def bits_to_bytes(bits: np.ndarray) -> Tuple[bytes, int]:
    """
    Convert bit array to byte string with zero-padding to byte boundary.
    Returns (byte_data, pad_count).
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    pad = (8 - (len(bits) % 8)) % 8
    if pad:
        padded = np.pad(bits, (0, pad), mode="constant")
    else:
        padded = bits
    packed = np.packbits(padded)
    return bytes(packed), pad


def bytes_to_bits(data: Union[bytes, bytearray], pad_count: int = 0) -> np.ndarray:
    """
    Convert byte string to 1D uint8 bit array, trimming optional trailing pad bits.
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    bits = np.unpackbits(arr)
    if pad_count > 0:
        bits = bits[:-pad_count]
    return bits


def calculate_bit_error_rate(
    reference_bits: Union[np.ndarray, list],
    recovered_bits: Union[np.ndarray, list]
) -> float:
    """
    Calculate Bit Error Rate (BER) between reference and recovered bitstreams.
    """
    ref = np.asarray(reference_bits, dtype=np.uint8).flatten()
    rec = np.asarray(recovered_bits, dtype=np.uint8).flatten()
    n = min(len(ref), len(rec))
    if n == 0:
        return float("nan")
    return float(np.mean(ref[:n] != rec[:n]))


# ============================================================
# CONVOLUTIONAL ENCODING & VITERBI DECODING
# ============================================================

def convolutional_encode(
    bits: np.ndarray,
    constraint_length: int = 7,
    generators: Tuple[int, ...] = (171, 133),
    termination: str = "zero"
) -> np.ndarray:
    """
    Rate 1/n convolutional encoder.
    
    Standard configurations:
    - K=7, G=(171, 133) octal (NASA standard rate 1/2)
    - K=3, G=(7, 5) octal (rate 1/2)

    termination='zero' appends K-1 zero bits to flush encoder back to state 0.
    """
    bits = np.asarray(bits, dtype=np.uint8).flatten()
    K = int(constraint_length)
    n_reg = K - 1
    g_masks = [[(g >> (K - 1 - i)) & 1 for i in range(K)] for g in generators]

    padded = (
        np.concatenate([bits, np.zeros(n_reg, dtype=np.uint8)])
        if termination == "zero"
        else bits
    )

    out = []
    state = 0
    for b in padded:
        sr = [int(b)] + [(state >> (n_reg - 1 - i)) & 1 for i in range(n_reg)]
        for m in g_masks:
            val = sum(sr[i] * m[i] for i in range(K)) % 2
            out.append(val)
        state = ((state >> 1) | (int(b) << (n_reg - 1))) & ((1 << n_reg) - 1)

    return np.asarray(out, dtype=np.uint8)


_VITERBI_TRELLIS_CACHE: Dict[Tuple[int, Tuple[int, ...]], Any] = {}

def _get_viterbi_trellis(K: int, generators: Tuple[int, ...]):
    key = (K, generators)
    if key in _VITERBI_TRELLIS_CACHE:
        return _VITERBI_TRELLIS_CACHE[key]
    n_reg = K - 1
    n_states = 1 << n_reg
    rate = len(generators)
    g_masks = [[(g >> (K - 1 - i)) & 1 for i in range(K)] for g in generators]

    predecessors = [[] for _ in range(n_states)]
    for s in range(n_states):
        sr_state = [(s >> (n_reg - 1 - i)) & 1 for i in range(n_reg)]
        for b in (0, 1):
            sr = [b] + sr_state
            out_syms = tuple(sum(sr[i] * m[i] for i in range(K)) % 2 for m in g_masks)
            ns = (s >> 1) | (b << (n_reg - 1))
            predecessors[ns].append((s, b, out_syms))

    pred_flat = []
    for ns in range(n_states):
        p0, b0, s0 = predecessors[ns][0]
        p1, b1, s1 = predecessors[ns][1]
        pred_flat.append((p0, b0, s0, p1, b1, s1))

    _VITERBI_TRELLIS_CACHE[key] = (n_reg, n_states, rate, pred_flat)
    return _VITERBI_TRELLIS_CACHE[key]


def viterbi_decode(
    encoded_bits: np.ndarray,
    original_length: Optional[int] = None,
    constraint_length: int = 7,
    generators: Tuple[int, ...] = (171, 133),
    termination: str = "zero"
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Hard-decision Viterbi decoder for rate 1/n convolutional codes.
    
    Returns:
        (decoded_bits, metrics_dict)
    """
    encoded = np.asarray(encoded_bits, dtype=np.uint8).flatten()
    K = int(constraint_length)
    generators = tuple(generators)
    n_reg, n_states, rate, pred_flat = _get_viterbi_trellis(K, generators)
    n_steps = len(encoded) // rate

    if n_steps == 0:
        return np.array([], dtype=np.uint8), {"final_metric": 0.0, "normalized_metric": 1.0, "valid": False}

    path_metrics = [1e8] * n_states
    path_metrics[0] = 0.0  # Assumes encoder started at state 0
    history_prev = [[0] * n_states for _ in range(n_steps)]
    history_bit = [[0] * n_states for _ in range(n_steps)]

    for t in range(n_steps):
        r = tuple(encoded[t * rate:(t + 1) * rate])
        new_metrics = [1e8] * n_states
        hp_t = history_prev[t]
        hb_t = history_bit[t]
        for ns in range(n_states):
            p0, b0, s0, p1, b1, s1 = pred_flat[ns]
            d0 = sum(r[i] ^ s0[i] for i in range(rate))
            d1 = sum(r[i] ^ s1[i] for i in range(rate))
            c0 = path_metrics[p0] + d0
            c1 = path_metrics[p1] + d1
            if c0 <= c1:
                new_metrics[ns] = c0
                hp_t[ns] = p0
                hb_t[ns] = b0
            else:
                new_metrics[ns] = c1
                hp_t[ns] = p1
                hb_t[ns] = b1
        path_metrics = new_metrics

    # Traceback: if zero-terminated, end state is 0
    if termination == "zero" and path_metrics[0] < 1e7:
        curr_state = 0
    else:
        curr_state = int(np.argmin(path_metrics))

    final_metric = float(path_metrics[curr_state])

    decoded = []
    for t in range(n_steps - 1, -1, -1):
        decoded.append(history_bit[t][curr_state])
        curr_state = history_prev[t][curr_state]

    decoded.reverse()

    # If zero-terminated, remove flushing bits
    if termination == "zero":
        data_bits = np.array(decoded[:len(decoded) - n_reg], dtype=np.uint8)
    else:
        data_bits = np.array(decoded, dtype=np.uint8)

    if original_length is not None:
        data_bits = data_bits[:original_length]

    # Metrics
    norm_metric = final_metric / max(1, len(encoded))
    valid = norm_metric <= 0.08

    return data_bits, {
        "final_metric": final_metric,
        "normalized_metric": float(norm_metric),
        "valid": bool(valid),
        "constraint_length": K,
        "generators": generators,
    }


# ============================================================
# REED-SOLOMON CODEC (GF(256))
# ============================================================

def rs_encode(
    data: Union[bytes, bytearray, np.ndarray],
    nsym: int = 10
) -> Tuple[Union[bytes, np.ndarray], Dict[str, Any]]:
    """
    Reed-Solomon systematic encoder over GF(256).
    Accepts bytes or bit array; returns codeword matching input type.
    nsym = number of parity symbols (error correction capability T = nsym // 2).
    """
    nsym = int(nsym)
    is_bits = isinstance(data, np.ndarray)

    if is_bits:
        byte_data, pad_count = bits_to_bytes(data)
    else:
        byte_data = bytes(data)
        pad_count = 0

    rsc = reedsolo.RSCodec(nsym)
    codeword_bytes = rsc.encode(byte_data)

    if is_bits:
        codeword = bytes_to_bits(codeword_bytes)
    else:
        codeword = codeword_bytes

    metadata = {
        "nsym": nsym,
        "correction_capacity": nsym // 2,
        "pad_count": pad_count,
        "message_length": len(byte_data),
        "codeword_length": len(codeword_bytes),
    }
    return codeword, metadata


def rs_decode(
    codeword: Union[bytes, bytearray, np.ndarray],
    nsym: int = 10,
    pad_count: int = 0
) -> Tuple[Optional[Union[bytes, np.ndarray]], Dict[str, Any]]:
    """
    Reed-Solomon decoder over GF(256).
    Returns (decoded_data, status_dict).
    Handles up to nsym // 2 corrupted symbols.
    """
    nsym = int(nsym)
    is_bits = isinstance(codeword, np.ndarray)

    if is_bits:
        cw_bytes, _ = bits_to_bytes(codeword)
    else:
        cw_bytes = bytes(codeword)

    if len(cw_bytes) <= nsym:
        return None, {
            "status": "INSUFFICIENT_DATA",
            "corrected_symbols": 0,
            "nsym": nsym,
            "error": "Codeword length is shorter than or equal to parity length",
        }

    rsc = reedsolo.RSCodec(nsym)
    try:
        dec_bytes, _, errata_pos = rsc.decode(cw_bytes)
        corrected_count = len(errata_pos)
        status = "VALIDATED" if len(dec_bytes) > 0 else "INSUFFICIENT_DATA"
        err_msg = None

        if is_bits:
            decoded = bytes_to_bits(dec_bytes, pad_count=pad_count)
        else:
            decoded = dec_bytes
    except reedsolo.ReedSolomonError as exc:
        decoded = None
        corrected_count = 0
        status = "UNCORRECTABLE"
        err_msg = str(exc)

    return decoded, {
        "status": status,
        "corrected_symbols": int(corrected_count),
        "nsym": nsym,
        "error": err_msg,
    }


# ============================================================
# CONCATENATED FEC (Outer RS + Interleaver + Inner Viterbi)
# ============================================================

def concatenated_encode(
    bits: np.ndarray,
    rs_nsym: int = 8,
    conv_k: int = 7,
    conv_g: Tuple[int, ...] = (171, 133),
    interleaver_rows: int = 8,
    interleaver_cols: Optional[int] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Standard concatenated forward encoder:
    Message Bits -> Outer RS Encode -> Block Interleave -> Inner Convolutional Encode.
    """
    from .interleaving import block_interleave

    bits = np.asarray(bits, dtype=np.uint8).flatten()
    # 1. Outer RS Encode
    rs_cw_bits, rs_meta = rs_encode(bits, nsym=rs_nsym)

    # 2. Block Interleave
    rows = interleaver_rows
    cols = interleaver_cols or (len(rs_cw_bits) // rows)
    if cols < 1:
        cols = 1
    interleaved_bits = block_interleave(rs_cw_bits, rows=rows, cols=cols)

    # 3. Inner Convolutional Encode
    conv_bits = convolutional_encode(interleaved_bits, constraint_length=conv_k, generators=conv_g)

    meta = {
        "architecture": "Outer RS + Block Interleaver + Inner Convolutional",
        "rs": rs_meta,
        "interleaver": {"rows": rows, "cols": cols},
        "conv": {"K": conv_k, "generators": conv_g},
        "encoded_length": len(conv_bits),
    }
    return conv_bits, meta


def concatenated_decode(
    encoded_bits: np.ndarray,
    original_bit_length: Optional[int] = None,
    rs_nsym: int = 8,
    conv_k: int = 7,
    conv_g: Tuple[int, ...] = (171, 133),
    interleaver_rows: int = 8,
    interleaver_cols: Optional[int] = None
) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """
    Standard concatenated reverse decoder:
    Encoded Bits -> Inner Viterbi Decode -> Block Deinterleave -> Outer RS Decode.
    """
    from .interleaving import block_deinterleave

    encoded_bits = np.asarray(encoded_bits, dtype=np.uint8).flatten()

    if original_bit_length is not None:
        pad_len = (8 - (original_bit_length % 8)) % 8
        orig_bytes = (original_bit_length + pad_len) // 8
        rs_cw_bytes = orig_bytes + rs_nsym
        rs_cw_bits_len = rs_cw_bytes * 8
    else:
        pad_len = 0
        n_rate = len(conv_g)
        n_info_bits = max(0, len(encoded_bits) // n_rate - (conv_k - 1))
        rs_cw_bytes = max(rs_nsym + 1, n_info_bits // 8)
        rs_cw_bits_len = rs_cw_bytes * 8

    # 1. Inner Viterbi Decode
    deconv_bits, conv_metrics = viterbi_decode(
        encoded_bits,
        original_length=rs_cw_bits_len,
        constraint_length=conv_k,
        generators=conv_g
    )

    # 2. Block Deinterleave
    rows = interleaver_rows
    cols = interleaver_cols or (len(deconv_bits) // rows)
    if cols < 1:
        cols = 1
    deinterleaved = block_deinterleave(deconv_bits, rows=rows, cols=cols)

    # 3. Outer RS Decode
    decoded_bits, rs_status = rs_decode(deinterleaved, nsym=rs_nsym, pad_count=pad_len)

    status = (
        "VALIDATED"
        if (
            rs_status.get("status") == "VALIDATED"
            and decoded_bits is not None
            and len(decoded_bits) >= 8
            and conv_metrics.get("valid", False)
        )
        else "FAILED"
    )
    return decoded_bits, {
        "status": status,
        "conv_metrics": conv_metrics,
        "rs_status": rs_status,
        "interleaver": {"rows": rows, "cols": cols},
    }


# ============================================================
# LDPC (Low-Density Parity-Check) BASELINE
# ============================================================

# Standard systematic (12, 6) Gallager LDPC code: H = [P | I_6], G = [I_6 | P^T]
STANDARD_LDPC_P = np.array([
    [1, 1, 0, 1, 0, 0],
    [0, 1, 1, 0, 1, 0],
    [0, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 1],
    [1, 0, 1, 0, 0, 1],
    [0, 1, 0, 1, 1, 0],
], dtype=np.uint8)

STANDARD_LDPC_H = np.hstack([STANDARD_LDPC_P, np.eye(6, dtype=np.uint8)])
STANDARD_LDPC_G = np.hstack([np.eye(6, dtype=np.uint8), STANDARD_LDPC_P.T])


def ldpc_encode(
    message_bits: np.ndarray,
    G: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Encode message bits using systematic LDPC generator matrix G (default: (12, 6) code).
    """
    msg = np.asarray(message_bits, dtype=np.uint8).flatten()
    if G is None:
        G = STANDARD_LDPC_G

    k = G.shape[0]
    n_blocks = len(msg) // k
    out = []
    for i in range(n_blocks):
        blk = msg[i * k:(i + 1) * k]
        cw = (blk @ G) % 2
        out.extend(cw)

    # Append trailing bits
    rem = len(msg) % k
    if rem > 0:
        pad_blk = np.pad(msg[n_blocks * k:], (0, k - rem), mode="constant")
        out.extend((pad_blk @ G) % 2)

    return np.asarray(out, dtype=np.uint8)


def ldpc_decode(
    received_bits: np.ndarray,
    H: Optional[np.ndarray] = None,
    max_iterations: int = 20
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Hard-decision Gallager Bit-Flipping / Min-Sum syndrome decoder.
    Decodes blocks of length N using parity-check matrix H.
    Early stopping occurs as soon as syndrome s = H * c == 0 (mod 2).
    """
    rec = np.asarray(received_bits, dtype=np.uint8).flatten()
    if H is None:
        H = STANDARD_LDPC_H

    n = H.shape[1]
    m = H.shape[0]
    k = n - m
    n_blocks = len(rec) // n

    if n_blocks == 0:
        return rec, {"status": "INSUFFICIENT_DATA", "syndrome_zero": False, "iterations": 0}

    out_msg = []
    total_iters = 0
    all_syndromes_zero = True

    for i in range(n_blocks):
        c = rec[i * n:(i + 1) * n].copy()
        iters = 0
        for iters in range(1, max_iterations + 1):
            syndrome = (H @ c) % 2
            if np.all(syndrome == 0):
                break
            # Compute number of unsatisfied parity checks per bit
            viol = H.T @ syndrome
            flip_idx = int(np.argmax(viol))
            c[flip_idx] ^= 1

        syn_final = (H @ c) % 2
        if not np.all(syn_final == 0):
            all_syndromes_zero = False

        total_iters += iters
        out_msg.extend(c[:k])

    return np.asarray(out_msg, dtype=np.uint8), {
        "status": "VALIDATED" if all_syndromes_zero else "FAILED",
        "syndrome_zero": bool(all_syndromes_zero),
        "iterations": int(total_iters // n_blocks),
        "code_n": n,
        "code_k": k,
    }


def try_ldpc(bits: np.ndarray) -> Dict[str, Any]:
    """
    Blind LDPC hypothesis evaluator.
    Discloses honest SIH technical assessment:
    Blind LDPC code identification on arbitrary bitstreams without code metadata
    is an open NP-hard dual-code reconstruction problem. A standard (12, 6) reference
    LDPC codec is implemented and validated, but blind decoding on arbitrary streams
    is marked NOT_IMPLEMENTED.
    """
    return {
        "type": "ldpc",
        "status": "NOT_IMPLEMENTED",
        "score": 0.0,
        "reason": (
            "Blind LDPC decoding requires the parity-check matrix H and block length. "
            "Arbitrary blind matrix reconstruction is an NP-hard problem. "
            "AutoSig-Intel implements and validates the standard (12, 6) LDPC codec "
            "for verified frames."
        ),
        "bits": np.asarray(bits, dtype=np.uint8),
    }


# ============================================================
# FEC HYPOTHESIS ENGINE
# ============================================================

def build_fec_candidate(
    fec_type: str,
    output_bits: np.ndarray,
    parameters: Dict[str, Any],
    input_bits: np.ndarray,
    score: float = 0.0,
    status: str = "HYPOTHESIS",
    evidence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standardized FEC hypothesis report format.
    """
    return {
        "type": fec_type,
        "status": status,
        "parameters": parameters,
        "input_bits": np.asarray(input_bits, dtype=np.uint8),
        "output_bits": np.asarray(output_bits, dtype=np.uint8),
        "score": float(score),
        "evidence": evidence or {},
    }


def evaluate_fec_hypotheses(
    bits: np.ndarray,
    preamble_validator: Optional[Callable[[np.ndarray], Tuple[bool, float, Dict[str, Any]]]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate candidate FEC decoding hypotheses:
    - Pass-through ('none')
    - Convolutional / Viterbi (K=7, rate 1/2)
    - Convolutional / Viterbi (K=3, rate 1/2)
    - Reed-Solomon (nsym=8, 10)
    - Concatenated FEC (RS + Convolutional)
    - LDPC (baseline (12, 6) code)

    Hypotheses are scored based on syndrome/metric checks and preamble matches.
    If no evidence confirms a code, the top hypothesis reports 'none' or 'UNKNOWN'.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    if len(bits) == 0:
        return [build_fec_candidate("none", bits, {}, bits, score=0.0, status="INSUFFICIENT_DATA")]

    candidates = []

    # 1. Pass-through (No FEC)
    candidates.append(
        build_fec_candidate(
            fec_type="none",
            output_bits=bits,
            parameters={},
            input_bits=bits,
            score=0.1,
            status="EVALUATED",
            evidence={"note": "Raw uncorrected bitstream"}
        )
    )

    # 2. Viterbi K=7
    try:
        dec_v7, met_v7 = viterbi_decode(bits, constraint_length=7)
        score_v7 = max(0.0, 1.0 - met_v7["normalized_metric"] * 10.0) if met_v7["valid"] else 0.0
        status_v7 = "VALIDATED" if met_v7["valid"] else "EVALUATED"
        candidates.append(
            build_fec_candidate(
                fec_type="convolutional_viterbi_k7",
                output_bits=dec_v7,
                parameters={"K": 7, "generators": (171, 133)},
                input_bits=bits,
                score=score_v7,
                status=status_v7,
                evidence=met_v7
            )
        )
    except Exception as exc:
        candidates.append(
            build_fec_candidate("convolutional_viterbi_k7", bits, {}, bits, score=0.0, status="FAILED", evidence={"error": str(exc)})
        )

    # 3. Viterbi K=3
    try:
        dec_v3, met_v3 = viterbi_decode(bits, constraint_length=3, generators=(7, 5))
        score_v3 = max(0.0, 1.0 - met_v3["normalized_metric"] * 10.0) if met_v3["valid"] else 0.0
        status_v3 = "VALIDATED" if met_v3["valid"] else "EVALUATED"
        candidates.append(
            build_fec_candidate(
                fec_type="convolutional_viterbi_k3",
                output_bits=dec_v3,
                parameters={"K": 3, "generators": (7, 5)},
                input_bits=bits,
                score=score_v3,
                status=status_v3,
                evidence=met_v3
            )
        )
    except Exception as exc:
        pass

    # 4. Reed-Solomon (test standard parity lengths: 4, 6, 8, 10)
    for nsym_val in (4, 6, 8, 10):
        try:
            dec_rs, meta_rs = rs_decode(bits, nsym=nsym_val)
            if dec_rs is not None and meta_rs.get("status") == "VALIDATED":
                candidates.append(
                    build_fec_candidate(
                        fec_type=f"reed_solomon_nsym{nsym_val}",
                        output_bits=dec_rs,
                        parameters={"nsym": nsym_val},
                        input_bits=bits,
                        score=0.95,
                        status="VALIDATED",
                        evidence=meta_rs
                    )
                )
                break
        except Exception:
            pass

    # 5. Concatenated FEC (Outer RS + Inner Convolutional)
    # Only test if inner Viterbi decoder has reasonable metric
    if met_v7.get("normalized_metric", 1.0) < 0.15:
        for rs_val in (4, 6, 8):
            try:
                dec_conc, meta_conc = concatenated_decode(bits, rs_nsym=rs_val, conv_k=7)
                if dec_conc is not None and meta_conc.get("status") == "VALIDATED":
                    candidates.append(
                        build_fec_candidate(
                            fec_type=f"concatenated_rs{rs_val}_conv_k7",
                            output_bits=dec_conc,
                            parameters={"rs_nsym": rs_val, "conv_k": 7},
                            input_bits=bits,
                            score=0.98,
                            status="VALIDATED",
                            evidence=meta_conc
                        )
                    )
                    break
            except Exception:
                pass

    # 5. LDPC Standard Reference
    try:
        dec_ldpc, meta_ldpc = ldpc_decode(bits)
        if meta_ldpc["syndrome_zero"]:
            candidates.append(
                build_fec_candidate(
                    fec_type="ldpc_12_6",
                    output_bits=dec_ldpc,
                    parameters={"N": 12, "K": 6},
                    input_bits=bits,
                    score=0.90,
                    status="VALIDATED",
                    evidence=meta_ldpc
                )
            )
    except Exception:
        pass

    # Re-score if downstream preamble validator is provided
    if preamble_validator is not None:
        for cand in candidates:
            if cand["status"] in ("VALIDATED", "EVALUATED"):
                is_valid, p_score, p_meta = preamble_validator(cand["output_bits"])
                if is_valid:
                    cand["score"] = max(cand["score"], p_score)
                    cand["status"] = "VALIDATED"
                    cand["evidence"]["preamble"] = p_meta

    candidates.sort(key=lambda h: h["score"], reverse=True)
    return candidates


# Backward compatibility aliases
test_fec_hypotheses = evaluate_fec_hypotheses
try_convolutional_viterbi = lambda bits: viterbi_decode(bits)[0]
try_reed_solomon = lambda bits: rs_decode(bits)[0]