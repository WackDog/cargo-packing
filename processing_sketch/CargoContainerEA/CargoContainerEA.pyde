from __future__ import print_function

import time

from cargo_packing import genetic_algorithm, validate_solution
from alternative_algorithms import hill_climbing, simulated_annealing
from instances_processing import create_all_problems

# ---------------------------------------------------------------------------
# Cargo Container Loading Processing.py visualisation and runner
# -==================================================================================
# Default loading interpretation follows the Week 7 wording literally:
# placements progress from rear (y=0) to front (y=depth).  The core module
# also contains an optional stricter straight_path mode for exploration.

LOADING_RULE = "rear_to_front"
RUN_COMPARISON_ALGORITHMS = True

records = []
record_index = 0
status_message = "Starting..."

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
}


def setup():
    global records, status_message
    size(1280, 820)
    smooth(4)
    textFont(createFont("Arial", 14))
    noLoop()

    try:
        records = solve_all_instances()
        status_message = "Loaded %d verified solutions" % len(records)
    except Exception as exc:
        status_message = "ERROR: %s" % exc
        print(status_message)


def draw():
    background(8, 37, 52)
    if not records:
        fill(255)
        textAlign(LEFT, TOP)
        textSize(18)
        text(status_message, 40, 40)
        return

    draw_record(records[record_index])


def solve_all_instances():
    output = []
    problems = create_all_problems(LOADING_RULE)

    for problem_index, problem in enumerate(problems):
        print("Solving", problem.name)

        start = time.time()
        ga = genetic_algorithm(problem, seed=700 + problem_index,
                               verbose=False, **GA_CONFIG)
        ga_time = time.time() - start
        output.append(make_record(problem, "GA", ga, ga_time,
                                  ga.get("generation", 0)))

        if RUN_COMPARISON_ALGORITHMS:
            start = time.time()
            hc = hill_climbing(problem, seed=1700 + problem_index,
                               max_iterations=4000, restarts=20,
                               stagnation_limit=150,
                               insertion_probability=0.30,
                               include_heuristic_starts=True,
                               verbose=False)
            hc_time = time.time() - start
            output.append(make_record(problem, "Hill Climbing", hc, hc_time,
                                      hc.get("step", 0)))

            start = time.time()
            sa = simulated_annealing(problem, seed=2700 + problem_index,
                                     max_iterations=6000,
                                     initial_temperature=600.0,
                                     cooling_rate=0.997,
                                     minimum_temperature=0.01,
                                     insertion_probability=0.30,
                                     reheat_after=700,
                                     include_heuristic_start=False,
                                     verbose=False)
            sa_time = time.time() - start
            output.append(make_record(problem, "Simulated Annealing", sa,
                                      sa_time, sa.get("step", 0)))

    return output


def make_record(problem, algorithm_name, result, elapsed, search_step):
    valid, messages = validate_solution(problem, result["solution"])
    if result["fitness"] != 0.0 or not valid:
        print("WARNING", problem.name, algorithm_name,
              "fitness", result["fitness"], messages)

    return {
        "problem": problem,
        "algorithm": algorithm_name,
        "fitness": result["fitness"],
        "tie_break": result["tie_break"],
        "order": list(result["order"]),
        "solution": result["solution"],
        "valid": valid,
        "messages": messages,
        "runtime": elapsed,
        "search_step": search_step,
    }


def draw_record(record):
    problem = record["problem"]
    solution = record["solution"]

    # Main layout area and right-hand information panel.
    panel_x = 930
    area_left = 70
    area_top = 70
    area_right = panel_x - 45
    area_bottom = 745

    available_w = area_right - area_left
    available_h = area_bottom - area_top
    scale_value = min(available_w / problem.width,
                      available_h / problem.depth)

    container_w = problem.width * scale_value
    container_h = problem.depth * scale_value
    origin_x = area_left + (available_w - container_w) / 2.0
    origin_y = area_top + (available_h - container_h) / 2.0

    # Title.
    fill(248)
    textAlign(LEFT, TOP)
    textSize(22)
    text(problem.name, 40, 20)
    textSize(15)
    fill(180, 225, 230)
    text(record["algorithm"], 560, 24)

    # Central 60% safe centre-of-mass region.
    safe_x = origin_x + 0.2 * problem.width * scale_value
    safe_y_math = 0.8 * problem.depth
    safe_y = to_screen_y(safe_y_math, origin_y, container_h, scale_value)
    noStroke()
    fill(90, 190, 145, 45)
    rect(safe_x, safe_y,
         0.6 * problem.width * scale_value,
         0.6 * problem.depth * scale_value)
    noFill()
    stroke(95, 220, 165)
    strokeWeight(2)
    rect(safe_x, safe_y,
         0.6 * problem.width * scale_value,
         0.6 * problem.depth * scale_value)

    # Container boundary.
    noFill()
    stroke(248)
    strokeWeight(3)
    rect(origin_x, origin_y, container_w, container_h)

    # Rear/front labels and loading direction.
    fill(255, 150, 120)
    noStroke()
    textAlign(CENTER, TOP)
    textSize(12)
    text("REAR  y=0", origin_x + container_w / 2.0, origin_y + container_h + 8)
    text("FRONT  y=D", origin_x + container_w / 2.0, origin_y - 23)
    stroke(255, 150, 120)
    strokeWeight(2)
    line(origin_x - 24, origin_y + container_h - 8,
         origin_x - 24, origin_y + 18)
    line(origin_x - 24, origin_y + 18,
         origin_x - 30, origin_y + 30)
    line(origin_x - 24, origin_y + 18,
         origin_x - 18, origin_y + 30)

    # Cylinder load-step lookup.
    step_lookup = {}
    for i in range(len(record["order"])):
        step_lookup[record["order"][i]] = i + 1

    # Cylinders.
    for placement in solution.placements:
        sx = origin_x + placement.x * scale_value
        sy = to_screen_y(placement.y, origin_y, container_h, scale_value)
        diameter_px = placement.cylinder.diameter * scale_value

        stroke(245)
        strokeWeight(2)
        fill(120, 210, 220, 95)
        ellipse(sx, sy, diameter_px, diameter_px)

        fill(248)
        noStroke()
        textAlign(CENTER, CENTER)
        textSize(max(9, min(13, int(diameter_px / 5.0))))
        label = "ID %s\n#%s" % (placement.cylinder.id,
                                step_lookup.get(placement.cylinder.id, "?"))
        text(label, sx, sy)

    # Centre of mass marker.
    com = solution.centre_of_mass()
    if com is not None:
        com_x = origin_x + com[0] * scale_value
        com_y = to_screen_y(com[1], origin_y, container_h, scale_value)
        stroke(250, 190, 30)
        strokeWeight(4)
        line(com_x - 9, com_y - 9, com_x + 9, com_y + 9)
        line(com_x - 9, com_y + 9, com_x + 9, com_y - 9)
        fill(250, 190, 30)
        noStroke()
        textAlign(LEFT, CENTER)
        textSize(12)
        text("COM", com_x + 14, com_y)

    draw_info_panel(record, panel_x)


