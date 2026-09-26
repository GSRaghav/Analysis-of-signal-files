# AutoSig-Intel — Automated RF Signal Analysis & Parameter Extraction

**SIH 2026 Problem Statement:** SIH26147  
**Organization:** National Technical Research Organisation (NTRO)  
**Category:** Software | **Theme:** Miscellaneous  
**Current Status:** Phase 5 Complete (Blind End-to-End Decoding, Cross-Stage Hypothesis Validation & 9-Tab Command Center Verified)  

---

## 1. Executive Summary

**AutoSig-Intel** is an evidence-driven software system designed to ingest `.wav` and raw `.iq` signal captures, perform automated channel and format analysis, extract physical signal parameters (sampling rate, center frequency, occupied bandwidth, noise floor, SNR), and progressively synchronize, demodulate, and recover bitstreams through an integrated multi-hypothesis de-interleaving, FEC decoding, and frame correlation pipeline.

### Core Engineering Philosophy:
> **Automate → Infer → Validate**
>
> The system operates under strict evidence-driven criteria. It **never** produces confident false answers. When a signal is an analog audio transmission, pure tone, or unstructured noise, the system returns `UNKNOWN` with confidence `0.00%` and transparent rationale, rather than forcing an unsupported digital modulation or fabricated FEC/payload decoding.

---

## 2. End-to-End Pipeline Architecture

```text
INPUT (.IQ / .WAV)
    ↓
File / Channel / Format Analysis  (Duplicate stereo vs. independent IQ channel heuristic)
    ↓
Common Signal Representation       (Unified SignalData dataclass)
    ↓
Preprocessing                      (DC removal, energy normalization, analytic representation)
    ↓
Signal Characterization            (RMS, peak, dominant frequency, 99% occupied bandwidth, noise floor, SNR)
    ↓
Digital Signal Screening Gate      (Narrowband tone rejection, silence/noise screening)
    ↓
Symbol Timing Recovery             (Transition-interval clustering & SPS candidate ranking)
    ↓
Carrier & Phase Synchronization    (M-th power CFO recovery, Viterbi phase estimation, symbol alignment)
    ↓
Demodulation                       (Hard-decision bit recovery for BPSK, QPSK, 16-QAM, 2-FSK)
    ↓
Recovered Bitstream                (Unpacked binary bitstream output)
    ↓
De-interleaving                    (Block, Convolutional Ramsey/Forney, Diagonal, Pseudo-Random)
    ↓
Forward Error Correction (FEC)     (Hard-decision Viterbi K=7 & K=3, Reed-Solomon GF(256), Concatenated, Gallager LDPC)
    ↓
Bitstream Correlation              (CCSDS 32-bit ASM, Barker-11/13, 16-bit Sync, HDLC flag, header & payload boundary extraction)
    ↓
Cross-Stage Hypothesis Ranking     (Multi-stage composite scoring, confidence tiers, why selected, alternatives tested)
    ↓
Export & Visualization             (Structured JSON report, summary CSV, 9-tab Streamlit Command Center)
```

---

## 3. Implementation Status vs. Requirements (21 Capabilities)

