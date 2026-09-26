from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class SignalData:
    """
    Standard internal representation of an input signal.

    samples:
        1-D NumPy array.
        Real-valued for ordinary/mono WAV.
        Complex-valued for possible I/Q WAV.

    representation:
        "real"
        "complex_iq"
    """

    samples: np.ndarray

    sample_rate: float
    source_type: str

    representation: str = "real"

    filename: str = ""

    original_channels: int = 1

    channel_correlation: Optional[float] = None

    possible_iq: bool = False

    metadata: dict = field(default_factory=dict)

    # Basic signal information
    duration: Optional[float] = None
    rms: Optional[float] = None
    peak: Optional[float] = None
    dc_offset: Optional[float] = None

    # Spectral information
    peak_frequency: Optional[float] = None
    occupied_lower_frequency: Optional[float] = None
    occupied_upper_frequency: Optional[float] = None
    occupied_center_frequency: Optional[float] = None
    bandwidth: Optional[float] = None

    noise_floor_db: Optional[float] = None
    snr_db: Optional[float] = None

    # Modulation information
    modulation: Optional[str] = None
    modulation_confidence: Optional[float] = None
    symbol_rate: Optional[float] = None

    # Coding information
    interleaving: Optional[str] = None
    fec: Optional[str] = None

    notes: list = field(default_factory=list)

    @property
    def num_samples(self) -> int:
        return len(self.samples)

    @property
    def nyquist(self) -> float:
        return self.sample_rate / 2.0