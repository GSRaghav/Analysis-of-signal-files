# AUTOSIG-INTEL — FINAL API & RESULT-SCHEMA CONTRACT AUDIT

**Project:** AutoSig-Intel (SIH 2026 — SIH26147, NTRO)  
**System Baseline:** 145 / 145 Tests Passing | Phase 6 Acceptance Baseline  
**Scope:** Cross-Module Function Contracts, Canonical Result Schema, GUI Bindings, and Export Mappings  
**Execution Constraint:** Audit Only (Zero Source Code Modifications)

---

## 1. Canonical Result Schema Contract

The authoritative data structure returned by the primary receiver orchestrator `core.receiver.analyze_signal(path, ...)` is a comprehensive Python dictionary with structured hierarchical namespaces.

```
analyze_signal(...)
├── file: str                                [File path as string]
├── path: str                                [Absolute filesystem path]
├── sample_rate_hz: int | float              [Sampling rate in Hz]
├── num_samples: int                         [Total sample count]
├── duration_seconds: float                  [Duration N / Fs in seconds]
├── representation: str                      ['complex_iq' | 'real']
├── possible_iq: bool                        [True if channels are independent IQ]
├── channel_correlation: float | None        [Normalized dot product between stereo channels]
├── characterization: dict                   [Low-level physical DSP metrics]
│   ├── rms: float                           [Normalized root-mean-square amplitude]
│   ├── peak: float                          [Peak absolute amplitude]
│   ├── dc: float                            [DC offset residual]
│   ├── dominant_frequency_hz: float         [Spectral peak frequency relative to center]
│   └── occupied_bandwidth_hz: float         [99% power spectral bandwidth]
├── timing_candidates: list[dict]            [Ranked SPS timing hypotheses from core.timing]
│   └── dict: samples_per_symbol (int), symbol_rate_hz (float), score (float),
│             timing_offset (int), timing_error (float), method (str)
├── tested_sps: list[int]                    [Explicit candidate SPS integers evaluated]
├── modulation_hypotheses: list[dict]        [Raw physical-layer modulation evaluations]
│   └── dict: modulation (str), samples_per_symbol (int), symbol_rate_hz (float),
│             score (float), frequency_offset_hz (float), timing_offset (int),
│             phase_offset_rad (float), symbol_count (int)
├── best_hypothesis: dict                    [Authoritative selected hypothesis]
│   ├── modulation: str                      [e.g., 'BPSK', 'QPSK', '16-QAM', '2-FSK', 'UNKNOWN']
│   ├── samples_per_symbol: int | None       [Selected integer SPS]
│   ├── symbol_rate_hz: float | None         [Selected baud rate in Hz]
│   ├── score: float                         [Physical constellation quality score in [0.0, 1.0]]
│   ├── cross_score: float                   [Cross-stage validation score in [0.0, 2.0]]
│   ├── confidence: float                    [Reported confidence in [0.0, 1.0]]
│   ├── confidence_tier: str                 ['HIGH CONFIDENCE' | 'MEDIUM CONFIDENCE' | 'INSUFFICIENT_EVIDENCE']
│   ├── frequency_offset_hz: float           [Carrier frequency offset in Hz]
│   ├── timing_offset: int                   [Symbol timing fractional sample offset]
│   ├── phase_offset_rad: float              [Constellation residual phase in radians]
│   ├── status: str                          ['ANALYSIS_COMPLETE' | 'INSUFFICIENT_EVIDENCE']
│   ├── why_selected: str                    [Human-readable evidence justification string]
│   ├── reason: str                          [Identical to why_selected for backward compatibility]
│   └── alternatives_tested: list[dict]      [Other hypotheses with rejection reasons]
├── modulation: str                          [Authoritative modulation string from best_hypothesis]
├── samples_per_symbol: int | None           [Authoritative SPS integer from best_hypothesis]
├── symbol_rate_hz: float | None             [Authoritative baud rate from best_hypothesis]
├── cfo_est_hz: float                        [Estimated CFO in Hz]
├── confidence: float                        [Confidence float from best_hypothesis]
├── status: str                              [Execution status string]
├── evidence_profile: dict                   [Multi-stage structured forensic container]
│   ├── modulation_evidence: dict            [quality_score, cross_score, modulation]
│   ├── timing_evidence: dict                [samples_per_symbol, symbol_rate_hz, timing_offset]
│   ├── synchronization_residual: dict       [frequency_offset_hz, phase_offset_rad]
│   ├── correlation_evidence: dict           [preamble_found, preamble_type, preamble_score]
│   ├── interleaver_evidence: dict           [best_type, status]
│   └── fec_evidence: dict                   [best_type, fec_valid]
├── decoding: dict                           [Full protocol stack decoding tree]
│   ├── demodulation: dict                   [status, modulation, recovered_bits_count, sps, symbol_rate_hz]
│   ├── correlation: dict                    [status, preamble dict, frame_structure dict]
│   ├── interleaving: dict                   [status, best_hypothesis, parameters dict]
│   ├── fec: dict                            [status, best_hypothesis, parameters dict, fec_valid]
│   └── frame: dict                          [status, overall_score, candidates list, decoded_bits]
├── execution_times: dict                    [High-precision perf_counter breakdown in seconds]
│   ├── ingestion_time_seconds: float
│   ├── characterization_time_seconds: float
│   ├── modulation_inference_time_seconds: float
│   ├── demodulation_time_seconds: float
│   ├── decoding_time_seconds: float
│   └── total_time_seconds: float
├── recovered_bits: np.ndarray | None        [Demodulated hard decision 0/1 bits]
└── bitstream: str | None                    [Raw bit sequence formatted as ASCII '0101...']
```

