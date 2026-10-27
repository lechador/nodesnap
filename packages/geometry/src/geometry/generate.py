"""Assemble a generated floor into canonical Spaces — spec A5.2 stages 4-6
(bounded: circulation is the reserved corridor band; doors/openings and
wall-thickness derivation remain M2 follow-ups, recorded in build-status)."""
from __future__ import annotations

from domain.models import Space
from .layout import solve_floor

ENVELOPE_W_M, ENVELOPE_D_M = 18.0, 15.5


def _rect(level_id, name, use, classification, x, y, w, d, target=None):
    ring = [[x, y], [x + w, y], [x + w, y + d], [x, y + d], [x, y]]
    return Space(level_id=level_id, name=name, use=use, classification=classification,
                 polygon=ring, target_area_m2=target)


def generate_floor(snapshot, level_name: str, rooms: list[dict]) -> dict:
    """Returns {spaces, solver_status}; spaces replace that level's spaces."""
    level = next(l for l in snapshot.levels if l.name == level_name)
    solved = solve_floor(rooms)
    if not solved["placements"]:
        return {"spaces": None, "solver_status": solved["solver_status"]}
    keep = [s for s in snapshot.spaces if s.level_id != level.id]
    support = [s for s in snapshot.spaces
               if s.level_id == level.id and s.classification == "support"
               and s.use not in ("circulation",)]
    new_spaces = list(keep)
    for p in solved["placements"]:
        new_spaces.append(_rect(level.id, p["name"], p["use"], "principal",
                                p["x_m"], p["y_m"], p["width_m"], p["depth_m"],
                                target=p["target_area_m2"]))
    c = solved["corridor"]
    new_spaces.append(_rect(level.id, "Circulation", "circulation", "support",
                            c["x_m"], c["y_m"], c["width_m"], c["depth_m"]))
    k = solved["core"]
    # stairs occupy the first 5.5 m of the core; existing support rooms stack after
    new_spaces.append(_rect(level.id, "Stairs / service core", "stairs_service",
                            "support", k["x_m"], 0.0, k["width_m"], 5.5))
    y = 5.5
    for s in support:
        if s.use in ("stairs_service",):
            continue
        xs = [pt[0] for pt in s.polygon]; ys = [pt[1] for pt in s.polygon]
        h = max(ys) - min(ys)
        if y + h > ENVELOPE_D_M:
            h = ENVELOPE_D_M - y
        if h <= 0:
            break
        new_spaces.append(_rect(level.id, s.name, s.use, "support",
                                k["x_m"], y, k["width_m"], h,
                                target=s.target_area_m2))
        y += h
    return {"spaces": new_spaces, "solver_status": solved["solver_status"]}
