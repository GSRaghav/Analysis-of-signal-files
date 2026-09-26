from core.reference_signals import (
    generate_bpsk,
    generate_qpsk,
    generate_16qam,
    generate_2fsk,
)

from core.demodulation import (
    demodulate_bpsk,
    demodulate_qpsk,
    demodulate_16qam,
    demodulate_2fsk,
    calculate_ber,
)


def report(
    name,
    expected_modulation,
    original_bits,
    recovered_bits
):

    ber = calculate_ber(
        original_bits,
        recovered_bits
    )

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print(
        "Expected modulation:",
        expected_modulation
    )

    print(
        "Original bits:",
        len(original_bits)
    )

    print(
        "Recovered bits:",
        len(recovered_bits)
    )

    print(
        "BER:",
        ber
    )

    if ber <= 0.001:

        print(
            "RESULT: PASS"
        )

    else:

        print(
            "RESULT: FAIL"
        )


def test_bpsk():

    signal, bits, fs = (
        generate_bpsk(
            num_symbols=2000,
            samples_per_symbol=8,
            noise_std=0.0,
            sample_rate=8000
        )
    )

    recovered = demodulate_bpsk(
        signal,
        samples_per_symbol=8,
        timing_offset=4
    )

    report(
        "BPSK DEMODULATION",
        "BPSK / PSK",
        bits,
        recovered
    )


def test_qpsk():

    signal, bits, fs = (
        generate_qpsk(
            num_symbols=2000,
            samples_per_symbol=8,
            noise_std=0.0,
            sample_rate=8000
        )
    )

    recovered = demodulate_qpsk(
        signal,
        samples_per_symbol=8,
        timing_offset=4
    )

    report(
        "QPSK DEMODULATION",
        "QPSK / PSK",
        bits,
        recovered
    )


def test_16qam():

    signal, bits, fs = (
        generate_16qam(
            num_symbols=2000,
            samples_per_symbol=8,
            noise_std=0.0,
            sample_rate=8000
        )
    )

    recovered = demodulate_16qam(
        signal,
        samples_per_symbol=8,
        timing_offset=4
    )

    report(
        "16-QAM DEMODULATION",
        "16-QAM / QAM",
        bits,
        recovered
    )


def test_2fsk():

    signal, bits, fs = (
        generate_2fsk(
            num_symbols=2000,
            samples_per_symbol=16,
            frequency_deviation=500,
            noise_std=0.0,
            sample_rate=16000
        )
    )

    recovered = demodulate_2fsk(
        signal,
        sample_rate=fs,
        samples_per_symbol=16,
        timing_offset=0,
        frequency_threshold=0.0
    )

    # FSK frequency decision may produce one fewer
    # sample because instantaneous frequency uses diff().
    recovered = recovered[
        :len(bits)
    ]

    report(
        "2-FSK DEMODULATION",
        "2-FSK / FSK",
        bits,
        recovered
    )


def main():

    test_bpsk()

    test_qpsk()

    test_16qam()

    test_2fsk()


if __name__ == "__main__":
    main()