#!/usr/bin/env python3
"""
Generate deterministic golden synthetic datasets for AutoSig-Intel (SIH26147).

Creates calibrated captures (.wav and raw .iq) with full metadata .json
in samples/synthetic/ for end-to-end pipeline verification.
"""

import sys
from pathlib import Path
import json
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import soundfile as sf
except ImportError:
    sf = None

from core.interleaving import (
    block_interleave,
    diagonal_interleave,
    pseudo_random_interleave,
)
from core.fec import (
    convolutional_encode,
    rs_encode,
    concatenated_encode,
)
from core.correlation import STANDARD_PREAMBLES


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "samples" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def text_to_bits(text: str) -> np.ndarray:
    raw_bytes = text.encode("utf-8")
    bits = []
    for b in raw_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return np.array(bits, dtype=np.uint8)


def apply_awgn(signal: np.ndarray, snr_db: float) -> np.ndarray:
    sig_power = np.mean(np.abs(signal) ** 2)
    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_power = sig_power / snr_linear
    noise_std = np.sqrt(noise_power / 2.0)
    noise = np.random.normal(0, noise_std, len(signal)) + 1j * np.random.normal(0, noise_std, len(signal))
    return signal + noise


def save_iq_files(stem: str, signal: np.ndarray, fs: float, meta: dict):
    # 1. Save complex IQ as WAV (stereo float32: channel 0 = I, channel 1 = Q)
    wav_path = OUTPUT_DIR / f"{stem}.wav"
    if sf is not None:
        stereo_data = np.column_stack([np.real(signal), np.imag(signal)]).astype(np.float32)
        sf.write(str(wav_path), stereo_data, int(fs))

    # 2. Save raw interleaved float32 IQ
    iq_f32_path = OUTPUT_DIR / f"{stem}_f32.iq"
    interleaved_f32 = np.empty(2 * len(signal), dtype=np.float32)
    interleaved_f32[0::2] = np.real(signal).astype(np.float32)
    interleaved_f32[1::2] = np.imag(signal).astype(np.float32)
    interleaved_f32.tofile(str(iq_f32_path))

    # 3. Save raw interleaved int16 IQ
    iq_i16_path = OUTPUT_DIR / f"{stem}_i16.iq"
    scale = 30000.0 / max(1e-6, np.max(np.abs(signal)))
    interleaved_i16 = np.empty(2 * len(signal), dtype=np.int16)
    interleaved_i16[0::2] = np.clip(np.real(signal) * scale, -32767, 32767).astype(np.int16)
    interleaved_i16[1::2] = np.clip(np.imag(signal) * scale, -32767, 32767).astype(np.int16)
    interleaved_i16.tofile(str(iq_i16_path))

    # 4. Save metadata JSON
    json_path = OUTPUT_DIR / f"{stem}.json"
    json_path.write_text(json.dumps(meta, indent=2))
    print(f"[+] Generated golden dataset: {stem}")


def generate_bpsk_dataset():
    np.random.seed(42)
    fs = 48000.0
    sps = 8
    symbol_rate = fs / sps
    cfo = 45.0
    phase = 0.45
    snr_db = 25.0

    payload_text = "AUTOSIG_INTEL_SIH2026_GOLDEN_PAYLOAD_BPSK"
    payload_bits = text_to_bits(payload_text)

    # FEC: K=7 NASA
    fec_bits = convolutional_encode(payload_bits, constraint_length=7, generators=(171, 133))

    # Interleaver: 8x8 block
    int_bits = block_interleave(fec_bits, rows=8, cols=8)

    # Frame: CCSDS 32-bit preamble
    preamble_bits = STANDARD_PREAMBLES["CCSDS_ASM"]
    frame_bits = np.concatenate([preamble_bits, int_bits])

    # Modulate BPSK: 0 -> -1, 1 -> +1
    symbols = (2.0 * frame_bits.astype(float) - 1.0)
    tx_signal = np.repeat(symbols, sps).astype(np.complex128)

    # Add lead-in silence/noise and lead-out
    lead_in = np.zeros(sps * 20, dtype=np.complex128)
    lead_out = np.zeros(sps * 20, dtype=np.complex128)
    full_signal = np.concatenate([lead_in, tx_signal, lead_out])

    # Apply impairments
    t = np.arange(len(full_signal)) / fs
    impaired = full_signal * np.exp(1j * (2.0 * np.pi * cfo * t + phase))
    rx_signal = apply_awgn(impaired, snr_db)

    meta = {
        "modulation": "BPSK",
        "sample_rate": fs,
        "samples_per_symbol": sps,
        "symbol_rate": symbol_rate,
        "cfo": cfo,
        "phase": phase,
        "snr_db": snr_db,
        "interleaver": {"type": "block", "rows": 8, "cols": 8},
        "fec": {"type": "convolutional", "poly": [171, 133], "k": 7, "rate": "1/2"},
        "preamble": {"name": "CCSDS_32", "hex": "1acffc1d", "length": 32},
        "payload": payload_text,
        "payload_bits_count": len(payload_bits),
    }
    save_iq_files("golden_bpsk_viterbi_block", rx_signal, fs, meta)


