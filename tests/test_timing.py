import numpy as np

from core.timing import (
    estimate_samples_per_symbol
)


def make_bpsk(
    num_symbols,
    sps
):
    rng = np.random.default_rng(42)

    symbols = rng.choice(
        [-1.0, 1.0],
        size=num_symbols
    )

    return np.repeat(
        symbols,
        sps
    ).astype(np.complex64)


def make_qpsk(
    num_symbols,
    sps
):
    rng = np.random.default_rng(42)

    phase_indices = rng.integers(
        0,
        4,
        num_symbols
    )

    symbols = np.exp(
        1j
        * phase_indices
        * np.pi / 2
    )

    return np.repeat(
        symbols,
        sps
    ).astype(np.complex64)


def make_16qam(
    num_symbols,
    sps
):
    rng = np.random.default_rng(42)

    levels = np.array(
        [-3, -1, 1, 3]
    )

    i = rng.choice(
        levels,
        num_symbols
    )

    q = rng.choice(
        levels,
        num_symbols
    )

    symbols = (
        i + 1j * q
    ) / np.sqrt(10)

    return np.repeat(
        symbols,
        sps
    ).astype(np.complex64)


def make_2fsk(
    num_symbols,
    sps,
    sample_rate
):
    rng = np.random.default_rng(42)

    bits = rng.integers(
        0,
        2,
        num_symbols
    )

    f1 = -800.0
    f2 = 800.0

    total_samples = (
        num_symbols * sps
    )

    result = np.zeros(
        total_samples,
        dtype=np.complex64
    )

    phase = 0.0

    index = 0

    for bit in bits:

        frequency = (
            f2
            if bit
            else f1
        )

        phase_step = (
            2
            * np.pi
            * frequency
            / sample_rate
        )

        for _ in range(sps):

            result[index] = (
                np.exp(1j * phase)
            )

            phase += phase_step

            index += 1

    return result


def run_test(
    name,
    signal,
    fs,
    expected_sps,
    modulation
):

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    candidates = estimate_samples_per_symbol(
        signal,
        fs,
        min_symbol_rate=fs / 32,
        max_symbol_rate=fs / 2,
        modulation=modulation
    )

    print(
        "Expected SPS:",
        expected_sps
    )

    print()

    for candidate in candidates[:10]:

        print(
    f"SPS={candidate['samples_per_symbol']}, "
    f"SR={candidate['symbol_rate_hz']:.2f} Hz, "
    f"offset={candidate.get('timing_offset', 0)}, "
    f"timing_error={candidate.get('timing_error', 0):.4f}, "
    f"method={candidate['method']}, "
    f"score={candidate['score']:.5f}"
    )

    if not candidates:

        print(
            "RESULT: FAIL"
        )

        return

    best = candidates[0]

    error = abs(
        best["samples_per_symbol"]
        - expected_sps
    )

    print()
    print(
        "Best SPS:",
        best["samples_per_symbol"]
    )

    print(
        "SPS error:",
        error
    )

    if error == 0:
        print(
            "RESULT: PASS"
        )
    else:
        print(
            "RESULT: NEEDS IMPROVEMENT"
        )


def main():

    fs = 8000
    sps = 8
    num_symbols = 2000

    bpsk = make_bpsk(
        num_symbols,
        sps
    )

    qpsk = make_qpsk(
        num_symbols,
        sps
    )

    qam = make_16qam(
        num_symbols,
        sps
    )

    fsk = make_2fsk(
        num_symbols,
        sps,
        fs
    )

    run_test(
        "BPSK",
        bpsk,
        fs,
        sps,
        "BPSK"
    )

    run_test(
        "QPSK",
        qpsk,
        fs,
        sps,
        "QPSK"
    )

    run_test(
        "16-QAM",
        qam,
        fs,
        sps,
        "16-QAM"
    )

    run_test(
        "2-FSK",
        fsk,
        fs,
        sps,
        "2-FSK"
    )


if __name__ == "__main__":
    main()