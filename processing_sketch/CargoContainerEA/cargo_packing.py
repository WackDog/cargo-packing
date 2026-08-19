from __future__ import print_function

import math
import random

EPS = 1e-7


class Cylinder(object):
    """One cylindrical cargo item viewed from above as a circle."""

    def __init__(self, item_id, diameter, weight):
        self.id = item_id
        self.diameter = float(diameter)
        self.radius = float(diameter) / 2.0
        self.weight = float(weight)


class Placement(object):
    """A decoded cylinder position."""

    def __init__(self, cylinder, x, y):
        self.cylinder = cylinder
        self.x = float(x)
        self.y = float(y)


class Problem(object):
    def __init__(self, width, depth, max_weight, cylinders,
                 loading_rule="rear_to_front"):
        self.width = float(width)
        self.depth = float(depth)
        self.max_weight = float(max_weight)
        self.cylinders = list(cylinders)
        self.by_id = dict((c.id, c) for c in self.cylinders)
        self.loading_rule = loading_rule

        if len(self.by_id) != len(self.cylinders):
            raise ValueError("Cylinder IDs must be unique")
        if loading_rule not in ("rear_to_front", "straight_path", "none"):
            raise ValueError("Unknown loading rule: %s" % loading_rule)

    def total_weight(self):
        return sum(c.weight for c in self.cylinders)

    def overweight_amount(self):
        return max(0.0, self.total_weight() - self.max_weight)


class DecodedSolution(object):
    def __init__(self, order, placements, unplaced_ids):
        self.order = list(order)
        self.placements = list(placements)
        self.unplaced_ids = list(unplaced_ids)

    def centre_of_mass(self):
        total = sum(p.cylinder.weight for p in self.placements)
        if total <= 0:
            return None
        x = sum(p.cylinder.weight * p.x for p in self.placements) / total
        y = sum(p.cylinder.weight * p.y for p in self.placements) / total
        return (x, y)


# ---------- Geometry ----------

def inside_container(problem, cylinder, x, y):
    r = cylinder.radius
    return (r - EPS <= x <= problem.width - r + EPS and
            r - EPS <= y <= problem.depth - r + EPS)


def overlaps_existing(cylinder, x, y, placements):
    for p in placements:
        minimum = cylinder.radius + p.cylinder.radius
        dx = x - p.x
        dy = y - p.y
        if dx * dx + dy * dy < minimum * minimum - EPS:
            return True
    return False


def circle_circle_tangent_points(p1, p2, new_radius):
    """Centres at which a new circle is tangent to both placed circles."""
    r1 = p1.cylinder.radius + new_radius
    r2 = p2.cylinder.radius + new_radius

    dx = p2.x - p1.x
    dy = p2.y - p1.y
    d2 = dx * dx + dy * dy
    if d2 <= EPS:
        return []

    d = math.sqrt(d2)
    if d > r1 + r2 + EPS or d < abs(r1 - r2) - EPS:
        return []

    a = (r1 * r1 - r2 * r2 + d * d) / (2.0 * d)
    h2 = r1 * r1 - a * a
    if h2 < -EPS:
        return []
    h = math.sqrt(max(0.0, h2))

    px = p1.x + a * dx / d
    py = p1.y + a * dy / d

    if h <= EPS:
        return [(px, py)]

    ox = -dy * h / d
    oy = dx * h / d
    return [(px + ox, py + oy), (px - ox, py - oy)]


def wall_tangent_points(problem, placed, new_radius):
    """Points tangent to one placed circle and one rectangular wall."""
    points = []
    combined = placed.cylinder.radius + new_radius

    # left/right wall: x is fixed, solve y
    for x in (new_radius, problem.width - new_radius):
        dx = x - placed.x
        value = combined * combined - dx * dx
        if value >= -EPS:
            root = math.sqrt(max(0.0, value))
            points.append((x, placed.y + root))
            points.append((x, placed.y - root))

    # front/rear wall: y is fixed, solve x
    for y in (new_radius, problem.depth - new_radius):
        dy = y - placed.y
        value = combined * combined - dy * dy
        if value >= -EPS:
            root = math.sqrt(max(0.0, value))
            points.append((placed.x + root, y))
            points.append((placed.x - root, y))

    return points



def loading_path_clear(problem, cylinder, x, y, placements):
    """Conservative optional loading test using a straight path from y=0."""
    r = cylinder.radius
    start_y = r
    end_y = y
    low_y = min(start_y, end_y)
    high_y = max(start_y, end_y)

    for p in placements:
        closest_y = min(max(p.y, low_y), high_y)
        dx = p.x - x
        dy = p.y - closest_y
        minimum = cylinder.radius + p.cylinder.radius
        if dx * dx + dy * dy < minimum * minimum - EPS:
            return False
    return True


