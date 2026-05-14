import subprocess
import itertools

# parameter combinations
beta_options = [
    "-1.0,1.0",
    "0.0,1.0"
]

samples_options = [16, 24, 32, 500]
L_options = [4, 8]

run_id = 0

for beta_map, sps, L in itertools.product(
    beta_options,
    samples_options,
    L_options
):

    run_id += 1

    source_file = rf"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\source_{run_id}.bin"
    encoded_file = rf"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\encoded_{run_id}.bin"
    decoded_file = rf"C:\Users\ANEDCD~1\Desktop\3.letnik\Diploma\simulations\decoded_{run_id}.bin"

    cmd = [
        "python",
        "alpha_stable_generator.py",

        f"--beta-map-str={beta_map}",

        "--samples-per-symbol", str(sps),
        "--L", str(L),
        "--encoded-file", encoded_file,
        "--decoded-file", decoded_file
    ]

    print("\nRUNNING:")
    print(" ".join(cmd))

    subprocess.run(cmd)

print("\nALL EXPERIMENTS FINISHED")