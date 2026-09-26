# AutoSig-Intel: Comprehensive System Architecture, Frontend, Backend & Integration Audit (Stage 1)

**Project:** AutoSig-Intel (SIH 2026 Problem Statement SIH26147)  
**Organization:** National Technical Research Organisation (NTRO)  
**Baseline Acceptance Status:** Phase 6 Complete | 145 / 145 Tests Passing | Official Demo Captures Verified  
**Audit Scope:** Read-Only Audit across Architecture, Frontend, Backend, Integration, and APIs (Zero modifications executed).  
**Date:** September 2026  

---

## 1. System Architecture Map

```
USER
  │ (Selects signal file: WAV or IQ, configures optional visualization/IQ settings)
  ▼
FRONTEND (app/gui.py)
  │ parses input file via parse_uploaded_wav / parse_uploaded_iq
  ▼
INGESTION ADAPTER (app/gui.py -> run_project_backend)
  │ delegates file path & binary parameters to orchestrator
  ▼
RECEIVER ORCHESTRATOR (core/receiver.py: analyze_signal)
  │
  ├── 1. DATA INGESTION: core/receiver.py: load_signal_for_receiver
  │      └── delegates to core/signal_loader.py: load_wav or load_iq
  │          └── produces standard SignalData container (core/signal_data.py)
  │
  ├── 2. PREPROCESSING: core/receiver.py: preprocess & representative_segment
  │      └── Zero-mean centering, unit-power normalization, contiguous bounding
  │
  ├── 3. DIGITAL SIGNAL SCREENING: core/hypothesis.py: build_hypothesis_report
  │      └── Screening gatekeeper: checks kurtosis, spectral concentration, crest factor
  │          └── [Decision: NON_DIGITAL_LIKELY / INSUFFICIENT_DATA -> Early Rejection]
  │
  ├── 4. SIGNAL CHARACTERIZATION: core/receiver.py: characterize
  │      └── Computes RMS, peak, DC offset, dominant frequency, occupied bandwidth (99% power)
  │
  ├── 5. SYMBOL TIMING RECOVERY: core/timing.py: estimate_samples_per_symbol
  │      └── Cyclostationary transition detection, cyclic autocorrelation, candidate SPS ranking
  │
  ├── 6. MODULATION & SYNCHRONIZATION HYPOTHESES:
  │      ├── PSK (order 2 & 4): core/receiver.py: test_psk_hypothesis
  │      │   └── core/synchronization.py: synchronize_psk (M-th power CFO + phase recovery)
  │      ├── 16-QAM: core/receiver.py: test_qam_hypothesis
  │      │   └── core/synchronization.py: synchronize_qam (4th power CFO + grid variance)
  │      └── 2-FSK: core/receiver.py: test_fsk_hypothesis
  │          └── core/synchronization.py: synchronize_fsk (Envelope constancy + tone tracking)
  │
  ├── 7. DEMODULATION & BITSTREAM EXTRACTION:
  │      ├── core/demodulation.py: demodulate_bpsk
  │      ├── core/demodulation.py: demodulate_qpsk
  │      ├── core/demodulation.py: demodulate_16qam
  │      └── core/demodulation.py: demodulate_2fsk
  │
  ├── 8. FRAME CORRELATION & DECODING HYPOTHESIS ENGINE:
  │      └── core/frame.py: analyze_frame_hypotheses
  │          ├── Preamble Correlation: core/correlation.py: detect_preamble
  │          │   └── Checks CCSDS_ASM (32-bit), SYNC_AA55 (16-bit), BARKER_11/13, HDLC
  │          ├── De-interleaving Hypotheses: core/interleaving.py: evaluate_interleaving_hypotheses
  │          │   └── Tests Block, Convolutional (Ramsey/Forney), Diagonal, Pseudo-Random
  │          └── FEC Syndrome Hypotheses: core/fec.py: evaluate_fec_hypotheses
  │              └── Tests Viterbi (K=3, 7), Reed-Solomon (nsym=4, 8), Concatenated RS+Conv
  │
  ├── 9. CROSS-STAGE EVIDENCE SCORING: core/receiver.py (composite cross_score)
  │      └── Combines: Constellation clustering + Preamble match + Zero-syndrome FEC
  │
  └── 10. RESULT SCHEMA GENERATION: core/receiver.py
         └── Emits canonical result dict containing metadata, best_hypothesis, evidence_profile,
             decoding, execution_times, recovered_bits, and bitstream.
  │
  ▼
GUI RENDERER (app/gui.py)
  ├── Mission Status Banner & Hero Dashboard
  ├── Parameter Summary Tiles (Fs, Modulation, Duration, Representation, Peak, BW, Noise, SNR)
  ├── End-to-End Decoding Pipeline Trajectory Banner
  └── 9 Automated Architecture Tabs:
      1. INPUT & INGESTION (File metadata, hypothesis status, raw waveform plot)
      2. SIGNAL CHARACTERIZATION (Power spectrum Welch PSD, Spectrogram waterfall)
      3. MODULATION & SYNC (Analytic complex plane, instantaneous frequency, SPS table)
      4. DEMODULATION (CFO/phase offsets, synchronized constellation, interactive ground-truth BER calc)
      5. DE-INTERLEAVING (Architecture visualizer: block matrix / conv branches, hypothesis table)
      6. FEC DECODER (Codec status, parameters, Gallager LDPC disclosure, hypothesis table)
      7. BITSTREAM & FRAMES (Color-coded binary, Hexadecimal dump, Printable ASCII, Download buttons)
      8. HYPOTHESIS & EVIDENCE (Why selected, alternatives tested table, JSON profile, Jury compare mode)
      9. EXPORTS & ARTIFACTS (Download JSON report, Download summary CSV, Latency metrics, Terminal logs)
```

