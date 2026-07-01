import subprocess
import os

# parameter combinations
beta_options = [
    "-1.0,1.0",
    "-0.5,0.5",
    "-1.0,-0.5,0.5,1.0",
    "-0.9,0.9",
    "-1.0,-0.8,0.8,1.0"
]

base_dir = r"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\BERvsMSNR_different_beta"

for beta_map in beta_options:

    # Create the output directory if it doesn't exist
    output_dir = os.path.join(base_dir, beta_map)
    os.makedirs(output_dir, exist_ok=True)

    for i in range(10):

        source_file = os.path.join(output_dir, f"source_{i}.bin")
        encoded_file = os.path.join(output_dir, f"encoded_{i}.bin")
        decoded_file = os.path.join(output_dir, f"decoded_{i}.bin")

        cmd = [
            "python",
            "alpha_stable_generator.py",

            f"--beta-map-str={beta_map}",

            "--samples-per-symbol", str(500),
            "--L", str(20),
            "--source-file", source_file,
            "--encoded-file", encoded_file,
            "--decoded-file", decoded_file
        ]

        print("\nRUNNING:")
        print(" ".join(cmd))

        subprocess.run(cmd, check=True)

print("\nALL EXPERIMENTS FINISHED")