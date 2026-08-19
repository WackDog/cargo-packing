from __future__ import print_function

import argparse
import csv
import json
import os
import time

from cargo_packing import Problem, genetic_algorithm, validate_solution
from container_instances import create_basic_instances, create_challenging_instances
from run_reference_instances import convert_instance


DEFAULT_GA = {
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


def mean(values):
    if not values:
        return None
    return float(sum(values)) / float(len(values))


def median(values):
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    if n % 2:
        return float(ordered[middle])
    return (float(ordered[middle - 1]) + float(ordered[middle])) / 2.0


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def run_trial(problem, seed, config):
    start = time.time()
    result = genetic_algorithm(
        problem,
        population_size=config["population_size"],
        generations=config["generations"],
        crossover_rate=config["crossover_rate"],
        mutation_rate=config["mutation_rate"],
        insertion_rate=config["insertion_rate"],
        elite_count=config["elite_count"],
        tournament_size=config["tournament_size"],
        local_search_rate=config["local_search_rate"],
        local_search_attempts=config["local_search_attempts"],
        include_heuristic_seeds=config.get("include_heuristic_seeds", True),
        seed=seed,
        verbose=False,
    )
    elapsed = time.time() - start
    valid, messages = validate_solution(problem, result["solution"])
    success = (result["fitness"] == 0.0 and valid)

    return {
        "seed": seed,
        "success": success,
        "fitness": result["fitness"],
        "generation": result["generation"],
        "runtime_seconds": elapsed,
        "initial_fitness": result["history"][0] if result["history"] else result["fitness"],
        "zero_at_generation_0": bool(success and result["generation"] == 0),
        "validation_messages": messages,
    }


def summarise_trials(trials):
    successes = [t for t in trials if t["success"]]
    runtimes = [t["runtime_seconds"] for t in trials]
    successful_generations = [t["generation"] for t in successes]
    fitnesses = [t["fitness"] for t in trials]
    zero_initial = [t for t in trials if t["zero_at_generation_0"]]

    return {
        "runs": len(trials),
        "successes": len(successes),
        "success_rate": (float(len(successes)) / float(len(trials))) if trials else 0.0,
        "zero_at_generation_0_rate": (float(len(zero_initial)) / float(len(trials))) if trials else 0.0,
        "mean_runtime_seconds": mean(runtimes),
        "median_runtime_seconds": median(runtimes),
        "mean_generation_to_zero": mean(successful_generations),
        "median_generation_to_zero": median(successful_generations),
        "mean_final_fitness": mean(fitnesses),
        "best_final_fitness": min(fitnesses) if fitnesses else None,
        "worst_final_fitness": max(fitnesses) if fitnesses else None,
    }


def official_reliability(runs):
    records = []
    groups = [
        ("basic", create_basic_instances()),
        ("challenging", create_challenging_instances()),
    ]

    for group_name, instances in groups:
        for instance_index, instance in enumerate(instances):
            print("Official reliability: %s (%d runs)" % (instance.name, runs))
            problem = convert_instance(instance)
            trials = []
            for run_index in range(runs):
                seed = 100000 + instance_index * 1000 + run_index
                trials.append(run_trial(problem, seed, DEFAULT_GA))
            summary = summarise_trials(trials)
            records.append({
                "group": group_name,
                "instance": instance.name,
                "config": dict(DEFAULT_GA),
                "summary": summary,
                "trials": trials,
            })
            print("  success=%d/%d, gen0=%.1f%%, mean runtime=%.4fs" % (
                summary["successes"], summary["runs"],
                summary["zero_at_generation_0_rate"] * 100.0,
                summary["mean_runtime_seconds"]))
    return records


def make_stress_problem(scale=0.80):
    """Create a harder, clearly labelled derivative of challenge_01.

    This is not an official assessment instance.  It is used only to make
    parameter effects measurable because the supplied instances are usually
    solved by the initial population.
    """
    instance = create_challenging_instances()[0]
    original = convert_instance(instance)
    return Problem(original.width * scale,
                   original.depth * scale,
                   original.max_weight,
                   original.cylinders)


def parameter_configs():
    base = {
        "population_size": 20,
        "generations": 100,
        "crossover_rate": 0.90,
        "mutation_rate": 0.25,
        "insertion_rate": 0.08,
        "elite_count": 2,
        "tournament_size": 4,
        "local_search_rate": 0.20,
        "local_search_attempts": 6,
        "include_heuristic_seeds": False,
    }

    def changed(name, **updates):
        config = dict(base)
        config.update(updates)
        return (name, config)

    return [
        changed("baseline_random_only"),
        changed("small_population", population_size=8),
        changed("large_population", population_size=60, elite_count=4),
        changed("low_mutation", mutation_rate=0.05),
        changed("high_mutation", mutation_rate=0.50),
        changed("no_local_search", local_search_rate=0.0),
        changed("high_local_search", local_search_rate=0.50),
        changed("heuristic_seeded", include_heuristic_seeds=True),
    ]


def parameter_sweep(runs, stress_scale=0.80):
    problem = make_stress_problem(stress_scale)
    records = []

    for config_index, (name, config) in enumerate(parameter_configs()):
        print("Parameter sweep: %s (%d runs)" % (name, runs))
        trials = []
        for run_index in range(runs):
            seed = 500000 + config_index * 10000 + run_index
            trials.append(run_trial(problem, seed, config))
        summary = summarise_trials(trials)
        records.append({
            "name": name,
            "stress_scale": stress_scale,
            "derived_from": "challenge_01_tight_packing",
            "container_width": problem.width,
            "container_depth": problem.depth,
            "config": config,
            "summary": summary,
            "trials": trials,
        })
        print("  success=%d/%d, mean generation=%s, mean runtime=%.4fs" % (
            summary["successes"], summary["runs"],
            "n/a" if summary["mean_generation_to_zero"] is None else "%.2f" % summary["mean_generation_to_zero"],
            summary["mean_runtime_seconds"]))
    return records


def write_official_csv(path, records):
    fields = [
        "group", "instance", "runs", "successes", "success_rate",
        "zero_at_generation_0_rate", "mean_runtime_seconds",
        "median_runtime_seconds", "mean_generation_to_zero",
        "median_generation_to_zero", "mean_final_fitness",
        "best_final_fitness", "worst_final_fitness",
    ]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {"group": record["group"], "instance": record["instance"]}
            row.update(record["summary"])
            writer.writerow(row)


def write_sweep_csv(path, records):
    fields = [
        "name", "stress_scale", "population_size", "mutation_rate",
        "local_search_rate", "include_heuristic_seeds", "runs", "successes",
        "success_rate", "zero_at_generation_0_rate", "mean_runtime_seconds",
        "median_runtime_seconds", "mean_generation_to_zero",
        "median_generation_to_zero", "mean_final_fitness",
        "best_final_fitness", "worst_final_fitness",
    ]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            config = record["config"]
            row = {
                "name": record["name"],
                "stress_scale": record["stress_scale"],
                "population_size": config["population_size"],
                "mutation_rate": config["mutation_rate"],
                "local_search_rate": config["local_search_rate"],
                "include_heuristic_seeds": config["include_heuristic_seeds"],
            }
            row.update(record["summary"])
            writer.writerow(row)


def write_summary(path, official, sweep):
    with open(path, "w") as handle:
        handle.write("KV6018 Cargo Packing - Experimental Summary\n")
        handle.write("============================================\n\n")
        handle.write("OFFICIAL INSTANCE RELIABILITY\n")
        handle.write("-----------------------------\n")
        for record in official:
            s = record["summary"]
            handle.write("%-34s success %3d/%3d (%6.2f%%), gen0 %6.2f%%, mean time %.4fs\n" % (
                record["instance"], s["successes"], s["runs"],
                100.0 * s["success_rate"],
                100.0 * s["zero_at_generation_0_rate"],
                s["mean_runtime_seconds"]))

        handle.write("\nPARAMETER EXPLORATION ON DERIVED STRESS INSTANCE\n")
        handle.write("------------------------------------------------\n")
        handle.write("The stress instance is challenge_01_tight_packing with width and depth\n")
        handle.write("scaled to 80%. It is NOT one of the official assessment instances.\n")
        handle.write("Heuristic seeding is disabled except where explicitly tested.\n\n")
        for record in sweep:
            s = record["summary"]
            generation = "n/a" if s["mean_generation_to_zero"] is None else "%.2f" % s["mean_generation_to_zero"]
            handle.write("%-24s success %3d/%3d (%6.2f%%), mean gen %7s, mean time %.4fs\n" % (
                record["name"], s["successes"], s["runs"],
                100.0 * s["success_rate"], generation,
                s["mean_runtime_seconds"]))


def main():
    parser = argparse.ArgumentParser(description="Run repeatable GA experiments")
    parser.add_argument("--runs", type=int, default=30,
                        help="runs per official instance (default: 30)")
    parser.add_argument("--sweep-runs", type=int, default=20,
                        help="runs per parameter configuration (default: 20)")
    parser.add_argument("--quick", action="store_true",
                        help="small smoke test: 3 official runs and 3 sweep runs")
    parser.add_argument("--official-only", action="store_true",
                        help="skip the derived stress-instance parameter sweep")
    args = parser.parse_args()

    if args.quick:
        args.runs = 3
        args.sweep_runs = 3

    output_dir = os.path.join(os.path.dirname(__file__), "results", "experiments")
    ensure_dir(output_dir)

    official = official_reliability(args.runs)
    sweep = [] if args.official_only else parameter_sweep(args.sweep_runs)

    combined = {
        "official_reliability": official,
        "parameter_sweep": sweep,
        "notes": {
            "official_parameters": DEFAULT_GA,
            "stress_instance": "challenge_01_tight_packing scaled to 80% width and depth",
            "stress_instance_is_official": False,
        },
    }

    json_path = os.path.join(output_dir, "experiments.json")
    with open(json_path, "w") as handle:
        json.dump(combined, handle, indent=2)

    write_official_csv(os.path.join(output_dir, "official_reliability.csv"), official)
    if sweep:
        write_sweep_csv(os.path.join(output_dir, "parameter_sweep.csv"), sweep)
    write_summary(os.path.join(output_dir, "summary.txt"), official, sweep)

    print("\nExperimental results written to: %s" % output_dir)


if __name__ == "__main__":
    main()