def loading_rule_allows(problem, cylinder, x, y, placements):
    """Apply the selected interpretation of the loading-order constraint.

    The Week 7 assignment guidance explicitly says loading should proceed
    rear-to-front, but does not define a swept-path model.  Therefore the
    default rule enforces non-decreasing centre y coordinates, with rear at
    y=0 and front at y=depth.  The previous straight-path interpretation is
    retained as an optional stricter mode for exploration.
    """
    if problem.loading_rule == "none":
        return True
    if problem.loading_rule == "straight_path":
        return loading_path_clear(problem, cylinder, x, y, placements)
    if not placements:
        return True
    return y + EPS >= placements[-1].y

def candidate_points(problem, cylinder, placements):
    """Generate geometric contact positions for a new cylinder."""
    r = cylinder.radius
    candidates = [
        (r, r),
        (problem.width - r, r),
        (r, problem.depth - r),
        (problem.width - r, problem.depth - r),
        (problem.width / 2.0, r),
        (problem.width / 2.0, problem.depth - r),
        (problem.width / 2.0, problem.depth / 2.0),
        (r, problem.depth / 2.0),
        (problem.width - r, problem.depth / 2.0),
    ]

    # Tangency with one existing circle (cardinal directions) and walls.
    for p in placements:
        d = p.cylinder.radius + r
        candidates.extend([
            (p.x + d, p.y),
            (p.x - d, p.y),
            (p.x, p.y + d),
            (p.x, p.y - d),
        ])
        candidates.extend(wall_tangent_points(problem, p, r))

    # Tangency with pairs of circles.
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            candidates.extend(circle_circle_tangent_points(
                placements[i], placements[j], r))

    # Remove near-duplicates to reduce evaluation work.
    unique = []
    seen = set()
    for x, y in candidates:
        key = (round(x, 7), round(y, 7))
        if key not in seen:
            seen.add(key)
            unique.append((x, y))
    return unique


def com_distance_from_safe_region(problem, placements):
    """Euclidean distance of current COM from the central 60% rectangle."""
    if not placements:
        return 0.0

    total = sum(p.cylinder.weight for p in placements)
    if total <= 0:
        return 0.0

    cx = sum(p.cylinder.weight * p.x for p in placements) / total
    cy = sum(p.cylinder.weight * p.y for p in placements) / total

    min_x, max_x = 0.2 * problem.width, 0.8 * problem.width
    min_y, max_y = 0.2 * problem.depth, 0.8 * problem.depth

    dx = 0.0 if min_x <= cx <= max_x else min(abs(cx - min_x), abs(cx - max_x))
    dy = 0.0 if min_y <= cy <= max_y else min(abs(cy - min_y), abs(cy - max_y))
    return math.sqrt(dx * dx + dy * dy)


def placement_score(problem, cylinder, x, y, current_placements):
    """
    Decoder tie-break score (lower is better).

    The Week 7 material uses a placement heuristic to turn an ordering into
    geometry.  Here, candidates near the container centre are preferred,
    while the partial centre of mass is also encouraged towards the centre.
    This produces compact layouts and helps satisfy the central-60% balance
    constraint without adding a non-zero compactness term to final fitness.
    """
    temp = list(current_placements)
    temp.append(Placement(cylinder, x, y))

    total = sum(p.cylinder.weight for p in temp)
    cx = sum(p.cylinder.weight * p.x for p in temp) / total
    cy = sum(p.cylinder.weight * p.y for p in temp) / total

    scale = max(problem.width, problem.depth, EPS)
    item_centrality = math.sqrt(
        (x - problem.width / 2.0) ** 2 +
        (y - problem.depth / 2.0) ** 2) / scale
    com_centrality = math.sqrt(
        (cx - problem.width / 2.0) ** 2 +
        (cy - problem.depth / 2.0) ** 2) / scale

    return item_centrality + 2.0 * com_centrality

