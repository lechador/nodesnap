"""Assemble bounded solver output while preserving domain entity identities."""
from __future__ import annotations

from domain.architecture import rect, stable_id
from domain.models import Space
from .layout import solve_floor


def generate_floor(snapshot, level_name: str, rooms: list[dict]) -> dict:
    if snapshot.building_program is not None:
        from domain.building import regenerate_program_floor
        return regenerate_program_floor(snapshot, level_name, rooms)
    level = next((l for l in snapshot.levels if l.name == level_name), None)
    ground = next((l for l in snapshot.levels if l.name == "ground"), None)
    if (level is None or ground is None or level.name in {"basement", "roof"}
            or level.elevation_m < ground.elevation_m
            or sum(s.classification == "principal" for s in snapshot.spaces if s.level_id == level.id) != 6
            or len(rooms) != 6):
        return {"spaces": None, "solver_status": "MODEL_INVALID"}
    solved = solve_floor(rooms)
    if not solved["placements"]:
        return {"spaces": None, "solver_status": solved["solver_status"], "settings": solved.get("settings")}
    existing = [s for s in snapshot.spaces if s.level_id == level.id]
    new_spaces = [s.model_copy(deep=True) for s in snapshot.spaces if s.level_id != level.id]
    matched = set()
    for index, p in enumerate(solved["placements"]):
        original = next((s for s in existing if s.name == p["name"] and s.id not in matched), None)
        if original is None:
            original = next((s for s in existing if s.use == p["use"] and s.classification == "principal" and s.id not in matched), None)
        identity = original.id if original else stable_id(snapshot.project_id, f"space:{level.id}:{p['name']}:{index}")
        matched.add(identity)
        new_spaces.append(Space(id=identity, level_id=level.id, name=p["name"], use=p["use"], classification="principal",
                                polygon=rect(p["x_m"], p["y_m"], p["width_m"], p["depth_m"]), target_area_m2=p["target_area_m2"]))
    # Keep fixed core and support identities. Seed owns aligned stair geometry.
    new_spaces.extend(s.model_copy(deep=True) for s in existing if s.classification == "support" and s.use != "circulation")
    corridor = next((s for s in existing if s.use == "circulation"), None)
    new_spaces.append(Space(id=corridor.id if corridor else stable_id(snapshot.project_id, f"corridor:{level.id}"),
                            level_id=level.id, name="Circulation", use="circulation", classification="support",
                            polygon=rect(0, 6.95, 18, 1.6)))
    # Leftover area remains explicit circulation rather than disappearing from
    # the gross area ledger or being misleadingly included as net room area.
    for side, y in (("south", 0.0), ("north", 8.55)):
        end = max((p["x_m"] + p["width_m"] for p in solved["placements"] if p["strip"] == side), default=0.0)
        if 15 - end > 1e-6:
            new_spaces.append(Space(id=stable_id(snapshot.project_id, f"circulation:{level.id}:{side}"), level_id=level.id,
                name=f"{side.title()} circulation", use="circulation", classification="support", polygon=rect(end, y, 15-end, 6.95)))
    return {"spaces": new_spaces, "solver_status": solved["solver_status"], "settings": solved["settings"]}
