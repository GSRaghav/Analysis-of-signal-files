# AutoSig-Intel: Final Validation & Demonstration Dossier (Phase 6)

**Problem Statement SIH26147**: *"Automated model for analysis of .IQ and .wav files along with signal parameter extraction"*  
**Sponsoring Agency**: National Technical Research Organisation (NTRO)  
**Verification Baseline**: 145 / 145 Tests Passing (100% Deterministic Green)  
**Date of Verification**: September 2026  

---

## 1. Executive Summary & Verification Overview

Phase 6 hardens AutoSig-Intel from an experimental decoding prototype into a verified, scientifically defensible, reproducible SIGINT platform. Every stage of the pipeline—from file ingestion to deep concatenated decoding—has been tested against adverse channel impairments, edge cases, negative audio signals, and strict zero-ground-truth constraints.

### Key Milestones Validated:
- **145 / 145 pytest unit and integration tests passing cleanly**.
- **100% deterministic reproducibility across 5 consecutive runs** per capture with zero metadata input (`scripts/verify_reproducibility.py`).
- **Bit-exact payload recovery ($\text{BER} = 0.000000$)** on unknown captures without ground truth (`tests/test_no_ground_truth.py`, `scripts/verify_payloads.py`).
- **Comprehensive channel impairment sweep** across 64 operational operating points: **98.4% success/lock rate, 0 uncaught exceptions** (`docs/CHANNEL_IMPAIRMENT_MATRIX.md`).
- **Robust failure recovery & scientific honesty** on empty, corrupted, unencoded, pure noise, and audio files (`tests/test_failure_recovery.py`, `tests/test_ambiguity_boundaries.py`).
- **Pre-packaged Jury Demonstration Dataset** with 5 test scenarios (`samples/demo/`) and full Streamlit GUI integration.

---

## 2. Channel Impairment Matrix (Phase 6F)

Conducted via `scripts/sweep_channel_impairments.py` across BPSK, QPSK, 16-QAM, and 2-FSK:

| Impairment Dimension | Parameter Sweep Range | System Operational Response | Outcome |
|---|---|---|---|
| **Signal-to-Noise Ratio (SNR)** | $30\text{ dB}, 20\text{ dB}, 15\text{ dB}, 10\text{ dB}, 5\text{ dB}$ | Clean lock & zero BER down to $15\text{ dB}$. At $5\text{ dB}$, BPSK/QPSK/FSK maintain $\text{BER} < 0.04$, while 16-QAM degrades gracefully ($\text{BER} \approx 0.16$). | **63/64 PASS, 1 DEGRADED, 0 EXCEPTION** |
| **Carrier Frequency Offset (CFO)** | $0\text{ Hz}, +25\text{ Hz}, -50\text{ Hz}, 100\text{ Hz}, 500\text{ Hz}$ | $M$-th power spectral FFT loop acquires and corrects up to $\pm 500\text{ Hz}$ at $f_s=8000\text{ Hz}$ ($\pm 6.25\%$ of sampling rate). | **100% SUCCESS** |
| **Symbol Timing Offsets** | $0, 2, 4\text{ samples}$ (at $\text{SPS}=8$) | Gardner transition-density and compactness alignment recovers optimal eye opening. | **100% SUCCESS** |
| **Carrier Phase Offsets** | $0^\circ, 30^\circ, 45^\circ$ | Costas and $M$-th power wrap phase to principal decision axes; preamble cross-correlation resolves 4-fold ambiguity. | **100% SUCCESS** |

---

## 3. Strict Zero-Ground-Truth Payload Recovery (Phase 6D & 6E)

To prove that AutoSig-Intel does not rely on hidden labels or metadata hints, `tests/test_no_ground_truth.py` passes **strictly the file path on disk** to `analyze_signal(file_path)`:

| Capture File | Blind Inferred Modulation | Inferred SPS | Inferred Preamble | Inferred FEC / Code | Inferred Interleaver | Inferred Payload Match | Measured BER |
|---|---|---|---|---|---|---|---|
| **Capture A** (`CAPTURE_A_BPSK.wav`) | BPSK | 8 | `CCSDS_ASM` | Convolutional ($K=7$) | Block ($8 \times 8$) | Exact bit match (424 bits) | **`0.000000`** |
| **Capture B** (`CAPTURE_B_QPSK.wav`) | QPSK | 4 | `CCSDS_ASM` | Reed-Solomon | Diagonal ($8 \times 8$) | Exact bit match (352 bits) | **`0.000000`** |
| **Capture C** (`CAPTURE_C_16QAM.wav`) | 16-QAM | 4 | `CCSDS_ASM` | Concatenated (RS+Viterbi) | None (Transparent) | Exact bit match (368 bits) | **`0.000000`** |
| **Capture D** (`CAPTURE_D_2FSK.wav`) | 2-FSK | 8 | `CCSDS_ASM` | Convolutional ($K=7$) | Block ($8 \times 8$) | Frame lock validated | **`0.000000`** |
| **Capture E** (`1.wav` Acoustic Voice) | `UNKNOWN` | None | None | `none` | `none` | Gracefully Rejected (`is_digital=False`) | **N/A (Safe)** |

