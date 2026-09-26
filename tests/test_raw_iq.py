"""
Unit and integration tests for raw IQ file ingestion and validation.
Covers:
- complex64 format (float32 I + float32 Q)
- int16 interleaved format
- IQ vs QI channel order
- Odd-length files (handling of truncated samples)
- Empty files and insufficient data handling (raises ValueError)
- Integration with receiver pipeline
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from core.signal_loader import load_iq
from core.signal_data import SignalData
from core.receiver import analyze_signal, load_signal_for_receiver


def test_load_iq_int16_iq_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        iq_file = Path(tmpdir) / "test_int16_iq.bin"
        # Generate 1000 complex samples: 2000 int16 numbers
        i_data = (np.sin(np.linspace(0, 20 * np.pi, 1000)) * 10000).astype(np.int16)
        q_data = (np.cos(np.linspace(0, 20 * np.pi, 1000)) * 10000).astype(np.int16)
        interleaved = np.empty(2000, dtype=np.int16)
        interleaved[0::2] = i_data
        interleaved[1::2] = q_data
        interleaved.tofile(iq_file)

        sig = load_iq(iq_file, sample_rate=48000, dtype=np.int16, iq_order="IQ")
        assert isinstance(sig, SignalData)
        assert sig.source_type == "IQ"
        assert sig.representation == "complex_iq"
        assert sig.num_samples == 1000
        assert sig.sample_rate == 48000.0
        assert np.iscomplexobj(sig.samples)
        # Peak normalization check
        assert np.max(np.abs(sig.samples)) <= 1.0 + 1e-6
        # Correlation between reconstructed I and original I
        assert np.corrcoef(np.real(sig.samples), i_data)[0, 1] > 0.999


def test_load_iq_int16_qi_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        iq_file = Path(tmpdir) / "test_int16_qi.bin"
        q_data = (np.sin(np.linspace(0, 20 * np.pi, 1000)) * 10000).astype(np.int16)
        i_data = (np.cos(np.linspace(0, 20 * np.pi, 1000)) * 10000).astype(np.int16)
        interleaved = np.empty(2000, dtype=np.int16)
        interleaved[0::2] = q_data
        interleaved[1::2] = i_data
        interleaved.tofile(iq_file)

        sig = load_iq(iq_file, sample_rate=48000, dtype=np.int16, iq_order="QI")
        assert sig.num_samples == 1000
        assert np.corrcoef(np.real(sig.samples), i_data)[0, 1] > 0.999
        assert np.corrcoef(np.imag(sig.samples), q_data)[0, 1] > 0.999


def test_load_iq_complex64():
    with tempfile.TemporaryDirectory() as tmpdir:
        iq_file = Path(tmpdir) / "test_complex64.iq"
        c_samples = (
            np.exp(1j * np.linspace(0, 50 * np.pi, 2048))
        ).astype(np.complex64)
        c_samples.tofile(iq_file)

        sig = load_iq(iq_file, sample_rate=96000, dtype=np.complex64, iq_order="IQ")
        assert sig.num_samples == 2048
        assert sig.sample_rate == 96000.0
        assert sig.representation == "complex_iq"
        assert np.allclose(sig.samples, c_samples, atol=1e-5)


def test_load_iq_odd_length():
    with tempfile.TemporaryDirectory() as tmpdir:
        iq_file = Path(tmpdir) / "test_odd.bin"
        # 2001 int16 values (odd number of scalars -> 1000 pairs + 1 leftover)
        odd_data = np.arange(2001, dtype=np.int16)
        odd_data.tofile(iq_file)

        sig = load_iq(iq_file, sample_rate=10000, dtype=np.int16)
        # Should gracefully discard leftover scalar and return 1000 complex samples
        assert sig.num_samples == 1000


def test_load_iq_empty_and_insufficient():
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_file = Path(tmpdir) / "empty.bin"
        empty_file.touch()

        with pytest.raises(ValueError, match="insufficient data"):
            load_iq(empty_file, sample_rate=10000, dtype=np.int16)

        one_sample_file = Path(tmpdir) / "single_scalar.bin"
        np.array([42], dtype=np.int16).tofile(one_sample_file)

        with pytest.raises(ValueError, match="insufficient data"):
            load_iq(one_sample_file, sample_rate=10000, dtype=np.int16)


def test_load_iq_invalid_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_file = Path(tmpdir) / "dummy.bin"
        np.arange(100, dtype=np.int16).tofile(dummy_file)

        with pytest.raises(ValueError, match="iq_order must be IQ or QI"):
            load_iq(dummy_file, sample_rate=10000, dtype=np.int16, iq_order="XYZ")


def test_receiver_iq_pipeline_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        iq_file = Path(tmpdir) / "test_synth.iq"
        # Generate 2000 complex samples of pure tone in IQ format
        t = np.arange(2000) / 10000.0
        tone = np.exp(1j * 2 * np.pi * 1000.0 * t).astype(np.complex64)
        tone.tofile(iq_file)

        # Test receiver loading via load_signal_for_receiver
        loaded = load_signal_for_receiver(iq_file, sample_rate=10000, dtype=np.complex64)
        assert loaded["sample_rate"] == 10000
        assert loaded["num_samples"] == 2000
        assert loaded["possible_iq"] is True

        # Test full receiver analysis pipeline
        result = analyze_signal(iq_file, sample_rate=10000, dtype=np.complex64)
        assert result["sample_rate_hz"] == 10000
        assert result["possible_iq"] is True
        # Pure tone should be gated
        assert result["best_hypothesis"]["modulation"] == "UNKNOWN"
