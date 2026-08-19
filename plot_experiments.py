from __future__ import print_function

import csv
import os

import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(__file__)
EXPERIMENT_DIR = os.path.join(BASE_DIR, "results", "experiments")
PLOT_DIR = os.path.join(EXPERIMENT_DIR, "plots")


def read_rows(path):
    with open(path, "r") as handle:
        return list(csv.DictReader(handle))


def save_generation_plot(rows):
    names = [r["name"].replace("_", " ") for r in rows]
    values = [float(r["mean_generation_to_zero"]) for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(range(len(names)), values)
    ax.set_ylabel("Mean generation to fitness 0")
    ax.set_title("GA parameter exploration on derived stress instance")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "parameter_mean_generation.png"), dpi=180)
    plt.close(fig)


def save_runtime_plot(rows):
    names = [r["name"].replace("_", " ") for r in rows]
    values = [float(r["mean_runtime_seconds"]) for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(range(len(names)), values)
    ax.set_ylabel("Mean runtime (seconds)")
    ax.set_title("Runtime by GA parameter configuration")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "parameter_mean_runtime.png"), dpi=180)
    plt.close(fig)


def save_official_runtime_plot(rows):
    names = [r["instance"].replace("_", " ") for r in rows]
    values = [float(r["mean_runtime_seconds"]) for r in rows]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(range(len(names)), values)
    ax.set_ylabel("Mean runtime (seconds)")
    ax.set_title("Mean GA runtime across official instances (30 runs each)")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "official_mean_runtime.png"), dpi=180)
    plt.close(fig)


def main():
    if not os.path.isdir(PLOT_DIR):
        os.makedirs(PLOT_DIR)

    sweep = read_rows(os.path.join(EXPERIMENT_DIR, "parameter_sweep.csv"))
    official = read_rows(os.path.join(EXPERIMENT_DIR, "official_reliability.csv"))
    save_generation_plot(sweep)
    save_runtime_plot(sweep)
    save_official_runtime_plot(official)
    print("Plots written to: %s" % PLOT_DIR)


if __name__ == "__main__":
    main()
