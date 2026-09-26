import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.receiver import analyze_signal

files = [
    "capture_a_bpsk.wav",
    "capture_b_qpsk.wav",
    "capture_c_qpsk.wav",
    "capture_d_16qam.wav",
    "capture_e_2fsk.wav",
    "negative_pure_sine.wav",
    "negative_two_tone.wav",
    "negative_gaussian_noise.wav",
]

for name in files:
    path = Path("samples/synthetic") / name
    if not path.exists():
        continue
    print(f"\n>>> Processing {name}...", flush=True)
    t0 = time.time()
    res = analyze_signal(path)
    dt = time.time() - t0
    best = res.get("best_hypothesis", {})
    dec = res.get("decoding", {})
    fec = dec.get("fec", {})
    corr = dec.get("correlation", {})
    print(f"=== {name} ({dt:.2f}s) ===", flush=True)
    print(f"  Status:     {res.get('status')}", flush=True)
    print(f"  Modulation: {best.get('modulation')} (sps={best.get('samples_per_symbol')}, score={best.get('score', 0):.2f})", flush=True)
    print(f"  Preamble:   {corr.get('status')} | {corr.get('preamble', {}).get('pattern_type') if corr.get('preamble') else None}", flush=True)
    print(f"  Deinter:    {dec.get('interleaving', {}).get('best_hypothesis')} | {dec.get('interleaving', {}).get('status')}", flush=True)
    print(f"  FEC:        {fec.get('best_hypothesis')} | Valid={fec.get('fec_valid')} | Status={fec.get('status')}", flush=True)
    print(f"  Confidence: {res.get('confidence', 0):.2f}", flush=True)
