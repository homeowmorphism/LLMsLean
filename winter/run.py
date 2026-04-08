from dotenv import load_dotenv
from generate_concurrent import generate_concurrent
from verify import check_accuracy_all
from verify import verify_parallel
from sys import argv
import shutil
import os

load_dotenv("../.env")

# Low temperature keeps outputs deterministic / consistent across runs
_TEMP = 0.5

def generate_loop(data, model, amend, workers=4, loops=1, repair=False):
    """
    Run the generate-then-verify pipeline for `loops` total iterations.

    - data:    path to the source .jsonl dataset
    - amend:   if True, the model tries to fix its previous attempt (amend@k);
               otherwise it generates from scratch each iteration (pass@k)
    - repair:  if True, skip the initial generation from `data` and iterate
               directly on the existing output file (used to resume a run)
    """
    at = f"amend@{loops}" if amend else f"pass@{loops}"
    output = data.split(".jsonl")[0] + f"_{model}_{at}.jsonl"

    # sub tracks whether the first loop was already consumed by the initial
    # generation from `data`. In repair mode we skip that step and sub stays 0,
    # so all `loops` iterations run against the existing output.
    sub = 0
    if not repair:
        sub = 1  # the initial generation counts as the first loop
        generate_concurrent(data, output, model, _TEMP, False, workers)
        verify_parallel(output, output)
        print(check_accuracy_all(output))

    for i in range(loops - sub):
        r = generate_concurrent(output, output, model, _TEMP, amend, workers)
        if r == -1:
            # generate_concurrent signals -1 when there is nothing left to do
            return output
        verify_parallel(output, output)
        print(check_accuracy_all(output))

    print(output)
    return output


def copy_to_final(output):
    """Copy the output file to the Final Tests archive, warning if it already exists."""
    filename = output.split("/")[-1]
    if filename not in os.listdir("../data/Final Tests/"):
        shutil.copy(output, "../data/Final Tests/")
    else:
        print(f"Test already exists. Please check {output} and manually back up.")


def parse_run_args(cmd, argv, argc):
    """Parse the shared positional arguments used by --final and --repair."""
    if argc < 5:
        print(f"Error: {cmd} requires: <model> <amend: bool> <dataset: C|F> [<workers: int> <loops: int>]")
        exit(1)
    model = argv[2]
    amend = argv[3] == "True"
    dataset = "miniCTX" if argv[4] == "C" else "minif2f"
    workers = int(argv[5]) if argc >= 6 else 4
    loops = int(argv[6]) if argc >= 7 else 4
    return model, amend, dataset, workers, loops


if __name__ == "__main__":
    argc = len(argv)

    if argc < 2:
        # No command given at all
        print("Usage: python3 run.py <command> [args...]")
        print("Commands: --help, --gen, --verify, --final, --repair")
        exit(1)

    if argv[1] == "--help":
        print("Usage: python3 run.py <model: str> <amend: bool> [<workers: int> <loops: int>]")

    elif argv[1] == "--gen":
        # One-shot generation only, no verification
        if argc < 3:
            print("Error: --gen requires a model argument")
            exit(1)
        model = argv[2]
        workers = int(argv[3]) if argc >= 4 else 4
        output = f"../data/mini_minif2f_{model}.jsonl"
        generate_concurrent("../data/mini_minif2f.jsonl", output, model, _TEMP, False, workers)

    elif argv[1] == "--verify":
        # Re-run verification on an existing output file
        if argc < 3:
            print("Error: --verify requires a model argument")
            exit(1)
        model = argv[2]
        output = f"../data/mini_minif2f_{model}.jsonl"
        verify_parallel(output, output)
        print(check_accuracy_all(output))

    elif argv[1] in ("--final", "--repair"):
        # --final:  run the full pipeline from scratch and archive the result
        # --repair: resume an existing output file and archive after finishing
        model, amend, dataset, workers, loops = parse_run_args(argv[1], argv, argc)
        repair = argv[1] == "--repair"
        output = generate_loop(f"../data/{dataset}.jsonl", model, amend, workers, loops, repair)
        copy_to_final(output)

    else:
        # Legacy positional-arg interface: <model> <amend> [workers] [loops]
        if argc < 3:
            print(f"Error: Expected at least 3 arguments, got {argc}")
            print("Usage: python3 run.py <model: str> <amend: bool> [<workers: int> <loops: int>]")
            exit(1)
        model = argv[1]
        amend = argv[2] == "True"
        workers = int(argv[3]) if argc >= 4 else 4
        loops = int(argv[4]) if argc >= 5 else 1
        generate_loop("../data/mini_minif2f.jsonl", model, amend, workers, loops)