def decode(problem, order):
    """Decode a loading-order permutation into a legal geometric layout."""
    placements = []
    unplaced = []

    for item_id in order:
        cylinder = problem.by_id[item_id]
        valid = []
        for x, y in candidate_points(problem, cylinder, placements):
            if not inside_container(problem, cylinder, x, y):
                continue
            if overlaps_existing(cylinder, x, y, placements):
                continue
            if not loading_rule_allows(problem, cylinder, x, y, placements):
                continue
            valid.append((placement_score(problem, cylinder, x, y, placements), x, y))

        if not valid:
            unplaced.append(item_id)
            continue

        # Prefer the lowest heuristic score.  Remaining terms make ties
        # deterministic, which is helpful for experiments and debugging.
        valid.sort(key=lambda item: (item[0], item[2], item[1]))
        _, best_x, best_y = valid[0]
        placements.append(Placement(cylinder, best_x, best_y))

    return DecodedSolution(order, placements, unplaced)


# ---------- Fitness ----------

def final_com_penalty(problem, solution):
    com = solution.centre_of_mass()
    if com is None:
        return max(problem.width, problem.depth)

    cx, cy = com
    min_x, max_x = 0.2 * problem.width, 0.8 * problem.width
    min_y, max_y = 0.2 * problem.depth, 0.8 * problem.depth

    dx = 0.0
    if cx < min_x:
        dx = min_x - cx
    elif cx > max_x:
        dx = cx - max_x

    dy = 0.0
    if cy < min_y:
        dy = min_y - cy
    elif cy > max_y:
        dy = cy - max_y

    return math.sqrt(dx * dx + dy * dy)


def compactness_tiebreak(problem, solution):
    """Area of the placement bounding box; used only as a secondary score."""
    if not solution.placements:
        return problem.width * problem.depth
    min_x = min(p.x - p.cylinder.radius for p in solution.placements)
    max_x = max(p.x + p.cylinder.radius for p in solution.placements)
    min_y = min(p.y - p.cylinder.radius for p in solution.placements)
    max_y = max(p.y + p.cylinder.radius for p in solution.placements)
    return max(0.0, max_x - min_x) * max(0.0, max_y - min_y)


def evaluate(problem, order):
    """Return (primary_fitness, tie_break, decoded_solution). Lower is better."""
    solution = decode(problem, order)

    unplaced_penalty = float(len(solution.unplaced_ids))
    com_penalty = final_com_penalty(problem, solution)
    overweight = problem.overweight_amount()

    # Geometry is enforced by the decoder; zero is retained conceptually.
    # Weight is constant for the instance, but included as a defensive check.
    fitness = (
        1000000.0 * unplaced_penalty +
        10000.0 * com_penalty +
        1000000.0 * overweight
    )

    # Snap very small numerical noise to zero.
    if abs(fitness) < 1e-8:
        fitness = 0.0

    return fitness, compactness_tiebreak(problem, solution), solution


# ---------- Independent solution validation ----------

def validate_solution(problem, solution):
    """Return (is_valid, list_of_messages) for a decoded solution."""
    messages = []

    placed_ids = [p.cylinder.id for p in solution.placements]
    expected_ids = [c.id for c in problem.cylinders]
    if sorted(placed_ids) != sorted(expected_ids):
        messages.append("Not every cylinder is placed exactly once")

    for p in solution.placements:
        if not inside_container(problem, p.cylinder, p.x, p.y):
            messages.append("Cylinder %s is outside the container" % p.cylinder.id)

    for i in range(len(solution.placements)):
        a = solution.placements[i]
        for j in range(i + 1, len(solution.placements)):
            b = solution.placements[j]
            minimum = a.cylinder.radius + b.cylinder.radius
            dx = a.x - b.x
            dy = a.y - b.y
            if dx * dx + dy * dy < minimum * minimum - EPS:
                messages.append("Cylinders %s and %s overlap" %
                                (a.cylinder.id, b.cylinder.id))

    if problem.total_weight() > problem.max_weight + EPS:
        messages.append("Total weight exceeds container capacity")

    com = solution.centre_of_mass()
    if com is None:
        messages.append("Centre of mass is undefined")
    else:
        cx, cy = com
        if not (0.2 * problem.width - EPS <= cx <= 0.8 * problem.width + EPS and
                0.2 * problem.depth - EPS <= cy <= 0.8 * problem.depth + EPS):
            messages.append("Centre of mass is outside the central 60%")

    # Re-check the selected loading rule in the actual placement sequence.
    previous = []
    for p in solution.placements:
        if not loading_rule_allows(problem, p.cylinder, p.x, p.y, previous):
            messages.append("Cylinder %s violates loading rule %s" %
                            (p.cylinder.id, problem.loading_rule))
        previous.append(p)

    return (len(messages) == 0, messages)


# ---------- Genetic algorithm ----------

def random_order(problem, rng):
    order = [c.id for c in problem.cylinders]
    rng.shuffle(order)
    return order


