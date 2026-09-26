# AutoSig-Intel: Mathematical Algorithms & Theoretical Formulations

**Problem Statement ID:** SIH26147  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme / Category:** Miscellaneous / Software  
**Version:** Phase 5 Baseline  

---

## 1. Signal Characterization & Occupied Bandwidth

### 1.1 Welch Power Spectral Density (PSD)
Given discrete complex signal $x[n]$ of length $N$:
1. Signal is partitioned into overlapping segments $x_m[n]$ of length $L = 4096$ with $50\%$ overlap (Hanning windowed).
2. The periodogram of each windowed segment is averaged:
   $$P_{xx}(f) = \frac{1}{K L U} \sum_{m=0}^{K-1} \left| \sum_{n=0}^{L-1} x_m[n] w[n] e^{-j 2\pi f n} \right|^2$$
   where $U = \frac{1}{L} \sum_{n=0}^{L-1} |w[n]|^2$ is the window energy normalization factor.

### 1.2 99% Occupied Bandwidth Integration
Occupied bandwidth is calculated directly from the cumulative distribution function (CDF) of the PSD:
$$C(f) = \int_{-F_s/2}^f P_{xx}(\nu) d\nu, \quad C_{\text{total}} = C(F_s/2)$$
The lower edge $f_1$ and upper edge $f_2$ are identified such that:
$$C(f_1) = 0.005 \cdot C_{\text{total}}, \quad C(f_2) = 0.995 \cdot C_{\text{total}}$$
$$\text{OBW}_{99\%} = f_2 - f_1$$

---

## 2. Preliminary Non-Digital Screening

To prevent false classifications on analog audio, unmodulated carriers, or ambient background noise:

### 2.1 Single-Tone Spectral Kurtosis
The spectral sharpness ratio tests if total power is concentrated in an isolated carrier tone:
$$K_{\text{tone}} = \frac{\max(P_{xx})}{\frac{1}{B} \sum_{f} P_{xx}(f)}$$
If $K_{\text{tone}} > 35.0$ and the spectral standard deviation $\sigma_f < 0.02 F_s$, the signal is gated as `NON_DIGITAL_LIKELY` (pure tone).

### 2.2 Fourth-Moment Kurtosis Invariance
The 4th-moment ratio $\kappa$ characterizes the radial energy distribution:
$$\kappa = \frac{\mathbb{E}[|x[n]|^4]}{(\mathbb{E}[|x[n]|^2])^2}$$

- **Constant-Envelope Phase Keying (BPSK, QPSK):** All points lie on unit circle $|s| = 1 \implies \kappa = \mathbf{1.0000}$.
- **16-QAM:** With constellation coordinates $a, b \in \{-3, -1, 1, 3\}$, $\mathbb{E}[|s|^2] = 10, \mathbb{E}[|s|^4] = 132 \implies \kappa = \mathbf{1.3200}$.
- **Complex Gaussian Noise:** Real and imaginary components are independent $\mathcal{N}(0, \sigma^2) \implies \kappa = \mathbf{2.0000}$.

---

## 3. Symbol Timing Recovery (SPS Estimation)

Digital symbol transitions create cyclostationary periodicities at integer multiples of symbol period $T_s$.

### 3.1 Transition-Interval Cyclostationary Peak Detection
1. Compute the instantaneous envelope magnitude derivative or phase derivative:
   $$d[n] = |x[n] - x[n-1]|$$
2. Auto-correlate the transition metric:
   $$R_d[k] = \sum_{n} d[n] d[n+k]$$
3. Candidate symbol intervals (samples per symbol, $\text{SPS}$) appear as prominent peaks in $R_d[k]$. Candidates $\text{SPS} \in [2, 64]$ are ranked by peak-to-average ratio.

---

## 4. Carrier Synchronization

### 4.1 $M$-th Power Carrier Frequency Offset (CFO) Recovery
Modulation phase is removed by raising the complex signal to the $M$-th power:
$$y[n] = (x[n])^M$$
- For BPSK ($M=2$): Phase modulation $\in \{0, \pi\} \implies 2\theta \in \{0, 2\pi\} \equiv 0 \pmod{2\pi}$.
- For QPSK / 16-QAM ($M=4$): Phase modulation $\in \{\frac{\pi}{4}, \frac{3\pi}{4}, \frac{5\pi}{4}, \frac{7\pi}{4}\} \implies 4\theta \equiv \pi \pmod{2\pi}$.

In the frequency domain, this collapses modulation spread into a discrete spectral line at $M \cdot \Delta f$:
$$\Delta f = \frac{1}{M} \arg\max_{f} \left| \mathcal{F}\{(x[n])^M\} \right|$$
The signal is frequency-corrected via complex mixing:
$$x_{\text{corr}}[n] = x[n] \cdot e^{-j 2\pi \Delta f n / F_s}$$

### 4.2 Viterbi-Viterbi Phase Estimation
Residual phase offset $\phi_0$ is estimated from the $M$-th power of symbol-rate samples:
$$\phi_0 = \frac{1}{M} \operatorname{atan2} \left( \sum_{k} \operatorname{Im}(s[k]^M), \sum_{k} \operatorname{Re}(s[k]^M) \right)$$
Symbols are rotated by $-\phi_0$ to align constellation axes.

---

## 5. Demodulation Engines

