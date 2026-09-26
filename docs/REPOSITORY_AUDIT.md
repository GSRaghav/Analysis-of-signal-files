# AutoSig-Intel: Comprehensive Repository & Filesystem Audit

**Project**: AutoSig-Intel (SIH 2026 Problem Statement SIH26147)

**Organization**: National Technical Research Organisation (NTRO)

**Audit Date**: September 2026

**Baseline Status**: Phase 6 Complete (145/145 Tests Passing)

---

## 1. Audit Overview & Methodology

Every file and directory in the local repository has been recursively inspected. Dependencies, imports, references, execution roles, and test requirements were traced to classify each item.

- **Total Audited Items**: 188
- **Classified to KEEP**: 117 items
- **Classified to REMOVE**: 71 items (caches, stale artifacts, regeneratable outputs)

---

## 2. Complete Filesystem Audit Inventory

| Path | Purpose | Dependencies / References | Classification | Action | Reason |
|---|---|---|---|---|---|
| `.gitignore` | Root configuration / entrypoint: .gitignore | Local development, execution, testing | **KEEP-PRODUCTION** | **KEEP** | Root project entrypoint, configuration, or documentation |
| `.pytest_cache/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `.pytest_cache/.gitignore` | Cached artifact: .gitignore | Python / pytest runtime | **REMOVE** | **REMOVE** | Python bytecode or test cache; regeneratable at runtime |
| `.pytest_cache/CACHEDIR.TAG` | Cached artifact: CACHEDIR.TAG | Python / pytest runtime | **REMOVE** | **REMOVE** | Python bytecode or test cache; regeneratable at runtime |
| `.pytest_cache/README.md` | Cached artifact: README.md | Python / pytest runtime | **REMOVE** | **REMOVE** | Python bytecode or test cache; regeneratable at runtime |
| `.pytest_cache/v/cache/nodeids` | Cached artifact: nodeids | Python / pytest runtime | **REMOVE** | **REMOVE** | Python bytecode or test cache; regeneratable at runtime |
| `__pycache__/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `__pycache__/main.cpython-313.pyc` | Cached artifact: main.cpython-313.pyc | Python / pytest runtime | **REMOVE** | **REMOVE** | Python bytecode or test cache; regeneratable at runtime |
| `app/__pycache__/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `app/__pycache__/gui.cpython-313.pyc` | Cached bytecode for gui.py | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `app/gui.py` | Main GUI application | core.*, streamlit, plotly, pandas, soundfile | **KEEP-PRODUCTION** | **KEEP** | Streamlit interactive GUI application for analysis and jury demo |
| `core/__init__.py` | Core processing module: __init__ | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/__pycache__/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `core/__pycache__/__init__.cpython-313.pyc` | Cached bytecode for __init__.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/correlation.cpython-313.pyc` | Cached bytecode for correlation.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/demodulation.cpython-313.pyc` | Cached bytecode for demodulation.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/fec.cpython-313.pyc` | Cached bytecode for fec.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/frame.cpython-313.pyc` | Cached bytecode for frame.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/hypothesis.cpython-313.pyc` | Cached bytecode for hypothesis.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/interleaving.cpython-313.pyc` | Cached bytecode for interleaving.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/preprocessing.cpython-313.pyc` | Cached bytecode for preprocessing.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/receiver.cpython-313.pyc` | Cached bytecode for receiver.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/reference_signals.cpython-313.pyc` | Cached bytecode for reference_signals.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/signal_analysis.cpython-313.pyc` | Cached bytecode for signal_analysis.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/signal_data.cpython-313.pyc` | Cached bytecode for signal_data.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/signal_loader.cpython-313.pyc` | Cached bytecode for signal_loader.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/synchronization.cpython-313.pyc` | Cached bytecode for synchronization.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/test_signal_generator.cpython-313.pyc` | Cached bytecode for test_signal_generator.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/timing.cpython-313.pyc` | Cached bytecode for timing.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/__pycache__/visualization.cpython-313.pyc` | Cached bytecode for visualization.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `core/correlation.py` | Core processing module: correlation | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/demodulation.py` | Core processing module: demodulation | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/fec.py` | Core processing module: fec | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/frame.py` | Core processing module: frame | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/hypothesis.py` | Core processing module: hypothesis | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/interleaving.py` | Core processing module: interleaving | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/preprocessing.py` | Core processing module: preprocessing | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/receiver.py` | Core processing module: receiver | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/reference_signals.py` | Core processing module: reference_signals | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/signal_analysis.py` | Core processing module: signal_analysis | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/signal_data.py` | Core processing module: signal_data | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/signal_loader.py` | Core processing module: signal_loader | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/synchronization.py` | Core processing module: synchronization | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/test_signal_generator.py` | Core processing module: test_signal_generator | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/timing.py` | Core processing module: timing | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `core/visualization.py` | Core processing module: visualization | Imported across core, app, tests, scripts | **KEEP-PRODUCTION** | **KEEP** | Core DSP and decoding engine module |
| `docs/ALGORITHMS.md` | Technical documentation: ALGORITHMS.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/ARCHITECTURE.md` | Technical documentation: ARCHITECTURE.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/CHANNEL_IMPAIRMENT_MATRIX.md` | Technical documentation: CHANNEL_IMPAIRMENT_MATRIX.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/FINAL_SIH_VALIDATION.md` | Technical documentation: FINAL_SIH_VALIDATION.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/FINAL_VALIDATION.md` | Technical documentation: FINAL_VALIDATION.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/PHASE5_REPORT.md` | Technical documentation: PHASE5_REPORT.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/PHASE6_REGRESSION_FIX_REPORT.md` | Technical documentation: PHASE6_REGRESSION_FIX_REPORT.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/PHASE6_REPORT.md` | Technical documentation: PHASE6_REPORT.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/REPOSITORY_AUDIT.md` | Technical documentation: REPOSITORY_AUDIT.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/SIH_FINAL_REQUIREMENT_AUDIT.md` | Technical documentation: SIH_FINAL_REQUIREMENT_AUDIT.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/SIH_STATUS.md` | Technical documentation: SIH_STATUS.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `docs/VALIDATION.md` | Technical documentation: VALIDATION.md | Developers, NTRO evaluators, jury | **KEEP-DOCUMENTATION** | **KEEP** | Authoritative technical documentation, audit, or validation report |
| `main.py` | Root configuration / entrypoint: main.py | Local development, execution, testing | **KEEP-PRODUCTION** | **KEEP** | Root project entrypoint, configuration, or documentation |
| `pytest.ini` | Root configuration / entrypoint: pytest.ini | Local development, execution, testing | **KEEP-PRODUCTION** | **KEEP** | Root project entrypoint, configuration, or documentation |
| `README.md` | Root configuration / entrypoint: README.md | Local development, execution, testing | **KEEP-PRODUCTION** | **KEEP** | Root project entrypoint, configuration, or documentation |
| `requirements.txt` | Root configuration / entrypoint: requirements.txt | Local development, execution, testing | **KEEP-PRODUCTION** | **KEEP** | Root project entrypoint, configuration, or documentation |
| `results/plots/` | Plot output directory | main.py | **REGENERATABLE** | **REMOVE** | Empty output directory; automatically recreated by main.py |
| `results/plots/1_spectrogram.png` | Generated analysis artifact: 1_spectrogram.png | main.py, tests/test_receiver.py | **REGENERATABLE** | **REMOVE** | Generated analysis output; cleanly regenerated by main.py / test_receiver.py |
| `results/plots/1_spectrum.png` | Generated analysis artifact: 1_spectrum.png | main.py, tests/test_receiver.py | **REGENERATABLE** | **REMOVE** | Generated analysis output; cleanly regenerated by main.py / test_receiver.py |
| `results/plots/1_waveform.png` | Generated analysis artifact: 1_waveform.png | main.py, tests/test_receiver.py | **REGENERATABLE** | **REMOVE** | Generated analysis output; cleanly regenerated by main.py / test_receiver.py |
| `samples/demo/DEMO_01_BPSK_VITERBI.wav` | Jury demonstration asset: DEMO_01_BPSK_VITERBI.wav | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_01_BPSK_VITERBI_f32.iq` | Jury demonstration asset: DEMO_01_BPSK_VITERBI_f32.iq | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_01_BPSK_VITERBI_truth.json` | Jury demonstration asset: DEMO_01_BPSK_VITERBI_truth.json | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_02_QPSK_RS.wav` | Jury demonstration asset: DEMO_02_QPSK_RS.wav | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_02_QPSK_RS_f32.iq` | Jury demonstration asset: DEMO_02_QPSK_RS_f32.iq | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_02_QPSK_RS_truth.json` | Jury demonstration asset: DEMO_02_QPSK_RS_truth.json | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_03_16QAM_CONCATENATED.wav` | Jury demonstration asset: DEMO_03_16QAM_CONCATENATED.wav | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_03_16QAM_CONCATENATED_f32.iq` | Jury demonstration asset: DEMO_03_16QAM_CONCATENATED_f32.iq | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_03_16QAM_CONCATENATED_truth.json` | Jury demonstration asset: DEMO_03_16QAM_CONCATENATED_truth.json | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_04_2FSK_VITERBI.wav` | Jury demonstration asset: DEMO_04_2FSK_VITERBI.wav | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_04_2FSK_VITERBI_f32.iq` | Jury demonstration asset: DEMO_04_2FSK_VITERBI_f32.iq | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_04_2FSK_VITERBI_truth.json` | Jury demonstration asset: DEMO_04_2FSK_VITERBI_truth.json | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_05_UNKNOWN_AUDIO.wav` | Jury demonstration asset: DEMO_05_UNKNOWN_AUDIO.wav | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/demo/DEMO_05_UNKNOWN_AUDIO_truth.json` | Jury demonstration asset: DEMO_05_UNKNOWN_AUDIO_truth.json | app/gui.py | **KEEP-DEMO** | **KEEP** | Official SIH jury demonstration dataset and ground truth |
| `samples/synthetic/capture_a_bpsk.wav` | Test fixture / golden capture: capture_a_bpsk.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_a_bpsk_f32.iq` | Test fixture / golden capture: capture_a_bpsk_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_a_bpsk_truth.json` | Test fixture / golden capture: capture_a_bpsk_truth.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_b_qpsk.wav` | Test fixture / golden capture: capture_b_qpsk.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_b_qpsk_f32.iq` | Test fixture / golden capture: capture_b_qpsk_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_b_qpsk_truth.json` | Test fixture / golden capture: capture_b_qpsk_truth.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_c_qpsk.wav` | Test fixture / golden capture: capture_c_qpsk.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_c_qpsk_f32.iq` | Test fixture / golden capture: capture_c_qpsk_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_c_qpsk_truth.json` | Test fixture / golden capture: capture_c_qpsk_truth.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_d_16qam.wav` | Test fixture / golden capture: capture_d_16qam.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_d_16qam_f32.iq` | Test fixture / golden capture: capture_d_16qam_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_d_16qam_truth.json` | Test fixture / golden capture: capture_d_16qam_truth.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_e_2fsk.wav` | Test fixture / golden capture: capture_e_2fsk.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_e_2fsk_f32.iq` | Test fixture / golden capture: capture_e_2fsk_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/capture_e_2fsk_truth.json` | Test fixture / golden capture: capture_e_2fsk_truth.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_16qam_viterbi.json` | Test fixture / golden capture: golden_16qam_viterbi.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_16qam_viterbi.wav` | Test fixture / golden capture: golden_16qam_viterbi.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_16qam_viterbi_f32.iq` | Test fixture / golden capture: golden_16qam_viterbi_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_16qam_viterbi_i16.iq` | Test fixture / golden capture: golden_16qam_viterbi_i16.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_2fsk_clean.json` | Test fixture / golden capture: golden_2fsk_clean.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_2fsk_clean.wav` | Test fixture / golden capture: golden_2fsk_clean.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_2fsk_clean_f32.iq` | Test fixture / golden capture: golden_2fsk_clean_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_2fsk_clean_i16.iq` | Test fixture / golden capture: golden_2fsk_clean_i16.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_bpsk_viterbi_block.json` | Test fixture / golden capture: golden_bpsk_viterbi_block.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_bpsk_viterbi_block.wav` | Test fixture / golden capture: golden_bpsk_viterbi_block.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_bpsk_viterbi_block_f32.iq` | Test fixture / golden capture: golden_bpsk_viterbi_block_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_bpsk_viterbi_block_i16.iq` | Test fixture / golden capture: golden_bpsk_viterbi_block_i16.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_qpsk_concatenated.json` | Test fixture / golden capture: golden_qpsk_concatenated.json | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_qpsk_concatenated.wav` | Test fixture / golden capture: golden_qpsk_concatenated.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_qpsk_concatenated_f32.iq` | Test fixture / golden capture: golden_qpsk_concatenated_f32.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/golden_qpsk_concatenated_i16.iq` | Test fixture / golden capture: golden_qpsk_concatenated_i16.iq | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/negative_gaussian_noise.wav` | Test fixture / golden capture: negative_gaussian_noise.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/negative_pure_sine.wav` | Test fixture / golden capture: negative_pure_sine.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/synthetic/negative_two_tone.wav` | Test fixture / golden capture: negative_two_tone.wav | tests/test_no_ground_truth.py, scripts/verify_payloads.py | **KEEP-TEST** | **KEEP** | Synthetic reference captures for blind receiver test suite |
| `samples/wav/1.wav` | Field audio recording: 1.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/1khz-sine.wav` | Field audio recording: 1khz-sine.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/2.wav` | Field audio recording: 2.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/3.wav` | Field audio recording: 3.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/4.wav` | Field audio recording: 4.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/5.wav` | Field audio recording: 5.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/6.wav` | Field audio recording: 6.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/7.wav` | Field audio recording: 7.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/8.wav` | Field audio recording: 8.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `samples/wav/9.wav` | Field audio recording: 9.wav | main.py, tests/test_receiver.py | **KEEP-DATA** | **KEEP** | Original problem statement field audio WAV files |
| `scripts/__pycache__/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `scripts/__pycache__/audit_repo.cpython-313.pyc` | Cached bytecode for audit_repo.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/eval_pipeline.cpython-313.pyc` | Cached bytecode for eval_pipeline.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/generate_blind_dataset.cpython-313.pyc` | Cached bytecode for generate_blind_dataset.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/generate_golden_datasets.cpython-313.pyc` | Cached bytecode for generate_golden_datasets.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/prepare_demo_dataset.cpython-313.pyc` | Cached bytecode for prepare_demo_dataset.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/sweep_channel_impairments.cpython-313.pyc` | Cached bytecode for sweep_channel_impairments.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/test_cross_stage.cpython-313.pyc` | Cached bytecode for test_cross_stage.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/verify_payloads.cpython-313.pyc` | Cached bytecode for verify_payloads.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/__pycache__/verify_reproducibility.cpython-313.pyc` | Cached bytecode for verify_reproducibility.cpython-313 | Python runtime | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `scripts/audit_repo.py` | Validation script: audit_repo | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/eval_pipeline.py` | Validation script: eval_pipeline | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/generate_blind_dataset.py` | Validation script: generate_blind_dataset | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/generate_golden_datasets.py` | Validation script: generate_golden_datasets | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/prepare_demo_dataset.py` | Validation script: prepare_demo_dataset | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/sweep_channel_impairments.py` | Validation script: sweep_channel_impairments | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/test_cross_stage.py` | Validation script: test_cross_stage | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/verify_payloads.py` | Validation script: verify_payloads | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `scripts/verify_reproducibility.py` | Validation script: verify_reproducibility | core.*, sys | **KEEP-VALIDATION** | **KEEP** | Validation / dataset generation utility script |
| `tests/__init__.py` | Unit/integration test suite: __init__ | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/__pycache__/` | Cache directory | None | **REMOVE** | **REMOVE** | Ephemeral runtime cache directory; safe to remove |
| `tests/__pycache__/__init__.cpython-313.pyc` | Cached bytecode for __init__.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_ambiguity_boundaries.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_ambiguity_boundaries.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_ambiguity_boundaries.cpython-313.pyc` | Cached bytecode for test_ambiguity_boundaries.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_blind_pipeline.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_blind_pipeline.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_blind_pipeline.cpython-313.pyc` | Cached bytecode for test_blind_pipeline.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_correlation.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_correlation.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_correlation.cpython-313.pyc` | Cached bytecode for test_correlation.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_decoding_pipeline.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_decoding_pipeline.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_decoding_pipeline.cpython-313.pyc` | Cached bytecode for test_decoding_pipeline.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_failure_recovery.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_failure_recovery.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_failure_recovery.cpython-313.pyc` | Cached bytecode for test_failure_recovery.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_fec.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_fec.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_fec.cpython-313.pyc` | Cached bytecode for test_fec.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_interleaving.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_interleaving.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_interleaving.cpython-313.pyc` | Cached bytecode for test_interleaving.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_no_ground_truth.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_no_ground_truth.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_no_ground_truth.cpython-313.pyc` | Cached bytecode for test_no_ground_truth.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_raw_iq.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_raw_iq.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_raw_iq.cpython-313.pyc` | Cached bytecode for test_raw_iq.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_receiver.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_receiver.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_receiver.cpython-313.pyc` | Cached bytecode for test_receiver.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_reference_signals.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_reference_signals.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_reference_signals.cpython-313.pyc` | Cached bytecode for test_reference_signals.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_robustness.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_robustness.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_robustness.cpython-313.pyc` | Cached bytecode for test_robustness.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_synchronization.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_synchronization.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_synchronization.cpython-313.pyc` | Cached bytecode for test_synchronization.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_timing.cpython-313-pytest-9.1.1.pyc` | Cached bytecode for test_timing.cpython-313-pytest-9.1.1 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/__pycache__/test_timing.cpython-313.pyc` | Cached bytecode for test_timing.cpython-313 | pytest | **REMOVE** | **REMOVE** | Python bytecode cache; regeneratable at runtime |
| `tests/test_ambiguity_boundaries.py` | Unit/integration test suite: test_ambiguity_boundaries | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_blind_pipeline.py` | Unit/integration test suite: test_blind_pipeline | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_correlation.py` | Unit/integration test suite: test_correlation | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_decoding_pipeline.py` | Unit/integration test suite: test_decoding_pipeline | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_failure_recovery.py` | Unit/integration test suite: test_failure_recovery | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_fec.py` | Unit/integration test suite: test_fec | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_interleaving.py` | Unit/integration test suite: test_interleaving | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_no_ground_truth.py` | Unit/integration test suite: test_no_ground_truth | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_raw_iq.py` | Unit/integration test suite: test_raw_iq | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_receiver.py` | Unit/integration test suite: test_receiver | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_reference_signals.py` | Unit/integration test suite: test_reference_signals | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_robustness.py` | Unit/integration test suite: test_robustness | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_synchronization.py` | Unit/integration test suite: test_synchronization | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |
| `tests/test_timing.py` | Unit/integration test suite: test_timing | pytest, core.* | **KEEP-TEST** | **KEEP** | Test suite module (145 tests regression baseline) |

---

## 3. Summary of Cleanup Actions

1. **Zero Production/Test Code Deletions**: No core DSP algorithms, tests, or validation scripts are removed.
2. **Preservation of Datasets**: All 10 problem statement WAV files in `samples/wav/`, all 5 official demo files in `samples/demo/`, and all 15 synthetic test captures in `samples/synthetic/` are retained.
3. **Cache & Bytecode Purge**: Ephemeral `.pyc` and `__pycache__` artifacts are cleared to ensure clean local state.
4. **Stale Artifact Removal**: Stale `results/receiver/test_signal.json` is purged.
5. **Clean Output Regeneration**: Output CSVs/JSONs in `results/` are cleared so that fresh local execution runs (`python main.py` and `python -m tests.test_receiver`) generate clean, authoritative outputs.
