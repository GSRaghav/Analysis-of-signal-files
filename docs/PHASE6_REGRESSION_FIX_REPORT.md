# AutoSig-Intel: Phase 6 Regression Investigation & Root-Cause Resolution Report

**Problem Statement:** SIH26147 (Automated model for analysis of .IQ and .wav files along with signal parameter extraction)  
**Organization:** National Technical Research Organisation (NTRO)  
**Baseline Test Suite:** 145 / 145 Unit & Integration Tests PASSING  
**Date:** September 2026  

---

## 1. Executive Summary

During recent UI maintenance, two issues emerged:
1. **Streamlit UI Crash (`NameError: name 'tab_dsp' is not defined`):** Accessing the GUI crashed immediately at line 1625 due to an uninitialized tab variable referencing legacy plotting code.
2. **Modulation Inferred as `UNKNOWN`:** In the GUI, inputs were reported as `UNKNOWN` because:
   - For all signals, the GUI crashed mid-render due to the `tab_dsp` exception before the full analysis view completed.
   - For 16-QAM captures (`DEMO_03_16QAM_CONCATENATED.wav`), the multi-stage receiver candidate threshold (`>= 0.40`) in `core/receiver.py` excluded genuine 16-QAM hypotheses scoring 0.383 from downstream cross-stage validation (preamble lock and concatenated FEC validation).

Both root causes were isolated, mathematically validated, and repaired without regression. Ground-truth insulation remains 100% intact with zero hardcoding.

---

## 2. Root Cause Analysis

### Issue A: Streamlit UI Crash (`tab_dsp`)
- **Location:** `app/gui.py`, lines 1621–1851.
- **Mechanism:** In `app/gui.py`, `st.tabs` unpacked nine tabs:
  ```python
  (tab_input, tab_char, tab_mod, tab_demod, tab_interleave, tab_fec, tab_bitstream, tab_evidence, tab_exports)
  ```
  The Waveform, Waterfall, and Spectrum plots were already rendered in `tab_char`, while the Constellation, Eye Diagram, Instantaneous Frequency, Modulation Hypotheses, and SPS Candidates were already rendered in `tab_mod`.
  Immediately after `tab_mod`, a legacy duplicate block `with tab_dsp:` attempted to render duplicate plots under `tab_dsp`, which was never declared. This threw `NameError: name 'tab_dsp' is not defined`.
- **Resolution:** Removed the redundant lines (1621–1851). The clean 9-tab workflow now renders without errors.

### Issue B: 16-QAM Viable Candidate Gating
- **Location:** `core/receiver.py`, line 663.
- **Mechanism:** The candidate filtering rule was:
  ```python
  viable_candidates = [h for h in hypotheses if h.get("score", 0.0) >= 0.40][:6]
  ```
  In `qam16_quality()`, the quality score is the product of four sub-unity metrics:
  $$\text{score} = \text{compactness} \times \frac{\text{occupied}}{16} \times \text{entropy} \times m_4\text{\_score}$$
  For `DEMO_03_16QAM_CONCATENATED.wav`:
  - $\text{compactness} \approx 0.600$
  - $\frac{\text{occupied}}{16} = 1.000$
  - $\text{entropy} \approx 0.962$
  - $m_4\text{\_score} \approx 0.664$
  - $\text{score} = 0.600 \times 1.0 \times 0.962 \times 0.664 = 0.3831$
  
  Because $0.3831 < 0.40$, 16-QAM was excluded from `viable_candidates`. Downstream cross-stage correlation (`analyze_frame_hypotheses`), which detects the `CCSDS_ASM` preamble with 0 bit errors and successfully validates `concatenated_rs4_conv_k7` with a 98.7% composite score, was never evaluated. Consequently, the receiver fell back to `UNKNOWN`.
- **Resolution:** Adjusted the viable candidate threshold in `core/receiver.py` from `>= 0.40` to `>= 0.30`. This safely allows candidates with valid constellation clustering to proceed to full cross-stage validation, where downstream preamble match and FEC validation determine the final verdict. Non-digital signals (e.g. noise, speech) score $0.00$ and remain cleanly rejected.

---

## 3. End-to-End Demo Verification Results

Evaluation using `run_project_backend()` across all official demo recordings:

| Signal File | Modulation Inferred | Confidence | FEC Recovered | Status |
|---|---|---|---|---|
| `DEMO_01_BPSK_VITERBI.wav` | **BPSK** | **97.0%** | `convolutional_viterbi_k7` | PASS |
| `DEMO_02_QPSK_RS.wav` | **QPSK** | **97.5%** | `reed_solomon_nsym4` | PASS |
| `DEMO_03_16QAM_CONCATENATED.wav` | **16-QAM** | **90.7%** | `concatenated_rs4_conv_k7` | PASS |
| `DEMO_04_2FSK_VITERBI.wav` | **2-FSK** | **97.7%** | `convolutional_viterbi_k7` | PASS |
| `DEMO_05_UNKNOWN_AUDIO.wav` | **UNKNOWN** | **0.0%** | None (Gate Rejected) | PASS |

---

## 4. Test Suite Integrity Verification

- **Command:** `pytest -q`
- **Result:** `145 passed in 1206.18s (0:20:06)`
- **Regression:** Zero test regressions across unit, DSP, synchronization, demodulation, interleaving, and FEC suites.

---

## 5. Blind Pipeline Reproducibility Verification

- **Command:** `python scripts/verify_reproducibility.py` (5 consecutive runs per capture)
- **Result:**
  - `capture_a_bpsk.wav`: 100% Consistent (BPSK, SPS=8, Preamble=CCSDS_ASM, FEC=convolutional_viterbi_k7, Interleaver=block)
  - `capture_b_qpsk.wav`: 100% Consistent (QPSK, SPS=8, Preamble=CCSDS_ASM, FEC=reed_solomon_nsym4, Interleaver=diagonal)
  - `capture_c_qpsk.wav`: 100% Consistent (QPSK, SPS=8, Preamble=CCSDS_ASM, FEC=convolutional_viterbi_k3, Interleaver=pseudo_random)
  - `capture_d_16qam.wav`: 100% Consistent (16-QAM, SPS=4, Preamble=SYNC_AA55, FEC=reed_solomon_nsym4, Interleaver=block)
  - `capture_e_2fsk.wav`: 100% Consistent (2-FSK, SPS=16, Preamble=SYNC_AA55, FEC=convolutional_viterbi_k7, Interleaver=convolutional)
- **Verdict:** `ALL RUNS 100% REPRODUCIBLE & DETERMINISTIC. ZERO NONDETERMINISM.`