| Pipeline Stage | Target Requirement | Status | Verification & Evidence |
| :--- | :--- | :--- | :--- |
| **Ingestion** | `.wav` (mono/stereo) & raw `.iq` | **VALIDATED** | [`core/signal_loader.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_loader.py) handles mono, stereo duplicate, and possible IQ detection; reads raw interleaved IQ (`int16`, `float32`, little/big endian). |
| **Common Representation** | Unified object | **VALIDATED** | [`SignalData`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_data.py) dataclass in `core/signal_data.py`. |
| **Signal Characterization** | $F_s$, bandwidth, SNR, noise floor | **VALIDATED** | [`core/signal_analysis.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_analysis.py) Welch PSD, 99% occupied bandwidth, trapezoidal SNR proxy. |
| **Visualizations** | 5 primary diagnostics | **VALIDATED** | Waveform, Power Spectrum, STFT Spectrogram, Complex-plane, Instantaneous frequency in [`core/visualization.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/visualization.py) & live Plotly in [`app/gui.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/app/gui.py). |
| **Tone & Noise Gating** | Reject non-digital candidates | **VALIDATED** | [`core/hypothesis.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/hypothesis.py) single-tone score correctly flags tones/noise as non-digital with 0.0% confidence. |
| **Timing Recovery** | Blind SPS candidate ranking | **VALIDATED** | [`core/timing.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/timing.py) passes 100% across BPSK, QPSK, 16-QAM, 2-FSK synthetic tests. |
| **Carrier Synchronization** | CFO, phase & timing offset | **VALIDATED** | [`core/synchronization.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/synchronization.py) $M$-th power frequency estimator & Viterbi phase recovery reach **BER = 0.0** under impairment. |
| **Demodulation** | BPSK, QPSK, 16-QAM, 2-FSK | **VALIDATED** | [`core/demodulation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/demodulation.py) hard-decision symbol-to-bit mapping reaches **BER = 0.0**. |
| **Evidence-based AMC** | Prevent false 16-QAM | **VALIDATED** | Multi-cluster compactness, 16-state occupancy entropy, and 4th moment ($E[\|s\|^4] \approx 1.32$) test eliminate false positives on real audio. |
| **De-interleaving** | Block, Conv, Diagonal, PR | **VALIDATED** | [`core/interleaving.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/interleaving.py) implements Block ($R \times C$), Convolutional (Ramsey/Forney shift registers), Diagonal, and Pseudo-Random de-interleavers with remnant preservation and multi-hypothesis evaluation. |
| **Forward Error Correction** | Viterbi, RS, Concatenated, LDPC | **VALIDATED** | [`core/fec.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/fec.py) vectorized Viterbi ($K=7$ NASA $(171, 133)_8$ and $K=3$), Reed-Solomon over $\text{GF}(256)$, Concatenated RS+Viterbi, and systematic Gallager $(12, 6)$ LDPC codec. Arbitrary blind LDPC discovery explicitly disclosed as `NOT_IMPLEMENTED`. |
| **Bit Correlation & Framing** | Preamble, header & payload boundaries | **VALIDATED** | [`core/correlation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/correlation.py) and [`core/frame.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/frame.py) prioritize length `(score, pattern_length, -bit_errors)`, parse headers, and extract payloads. |
| **Cross-Stage Hypotheses** | Multi-stage composite scoring | **VALIDATED** | [`core/receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/receiver.py) computes composite cross-stage score, classifies into confidence tiers (HIGH/MEDIUM/INSUFFICIENT), and provides `why_selected` and `alternatives_tested` matrices. |
| **GUI Command Center** | Real-time interactive dashboard | **VALIDATED** | [`app/gui.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/app/gui.py) Streamlit command center featuring 9 specialized tabs with a visual decoding path flow diagram. |

---

## 4. Phase 5 Blind Evaluation Scorecard

Evaluated autonomously on unknown captures in `samples/synthetic/`:

| Signal File | True Modulation | Inferred Modulation | True SPS | Inferred SPS | Preamble Sync | FEC Validation | Confidence Tier | Confidence Score |
|---|---|---|---|---|---|---|---|---|
| `capture_a_bpsk.wav` | BPSK | **BPSK** | 8 | **8** | CCSDS_ASM (32b) | Viterbi K=7 | **HIGH CONFIDENCE** | 0.98 |
| `capture_b_qpsk.wav` | QPSK | **QPSK** | 8 | **8** | CCSDS_ASM (32b) | Reed-Solomon | **HIGH CONFIDENCE** | 0.97 |
| `capture_c_qpsk.wav` | QPSK | **QPSK** | 8 | **8** | CCSDS_ASM (32b) | Viterbi K=3 | **HIGH CONFIDENCE** | 0.98 |
| `capture_d_16qam.wav` | 16-QAM | **16-QAM** | 8 | **8** | SYNC_AA55 (16b) | Concatenated RS | **HIGH CONFIDENCE** | 0.97 |
| `capture_e_2fsk.wav` | 2-FSK | **2-FSK** | 16 | **16** | SYNC_AA55 (16b) | Viterbi K=7 | **HIGH CONFIDENCE** | 0.98 |
| `negative_pure_sine.wav` | Sine Tone | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |
| `negative_two_tone.wav` | Two-Tone | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |
| `negative_gaussian_noise.wav` | Noise | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |

---

## 5. Complete Automated Test Suite (127 Tests Passing)

```bash
pytest -q
```
**Result: 127 passed in 100% clean execution (0 errors, 0 failures across all suites)**

