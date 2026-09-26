from pathlib import Path

import pandas as pd

from core.signal_loader import load_wav

from core.signal_analysis import (
    calculate_basic_parameters,
    estimate_peak_frequency,
    estimate_bandwidth,
    estimate_snr,
    estimate_noise_floor,
    analytic_features,
)

from core.visualization import (
    save_waveform,
    save_spectrum,
    save_spectrogram,
    save_constellation,
    save_instantaneous_frequency,
)


INPUT_DIR = Path("samples/wav")
RESULTS_DIR = Path("results")
PLOTS_DIR = RESULTS_DIR / "plots"


RESULTS_DIR.mkdir(
    exist_ok=True
)

PLOTS_DIR.mkdir(
    exist_ok=True
)


def analyze_file(path):

    signal_data = load_wav(path)

    samples = signal_data.samples
    sample_rate = signal_data.sample_rate

    parameters = calculate_basic_parameters(
        samples,
        sample_rate
    )

    peak_frequency = estimate_peak_frequency(
        samples,
        sample_rate
    )

    bandwidth = estimate_bandwidth(
        samples,
        sample_rate
    )

    noise_floor = estimate_noise_floor(
        samples,
        sample_rate
    )

    snr = estimate_snr(
        samples,
        sample_rate
    )

    # --------------------------------------------------
    # Analytic features
    # --------------------------------------------------

    try:

        features = analytic_features(
            samples,
            sample_rate
        )

    except ValueError:

        # Real signals are temporarily converted to
        # their analytic representation inside the
        # visualization stage, but we don't store
        # those features here yet.
        features = {}

    # --------------------------------------------------
    # Save plots
    # --------------------------------------------------

    prefix = path.stem

    save_waveform(
        samples,
        sample_rate,
        PLOTS_DIR / f"{prefix}_waveform.png",
        f"{prefix} - Waveform"
    )

    save_spectrum(
        samples,
        sample_rate,
        PLOTS_DIR / f"{prefix}_spectrum.png",
        f"{prefix} - Spectrum"
    )

    save_spectrogram(
        samples,
        sample_rate,
        PLOTS_DIR / f"{prefix}_spectrogram.png",
        f"{prefix} - Spectrogram"
    )

    save_constellation(
        samples,
        PLOTS_DIR / f"{prefix}_constellation.png",
        f"{prefix} - Analytic Constellation"
    )

    save_instantaneous_frequency(
        samples,
        sample_rate,
        PLOTS_DIR / f"{prefix}_instantaneous_frequency.png",
        f"{prefix} - Instantaneous Frequency"
    )

    # --------------------------------------------------
    # CSV result
    # --------------------------------------------------

    result = {
        "filename":
            path.name,

        "sample_rate_hz":
            sample_rate,

        "num_samples":
            signal_data.num_samples,

        "duration_seconds":
            parameters["duration"],

        "original_channels":
            signal_data.original_channels,

        "representation":
            signal_data.representation,

        "possible_iq":
            signal_data.possible_iq,

        "channel_correlation":
            signal_data.channel_correlation,

        "rms":
            parameters["rms"],

        "peak":
            parameters["peak"],

        "dc_offset":
            parameters["dc_offset"],

        "peak_frequency_hz":
            peak_frequency,

        "estimated_bandwidth_hz":
            bandwidth,

        "estimated_noise_floor_db":
            noise_floor,

        "estimated_snr_db":
            snr,

        "notes":
            " | ".join(signal_data.notes),
    }

    result.update(features)

    return result


def main():

    wav_files = sorted(
        INPUT_DIR.glob("*.wav")
    )

    if not wav_files:

        print(
            "ERROR: No WAV files found in:"
        )

        print(
            INPUT_DIR.resolve()
        )

        return

    print(
        f"Found {len(wav_files)} WAV files."
    )

    print()

    results = []

    failures = []

    for index, wav_file in enumerate(
        wav_files,
        start=1
    ):

        print(
            f"[{index}/{len(wav_files)}] "
            f"Analyzing {wav_file.name}..."
        )

        try:

            result = analyze_file(
                wav_file
            )

            results.append(result)

            print(
                f"    SUCCESS"
            )

            print(
                f"    Representation: "
                f"{result['representation']}"
            )

            print(
                f"    Possible IQ: "
                f"{result['possible_iq']}"
            )

        except Exception as error:

            failures.append({
                "filename":
                    wav_file.name,

                "error":
                    str(error)
            })

            print(
                f"    ERROR: {error}"
            )

    # --------------------------------------------------
    # Save summary
    # --------------------------------------------------

    if results:

        dataframe = pd.DataFrame(
            results
        )

        output_file = (
            RESULTS_DIR /
            "signal_summary.csv"
        )

        dataframe.to_csv(
            output_file,
            index=False
        )

        print()

        print(
            f"Completed "
            f"{len(results)} "
            f"of "
            f"{len(wav_files)} files."
        )

        print()

        print(
            f"Results saved to:"
        )

        print(
            output_file.resolve()
        )

        print()

        print(
            dataframe.to_string(
                index=False
            )
        )

    else:

        print()
        print(
            "No files were successfully analyzed."
        )

    # --------------------------------------------------
    # Save failures separately
    # --------------------------------------------------

    if failures:

        failure_file = (
            RESULTS_DIR /
            "analysis_errors.csv"
        )

        pd.DataFrame(
            failures
        ).to_csv(
            failure_file,
            index=False
        )

        print()

        print(
            f"Errors saved to:"
        )

        print(
            failure_file.resolve()
        )


if __name__ == "__main__":
    main()