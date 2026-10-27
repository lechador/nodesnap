"""Bounded CP-SAT layout generation — spec A5.

Grammar (declared, limited): one floor plate 18.0 x 15.5 m, a horizontal
corridor band, rooms in a north or south strip, east stair/service core.
The solver chooses strip assignment and 0.1 m-grid widths so each room's
area lands within +/-15% of its program target. CP-SAT status describes
the encoded problem only — not code compliance.
"""
from __future__ import annotations

from ortools.sat.python import cp_model

GRID = 10  # 0.1 m planning grid (spec A5.1)
W_DM, D_DM = 180, 155
CORRIDOR_DM, CORE_DM = 16, 30
ROOM_W_DM = W_DM - CORE_DM
SOUTH_H_DM = (D_DM - CORRIDOR_DM) // 2          # 69
NORTH_H_DM = D_DM - CORRIDOR_DM - SOUTH_H_DM    # 70


def solve_floor(rooms: list[dict], seed: int = 7, time_limit_s: float = 10.0) -> dict:
    """rooms: [{name, use, target_area_m2}]. Returns status + placements in metres."""
    m = cp_model.CpModel()
    n = len(rooms)
    north = [m.NewBoolVar(f"north_{i}") for i in range(n)]
    # width in dm; bounded by strip depth-derived aspect sanity (min 2.0 m)
    width = [m.NewIntVar(20, ROOM_W_DM, f"w_{i}") for i in range(n)]
    # area in dm^2 = width * strip_height (depends on strip) -> two products
    area_terms = []
    for i, r in enumerate(rooms):
        target_dm2 = int(round(r["target_area_m2"] * 100))
        lo, hi = int(target_dm2 * 0.85), int(target_dm2 * 1.15)
        a_south = m.NewIntVar(0, ROOM_W_DM * SOUTH_H_DM, f"as_{i}")
        a_north = m.NewIntVar(0, ROOM_W_DM * NORTH_H_DM, f"an_{i}")
        m.AddMultiplicationEquality(a_south, [width[i], m.NewConstant(SOUTH_H_DM)])
        m.AddMultiplicationEquality(a_north, [width[i], m.NewConstant(NORTH_H_DM)])
        area = m.NewIntVar(0, ROOM_W_DM * D_DM, f"a_{i}")
        m.Add(area == a_north).OnlyEnforceIf(north[i])
        m.Add(area == a_south).OnlyEnforceIf(north[i].Not())
        m.Add(area >= lo)
        m.Add(area <= hi)
        area_terms.append(area)
    # strip width budgets: rooms on a strip, in input order, cannot exceed plate
    for is_north in (0, 1):
        terms = []
        for i in range(n):
            w_in = m.NewIntVar(0, ROOM_W_DM, f"win_{i}_{is_north}")
            m.Add(w_in == width[i]).OnlyEnforceIf(north[i] if is_north else north[i].Not())
            m.Add(w_in == 0).OnlyEnforceIf(north[i].Not() if is_north else north[i])
            terms.append(w_in)
        m.Add(sum(terms) <= ROOM_W_DM)
    # objective: get close to targets
    dev = []
    for i, r in enumerate(rooms):
        target_dm2 = int(round(r["target_area_m2"] * 100))
        d = m.NewIntVar(0, ROOM_W_DM * D_DM, f"dev_{i}")
        m.AddAbsEquality(d, area_terms[i] - target_dm2)
        dev.append(d)
    m.Minimize(sum(dev))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.Solve(m)
    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"solver_status": status_name, "placements": []}
    placements = []
    x_south = x_north = 0.0
    for i, r in enumerate(rooms):
        w_m = solver.Value(width[i]) / GRID
        if solver.Value(north[i]):
            placements.append({**r, "x_m": x_north, "y_m": (SOUTH_H_DM + CORRIDOR_DM) / GRID,
                               "width_m": w_m, "depth_m": NORTH_H_DM / GRID, "strip": "north"})
            x_north += w_m
        else:
            placements.append({**r, "x_m": x_south, "y_m": 0.0,
                               "width_m": w_m, "depth_m": SOUTH_H_DM / GRID, "strip": "south"})
            x_south += w_m
    return {"solver_status": status_name, "placements": placements,
            "corridor": {"x_m": 0.0, "y_m": SOUTH_H_DM / GRID, "width_m": ROOM_W_DM / GRID,
                         "depth_m": CORRIDOR_DM / GRID},
            "core": {"x_m": ROOM_W_DM / GRID, "y_m": 0.0, "width_m": CORE_DM / GRID,
                     "depth_m": D_DM / GRID}}