def generate_qpsk_dataset():
    np.random.seed(1337)
    fs = 64000.0
    sps = 8
    symbol_rate = fs / sps
    cfo = -35.0
    phase = -0.30
    snr_db = 25.0

    payload_text = "NTRO_SIH_QPSK_SECURE_PAYLOAD_DATA"
    payload_bits = text_to_bits(payload_text)

    # FEC: Concatenated (Outer RS + Block Interleaver + Inner Conv)
    conc_bits, _ = concatenated_encode(
        payload_bits,
        rs_nsym=4,
        interleaver_rows=8,
        interleaver_cols=8,
        conv_g=(171, 133),
        conv_k=7,
    )

    # Frame: CCSDS 32-bit preamble
    preamble_bits = STANDARD_PREAMBLES["CCSDS_ASM"]
    frame_bits = np.concatenate([preamble_bits, conc_bits])

    # Modulate QPSK Gray code
    if len(frame_bits) % 2 != 0:
        frame_bits = np.append(frame_bits, 0)
    pairs = frame_bits.reshape(-1, 2)
    mapping = {
        (0, 0): (1.0 + 1j) / np.sqrt(2),
        (0, 1): (-1.0 + 1j) / np.sqrt(2),
        (1, 1): (-1.0 - 1j) / np.sqrt(2),
        (1, 0): (1.0 - 1j) / np.sqrt(2),
    }
    symbols = np.array([mapping[tuple(p)] for p in pairs], dtype=np.complex128)
    tx_signal = np.repeat(symbols, sps)

    lead_in = np.zeros(sps * 25, dtype=np.complex128)
    lead_out = np.zeros(sps * 25, dtype=np.complex128)
    full_signal = np.concatenate([lead_in, tx_signal, lead_out])

    t = np.arange(len(full_signal)) / fs
    impaired = full_signal * np.exp(1j * (2.0 * np.pi * cfo * t + phase))
    rx_signal = apply_awgn(impaired, snr_db)

    meta = {
        "modulation": "QPSK",
        "sample_rate": fs,
        "samples_per_symbol": sps,
        "symbol_rate": symbol_rate,
        "cfo": cfo,
        "phase": phase,
        "snr_db": snr_db,
        "interleaver": {"type": "block", "rows": 8, "cols": 8},
        "fec": {"type": "concatenated", "outer": "reed_solomon_nsym4", "inner": "convolutional_k7"},
        "preamble": {"name": "CCSDS_32", "hex": "1acffc1d", "length": 32},
        "payload": payload_text,
        "payload_bits_count": len(payload_bits),
    }
    save_iq_files("golden_qpsk_concatenated", rx_signal, fs, meta)