def to_screen_y(y_value, origin_y, container_h, scale_value):
    return origin_y + container_h - y_value * scale_value


def draw_info_panel(record, panel_x):
    problem = record["problem"]
    solution = record["solution"]
    com = solution.centre_of_mass()

    noStroke()
    fill(13, 52, 69)
    rect(panel_x, 0, width - panel_x, height)

    fill(248)
    textAlign(LEFT, TOP)
    textSize(18)
    text("Solution details", panel_x + 24, 28)

    textSize(13)
    y = 72
    gap = 24
    fields = [
        ("Algorithm", record["algorithm"]),
        ("Fitness", "%.6f" % record["fitness"]),
        ("Valid", str(record["valid"])),
        ("Runtime", "%.4f s" % record["runtime"]),
        ("Search step", str(record["search_step"])),
        ("Loading rule", problem.loading_rule),
        ("Container", "%.1f x %.1f m" % (problem.width, problem.depth)),
        ("Weight", "%.1f / %.1f kg" %
                   (problem.total_weight(), problem.max_weight)),
    ]
    if com is not None:
        fields.append(("Centre of mass", "(%.2f, %.2f)" % com))

    for label, value in fields:
        fill(150, 205, 215)
        text(label + ":", panel_x + 24, y)
        fill(248)
        text(value, panel_x + 142, y)
        y += gap

    y += 12
    fill(150, 205, 215)
    text("Loading order:", panel_x + 24, y)
    fill(248)
    y += 24
    order_text = " -> ".join([str(item) for item in record["order"]])
    text(order_text, panel_x + 24, y, width - panel_x - 48, 90)

    y += 104
    fill(150, 205, 215)
    text("Controls", panel_x + 24, y)
    fill(248)
    y += 26
    controls = (
        "Left / Right: previous / next\n"
        "Up / Down: previous / next instance\n"
        "1: GA   2: Hill Climbing   3: SA\n"
        "S: save current frame"
    )
    text(controls, panel_x + 24, y, width - panel_x - 48, 120)

    y += 132
    fill(150, 205, 215)
    text("Legend", panel_x + 24, y)
    y += 26
    fill(90, 190, 145)
    rect(panel_x + 24, y + 3, 18, 12)
    fill(248)
    text("central 60% COM region", panel_x + 52, y)
    y += 24
    stroke(250, 190, 30)
    strokeWeight(3)
    line(panel_x + 25, y + 4, panel_x + 39, y + 18)
    line(panel_x + 25, y + 18, panel_x + 39, y + 4)
    noStroke()
    fill(248)
    text("centre of mass", panel_x + 52, y)

    fill(165, 210, 220)
    textAlign(LEFT, BOTTOM)
    textSize(11)
    text(status_message, panel_x + 24, height - 20)


def current_instance_name():
    if not records:
        return None
    return records[record_index]["problem"].name


def jump_instance(delta):
    global record_index
    if not records:
        return
    name = current_instance_name()
    names = []
    for record in records:
        n = record["problem"].name
        if n not in names:
            names.append(n)
    current = names.index(name)
    target = names[(current + delta) % len(names)]
    for i in range(len(records)):
        if records[i]["problem"].name == target:
            record_index = i
            return


def jump_algorithm(number):
    global record_index
    if not records:
        return
    name = current_instance_name()
    desired = {1: "GA", 2: "Hill Climbing", 3: "Simulated Annealing"}.get(number)
    if desired is None:
        return
    for i in range(len(records)):
        if (records[i]["problem"].name == name and
                records[i]["algorithm"] == desired):
            record_index = i
            return


def keyPressed():
    global record_index, status_message
    if not records:
        return

    if keyCode == RIGHT:
        record_index = (record_index + 1) % len(records)
    elif keyCode == LEFT:
        record_index = (record_index - 1) % len(records)
    elif keyCode == DOWN:
        jump_instance(1)
    elif keyCode == UP:
        jump_instance(-1)
    elif key == '1':
        jump_algorithm(1)
    elif key == '2':
        jump_algorithm(2)
    elif key == '3':
        jump_algorithm(3)
    elif key == 's' or key == 'S':
        filename = "%s_%s.png" % (
            records[record_index]["problem"].name,
            records[record_index]["algorithm"].replace(" ", "_").lower())
        saveFrame(filename)
        status_message = "Saved " + filename
    redraw()