---

## 2. Frontend Audit (`app/gui.py`)

### Control-by-Control Inspection

| Widget / Control | Location | Interaction / State | Backend Binding | Assessment |
|---|---|---|---|---|
| `source_mode` (Radio) | Sidebar | Toggles between "Official Demo Captures" and "Custom File Upload" | Swaps active input between `DemoFileWrapper` and `st.file_uploader` | **FUNCTIONAL** |
| `selected_demo` (Selectbox) | Sidebar | Selects one of 8 pre-indexed demo options (WAV/IQ pairs) | Points to canonical files in `samples/demo/` | **FUNCTIONAL** |
| `iq_sample_rate` (Number Input) | Sidebar (IQ Mode) | Sets sample rate for binary IQ parsing | Passed directly as `sample_rate` to `parse_uploaded_iq` and `run_project_backend` | **FUNCTIONAL** |
| `iq_dtype` (Selectbox) | Sidebar (IQ Mode) | Selects `float32`, `int16`, `float64`, `int32` | Passed directly to `parse_uploaded_iq` and `run_project_backend` | **FUNCTIONAL** |
| `iq_order` (Selectbox) | Sidebar (IQ Mode) | Selects `I-Q` or `Q-I` | Passed directly to `parse_uploaded_iq` and `run_project_backend` | **FUNCTIONAL** |
| `iq_endian` (Selectbox) | Sidebar (IQ Mode) | Selects `Little` or `Big` | Used in `parse_uploaded_iq` | **FUNCTIONAL** |
| `uploaded_file` (File Uploader) | Sidebar (Custom Mode) | Accepts `.wav` and `.iq` files | Saves to temporary file and passes to backend | **FUNCTIONAL** |
| `modulation_target` (Selectbox) | Sidebar (DSP Config) | "Auto-Detect", "FSK", "QAM", "PSK" | Stored in `backend_result['_gui']`; backend runs blind discovery automatically | **PASSIVE ADVISORY** (Does not override blind engine, acts as user target selector) |
| `deinterleave_mode` (Selectbox) | Sidebar (DSP Config) | "Auto", "Block", "Convolution", "Diagonal", "Pseudo Random" | Stored in `backend_result['_gui']`; displayed in Tab 5 | **PASSIVE ADVISORY** |
| `fec_engine` (Selectbox) | Sidebar (DSP Config) | "Auto", "Viterbi", "Reed-Solomon", "Concatenated", "LDPC" | Stored in `backend_result['_gui']`; displayed in Tab 6 | **PASSIVE ADVISORY** |
| `display_seconds` (Slider) | Sidebar (Vis Config) | 0.25s to 10.0s (default 2.0s) | Dynamically controls time window in `compute_waveform`, `compute_spectrogram` | **FUNCTIONAL** |
| `max_points` (Slider) | Sidebar (Vis Config) | 1,000 to 12,000 (default 6,000) | Dynamically controls point thinning in plots | **FUNCTIONAL** |
| `analyze_btn` (Button) | Sidebar | "INITIATE ANALYSIS ENGINE" | Resets logs/state, loads file, invokes `run_project_backend()`, sets `is_analyzed=True` | **FUNCTIONAL** |
| `ref_input` (Text Area) | Tab 4 (Demod) | Hex (`0x...`) or Binary (`0101...`) string input | Live evaluates bit errors and computes exact BER against `recovered_bits` | **FUNCTIONAL** |
| `view_choice` (Radio) | Tab 7 (Bitstream) | "Color-Coded Binary", "Hexadecimal Dump", "Printable ASCII" | Dynamically switches payload rendering view | **FUNCTIONAL** |
| `download_bits` (Download Button) | Tab 7 (Bitstream) | Generates `*_recovered_bits.txt` | Downloads recovered bit sequence as text | **FUNCTIONAL** |
| `download_payload` (Download Button) | Tab 7 (Bitstream) | Generates `*_payload.bin` | Downloads packed payload byte buffer | **FUNCTIONAL** |
| `download_json` (Download Button) | Tab 9 (Exports) | Generates `*_analysis.json` | Downloads complete canonical analysis dictionary | **FUNCTIONAL** |
| `download_csv` (Download Button) | Tab 9 (Exports) | Generates `*_summary.csv` | Downloads extracted summary parameters as CSV | **FUNCTIONAL** |