def largest_first(problem):
    return [c.id for c in sorted(problem.cylinders,
                                  key=lambda c: c.radius,
                                  reverse=True)]


def heaviest_first(problem):
    return [c.id for c in sorted(problem.cylinders,
                                  key=lambda c: c.weight,
                                  reverse=True)]


def order_crossover(parent1, parent2, rng):
    """Standard OX permutation crossover."""
    n = len(parent1)
    if n < 2:
        return list(parent1)

    a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n
    child[a:b + 1] = parent1[a:b + 1]

    remaining = [gene for gene in parent2 if gene not in child]
    index = (b + 1) % n
    for gene in remaining:
        while child[index] is not None:
            index = (index + 1) % n
        child[index] = gene
        index = (index + 1) % n
    return child


def swap_mutation(order, rng):
    child = list(order)
    if len(child) >= 2:
        i, j = rng.sample(range(len(child)), 2)
        child[i], child[j] = child[j], child[i]
    return child


def insertion_mutation(order, rng):
    child = list(order)
    if len(child) >= 2:
        i, j = rng.sample(range(len(child)), 2)
        gene = child.pop(i)
        child.insert(j, gene)
    return child


def local_search(problem, order, rng, attempts=8):
    best_order = list(order)
    best_eval = evaluate(problem, best_order)

    for _ in range(attempts):
        if rng.random() < 0.5:
            neighbour = swap_mutation(best_order, rng)
        else:
            neighbour = insertion_mutation(best_order, rng)
        candidate_eval = evaluate(problem, neighbour)
        if (candidate_eval[0], candidate_eval[1]) < (best_eval[0], best_eval[1]):
            best_order = neighbour
            best_eval = candidate_eval

    return best_order, best_eval


def tournament_select(scored_population, rng, tournament_size):
    contestants = rng.sample(scored_population,
                             min(tournament_size, len(scored_population)))
    contestants.sort(key=lambda item: (item[0], item[1]))
    return list(contestants[0][2])


def genetic_algorithm(problem,
                      population_size=120,
                      generations=500,
                      crossover_rate=0.9,
                      mutation_rate=0.25,
                      insertion_rate=0.08,
                      elite_count=4,
                      tournament_size=4,
                      local_search_rate=0.20,
                      local_search_attempts=6,
                      seed=None,
                      verbose=False,
                      include_heuristic_seeds=True):
    """Run the memetic GA and return a result dictionary."""
    if problem.overweight_amount() > 0:
        raise ValueError("Instance is infeasible: total weight exceeds container capacity")

    rng = random.Random(seed)

    population = []
    if include_heuristic_seeds:
        population.append(largest_first(problem))
        if population_size > 1:
            population.append(heaviest_first(problem))
    while len(population) < population_size:
        population.append(random_order(problem, rng))

    best = None
    history = []

    for generation in range(generations + 1):
        scored = []
        for order in population:
            fitness, tie, solution = evaluate(problem, order)
            scored.append((fitness, tie, list(order), solution))
        scored.sort(key=lambda item: (item[0], item[1]))

        current = scored[0]
        history.append(current[0])
        if best is None or (current[0], current[1]) < (best[0], best[1]):
            best = current

        if verbose and (generation == 0 or generation % 25 == 0 or best[0] == 0):
            print("generation=%d fitness=%.6f unplaced=%d" %
                  (generation, best[0], len(best[3].unplaced_ids)))

        # Perfect primary fitness: all constraints are satisfied.
        if best[0] == 0.0:
            return {
                "fitness": best[0],
                "tie_break": best[1],
                "order": best[2],
                "solution": best[3],
                "generation": generation,
                "history": history,
                "seed": seed,
            }

        next_population = [list(item[2]) for item in scored[:elite_count]]

        while len(next_population) < population_size:
            p1 = tournament_select(scored, rng, tournament_size)
            p2 = tournament_select(scored, rng, tournament_size)

            if rng.random() < crossover_rate:
                child = order_crossover(p1, p2, rng)
            else:
                child = list(p1)

            if rng.random() < mutation_rate:
                child = swap_mutation(child, rng)
            if rng.random() < insertion_rate:
                child = insertion_mutation(child, rng)

            if rng.random() < local_search_rate:
                child, _ = local_search(problem, child, rng,
                                        attempts=local_search_attempts)

            next_population.append(child)

        population = next_population

    return {
        "fitness": best[0],
        "tie_break": best[1],
        "order": best[2],
        "solution": best[3],
        "generation": generations,
        "history": history,
        "seed": seed,
    }