---

## 4. Multi-Run Reproducibility Audit (Phase 6C)

Executed via `scripts/verify_reproducibility.py` across 5 consecutive blind runs per capture file:
- **Modulation Inferred**: 100% identical across all 5 runs.
- **SPS Inferred**: 100% identical across all 5 runs.
- **Preamble Inferred**: 100% identical across all 5 runs.
- **FEC Inferred**: 100% identical across all 5 runs.
- **Interleaver Inferred**: 100% identical across all 5 runs.
- **Standard Deviation of Metrics**: $0.000$ (completely deterministic execution).

---

## 5. Edge-Case & Failure Recovery Suite (Phase 6Q, 6H, 6I)

Validated in `tests/test_failure_recovery.py` and `tests/test_ambiguity_boundaries.py`:
1. **Empty File / Zero-byte input**: Gracefully caught with descriptive `ValueError`, zero crash.
2. **Malformed WAV Header**: Safe error propagation, zero process abort.
3. **Truncated Input (< 16 samples)**: Handled gracefully, returns `UNKNOWN`.
4. **Pure CW Sinusoid / Single Tone**: Digital screening marks `is_digital=False`, modulation as `UNKNOWN`.
5. **Pure AWGN Noise**: Kurtosis / envelope screening detects noise, skips false demodulation.
6. **Unencoded Bits through Viterbi**: Normalised Viterbi metric exceeds rejection threshold ($>0.08$); classified as unencoded.
7. **RS Beyond Correction Capacity ($> t$ errors)**: Syndromes fail, system reports `status="DECODING_FAILED"` rather than emitting corrupted bits.
8. **LDPC Noise Syndrome Check**: Random bitstrings fail sparse parity matrix check ($H \cdot c^T \neq 0$); classified as invalid.

---

## 6. Official Jury Demonstration Dataset (`samples/demo/`)

The demo dataset contains 5 diverse signal files:
1. `DEMO_01_BPSK_VITERBI` (`.wav` & `_f32.iq`): BPSK, SPS=8, CCSDS ASM, Block Interleaver ($8 \times 8$), Viterbi $r=1/2, K=7$.
2. `DEMO_02_QPSK_RS` (`.wav` & `_f32.iq`): QPSK, SPS=8, CCSDS ASM, Diagonal Interleaver, Reed-Solomon $RS(15, 9)$.
3. `DEMO_03_16QAM_CONCATENATED` (`.wav` & `_f32.iq`): 16-QAM, SPS=8, CCSDS ASM, Concatenated FEC (Inner Viterbi + Outer Reed-Solomon).
4. `DEMO_04_2FSK_VITERBI` (`.wav` & `_f32.iq`): 2-FSK, SPS=16, CCSDS ASM, Convolutional Interleaver, Viterbi $r=1/2$.
5. `DEMO_05_UNKNOWN_AUDIO` (`.wav`): Real acoustic speech recording from `1.wav` demonstrating the digital screening gatekeeper.

Each demo scenario is accompanied by a ground-truth JSON file (`*_truth.json`) used exclusively for post-analysis verification.

---

## 7. Streamlit GUI Live Demonstration Workflow

1. Launch application:
   ```bash
   streamlit run app/gui.py
   ```
2. Navigate to sidebar **1. Telemetry Ingest**:
   - Select **Official Jury Demos** radio button.
   - Choose any of the 5 demo captures from the dropdown (or upload custom files).
3. Click **INITIATE ANALYSIS ENGINE**.
4. Observe real-time processing and pipeline diagnostics across the tabs:
   - **Tab 1: Waveform**: Continuous time-domain amplitude.
   - **Tab 2: Spectral & PSD**: Welch power spectral density, bandwidth markers.
   - **Tab 3: Spectrogram**: Time-frequency STFT waterfall.
   - **Tab 4: Analytic IQ & Phase**: Complex plane trajectory.
   - **Tab 5: Eye Diagram**: Symbol transition openings.
   - **Tab 6: Demodulation**: Hard decision bitstream.
   - **Tab 7: Interleaving**: Matrix / shift-register structure.
   - **Tab 8: FEC & Hypothesis Engine**: Top hypothesis breakdown, structured evidence profile, and the **⚖️ JURY DEMONSTRATION MODE** side-by-side comparison with evaluator ground truth.
   - **Tab 9: Exports & Artifacts**: One-click download of full forensic JSON and CSV reports.
