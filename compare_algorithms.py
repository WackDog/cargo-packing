from __future__ import print_function

import argparse
import csv
import json
import os
import time

from alternative_algorithms import hill_climbing, simulated_annealing
from cargo_packing import genetic_algorithm, validate_solution
from container_instances import create_basic_instances, create_challenging_instances
from run_reference_instances import convert_instance, solution_record as reference_solution_record
from experiments import make_stress_problem


GA_CONFIG = {
    "population_size": 60,
    "generations": 250,
    "crossover_rate": 0.90,
    "mutation_rate": 0.25,
    "insertion_rate": 0.08,
    "elite_count": 4,
    "tournament_size": 4,
    "local_search_rate": 0.20,
    "local_search_attempts": 6,
    "include_heuristic_seeds": True,
}

HC_CONFIG = {
    "max_iterations": 4000,
    "restarts": 20,
    "stagnation_limit": 150,
    "insertion_probability": 0.30,
    "include_heuristic_starts": True,
}

SA_CONFIG = {
    "max_iterations": 6000,
    "initial_temperature": 600.0,
    "cooling_rate": 0.997,
    "minimum_temperature": 0.01,
    "insertion_probability": 0.30,
    "reheat_after": 700,
    "include_heuristic_start": False,
}


def mean(values):
    return None if not values else float(sum(values)) / float(len(values))


