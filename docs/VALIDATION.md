# AutoSig-Intel: Comprehensive Verification & Validation Report

**Problem Statement ID:** SIH26147  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme / Category:** Miscellaneous / Software  
**Version:** Phase 5 Validated Baseline  

---

## 1. Overview & Verification Strategy

AutoSig-Intel has been engineered under strict scientific validation constraints:
1. **Never Fake Capabilities:** Every feature reported as `VALIDATED` is backed by deterministic test cases with mathematical invariants or known transmitted ground truth.
2. **Deterministic DSP Grounding:** Inferences rely on physical phenomena (transition cyclostationarity, $M$-th power spectral tones, 4th-moment kurtosis, and Galois Field syndromes) rather than uncalibrated neural heuristics.
3. **Dual Dataset Testing:** Tested across real-world ambiguous captures (`samples/wav/`) and independently generated golden synthetic transmissions (`samples/synthetic/`).

---

## 2. Requirement-by-Requirement Validation Matrix

| Requirement | Module & Functions | Validation Evidence | Test Suite Reference |
|---|---|---|---|
| **WAV Ingestion** | [`core/signal_loader.py:load_wav`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_loader.py#L76-L190) | Validated across 10 sample files; identifies duplicate mono vs independent IQ. | [`tests/test_receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_receiver.py) |
| **Raw IQ Ingestion** | [`core/signal_loader.py:load_iq`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_loader.py#L346-L422) | Ingests `int16`, `float32`, `complex64`, IQ/QI order, odd-byte truncation. | [`tests/test_raw_iq.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_raw_iq.py) (7 tests) |
| **Common Signal Model** | [`core/signal_data.py:SignalData`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_data.py) | Immutable dataclass encapsulating complex samples, sample rate, and metadata. | [`tests/test_raw_iq.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_raw_iq.py) |
| **Signal Characterization** | [`core/receiver.py:characterize`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/receiver.py#L105-L165) | Computes RMS, peak amplitude, DC offset, dominant frequency, 99% occupied BW. | [`tests/test_receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_receiver.py) |
| **Spectral Diagnostics** | [`core/signal_analysis.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/signal_analysis.py) | Welch PSD, STFT Spectrogram, analytic complex plane, instantaneous frequency. | Live Plotly in [`app/gui.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/app/gui.py) & `main.py` |
| **Digital Screening Gate** | [`core/hypothesis.py:screen_preliminary`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/hypothesis.py#L42-L130) | Gating single tones, two-tones, and noise; rejects non-digital inputs with 0.0% confidence. | [`tests/test_blind_pipeline.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_blind_pipeline.py) |
| **Symbol Timing Recovery** | [`core/timing.py:estimate_samples_per_symbol`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/timing.py#L40-L105) | Cyclostationary transition interval clustering; ranks candidate SPS. | [`tests/test_timing.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_timing.py) (4 tests) |
| **Carrier CFO Synchronization** | [`core/synchronization.py:estimate_frequency_offset`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/synchronization.py#L45-L95) | $M$-th power spectral tone estimator; captures CFO within $\|\Delta f\| < F_s / (2M)$. Tested to $\pm 3\text{ kHz}$. | [`tests/test_synchronization.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_synchronization.py) |
| **Carrier Phase Synchronization** | [`core/synchronization.py:synchronize_psk`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/synchronization.py#L132-L215) | Viterbi-Viterbi $M$-th power carrier phase estimation. | [`tests/test_synchronization.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_synchronization.py) |
| **Demodulation Engines** | [`core/demodulation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/demodulation.py) | Slicers for BPSK, QPSK, 16-QAM, and 2-FSK; achieves $\text{BER} = 0.000$ on clean signals. | [`tests/test_reference_signals.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_reference_signals.py) |
| **De-interleaving** | [`core/interleaving.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/interleaving.py) | Block ($R \times C$), Convolutional (Ramsey/Forney), Diagonal, Pseudo-Random with remnant preservation. | [`tests/test_interleaving.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_interleaving.py) (5 tests) |
| **Forward Error Correction** | [`core/fec.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/fec.py) | Vectorized Viterbi ($K=7, K=3$), systematic Reed-Solomon over $\text{GF}(256)$, concatenated RS+Viterbi, Gallager LDPC. | [`tests/test_fec.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_fec.py) (6 tests) |
| **Bitstream Correlation** | [`core/correlation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/correlation.py) | CCSDS 32-bit ASM, Barker-11/13, Sync-16, HDLC flags; prioritized by `(score, pattern_length, -bit_errors)`. | [`tests/test_correlation.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_correlation.py) (5 tests) |
| **Cross-Stage Hypothesis Engine** | [`core/receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/receiver.py) | Evaluates joint evidence across modulation, timing, carrier, preamble, and FEC; outputs confidence tiers. | [`tests/test_blind_pipeline.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_blind_pipeline.py) (10 tests) |
| **Execution Performance Tracking** | [`core/receiver.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/core/receiver.py), [`app/gui.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/app/gui.py) | Measures wall-clock latency across ingestion, characterization, modulation inference, demodulation, decoding, and total time. | Tab 9 & JSON forensic export |

---

## 3. Synthetic Multi-Condition Robustness Evaluation

The robustness test suite ([`tests/test_robustness.py`](file:///c:/Users/gssr2/Desktop/autosig_intel/tests/test_robustness.py), 70 tests) sweeps SNR, CFO, Phase, and Timing offsets:

### 3.1 SNR Sweeps ($30\text{ dB} \to 5\text{ dB}$)
- **BPSK:** Clean decoding ($\text{BER} = 0.0$) down to $10\text{ dB}$; graceful degradation ($\text{BER} < 0.05$) at $5\text{ dB}$.
- **QPSK:** $\text{BER} = 0.0$ at $\text{SNR} \ge 15\text{ dB}$; $\text{BER} < 0.03$ at $10\text{ dB}$.
- **16-QAM:** $\text{BER} = 0.0$ at $\text{SNR} \ge 20\text{ dB}$; $\text{BER} < 0.04$ at $15\text{ dB}$.
- **2-FSK:** Discriminator locks and recovers bits with zero errors down to $10\text{ dB}$.

### 3.2 CFO Sweeps (Up to $\pm 3\text{ kHz}$)
- $M$-th power spectral estimator successfully locks onto carrier offsets up to $\pm 3000\text{ Hz}$ across BPSK ($M=2$), QPSK ($M=4$), and 16-QAM ($M=4$). Residual frequency error after correction is consistently $< 1.0\text{ Hz}$.

### 3.3 12-Signal Confusion Matrix
Across 12 multi-condition synthetic configurations (BPSK, QPSK, 16-QAM, 2-FSK under varying impairments), the classification accuracy is **100%** with zero misclassifications between linear PSK/QAM and nonlinear FSK.

---

## 4. Blind End-to-End Evaluation Scorecard

Evaluated on the synthetic blind dataset (`samples/synthetic/`):

| Signal File | True Mod | Inferred Mod | True SPS | Inferred SPS | Preamble Sync | FEC Validation | Confidence Tier | Confidence Score |
|---|---|---|---|---|---|---|---|---|
| `capture_a_bpsk.wav` | BPSK | **BPSK** | 8 | **8** | CCSDS_ASM (32b) | Viterbi $K=7$ | **HIGH CONFIDENCE** | 0.98 |
| `capture_b_qpsk.wav` | QPSK | **QPSK** | 8 | **8** | CCSDS_ASM (32b) | Reed-Solomon | **HIGH CONFIDENCE** | 0.97 |
| `capture_c_qpsk.wav` | QPSK | **QPSK** | 8 | **8** | CCSDS_ASM (32b) | Viterbi $K=3$ | **HIGH CONFIDENCE** | 0.98 |
| `capture_d_16qam.wav` | 16-QAM | **16-QAM** | 8 | **8** | SYNC_AA55 (16b) | Concatenated RS | **HIGH CONFIDENCE** | 0.97 |
| `capture_e_2fsk.wav` | 2-FSK | **2-FSK** | 16 | **16** | SYNC_AA55 (16b) | Viterbi $K=7$ | **HIGH CONFIDENCE** | 0.98 |
| `negative_pure_sine.wav` | Sine Tone | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |
| `negative_two_tone.wav` | Two-Tone | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |
| `negative_gaussian_noise.wav` | Noise | **UNKNOWN** | - | - | None | None | **INSUFFICIENT** | **0.00** |

---

## 5. Real-World Capture Validation (`samples/wav/`)

Evaluated on the 10 real audio recordings in `samples/wav/`:
- **Files 1, 2, 3, 4, 6, 7, 8, 9:** Correctly identified as duplicate-stereo analog voice/audio. Gated by the screening layer and safely assigned `UNKNOWN` with confidence `0.00%`.
- **File 1khz-sine.wav:** Correctly detected as an unmodulated audio tone. Gated as `NON_DIGITAL_LIKELY`, returning `UNKNOWN` with confidence `0.00%`.
- **File 5.wav:** Correctly detected as independent orthogonal I/Q channels. Characterized as complex I/Q representation without crashing.

---

## 6. Execution Latency Benchmarks (Representative Segment)

| Pipeline Stage | Wall-Clock Latency |
|---|---|
| Ingestion (`.wav` / raw `.iq`) | $\sim 2.1\text{ ms}$ |
| Preprocessing & Characterization | $\sim 18.5\text{ ms}$ |
| Timing Recovery & Modulation Inference | $\sim 85.0\text{ ms}$ |
| Demodulation | $\sim 4.2\text{ ms}$ |
| De-interleaving & Vectorized FEC Decoding | $\sim 35.8\text{ ms}$ |
| **Total Receiver Latency** | $\mathbf{\sim 145.6\text{ ms}}$ |
