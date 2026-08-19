# KV6018 Cargo Container Loading

Python implementation of the cargo container loading assessment, the project uses a permutation-based memetic genetic algorithm to determine cylinder loading order while using a geometric decoder used to place cylinders inside a rectangular container while enforcing non-overlap, boundary, weight, centre-of-mass and rear-to-front loading constraints.

Two additional search methods, hill climbing and simulated annealing, are included for comparison.

## Requirements

Python 3 is required for the command-line experiments. Matplotlib is required only for the experiment plots:

```bash
python -m pip install -r requirements.txt
```

The Processing visualisation requires Processing with Python Mode.

## Run the supplied instances

From the project directory:

```bash
python run_reference_instances.py
```

The script prints the best loading order, fitness, centre of mass, weight and cylinder coordinates for each supplied instance. Results are written to `results/reference_results.txt` and `results/reference_results.json`.

## Run experiments

Repeated genetic-algorithm tests and the parameter sweep:

```bash
python experiments.py
python plot_experiments.py
```

Algorithm comparison:

```bash
python compare_algorithms.py
python plot_algorithm_comparison.py
```

The generated CSV files and plots are stored under `results/experiments/` and `results/algorithm_comparison/`.

## Processing visualisation

Open:

`processing_sketch/CargoContainerEA/CargoContainerEA.pyde`

in Processing with Python Mode and press **Run**.

Controls:

- Left / Right — change algorithm solution
- Up / Down — change problem instance
- `1` — Genetic Algorithm
- `2` — Hill Climbing
- `3` — Simulated Annealing
- `S` — save the current frame

## Loading rule

The rear of the container is represented by `y = 0`. Cylinders are decoded in loading order and their centre positions must progress from rear to front without decreasing in `y`. A zero f represents a complete feasible solution satisfying the required constraints.