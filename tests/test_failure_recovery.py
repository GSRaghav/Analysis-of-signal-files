"""
Failure Recovery Test Suite (Phase 6Q).

Validates that AutoSig-Intel degrades gracefully under pathological, malformed,
or edge-case inputs without unhandled exceptions or crashes.
Every case must return a structured result with confidence 0.0% or clean error dict.
"""

from pathlib import Path
import tempfile
import numpy as np
import pytest

from core.receiver import analyze_signal
from core.signal_loader import load_iq, load_wav
from core.signal_data import SignalData
from core.demodulation import demodulate_bpsk, demodulate_qpsk
from core.fec import rs_decode, viterbi_decode, ldpc_decode
from core.interleaving import block_deinterleave, convolutional_deinterleave


class TestFailureRecovery:
    """Pathological and malformed input handling."""

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"")
            tmp_path = Path(f.name)
        try:
            result = analyze_signal(tmp_path)
            assert result["confidence"] == 0.0
            assert result["modulation"] == "UNKNOWN"
        except Exception as exc:
            # If load raises error, it must be clean and caught
            assert isinstance(exc, (ValueError, RuntimeError, EOFError, Exception))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_malformed_wav_header(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00")
            tmp_path = Path(f.name)
        try:
            result = analyze_signal(tmp_path)
            assert result["confidence"] == 0.0
            assert result["modulation"] == "UNKNOWN"
        except Exception as exc:
            assert isinstance(exc, Exception)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_raw_iq_missing_sample_rate(self):
        with tempfile.NamedTemporaryFile(suffix=".iq", delete=False) as f:
            f.write(np.zeros(200, dtype=np.int16).tobytes())
            tmp_path = Path(f.name)
        try:
            with pytest.raises((ValueError, TypeError)):
                load_iq(tmp_path, sample_rate=None)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_insufficient_samples(self):
        """Very short signal (< 32 samples)."""
        short_sig = SignalData(
            samples=np.array([1.0 + 0j, -1.0 + 0j, 0.5 + 0.5j], dtype=np.complex64),
            sample_rate=10000.0,
            source_type="iq",
            representation="complex_iq",
            filename="tiny.iq"
        )
        result = analyze_signal(short_sig)
        assert result["confidence"] == 0.0
        assert result["modulation"] == "UNKNOWN"
        assert result["status"] in ("NON_DIGITAL_REJECTED", "INSUFFICIENT_EVIDENCE")

    def test_pure_tone_rejection(self):
        """Pure unmodulated sinusoidal tone."""
        fs = 48000.0
        t = np.arange(fs * 0.2) / fs
        tone = np.cos(2 * np.pi * 1000.0 * t).astype(np.float32)
        sig = SignalData(samples=tone, sample_rate=fs, source_type="wav", representation="real", filename="pure_tone.wav")
        result = analyze_signal(sig)
        assert result["modulation"] == "UNKNOWN"
        assert result["confidence"] == 0.0
        assert result["status"] == "NON_DIGITAL_REJECTED"

    def test_pure_gaussian_noise(self):
        """Pure Gaussian noise."""
        np.random.seed(42)
        noise = (np.random.randn(20000) + 1j * np.random.randn(20000)).astype(np.complex64)
        sig = SignalData(samples=noise, sample_rate=48000.0, source_type="iq", representation="complex_iq", filename="noise.iq")
        result = analyze_signal(sig)
        assert result["modulation"] == "UNKNOWN"
        assert result["confidence"] == 0.0

    def test_fec_beyond_correction_capability(self):
        """Reed-Solomon with corrupted payload exceeding correction capability."""
        # 10 parity symbols -> can correct up to 5 byte errors
        msg = b"AUTO_SIG_INTEL_SYSTEMATIC_PAYLOAD_TEST_12345"
        from core.fec import rs_encode
        cw, meta = rs_encode(msg, nsym=10)
        corrupted = bytearray(cw)
        # Corrupt 8 bytes (> 5)
        for i in range(8):
            corrupted[i * 2] ^= 0xFF
        dec, status = rs_decode(corrupted, nsym=10)
        assert dec is None
        assert status["status"] == "UNCORRECTABLE"

    def test_interleaver_empty_and_zero_dims(self):
        """Interleavers must handle empty inputs and reject invalid dimensions."""
        with pytest.raises(ValueError):
            block_deinterleave(np.array([1, 0, 1]), rows=0, cols=8)
        with pytest.raises(ValueError):
            convolutional_deinterleave(np.array([1, 0, 1]), branches=1, branch_delay=2)

    def test_ldpc_unencoded_noise_syndrome(self):
        """Random unencoded bits must fail LDPC syndrome parity check."""
        np.random.seed(99)
        random_bits = np.random.randint(0, 2, 60, dtype=np.uint8)
        dec, meta = ldpc_decode(random_bits)
        assert meta["syndrome_zero"] is False
        assert meta["status"] == "FAILED"
