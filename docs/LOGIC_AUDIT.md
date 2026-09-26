# AutoSig-Intel: Backend Logic & Hypothesis Engine Audit (Stage 3)

**Project:** AutoSig-Intel (SIH 2026 Problem Statement SIH26147)  
**Organization:** National Technical Research Organisation (NTRO)  
**Baseline Test Status:** 145 / 145 Tests Passing | Official Demo Set Verified  
**Audit Scope:** Multi-stage hypothesis reasoning, candidate ranking, decision thresholds, edge-case failure modes, counterexamples, and state conflation analysis (Zero code modifications).  
**Date:** September 2026  

---

## 1. End-to-End Reasoning Pipeline Flow

```
Digital Gatekeeper (Screening)
  │ [Rejects pure continuous tones & unmodulated Gaussian noise early]
  ▼
Symbol Timing Recovery (estimate_samples_per_symbol)
  │ [Recovers SPS candidates via cyclostationary autocorrelation + fallback grid {4, 8, 16}]
  ▼
Physical Modulation Hypotheses (BPSK, QPSK, 16-QAM, 2-FSK at candidate SPS)
  │ [Carrier CFO + Phase + Symbol Timing locked per candidate]
  │ [Computes raw physical constellation quality score: compactness * balance * envelope * m4]
  ▼
Viable Candidate Gating (score >= 0.30)
  │ [Filters unviable noise/cross-talk while preserving valid multi-level 16-QAM constellations]
  ▼
Downstream Protocol Demodulation (demodulate_bpsk / qpsk / 16qam / 2fsk)
  │ [Extracts hard-decision bitstream from synchronized symbols]
  ▼
Frame & Preamble Cross-Correlation (detect_preamble)
  │ [Correlates against CCSDS_ASM, SYNC_AA55, BARKER_11/13, HDLC_FLAG; PSR > 4.0 threshold]
  ▼
De-interleaving & FEC Syndrome Hypotheses (evaluate_interleaving_hypotheses & evaluate_fec_hypotheses)
  │ [Evaluates Viterbi trellis path metrics, Reed-Solomon zero-syndrome checks, Concatenated RS+Conv]
  ▼
Cross-Stage Composite Evidence Scoring (cross_score)
  │ [Fuses: 0.30*ModScore + 0.35*PreambleScore + 0.35*FECScore + 0.30]
  ▼
Decision Gate & Confidence Tier Assignment
  ├── Conf >= 50% or ModScore >= 0.55 -> ANALYSIS_COMPLETE (Best Hypothesis Selected)
  └── Else -> UNKNOWN (INSUFFICIENT_EVIDENCE)
```

---

## 2. Threshold Justification Matrix

| Parameter / Threshold | Location | Value | Mathematical / Physical Justification | Behavior Below Threshold | Behavior Above Threshold |
|---|---|---|---|---|---|
| **Tone Detection Score** | `core/hypothesis.py:528` | $0.70$ | Signals dominated by a single discrete Dirac delta frequency spike are unmodulated carrier tones. | Allows signal to enter digital likelihood evaluation. | Flags `NON_DIGITAL_LIKELY`, halting DSP pipeline early. |
| **Digital Likelihood Gate** | `core/hypothesis.py:539` | $0.45$ | Combines spectral entropy, bandwidth ratio, and moment structure. | Marked `AMBIGUOUS` (proceeds cautiously to timing). | Marked `DIGITAL_SIGNAL_PLAUSIBLE` (proceeds with high prior). |
| **Viable Candidate Filter** | `core/receiver.py:663` | $0.30$ | Multi-level square constellations (16-QAM) have multi-metric products around $0.35$–$0.40$ even when clean. | Candidate is discarded from expensive downstream FEC/preamble search. | Candidate advances to downstream demodulation, preamble search, and FEC verification. |
| **Viterbi Metric Normalization** | `core/fec.py:208` | $0.08$ | Hard-decision Viterbi normalized branch metric $M_{\text{final}} / N_{\text{code}} \le 0.08$ represents $\le 8\%$ uncorrected channel bit errors. | `valid = True`, codec hypothesis validated with high score. | `valid = False`, treated as uncorrected raw bits. |
| **Preamble Match Threshold** | `core/correlation.py:116` | $0.80$ ($80\%$) | Allows up to $2$ bit errors on 32-bit CCSDS ASM or $1$ error on 16-bit AA55 under noisy channels. | Preamble rejected as random bit noise. | Preamble lock confirmed; sync offset and frame length extracted. |
| **Minimum Preamble Length** | `core/receiver.py:709` | $16\text{ bits}$ | Prevents short trivial sequences (e.g. 4-bit runs) from falsely promoting an unvalidated decoding hypothesis. | Treated as partial/unconfirmed preamble ($S_{\text{preamble}} = 0$). | Promotes hypothesis to Tier 1 / Tier 2 confidence scoring. |
| **Decision Gate Confidence** | `core/receiver.py:760` | $0.50$ | Minimum required confidence to assert a digital communication hypothesis. | Relegated to `UNKNOWN` (`INSUFFICIENT_EVIDENCE`). | Accepted as `ANALYSIS_COMPLETE`. |

---

## 3. Critical Reasoning Logic Verifications

### 1. Candidate Generation & Equal Opportunity
- **Finding:** Every candidate SPS recovered by `estimate_samples_per_symbol()` is tested across **all four supported modulation families** (BPSK, QPSK, 16-QAM, 2-FSK). Standard fallback grid $\{4, 8, 16\}$ is always appended.
- **Fairness:** No modulation family is given an architectural precedence in candidate generation.

