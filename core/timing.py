import numpy as np


# ============================================================
# UTILITIES
# ============================================================

def _normalize(x):
    x = np.asarray(x, dtype=np.complex64)

    power = np.mean(np.abs(x) ** 2)

    if power <= 1e-12:
        return x

    return x / np.sqrt(power)


def _robust_threshold(x, multiplier=6.0):
    x = np.asarray(x, dtype=np.float64)

    median = np.median(x)

    mad = np.median(
        np.abs(x - median)
    )

    sigma = 1.4826 * mad

    if sigma < 1e-12:
        return float(
            np.percentile(x, 90)
        )

    return float(
        median + multiplier * sigma
    )


# ============================================================
# NON-FSK SYMBOL-BOUNDARY DETECTION
# ============================================================

def _detect_signal_transitions(samples):

    x = _normalize(samples)

    if len(x) < 20:
        return np.array([], dtype=np.int64)

    difference = np.abs(
        np.diff(x)
    )

    threshold = _robust_threshold(
        difference,
        multiplier=4.0
    )

    # Prevent threshold from becoming too low.
    threshold = max(
        threshold,
        np.percentile(difference, 75)
    )

    transition_mask = (
        difference > threshold
    )

    positions = np.flatnonzero(
        transition_mask
    )

    if len(positions) < 3:
        return positions.astype(np.int64)

    # Collapse clusters of adjacent transition samples.
    groups = []

    start = positions[0]
    previous = positions[0]

    for position in positions[1:]:

        if position <= previous + 2:

            previous = position

        else:

            groups.append(
                (
                    start + previous
                ) // 2
            )

            start = position
            previous = position

    groups.append(
        (
            start + previous
        ) // 2
    )

    return np.asarray(
        groups,
        dtype=np.int64
    )


# ============================================================
# FSK TRANSITION DETECTION
# ============================================================

def _instantaneous_frequency(
    samples,
    sample_rate
):

    x = np.asarray(
        samples,
        dtype=np.complex64
    )

    if len(x) < 2:
        return np.array(
            [],
            dtype=np.float64
        )

    phase_difference = np.angle(
        x[1:] * np.conj(x[:-1])
    )

    return (
        phase_difference
        * sample_rate
        / (2 * np.pi)
    ).astype(np.float64)


def _detect_fsk_transitions(
    samples,
    sample_rate
):
    """
    Detect FSK symbol-state transitions from the
    instantaneous-frequency trajectory.

    Unlike PSK/QAM, FSK does not necessarily produce
    sharp complex-sample transitions because the phase
    is continuous. We therefore detect changes in the
    frequency discriminator output.
    """

    frequency = _instantaneous_frequency(
        samples,
        sample_rate
    )

    if len(frequency) < 20:
        return np.array([], dtype=np.int64)

    # Smooth discriminator noise.
    kernel_size = 5

    kernel = np.ones(
        kernel_size,
        dtype=np.float64
    ) / kernel_size

    smooth = np.convolve(
        frequency,
        kernel,
        mode="same"
    )

    # Estimate the two FSK frequency states.
    c1 = float(
        np.percentile(
            smooth,
            25
        )
    )

    c2 = float(
        np.percentile(
            smooth,
            75
        )
    )

    for _ in range(20):

        d1 = np.abs(
            smooth - c1
        )

        d2 = np.abs(
            smooth - c2
        )

        group1 = smooth[
            d1 <= d2
        ]

        group2 = smooth[
            d2 < d1
        ]

        if (
            len(group1) == 0
            or
            len(group2) == 0
        ):
            break

        new_c1 = float(
            np.median(group1)
        )

        new_c2 = float(
            np.median(group2)
        )

        if (
            abs(new_c1 - c1) < 1e-3
            and
            abs(new_c2 - c2) < 1e-3
        ):
            c1 = new_c1
            c2 = new_c2
            break

        c1 = new_c1
        c2 = new_c2

    threshold = (
        c1 + c2
    ) / 2.0

    # Convert frequency trajectory to binary states.
    state = (
        smooth >= threshold
    ).astype(np.int8)

    # Find state changes.
    changes = np.flatnonzero(
        state[1:] != state[:-1]
    ) + 1

    if len(changes) < 2:
        return changes.astype(np.int64)

    # Merge very closely spaced changes caused by noise.
    merged = []

    start = int(changes[0])
    previous = int(changes[0])

    minimum_gap = 2

    for position in changes[1:]:

        position = int(position)

        if position - previous <= minimum_gap:

            previous = position

        else:

            merged.append(
                (start + previous) // 2
            )

            start = position
            previous = position

    merged.append(
        (start + previous) // 2
    )

    return np.asarray(
        merged,
        dtype=np.int64
    )