---

## 3. GUI Tab Audit (All 9 Tabs)

1. **Tab 1: INPUT & INGESTION**
   - *Purpose:* Container analysis, channel correlation, sample rate verification, raw waveform preview.
   - *Backend calls:* `first_value`, `compute_waveform`.
   - *Outputs:* Parameter summary table (Samples, Fs, Duration, Channels, IQ classification), Hypothesis status callout, Real/Imag time-domain Plotly trace.
   - *Status:* Clean. No duplicate or dead elements.

2. **Tab 2: SIGNAL CHARACTERIZATION**
   - *Purpose:* Frequency-domain spectral energy distribution and time-frequency dynamics.
   - *Backend calls:* `compute_spectrum` (Welch PSD), `compute_spectrogram` (STFT Waterfall).
   - *Outputs:* PSD power curve (dB/Hz), 2D Turbo-colored spectrogram heatmap.
   - *Status:* Clean. Robust to varying signal durations.

3. **Tab 3: MODULATION & SYNC**
   - *Purpose:* Constellation scatter and frequency discriminator diagnostics before sync.
   - *Backend calls:* `compute_constellation`, `compute_instantaneous_frequency`.
   - *Outputs:* Analytic complex plane scatter plot, instantaneous frequency tracking plot, SPS candidate ranking table.
   - *Status:* Clean.

4. **Tab 4: DEMODULATION**
   - *Purpose:* Carrier recovery residuals, synchronized symbol constellation, interactive ground-truth BER calculator.
   - *Backend calls:* `best_hypothesis.get("symbols")`, `calculate_ber`.
   - *Outputs:* 4 parameter tiles (Scheme, CFO, Phase Offset, Recovered Bits count), synchronized constellation plot, interactive BER evaluation widget with diff viewer.
   - *Status:* Clean.

5. **Tab 5: DE-INTERLEAVING**
   - *Purpose:* Interleaver detection, parameters, architecture visualization, alternative hypotheses.
   - *Backend calls:* `decoding.interleaving`, `evidence_profile.interleaver_evidence`.
   - *Outputs:* 4 parameter tiles, interactive CSS grid matrix for block interleaver / branch delay diagrams for convolutional interleaver, evaluated hypotheses table.
   - *Status:* Clean.

6. **Tab 6: FEC DECODER**
   - *Purpose:* FEC decoding verdict, syndrome checks, corrected error metrics, NP-hard LDPC disclosure.
   - *Backend calls:* `decoding.fec`, `evidence_profile.fec_evidence`.
   - *Outputs:* 4 parameter tiles (FEC Codec, Parameters, Corrected Errors, Verification Verdict), scientific LDPC disclosure banner, FEC hypothesis evaluation table.
   - *Status:* Clean.

7. **Tab 7: BITSTREAM & FRAMES**
   - *Purpose:* Frame preamble synchronization, frame length, payload extraction, hex/ASCII views, raw bit/byte export.
   - *Backend calls:* `decoding.correlation`, `recovered_bits`, `bits_to_bytes`, `format_hex_dump`.
   - *Outputs:* Detected preamble name, sync offset, frame length, correlation score, tri-view bitstream inspector, binary `.txt` and payload `.bin` download buttons.
   - *Status:* Clean.