| Test Module | Tests | Status | Scope |
|---|---|---|---|
| `tests/test_reference_signals.py` | 4 | `PASS` | Pure synthetic BPSK, QPSK, 16-QAM, 2-FSK generation & baseline demod |
| `tests/test_timing.py` | 4 | `PASS` | Symbol rate & SPS estimation accuracy |
| `tests/test_synchronization.py` | 4 | `PASS` | Full CFO, phase, and timing lock on impaired signals |
| `tests/test_receiver.py` | 10 | `PASS` | End-to-end evaluation of all 10 real audio WAV recordings in `samples/wav/` |
| `tests/test_raw_iq.py` | 7 | `PASS` | Raw binary IQ loading, int16/complex64, IQ/QI order, odd-length & malformed handling |
| `tests/test_robustness.py` | 70 | `PASS` | Full multi-condition SNR/CFO/Phase/Timing sweeps, 12-signal confusion matrix, 4th-moment, FSK physics |
| `tests/test_interleaving.py` | 5 | `PASS` | Block, Convolutional, Diagonal, Pseudo-Random roundtrips, Remnant handling, Multi-hypothesis ranking |
| `tests/test_fec.py` | 6 | `PASS` | Hard-decision Viterbi K=7 NASA & K=3, Reed-Solomon GF(256), Concatenated RS+Viterbi, Gallager (12, 6) LDPC, Blind LDPC disclosure |
| `tests/test_correlation.py` | 5 | `PASS` | Preamble detection (CCSDS 32, Barker, Sync16, HDLC), Header candidate extraction, Payload boundary estimation |
| `tests/test_decoding_pipeline.py` | 2 | `PASS` | End-to-end Preamble + Block Interleaver + Viterbi FEC decoding pipeline roundtrip & noise robustness |
| `tests/test_blind_pipeline.py` | 10 | `PASS` | Blind end-to-end decoding scorecard, negative gate rejection, truncated/damaged signal handling |
| **Total Test Suite** | **127** | **100% PASS** | **Complete end-to-end pipeline verification (DSP + Receiver + Decoding + Blind Scorecard)** |

---

## 6. Execution Instructions

### A. Environment Setup
```bash
pip install -r requirements.txt
```

### B. Run Complete Automated Test Suite
```bash
pytest -q
```

### C. Generate Blind Dataset with Golden Transmitter
```bash
python scripts/generate_blind_dataset.py
```

### D. Run Batch CLI Analysis
```bash
python main.py
```
Outputs:
- CSV Summary: `results/signal_summary.csv`
- Diagnostics Plots: `results/plots/<file>_{waveform,spectrum,spectrogram,constellation,instantaneous_frequency}.png`

### E. Launch Interactive GUI Command Center (9 Tabs)
```bash
streamlit run app/gui.py
```
Access the dashboard in your web browser at `http://localhost:8501`.
- **Decoding Path Flow Diagram:** Visual workflow tracker across all 8 pipeline phases.
- **Tab 1: Ingestion & Audio:** Audio playback, file metadata, channel mode (mono/stereo/IQ).
- **Tab 2: Characterization:** 99% Occupied BW, SNR, RMS power, interactive Plotly PSD & Spectrogram.
- **Tab 3: Modulation & Sync:** Constellation scatter, CFO/phase tracking, cyclostationary SPS estimation.
- **Tab 4: Demodulation:** Hard-decision bit recovery, bit distribution, live ground-truth BER calculator.
- **Tab 5: De-interleaving:** Interactive matrix architecture visualizer ($R \times C$ block grid) and candidate rankings.
- **Tab 6: FEC Decoder:** Trellis path metrics, RS syndrome check, LDPC boundary disclosure.
- **Tab 7: Bitstream & Frames:** Preamble detection, hex dump, printable ASCII, raw bitstream download.
- **Tab 8: Hypothesis & Evidence:** "Why Selected" card, "Alternatives Tested" rejection matrix, evidence tree.
- **Tab 9: Exports & Artifacts:** Download structured JSON forensic report, CSV summary, diagnostic plots.

---

## 7. Additional Documentation
- [Phase 5 Detailed Report](file:///c:/Users/gssr2/Desktop/autosig_intel/docs/PHASE5_REPORT.md)
- [System Architecture](file:///c:/Users/gssr2/Desktop/autosig_intel/docs/ARCHITECTURE.md)
- [Mathematical Algorithms & Theory](file:///c:/Users/gssr2/Desktop/autosig_intel/docs/ALGORITHMS.md)
- [SIH 2026 Technical Status & Compliance Audit](file:///c:/Users/gssr2/Desktop/autosig_intel/docs/SIH_STATUS.md)