# ============================================================
# CANDIDATE SPS SCORING
# ============================================================

def _score_candidate_sps(
    intervals,
    sps
):
    """
    Score how consistently transition intervals are
    integer multiples of a candidate SPS.
    """

    if len(intervals) == 0:
        return 0.0

    errors = []

    for interval in intervals:

        multiple = max(
            1,
            round(
                interval / sps
            )
        )

        expected = multiple * sps

        error = abs(
            interval - expected
        )

        normalized_error = (
            error / sps
        )

        errors.append(
            normalized_error
        )

    errors = np.asarray(
        errors
    )

    support = np.mean(
        errors <= 0.20
    )

    median_error = np.median(
        errors
    )

    # Strong support + low timing error.
    return float(
        support
        /
        (
            1.0
            +
            2.0 * median_error
        )
    )


# ============================================================
# SPS CANDIDATE GENERATION
# ============================================================

def _rank_sps_candidates(
    intervals,
    sample_rate,
    min_sps=2,
    max_sps=64
):

    if len(intervals) == 0:
        return []

    results = []

    for sps in range(
        min_sps,
        max_sps + 1
    ):

        score = _score_candidate_sps(
            intervals,
            sps
        )

        results.append(
            {
                "samples_per_symbol": int(
                    sps
                ),
                "symbol_rate_hz": float(
                    sample_rate / sps
                ),
                "score": float(
                    score
                )
            }
        )

    # Critical:
    #
    # If multiple candidates explain the intervals,
    # prefer the LARGEST candidate whose structural
    # support is strong. This avoids selecting 2, 4
    # when the true symbol length is 8.
    strong = [
        x
        for x in results
        if x["score"] >= 0.75
    ]

    if strong:

        strong.sort(
            key=lambda x: (
                -x["score"],
                -x["samples_per_symbol"]
            )
        )

        # Prefer the largest strongly supported SPS,
        # but retain score for confidence.
        best_sps = max(
    strong,
    key=lambda x: x[
        "samples_per_symbol"]
        )

        # Put the selected candidate first.
        results.sort(
            key=lambda x: (
                x is not best_sps,
                -x["score"]
            )
        )

    else:

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

    return results

def _fsk_quality_for_sps(
    samples,
    sample_rate,
    sps
):
    """
    Directly evaluate an SPS candidate using FSK
    frequency-state compactness.

    The correct SPS should make symbol-wise frequency
    measurements cluster tightly into two states.
    """

    frequency = _instantaneous_frequency(
        samples,
        sample_rate
    )

    if len(frequency) < sps * 20:
        return -np.inf

    best_score = -np.inf

    for offset in range(sps):

        available = len(frequency) - offset

        num_symbols = available // sps

        if num_symbols < 20:
            continue

        trimmed = frequency[
            offset:
            offset + num_symbols * sps
        ]

        blocks = trimmed.reshape(
            num_symbols,
            sps
        )

        # Robust average frequency per symbol.
        symbol_frequency = np.median(
            blocks,
            axis=1
        )

        # Two-state clustering.
        c1 = float(
            np.percentile(
                symbol_frequency,
                25
            )
        )

        c2 = float(
            np.percentile(
                symbol_frequency,
                75
            )
        )

        for _ in range(20):

            d1 = np.abs(
                symbol_frequency - c1
            )

            d2 = np.abs(
                symbol_frequency - c2
            )

            g1 = symbol_frequency[
                d1 <= d2
            ]

            g2 = symbol_frequency[
                d2 < d1
            ]

            if (
                len(g1) == 0
                or
                len(g2) == 0
            ):
                break

            c1 = float(np.median(g1))
            c2 = float(np.median(g2))

        separation = abs(
            c2 - c1
        )

        within_cluster = np.minimum(
            np.abs(
                symbol_frequency - c1
            ),
            np.abs(
                symbol_frequency - c2
            )
        )

        compactness = float(
            np.median(
                within_cluster
            )
        )

        if separation <= 1e-9:
            continue

        score = (
            separation
            /
            (
                compactness + 1e-9
            )
        )

        best_score = max(
            best_score,
            score
        )

    return float(best_score)