def generate_16qam_dataset():
    np.random.seed(999)
    fs = 64000.0
    sps = 8
    symbol_rate = fs / sps
    cfo = 25.0
    phase = 0.20
    snr_db = 30.0

    payload_text = "16QAM_CONSTELLATION_HIGH_RATE_DATA"
    payload_bits = text_to_bits(payload_text)

    # FEC: Conv K=7
    fec_bits = convolutional_encode(payload_bits, constraint_length=7, generators=(171, 133))

    # Interleaver: Diagonal 8x8
    int_bits = diagonal_interleave(fec_bits, rows=8, cols=8)

    # Frame: SYNC_16 preamble
    preamble_bits = STANDARD_PREAMBLES["SYNC_AA55"]
    frame_bits = np.concatenate([preamble_bits, int_bits])

    # Pad to multiple of 4 for 16-QAM
    rem = len(frame_bits) % 4
    if rem != 0:
        frame_bits = np.append(frame_bits, [0] * (4 - rem))

    # 16-QAM Gray mapping
    nibbles = frame_bits.reshape(-1, 4)
    gray_map = {
        (0, 0): -3, (0, 1): -1, (1, 1): 1, (1, 0): 3
    }
    symbols = []
    norm = np.sqrt(10.0)
    for nib in nibbles:
        i_val = gray_map[(nib[0], nib[1])]
        q_val = gray_map[(nib[2], nib[3])]
        symbols.append((i_val + 1j * q_val) / norm)
    symbols = np.array(symbols, dtype=np.complex128)

    tx_signal = np.repeat(symbols, sps)
    lead_in = np.zeros(sps * 20, dtype=np.complex128)
    lead_out = np.zeros(sps * 20, dtype=np.complex128)
    full_signal = np.concatenate([lead_in, tx_signal, lead_out])

    t = np.arange(len(full_signal)) / fs
    impaired = full_signal * np.exp(1j * (2.0 * np.pi * cfo * t + phase))
    rx_signal = apply_awgn(impaired, snr_db)

    meta = {
        "modulation": "16-QAM",
        "sample_rate": fs,
        "samples_per_symbol": sps,
        "symbol_rate": symbol_rate,
        "cfo": cfo,
        "phase": phase,
        "snr_db": snr_db,
        "interleaver": {"type": "diagonal", "rows": 8, "cols": 8},
        "fec": {"type": "convolutional", "poly": [171, 133], "k": 7, "rate": "1/2"},
        "preamble": {"name": "SYNC_16", "hex": "aa55", "length": 16},
        "payload": payload_text,
        "payload_bits_count": len(payload_bits),
    }
    save_iq_files("golden_16qam_viterbi", rx_signal, fs, meta)


def generate_2fsk_dataset():
    np.random.seed(777)
    fs = 48000.0
    sps = 16
    symbol_rate = fs / sps
    freq_dev = 1500.0  # +/- 1500 Hz
    cfo = 15.0
    snr_db = 22.0

    payload_text = "2FSK_ROBUST_TACTICAL_TELEMETRY"
    payload_bits = text_to_bits(payload_text)

    # Frame: SYNC_16 preamble
    preamble_bits = STANDARD_PREAMBLES["SYNC_AA55"]
    frame_bits = np.concatenate([preamble_bits, payload_bits])

    # Continuous Phase FSK (CPFSK)
    freqs = np.where(frame_bits == 1, freq_dev, -freq_dev)
    freq_samples = np.repeat(freqs, sps)

    lead_in = np.zeros(sps * 15)
    lead_out = np.zeros(sps * 15)
    full_freqs = np.concatenate([lead_in, freq_samples, lead_out])

    # Integrate frequency to get continuous phase
    phase = 2.0 * np.pi * np.cumsum(full_freqs + cfo) / fs
    rx_signal = apply_awgn(np.exp(1j * phase), snr_db)

    meta = {
        "modulation": "2-FSK",
        "sample_rate": fs,
        "samples_per_symbol": sps,
        "symbol_rate": symbol_rate,
        "frequency_deviation_hz": freq_dev,
        "cfo": cfo,
        "phase": 0.0,
        "snr_db": snr_db,
        "interleaver": {"type": "none"},
        "fec": {"type": "none"},
        "preamble": {"name": "SYNC_16", "hex": "aa55", "length": 16},
        "payload": payload_text,
        "payload_bits_count": len(payload_bits),
    }
    save_iq_files("golden_2fsk_clean", rx_signal, fs, meta)


def main():
    print("[*] Generating AutoSig-Intel Golden Synthetic Datasets...")
    generate_bpsk_dataset()
    generate_qpsk_dataset()
    generate_16qam_dataset()
    generate_2fsk_dataset()
    print("[*] All golden datasets generated successfully in samples/synthetic/")


if __name__ == "__main__":
    main()