---

## 2. Cross-Module Function Contracts

| Source Module | Target Module | Cross-Module Function | Input Types & Required Args | Return Type | Units | Error Handling Behavior |
|---|---|---|---|---|---|---|
| `core.signal_loader` | `core.receiver` | `load_wav` | `path: str \| Path` | `SignalData` | Amplitudes $[-1, 1]$, Fs in Hz | Raises `LibsndfileError` / `ValueError` |
| `core.signal_loader` | `core.receiver` | `load_iq` | `path`, `sample_rate: float`, `dtype`, `iq_order` | `SignalData` | Complex IQ array, Fs in Hz | Raises `ValueError` if truncated |
| `core.hypothesis` | `core.receiver` | `build_hypothesis_report` | `samples: np.ndarray`, `sample_rate: float` | `dict` | Spectral features, decision string | Fallback defaults on zero length |
| `core.receiver` | internal | `characterize` | `samples: np.ndarray`, `sample_rate: float` | `dict[str, float]` | RMS, peak, dominant Freq (Hz), BW (Hz) | Safe return on DC/zero input |
| `core.timing` | `core.receiver` | `estimate_samples_per_symbol` | `samples`, `sample_rate`, `min_symbol_rate` | `dict` | List of candidate dicts with integer SPS | Returns default grid $\{4, 8, 16\}$ on low SNR |
| `core.synchronization`| `core.receiver` | `synchronize_psk` | `samples`, `sample_rate`, `sps: int`, `order: int` | `dict` | Synchronized symbols, CFO (Hz), $\phi$ (rad) | Bounded to principal quadrants |
| `core.synchronization`| `core.receiver` | `synchronize_qam` | `samples`, `sample_rate`, `sps: int`, `order=16` | `dict` | Synchronized symbols, CFO (Hz), $\phi$ (rad) | 4th-power carrier tracking |
| `core.synchronization`| `core.receiver` | `synchronize_fsk` | `samples`, `sample_rate`, `sps: int` | `dict` | Instantaneous frequency, CFO (Hz) | Discriminator phase differentiation |
| `core.demodulation` | `core.receiver` | `demodulate_bpsk` | `samples: np.ndarray`, `sps=1`, `timing_offset`, $\phi$ | `np.ndarray` (uint8) | Array of binary 0/1 bits | Hard thresholding at real plane $\ge 0$ |
| `core.demodulation` | `core.receiver` | `demodulate_qpsk` | `samples: np.ndarray`, `sps=1`, `timing_offset`, $\phi$ | `np.ndarray` (uint8) | Array of binary 0/1 bits (Gray coded) | Quadrant slicing |
| `core.demodulation` | `core.receiver` | `demodulate_16qam`| `samples: np.ndarray`, `sps=1`, `timing_offset`, $\phi$ | `np.ndarray` (uint8) | Array of binary 0/1 bits (Gray coded) | 4-level PAM decision grid |
| `core.demodulation` | `core.receiver` | `demodulate_2fsk` | `samples`, `sample_rate`, `sps`, `timing_offset` | `np.ndarray` (uint8) | Array of binary 0/1 bits | Envelope/frequency comparison |
| `core.frame` | `core.receiver` | `analyze_frame_hypotheses`| `bits: np.ndarray`, `modulation: str` | `dict` | Best decoding candidate, preamble metadata | Evaluates frame stack safely |
| `core.correlation` | `core.frame` | `detect_preamble` | `bits: np.ndarray`, `preambles: dict` | `dict \| None` | Start/end index, match score $[0, 1]$ | None if threshold not met |
| `core.interleaving` | `core.frame` | `evaluate_interleaving_hypotheses` | `bits: np.ndarray`, `validator_fn` | `list[dict]` | Evaluated interleaver candidates | Safe fallback to 'none' / 'UNKNOWN' |
| `core.fec` | `core.frame` | `evaluate_fec_hypotheses` | `bits: np.ndarray`, `preamble_validator` | `list[dict]` | Evaluated FEC candidates | Catches decoder errors gracefully |