### 2. Candidate Ranking Comparability
- **Finding:** PSK and FSK quality use envelope constancy and harmonic power, while 16-QAM uses grid variance and 4th-moment Gaussian scoring.
- **Risk Identified (Resolved in Phase 6):** 16-QAM's composite raw score ($\sim 0.38$) is naturally lower than constant-envelope BPSK ($\sim 0.85$) due to amplitude variations. Lowering the viable candidate threshold to $0.30$ allows 16-QAM to be evaluated in cross-stage validation where downstream zero-syndrome FEC and 32-bit preamble lock elevate it to $>90\%$ confidence.

### 3. Downstream Evidence Legitimate Confidence Promotion
- **Finding:** Physical layer clustering alone can only reach a maximum confidence of $75\%$ (`MEDIUM CONFIDENCE`). Confidence can **only** cross into $85.0\% - 100.0\%$ (`HIGH CONFIDENCE`) when corroborated by **genuine downstream protocol lock** (zero-syndrome algebraic FEC and $\ge 16$-bit preamble match).
- **Legitimacy:** This prevents false high-confidence classifications on non-communicative clustering artifacts.

### 4. Gatekeeper Separation of UNKNOWN States
- The system distinguishes between distinct failure modes in `best_hypothesis['status']`:
  1. `NON_DIGITAL_REJECTED`: Signal is a pure tone or narrowband acoustic source (e.g. `1khz-sine.wav`).
  2. `INSUFFICIENT_EVIDENCE`: Signal is wideband noise or unmodulated acoustic speech (e.g. `DEMO_05_UNKNOWN_AUDIO.wav`).
  3. `INSUFFICIENT_DATA`: File buffer contains fewer than minimum required symbols.
  4. `ANALYSIS_COMPLETE`: Legitimate digital signal identified with verified parameters.
- **Conclusion:** UNKNOWN states are **not** silently conflated; explicit reasons are recorded in `best_hypothesis['why_selected']` and `best_hypothesis['reason']`.

### 5. Independence from Ground Truth
- In `core/fec.py`, `viterbi_decode` and `rs_decode` evaluate the actual bit sequence and check algebraic parity matrices ($H c^T \pmod 2 = 0$ and RS syndrome $= 0$).
- If noise or incorrect demodulation bits are fed in, syndromes fail algebraic verification and return `fec_valid = False` with zero score.
- Ground truth is neither imported nor referenced anywhere in `core/receiver.py`.

---

## 4. Counterexample Stress Testing & Edge Cases

| Scenario / Counterexample | Input Condition | Expected Behavior | Observed System Behavior | Vulnerability Assessment |
|---|---|---|---|---|
| **Continuous Sine Wave** | $1\text{ kHz}$ unmodulated tone (`1khz-sine.wav`) | Immediate gatekeeper rejection as `UNKNOWN` | Screen triggers `NON_DIGITAL_LIKELY`; skips downstream DSP; outputs `UNKNOWN` (0.0% conf) | **ROBUST (No false alarm)** |
| **Gaussian White Noise** | Synthetic random Gaussian samples | No modulation, no sync lock, `UNKNOWN` | Screening or modulation scoring evaluates to $0.0$; outputs `UNKNOWN` (0.0% conf) | **ROBUST (No false alarm)** |
| **Short Truncated Preamble** | 8-bit partial preamble match | Must NOT promote hypothesis to high confidence | $P_{\text{len}} = 8 < 16$ gate triggers; composite score receives zero preamble weight | **ROBUST (Immune to false lock)** |
| **Random Bitstream FEC Test** | Uniformly random bitstream input to `analyze_frame_hypotheses` | Must NOT validate RS or Viterbi | Viterbi metric exceeds $0.08$; RS throws `ReedSolomonError`; `fec_valid = False` | **ROBUST (Zero false validation)** |
| **Severe CFO Mistune ($\pm 500\text{ Hz}$)** | 25dB SNR with large frequency offset | Must recover carrier before demodulation | $M$-th power estimator tracks peak accurately; BER remains $0.000$ | **ROBUST** |

---

## 5. Logic Audit Findings & Severity Classification

| Issue / Finding | Severity | Description & Architectural Impact |
|---|---|---|
| **Tie-Breaker Rule in Cross-Stage Ranking** | **LOW** | If two modulations yield identical composite cross-scores (extremely rare in floating-point arithmetic), the sorting preserves the earlier candidate in the list. |
| **Multi-Level QAM Pre-Screen Sensitivity** | **LOW** | Clean 16-QAM constellations inherently yield lower raw compactness products ($0.35$–$0.40$) than single-circle PSK ($0.85$–$0.95$). Threshold of $0.30$ currently protects QAM candidates, but signals with extreme distortion ($<0.30$) rely on fallback candidates. |
| **Acoustic Voice Signals Entering Timing Search** | **INFO** | Speech signals with moderate formant bandwidth occasionally bypass the initial gatekeeper as `AMBIGUOUS`. However, they fail all constellation clustering checks ($S_{\text{mod}} = 0.000$) and are cleanly rejected at the Decision Gate as `UNKNOWN` with 0.0% confidence. |

---

## 6. Audit Verdict

The backend reasoning and hypothesis engine in AutoSig-Intel exhibits **defense-grade logical integrity**:
1. All candidate selections and ranking decisions derive from **multi-layer physical and mathematical evidence**.
2. Downstream protocol validation strictly protects against premature physical-layer misclassifications.
3. Negative and non-digital signals are cleanly rejected without polluting the digital hypothesis space.
4. Ground-truth metadata remains 100% isolated outside the inference pipeline.
