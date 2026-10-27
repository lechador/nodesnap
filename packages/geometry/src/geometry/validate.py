"""Planar geometry validation — spec A5/E4. Shapely checks, SI metres."""
from __future__ import annotations

from shapely.geometry import Polygon
from shapely.validation import explain_validity


def polygon_area_m2(ring: list[list[float]]) -> float:
    return float(Polygon(ring).area)


def validate_spaces(spaces) -> list[dict]:
    """Return structured issues; empty list = geometrically valid."""
    issues: list[dict] = []
    polys = {}
    for s in spaces:
        p = Polygon(s.polygon)
        polys[s.id] = p
        if not p.is_valid:
            issues.append({"code": "INVALID_GEOMETRY", "object_id": s.id,
                           "message": f"{s.name}: {explain_validity(p)}"})
        if p.area <= 0:
            issues.append({"code": "INVALID_GEOMETRY", "object_id": s.id,
                           "message": f"{s.name}: non-positive area"})
        minx, miny, maxx, maxy = p.bounds
        if minx < -1e-9 or miny < -1e-9 or maxx > 18.0 + 1e-9 or maxy > 15.5 + 1e-9:
            issues.append({"code": "OUTSIDE_ENVELOPE", "object_id": s.id,
                           "message": f"{s.name}: outside the 18.0 x 15.5 m floor plate"})
    ids = list(polys)
    level_of = {s.id: s.level_id for s in spaces}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if level_of[ids[i]] != level_of[ids[j]]:
                continue
            a, b = polys[ids[i]], polys[ids[j]]
            if a.intersection(b).area > 1e-6:
                issues.append({"code": "OVERLAP", "object_id": ids[i],
                               "message": f"spaces {ids[i]} and {ids[j]} overlap"})
    return issues


def area_schedule(snapshot) -> list[dict]:
    """Actual net areas vs program targets, per space. Never fudged to totals."""
    level_name = {l.id: l.label for l in snapshot.levels}
    rows = []
    for s in snapshot.spaces:
        actual = polygon_area_m2(s.polygon)
        rows.append({
            "space_id": s.id, "level": level_name.get(s.level_id, "?"),
            "name": s.name, "use": s.use, "classification": s.classification,
            "actual_area_m2": round(actual, 4),
            "target_area_m2": s.target_area_m2,
            "delta_m2": (round(actual - s.target_area_m2, 4)
                         if s.target_area_m2 is not None else None),
        })
    return rows