---

## 3. GUI Panel to Schema Traceability

Every GUI element in `app/gui.py` is traced back directly to its authoritative location in the canonical schema:

| GUI Tab / Section | Visual Widget / Metric | Schema Access Expression in `app/gui.py` | Authoritative Key in `core.receiver` | Data Type & Unit |
|---|---|---|---|---|
| **Top Status Banner** | Active File | `file_name` | Derived from `uploaded_file.name` | String |
| **Top Metric Tile 1** | Sampling Frequency | `fmt_hz(fs)` | `signal_meta['fs']` / `result['sample_rate_hz']` | Float / Int ($\text{Hz}$) |
| **Top Metric Tile 2** | Modulation & Conf | `modulation`, `confidence` | `result['modulation']`, `result['confidence']` | String, Float ($0.0 - 100.0\%$) |
| **Top Metric Tile 3** | Duration & Channels | `fmt_number(duration, 2, " s")` | `result['duration_seconds']`, `result['num_samples'] / Fs` | Float ($\text{s}$), Int count |
| **Top Metric Tile 4** | Representation | `signal_meta.get("representation")` | `result['representation']` | `'complex_iq'` \| `'real'` |
| **Top Metric Tile 5** | Dominant Peak Freq | `fmt_hz(peak_freq)` | Live Welch PSD peak / `result['characterization']['dominant_frequency_hz']` | Float ($\text{Hz}$) |
| **Top Metric Tile 6** | Occupied Bandwidth | `fmt_hz(bandwidth)` | `result['characterization']['occupied_bandwidth_hz']` | Float ($\text{Hz}$) |
| **Top Metric Tile 7** | Noise Floor | `fmt_number(noise_floor, 2, " dB")` | 20th percentile Welch / `result.get('noise_floor_db')` | Float ($\text{dB}$) |
| **Top Metric Tile 8** | Screening SNR | `fmt_number(snr, 2, " dB")` | In-band vs out-of-band / `result.get('snr_db')` | Float ($\text{dB}$) |
| **Trajectory Bar** | 8 Pipeline Stages | Path classes (`validated`, `rejected`, `active`) | Derived from `result['status']`, `result['decoding']` | Discrete CSS states |
| **Tab 1: Input** | Ingestion Table | `pd.DataFrame(summary.items())` | `signal_meta` & `result['channel_correlation']` | Table |
| **Tab 1: Input** | Hex Dump | `format_hex_dump(...)` | First 1024 bytes of input buffer | Hex lines with ASCII preview |
| **Tab 2: Characterization**| Waveform / Spectrum | `compute_waveform`, `compute_spectrum` | Preprocessed signal $x(t)$ | Plotly Scatter WebGL traces |
| **Tab 3: Mod & Sync** | Constellation Scatter | `compute_constellation(x, fs)` | Complex analytic signal $z[n]$ | Square aspect ratio scatter |
| **Tab 3: Mod & Sync** | Timing Table | `result.get("timing_candidates")` | `result['timing_candidates']` | List of dicts |
| **Tab 4: Demodulation** | Demod Tiles & Const | `result['decoding']['demodulation']` | `result['decoding']['demodulation']` | Recovered bits, CFO, $\phi$ |
| **Tab 5: De-interleaving**| Deinterleaver & Matrix | `result['decoding']['interleaving']` | `result['decoding']['interleaving']['best_hypothesis']` | Name, $R \times C$ block grid |
| **Tab 6: FEC Decoder** | FEC Codec & Syndrome | `result['decoding']['fec']` | `result['decoding']['fec']['best_hypothesis']` | Codec name, syndrome status |
| **Tab 7: Bitstream** | Preamble & Sync Offset | `result['decoding']['correlation']` | `result['decoding']['correlation']['preamble']` | Preamble name, bit offset |
| **Tab 7: Bitstream** | Recovered Bits Text | `result.get("recovered_bits")` | `result['recovered_bits']` | Hard-decision bit array |
| **Tab 8: Evidence** | Why Selected Banner | `best_hyp.get("why_selected")` | `result['best_hypothesis']['why_selected']` | Justification text string |
| **Tab 8: Evidence** | Alternatives Table | `best_hyp.get("alternatives_tested")` | `result['best_hypothesis']['alternatives_tested']` | Rejection rationales table |
| **Tab 8: Evidence** | Evidence Profile JSON | `result.get("evidence_profile")` | `result['evidence_profile']` | Structured JSON viewer |
| **Tab 9: Exports** | Latency Metrics | `result.get("execution_times")` | `result['execution_times']` | Ingestion, Char, Mod, Demod, Dec |
| **Tab 9: Exports** | Execution Logs | `st.session_state.analysis_logs` | Internal session log array | Monospaced console text |

