from __future__ import print_function
from cargo_packing import Cylinder, Problem


def _problem(name, width, depth, max_weight, cylinder_rows,
             loading_rule="rear_to_front"):
    cylinders = [Cylinder(row[0], row[1], row[2]) for row in cylinder_rows]
    p = Problem(width, depth, max_weight, cylinders, loading_rule=loading_rule)
    p.name = name
    return p


def create_basic_problems(loading_rule="rear_to_front"):
    return [
        _problem("basic_01_three_identical", 10.0, 10.0, 100.0, [
            (1, 2.0, 10.0),
            (2, 2.0, 10.0),
            (3, 2.0, 10.0),
        ], loading_rule),
        _problem("basic_02_two_sizes", 12.0, 10.0, 150.0, [
            (1, 3.0, 20.0),
            (2, 3.0, 20.0),
            (3, 2.0, 15.0),
            (4, 2.0, 15.0),
        ], loading_rule),
        _problem("basic_03_varied_sizes", 15.0, 12.0, 200.0, [
            (1, 3.5, 25.0),
            (2, 3.0, 20.0),
            (3, 2.5, 18.0),
            (4, 2.5, 18.0),
            (5, 2.0, 15.0),
        ], loading_rule),
    ]


def create_challenging_problems(loading_rule="rear_to_front"):
    return [
        _problem("challenge_01_tight_packing", 15.0, 15.0, 300.0, [
            (1, 4.0, 35.0),
            (2, 3.5, 30.0),
            (3, 3.5, 30.0),
            (4, 3.0, 25.0),
            (5, 3.0, 25.0),
            (6, 2.5, 20.0),
            (7, 2.5, 20.0),
            (8, 2.0, 15.0),
        ], loading_rule),
        _problem("challenge_02_weight_balance", 18.0, 14.0, 400.0, [
            (1, 3.0, 80.0),
            (2, 3.0, 80.0),
            (3, 2.5, 10.0),
            (4, 2.5, 10.0),
            (5, 2.5, 10.0),
            (6, 2.5, 10.0),
            (7, 3.5, 60.0),
            (8, 3.5, 60.0),
        ], loading_rule),
        _problem("challenge_03_many_small", 20.0, 15.0, 350.0, [
            (1, 2.0, 15.0), (2, 2.0, 15.0), (3, 2.0, 15.0),
            (4, 2.0, 15.0), (5, 2.0, 15.0), (6, 2.0, 15.0),
            (7, 2.0, 15.0), (8, 2.0, 15.0), (9, 2.0, 15.0),
            (10, 2.0, 15.0), (11, 2.0, 15.0), (12, 2.0, 15.0),
        ], loading_rule),
        _problem("challenge_04_mixed_constraints", 20.0, 20.0, 500.0, [
            (1, 5.0, 50.0),
            (2, 4.5, 45.0),
            (3, 4.0, 40.0),
            (4, 3.5, 35.0),
            (5, 3.5, 35.0),
            (6, 3.0, 30.0),
            (7, 3.0, 30.0),
            (8, 2.5, 25.0),
            (9, 2.5, 25.0),
            (10, 2.0, 20.0),
        ], loading_rule),
    ]


def create_all_problems(loading_rule="rear_to_front"):
    return create_basic_problems(loading_rule) + create_challenging_problems(loading_rule)