def median(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    m = n // 2
    if n % 2:
        return float(values[m])
    return (float(values[m - 1]) + float(values[m])) / 2.0


def run_algorithm(problem, algorithm, seed):
    start = time.time()
    if algorithm == "ga":
        result = genetic_algorithm(problem, seed=seed, verbose=False, **GA_CONFIG)
        step = result["generation"]
        display_name = "Genetic Algorithm"
    elif algorithm == "hc":
        result = hill_climbing(problem, seed=seed, verbose=False, **HC_CONFIG)
        step = result["step"]
        display_name = "Hill Climbing"
    elif algorithm == "sa":
        result = simulated_annealing(problem, seed=seed, verbose=False, **SA_CONFIG)
        step = result["step"]
        display_name = "Simulated Annealing"
    else:
        raise ValueError("Unknown algorithm: %s" % algorithm)

    elapsed = time.time() - start
    valid, messages = validate_solution(problem, result["solution"])
    return {
        "algorithm": algorithm,
        "algorithm_name": display_name,
        "seed": seed,
        "fitness": result["fitness"],
        "tie_break": result["tie_break"],
        "step": step,
        "runtime_seconds": elapsed,
        "success": bool(result["fitness"] == 0.0 and valid),
        "valid": valid,
        "validation_messages": messages,
        "order": list(result["order"]),
        "solution": result["solution"],
    }


def summarise(trials):
    successes = [t for t in trials if t["success"]]
    return {
        "runs": len(trials),
        "successes": len(successes),
        "success_rate": (float(len(successes)) / len(trials)) if trials else 0.0,
        "mean_runtime_seconds": mean([t["runtime_seconds"] for t in trials]),
        "median_runtime_seconds": median([t["runtime_seconds"] for t in trials]),
        "mean_step_to_solution": mean([t["step"] for t in successes]),
        "median_step_to_solution": median([t["step"] for t in successes]),
        "best_fitness": min([t["fitness"] for t in trials]) if trials else None,
        "mean_final_fitness": mean([t["fitness"] for t in trials]),
    }


def solution_record(instance, problem, trial, group):
    base = reference_solution_record(instance, {
        "fitness": trial["fitness"],
        "tie_break": trial["tie_break"],
        "order": trial["order"],
        "solution": trial["solution"],
        "generation": trial["step"],
        "history": [],
        "seed": trial["seed"],
    }, trial["runtime_seconds"])
    base["group"] = group
    base["algorithm"] = trial["algorithm"]
    base["algorithm_name"] = trial["algorithm_name"]
    base["runtime_seconds"] = trial["runtime_seconds"]
    base["search_step"] = trial["step"]
    return base


def main():
    parser = argparse.ArgumentParser(description="Compare GA, hill climbing and simulated annealing")
    parser.add_argument("--runs", type=int, default=20,
                        help="independent runs per algorithm per instance (default: 20)")
    parser.add_argument("--quick", action="store_true",
                        help="run 3 trials per algorithm per instance")
    parser.add_argument("--stress-scale", type=float, default=0.76,
                        help="scale factor for the derived stress instance (default: 0.76)")
    parser.add_argument("--no-stress", action="store_true",
                        help="skip the derived, non-official stress comparison")
    args = parser.parse_args()
    if args.quick:
        args.runs = 3

    groups = [
        ("basic", create_basic_instances()),
        ("challenging", create_challenging_instances()),
    ]
    algorithms = ["ga", "hc", "sa"]
    all_records = []
    best_solutions = []

    for group_name, instances in groups:
        for instance_index, instance in enumerate(instances):
            problem = convert_instance(instance)
            for algorithm_index, algorithm in enumerate(algorithms):
                trials = []
                for run_index in range(args.runs):
                    seed = (700000 + instance_index * 10000 +
                            algorithm_index * 1000 + run_index)
                    trials.append(run_algorithm(problem, algorithm, seed))

                summary = summarise(trials)
                best = min(trials,
                           key=lambda t: (0 if t["success"] else 1,
                                          t["fitness"], t["tie_break"],
                                          t["runtime_seconds"]))
                best_solutions.append(solution_record(instance, problem, best, group_name))
                all_records.append({
                    "group": group_name,
                    "instance": instance.name,
                    "algorithm": algorithm,
                    "algorithm_name": best["algorithm_name"],
                    "summary": summary,
                    "trials": [{k: v for k, v in t.items() if k != "solution"}
                               for t in trials],
                })
                print("%-34s %-20s %2d/%2d success, mean %.4fs" % (
                    instance.name, best["algorithm_name"],
                    summary["successes"], summary["runs"],
                    summary["mean_runtime_seconds"]))

    # The official instances are intentionally approachable and often solved
    # immediately by the decoder 
    # a derived stress case makes differences in search behaviour measurable. 
    if not args.no_stress:
        stress_problem = make_stress_problem(args.stress_scale)
        stress_name = "stress_%.2f_from_challenge_01" % args.stress_scale
        for algorithm_index, algorithm in enumerate(algorithms):
            trials = []
            for run_index in range(args.runs):
                seed = 950000 + algorithm_index * 1000 + run_index
                trials.append(run_algorithm(stress_problem, algorithm, seed))
            summary = summarise(trials)
            display_name = trials[0]["algorithm_name"] if trials else algorithm
            all_records.append({
                "group": "experimental",
                "instance": stress_name,
                "algorithm": algorithm,
                "algorithm_name": display_name,
                "summary": summary,
                "trials": [{k: v for k, v in t.items() if k != "solution"}
                           for t in trials],
                "note": "Derived from challenge_01_tight_packing; not an official assessment instance",
                "stress_scale": args.stress_scale,
            })
            print("%-34s %-20s %2d/%2d success, mean %.4fs" % (
                stress_name, display_name, summary["successes"], summary["runs"],
                summary["mean_runtime_seconds"]))

    out_dir = os.path.join(os.path.dirname(__file__), "results", "algorithm_comparison")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    with open(os.path.join(out_dir, "comparison.json"), "w") as handle:
        json.dump(all_records, handle, indent=2)
    with open(os.path.join(out_dir, "best_solutions.json"), "w") as handle:
        json.dump({"solutions": best_solutions}, handle, indent=2)

    csv_fields = ["group", "instance", "algorithm", "algorithm_name", "runs",
                  "successes", "success_rate", "mean_runtime_seconds",
                  "median_runtime_seconds", "mean_step_to_solution",
                  "median_step_to_solution", "best_fitness", "mean_final_fitness"]
    with open(os.path.join(out_dir, "comparison.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for record in all_records:
            row = {
                "group": record["group"],
                "instance": record["instance"],
                "algorithm": record["algorithm"],
                "algorithm_name": record["algorithm_name"],
            }
            row.update(record["summary"])
            writer.writerow(row)

    with open(os.path.join(out_dir, "summary.txt"), "w") as handle:
        handle.write("KV6018 Algorithm Comparison\n")
        handle.write("===========================\n\n")
        handle.write("All algorithms use the same order representation, placement decoder,\n")
        handle.write("fitness function and independent validity checker. Search-step counts\n")
        handle.write("are algorithm-specific, so runtime and success rate are the fairest\n")
        handle.write("cross-algorithm measures.\n")
        handle.write("The experimental stress case is derived from challenge_01 and is not an official assessment instance.\n\n")
        for record in all_records:
            s = record["summary"]
            step = "n/a" if s["mean_step_to_solution"] is None else "%.2f" % s["mean_step_to_solution"]
            handle.write("%-34s %-20s %2d/%2d (%6.2f%%), mean time %.4fs, mean step %s\n" % (
                record["instance"], record["algorithm_name"],
                s["successes"], s["runs"], 100.0 * s["success_rate"],
                s["mean_runtime_seconds"], step))

    print("\nResults written to %s" % out_dir)


if __name__ == "__main__":
    main()
