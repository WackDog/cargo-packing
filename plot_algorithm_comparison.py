from __future__ import print_function

import csv
import os

import matplotlib.pyplot as plt


def read_rows(path):
    with open(path, "r") as handle:
        return list(csv.DictReader(handle))


def mean(values):
    return sum(values) / float(len(values)) if values else 0.0


def main():
    base = os.path.dirname(__file__)
    result_dir = os.path.join(base, "results", "algorithm_comparison")
    rows = read_rows(os.path.join(result_dir, "comparison.csv"))
    plot_dir = os.path.join(result_dir, "plots")
    if not os.path.isdir(plot_dir):
        os.makedirs(plot_dir)

    algorithms = ["Genetic Algorithm", "Hill Climbing", "Simulated Annealing"]
    official = [r for r in rows if r["group"] in ("basic", "challenging")]

    runtime_means = []
    for name in algorithms:
        values = [float(r["mean_runtime_seconds"]) for r in official
                  if r["algorithm_name"] == name]
        runtime_means.append(mean(values))

    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111)
    ax.bar(algorithms, runtime_means)
    ax.set_ylabel("Mean runtime across official instances (s)")
    ax.set_title("Algorithm runtime comparison")
    ax.tick_params(axis="x", rotation=18)
    fig.tight_layout()
    fig.savefig(os.path.join(plot_dir, "official_algorithm_runtime.png"), dpi=180)
    plt.close(fig)

    stress = [r for r in rows if r["group"] == "experimental"]
    if stress:
        success = []
        for name in algorithms:
            matches = [r for r in stress if r["algorithm_name"] == name]
            success.append(100.0 * float(matches[0]["success_rate"]) if matches else 0.0)
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)
        ax.bar(algorithms, success)
        ax.set_ylim(0, 105)
        ax.set_ylabel("Success rate (%)")
        ax.set_title("Derived stress-instance success rate")
        ax.tick_params(axis="x", rotation=18)
        fig.tight_layout()
        fig.savefig(os.path.join(plot_dir, "stress_algorithm_success.png"), dpi=180)
        plt.close(fig)

    print("Plots written to %s" % plot_dir)


if __name__ == "__main__":
    main()
