import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import numpy as np
from core.receiver import analyze_signal

captures = [
    "capture_a_bpsk",
    "capture_b_qpsk",
    "capture_c_qpsk",
    "capture_d_16qam",
    "capture_e_2fsk",
]

print("=" * 80)
print("AUTOSIG-INTEL BLIND PAYLOAD RECOVERY VERIFICATION")
print("=" * 80)

for cap in captures:
    wav_path = f"samples/synthetic/{cap}.wav"
    json_path = f"samples/synthetic/{cap}_truth.json"
    with open(json_path) as f:
        meta = json.load(f)
    
    true_payload = np.array(meta["payload_bits"], dtype=np.uint8)
    res = analyze_signal(wav_path)
    frame_dec = res.get("decoding", {}).get("frame", {})
    fec_dec = res.get("decoding", {}).get("fec", {})
    int_dec = res.get("decoding", {}).get("interleaving", {})
    rec_payload = frame_dec.get("decoded_bits")
    
    rec_len = len(rec_payload) if rec_payload is not None else 0
    if rec_payload is not None and rec_len > 0:
        rec_arr = np.array(rec_payload, dtype=np.uint8)
        cmp_len = min(len(true_payload), rec_len)
        errs = int(np.sum(true_payload[:cmp_len] != rec_arr[:cmp_len]))
        ber = errs / cmp_len if cmp_len > 0 else 1.0
        exact_match = (errs == 0) and (rec_len == len(true_payload))
        print(f"[{cap}]")
        print(f"  Modulation : Inferred={res['modulation']} (True={meta['modulation']})")
        print(f"  SPS        : Inferred={res['samples_per_symbol']} (True={meta['samples_per_symbol']})")
        print(f"  FEC        : Inferred={fec_dec.get('best_hypothesis')} (Status={fec_dec.get('status')})")
        print(f"  Interleaver: Inferred={int_dec.get('best_hypothesis')}")
        print(f"  True Len   : {len(true_payload)} bits")
        print(f"  Rec Len    : {rec_len} bits")
        print(f"  Errors     : {errs} / {cmp_len}")
        print(f"  Payload BER: {ber:.6f}")
        print(f"  Exact Match: {exact_match}")
        print("-" * 80)
    else:
        print(f"[{cap}] No decoded bits returned!")
        print("-" * 80)
