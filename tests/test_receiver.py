import os
import json

from core.receiver import (
    analyze_signal,
    save_result_json
)


def main():

    wav_directory = (
        "samples/wav"
    )

    output_directory = (
        "results/receiver"
    )

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    files = sorted(
        [
            filename
            for filename in os.listdir(
                wav_directory
            )
            if filename.lower().endswith(
                ".wav"
            )
        ]
    )

    if not files:

        print(
            "No WAV files found."
        )

        return

    print()
    print(
        "=" * 75
    )
    print(
        "AUTOSIG-INTEL AUTOMATIC RECEIVER"
    )
    print(
        "=" * 75
    )

    for filename in files:

        path = os.path.join(
            wav_directory,
            filename
        )

        print()
        print(
            "-" * 75
        )
        print(
            f"FILE: {filename}"
        )
        print(
            "-" * 75
        )

        try:

            result = analyze_signal(
                path
            )

            print(
                f"Sample rate: "
                f"{result['sample_rate_hz']} Hz"
            )

            print(
                f"Duration: "
                f"{result['duration_seconds']:.3f} s"
            )

            print(
                f"Representation: "
                f"{result['representation']}"
            )

            print(
                f"Possible IQ: "
                f"{result['possible_iq']}"
            )

            char = result[
                "characterization"
            ]

            print(
                f"Dominant frequency: "
                f"{char['dominant_frequency_hz']:.2f} Hz"
            )

            print(
                f"Occupied bandwidth: "
                f"{char['occupied_bandwidth_hz']:.2f} Hz"
            )

            print()

            best = result[
                "best_hypothesis"
            ]

            if best:

                print(
                    "BEST HYPOTHESIS"
                )

                print(
                    f"Modulation: "
                    f"{best['modulation']}"
                )

                if best.get("samples_per_symbol") is not None:
                    print(
                        f"SPS: "
                        f"{best['samples_per_symbol']}"
                    )
                else:
                    print("SPS: N/A")

                if best.get("symbol_rate_hz") is not None:
                    print(
                        f"Symbol rate: "
                        f"{best['symbol_rate_hz']:.2f} baud"
                    )
                else:
                    print("Symbol rate: N/A")

                print(
                    f"Score: "
                    f"{best['score']:.4f}"
                )

                print(
                    f"Confidence: "
                    f"{result['confidence']:.2%}"
                )

                if (
                    "frequency_offset_hz"
                    in best
                ):

                    print(
                        f"Frequency offset: "
                        f"{best['frequency_offset_hz']:.2f} Hz"
                    )

            print()

            print(
                "TOP HYPOTHESES"
            )

            for index, hypothesis in enumerate(
                result[
                    "modulation_hypotheses"
                ][:5],
                start=1
            ):

                print(
                    f"{index}. "
                    f"{hypothesis['modulation']} | "
                    f"SPS={hypothesis['samples_per_symbol']} | "
                    f"score={hypothesis['score']:.4f}"
                )

            output_path = os.path.join(
                output_directory,
                filename.replace(
                    ".wav",
                    ".json"
                )
            )

            save_result_json(
                result,
                output_path
            )

            print(
                f"\nSaved: {output_path}"
            )

        except Exception as exc:

            print(
                f"ERROR: {exc}"
            )

    print()
    print(
        "=" * 75
    )
    print(
        "RECEIVER RUN COMPLETE"
    )
    print(
        "=" * 75
    )


if __name__ == "__main__":
    main()