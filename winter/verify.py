from tqdm import tqdm
from lean_interact import LeanREPLConfig, Command, AutoLeanServer
from lean_interact.pool import LeanServerPool
from lean_interact.project import TempRequireProject
import jsonlines as jsl
from lean_interact.interface import LeanError
import re
import math
import os


def verify_single_result(response, project):
    server = None
    try:
        config = LeanREPLConfig(project=project)
        server = AutoLeanServer(config)

        if "ERROR: Generation failed" in response:
            return "Generation failed, unable to verify"

        full_code = f"import Mathlib\n\n{response}"
        result = server.run(Command(cmd=full_code), timeout=20)
        if not isinstance(result, LeanError) and result.lean_code_is_valid() and len(result.sorries) == 0:
            return "Pass"
        errors = "; ".join(str(e) for e in result.get_errors())
        return f"Fail: {errors}"
    except TimeoutError:
        return "Unknown Error: LEAN Verification timed out"
    except Exception as e:
        return f"Verification Failed: {e}"
    finally:
        if server:
            server.kill()


def verify_parallel(input, output):
    theorems = list(jsl.open(input))
    try:
        print("Setting Up Temp Project")
        project = TempRequireProject(lean_version="v4.16.0", require="mathlib")
    except Exception as e:
        print(f"Exception: {e}")
        return

    t_list = []
    for theorem in theorems:
        clean_response = theorem["responses"][-1].replace("lean\n", "").strip()
        full_code = theorem["header"] + clean_response
        t_list.append(Command(cmd=full_code))

    try:
        config = LeanREPLConfig(project=project)
        pool = LeanServerPool(config)
    except Exception as e:
        print(e)

    try:
        r_list = pool.run_batch(t_list, show_progress=True, timeout_per_cmd=60)
        pool.close()
    except Exception as e:
        r_list = []
        print(e)

    for i, theorem in enumerate(theorems):
        if "verification" not in theorem:
            theorem["verification"] = []

        result = r_list[i]

        if isinstance(result, Exception):
            # Propagate a previous Pass through a timeout when in amend mode
            if "amend" in output and len(theorem["verification"]) > 0 and theorem["verification"][-1] == "Pass":
                theorem["verification"].append("Pass")
            else:
                theorem["verification"].append("Unknown Error: LEAN Verification timed out")
            theorem.setdefault("verify_time", []).append(-1)
            continue

        if not isinstance(result, LeanError) and result.lean_code_is_valid() and len(result.sorries) == 0:
            theorem["verification"].append("Pass")
        else:
            errors = "; ".join(str(e) for e in result.get_errors())
            theorem["verification"].append(f"Fail: {errors}")

        # Extract elaboration time from Lean's [Elab.command] message if present
        elapsed = 0
        for message in result.messages:
            m = re.search(r"\[Elab\.command\] \[([0-9]+\.[0-9]+)\]", message.data)
            if m:
                elapsed = float(m.group(1))
        theorem.setdefault("verify_time", []).append(elapsed)

    with jsl.open(output, mode="w") as writer:
        writer.write_all(theorems)


def check_accuracy_all(filepath):
    theorems = list(jsl.open(filepath))
    if "pass" not in os.path.basename(filepath):
        # Amend mode: return per-round accuracy as percentages (0–100).
        # Size the counts array from the first theorem that has verification data.
        verified = [t for t in theorems if "verification" in t]
        num_rounds = len(verified[0]["verification"]) if verified else 0
        counts = [0] * num_rounds
        total = len(theorems)
        for theorem in theorems:
            if "verification" not in theorem:
                total -= 1
            else:
                for i, result in enumerate(theorem["verification"]):
                    if i < num_rounds and "Pass" in result:
                        counts[i] += 1
        return [c * 100 / total for c in counts]
    else:
        # Pass@k mode: return unbiased pass@k estimates (0–1) for k = 1..n.
        # Formula: pass@k = 1 - C(n - c, k) / C(n, k)
        n = len(theorems[0]["verification"])
        totals = [0.0] * n
        for theorem in theorems:
            c = theorem["verification"].count("Pass")
            for k in range(1, n + 1):
                totals[k - 1] += 1 - math.comb(n - c, k) / math.comb(n, k)
        return [t / len(theorems) for t in totals]


if __name__ == "__main__":
    print(check_accuracy_all("../data/Final Tests/minif2f_gemini_lite_pass@4.jsonl"))