# ============================================================
# MAIN ESTIMATOR
# ============================================================

def estimate_samples_per_symbol(
    samples,
    sample_rate,
    min_symbol_rate=100.0,
    max_symbol_rate=None,
    modulation=None
):
    """
    Estimate symbol timing from signal-boundary structure.

    This is intentionally a hypothesis estimator, not a
    claim of universal blind symbol-rate recovery.
    """

    samples = np.asarray(
        samples,
        dtype=np.complex64
    )

    if len(samples) < 100:
        return []

    if max_symbol_rate is None:
        max_symbol_rate = sample_rate / 2.0

    min_sps = max(
        2,
        int(
            np.floor(
                sample_rate / max_symbol_rate
            )
        )
    )

    max_sps = min(
        128,
        int(
            np.ceil(
                sample_rate / min_symbol_rate
            )
        )
    )

    # --------------------------------------------------------
    # Modulation-specific transition extraction
    # --------------------------------------------------------

    if modulation == "2-FSK":

        transitions = _detect_fsk_transitions(
            samples,
            sample_rate
        )

        method = "FSK_frequency_transitions"

    else:

        transitions = _detect_signal_transitions(
            samples
        )

        method = "signal_transitions"

    if len(transitions) < 3:

        if modulation == "2-FSK":

        # Fall back to a direct symbol-rate search.
        #
        # This is particularly useful for continuous-phase
        # FSK where explicit transition detection may be sparse.

            results = []

            for sps in range(
            min_sps,
            max_sps + 1
            ):

                score = _fsk_quality_for_sps(
                samples,
                sample_rate,
                sps
                )

                if np.isfinite(score):

                    results.append(
                    {
                        "samples_per_symbol": int(sps),
                        "symbol_rate_hz": float(
                            sample_rate / sps
                        ),
                        "timing_offset": 0,
                        "timing_error": float(
                            1.0 / (score + 1e-12)
                        ),
                        "method": "FSK_frequency_structure",
                        "score": float(score),
                        "num_transitions": int(
                            len(transitions)
                        ),
                        "median_transition_interval": 0.0
                    }
                    )

            results.sort(
            key=lambda item: item["score"],
            reverse=True
            )

            return results

        return []

    intervals = np.diff(
        transitions
    )

    # Remove pathological very-short intervals.
    intervals = intervals[
        intervals >= min_sps
    ]

    if len(intervals) < 2:
        return []

    results = _rank_sps_candidates(
    intervals,
    sample_rate,
    min_sps=min_sps,
    max_sps=max_sps
    )

# Determine the best timing offset for every SPS candidate.
    for result in results:
        sps = result["samples_per_symbol"]

        best_offset = 0
        best_offset_error = np.inf

        for offset in range(sps):

            aligned_transitions = (
                transitions - offset
            )

            aligned_transitions = (
                aligned_transitions[
                    aligned_transitions >= 0
                ]
            )

            if len(aligned_transitions) < 3:
                continue

            remainders = np.mod(
                aligned_transitions,
                sps
            )

        # A correct symbol boundary should make
        # transition positions cluster around one
        # phase of the symbol clock.
            circular_error = np.minimum(
              remainders,
                sps - remainders
            )

            error = float(
                np.median(circular_error)
            )

            if error < best_offset_error:
                best_offset_error = error
                best_offset = offset

        result["timing_offset"] = int(
            best_offset
        )

        result["timing_error"] = float(
        best_offset_error
        )

        result["method"] = method

        result["num_transitions"] = int(
        len(transitions)
        )

        result["median_transition_interval"] = float(
        np.median(intervals)
        )

    return results