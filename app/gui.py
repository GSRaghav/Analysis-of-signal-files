import io
import json
import time
import inspect
import tempfile
import sys
from pathlib import Path

# Make the project root importable even when Streamlit executes this file
# from the app/ directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import signal
from scipy.signal import hilbert

try:
    import soundfile as sf
except ImportError:
    sf = None


# ============================================================
# PAGE / STYLE
# ============================================================

st.set_page_config(
    page_title="SIGNALX Command Center",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "is_analyzed" not in st.session_state:
    st.session_state.is_analyzed = False
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "signal_data" not in st.session_state:
    st.session_state.signal_data = None
if "signal_path" not in st.session_state:
    st.session_state.signal_path = None
if "analysis_logs" not in st.session_state:
    st.session_state.analysis_logs = []


EARTH_BG_URL = (
    "https://images.unsplash.com/"
    "photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop"
)

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=Space+Mono:wght@400;700&display=swap');

    h1, h2, h3 {{ font-family: 'Orbitron', sans-serif !important; }}
    p, span, div {{ font-family: 'Rajdhani', sans-serif; }}

    .stApp {{
        background-color: #010308;
        background-image:
            linear-gradient(rgba(0, 210, 255, 0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 210, 255, 0.04) 1px, transparent 1px),
            url("{EARTH_BG_URL}");
        background-size: 50px 50px, 50px 50px, cover;
        background-position: center center;
        background-attachment: fixed;
    }}

    section[data-testid="stSidebar"] {{
        background: rgba(2, 8, 18, 0.95) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(0, 210, 255, 0.2);
    }}

    .sidebar-badge {{
        background: rgba(0, 255, 170, 0.1);
        border: 1px solid rgba(0, 255, 170, 0.3);
        color: #00ffaa;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: 'Orbitron', sans-serif;
        font-size: 11px;
        text-align: center;
        letter-spacing: 1px;
        margin-bottom: 20px;
    }}

    .sidebar-section-title {{
        font-family: 'Orbitron', sans-serif;
        font-size: 13px;
        color: #00d2ff;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 15px;
        margin-bottom: 8px;
        border-left: 3px solid #00d2ff;
        padding-left: 8px;
    }}

    .liquid-glass-card {{
        background: linear-gradient(
            135deg,
            rgba(16, 36, 64, 0.65) 0%,
            rgba(6, 16, 32, 0.85) 100%
        );
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(0, 210, 255, 0.25);
        border-top: 1px solid rgba(255, 255, 255, 0.35);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
        transition: transform 0.3s ease, border-color 0.3s ease;
        margin-bottom: 12px;
    }}

    .liquid-glass-card:hover {{
        transform: translateY(-4px);
        border-color: rgba(0, 210, 255, 0.6);
    }}

    .metric-tag {{
        font-family: 'Orbitron', sans-serif;
        font-size: 11px;
        color: #8fa0b5;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .metric-reading {{
        font-family: 'Orbitron', sans-serif;
        font-size: 21px;
        font-weight: 700;
        color: #ffffff;
        margin: 3px 0 6px 0;
    }}

    .metric-badge {{
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }}

    .badge-cyan {{
        background: rgba(0, 210, 255, 0.15);
        color: #00d2ff;
        border: 1px solid rgba(0, 210, 255, 0.3);
    }}

    .badge-green {{
        background: rgba(0, 255, 170, 0.15);
        color: #00ffaa;
        border: 1px solid rgba(0, 255, 170, 0.3);
    }}

    .badge-amber {{
        background: rgba(255, 170, 0, 0.15);
        color: #ffaa00;
        border: 1px solid rgba(255, 170, 0, 0.3);
    }}

    .badge-magenta {{
        background: rgba(255, 0, 85, 0.15);
        color: #ff0055;
        border: 1px solid rgba(255, 0, 85, 0.3);
    }}

    .chart-liquid-panel {{
        background: linear-gradient(
            135deg,
            rgba(8, 20, 36, 0.74) 0%,
            rgba(4, 12, 24, 0.92) 100%
        );
        backdrop-filter: blur(24px);
        border: 1px solid rgba(0, 210, 255, 0.2);
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 14px;
        padding: 12px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.7);
        margin-bottom: 12px;
    }}

    .console-text {{
        font-family: 'Space Mono', monospace;
        color: #00ffaa;
        line-height: 1.65;
        font-size: 13px;
    }}

    .hero-title {{
        font-size: 50px;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 3px;
        text-transform: uppercase;
    }}

    .hero-subtitle {{
        text-align: center;
        color: #a0aec0;
        font-size: 15px;
        letter-spacing: 5px;
        margin-bottom: 24px;
        font-weight: 700;
        text-transform: uppercase;
    }}

    .mission-status-banner {{
        background: rgba(0, 210, 255, 0.08);
        border: 1px solid rgba(0, 210, 255, 0.3);
        color: #00d2ff;
        text-align: center;
        padding: 10px;
        font-family: 'Orbitron', sans-serif;
        font-size: 11px;
        letter-spacing: 2px;
        border-radius: 6px;
        margin-bottom: 20px;
    }}

    .bitstream-container {{
        font-family: 'Space Mono', monospace;
        font-size: 15px;
        background: rgba(2, 6, 12, 0.8);
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #1a2c42;
        height: 210px;
        overflow-y: auto;
        line-height: 1.6;
        word-break: break-all;
    }}

    .bit-header {{
        color: #ff0055;
        font-weight: bold;
        background: rgba(255, 0, 85, 0.1);
        padding: 0 4px;
        border-radius: 3px;
        border: 1px solid rgba(255, 0, 85, 0.3);
    }}

    .bit-payload {{
        color: #00d2ff;
        letter-spacing: 2px;
    }}

    .status-box {{
        border-radius: 10px;
        padding: 12px 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(0, 210, 255, 0.22);
        background: rgba(0, 15, 30, 0.72);
    }}

    .path-container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        overflow-x: auto;
        padding: 6px 2px;
    }}
    .path-step {{
        flex: 1;
        min-width: 95px;
        background: rgba(10, 24, 45, 0.75);
        border: 1px solid rgba(0, 210, 255, 0.25);
        border-radius: 8px;
        padding: 8px 6px;
        text-align: center;
        transition: all 0.2s ease;
    }}
    .path-step.validated {{
        border-color: #00ffaa;
        background: rgba(0, 255, 170, 0.09);
        box-shadow: 0 0 10px rgba(0, 255, 170, 0.15);
    }}
    .path-step.rejected {{
        border-color: #ff0055;
        background: rgba(255, 0, 85, 0.09);
    }}
    .path-step.active {{
        border-color: #00d2ff;
        background: rgba(0, 210, 255, 0.09);
    }}
    .path-title {{
        display: block;
        font-family: 'Orbitron', sans-serif;
        font-size: 9px;
        color: #8fa0b5;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    .path-val {{
        display: block;
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        color: #ffffff;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .path-arrow {{
        color: #00d2ff;
        font-size: 14px;
        opacity: 0.6;
        user-select: none;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def first_value(d, *keys, default=None):
    """Read the first non-empty key from a nested flat result dictionary."""
    if not isinstance(d, dict):
        return default

    for key in keys:
        if key in d and d[key] is not None:
            return d[key]

    # Common nested containers used by receiver/hypothesis code.
    for parent in ("characterization", "signal", "analysis", "best_hypothesis", "best"):
        child = d.get(parent)
        if isinstance(child, dict):
            for key in keys:
                if key in child and child[key] is not None:
                    return child[key]

    return default


def fmt_number(value, digits=2, suffix=""):
    if value is None:
        return "N/A"
    try:
        x = float(value)
        if not np.isfinite(x):
            return "N/A"
        return f"{x:.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def fmt_hz(value):
    if value is None:
        return "N/A"
    try:
        x = float(value)
        if not np.isfinite(x):
            return "N/A"
        ax = abs(x)
        if ax >= 1e9:
            return f"{x / 1e9:.3f} GHz"
        if ax >= 1e6:
            return f"{x / 1e6:.3f} MHz"
        if ax >= 1e3:
            return f"{x / 1e3:.3f} kHz"
        return f"{x:.1f} Hz"
    except (TypeError, ValueError):
        return str(value)


def add_log(message):
    stamp = time.strftime("%H:%M:%S")
    st.session_state.analysis_logs.append(f"[{stamp}] {message}")


def normalize_audio_or_complex(x):
    x = np.asarray(x)
    if np.iscomplexobj(x):
        x = x.astype(np.complex128, copy=False)
    else:
        x = x.astype(np.float64, copy=False)

    x = np.nan_to_num(x)
    x = x - np.mean(x)

    peak = np.max(np.abs(x)) if len(x) else 0.0
    if peak > 0:
        x = x / peak
    return x


def bits_to_bytes(bit_array):
    """Convert a sequence of 0/1 bits into bytes with MSB-first bit order."""
    if bit_array is None or len(bit_array) == 0:
        return b""
    try:
        bits = [int(b) for b in bit_array]
    except Exception:
        return b""
    rem = len(bits) % 8
    if rem != 0:
        bits = bits + [0] * (8 - rem)
    byte_vals = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for b in bits[i:i + 8]:
            byte_val = (byte_val << 1) | (b & 1)
        byte_vals.append(byte_val)
    return bytes(byte_vals)


def format_hex_dump(byte_data, bytes_per_line=16, max_lines=64):
    """Format bytes as a canonical hexadecimal dump with ASCII preview."""
    if not byte_data:
        return "No data available."
    lines = []
    total = min(len(byte_data), bytes_per_line * max_lines)
    for i in range(0, total, bytes_per_line):
        chunk = byte_data[i:i + bytes_per_line]
        hex_bytes = " ".join(f"{b:02x}" for b in chunk)
        padding = "   " * (bytes_per_line - len(chunk))
        ascii_chars = "".join(chr(b) if 32 <= b < 127 else "·" for b in chunk)
        lines.append(f"{i:08x}:  {hex_bytes}{padding}  |{ascii_chars}|")
    if len(byte_data) > total:
        lines.append(f"... ({len(byte_data) - total} bytes truncated for display) ...")
    return "\n".join(lines)


# ============================================================
# FILE LOADING
# ============================================================

class DemoFileWrapper:
    """Wrapper around local sample files providing Streamlit UploadedFile interface."""
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.name = self.file_path.name
        self._bytes = self.file_path.read_bytes()

    def getvalue(self):
        return self._bytes


def parse_uploaded_wav(uploaded_file):
    if sf is None:
        raise RuntimeError("soundfile is not installed. Run: pip install soundfile")

    data, fs = sf.read(io.BytesIO(uploaded_file.getvalue()), always_2d=True)

    # Preserve channels for analysis.
    data = np.asarray(data)
    channel_count = data.shape[1]

    if channel_count == 1:
        x = data[:, 0]
        representation = "real"
        possible_iq = False
        corr = None
    elif channel_count == 2:
        c0 = data[:, 0].astype(float)
        c1 = data[:, 1].astype(float)

        c0_center = c0 - np.mean(c0)
        c1_center = c1 - np.mean(c1)
        denom = np.linalg.norm(c0_center) * np.linalg.norm(c1_center)
        corr = float(np.dot(c0_center, c1_center) / denom) if denom else 0.0

        # Match the backend's practical heuristic: duplicated channels are
        # treated as a real signal; sufficiently independent channels may be IQ.
        if abs(corr) > 0.95:
            x = c0
            representation = "real"
            possible_iq = False
        else:
            x = c0 + 1j * c1
            representation = "complex_iq"
            possible_iq = True
    else:
        x = data[:, 0]
        representation = "real"
        possible_iq = False
        corr = None

    return {
        "x": normalize_audio_or_complex(x),
        "fs": float(fs),
        "channels": int(channel_count),
        "representation": representation,
        "possible_iq": bool(possible_iq),
        "channel_correlation": corr,
        "num_samples": int(len(x)),
    }


def parse_uploaded_iq(uploaded_file, dtype_name, iq_order, endian, sample_rate=64000.0):
    raw = uploaded_file.getvalue()

    dtype_map = {
        "float32": "f4",
        "float64": "f8",
        "int16": "i2",
        "int32": "i4",
    }

    code = dtype_map[dtype_name]
    code = ("<" if endian == "Little" else ">") + code

    values = np.frombuffer(raw, dtype=np.dtype(code))

    if len(values) < 4:
        raise ValueError("IQ file is too small for the selected format.")

    if len(values) % 2:
        values = values[:-1]

    values = values.astype(np.float64)

    i = values[0::2]
    q = values[1::2]

    if iq_order == "Q-I":
        i, q = q, i

    x = i + 1j * q
    x = normalize_audio_or_complex(x)

    return {
        "x": x,
        "fs": float(sample_rate) if sample_rate else None,
        "sample_rate_source": "User Supplied (Raw IQ has no header)",
        "channels": 2,
        "representation": "complex_iq",
        "possible_iq": True,
        "channel_correlation": None,
        "num_samples": int(len(x)),
        "iq_dtype": dtype_name,
        "iq_order": iq_order,
        "iq_endian": endian,
    }


# ============================================================
# BACKEND ADAPTER
# ============================================================

def run_project_backend(file_path, sample_rate=None, dtype=np.float32, iq_order="IQ"):
    """
    Connect the interactive GUI to the existing backend.

    Expected current backend entry point:
        core.receiver.analyze_signal(...)
    """
    try:
        from core import receiver
    except Exception as exc:
        raise RuntimeError(
            "Could not import core.receiver. Start Streamlit from the project root "
            "where the autosig_intel/core package is available."
        ) from exc

    analyze_fn = getattr(receiver, "analyze_signal", None)
    if analyze_fn is None:
        raise RuntimeError(
            "core.receiver.analyze_signal was not found. "
            "Expose the receiver through this function."
        )

    sig = inspect.signature(analyze_fn)
    params = sig.parameters

    candidate_kwargs = {}

    for name in ("file_path", "filepath", "path", "filename", "input_path"):
        if name in params:
            candidate_kwargs[name] = str(file_path)
            break
    else:
        positional = [
            p for p in params.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if positional:
            candidate_kwargs[positional[0].name] = str(file_path)
        else:
            raise RuntimeError(
                "analyze_signal() does not expose an input-file parameter."
            )

    if "sample_rate" in params and sample_rate is not None:
        candidate_kwargs["sample_rate"] = float(sample_rate)
    if "dtype" in params and dtype is not None:
        candidate_kwargs["dtype"] = dtype
    if "iq_order" in params and iq_order is not None:
        candidate_kwargs["iq_order"] = iq_order

    if "verbose" in params:
        candidate_kwargs["verbose"] = False

    result = analyze_fn(**candidate_kwargs)

    if result is None:
        raise RuntimeError("Backend returned no analysis result.")

    if not isinstance(result, dict):
        result = {"backend_result": result}

    return result


# ============================================================
# SIGNAL ANALYSIS FOR THE LIVE GUI
# ============================================================

def representative_segment(x, fs, seconds=2.0, max_samples=200_000):
    if len(x) == 0:
        return x

    n_target = min(len(x), int(seconds * fs), max_samples)

    if n_target <= 0:
        return x[:0]

    # Start near the beginning for reproducibility.
    return x[:n_target]


def analytic_for_plot(x):
    if np.iscomplexobj(x):
        return x
    return hilbert(np.real(x))


def compute_waveform(x, fs, seconds=1.0, max_points=6000):
    seg = representative_segment(x, fs, seconds)
    if len(seg) == 0:
        return np.array([]), np.array([])

    step = max(1, len(seg) // max_points)
    y = seg[::step]
    t = np.arange(len(y)) * step / fs

    return t, y


def compute_spectrum(x, fs, max_points=5000):
    if len(x) < 32:
        return np.array([]), np.array([])

    nperseg = min(8192, len(x))
    noverlap = nperseg // 2

    if np.iscomplexobj(x):
        f, pxx = signal.welch(
            x,
            fs=fs,
            nperseg=nperseg,
            noverlap=noverlap,
            return_onesided=False,
            scaling="density",
        )
        order = np.argsort(f)
        f, pxx = f[order], pxx[order]
    else:
        f, pxx = signal.welch(
            np.real(x),
            fs=fs,
            nperseg=nperseg,
            noverlap=noverlap,
            return_onesided=True,
            scaling="density",
        )

    p_db = 10 * np.log10(np.maximum(pxx, 1e-15))
    step = max(1, len(f) // max_points)

    return f[::step], p_db[::step]


def compute_spectrogram(x, fs, seconds=8.0):
    seg = representative_segment(x, fs, seconds, max_samples=500_000)
    if len(seg) < 128:
        return None

    nperseg = min(2048, len(seg))
    noverlap = int(nperseg * 0.75)

    if np.iscomplexobj(seg):
        f, t, z = signal.stft(
            seg,
            fs=fs,
            nperseg=nperseg,
            noverlap=noverlap,
            return_onesided=False,
        )
        order = np.argsort(f)
        f = f[order]
        z = z[order, :]
        power = np.abs(z) ** 2
    else:
        f, t, z = signal.stft(
            np.real(seg),
            fs=fs,
            nperseg=nperseg,
            noverlap=noverlap,
            return_onesided=True,
        )
        power = np.abs(z) ** 2

    power_db = 10 * np.log10(np.maximum(power, 1e-15))

    # Keep plots fast.
    if len(t) > 500:
        t_idx = np.linspace(0, len(t) - 1, 500).astype(int)
        t = t[t_idx]
        power_db = power_db[:, t_idx]

    if len(f) > 500:
        f_idx = np.linspace(0, len(f) - 1, 500).astype(int)
        f = f[f_idx]
        power_db = power_db[f_idx, :]

    return t, f, power_db


def compute_constellation(x, fs, max_points=10_000):
    if len(x) == 0:
        return np.array([]), np.array([])

    z = analytic_for_plot(x)
    z = z / max(np.max(np.abs(z)), 1e-12)

    # Random-free uniform thinning.
    if len(z) > max_points:
        idx = np.linspace(0, len(z) - 1, max_points).astype(int)
        z = z[idx]

    return np.real(z), np.imag(z)


def compute_instantaneous_frequency(x, fs, max_points=8000):
    z = analytic_for_plot(x)

    if len(z) < 4:
        return np.array([]), np.array([])

    phase = np.unwrap(np.angle(z))
    inst = np.diff(phase) * fs / (2 * np.pi)

    # Remove extreme numerical spikes for a more readable diagnostic view.
    finite = np.isfinite(inst)
    inst = inst[finite]

    if len(inst) == 0:
        return np.array([]), np.array([])

    if len(inst) > 4_000:
        lo, hi = np.percentile(inst, [1, 99])
        inst = np.clip(inst, lo, hi)

    step = max(1, len(inst) // max_points)
    inst = inst[::step]
    t = np.arange(len(inst)) * step / fs

    return t, inst


def extract_peak_frequency(x, fs):
    f, p = compute_spectrum(x, fs, max_points=10000)
    if len(f) == 0:
        return None

    idx = int(np.argmax(p))
    return float(f[idx])


# ============================================================
# RESULT EXTRACTION / PRESENTATION
# ============================================================

def extract_modulation(result):
    value = first_value(
        result,
        "modulation",
        "best_modulation",
        "modulation_type",
        default=None,
    )

    if value is None:
        best = result.get("best_hypothesis")
        if isinstance(best, dict):
            value = best.get("modulation")

    if value is None:
        return "UNKNOWN"

    return str(value)


def extract_confidence(result):
    value = first_value(
        result,
        "confidence",
        "confidence_percent",
        "modulation_confidence",
        default=None,
    )

    if value is None:
        best = result.get("best_hypothesis")
        if isinstance(best, dict):
            value = best.get("confidence", best.get("score"))

    if value is None:
        return None

    try:
        x = float(value)
        if x <= 1:
            x *= 100
        return x
    except (TypeError, ValueError):
        return None


def result_to_csv_row(result, signal_meta, file_name, live_peak_frequency):
    modulation = extract_modulation(result)
    confidence = extract_confidence(result)

    return {
        "filename": file_name,
        "sample_rate_hz": signal_meta.get("fs"),
        "num_samples": signal_meta.get("num_samples"),
        "duration_seconds": (
            signal_meta["num_samples"] / signal_meta["fs"]
            if signal_meta.get("fs")
            else None
        ),
        "channels": signal_meta.get("channels"),
        "representation": signal_meta.get("representation"),
        "possible_iq": signal_meta.get("possible_iq"),
        "channel_correlation": signal_meta.get("channel_correlation"),
        "peak_frequency_hz_live": live_peak_frequency,
        "modulation_hypothesis": modulation,
        "modulation_confidence_percent": confidence,
        "estimated_bandwidth_hz": first_value(
            result, "estimated_bandwidth_hz", "occupied_bandwidth_hz"
        ),
        "estimated_noise_floor_db": first_value(
            result, "estimated_noise_floor_db", "noise_floor_db"
        ),
        "estimated_snr_proxy_db": first_value(
            result, "estimated_snr_db", "snr_db", "spectral_snr_proxy_db"
        ),
        "samples_per_symbol": first_value(
            result, "samples_per_symbol", "sps"
        ),
        "symbol_rate_baud": first_value(
            result, "symbol_rate_baud", "symbol_rate"
        ),
    }


def make_figure(fig):
    fig.update_layout(
        height=360,
        margin=dict(l=45, r=20, t=20, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(2,8,16,0.75)",
        font=dict(color="white"),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.10)",
            title_font=dict(size=12, color="gray"),
            tickfont=dict(color="gray"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.10)",
            title_font=dict(size=12, color="gray"),
            tickfont=dict(color="gray"),
        ),
    )
    return fig


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        "<div class='sidebar-badge'>● SIGNAL NODE: ONLINE</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<h2>◈ NTRO GATEWAY</h2>", unsafe_allow_html=True)
    st.caption("Automated Signal Analysis & Parameter Extraction")
    st.divider()

    if st.session_state.is_analyzed:
        st.markdown(
            "<div class='sidebar-section-title'>Navigation</div>",
            unsafe_allow_html=True,
        )
        if st.button("⬅ RETURN TO HOMEPAGE", use_container_width=True):
            st.session_state.is_analyzed = False
            st.session_state.analysis_result = None
            st.session_state.signal_data = None
            st.session_state.signal_path = None
            st.session_state.analysis_logs = []
            st.rerun()

    st.markdown(
        "<div class='sidebar-section-title'>1. Telemetry Ingest</div>",
        unsafe_allow_html=True,
    )

    ingest_source = st.radio(
        "Source",
        ["Official Jury Demos", "Custom File Upload"],
        horizontal=True,
    )

    uploaded_file = None
    iq_dtype = "float32"
    iq_order = "I-Q"
    iq_endian = "Little"
    iq_sample_rate = 64000.0

    demo_dir = Path(__file__).resolve().parents[1] / "samples" / "demo"
    if ingest_source == "Official Jury Demos":
        demo_map = {
            "DEMO 01: BPSK + Block + Viterbi (.wav)": demo_dir / "DEMO_01_BPSK_VITERBI.wav",
            "DEMO 01: BPSK + Block + Viterbi (.iq)": demo_dir / "DEMO_01_BPSK_VITERBI_f32.iq",
            "DEMO 02: QPSK + Diagonal + RS (.wav)": demo_dir / "DEMO_02_QPSK_RS.wav",
            "DEMO 02: QPSK + Diagonal + RS (.iq)": demo_dir / "DEMO_02_QPSK_RS_f32.iq",
            "DEMO 03: 16-QAM + Concatenated (.wav)": demo_dir / "DEMO_03_16QAM_CONCATENATED.wav",
            "DEMO 03: 16-QAM + Concatenated (.iq)": demo_dir / "DEMO_03_16QAM_CONCATENATED_f32.iq",
            "DEMO 04: 2-FSK + Convolutional + Viterbi (.wav)": demo_dir / "DEMO_04_2FSK_VITERBI.wav",
            "DEMO 04: 2-FSK + Convolutional + Viterbi (.iq)": demo_dir / "DEMO_04_2FSK_VITERBI_f32.iq",
            "DEMO 05: UNKNOWN AUDIO (Voice .wav - Gatekeeper)": demo_dir / "DEMO_05_UNKNOWN_AUDIO.wav",
        }
        selected_demo = st.selectbox("Select Official Demo Signal", list(demo_map.keys()))
        target_path = demo_map[selected_demo]
        if target_path.exists():
            uploaded_file = DemoFileWrapper(target_path)
            st.caption(f"📁 Selected: `{target_path.name}` ({target_path.stat().st_size / 1024:.1f} KB)")
        else:
            st.warning(f"File {target_path.name} not found in samples/demo.")

        if uploaded_file is not None and uploaded_file.name.lower().endswith(".iq"):
            st.markdown(
                "<div class='sidebar-section-title'>IQ FORMAT</div>",
                unsafe_allow_html=True,
            )
            def_rate = 48000.0 if ("DEMO_01" in uploaded_file.name or "DEMO_04" in uploaded_file.name) else 64000.0
            iq_sample_rate = st.number_input("IQ Sample Rate (Hz)", min_value=1000.0, max_value=10000000.0, value=def_rate, step=1000.0)
            iq_dtype = "float32"
            iq_order = "I-Q"
            iq_endian = "Little"
            st.caption("Default IQ parameters pre-configured: float32, Little-endian, I-Q")
    else:
        uploaded_file = st.file_uploader(
            "Upload .wav / .iq",
            type=["wav", "iq"],
            help="WAV files can be analyzed immediately. Raw IQ files require the correct binary format settings below.",
        )

        if uploaded_file is not None and uploaded_file.name.lower().endswith(".iq"):
            st.markdown(
                "<div class='sidebar-section-title'>IQ FORMAT</div>",
                unsafe_allow_html=True,
            )
            iq_sample_rate = st.number_input("IQ Sample Rate (Hz)", min_value=1000.0, max_value=10000000.0, value=64000.0, step=1000.0)
            iq_dtype = st.selectbox(
                "Sample dtype",
                ["float32", "int16", "float64", "int32"],
                index=0,
            )
            iq_order = st.selectbox("Channel order", ["I-Q", "Q-I"])
            iq_endian = st.selectbox("Byte order", ["Little", "Big"])

    st.markdown(
        "<div class='sidebar-section-title'>2. DSP Configuration</div>",
        unsafe_allow_html=True,
    )

    modulation_target = st.selectbox(
        "Modulation Target",
        ["Auto-Detect", "FSK", "QAM", "PSK"],
    )

    deinterleave_mode = st.selectbox(
        "De-interleaver Mode",
        ["Auto", "Block", "Convolution", "Diagonal", "Pseudo Random"],
    )

    fec_engine = st.selectbox(
        "FEC Engine",
        [
            "Auto",
            "Viterbi (Convolutional)",
            "Reed-Solomon",
            "Concatenated",
            "LDPC",
        ],
    )

    st.markdown(
        "<div class='sidebar-section-title'>3. Visualization</div>",
        unsafe_allow_html=True,
    )

    display_seconds = st.slider(
        "Time window",
        min_value=0.25,
        max_value=10.0,
        value=2.0,
        step=0.25,
    )

    max_points = st.slider(
        "Plot points",
        min_value=1000,
        max_value=12000,
        value=6000,
        step=1000,
    )

    st.markdown(
        "<div class='sidebar-section-title'>4. Execution</div>",
        unsafe_allow_html=True,
    )

    analyze_btn = st.button(
        "INITIATE ANALYSIS ENGINE",
        type="primary",
        use_container_width=True,
    )

    if uploaded_file is None:
        st.caption("Attach a signal file to enable analysis.")

    st.divider()
    st.caption("Build: AUTOSIG-INTEL / SIGNALX UI")


# ============================================================
# RUN ANALYSIS
# ============================================================

if analyze_btn:
    if uploaded_file is None:
        st.error("FILE NOT ATTACHED. Upload a .wav or .iq file.")
    else:
        st.session_state.analysis_logs = []
        st.session_state.analysis_result = None
        st.session_state.signal_data = None
        st.session_state.signal_path = None

        progress = st.progress(0, text="Preparing input...")

        suffix = Path(uploaded_file.name).suffix.lower()

        try:
            add_log("INGESTION: Signal file received.")

            # Use direct file path if available, or write uploaded bytes to temporary file.
            if hasattr(uploaded_file, "file_path") and uploaded_file.file_path.exists():
                local_path = uploaded_file.file_path
                st.session_state.signal_path = str(local_path)
            else:
                tmp_dir = Path(tempfile.gettempdir()) / "autosig_intel_gui"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                safe_name = Path(uploaded_file.name).name
                local_path = tmp_dir / safe_name
                local_path.write_bytes(uploaded_file.getvalue())
                st.session_state.signal_path = str(local_path)

            progress.progress(15, text="Parsing signal format...")

            if suffix == ".wav":
                signal_meta = parse_uploaded_wav(uploaded_file)
            elif suffix == ".iq":
                signal_meta = parse_uploaded_iq(
                    uploaded_file,
                    iq_dtype,
                    iq_order,
                    iq_endian,
                    sample_rate=iq_sample_rate,
                )
            else:
                raise ValueError("Unsupported file type.")

            st.session_state.signal_data = signal_meta

            add_log(
                f"INGESTION: {uploaded_file.name} loaded | "
                f"representation={signal_meta['representation']}"
            )

            progress.progress(30, text="Running AutoSig-Intel backend...")

            backend_result = run_project_backend(
                local_path,
                sample_rate=iq_sample_rate if suffix == ".iq" else None,
                dtype=np.dtype(iq_dtype) if suffix == ".iq" else np.float32,
                iq_order=iq_order.replace("-", "") if suffix == ".iq" else "IQ",
            )

            # Store the selected GUI controls alongside the actual backend result.
            backend_result["_gui"] = {
                "modulation_target": modulation_target,
                "deinterleave_mode": deinterleave_mode,
                "fec_engine": fec_engine,
                "file_name": uploaded_file.name,
            }

            st.session_state.analysis_result = backend_result

            add_log("CHARACTERIZATION: Backend analysis completed.")
            progress.progress(60, text="Generating live signal diagnostics...")

            fs = signal_meta.get("fs")
            if fs is not None:
                peak_freq = extract_peak_frequency(signal_meta["x"], fs)
                add_log(
                    f"ANALYTICS: Peak frequency candidate = "
                    f"{fmt_hz(peak_freq)}"
                )
            else:
                peak_freq = None

            progress.progress(82, text="Preparing waveform / spectrum / waterfall...")

            add_log("ANALYTICS: Waveform, spectrum and spectrogram prepared.")
            add_log("ANALYTICS: Analytic complex-plane view prepared.")
            add_log("ANALYTICS: Instantaneous-frequency diagnostic prepared.")

            # We deliberately do NOT fake FEC/interleaving completion.
            add_log("DECODING: Interleaving/FEC modules remain hypothesis-driven.")
            add_log("VALIDATION: GUI is displaying measured/backend values only.")

            progress.progress(100, text="Analysis complete.")
            time.sleep(0.2)
            progress.empty()

            st.session_state.is_analyzed = True
            st.rerun()

        except Exception as exc:
            progress.empty()
            st.session_state.is_analyzed = False
            st.error(f"ANALYSIS ERROR: {exc}")
            add_log(f"ERROR: {type(exc).__name__}: {exc}")


# ============================================================
# LANDING PAGE
# ============================================================

if not st.session_state.is_analyzed:
    st.markdown(
        "<div class='mission-status-banner'>MISSION STATUS: AWAITING SIGNAL TELEMETRY</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='hero-title'>SIGNALX</div>"
        "<div class='hero-subtitle'>Tactical Signal Intelligence & Parameter Extraction</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='status-box'>
            <b style='color:#00ffaa;'>SYSTEM READY</b><br>
            <span style='color:#a0aec0;'>
            Upload a WAV or raw IQ capture. The interface then connects the live signal
            to the AutoSig-Intel backend and replaces simulated telemetry with measured
            signal parameters and diagnostics.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c, d = st.columns(4)

    cards = [
        ("INGESTION", "WAV / IQ parsing<br>channel & representation detection"),
        ("CHARACTERIZATION", "sampling rate<br>spectrum / bandwidth / signal statistics"),
        ("HYPOTHESIS", "FSK / PSK / QAM<br>timing & confidence candidates"),
        ("DECODING", "demodulation<br>interleaving / FEC / correlation pipeline"),
    ]

    for col, (title, body) in zip((a, b, c, d), cards):
        with col:
            st.markdown(
                f"""
                <div class='liquid-glass-card' style='min-height:145px;'>
                    <div class='metric-tag'>{title}</div>
                    <div style='color:#e2e8f0;font-size:16px;line-height:1.5;margin-top:10px;'>
                        {body}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown(
        "<h3 style='color:white;'>Backend Integration Status</h3>",
        unsafe_allow_html=True,
    )

    st.info(
        "The GUI is now designed as a live front end for the existing AutoSig-Intel "
        "backend. It does not fabricate modulation, RF frequency, SNR, FEC, or payload values."
    )


# ============================================================
# ANALYZED VIEW
# ============================================================

else:
    result = st.session_state.analysis_result or {}
    signal_meta = st.session_state.signal_data or {}
    x = signal_meta.get("x")

    file_name = result.get("_gui", {}).get(
        "file_name",
        Path(st.session_state.signal_path or "signal").name,
    )

    fs = signal_meta.get("fs")
    duration = (
        signal_meta["num_samples"] / fs
        if fs is not None and signal_meta.get("num_samples")
        else None
    )

    modulation = extract_modulation(result)
    confidence = extract_confidence(result)

    peak_freq = None
    if x is not None and fs is not None:
        peak_freq = extract_peak_frequency(x, fs)

    bandwidth = first_value(
        result,
        "estimated_bandwidth_hz",
        "occupied_bandwidth_hz",
        "bandwidth_hz",
    )

    noise_floor = first_value(
        result,
        "estimated_noise_floor_db",
        "noise_floor_db",
    )

    snr = first_value(
        result,
        "estimated_snr_db",
        "snr_db",
        "spectral_snr_proxy_db",
    )

    sps = first_value(result, "samples_per_symbol", "sps")
    symbol_rate = first_value(result, "symbol_rate_baud", "symbol_rate")

    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:15px;margin-bottom:15px;'>
            <div>
                <div style='font-family:Orbitron;font-size:30px;color:#00d2ff;'>
                    SIGNALX
                </div>
                <div style='color:#8fa0b5;font-size:12px;letter-spacing:3px;'>
                    LIVE SIGNAL ANALYSIS MATRIX
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='mission-status-banner'>ACTIVE FILE: {file_name}</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Parameter tiles
    # --------------------------------------------------------

    p1, p2, p3, p4 = st.columns(4)

    def tile(col, title, reading, badge, badge_class):
        with col:
            st.markdown(
                f"""
                <div class='liquid-glass-card'>
                    <div class='metric-tag'>{title}</div>
                    <div class='metric-reading'>{reading}</div>
                    <span class='metric-badge {badge_class}'>{badge}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    tile(
        p1,
        "Sampling Frequency",
        fmt_hz(fs),
        "Measured from file" if fs is not None else "Metadata required",
        "badge-green" if fs is not None else "badge-amber",
    )

    conf_text = (
        f"{confidence:.1f}% confidence"
        if confidence is not None
        else "Hypothesis under evaluation"
    )

    tile(
        p2,
        "Modulation",
        modulation,
        conf_text,
        "badge-cyan" if modulation != "UNKNOWN" else "badge-amber",
    )

    tile(
        p3,
        "Duration",
        fmt_number(duration, 2, " s"),
        f"{signal_meta.get('channels', '?')} channel(s)",
        "badge-cyan",
    )

    tile(
        p4,
        "Representation",
        signal_meta.get("representation", "unknown"),
        "Possible IQ" if signal_meta.get("possible_iq") else "Real signal",
        "badge-green" if signal_meta.get("possible_iq") else "badge-cyan",
    )

    p5, p6, p7, p8 = st.columns(4)

    tile(p5, "Peak / Center Candidate", fmt_hz(peak_freq), "Relative frequency", "badge-cyan")
    tile(p6, "Occupied Bandwidth", fmt_hz(bandwidth), "Backend estimate", "badge-cyan")
    tile(p7, "Noise Floor", fmt_number(noise_floor, 2, " dB"), "Measured estimate", "badge-amber")
    tile(p8, "SNR", fmt_number(snr, 2, " dB"), "Screening metric", "badge-amber")

    st.write("")

    # --------------------------------------------------------
    # Visual End-to-End Decoding Path Trajectory
    # --------------------------------------------------------
    scr_status = result.get("hypothesis_report", {}).get("screen", {}).get("decision", "PASS")
    scr_cls = "validated" if scr_status == "PASS" else ("rejected" if scr_status == "NON_DIGITAL_LIKELY" else "active")
    t_cand = sps if sps is not None else "AUTO"
    t_cls = "validated" if sps is not None else "active"
    m_cls = "validated" if modulation not in ("UNKNOWN", "NONE") else "rejected"
    d_bits_count = len(result.get("recovered_bits") or [])
    d_cls = "validated" if d_bits_count > 0 else "active"
    dec_info = result.get("decoding", {})
    int_info = dec_info.get("interleaving", {})
    int_type = int_info.get("best_hypothesis", "NONE")
    int_cls = "validated" if int_info.get("status") == "VALIDATED" else ("active" if int_type not in ("NONE", "UNKNOWN") else "rejected")
    fec_info = dec_info.get("fec", {})
    fec_type = fec_info.get("best_hypothesis", "NONE")
    fec_cls = "validated" if fec_info.get("fec_valid") else ("active" if fec_type not in ("NONE", "UNKNOWN") else "rejected")
    corr_info = dec_info.get("correlation", {})
    p_info = corr_info.get("preamble")
    p_name = p_info.get("pattern_type", "NO_PREAMBLE") if p_info else "NO_SYNC"
    p_cls = "validated" if corr_info.get("status") == "VALIDATED" else "active"
    conf_tier = result.get("best_hypothesis", {}).get("confidence_tier", "MEDIUM CONFIDENCE")
    tier_badge = "badge-green" if "HIGH" in conf_tier else ("badge-amber" if "MEDIUM" in conf_tier else "badge-magenta")

    st.markdown(
        f"""
        <div class='chart-liquid-panel' style='margin-bottom:14px; padding:12px 16px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                <span style='font-family:Orbitron; font-size:12px; color:#00d2ff; letter-spacing:1px;'>
                    ◈ END-TO-END DECODING PIPELINE TRAJECTORY
                </span>
                <span class='{tier_badge}' style='font-family:Orbitron; font-size:11px; padding:3px 8px; border-radius:4px;'>
                    {conf_tier}: {confidence if confidence is not None else 0.0:.1f}%
                </span>
            </div>
            <div class='path-container'>
                <div class='path-step validated'>
                    <span class='path-title'>1. INPUT</span>
                    <span class='path-val'>{signal_meta.get("representation", "IQ")}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {scr_cls}'>
                    <span class='path-title'>2. SCREEN</span>
                    <span class='path-val'>{scr_status}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {t_cls}'>
                    <span class='path-title'>3. TIMING</span>
                    <span class='path-val'>SPS={t_cand}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {m_cls}'>
                    <span class='path-title'>4. MODULATION</span>
                    <span class='path-val'>{modulation}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {d_cls}'>
                    <span class='path-title'>5. DEMOD</span>
                    <span class='path-val'>{d_bits_count} bits</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {int_cls}'>
                    <span class='path-title'>6. DEINTERLEAVE</span>
                    <span class='path-val'>{str(int_type)[:12]}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {fec_cls}'>
                    <span class='path-title'>7. FEC</span>
                    <span class='path-val'>{str(fec_type)[:12]}</span>
                </div>
                <div class='path-arrow'>➔</div>
                <div class='path-step {p_cls}'>
                    <span class='path-title'>8. PAYLOAD</span>
                    <span class='path-val'>{p_name}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # 9-Tab Automated Architecture Workflow
    # --------------------------------------------------------

    (
        tab_input,
        tab_char,
        tab_mod,
        tab_demod,
        tab_interleave,
        tab_fec,
        tab_bitstream,
        tab_evidence,
        tab_exports,
    ) = st.tabs(
        [
            "1. INPUT & INGESTION",
            "2. SIGNAL CHARACTERIZATION",
            "3. MODULATION & SYNC",
            "4. DEMODULATION",
            "5. DE-INTERLEAVING",
            "6. FEC DECODER",
            "7. BITSTREAM & FRAMES",
            "8. HYPOTHESIS & EVIDENCE",
            "9. EXPORTS & ARTIFACTS",
        ]
    )

    # ========================================================
    # 1. INPUT & INGESTION
    # ========================================================

    with tab_input:
        left, right = st.columns([1.05, 0.95])

        with left:
            st.markdown("<div class='chart-liquid-panel'>", unsafe_allow_html=True)
            st.markdown(
                "<h3 style='color:white;font-size:17px;'>Signal Ingestion & Container Analysis</h3>",
                unsafe_allow_html=True,
            )

            summary = {
                "File": file_name,
                "Samples": signal_meta.get("num_samples"),
                "Sample rate (Hz)": fs,
                "Duration (s)": duration,
                "Channels": signal_meta.get("channels"),
                "Representation": signal_meta.get("representation"),
                "Possible IQ": signal_meta.get("possible_iq"),
                "Channel correlation": signal_meta.get("channel_correlation"),
            }

            st.dataframe(
                pd.DataFrame(summary.items(), columns=["Parameter", "Value"]),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='chart-liquid-panel'>", unsafe_allow_html=True)
            st.markdown(
                "<h3 style='color:white;font-size:17px;'>Hypothesis Status</h3>",
                unsafe_allow_html=True,
            )

            if modulation == "UNKNOWN":
                st.warning(
                    "No modulation type is being asserted from the current evidence."
                )
            else:
                st.success(
                    f"Current backend hypothesis: {modulation}"
                )

            if confidence is not None:
                st.metric("Hypothesis confidence", f"{confidence:.1f}%")

            st.caption(
                "Confidence is the cross-stage hypothesis score combining modulation clustering, "
                "timing sharpness, frame preamble correlation, and FEC syndrome validation."
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Waveform preview in input tab
        if x is not None and fs is not None:
            st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Raw Waveform Time Domain</h3>", unsafe_allow_html=True)
            t_wave, y_wave = compute_waveform(x, fs, seconds=display_seconds, max_points=max_points)
            fig_w = go.Figure()
            if np.iscomplexobj(y_wave):
                fig_w.add_trace(go.Scatter(x=t_wave, y=np.real(y_wave), mode="lines", name="I / Real", line=dict(color="#00d2ff", width=1.2)))
                fig_w.add_trace(go.Scatter(x=t_wave, y=np.imag(y_wave), mode="lines", name="Q / Imag", line=dict(color="#00ffaa", width=1.2)))
            else:
                fig_w.add_trace(go.Scatter(x=t_wave, y=y_wave, mode="lines", name="Signal", line=dict(color="#00d2ff", width=1.1)))
            fig_w.update_layout(xaxis_title="Time (s)", yaxis_title="Amplitude")
            st.plotly_chart(make_figure(fig_w), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # 2. SIGNAL CHARACTERIZATION
    # ========================================================

    with tab_char:
        if x is None or fs is None:
            st.warning("Live characterization plots require a known sample rate.")
        else:
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Power Spectrum (Welch PSD)</h3>", unsafe_allow_html=True)
                f_spec, p_spec = compute_spectrum(x, fs)
                fig_s = go.Figure(data=go.Scatter(x=f_spec, y=p_spec, mode="lines", line=dict(color="#00ffaa", width=1.2)))
                fig_s.update_layout(xaxis_title="Frequency (Hz)", yaxis_title="PSD (dB/Hz)")
                st.plotly_chart(make_figure(fig_s), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c_p2:
                st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Waterfall / Spectrogram</h3>", unsafe_allow_html=True)
                spec = compute_spectrogram(x, fs, seconds=max(display_seconds, 4.0))
                if spec is not None:
                    st_t, st_f, st_p = spec
                    fig_wf = go.Figure(data=go.Heatmap(z=st_p, x=st_t, y=st_f, colorscale="Turbo", colorbar=dict(title="dB")))
                    fig_wf.update_layout(xaxis_title="Time (s)", yaxis_title="Frequency (Hz)")
                    st.plotly_chart(make_figure(fig_wf), use_container_width=True)
                else:
                    st.warning("Signal too short for spectrogram.")
                st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # 3. MODULATION & SYNC
    # ========================================================

    with tab_mod:
        if x is None or fs is None:
            st.warning("Synchronization requires a known sample rate.")
        else:
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Analytic Complex Plane</h3>", unsafe_allow_html=True)
                i_data, q_data = compute_constellation(x, fs, max_points=min(max_points, 10000))
                fig_c = go.Figure(data=go.Scattergl(x=i_data, y=q_data, mode="markers", marker=dict(color="#00d2ff", size=3, opacity=0.38)))
                fig_c.update_layout(xaxis_title="In-Phase", yaxis_title="Quadrature", xaxis=dict(scaleanchor="y", scaleratio=1))
                st.plotly_chart(make_figure(fig_c), use_container_width=True)
                st.caption("Raw analytic complex plane before symbol timing and carrier synchronization.")
                st.markdown("</div>", unsafe_allow_html=True)

            with c_m2:
                st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Instantaneous Frequency Diagnostic</h3>", unsafe_allow_html=True)
                it_f, ifreq_f = compute_instantaneous_frequency(x, fs, max_points=max_points)
                fig_if = go.Figure(data=go.Scatter(x=it_f, y=ifreq_f, mode="lines", line=dict(color="#ff0055", width=1.0)))
                fig_if.update_layout(xaxis_title="Time (s)", yaxis_title="Frequency (Hz)")
                st.plotly_chart(make_figure(fig_if), use_container_width=True)
                st.caption("Diagnostic indicator for FSK tone transitions vs PSK phase jumps.")
                st.markdown("</div>", unsafe_allow_html=True)

            # Timing candidates table
            st.markdown("<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Derived Symbol Timing Candidates</h3>", unsafe_allow_html=True)
            timing_candidates = result.get("timing_candidates") or result.get("timing_hypotheses") or result.get("sps_candidates")
            if isinstance(timing_candidates, list) and timing_candidates:
                st.dataframe(pd.DataFrame(timing_candidates), use_container_width=True, hide_index=True)
            else:
                timing_text = f"Current SPS candidate: {sps}" if sps is not None else "No timing candidate exposed by backend."
                st.info(timing_text)
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # DSP VISUALS
    # ========================================================

    with tab_dsp:
        if x is None or fs is None:
            st.warning(
                "Live DSP plots require a known sample rate. "
                "For raw IQ, provide metadata or configure a sample rate in the backend."
            )
        else:
            # Row 1: waveform + spectrum
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Waveform</h3>",
                    unsafe_allow_html=True,
                )

                t, y = compute_waveform(
                    x, fs, seconds=display_seconds, max_points=max_points
                )

                if np.iscomplexobj(y):
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=t,
                            y=np.real(y),
                            mode="lines",
                            name="I / Real",
                            line=dict(color="#00d2ff", width=1.2),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=t,
                            y=np.imag(y),
                            mode="lines",
                            name="Q / Imag",
                            line=dict(color="#00ffaa", width=1.2),
                        )
                    )
                    fig.update_layout(
                        xaxis_title="Time (s)",
                        yaxis_title="Amplitude",
                    )
                else:
                    fig = go.Figure(
                        data=go.Scatter(
                            x=t,
                            y=y,
                            mode="lines",
                            line=dict(color="#00d2ff", width=1.1),
                        )
                    )
                    fig.update_layout(
                        xaxis_title="Time (s)",
                        yaxis_title="Amplitude",
                    )

                st.plotly_chart(make_figure(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c2:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Power Spectrum</h3>",
                    unsafe_allow_html=True,
                )

                f, p = compute_spectrum(x, fs)

                fig = go.Figure(
                    data=go.Scatter(
                        x=f,
                        y=p,
                        mode="lines",
                        line=dict(color="#00ffaa", width=1.2),
                    )
                )

                fig.update_layout(
                    xaxis_title="Frequency (Hz)",
                    yaxis_title="PSD (dB/Hz)",
                )

                st.plotly_chart(make_figure(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Row 2: constellation + waterfall
            c3, c4 = st.columns(2)

            with c3:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Analytic Complex Plane</h3>",
                    unsafe_allow_html=True,
                )

                i_data, q_data = compute_constellation(x, fs, max_points=min(max_points, 10000))

                fig = go.Figure(
                    data=go.Scattergl(
                        x=i_data,
                        y=q_data,
                        mode="markers",
                        marker=dict(
                            color="#00d2ff",
                            size=3,
                            opacity=0.38,
                        ),
                    )
                )

                fig.update_layout(
                    xaxis_title="In-phase",
                    yaxis_title="Quadrature",
                    xaxis=dict(scaleanchor="y", scaleratio=1),
                )

                st.plotly_chart(make_figure(fig), use_container_width=True)

                st.caption(
                    "This is an analytic complex-plane view of the raw signal. "
                    "It becomes a true symbol constellation only after synchronization/timing recovery."
                )

                st.markdown("</div>", unsafe_allow_html=True)

            with c4:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Waterfall / Spectrogram</h3>",
                    unsafe_allow_html=True,
                )

                spec = compute_spectrogram(
                    x,
                    fs,
                    seconds=max(display_seconds, 4.0),
                )

                if spec is not None:
                    st_t, st_f, st_p = spec

                    fig = go.Figure(
                        data=go.Heatmap(
                            z=st_p,
                            x=st_t,
                            y=st_f,
                            colorscale="Turbo",
                            colorbar=dict(title="dB"),
                        )
                    )

                    fig.update_layout(
                        xaxis_title="Time (s)",
                        yaxis_title="Frequency (Hz)",
                    )

                    st.plotly_chart(make_figure(fig), use_container_width=True)
                else:
                    st.warning("Signal is too short for a meaningful spectrogram.")

                st.markdown("</div>", unsafe_allow_html=True)

            # Row 3: instantaneous frequency
            c5, c6 = st.columns(2)

            with c5:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Instantaneous Frequency Diagnostic</h3>",
                    unsafe_allow_html=True,
                )

                it, ifreq = compute_instantaneous_frequency(
                    x,
                    fs,
                    max_points=max_points,
                )

                fig = go.Figure(
                    data=go.Scatter(
                        x=it,
                        y=ifreq,
                        mode="lines",
                        line=dict(color="#ff0055", width=1.0),
                    )
                )

                fig.update_layout(
                    xaxis_title="Time (s)",
                    yaxis_title="Frequency (Hz)",
                )

                st.plotly_chart(make_figure(fig), use_container_width=True)

                st.caption(
                    "Use this plot as FSK evidence only after the signal has been "
                    "properly filtered and frequency-state clustering succeeds."
                )

                st.markdown("</div>", unsafe_allow_html=True)

            with c6:
                st.markdown(
                    "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Derived Timing Candidates</h3>",
                    unsafe_allow_html=True,
                )

                timing_candidates = (
                    result.get("timing_candidates")
                    or result.get("timing_hypotheses")
                    or result.get("sps_candidates")
                )

                if isinstance(timing_candidates, list) and timing_candidates:
                    st.dataframe(
                        pd.DataFrame(timing_candidates),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    timing_text = (
                        f"Current SPS candidate: {sps}"
                        if sps is not None
                        else "No timing candidate exposed by backend."
                    )
                    st.info(timing_text)

                st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # DEMODULATION
    # ========================================================

    with tab_demod:
        dm1, dm2, dm3, dm4 = st.columns(4)
        dec_demod = result.get("decoding", {}).get("demodulation", {})
        ev_sync = result.get("evidence_profile", {}).get("synchronization_residual", {})

        cfo_val = ev_sync.get("frequency_offset_hz", first_value(result, "cfo_est_hz", "frequency_offset_hz"))
        phase_val = ev_sync.get("phase_offset_rad", first_value(result, "phase_offset_rad"))
        recovered_bits_count = dec_demod.get(
            "recovered_bits_count",
            len(result.get("recovered_bits", [])) if result.get("recovered_bits") is not None else 0,
        )
        demod_status = dec_demod.get("status", result.get("demodulation_status", "UNKNOWN"))

        tile(
            dm1,
            "Demod Scheme",
            modulation,
            f"Status: {demod_status}",
            "badge-green" if demod_status == "VALIDATED" else "badge-amber",
        )
        tile(dm2, "Carrier CFO", fmt_hz(cfo_val), "Residual Offset", "badge-cyan")
        phase_deg = np.rad2deg(phase_val) if phase_val is not None and np.isfinite(phase_val) else None
        tile(
            dm3,
            "Phase Offset",
            f"{fmt_number(phase_val, 3)} rad" if phase_val is not None else "N/A",
            f"{fmt_number(phase_deg, 1)}°" if phase_deg is not None else "N/A",
            "badge-cyan",
        )
        tile(
            dm4,
            "Recovered Bits",
            str(recovered_bits_count),
            "Hard decisions",
            "badge-green" if recovered_bits_count > 0 else "badge-amber",
        )

        st.write("")
        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Synchronized Constellation</h3>",
                unsafe_allow_html=True,
            )
            best_hyp = result.get("best_hypothesis") or {}
            top_hyp = result.get("top_hypothesis") or {}
            sync_syms = best_hyp.get("symbols", top_hyp.get("symbols"))

            if sync_syms is not None and len(sync_syms) > 0:
                n_sym_plot = min(len(sync_syms), 6000)
                sub_syms = sync_syms[:n_sym_plot]
                fig = go.Figure(
                    data=go.Scattergl(
                        x=np.real(sub_syms),
                        y=np.imag(sub_syms),
                        mode="markers",
                        marker=dict(color="#00ffaa", size=4, opacity=0.6),
                    )
                )
                fig.update_layout(
                    xaxis_title="In-Phase (I)",
                    yaxis_title="Quadrature (Q)",
                    xaxis=dict(scaleanchor="y", scaleratio=1),
                )
                st.plotly_chart(make_figure(fig), use_container_width=True)
                st.caption(f"Synchronized symbol constellation ({n_sym_plot} symbols plotted after timing/carrier lock).")
            else:
                st.info("Synchronized symbols not explicitly cached. Showing analytic complex plane:")
                if x is not None and fs is not None:
                    i_data, q_data = compute_constellation(x, fs, max_points=4000)
                    fig = go.Figure(
                        data=go.Scattergl(
                            x=i_data,
                            y=q_data,
                            mode="markers",
                            marker=dict(color="#00d2ff", size=3, opacity=0.4),
                        )
                    )
                    fig.update_layout(
                        xaxis_title="In-Phase",
                        yaxis_title="Quadrature",
                        xaxis=dict(scaleanchor="y", scaleratio=1),
                    )
                    st.plotly_chart(make_figure(fig), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_right:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Ground-Truth BER Calculator</h3>",
                unsafe_allow_html=True,
            )
            st.caption("Paste reference bits (binary string '0101...' or hex '0x...') to verify receiver bit-error-rate against ground-truth:")
            ref_input = st.text_area("Reference Bitstream", height=90, placeholder="e.g. 010101100101... or 0x1ACFFC1D...")
            rec_bits = result.get("recovered_bits")
            if rec_bits is None:
                rec_bits = first_value(result, "bitstream", "bits")

            if ref_input.strip() and rec_bits is not None and len(rec_bits) > 0:
                clean_ref = ref_input.strip().lower()
                ref_bit_arr = None
                if clean_ref.startswith("0x"):
                    try:
                        hex_val = clean_ref[2:]
                        ref_bit_arr = np.array(
                            [int(b) for b in bin(int(hex_val, 16))[2:].zfill(len(hex_val) * 4)],
                            dtype=np.uint8,
                        )
                    except Exception:
                        st.error("Invalid hex format.")
                else:
                    try:
                        ref_bit_arr = np.array([int(b) for b in clean_ref if b in ('0', '1')], dtype=np.uint8)
                    except Exception:
                        st.error("Invalid binary string format.")

                if ref_bit_arr is not None and len(ref_bit_arr) > 0:
                    r_eval = np.asarray(rec_bits, dtype=np.uint8).flatten()
                    min_len = min(len(r_eval), len(ref_bit_arr))
                    errs = int(np.sum(r_eval[:min_len] != ref_bit_arr[:min_len]))
                    ber = errs / min_len if min_len > 0 else 0.0
                    acc = (1.0 - ber) * 100.0

                    b1, b2, b3 = st.columns(3)
                    b1.metric("Evaluated Bits", f"{min_len}")
                    b2.metric("Bit Errors", f"{errs}")
                    b3.metric("Measured BER", f"{ber:.4e}")

                    st.progress(acc / 100.0, text=f"Bit Accuracy: {acc:.2f}%")
                    disp_len = min(min_len, 64)
                    ref_str = "".join(str(b) for b in ref_bit_arr[:disp_len])
                    rec_str = "".join(str(b) for b in r_eval[:disp_len])
                    diff_str = "".join(" " if ref_bit_arr[i] == r_eval[i] else "^" for i in range(disp_len))
                    st.code(f"REF:  {ref_str}\nREC:  {rec_str}\nERR:  {diff_str}", language="text")
            elif not ref_input.strip():
                st.info("Awaiting reference bits to compute ground-truth BER.")
            else:
                st.warning("No recovered bits available from backend.")
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # INTERLEAVING
    # ========================================================

    with tab_interleave:
        int_dec = result.get("decoding", {}).get("interleaving", {})
        ev_int = result.get("evidence_profile", {}).get("interleaver_evidence", {})
        int_status = int_dec.get("status", result.get("deinterleaving_status", "UNKNOWN"))
        best_int = int_dec.get("best_hypothesis", ev_int.get("best", {}).get("type", "UNKNOWN"))
        int_params = int_dec.get("parameters", ev_int.get("best", {}).get("params", {}))
        int_score = ev_int.get("best", {}).get("score", 0.0)

        i1, i2, i3, i4 = st.columns(4)
        tile(
            i1,
            "Deinterleaver",
            str(best_int).upper(),
            f"Status: {int_status}",
            "badge-green" if int_status == "VALIDATED" else "badge-cyan",
        )
        param_str = ", ".join(f"{k}={v}" for k, v in int_params.items()) if int_params else "None"
        tile(i2, "Parameters", param_str, "Matrix/Branches", "badge-cyan")
        tile(i3, "Hypothesis Score", fmt_number(int_score, 3), "Syndrome correlation", "badge-amber")
        tile(i4, "Selected Mode", result.get("_gui", {}).get("deinterleave_mode", "Auto"), "User preference", "badge-cyan")

        st.write("")
        st.markdown(
            "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Interleaver Architecture Visualizer</h3>",
            unsafe_allow_html=True,
        )
        if best_int == "block" or "block" in str(best_int).lower():
            r = int_params.get("rows", 8)
            c = int_params.get("cols", 8)
            st.markdown(f"**Block Interleaver Matrix ($R \\times C = {r} \\times {c}$)**")
            st.caption("Bits are written row-by-row and read column-by-column across the interleaver buffer to disperse burst errors.")
            cells = "".join(
                f"<div style='background:rgba(0,210,255,0.12);border:1px solid #00d2ff;border-radius:3px;padding:4px;text-align:center;font-size:10px;font-family:Space Mono;'>R{row}C{col}</div>"
                for row in range(min(r, 6))
                for col in range(min(c, 8))
            )
            grid_cols = min(c, 8)
            st.markdown(
                f"<div style='display:grid;grid-template-columns:repeat({grid_cols}, 1fr);gap:4px;max-width:550px;margin-bottom:10px;'>{cells}</div>",
                unsafe_allow_html=True,
            )
        elif best_int == "convolutional" or "conv" in str(best_int).lower():
            b = int_params.get("branches", 4)
            m = int_params.get("branch_delay", 2)
            st.markdown(f"**Convolutional Interleaver (Forney/Ramsey $B={b}, M={m}$)**")
            st.caption(f"Structured FIFO shift-registers with branch delays $d_i = i \\times {m}$. Flushing delay is $B(B-1)M = {b * (b - 1) * m}$ bits.")
            branch_html = "".join(
                f"<div style='margin-bottom:6px;font-family:Space Mono;font-size:12px;color:#00ffaa;'>Branch {i}: [{'→ ' * (i * m)}FIFO Delay {i * m}]</div>"
                for i in range(min(b, 6))
            )
            st.markdown(f"<div style='background:rgba(2,10,24,0.7);padding:10px;border-radius:6px;border:1px solid #1a2c42;'>{branch_html}</div>", unsafe_allow_html=True)
        else:
            st.info("No active interleaver pattern detected above threshold. Signal bitstream is treated as non-interleaved or transparent.")
        st.markdown("</div>", unsafe_allow_html=True)

        cands = ev_int.get("hypotheses", [])
        if cands:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Evaluated Interleaving Hypotheses</h3>",
                unsafe_allow_html=True,
            )
            df_cands = []
            for c in cands:
                df_cands.append({
                    "Type": c.get("type", "UNKNOWN"),
                    "Parameters": str(c.get("params", {})),
                    "Syndrome / Score": f"{c.get('score', 0.0):.3f}",
                    "Status": c.get("status", "EVALUATED"),
                })
            st.dataframe(pd.DataFrame(df_cands), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # FEC DECODER
    # ========================================================

    with tab_fec:
        fec_dec = result.get("decoding", {}).get("fec", {})
        ev_fec = result.get("evidence_profile", {}).get("fec_evidence", {})
        fec_status = fec_dec.get("status", result.get("fec_status", "UNKNOWN"))
        best_fec = fec_dec.get("best_hypothesis", ev_fec.get("best", {}).get("code", "none"))
        fec_params = fec_dec.get("parameters", ev_fec.get("best", {}).get("params", {}))
        fec_valid = fec_dec.get("fec_valid", False)

        f1, f2, f3, f4 = st.columns(4)
        tile(
            f1,
            "FEC Codec",
            str(best_fec).upper(),
            f"Status: {fec_status}",
            "badge-green" if fec_valid else "badge-amber",
        )
        param_f_str = ", ".join(f"{k}={v}" for k, v in fec_params.items()) if fec_params else "Standard"
        tile(f2, "Parameters", param_f_str, "Code Specification", "badge-cyan")
        corr_stat = fec_dec.get("corrected_errors", 0)
        tile(f3, "Corrected Errors", str(corr_stat), "Bit/Byte corrections", "badge-cyan")
        tile(
            f4,
            "Verification Verdict",
            "PASSED" if fec_valid else "UNVERIFIED",
            "Syndrome / Trellis metric",
            "badge-green" if fec_valid else "badge-magenta",
        )

        st.write("")
        st.markdown(
            """
            <div class='status-box' style='border-left: 4px solid #ffaa00;'>
                <b style='color:#ffaa00;'>MATHEMATICAL INTEGRITY DISCLOSURE: BLIND LDPC DISCOVERY</b><br>
                <span style='color:#a0aec0;'>
                Arbitrary blind discovery of an unknown Low-Density Parity-Check (LDPC) matrix H ∈ {0, 1}<sup>M×N</sup>
                from unlabelled signal captures is mathematically an <b>NP-hard problem</b>. To uphold defense-grade scientific integrity,
                blind arbitrary LDPC estimation is explicitly designated <b>NOT_IMPLEMENTED</b>.
                <br>
                <b>Deterministic Reference Support:</b> AutoSig-Intel incorporates a verified systematic Gallager (12, 6) LDPC codec
                with hard-decision bit-flipping syndrome decoding for deterministic reference testing.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        cands_fec = ev_fec.get("hypotheses", [])
        if cands_fec:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Evaluated FEC Hypotheses</h3>",
                unsafe_allow_html=True,
            )
            df_fec = []
            for c in cands_fec:
                df_fec.append({
                    "Code Family": c.get("code", "UNKNOWN"),
                    "Parameters": str(c.get("params", {})),
                    "Metric / Syndrome": f"{c.get('metric', c.get('score', 0.0)):.4f}",
                    "Verdict": "VALIDATED" if c.get("valid") else "FAILED",
                })
            st.dataframe(pd.DataFrame(df_fec), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No candidate FEC decoder satisfied the parity/syndrome convergence thresholds on this signal.")

    # ========================================================
    # BITSTREAM & FRAMES
    # ========================================================

    with tab_bitstream:
        dec_corr = result.get("decoding", {}).get("correlation", {})
        preamble_info = dec_corr.get("preamble") or result.get("evidence_profile", {}).get("correlation_evidence", {})
        frame_struct = dec_corr.get("frame_structure") or {}

        b1, b2, b3, b4 = st.columns(4)
        p_name = preamble_info.get("name", "NO_PREAMBLE") if preamble_info else "NO_PREAMBLE"
        p_hex = preamble_info.get("hex", "None") if preamble_info else "None"
        tile(b1, "Detected Preamble", p_name, f"Hex: {p_hex}", "badge-green" if p_name != "NO_PREAMBLE" else "badge-amber")
        p_offset = preamble_info.get("offset", "N/A") if preamble_info else "N/A"
        tile(b2, "Sync Offset", f"Bit {p_offset}", "Frame start alignment", "badge-cyan")
        f_len = frame_struct.get("frame_length", "Variable") if frame_struct else "Variable"
        tile(b3, "Frame Length", f"{f_len} bits", "Periodic spacing", "badge-cyan")
        score_val = preamble_info.get("score", preamble_info.get("match_score", 0.0)) if preamble_info else 0.0
        bit_errs = preamble_info.get("bit_errors", 0) if preamble_info else 0
        tile(b4, "Correlation Score", fmt_number(score_val, 3), f"Bit errors: {bit_errs}", "badge-green" if score_val > 0.8 else "badge-amber")

        st.write("")
        st.markdown(
            "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Recovered Bitstream & Payload Inspection</h3>",
            unsafe_allow_html=True,
        )
        rec_bits = result.get("recovered_bits")
        if rec_bits is None:
            rec_bits = first_value(result, "bitstream", "bits")

        if rec_bits is not None and len(rec_bits) > 0:
            rec_bits_arr = np.asarray(rec_bits, dtype=np.uint8).flatten()
            bit_str = "".join(str(int(b)) for b in rec_bits_arr)
            byte_data = bits_to_bytes(rec_bits_arr)

            view_choice = st.radio(
                "Bitstream View Mode",
                ["Color-Coded Binary", "Hexadecimal Dump", "Printable ASCII Text"],
                horizontal=True,
            )

            if view_choice == "Color-Coded Binary":
                offset = int(preamble_info.get("offset", 0)) if preamble_info and isinstance(preamble_info.get("offset"), (int, float)) else 0
                p_len = int(preamble_info.get("length", 32)) if preamble_info and p_name != "NO_PREAMBLE" else 0

                lead = bit_str[:offset]
                preamble_part = bit_str[offset:offset + p_len]
                payload_part = bit_str[offset + p_len:]

                st.markdown(
                    f"""
                    <div class='bitstream-container'>
                        <span style='color:#8fa0b5;'>{lead}</span>
                        <span class='bit-header' title='Preamble Sync Word'>{preamble_part}</span>
                        <span class='bit-payload'>{payload_part[:10000]}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(f"Showing recovered bitstream: Preamble ({p_len} bits in red), Payload ({len(payload_part)} bits in cyan). Total: {len(bit_str)} bits.")
            elif view_choice == "Hexadecimal Dump":
                hex_dump_str = format_hex_dump(byte_data)
                st.code(hex_dump_str, language="text")
            else:
                ascii_text = "".join(chr(b) if 32 <= b < 127 else "·" for b in byte_data[:4096])
                st.code(ascii_text, language="text")
                st.caption(f"Sanitized ASCII representation of {min(len(byte_data), 4096)} bytes (non-printable characters mapped to '·').")

            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "💾 DOWNLOAD RAW BITS (.TXT)",
                    data=bit_str,
                    file_name=f"{Path(file_name).stem}_recovered_bits.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with d2:
                st.download_button(
                    "💾 DOWNLOAD PAYLOAD BYTES (.BIN)",
                    data=byte_data,
                    file_name=f"{Path(file_name).stem}_payload.bin",
                    mime="application/octet-stream",
                    use_container_width=True,
                )
        else:
            st.info("No recovered bits available from backend.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # 8. HYPOTHESIS & EVIDENCE
    # ========================================================

    with tab_evidence:
        best_hyp = result.get("best_hypothesis") or {}
        why_selected = best_hyp.get("why_selected", best_hyp.get("reason", "No justification recorded."))
        alternatives = best_hyp.get("alternatives_tested", [])

        st.markdown(
            f"""
            <div class='chart-liquid-panel' style='border-left: 4px solid #00ffaa; margin-bottom:14px;'>
                <h3 style='color:#00ffaa; font-size:16px; margin-bottom:6px;'>◈ WHY SELECTED (EVIDENCE JUSTIFICATION)</h3>
                <p style='color:#e2e8f0; font-size:14px; line-height:1.5; font-family: Rajdhani, sans-serif;'>
                    {why_selected}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if alternatives:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>◈ ALTERNATIVES TESTED & REJECTION RATIONALE</h3>",
                unsafe_allow_html=True,
            )
            df_alt = []
            for alt in alternatives:
                df_alt.append({
                    "Candidate": alt.get("candidate", "Unknown"),
                    "Composite Score": f"{alt.get('cross_score', alt.get('score', 0.0)):.3f}",
                    "Modulation Score": f"{alt.get('modulation_score', 0.0):.3f}",
                    "Rejection Rationale": alt.get("rejection_reason", "Lower confidence score"),
                })
            st.dataframe(pd.DataFrame(df_alt), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        ev_profile = result.get("evidence_profile")
        if ev_profile:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:16px;'>Structured Evidence Profile</h3>",
                unsafe_allow_html=True,
            )
            st.caption("Consolidated forensic evidence across modulation, timing, residual synchronization, preamble correlation, interleaving, and FEC:")
            st.json(ev_profile)
            st.markdown("</div>", unsafe_allow_html=True)

        # Jury Demonstration Mode: Ground Truth Comparison
        demo_truth_file = None
        sig_path_str = st.session_state.get("signal_path", "")
        if sig_path_str:
            p = Path(sig_path_str)
            p_stem = p.stem.replace("_f32", "").replace("_i16", "")
            cand1 = Path(__file__).resolve().parents[1] / "samples" / "demo" / f"{p_stem}_truth.json"
            cand2 = Path(__file__).resolve().parents[1] / "samples" / "synthetic" / f"{p_stem}_truth.json"
            if cand1.exists():
                demo_truth_file = cand1
            elif cand2.exists():
                demo_truth_file = cand2

        if demo_truth_file and demo_truth_file.exists():
            st.markdown(
                "<div class='chart-liquid-panel' style='border-left: 4px solid #ffd700; margin-top:14px;'>"
                "<h3 style='color:#ffd700;font-size:16px;'>⚖️ JURY DEMONSTRATION MODE: COMPARE WITH EVALUATOR GROUND TRUTH</h3>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Ground truth was strictly NOT supplied to the receiver. "
                "This comparison evaluates genuine blind inference accuracy:"
            )
            with open(demo_truth_file, "r", encoding="utf-8") as tf:
                truth_data = json.load(tf)

            c_sys, c_truth = st.columns(2)
            with c_sys:
                st.markdown("<h4 style='color:#00e5ff; font-size:15px;'>SYSTEM INFERRED RESULT</h4>", unsafe_allow_html=True)
                st.write(f"**Modulation:** {result.get('modulation')}")
                st.write(f"**SPS:** {result.get('samples_per_symbol')}")
                st.write(f"**Confidence:** {result.get('confidence', 0.0)*100:.1f}% ({result.get('best_hypothesis', {}).get('confidence_tier')})")
                st.write(f"**Preamble:** {result.get('decoding', {}).get('correlation', {}).get('preamble', {}).get('pattern_type', 'None')}")
                st.write(f"**FEC:** {result.get('decoding', {}).get('fec', {}).get('best_hypothesis')}")
                st.write(f"**Interleaver:** {result.get('decoding', {}).get('interleaving', {}).get('best_hypothesis')}")
            with c_truth:
                st.markdown("<h4 style='color:#ffd700; font-size:15px;'>EVALUATOR GROUND TRUTH</h4>", unsafe_allow_html=True)
                st.write(f"**Modulation:** {truth_data.get('modulation')}")
                st.write(f"**SPS:** {truth_data.get('samples_per_symbol')}")
                st.write(f"**Expected Status:** {truth_data.get('expected_status', 'VALIDATED')}")
                p_info = truth_data.get('preamble')
                p_name = p_info.get('name') if isinstance(p_info, dict) else p_info
                st.write(f"**Preamble:** {p_name}")
                st.write(f"**FEC:** {truth_data.get('fec')}")
                st.write(f"**Interleaver:** {truth_data.get('interleaver')}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # 9. EXPORTS & ARTIFACTS
    # ========================================================

    with tab_exports:

        st.markdown(
            "<div class='chart-liquid-panel'><h3 style='color:white;font-size:17px;'>Export Analysis</h3>",
            unsafe_allow_html=True,
        )

        live_peak = peak_freq

        csv_row = result_to_csv_row(
            result,
            signal_meta,
            file_name,
            live_peak,
        )

        csv_bytes = pd.DataFrame([csv_row]).to_csv(index=False).encode("utf-8")

        # Convert backend result to safe JSON.
        def json_safe(obj):
            if isinstance(obj, dict):
                return {str(k): json_safe(v) for k, v in obj.items() if not str(k).startswith("_internal")}
            if isinstance(obj, (list, tuple)):
                return [json_safe(v) for v in obj]
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, complex):
                return {"real": obj.real, "imag": obj.imag}
            try:
                json.dumps(obj)
                return obj
            except TypeError:
                return str(obj)

        report = {
            "file": file_name,
            "signal_metadata": {
                k: json_safe(v)
                for k, v in signal_meta.items()
                if k != "x"
            },
            "backend_result": json_safe(result),
            "live_peak_frequency_hz": live_peak,
        }

        json_bytes = json.dumps(
            report,
            indent=2,
            default=json_safe,
        ).encode("utf-8")

        e1, e2 = st.columns(2)

        with e1:
            st.download_button(
                "📄 EXPORT REPORT (.JSON)",
                data=json_bytes,
                file_name=Path(file_name).stem + "_analysis.json",
                mime="application/json",
                use_container_width=True,
            )

        with e2:
            st.download_button(
                "📊 EXPORT SUMMARY (.CSV)",
                data=csv_bytes,
                file_name=Path(file_name).stem + "_summary.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        exec_times = result.get("execution_times")
        if exec_times:
            st.markdown(
                "<div class='chart-liquid-panel'><h3 style='color:white;font-size:17px;'>Execution Performance & Latency</h3>",
                unsafe_allow_html=True,
            )
            st.caption("Measured backend wall-clock latencies across each stage of the receiver pipeline:")
            p1, p2, p3 = st.columns(3)
            with p1:
                st.metric("Ingestion Time", f"{exec_times.get('ingestion_time_seconds', 0.0):.4f} s")
                st.metric("Demodulation Time", f"{exec_times.get('demodulation_time_seconds', 0.0):.4f} s")
            with p2:
                st.metric("Characterization Time", f"{exec_times.get('characterization_time_seconds', 0.0):.4f} s")
                st.metric("FEC / Frame Decoding", f"{exec_times.get('decoding_time_seconds', 0.0):.4f} s")
            with p3:
                st.metric("Modulation Inference", f"{exec_times.get('modulation_inference_time_seconds', 0.0):.4f} s")
                st.metric("Total Processing Time", f"{exec_times.get('total_time_seconds', 0.0):.4f} s")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<div class='chart-liquid-panel'><h3 style='color:white;font-size:17px;'>Terminal Logs</h3>",
            unsafe_allow_html=True,
        )

        logs = st.session_state.analysis_logs or ["No logs available."]

        log_html = "<br>".join(
            f"<span class='console-text'>&gt; {line}</span>"
            for line in logs
        )

        st.markdown(
            f"""
            <div style='background:rgba(2,8,18,0.92);
                        padding:15px;
                        border-radius:10px;
                        border:1px solid rgba(0,210,255,0.20);
                        max-height:320px;
                        overflow-y:auto;'>
                {log_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div style='height:18px'></div>",
    unsafe_allow_html=True,
)
