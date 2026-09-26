# AutoSig-Intel: System Architecture & Design Documentation

**Problem Statement ID:** SIH26147  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme / Category:** Miscellaneous / Software  
**Version:** Phase 5 Baseline  

---

## 1. Architectural Overview

AutoSig-Intel is an automated, physics-grounded signal intelligence (SIGINT) and digital receiver processing engine designed to ingest raw radio frequency recordings (`.IQ` and `.wav` formats), characterize signal parameters, infer digital modulation and symbol rates, lock carrier and timing offsets, demodulate raw symbols, de-interleave, decode forward error correction (FEC), and correlate frame preambles to extract recovered payloads.

```
                          ┌─────────────────────────────┐
                          │   INPUT (.IQ / .WAV FILE)   │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  Format & Channel Ingestion │
                          │ (8/16/24/32-bit PCM, raw IQ)│
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  Signal Normalization &     │
                          │  Spectral Characterization  │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │ Non-Digital Screening Gate  │
                          │ (Tone / Noise / Audio Gate) │
                          └──────┬───────────────┬──────┘
                  Passed Digital │               │ Rejected Non-Digital
                                 ▼               ▼
        ┌────────────────────────────────┐   ┌───────────────────────────┐
        │  Cyclostationary SPS Recovery  │   │ Return Status: REJECTED   │
        │   (Transition interval timing) │   │ Conf: 0.0%, Mod: UNKNOWN  │
        └────────────────┬───────────────┘   └───────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │                 MULTI-STAGE HYPOTHESIS TESTING                 │
        │  Iterate over candidate (Modulation, SPS) pairs:               │
        │  • CFO / Phase Synchronization (M-th power / Viterbi)          │
        │  • Demodulation (BPSK, QPSK, 16-QAM, 2-FSK)                   │
        │  • Preamble Correlation (CCSDS 32b, Sync16, Barker, HDLC)      │
        │  • De-interleaving (Block, Conv, Diagonal, Pseudo-Random)      │
        │  • FEC Syndrome Validation (Viterbi K=7/3, RS(255,k), LDPC)    │
        └────────────────┬───────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │             CROSS-STAGE HYPOTHESIS RANKING ENGINE              │
        │  Calculate Composite Score:                                    │
        │  Score = 0.35·S_mod + 0.15·S_time + 0.15·S_cfo +               │
        │          0.20·S_preamble + 0.15·S_fec                          │
        │  Determine Confidence Tier: HIGH / MEDIUM / INSUFFICIENT       │
        │  Generate Explainability: Why Selected & Alternatives Tested   │
        └────────────────┬───────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │               OUTPUT & DEMONSTRATION LAYER                     │
        │  • Structured JSON Forensic Report & CSV Summary               │
        │  • 9-Tab Streamlit Interactive GUI Command Center              │
        └────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules & Responsibilities

| Module | Location | Primary Responsibilities |
|---|---|---|
| **Signal Loader** | [`core/signal_loader.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_loader.py) | Ingests WAV files (mono, stereo, IQ detection), headerless raw binary IQ (`int16`, `float32`, `complex64`), and little/big-endian handling with odd-byte truncation guards. |
| **Data Model** | [`core/signal_data.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_data.py) | Unified immutable `SignalData` dataclass encapsulating complex sample vectors, sample rate, source metadata, and channel configuration. |
| **Signal Analysis** | [`core/signal_analysis.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_analysis.py) | Welch PSD estimation, 99% occupied bandwidth integration, peak SNR estimation, and Matplotlib diagnostic plotting. |
| **Screening & Gating** | [`core/hypothesis.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/hypothesis.py) | Non-digital carrier tone gating, spectral kurtosis screening, 4th-moment envelope statistics, and envelope CV. |
| **Timing Recovery** | [`core/timing.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/timing.py) | Blind symbol rate and SPS estimation via cyclostationary instantaneous frequency/derivative transition interval clustering. |
| **Carrier Synchronization** | [`core/synchronization.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/synchronization.py) | $M$-th power spectral CFO estimation ($\pm 3\text{ kHz}$ range), Viterbi-Viterbi phase estimation, and matched symbol downsampling. |
| **Demodulation** | [`core/demodulation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/demodulation.py) | Hard-decision slicing and symbol-to-bit mapping for BPSK, QPSK, 16-QAM, and 2-FSK with bit error rate (BER) verification against ground truth. |
| **De-interleaving** | [`core/interleaving.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/interleaving.py) | Bijective Block ($R \times C$), Convolutional (Ramsey/Forney shift registers), Diagonal, and Pseudo-Random de-interleavers with trailing remnant preservation. |
| **Forward Error Correction** | [`core/fec.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/fec.py) | Vectorized Viterbi trellis decoding for $K=7$ NASA $(171, 133)_8$ and $K=3$, systematic Reed-Solomon over $\text{GF}(256)$ with multi-parameter search, concatenated RS+Viterbi, and Gallager LDPC reference decoder. |
| **Correlation & Framing** | [`core/correlation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/correlation.py), [`core/frame.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/frame.py) | Preamble correlation with length prioritization `(score, pattern_length, -bit_errors)`, frame header parsing, and multi-hypothesis decoding pipeline runner. |
| **Receiver Orchestrator** | [`core/receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/receiver.py) | End-to-end coordinator: extracts representative start segments, executes cross-stage hypothesis evaluation, ranks candidate pipelines, and constructs the explainability profile. |
| **Transmitter Generator** | [`core/test_signal_generator.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/test_signal_generator.py) | Generates synthetic transmissions with ground-truth bitstreams, configurable modulation, pulse shaping (RRC/rect), FEC, interleaving, preambles, and channel impairments (CFO, phase, AWGN). |
| **GUI Command Center** | [`app/gui.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/app/gui.py) | 9-tab Streamlit dashboard with interactive Plotly visualizer, decoding flow diagram, live BER calculator, and hypothesis explainability views. |

---

## 3. Cross-Stage Hypothesis Ranking & Explainability Engine

Traditional AMC architectures evaluate modulation and SPS purely at the constellation level. In real-world multi-rate or dispersive channels, harmonic symbol rates (e.g. $\text{SPS}=4$ vs $\text{SPS}=8$ vs $\text{SPS}=16$) or constellation symmetries can yield ambiguous clustering scores.

AutoSig-Intel solves this through **Cross-Stage Composite Scoring**:

### 3.1 Composite Score Formulation
$$\text{Score}_{\text{composite}} = 0.35 \cdot S_{\text{mod}} + 0.15 \cdot S_{\text{timing}} + 0.15 \cdot S_{\text{carrier}} + 0.20 \cdot S_{\text{preamble}} + 0.15 \cdot S_{\text{fec}}$$

Where:
- $S_{\text{mod}}$: Constellation cluster compactness / envelope score ($0.0$ to $1.0$).
- $S_{\text{timing}}$: Peak-to-average transition energy ratio for candidate SPS.
- $S_{\text{carrier}}$: Quality of CFO spectral tone and phase lock stability.
- $S_{\text{preamble}}$: Best preamble correlation match score ($1.0$ for exact match, normalized by bit errors).
- $S_{\text{fec}}$: FEC validity indicator ($1.0$ if syndrome valid or Viterbi metric $\le 0.08$, otherwise $0.0$).

### 3.2 Confidence Tiers
- **HIGH CONFIDENCE ($\ge 0.85$):** Conclusive multi-stage alignment across modulation, timing, carrier lock, preamble correlation, and FEC syndrome.
- **MEDIUM CONFIDENCE ($0.50 - 0.84$):** Clear modulation and timing, but partial preamble or unencoded/noisy payload.
- **INSUFFICIENT EVIDENCE ($< 0.50$):** Unlocked, poor cluster compactness, or non-digital signal. Confidence is strictly clamped to **0.0%**.

### 3.3 Explainability Architecture (`why_selected` and `alternatives_tested`)
Every analysis report provides two critical forensic explainability sections:
1. **`why_selected` (Positive Validation):** Concrete explanation of why the winning hypothesis was chosen (e.g. "Optimal cross-stage composite score 0.98; verified CCSDS_ASM preamble at offset 0; valid Viterbi K=7 FEC with metric 0.02").
2. **`alternatives_tested` (Negative Rejection Matrix):** Detailed record of every competing candidate tested, including:
   - Evaluated candidate $(Modulation, SPS)$
   - Cross-stage score
   - Preamble detected (or None)
   - FEC validity
   - Explicit rejection reason (e.g. "Sub-harmonic baud rate; failed preamble correlation", "Invalid constellation envelope for 16-QAM", "Excessive Viterbi trellis path metric > 0.08").

---

## 4. Algorithmic Optimizations & Acceleration

### 4.1 Vectorized Viterbi Trellis Caching
In $K=7$ NASA convolutional decoding, processing 1,500 trellis stages with 64 states per stage typically requires $1,500 \times 64 = 96,000$ state transitions. Python loops over states introduce significant overhead.
- **Optimization:** AutoSig-Intel precomputes the trellis butterfly structure in `_VITERBI_TRELLIS_CACHE`, storing vectorized predecessor state indices `p0, p1` and output parity symbols `out0, out1`.
- **Performance:** State metric updates and survivor path tracking are vectorized with NumPy array operations, reducing decode latency from $\sim 800\text{ ms}$ down to $\sim 20\text{ ms}$ per hypothesis (**40x acceleration**).

### 4.2 Multi-Parameter Reed-Solomon Search
Standard blind receivers often fail when payload Reed-Solomon parameters $(n, k)$ are unknown. AutoSig-Intel tests viable Reed-Solomon parameter combinations ($nsym \in [4, 8, 10, 16, 32]$) over systematic blocks. Explicit codeword length guards ($cw > nsym$ and $\text{len}(dec) > 0$) prevent empty zero-error false alarms.

### 4.3 Preamble Correlation Length Prioritization
In random bitstreams, short 8-bit patterns (such as HDLC flags `0x7E`) match by chance with probability $2^{-8} = 1/256$. AutoSig-Intel ranks candidate preambles by the tuple:
$$\text{Rank} = \left(\text{Score}, \text{Pattern Length}, -\text{Bit Errors}\right)$$
This guarantees that genuine 32-bit (CCSDS_ASM) or 16-bit (SYNC_AA55) synchronizations take precedence over incidental short false alarms.

---

## 5. Streamlit GUI Dashboard Architecture (9 Specialized Tabs)

The AutoSig-Intel GUI dashboard (`app/gui.py`) implements a complete SIGINT workstation:

```
[DECODING PATH FLOW: INPUT -> SCREEN -> TIMING -> MODULATION -> DEMOD -> DEINTERLEAVE -> FEC -> PAYLOAD]
---------------------------------------------------------------------------------------------------------
Tab 1: INPUT & INGESTION        - Audio playback, file metadata, channel mode (mono/stereo/IQ)
Tab 2: SIGNAL CHARACTERIZATION  - Occupied BW, SNR, RMS, interactive Plotly PSD & Spectrogram
Tab 3: MODULATION & SYNC        - Constellation scatter, CFO/phase tracking, cyclostationary SPS
Tab 4: DEMODULATION             - Hard-decision bit recovery, bit distribution, live BER verification
Tab 5: DE-INTERLEAVING          - Matrix architecture visualizer (R x C grid), delay compensation
Tab 6: FEC DECODER              - Trellis path metrics, RS syndrome check, LDPC boundary disclosure
Tab 7: BITSTREAM & FRAMES       - Preamble sync, hex dump, printable ASCII, raw bitstream download
Tab 8: HYPOTHESIS & EVIDENCE    - Why Selected card, Alternatives Tested rejection table, evidence tree
Tab 9: EXPORTS & ARTIFACTS      - Download structured JSON report, CSV summary, diagnostic plots
```