8. **Tab 8: HYPOTHESIS & EVIDENCE**
   - *Purpose:* Explainable AI / evidence-based justification, alternatives tested and rejected, JSON evidence profile, Jury comparison mode.
   - *Backend calls:* `best_hypothesis.why_selected`, `alternatives_tested`, `evidence_profile`.
   - *Outputs:* Evidence justification card, rejection rationale table, structured evidence JSON tree, Evaluator Ground Truth side-by-side comparison (active only after blind inference).
   - *Status:* Clean. Strictly preserves ground-truth insulation.

9. **Tab 9: EXPORTS & ARTIFACTS**
   - *Purpose:* Exporting reports, timing metrics, and terminal execution logs.
   - *Backend calls:* `result_to_csv_row`, `json_safe`, `result.execution_times`.
   - *Outputs:* Download JSON report button, Download CSV summary button, 6 execution latency metrics, scrollable terminal log container.
   - *Status:* Clean.

---

## 4. Backend Module Audit

| Module | Core Responsibility | Primary Functions | Input Schema | Output Schema |
|---|---|---|---|---|
| `core/signal_data.py` | Data container | `SignalData` class | Samples (1D/2D array), Fs | Dataclass with `samples`, `sample_rate`, `representation`, `possible_iq` |
| `core/signal_loader.py` | File ingestion | `load_wav`, `load_iq` | File path, optional binary specs | Populated `SignalData` instance |
| `core/preprocessing.py` | Signal conditioning | `normalize_power`, `remove_dc` | Raw samples array | Zero-mean, unit-variance complex64 array |
| `core/signal_analysis.py` | Classical spectral analysis | `calculate_basic_parameters`, `estimate_bandwidth`, `estimate_snr` | Samples, Fs | Dict with RMS, Peak, DC offset, Bandwidth (Hz), SNR (dB) |
| `core/timing.py` | Symbol timing recovery | `estimate_samples_per_symbol` | Complex samples, Fs | Ranked list of `{'samples_per_symbol', 'symbol_rate_hz', 'score'}` |
| `core/synchronization.py` | Carrier and symbol timing lock | `synchronize_psk`, `synchronize_qam`, `synchronize_fsk` | Samples, Fs, SPS | Dict with `symbols`, `frequency_offset_hz`, `phase_offset_rad`, `timing_offset` |
| `core/demodulation.py` | Constellation symbol slicing | `demodulate_bpsk`, `demodulate_qpsk`, `demodulate_16qam`, `demodulate_2fsk` | Synchronized symbols | 1D `np.uint8` array of demodulated bits |
| `core/interleaving.py` | Forward & inverse interleaving | `block_deinterleave`, `convolutional_deinterleave`, `diagonal_deinterleave`, `evaluate_interleaving_hypotheses` | Bit array, parameters | Deinterleaved bit array, ranked hypotheses |
| `core/fec.py` | Error correction codecs | `viterbi_decode`, `reed_solomon_decode`, `evaluate_fec_hypotheses` | Bit array | Decoded bit array, syndrome validity, corrected error count |
| `core/correlation.py` | Preamble search & framing | `detect_preamble`, `detect_header_candidates` | Bit array, preamble dictionary | Preamble match location, score, bit errors, frame boundaries |
| `core/frame.py` | Cross-layer decoding hypothesis search | `analyze_frame_hypotheses` | Recovered bits, modulation | Best decoding hypothesis, candidates list, preamble details |
| `core/hypothesis.py` | Gatekeeping & feature ranking | `build_hypothesis_report`, `screen_digital_signal` | Signal segment, Fs | Screening decision (`PASS`, `NON_DIGITAL_LIKELY`), spectral features |
| `core/receiver.py` | Central pipeline orchestrator | `analyze_signal`, `load_signal_for_receiver` | File path or `SignalData` | Canonical comprehensive analysis dictionary |

---

## 5. Integration Audit across Official Demo Signals