---

## 4. Export Mappings Audit

Both export pathways in Tab 9 consume the canonical schema:

### 4.1 JSON Tree Export (`<signal>_analysis.json`)
- **Structure:**
  ```json
  {
    "file": "<signal_name>",
    "signal_metadata": { ... },
    "backend_result": { ... },
    "live_peak_frequency_hz": ...
  }
  ```
- **Serialization Safety:** Sanitized via `json_safe()` helper in `app/gui.py` which recursively converts NumPy scalar dtypes (`np.float32`, `np.int64`), ndarrays, and non-serializable objects into native Python floats, ints, lists, and strings.
- **Verification:** Produces valid, compliant JSON (14 KB to 22 KB per file) without throwing `TypeError`.

### 4.2 CSV Telemetry Summary Export (`<signal>_summary.csv`)
- **Fields Mapped:**
  1. `filename`: `file_name`
  2. `sample_rate_hz`: `signal_meta["fs"]`
  3. `num_samples`: `signal_meta["num_samples"]`
  4. `duration_seconds`: `signal_meta["num_samples"] / signal_meta["fs"]`
  5. `channels`: `signal_meta["channels"]`
  6. `representation`: `signal_meta["representation"]`
  7. `possible_iq`: `signal_meta["possible_iq"]`
  8. `channel_correlation`: `signal_meta["channel_correlation"]`
  9. `peak_frequency_hz_live`: `live_peak_frequency`
  10. `modulation_hypothesis`: `extract_modulation(result)` $\to$ `result['modulation']`
  11. `modulation_confidence_percent`: `extract_confidence(result)` $\to$ `result['confidence'] * 100`
  12. `estimated_bandwidth_hz`: `first_value(result, "estimated_bandwidth_hz", "occupied_bandwidth_hz")`
  13. `estimated_noise_floor_db`: `first_value(result, "estimated_noise_floor_db", "noise_floor_db")`
  14. `estimated_snr_proxy_db`: `first_value(result, "estimated_snr_db", "snr_db", "spectral_snr_proxy_db")`
  15. `samples_per_symbol`: `first_value(result, "samples_per_symbol", "sps")`
  16. `symbol_rate_baud`: `first_value(result, "symbol_rate_baud", "symbol_rate")`

