import sys
from pathlib import Path
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.receiver import preprocess, test_psk_hypothesis, test_qam_hypothesis, test_fsk_hypothesis
from core.demodulation import demodulate_bpsk, demodulate_qpsk, demodulate_16qam, demodulate_2fsk
from core.frame import analyze_frame_hypotheses

def test_cap(name):
    data, fs = sf.read(f"samples/synthetic/{name}")
    c = data[:, 0] + 1j * data[:, 1]
    sig = preprocess(c)
    print(f"\n=== Testing {name} ===", flush=True)
    for sps in [4, 8, 16]:
        # Test PSK
        for order, mod, demod_fn in [(2, "BPSK", demodulate_bpsk), (4, "QPSK", demodulate_qpsk)]:
            h = test_psk_hypothesis(sig, fs, sps, order)
            if h.get("score", 0) >= 0.40:
                bits = demod_fn(h["symbols"], 1, 0, 0.0)
                rep = analyze_frame_hypotheses(bits, mod)
                best_dec = rep.get("best_decoding_hypothesis", {})
                p_type = rep.get("preamble", {}).get("pattern_type") if rep.get("preamble") else "None"
                p_len = rep.get("preamble", {}).get("pattern_length", 0) if rep.get("preamble") else 0
                print(f"  sps={sps} {mod:6s}: score={h['score']:.2f} | Preamble={p_type}(len={p_len}) | FEC={best_dec.get('fec')} valid={best_dec.get('fec_valid')}", flush=True)

        # Test 16-QAM
        h_qam = test_qam_hypothesis(sig, fs, sps)
        if h_qam.get("score", 0) >= 0.40:
            bits = demodulate_16qam(h_qam["symbols"], 1, 0, 0.0)
            rep = analyze_frame_hypotheses(bits, "16-QAM")
            best_dec = rep.get("best_decoding_hypothesis", {})
            p_type = rep.get("preamble", {}).get("pattern_type") if rep.get("preamble") else "None"
            p_len = rep.get("preamble", {}).get("pattern_length", 0) if rep.get("preamble") else 0
            print(f"  sps={sps} 16-QAM: score={h_qam['score']:.2f} | Preamble={p_type}(len={p_len}) | FEC={best_dec.get('fec')} valid={best_dec.get('fec_valid')}", flush=True)

        # Test 2-FSK
        h_fsk = test_fsk_hypothesis(sig, fs, sps)
        if h_fsk.get("score", 0) >= 0.40:
            bits = demodulate_2fsk(h_fsk.get("frequency_corrected_signal", sig), fs, sps, h_fsk.get("timing_offset", 0))
            rep = analyze_frame_hypotheses(bits, "2-FSK")
            best_dec = rep.get("best_decoding_hypothesis", {})
            p_type = rep.get("preamble", {}).get("pattern_type") if rep.get("preamble") else "None"
            p_len = rep.get("preamble", {}).get("pattern_length", 0) if rep.get("preamble") else 0
            print(f"  sps={sps} 2-FSK : score={h_fsk['score']:.2f} | Preamble={p_type}(len={p_len}) | FEC={best_dec.get('fec')} valid={best_dec.get('fec_valid')}", flush=True)

for name in ["capture_a_bpsk.wav", "capture_b_qpsk.wav", "capture_c_qpsk.wav", "capture_d_16qam.wav", "capture_e_2fsk.wav"]:
    test_cap(name)
