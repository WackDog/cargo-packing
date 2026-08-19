from __future__ import print_function

import math
import random

from cargo_packing import (evaluate, heaviest_first, insertion_mutation,
                           largest_first, random_order, swap_mutation)


def _better(a, b):
    """Return True if evaluation tuple a is lexicographically better than b."""
    return (a[0], a[1]) < (b[0], b[1])


def _result(name, best_eval, best_order, step, history, seed, extra=None):
    result = {
        "algorithm": name,
        "fitness": best_eval[0],
        "tie_break": best_eval[1],
        "order": list(best_order),
        "solution": best_eval[2],
        "step": step,
        "history": list(history),
        "seed": seed,
    }
    if extra:
        result.update(extra)
    return result


def hill_climbing(problem,
                  max_iterations=4000,
                  restarts=20,
                  stagnation_limit=150,
                  insertion_probability=0.30,
                  seed=None,
                  include_heuristic_starts=True,
                  verbose=False):
    """Random-restart first-improvement hill climbing over loading orders.

    Each move changes the permutation with either a swap or insertion. Worse
    neighbours are rejected and if the search stagnates it restarts from another
    ordering. The geometric decoder and fitness function are exactly the same
    as those used by the GA, keeping the comparison focused on search strategy.
    """
    if problem.overweight_amount() > 0:
        raise ValueError("Instance is infeasible: total weight exceeds container capacity")

    rng = random.Random(seed)
    best_eval = None
    best_order = None
    history = []
    total_iterations = 0

    starts = []
    if include_heuristic_starts:
        starts.extend([largest_first(problem), heaviest_first(problem)])

    restart_index = 0
    while restart_index < restarts and total_iterations < max_iterations:
        if restart_index < len(starts):
            current_order = list(starts[restart_index])
        else:
            current_order = random_order(problem, rng)

        current_eval = evaluate(problem, current_order)
        if best_eval is None or _better(current_eval, best_eval):
            best_eval = current_eval
            best_order = list(current_order)
        history.append(best_eval[0])

        if best_eval[0] == 0.0:
            return _result("Hill Climbing", best_eval, best_order,
                           total_iterations, history, seed,
                           {"restarts_used": restart_index + 1})

        stagnation = 0
        while (total_iterations < max_iterations and
               stagnation < stagnation_limit):
            if rng.random() < insertion_probability:
                neighbour = insertion_mutation(current_order, rng)
            else:
                neighbour = swap_mutation(current_order, rng)

            neighbour_eval = evaluate(problem, neighbour)
            total_iterations += 1

            if _better(neighbour_eval, current_eval):
                current_order = neighbour
                current_eval = neighbour_eval
                stagnation = 0
            else:
                stagnation += 1

            if _better(current_eval, best_eval):
                best_eval = current_eval
                best_order = list(current_order)

            history.append(best_eval[0])
            if verbose and (total_iterations == 1 or total_iterations % 250 == 0):
                print("hill iteration=%d fitness=%.6f" %
                      (total_iterations, best_eval[0]))

            if best_eval[0] == 0.0:
                return _result("Hill Climbing", best_eval, best_order,
                               total_iterations, history, seed,
                               {"restarts_used": restart_index + 1})

        restart_index += 1

    return _result("Hill Climbing", best_eval, best_order,
                   total_iterations, history, seed,
                   {"restarts_used": restart_index})


def _annealing_energy(evaluation):
    """Scale the shared fitness into a convenient SA energy value.
    """
    return evaluation[0] / 1000.0 + evaluation[1] * 0.01


def simulated_annealing(problem,
                        max_iterations=6000,
                        initial_temperature=600.0,
                        cooling_rate=0.997,
                        minimum_temperature=0.01,
                        insertion_probability=0.30,
                        reheat_after=700,
                        seed=None,
                        include_heuristic_start=False,
                        verbose=False):
    """Simulated annealing on the same permutation representation as the GA."""
    if problem.overweight_amount() > 0:
        raise ValueError("Instance is infeasible: total weight exceeds container capacity")

    rng = random.Random(seed)
    if include_heuristic_start:
        current_order = largest_first(problem)
    else:
        current_order = random_order(problem, rng)

    current_eval = evaluate(problem, current_order)
    best_eval = current_eval
    best_order = list(current_order)
    history = [best_eval[0]]
    temperature = float(initial_temperature)
    no_best_improvement = 0

    if best_eval[0] == 0.0:
        return _result("Simulated Annealing", best_eval, best_order,
                       0, history, seed,
                       {"final_temperature": temperature})

    for iteration in range(1, max_iterations + 1):
        if rng.random() < insertion_probability:
            neighbour = insertion_mutation(current_order, rng)
        else:
            neighbour = swap_mutation(current_order, rng)
        neighbour_eval = evaluate(problem, neighbour)

        current_energy = _annealing_energy(current_eval)
        neighbour_energy = _annealing_energy(neighbour_eval)
        delta = neighbour_energy - current_energy

        accept = delta <= 0.0
        if not accept and temperature > 0.0:
            accept = rng.random() < math.exp(-delta / temperature)

        if accept:
            current_order = neighbour
            current_eval = neighbour_eval

        if _better(current_eval, best_eval):
            best_eval = current_eval
            best_order = list(current_order)
            no_best_improvement = 0
        else:
            no_best_improvement += 1

        history.append(best_eval[0])
        if verbose and (iteration == 1 or iteration % 500 == 0):
            print("sa iteration=%d fitness=%.6f temperature=%.4f" %
                  (iteration, best_eval[0], temperature))

        if best_eval[0] == 0.0:
            return _result("Simulated Annealing", best_eval, best_order,
                           iteration, history, seed,
                           {"final_temperature": temperature})

        temperature = max(minimum_temperature,
                          temperature * cooling_rate)

        # Reheating gives a stalled run another chance to escape a local basin.
        if reheat_after and no_best_improvement >= reheat_after:
            temperature = max(temperature, initial_temperature * 0.35)
            no_best_improvement = 0

    return _result("Simulated Annealing", best_eval, best_order,
                   max_iterations, history, seed,
                   {"final_temperature": temperature})