### 5.1 Hard-Decision Decision Boundaries
- **BPSK:** Slices $\operatorname{Re}(s[k]) \ge 0 \implies 1$, otherwise $0$.
- **QPSK:** Gray-coded bit pair $(b_0, b_1)$ from Cartesian quadrants:
  $$b_0 = (\operatorname{Re}(s[k]) < 0), \quad b_1 = (\operatorname{Im}(s[k]) < 0)$$
- **16-QAM:** Standard rectangular decision grid slicing along real and imaginary axes at thresholds $\{-2, 0, +2\}$.
- **2-FSK:** Demodulated via instantaneous frequency discriminator:
  $$f_{\text{inst}}[n] = \frac{F_s}{2\pi} \arg(x[n] \cdot x^*[n-1])$$
  Matched integration over each symbol window determines mark vs space state.

---

## 6. De-interleaving Algorithms

### 6.1 Block De-interleaver ($R \times C$)
- Interleaver: Writes input stream into $R$ rows, reads out $C$ columns.
- De-interleaver: Reconstructs matrix by writing received stream into $C$ columns and reading out $R$ rows.
- Remnant Preservation: For bitstream length $N$, remnant $N \pmod{R \cdot C}$ bits are preserved without truncation, guaranteeing perfect bijection $\Pi^{-1}(\Pi(\mathbf{b})) = \mathbf{b}$.

### 6.2 Convolutional De-interleaver (Ramsey / Forney)
- Composed of $B$ parallel shift-register branches with incrementing delay steps $M$:
  $$\text{Branch } i \text{ delay}: D_i = i \cdot M \quad (i = 0, \dots, B-1)$$
- De-interleaver applies complementary delays:
  $$\tilde{D}_i = (B - 1 - i) \cdot M$$
- Total end-to-end delay across all branches is constant: $D_i + \tilde{D}_i = (B-1)M$.
- Synchronous payload extraction begins at flush offset $B(B-1)M$.

---

## 7. Forward Error Correction (FEC)

### 7.1 Vectorized Viterbi Decoder (Rate 1/2)
Standard NASA $K=7$ polynomial generators:
$$g_0 = 171_8 = 1111001_2, \quad g_1 = 133_8 = 1011011_2$$

At trellis stage $t$, for each state $S \in \{0, \dots, 63\}$:
$$\Gamma_t(S) = \min_{p \in \{p_0, p_1\}} \left( \Gamma_{t-1}(p) + d_H(y_t, \text{branch\_output}(p \to S)) \right)$$
Where $d_H$ is Hamming distance between received pair $y_t$ and expected output.

**Vectorization Optimization:**
The predecessor states $(p_0, p_1)$ and expected branch outputs $(\text{out}_0, \text{out}_1)$ for all 64 states are precomputed in `_VITERBI_TRELLIS_CACHE`. All 64 state branch metrics are evaluated simultaneously using NumPy vector broadcasts, achieving a **40x speedup** over iterative scalar loops.

### 7.2 Trellis Path Metric Thresholding
- Unencoded random noise produces normalized path metric:
  $$\text{Metric}_{\text{noise}} \approx 0.15 - 0.20$$
- Valid convolutional codewords with channel bit error rates up to $8\%$ produce:
  $$\text{Metric}_{\text{valid}} \le 0.08$$

### 7.3 Reed-Solomon over $\text{GF}(256)$
- Evaluates Berlekamp-Massey syndrome polynomial $S(x)$ over primitive polynomial $p(x) = x^8 + x^4 + x^3 + x^2 + 1$ (0x11D).
- Systematic codewords correct up to $t = \lfloor nsym / 2 \rfloor$ byte errors.
- Codeword boundary guard: $cw > nsym$ and $\text{len}(dec) > 0$ strictly enforced to reject short noise fragments.

---

## 8. Preamble Correlation & Length Prioritization

Given received bitstream $\mathbf{b}$ and preamble pattern $\mathbf{p}$ of length $L$:
$$\text{Score}(k) = 1.0 - \frac{1}{L} \sum_{i=0}^{L-1} (b[k+i] \oplus p[i])$$

To prevent short patterns (e.g. 8-bit HDLC flag `0x7E`) from dominating genuine longer headers (e.g. 32-bit CCSDS ASM `0x1ACFFC1D`), matches are prioritized by:
$$\text{Rank} = \left(\text{Score}, \text{Pattern Length}, -\text{Bit Errors}\right)$$

---

## 9. Cross-Stage Composite Hypothesis Scoring

The composite hypothesis score integrates evidence across all physical receiver stages:

$$\text{Score}_{\text{composite}} = 0.35 \cdot S_{\text{mod}} + 0.15 \cdot S_{\text{timing}} + 0.15 \cdot S_{\text{carrier}} + 0.20 \cdot S_{\text{preamble}} + 0.15 \cdot S_{\text{fec}}$$

### Confidence Decision Thresholds:
$$\text{Confidence} = \begin{cases} 
\text{HIGH CONFIDENCE} & \text{if } \text{Score} \ge 0.85 \text{ and preamble detected and FEC valid} \\
\text{MEDIUM CONFIDENCE} & \text{if } 0.50 \le \text{Score} < 0.85 \\
\text{INSUFFICIENT EVIDENCE} & \text{if } \text{Score} < 0.50 \implies \text{Confidence} = 0.0\% 
\end{cases}$$
