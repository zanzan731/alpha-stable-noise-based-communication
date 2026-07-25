import subprocess
import os
import argparse


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BINARY_DIFF_EXE = r"C:\Users\žan\Desktop\3.letnik\Diploma\binary_diff\x64\Debug\binary_diff.exe"
GRAPH_SCRIPT = os.path.join(SCRIPT_DIR, "graphs.py")
GRAPH_LOGARITHMIC_SCRIPT = os.path.join(SCRIPT_DIR, "graphs_logaritmic_scale.py")


def run_generator(beta_map, samples_per_symbol, L, output_dir, runs=100, noise_ratio=1.0, gama_map="1.0"):
    os.makedirs(output_dir, exist_ok=True)

    for i in range(1, runs + 1): #zaradi binary diff
        source_file = os.path.join(output_dir, f"source_{i}.bin")
        encoded_file = os.path.join(output_dir, f"encoded_{i}.bin")
        decoded_file = os.path.join(output_dir, f"decoded_{i}.bin")

        cmd = [
            "python",
            os.path.join(SCRIPT_DIR, "alpha_stable_generator.py"),
            f"--beta-map-str={beta_map}",
            f"--gama-map-str={gama_map}",
            "--samples-per-symbol", str(samples_per_symbol),
            "--L", str(L),
            "--noise-ratio", str(noise_ratio),
            "--source-file", source_file,
            "--encoded-file", encoded_file,
            "--decoded-file", decoded_file,
        ]

        print("\nRUNNING:")
        print(" ".join(cmd))
        subprocess.run(cmd, check=True)


def run_binary_diff(output_dir):
    if not os.path.exists(BINARY_DIFF_EXE):
        print(f"Skipping binary_diff.exe because it was not found: {BINARY_DIFF_EXE}")
        return

    print("\nRUNNING BINARY DIFF:")
    print(BINARY_DIFF_EXE)
    subprocess.run([BINARY_DIFF_EXE], cwd=output_dir, check=True)


def run_graphs():
    if not os.path.exists(GRAPH_SCRIPT):
        print(f"Skipping graphs because it was not found: {GRAPH_SCRIPT}")
        return

    print("\nRUNNING GRAPH GENERATION:")
    print(GRAPH_SCRIPT)
    subprocess.run(["python", GRAPH_SCRIPT], check=True)


def run_graphs_logarithmic():
    if not os.path.exists(GRAPH_LOGARITHMIC_SCRIPT):
        print(f"Skipping graphs because it was not found: {GRAPH_LOGARITHMIC_SCRIPT}")
        return

    print("\nRUNNING GRAPH(logarithmic) GENERATION:")
    print(GRAPH_LOGARITHMIC_SCRIPT)
    subprocess.run(["python", GRAPH_LOGARITHMIC_SCRIPT], check=True)


def run_different_beta():
    beta_options = [
        "-1.0,1.0",
        "-0.9,0.9",
        "-0.8,0.8",
        "-0.7,0.7",
        "-0.6,0.6",
        "-0.5,0.5",
        "-0.4,0.4",
        "-0.3,0.3",
        "-0.2,0.2",
        "-0.1,0.1"
    ]

    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_beta"
    for beta_map in beta_options:
        output_dir = os.path.join(base_dir, beta_map.replace(",", "_").replace("-", "m"))
        run_generator(beta_map, samples_per_symbol=1000, L=20, noise_ratio=0.0, output_dir=output_dir)
        run_binary_diff(output_dir)


def run_different_gama():
    gama_options = [
        "0.0398",
        "0.0501187",
        "0.0631",
        "0.07943",
        "0.1",
        "0.12589",
        "0.1585",
        "0.1995",
        "0.2512",
        "0.316227766"
    ]

    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_gama"
    for gama_map in gama_options:
        output_dir = os.path.join(base_dir, gama_map.replace(",", "_").replace("-", "m").replace(".", "p"))
        run_generator("-1.0,1.0", samples_per_symbol=1000, L=20, output_dir=output_dir, gama_map=gama_map, noise_ratio=0.1)
        run_binary_diff(output_dir)


def run_different_sample_size():
    sample_sizes = [16, 24, 32, 40, 80, 120, 200, 240, 320, 400, 800]
    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_sample_size"

    for sample_size in sample_sizes:
        output_dir = os.path.join(base_dir, str(sample_size))
        run_generator("-1.0,1.0", samples_per_symbol=sample_size, L=8, output_dir=output_dir)
        run_binary_diff(output_dir)

def run_different_sample_size_with_noise():
    sample_sizes = [16, 24, 32, 40, 80, 120, 200, 240, 320, 400, 800]
    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_sample_size_with_noise"

    for sample_size in sample_sizes:
        output_dir = os.path.join(base_dir, str(sample_size))
        run_generator("-1.0,1.0", samples_per_symbol=sample_size, L=8, noise_ratio=6.5, output_dir=output_dir)
        run_binary_diff(output_dir)


def run_different_noise_ratio():
    noise_ratios = [0.0, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_noise_ratio"

    for noise_ratio in noise_ratios:
        noise_tag = str(noise_ratio).replace(".", "p")
        output_dir = os.path.join(base_dir, f"noise_{noise_tag}")
        run_generator("-1.0,1.0", samples_per_symbol=64, L=8, output_dir=output_dir, noise_ratio=noise_ratio)
        run_binary_diff(output_dir)


def run_different_l_ratio():
    sample_sizes = [24]
    l_sizes = [1, 2, 3, 4, 6, 8, 12, 24]
    base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_L_K_ratio"

    for sample_size in sample_sizes:
        for L in l_sizes:
            if sample_size % L != 0:
                continue

            output_dir = os.path.join(base_dir, f"sample_{sample_size}_L_{L}")
            run_generator("-1.0,1.0", samples_per_symbol=sample_size, L=L, output_dir=output_dir)
            run_binary_diff(output_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment",
        choices=["all", "different_beta", "different_gama", "different_sample_size", "different_sample_size_with_noise", "different_noise_ratio", "different_l_ratio", "graphs"],
        help="Choose which experiment block to run.",
    )
    args = parser.parse_args()

    if args.experiment is None:
        print("Choose an experiment to run:")
        print("1 - all")
        print("2 - different_beta")
        print("3 - different_gama")
        print("4 - different_sample_size")
        print("5 - different_sample_size_with_noise")
        print("6 - different_noise_ratio")
        print("7 - different_l_ratio")
        print("8 - graphs")
        print("9 - graphs_logarithmic")
        choice = input("Enter choice: ").strip()

        menu = {
            "1": "all",
            "2": "different_beta",
            "3": "different_gama",
            "4": "different_sample_size",
            "5": "different_sample_size_with_noise",
            "6": "different_noise_ratio",
            "7": "different_l_ratio",
            "8": "graphs",
            "9": "graphs_logarithmic",
        }
        args.experiment = menu.get(choice, "all")

    if args.experiment in ("all", "different_beta"):
        run_different_beta()

    if args.experiment in ("all", "different_gama"):
        run_different_gama()

    if args.experiment in ("all", "different_sample_size"):
        run_different_sample_size()

    if args.experiment in ("all", "different_sample_size_with_noise"):
        run_different_sample_size_with_noise()

    if args.experiment in ("all", "different_noise_ratio"):
        run_different_noise_ratio()

    if args.experiment in ("all", "different_l_ratio"):
        run_different_l_ratio()
   
    if args.experiment == "graphs":
        run_graphs()
    if args.experiment == "graphs_logarithmic":
        run_graphs_logarithmic()
    

    print("\nALL EXPERIMENTS FINISHED")


if __name__ == "__main__":
    main()