| Signal File | Stage Transitions & Inferred Pipeline | End-to-End Status |
|---|---|---|
| **`DEMO_01_BPSK_VITERBI.wav`** | Fs=48kHz $\to$ Real/IQ Screening: PASS $\to$ Timing: SPS=8 $\to$ Sync: CFO=+30.0Hz, $\phi$=+0.04 rad $\to$ Demod: BPSK (3000 bits) $\to$ Deinterleave: Block (8x8) $\to$ FEC: Viterbi K=7 (Passed) $\to$ Preamble: CCSDS_ASM (32 bits, 0 err) $\to$ Result: **BPSK (97.0% confidence)** | **VERIFIED** |
| **`DEMO_02_QPSK_RS.wav`** | Fs=64kHz $\to$ Real/IQ Screening: PASS $\to$ Timing: SPS=2 $\to$ Sync: CFO=-34.9Hz, $\phi$=-0.38 rad $\to$ Demod: QPSK (7424 bits) $\to$ Deinterleave: Diagonal $\to$ FEC: Reed-Solomon nsym=4 (Passed) $\to$ Preamble: SYNC_AA55 (16 bits, 0 err) $\to$ Result: **QPSK (97.5% confidence)** | **VERIFIED** |
| **`DEMO_03_16QAM_CONCATENATED.wav`** | Fs=64kHz $\to$ Real/IQ Screening: PASS $\to$ Timing: SPS=8 $\to$ Sync: CFO=+18.1Hz, $\phi$=-0.22 rad $\to$ Demod: 16-QAM (3504 bits) $\to$ Deinterleave: None $\to$ FEC: Concatenated RS4+Conv7 (Passed) $\to$ Preamble: CCSDS_ASM (32 bits, 0 err) $\to$ Result: **16-QAM (90.7% confidence)** | **VERIFIED** |
| **`DEMO_04_2FSK_VITERBI.wav`** | Fs=48kHz $\to$ Real/IQ Screening: PASS $\to$ Timing: SPS=16 $\to$ Sync: CFO=-12.0Hz $\to$ Demod: 2-FSK (1500 bits) $\to$ Deinterleave: Block (8x8) $\to$ FEC: Viterbi K=7 (Passed) $\to$ Preamble: CCSDS_ASM (32 bits, 0 err) $\to$ Result: **2-FSK (97.7% confidence)** | **VERIFIED** |
| **`DEMO_05_UNKNOWN_AUDIO.wav`** | Fs=37.5kHz $\to$ Real/IQ Screening: NON_DIGITAL_LIKELY (Acoustic voice speech) $\to$ Downstream DSP safely bypassed $\to$ Result: **UNKNOWN (0.0% confidence, Clean Rejection)** | **VERIFIED** |

---

## 6. API / Interface Audit & Risk Assessment

1. **GUI vs. Receiver Schema Consistency:**
   - The GUI relies on `first_value(result, ...)` to extract properties like `cfo_est_hz`, `samples_per_symbol`, `noise_floor_db`. The canonical dictionary produced by `analyze_signal()` directly populates these keys at both the top level and inside `decoding`, `characterization`, and `evidence_profile`. All key bindings match.

2. **Data-Flow Integrity:**
   - **Bitstream Type Continuity:** Demodulation yields `np.uint8` arrays of 0 and 1 values. Interleaver functions, Viterbi decoders, and Reed-Solomon wrappers consistently consume and return 1D `np.uint8` arrays.
   - **Complex vs. Real Conditioning:** Dual-channel WAV files are checked for duplicate channels (mono duplicate) vs. orthogonal quadrature signals. When duplicate channels are detected, the loader extracts a single real channel, and `analytic_signal()` safely constructs the analytic representation for complex-plane plotting.

3. **Risk & Severity Classification:**

| Issue / Observation | Classification | Impact |
|---|---|---|
| Sidebar DSP Configuration selects (`Modulation Target`, `De-interleaver Mode`, `FEC Engine`) are advisory metadata stored in `result['_gui']` and do not constrain the backend blind search engine. | **LOW / INFO** | The backend performs fully autonomous blind discovery across all modulations and codes. If a user intends to manually force a specific demodulator, the UI currently does not pass forced parameters. |
| In Tab 8 (Jury Demo Mode), ground-truth JSON files are loaded by resolving the signal filename stem (e.g. `DEMO_01_BPSK_VITERBI_truth.json`). | **INFO** | Ground truth is only read after analysis completes and is strictly used to display evaluator comparison; no leakage into the inference engine occurs. |
| In `compute_waveform`, large signals are uniformly thinned to `max_points` (default 6000) for responsive Plotly rendering. | **INFO** | Essential for web browser stability. Raw samples remain unthinned in backend memory for DSP processing. |

---

## 7. Audit Conclusion

The AutoSig-Intel runtime architecture is fully aligned with Problem Statement SIH26147:
- The frontend cleanly renders all 9 pipeline tabs without unhandled exceptions.
- The backend receiver executes deterministic, mathematically grounded inference across modulation, timing, sync, de-interleaving, and FEC.
- Zero mock metrics, fake uptime, or hardcoded classifications exist in the pipeline.
- Ground truth remains strictly insulated outside the receiver orchestrator.
- The 145/145 test baseline remains completely valid and stable.
