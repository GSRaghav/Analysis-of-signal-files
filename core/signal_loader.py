from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .signal_data import SignalData


def _convert_channel_to_float32(channel):
    """
    Convert one WAV channel directly to float32.
    """

    channel = np.asarray(channel)

    if np.issubdtype(channel.dtype, np.integer):

        info = np.iinfo(channel.dtype)

        scale = max(
            abs(info.min),
            abs(info.max)
        )

        result = (
            channel.astype(np.float32)
            / np.float32(scale)
        )

    else:

        result = channel.astype(
            np.float32,
            copy=False
        )

    return result


def _channel_correlation(
    a,
    b,
    max_samples=250_000
):
    """
    Estimate channel correlation using only a subset.
    """

    n = min(
        len(a),
        len(b),
        max_samples
    )

    a = a[:n].astype(
        np.float64
    )

    b = b[:n].astype(
        np.float64
    )

    a -= np.mean(a)
    b -= np.mean(b)

    denominator = np.sqrt(
        np.sum(a * a)
        *
        np.sum(b * b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.sum(a * b)
        /
        denominator
    )


def _is_duplicate(
    a,
    b,
    correlation
):

    if np.array_equal(a, b):
        return True

    return correlation >= 0.995


def _possible_iq(
    a,
    b,
    correlation
):

    if abs(correlation) > 0.20:
        return False

    rms_a = np.sqrt(
        np.mean(
            a.astype(np.float64) ** 2
        )
    )

    rms_b = np.sqrt(
        np.mean(
            b.astype(np.float64) ** 2
        )
    )

    if rms_a == 0 or rms_b == 0:
        return False

    ratio = (
        min(rms_a, rms_b)
        /
        max(rms_a, rms_b)
    )

    return ratio >= 0.75


def load_wav(path):

    path = Path(path)

    sample_rate, raw_data = wavfile.read(
        path
    )

    original_channels = (
        1
        if raw_data.ndim == 1
        else raw_data.shape[1]
    )

    original_dtype = str(
        raw_data.dtype
    )

    # --------------------------------------------------
    # MONO
    # --------------------------------------------------

    if raw_data.ndim == 1:

        samples = _convert_channel_to_float32(
            raw_data
        )

        samples -= np.mean(
            samples,
            dtype=np.float32
        )

        peak = np.max(
            np.abs(samples)
        )

        if peak > 0:
            samples /= peak

        return SignalData(
            samples=samples,
            sample_rate=float(sample_rate),
            source_type="WAV",
            representation="real",
            filename=path.name,
            original_channels=1,
            possible_iq=False,
            metadata={
                "original_dtype": original_dtype,
                "original_shape": tuple(
                    raw_data.shape
                )
            },
            notes=[
                "Mono WAV"
            ]
        )

    # --------------------------------------------------
    # STEREO
    # --------------------------------------------------

    a = _convert_channel_to_float32(
        raw_data[:, 0]
    )

    b = _convert_channel_to_float32(
        raw_data[:, 1]
    )

    correlation = _channel_correlation(
        a,
        b
    )

    # Remove channel DC
    a -= np.mean(
        a,
        dtype=np.float32
    )

    b -= np.mean(
        b,
        dtype=np.float32
    )

    # --------------------------------------------------
    # DUPLICATE CHANNELS
    # --------------------------------------------------

    if _is_duplicate(
        a,
        b,
        correlation
    ):

        peak = np.max(
            np.abs(a)
        )

        if peak > 0:
            a /= peak

        return SignalData(
            samples=a,
            sample_rate=float(sample_rate),
            source_type="WAV",
            representation="real",
            filename=path.name,
            original_channels=original_channels,
            channel_correlation=correlation,
            possible_iq=False,
            metadata={
                "original_dtype": original_dtype,
                "original_shape": tuple(
                    raw_data.shape
                ),
                "channel_mode":
                    "duplicate_mono"
            },
            notes=[
                "Two channels are duplicates.",
                "Primary analysis uses one real-valued channel."
            ]
        )

    # --------------------------------------------------
    # POSSIBLE I/Q
    # --------------------------------------------------

    if _possible_iq(
        a,
        b,
        correlation
    ):

        magnitude = np.sqrt(
            a * a
            +
            b * b
        )

        peak = np.max(
            magnitude
        )

        if peak > 0:

            a /= peak
            b /= peak

        iq = (
            a
            +
            1j * b
        ).astype(
            np.complex64
        )

        return SignalData(
            samples=iq,
            sample_rate=float(sample_rate),
            source_type="WAV",
            representation="complex_iq",
            filename=path.name,
            original_channels=original_channels,
            channel_correlation=correlation,
            possible_iq=True,
            metadata={
                "original_dtype": original_dtype,
                "original_shape": tuple(
                    raw_data.shape
                ),
                "channel_mode":
                    "possible_iq"
            },
            notes=[
                "Two channels are independent.",
                "Possible I/Q interpretation."
            ]
        )

    # --------------------------------------------------
    # OTHER STEREO
    # --------------------------------------------------

    peak = np.max(
        np.abs(a)
    )

    if peak > 0:
        a /= peak

    return SignalData(
        samples=a,
        sample_rate=float(sample_rate),
        source_type="WAV",
        representation="real",
        filename=path.name,
        original_channels=original_channels,
        channel_correlation=correlation,
        possible_iq=False,
        metadata={
            "original_dtype": original_dtype,
            "original_shape": tuple(
                raw_data.shape
            ),
            "channel_mode":
                "independent_stereo"
        },
        notes=[
            "Stereo channels are not duplicates.",
            "I/Q interpretation not established.",
            "First channel used for primary analysis."
        ]
    )


def load_iq(
    path,
    sample_rate,
    dtype=np.int16,
    iq_order="IQ",
    byte_order="="
):

    path = Path(path)

    dtype = np.dtype(
        dtype
    ).newbyteorder(
        byte_order
    )

    raw = np.fromfile(
        path,
        dtype=dtype
    )

    if np.issubdtype(np.dtype(dtype), np.complexfloating):
        if len(raw) < 1:
            raise ValueError(
                "IQ file contains insufficient data."
            )
        if iq_order.upper() == "QI":
            samples = (
                raw.imag.astype(np.float32)
                + 1j * raw.real.astype(np.float32)
            )
        elif iq_order.upper() == "IQ":
            samples = raw.astype(np.complex64)
        else:
            raise ValueError(
                "iq_order must be IQ or QI."
            )
    else:
        if len(raw) < 2:
            raise ValueError(
                "IQ file contains insufficient data."
            )

        if len(raw) % 2:
            raw = raw[:-1]

        if iq_order.upper() == "IQ":
            i = raw[0::2]
            q = raw[1::2]
        elif iq_order.upper() == "QI":
            q = raw[0::2]
            i = raw[1::2]
        else:
            raise ValueError(
                "iq_order must be IQ or QI."
            )

        samples = (
            i.astype(np.float32)
            +
            1j * q.astype(np.float32)
        )

    peak = np.max(
        np.abs(samples)
    )

    if peak > 0:
        samples /= peak

    return SignalData(
        samples=samples.astype(
            np.complex64
        ),
        sample_rate=float(sample_rate),
        source_type="IQ",
        representation="complex_iq",
        filename=path.name,
        original_channels=2,
        possible_iq=True,
        metadata={
            "dtype": str(dtype),
            "iq_order": iq_order,
            "byte_order": byte_order
        },
        notes=[
            "Raw interleaved IQ input."
        ]
    )