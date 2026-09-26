import numpy as np


def generate_bpsk(
    num_symbols=2000,
    samples_per_symbol=8,
    noise_std=0.02,
    sample_rate=8000
):

    bits = np.random.randint(
        0,
        2,
        num_symbols
    )

    symbols = (
        2 * bits - 1
    ).astype(np.float32)

    waveform = np.repeat(
        symbols,
        samples_per_symbol
    )

    waveform = waveform.astype(
        np.complex64
    )

    noise = (
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
        +
        1j
        *
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
    )

    waveform += noise.astype(
        np.complex64
    )

    return waveform, bits, sample_rate


def generate_qpsk(
    num_symbols=2000,
    samples_per_symbol=8,
    noise_std=0.02,
    sample_rate=8000
):

    bits = np.random.randint(
        0,
        2,
        num_symbols * 2
    )

    pairs = bits.reshape(
        -1,
        2
    )

    mapping = {
        (0, 0): 1 + 1j,
        (0, 1): -1 + 1j,
        (1, 1): -1 - 1j,
        (1, 0): 1 - 1j
    }

    symbols = np.array(
        [
            mapping[
                tuple(pair)
            ]
            for pair in pairs
        ],
        dtype=np.complex64
    )

    symbols /= np.sqrt(2)

    waveform = np.repeat(
        symbols,
        samples_per_symbol
    )

    noise = (
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
        +
        1j
        *
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
    )

    waveform += noise.astype(
        np.complex64
    )

    return waveform, bits, sample_rate


def generate_16qam(
    num_symbols=2000,
    samples_per_symbol=8,
    noise_std=0.02,
    sample_rate=8000
):

    bits = np.random.randint(
        0,
        2,
        num_symbols * 4
    )

    groups = bits.reshape(
        -1,
        4
    )

    # Gray-style 4-PAM levels
    levels = {
        (0, 0): -3,
        (0, 1): -1,
        (1, 1): 1,
        (1, 0): 3
    }

    symbols = []

    for group in groups:

        i = levels[
            tuple(group[:2])
        ]

        q = levels[
            tuple(group[2:])
        ]

        symbols.append(
            i + 1j * q
        )

    symbols = np.asarray(
        symbols,
        dtype=np.complex64
    )

    symbols /= np.sqrt(
        np.mean(
            np.abs(symbols) ** 2
        )
    )

    waveform = np.repeat(
        symbols,
        samples_per_symbol
    )

    noise = (
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
        +
        1j
        *
        np.random.normal(
            0,
            noise_std,
            len(waveform)
        )
    )

    waveform += noise.astype(
        np.complex64
    )

    return waveform, bits, sample_rate


def generate_2fsk(
    num_symbols=2000,
    samples_per_symbol=16,
    frequency_deviation=500,
    noise_std=0.02,
    sample_rate=16000
):

    bits = np.random.randint(
        0,
        2,
        num_symbols
    )

    frequencies = np.where(
        bits == 0,
        -frequency_deviation,
        frequency_deviation
    )

    total_samples = (
        num_symbols
        *
        samples_per_symbol
    )

    waveform = np.zeros(
        total_samples,
        dtype=np.complex64
    )

    phase = 0.0

    sample_index = 0

    for symbol_frequency in frequencies:

        for _ in range(
            samples_per_symbol
        ):

            phase += (
                2
                *
                np.pi
                *
                symbol_frequency
                /
                sample_rate
            )

            waveform[
                sample_index
            ] = np.exp(
                1j * phase
            )

            sample_index += 1

    noise = (
        np.random.normal(
            0,
            noise_std,
            total_samples
        )
        +
        1j
        *
        np.random.normal(
            0,
            noise_std,
            total_samples
        )
    )

    waveform += noise.astype(
        np.complex64
    )

    return waveform, bits, sample_rate