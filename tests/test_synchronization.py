import numpy as np

from core.reference_signals import (
    generate_bpsk,
    generate_qpsk,
    generate_16qam,
    generate_2fsk,
)

from core.synchronization import (
    apply_frequency_offset,
    apply_phase_offset,
    add_awgn,
    synchronize_psk,
    synchronize_qam,
    synchronize_fsk,
)

from core.demodulation import (
    demodulate_bpsk,
    demodulate_qpsk,
    demodulate_16qam,
    demodulate_2fsk,
    calculate_ber,
)
np.random.seed(42)

def print_result(
    name,
    expected,
    reference_bits,
    recovered_bits,
    synchronization
):

    ber = calculate_ber(
        reference_bits,
        recovered_bits
    )

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print(
        "Expected:",
        expected
    )

    print(
        "Recovered bits:",
        len(recovered_bits)
    )

    print(
        "BER:",
        ber
    )

    print(
        "Estimated frequency offset:",
        synchronization.get(
            "frequency_offset_hz"
        )
    )

    print(
        "Estimated timing offset:",
        synchronization.get(
            "timing_offset"
        )
    )

    if "phase_offset_rad" in synchronization:

        print(
            "Estimated phase offset:",
            synchronization[
                "phase_offset_rad"
            ]
        )

    if ber < 0.01:

        print(
            "RESULT: PASS"
        )

    else:

        print(
            "RESULT: NEEDS IMPROVEMENT"
        )


def test_bpsk():

    signal, bits, fs = generate_bpsk(
        num_symbols=2000,
        samples_per_symbol=8,
        noise_std=0.0,
        sample_rate=8000
    )

    # Add realistic impairments
    impaired = apply_frequency_offset(
        signal,
        fs,
        80
    )

    impaired = apply_phase_offset(
        impaired,
        np.deg2rad(35)
    )

    impaired = add_awgn(
        impaired,
        20
    )

    sync = synchronize_psk(
        impaired,
        fs,
        8,
        2
    )

    recovered = (
        demodulate_bpsk(
            sync["symbols"],
            1,
            0,
            0
        )
    )

    # sync["symbols"] are already symbol-spaced
    recovered = recovered[
        :len(bits)
    ]

    print_result(
        "BPSK WITH IMPAIRMENTS",
        "BPSK",
        bits,
        recovered,
        sync
    )


def test_qpsk():

    signal, bits, fs = generate_qpsk(
        num_symbols=2000,
        samples_per_symbol=8,
        noise_std=0.0,
        sample_rate=8000
    )

    impaired = apply_frequency_offset(
        signal,
        fs,
        100
    )

    impaired = apply_phase_offset(
        impaired,
        np.deg2rad(30)
    )

    impaired = add_awgn(
        impaired,
        20
    )

    sync = synchronize_psk(
        impaired,
        fs,
        8,
        4
    )

    recovered = (
        demodulate_qpsk(
            sync["symbols"],
            1,
            0,
            0
        )
    )

    recovered = recovered[
        :len(bits)
    ]

    print_result(
        "QPSK WITH IMPAIRMENTS",
        "QPSK",
        bits,
        recovered,
        sync
    )


def test_16qam():

    signal, bits, fs = generate_16qam(
        num_symbols=2000,
        samples_per_symbol=8,
        noise_std=0.0,
        sample_rate=8000
    )

    impaired = apply_frequency_offset(
        signal,
        fs,
        60
    )

    impaired = apply_phase_offset(
        impaired,
        np.deg2rad(20)
    )

    impaired = add_awgn(
        impaired,
        25
    )

    sync = synchronize_qam(
        impaired,
        fs,
        8
    )

    recovered = (
        demodulate_16qam(
            sync["symbols"],
            1,
            0,
            0
        )
    )

    recovered = recovered[
        :len(bits)
    ]

    print_result(
        "16-QAM WITH IMPAIRMENTS",
        "16-QAM",
        bits,
        recovered,
        sync
    )


def test_2fsk():

    signal, bits, fs = generate_2fsk(
        num_symbols=2000,
        samples_per_symbol=16,
        frequency_deviation=500,
        noise_std=0.0,
        sample_rate=16000
    )

    impaired = apply_frequency_offset(
        signal,
        fs,
        100
    )

    impaired = add_awgn(
        impaired,
        20
    )

    sync = synchronize_fsk(
        impaired,
        fs,
        16
    )

    # sync["symbols"] are symbol-spaced, but FSK
    # demodulator requires the sampled waveform.
    recovered = (
    demodulate_2fsk(
        sync["frequency_corrected_signal"],
        fs,
        16,
        sync["timing_offset"],
        frequency_threshold=
            sync[
                "fsk_decision_threshold_hz"
            ]
    )
)

    recovered = recovered[
        :len(bits)
    ]

    print_result(
        "2-FSK WITH IMPAIRMENTS",
        "2-FSK",
        bits,
        recovered,
        sync
    )


def main():

    test_bpsk()

    test_qpsk()

    test_16qam()

    test_2fsk()


if __name__ == "__main__":
    main()