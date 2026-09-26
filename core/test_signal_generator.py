"""
Deterministic Golden Synthetic Signal Generator for AutoSig-Intel (SIH26147).

Constructs complete forward transmission pipelines:
Payload Bits
   ↓
Frame / Preamble & Header
   ↓
Forward Error Correction (FEC)
   ↓
Interleaving
   ↓
Digital Modulation (BPSK, QPSK, 16-QAM, 2-FSK)
   ↓
Oversampling & Pulse Shaping
   ↓
Channel Impairments (CFO, Phase Offset, Timing Offset, AWGN)
   ↓
Calibrated IQ Capture & Ground-Truth Metadata
"""

from typing import Dict, Any, Optional, Tuple, Union, List
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

from .interleaving import (
    block_interleave,
    convolutional_interleave,
    diagonal_interleave,
    pseudo_random_interleave,
)
from .fec import (
    convolutional_encode,
    rs_encode,
    concatenated_encode,
    ldpc_encode,
)
from .correlation import STANDARD_PREAMBLES


@dataclass
class SyntheticTransmission:
    """Container for generated transmission, ground truth, and intermediate stages."""
    samples: np.ndarray
    sample_rate: float
    metadata: Dict[str, Any]
    payload_bits: np.ndarray
    intermediate: Dict[str, Any]

    def to_wav(self, path: Union[str, Path]) -> Path:
        """Save complex IQ as calibrated 2-channel WAV (ch0=I, ch1=Q)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if sf is None:
            raise RuntimeError("soundfile library is required to save WAV.")
        stereo = np.column_stack([np.real(self.samples), np.imag(self.samples)]).astype(np.float32)
        sf.write(str(p), stereo, int(self.sample_rate))
        return p

    def to_iq(self, path: Union[str, Path], dtype: str = "float32", iq_order: str = "IQ") -> Path:
        """Save raw interleaved binary IQ."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        real_part = np.real(self.samples)
        imag_part = np.imag(self.samples)
        if iq_order == "QI":
            c0, c1 = imag_part, real_part
        else:
            c0, c1 = real_part, imag_part

        if dtype == "float32":
            interleaved = np.empty(2 * len(self.samples), dtype=np.float32)
            interleaved[0::2] = c0.astype(np.float32)
            interleaved[1::2] = c1.astype(np.float32)
        elif dtype == "int16":
            scale = 30000.0 / max(1e-6, np.max(np.abs(self.samples)))
            interleaved = np.empty(2 * len(self.samples), dtype=np.int16)
            interleaved[0::2] = np.clip(c0 * scale, -32767, 32767).astype(np.int16)
            interleaved[1::2] = np.clip(c1 * scale, -32767, 32767).astype(np.int16)
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")

        interleaved.tofile(str(p))
        return p

    def to_json(self, path: Union[str, Path]) -> Path:
        """Save ground truth metadata to JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(
                self.metadata,
                f,
                indent=2,
                default=lambda o: (
                    o.tolist() if isinstance(o, np.ndarray)
                    else o.item() if isinstance(o, np.generic)
                    else str(o)
                )
            )
        return p


def text_to_bits(text: str) -> np.ndarray:
    """Convert ASCII/UTF-8 string to 1D uint8 array of bits."""
    raw_bytes = text.encode("utf-8")
    bits = []
    for b in raw_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return np.array(bits, dtype=np.uint8)


def bits_to_text(bits: np.ndarray) -> str:
    """Convert bit array back to decoded ASCII text where printable."""
    arr = np.asarray(bits, dtype=np.uint8).flatten()
    usable = (len(arr) // 8) * 8
    if usable == 0:
        return ""
    byte_vals = bytearray()
    for i in range(0, usable, 8):
        val = 0
        for b in arr[i:i + 8]:
            val = (val << 1) | int(b)
        byte_vals.append(val)
    return byte_vals.decode("utf-8", errors="replace")


def generate_transmission(
    payload_bits: Union[np.ndarray, str],
    modulation: str = "QPSK",
    samples_per_symbol: int = 8,
    sample_rate: float = 64000.0,
    preamble_name: Optional[str] = "CCSDS_ASM",
    header: Optional[Dict[str, Any]] = None,
    fec: str = "convolutional",
    fec_parameters: Optional[Dict[str, Any]] = None,
    interleaver: str = "block",
    interleaver_parameters: Optional[Dict[str, Any]] = None,
    cfo_hz: float = 0.0,
    phase_offset: float = 0.0,
    timing_offset: int = 0,
    snr_db: float = 25.0,
    num_frames: int = 4,
    random_seed: int = 42,
    sps: Optional[int] = None,
) -> SyntheticTransmission:
    """
    Construct a complete synthetic transmission with known ground truth.

    Parameters:
        payload_bits: 1D uint8 array or ASCII text string
        modulation: 'BPSK', 'QPSK', '16-QAM', or '2-FSK'
        samples_per_symbol: samples per symbol (SPS)
        sample_rate: sampling frequency in Hz
        preamble_name: preamble sync word key in STANDARD_PREAMBLES
        header: optional header metadata dictionary
        fec: 'none', 'convolutional', 'reed_solomon', 'concatenated', or 'ldpc'
        fec_parameters: parameters dict for selected FEC
        interleaver: 'none', 'block', 'convolutional', 'diagonal', or 'pseudo_random'
        interleaver_parameters: parameters dict for selected interleaver
        cfo_hz: Carrier Frequency Offset in Hz
        phase_offset: initial carrier phase in radians
        timing_offset: sample delay offset
        snr_db: target Signal-to-Noise Ratio in dB
        num_frames: number of consecutive frames in transmission
        random_seed: seed for deterministic reproducibility
    """
    if sps is not None:
        samples_per_symbol = int(sps)
    np.random.seed(random_seed)

    if isinstance(payload_bits, str):
        payload_text = payload_bits
        bits = text_to_bits(payload_bits)
    else:
        payload_text = None
        bits = np.asarray(payload_bits, dtype=np.uint8).flatten()

    fec_params = dict(fec_parameters or {})
    int_params = dict(interleaver_parameters or {})

    # 1. Forward Error Correction (FEC)
    fec_type = fec.lower()
    if fec_type == "none":
        fec_bits = bits.copy()
    elif fec_type in ("convolutional", "viterbi"):
        k = int(fec_params.get("k", 7))
        poly = tuple(fec_params.get("poly", (171, 133)))
        fec_bits = convolutional_encode(bits, constraint_length=k, generators=poly)
        fec_params["k"] = k
        fec_params["poly"] = list(poly)
        fec_params["rate"] = f"1/{len(poly)}"
    elif fec_type in ("reed_solomon", "rs"):
        nsym = int(fec_params.get("nsym", 6))
        fec_bits, pad_count = rs_encode(bits, nsym=nsym)
        fec_params["nsym"] = nsym
        fec_params["pad_count"] = pad_count
    elif fec_type == "concatenated":
        rs_nsym = int(fec_params.get("rs_nsym", 4))
        conv_k = int(fec_params.get("conv_k", 7))
        conv_g = tuple(fec_params.get("conv_g", (171, 133)))
        i_rows = int(fec_params.get("interleaver_rows", 8))
        fec_bits, conc_meta = concatenated_encode(
            bits,
            rs_nsym=rs_nsym,
            conv_k=conv_k,
            conv_g=conv_g,
            interleaver_rows=i_rows,
        )
        fec_params.update(conc_meta)
    elif fec_type == "ldpc":
        fec_bits = ldpc_encode(bits)
        fec_params["code"] = "Gallager_(12,6)"
    else:
        raise ValueError(f"Unsupported FEC type: {fec}")

    # 2. Interleaving
    int_type = interleaver.lower()
    if int_type == "none":
        interleaved_bits = fec_bits.copy()
    elif int_type == "block":
        rows = int(int_params.get("rows", 8))
        cols = int(int_params.get("cols", 8))
        interleaved_bits = block_interleave(fec_bits, rows=rows, cols=cols)
        int_params["rows"] = rows
        int_params["cols"] = cols
    elif int_type in ("convolutional", "conv"):
        branches = int(int_params.get("branches", 4))
        branch_delay = int(int_params.get("branch_delay", 2))
        interleaved_bits = convolutional_interleave(fec_bits, branches=branches, branch_delay=branch_delay)
        int_params["branches"] = branches
        int_params["branch_delay"] = branch_delay
    elif int_type == "diagonal":
        rows = int(int_params.get("rows", 8))
        cols = int(int_params.get("cols", 8))
        interleaved_bits = diagonal_interleave(fec_bits, rows=rows, cols=cols)
        int_params["rows"] = rows
        int_params["cols"] = cols
    elif int_type in ("pseudo_random", "pr"):
        block_size = int(int_params.get("block_size", 64))
        seed = int(int_params.get("seed", 42))
        interleaved_bits = pseudo_random_interleave(fec_bits, block_size=block_size, seed=seed)
        int_params["block_size"] = block_size
        int_params["seed"] = seed
    else:
        raise ValueError(f"Unsupported interleaver type: {interleaver}")

    # 3. Framing: Preamble & Header
    preamble_bits = np.array([], dtype=np.uint8)
    preamble_meta = None
    if preamble_name is not None and preamble_name != "none":
        if preamble_name not in STANDARD_PREAMBLES:
            raise ValueError(f"Unknown preamble name: {preamble_name}. Available: {list(STANDARD_PREAMBLES.keys())}")
        preamble_bits = STANDARD_PREAMBLES[preamble_name]
        hex_val = hex(int("".join(str(b) for b in preamble_bits), 2))
        preamble_meta = {
            "name": preamble_name,
            "length": len(preamble_bits),
            "hex": hex_val,
        }

    header_bits = np.array([], dtype=np.uint8)
    if header is not None:
        length_val = int(header.get("length", len(interleaved_bits)))
        # 16-bit big endian length header
        header_bits = np.array([(length_val >> (15 - i)) & 1 for i in range(16)], dtype=np.uint8)

    single_frame = np.concatenate([preamble_bits, header_bits, interleaved_bits])

    # Build multi-frame transmission sequence to provide realistic periodic telemetry
    frame_sequence = []
    for _ in range(max(1, num_frames)):
        frame_sequence.append(single_frame)
    all_bits = np.concatenate(frame_sequence)

    # 4. Modulation
    mod = modulation.upper()
    sps = int(samples_per_symbol)
    symbol_rate = float(sample_rate / sps)

    if mod == "BPSK":
        symbols = (2.0 * all_bits.astype(float) - 1.0)
        baseband = np.repeat(symbols, sps).astype(np.complex128)
    elif mod == "QPSK":
        # Ensure even bit count for I/Q symbol mapping
        q_bits = all_bits if len(all_bits) % 2 == 0 else np.append(all_bits, 0)
        pairs = q_bits.reshape(-1, 2)
        mapping = {
            (0, 0): (1.0 + 1j) / np.sqrt(2),
            (0, 1): (-1.0 + 1j) / np.sqrt(2),
            (1, 1): (-1.0 - 1j) / np.sqrt(2),
            (1, 0): (1.0 - 1j) / np.sqrt(2),
        }
        symbols = np.array([mapping[tuple(p)] for p in pairs], dtype=np.complex128)
        baseband = np.repeat(symbols, sps)
    elif mod == "16-QAM":
        rem = len(all_bits) % 4
        qam_bits = all_bits if rem == 0 else np.append(all_bits, [0] * (4 - rem))
        nibbles = qam_bits.reshape(-1, 4)
        pam_map = {(0, 0): -3, (0, 1): -1, (1, 1): 1, (1, 0): 3}
        symbols = []
        norm = np.sqrt(10.0)
        for nib in nibbles:
            i_val = pam_map[(nib[0], nib[1])]
            q_val = pam_map[(nib[2], nib[3])]
            symbols.append((i_val + 1j * q_val) / norm)
        symbols = np.array(symbols, dtype=np.complex128)
        baseband = np.repeat(symbols, sps)
    elif mod in ("2-FSK", "FSK"):
        freq_dev = float(fec_params.get("freq_dev_hz", symbol_rate / 2.0))
        freqs = np.where(all_bits == 1, freq_dev, -freq_dev)
        freq_samples = np.repeat(freqs, sps)
        phase_accum = 2.0 * np.pi * np.cumsum(freq_samples) / sample_rate
        baseband = np.exp(1j * phase_accum)
        symbols = baseband[::sps]
    else:
        raise ValueError(f"Unsupported modulation: {modulation}")

    # 5. Channel Impairments
    tx_signal = baseband.copy()

    # Timing offset (shift)
    t_offset = int(timing_offset)
    if t_offset > 0:
        tx_signal = np.roll(tx_signal, t_offset)

    # Carrier Frequency Offset (CFO) and Phase Offset
    t = np.arange(len(tx_signal)) / sample_rate
    impaired = tx_signal * np.exp(1j * (2.0 * np.pi * cfo_hz * t + phase_offset))

    # Additive White Gaussian Noise (AWGN)
    sig_power = np.mean(np.abs(impaired) ** 2)
    snr_lin = 10.0 ** (snr_db / 10.0)
    noise_power = sig_power / max(1e-12, snr_lin)
    noise_std = np.sqrt(noise_power / 2.0)
    awgn = np.random.normal(0, noise_std, len(impaired)) + 1j * np.random.normal(0, noise_std, len(impaired))
    rx_samples = (impaired + awgn).astype(np.complex64)

    # 6. Complete Ground-Truth Metadata
    metadata = {
        "payload_bits": bits.tolist(),
        "payload_text": payload_text,
        "payload_bits_count": int(len(bits)),
        "preamble": preamble_meta,
        "header": header or {},
        "modulation": mod,
        "samples_per_symbol": int(sps),
        "symbol_rate": float(symbol_rate),
        "sample_rate": float(sample_rate),
        "cfo_hz": float(cfo_hz),
        "phase_offset": float(phase_offset),
        "timing_offset": int(t_offset),
        "snr_db": float(snr_db),
        "num_frames": int(num_frames),
        "single_frame_bits_count": int(len(single_frame)),
        "interleaver": int_type,
        "interleaver_parameters": int_params,
        "fec": fec_type,
        "fec_parameters": fec_params,
    }

    intermediate = {
        "payload_bits": bits,
        "fec_bits": fec_bits,
        "interleaved_bits": interleaved_bits,
        "single_frame_bits": single_frame,
        "all_bits": all_bits,
        "symbols": symbols,
        "tx_clean_samples": tx_signal,
    }

    return SyntheticTransmission(
        samples=rx_samples,
        sample_rate=float(sample_rate),
        metadata=metadata,
        payload_bits=bits,
        intermediate=intermediate,
    )
