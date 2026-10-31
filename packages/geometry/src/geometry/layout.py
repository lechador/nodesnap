"""Bounded strip CP-SAT layout: 0.1 m widths, fixed connected circulation.

Area bounds round inward; solver status reports only this encoded family.
Core and corridor are reserved before room placement. The fixed 6.95 m strips
are an exact template dimension, not silently rounded to the planning grid.
"""
from __future__ import annotations

import math
from ortools.sat.python import cp_model

GRID = 10
ROOM_W_DM = 150
STRIP_DEPTH_M = 6.95
CORRIDOR_Y_M = 6.95
CORRIDOR_DEPTH_M = 1.6


def solve_floor(rooms: list[dict], seed: int = 7, time_limit_s: float = 10.0) -> dict:
    if (not 1 <= len(rooms) <= 12 or not math.isfinite(time_limit_s) or time_limit_s < 0
            or any(not isinstance(r.get("target_area_m2"), (int, float))
                   or not math.isfinite(r["target_area_m2"]) or r["target_area_m2"] <= 0 for r in rooms)):
        return {"solver_status": "MODEL_INVALID", "placements": []}
    model = cp_model.CpModel()
    north = [model.new_bool_var(f"north_{i}") for i in range(len(rooms))]
    widths = [model.new_int_var(20, ROOM_W_DM, f"width_{i}") for i in range(len(rooms))]
    deviations = []
    # Width units 0.1 m × depth 6.95 m = 695/1000 m² exactly.
    for i, room in enumerate(rooms):
        target = room["target_area_m2"] * 1000
        model.add(widths[i] * 695 >= math.ceil(target * .85))
        model.add(widths[i] * 695 <= math.floor(target * 1.15))
        deviation = model.new_int_var(0, 2_000_000, f"deviation_{i}")
        model.add_abs_equality(deviation, widths[i] * 695 - round(target))
        deviations.append(deviation)
    for side in (0, 1):
        terms = []
        for i, width in enumerate(widths):
            selected_width = model.new_int_var(0, ROOM_W_DM, f"side_{side}_{i}")
            active = north[i] if side else north[i].Not()
            model.add(selected_width == width).only_enforce_if(active)
            model.add(selected_width == 0).only_enforce_if(active.Not())
            terms.append(selected_width)
        filled = model.new_bool_var(f"filled_{side}")
        model.add(sum(terms) == ROOM_W_DM).only_enforce_if(filled)
        model.add(sum(terms) <= ROOM_W_DM - 12).only_enforce_if(filled.Not())
    model.minimize(sum(deviations))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(time_limit_s, 15.0)
    solver.parameters.max_deterministic_time = 1.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    result = solver.solve(model)
    status = solver.status_name(result)
    settings = {"planning_grid_m": .1, "seed": seed, "num_search_workers": 1,
                "max_deterministic_time": 1.0, "max_time_in_seconds": min(time_limit_s, 15.0),
                "family": "central_corridor_fixed_core", "target_area_basis": "wall_centerline_zone",
                "clear_area_note": "Clear room areas subtract assumed wall thickness after placement and are reported separately; program net-area reconciliation remains visible."}
    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"solver_status": status, "placements": [], "settings": settings}
    positions = {False: 0.0, True: 0.0}
    placements = []
    for i, room in enumerate(rooms):
        side = bool(solver.value(north[i]))
        width = solver.value(widths[i]) / GRID
        placements.append({**room, "x_m": positions[side], "y_m": 8.55 if side else 0.0,
                           "width_m": width, "depth_m": STRIP_DEPTH_M, "strip": "north" if side else "south"})
        positions[side] += width
    return {"solver_status": status, "placements": placements, "settings": settings,
            "corridor": {"x_m": 0.0, "y_m": 6.95, "width_m": 18.0, "depth_m": 1.6},
            "core": {"x_m": 15.0, "y_m": 0.0, "width_m": 3.0, "depth_m": 15.5}}