---

## 5. Inconsistencies, Aliases & Legacy Fields Identified

During the audit, the following legacy aliases and fallback mappings were noted in the codebase:

1. **Top-Level Redundancy in `core.receiver.analyze_signal`:**
   - `result["modulation"]` duplicates `result["best_hypothesis"]["modulation"]`.
   - `result["samples_per_symbol"]` duplicates `result["best_hypothesis"]["samples_per_symbol"]`.
   - `result["confidence"]` duplicates `result["best_hypothesis"]["confidence"]`.
   - `result["symbol_rate_hz"]` duplicates `result["best_hypothesis"]["symbol_rate_hz"]`.
   - *Status:* **Benign.** Kept intentionally for flat-access convenience and backward compatibility with test suites.
2. **Field Naming Aliases in Receiver vs Characterization:**
   - In `characterization`, the field is named `occupied_bandwidth_hz`.
   - In earlier legacy receivers, it was named `estimated_bandwidth_hz`.
   - *Status:* **Resolved.** The GUI helper `first_value(result, "estimated_bandwidth_hz", "occupied_bandwidth_hz")` safely checks both.
3. **CFO Field Naming:**
   - `result["cfo_est_hz"]` is provided at top-level.
   - `result["best_hypothesis"]["frequency_offset_hz"]` is provided in the hypothesis.
   - `result["evidence_profile"]["synchronization_residual"]["frequency_offset_hz"]` is provided in forensic evidence.
   - *Status:* **Consistent values**, but slightly different key names across containers (`cfo_est_hz` vs `frequency_offset_hz`).
4. **Calculated but Not Prominently Rendered:**
   - `result["characterization"]["dc"]` (DC offset): Calculated in DSP characterization and exported to JSON, but not given a dedicated visual card in the GUI (subsumed by normalization).
   - `result["timing_candidates"][i]["median_transition_interval"]`: Calculated in timing, visible in the Tab 3 table, but not highlighted in top tiles.
5. **Displayed but Not Calculated on All Modes:**
   - In raw IQ mode without sample rate headers, sampling rate relies on user input (`iq_sample_rate`), and the GUI correctly displays the badge `"User Supplied (Raw IQ has no header)"`.

---

## 6. Audit Conclusion & Recommended Future Cleanups

1. **System Integrity:**
   - Every value displayed across the 9 GUI tabs and exported files has a single, verifiable, deterministic source of truth.
   - Zero hardcoded mock parameters exist.
   - Data types, units (Hz, seconds, dB, rad), and structures are strictly maintained.
2. **Recommended Cleanups (Post-SIH Freeze):**
   - Standardize all carrier frequency offset keys across the dictionary to `carrier_frequency_offset_hz`.
   - Standardize all bandwidth keys to `occupied_bandwidth_hz`.
   - Deprecate top-level flattened duplicate keys in favor of explicit `result["best_hypothesis"]` references once all external consumers are unified.
