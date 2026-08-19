from __future__ import print_function

import argparse
import json
import os
import time

from cargo_packing import Cylinder, Problem, genetic_algorithm, validate_solution
from container_instances import create_basic_instances, create_challenging_instances


DEFAULT_LOADING_RULE = "rear_to_front"


def convert_instance(instance, loading_rule=DEFAULT_LOADING_RULE):
    cylinders = [Cylinder(c.id, c.diameter, c.weight) for c in instance.cylinders]
    return Problem(instance.container.width,
                   instance.container.depth,
                   instance.container.max_weight,
                   cylinders,
                   loading_rule=loading_rule)


def solution_record(instance, result, elapsed, loading_rule=DEFAULT_LOADING_RULE):
    problem = convert_instance(instance, loading_rule)
    solution = result["solution"]
    valid, validation_messages = validate_solution(problem, solution)
    com = solution.centre_of_mass()
    return {
        "name": instance.name,
        "loading_rule": loading_rule,
        "fitness": result["fitness"],
        "valid": valid,
        "validation_messages": validation_messages,
        "seed": result["seed"],
        "generation": result["generation"],
        "runtime_seconds": elapsed,
        "order": result["order"],
        "centre_of_mass": None if com is None else [com[0], com[1]],
        "container": {
            "width": instance.container.width,
            "depth": instance.container.depth,
            "max_weight": instance.container.max_weight,
        },
        "total_weight": sum(c.weight for c in instance.cylinders),
        "placements": [
            {
                "id": p.cylinder.id,
                "diameter": p.cylinder.diameter,
                "weight": p.cylinder.weight,
                "x": p.x,
                "y": p.y,
            }
            for p in solution.placements
        ],
    }


def run_one(instance, loading_rule=DEFAULT_LOADING_RULE,
            seeds=(7, 21, 42, 84, 168)):
    problem = convert_instance(instance, loading_rule)
    best = None
    best_elapsed = None

    for seed in seeds:
        start = time.time()
        result = genetic_algorithm(
            problem,
            population_size=60,
            generations=250,
            crossover_rate=0.90,
            mutation_rate=0.25,
            insertion_rate=0.08,
            elite_count=4,
            tournament_size=4,
            local_search_rate=0.20,
            local_search_attempts=6,
            seed=seed,
            verbose=False,
        )
        elapsed = time.time() - start

        if best is None or (result["fitness"], result["tie_break"]) < (best["fitness"], best["tie_break"]):
            best = result
            best_elapsed = elapsed

        if result["fitness"] == 0.0:
            break

    return solution_record(instance, best, best_elapsed, loading_rule)


def print_record(record, handle=None):
    lines = []
    lines.append("=" * 76)
    lines.append(record["name"])
    lines.append("=" * 76)
    lines.append("loading:    %s" % record["loading_rule"])
    lines.append("fitness:    %.6f" % record["fitness"])
    lines.append("valid:      %s" % record["valid"])
    lines.append("seed:       %s" % record["seed"])
    lines.append("generation: %s" % record["generation"])
    lines.append("runtime:    %.4f s" % record["runtime_seconds"])
    lines.append("order:      %s" % record["order"])
    if record["centre_of_mass"] is not None:
        lines.append("COM:        (%.4f, %.4f)" % tuple(record["centre_of_mass"]))
    else:
        lines.append("COM:        undefined")
    lines.append("weight:     %.1f / %.1f" %
                 (record["total_weight"], record["container"]["max_weight"]))
    if record["validation_messages"]:
        lines.append("validation messages:")
        for message in record["validation_messages"]:
            lines.append("  - %s" % message)
    lines.append("placements:")
    for p in record["placements"]:
        lines.append("  id=%2d  x=%8.4f  y=%8.4f  d=%5.2f  w=%6.1f" %
                     (p["id"], p["x"], p["y"], p["diameter"], p["weight"]))
    lines.append("")
    text = "\n".join(lines)
    print(text)
    if handle is not None:
        handle.write(text + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run the GA on all official instances")
    parser.add_argument("--loading-rule", default=DEFAULT_LOADING_RULE,
                        choices=("rear_to_front", "straight_path", "none"),
                        help="loading interpretation (default: rear_to_front)")
    args = parser.parse_args()

    groups = [
        ("basic", create_basic_instances()),
        ("challenging", create_challenging_instances()),
    ]

    output = {"basic": [], "challenging": []}
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    text_path = os.path.join(output_dir, "reference_results.txt")

    with open(text_path, "w") as text_handle:
        text_handle.write("KV6018 Official Instance Results\n")
        text_handle.write("Loading rule: %s\n\n" % args.loading_rule)
        for group_name, instances in groups:
            heading = "### %s instances ###\n" % group_name.upper()
            print("\n" + heading)
            text_handle.write(heading + "\n")
            for instance in instances:
                record = run_one(instance, args.loading_rule)
                output[group_name].append(record)
                print_record(record, text_handle)

        total = sum(len(output[k]) for k in output)
        passed = sum(1 for k in output for r in output[k]
                     if r["fitness"] == 0.0 and r["valid"])
        summary = "Passed %d/%d official instances with fitness 0." % (passed, total)
        print(summary)
        text_handle.write(summary + "\n")

    output_path = os.path.join(output_dir, "reference_results.json")
    with open(output_path, "w") as handle:
        json.dump(output, handle, indent=2)

    print("Results written to: %s" % output_path)
    print("Text summary written to: %s" % text_path)


if __name__ == "__main__":
    main()
