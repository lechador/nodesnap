"""Planar geometry validation — spec A5/E4. Shapely checks, SI metres."""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon
from shapely.validation import explain_validity


def polygon_area_m2(ring: list[list[float]]) -> float:
    return float(Polygon(ring).area)


def validate_spaces(spaces, envelope=None) -> list[dict]:
    """Return structured issues; empty list = geometrically valid."""
    issues: list[dict] = []
    floor_plate = Polygon(envelope or [[0,0],[18,0],[18,15.5],[0,15.5],[0,0]])
    polys = {}
    for s in spaces:
        if (len(s.polygon) < 4 or s.polygon[0] != s.polygon[-1]
                or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in s.polygon)):
            issues.append({"code": "INVALID_GEOMETRY", "object_id": s.id,
                           "message": f"{s.name}: coordinates must be a closed ring of finite XY pairs"})
            continue
        p = Polygon(s.polygon)
        polys[s.id] = p
        if not p.is_valid:
            issues.append({"code": "INVALID_GEOMETRY", "object_id": s.id,
                           "message": f"{s.name}: {explain_validity(p)}"})
        if p.area <= 0:
            issues.append({"code": "INVALID_GEOMETRY", "object_id": s.id,
                           "message": f"{s.name}: non-positive area"})
        minx, miny, maxx, maxy = p.bounds
        if not floor_plate.buffer(1e-8).covers(p):
            issues.append({"code": "OUTSIDE_ENVELOPE", "object_id": s.id,
                           "message": f"{s.name}: outside the declared floor plate"})
    ids = list(polys)
    level_of = {s.id: s.level_id for s in spaces}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if level_of[ids[i]] != level_of[ids[j]]:
                continue
            a, b = polys[ids[i]], polys[ids[j]]
            if a.is_valid and b.is_valid and a.intersection(b).area > 1e-6:
                issues.append({"code": "OVERLAP", "object_id": ids[i],
                               "message": f"spaces {ids[i]} and {ids[j]} overlap"})
    return issues


def area_schedule(snapshot) -> list[dict]:
    """Actual net areas vs program targets, per space. Never fudged to totals."""
    level_name = {l.id: l.label for l in snapshot.levels}
    rows = []
    metrics = {m.space_id: m for m in snapshot.architecture.space_metrics} if snapshot.architecture else {}
    for s in snapshot.spaces:
        zone = polygon_area_m2(s.polygon)
        actual = metrics[s.id].net_area_m2 if s.id in metrics else zone
        rows.append({
            "revision_id": snapshot.revision_id,
            "space_id": s.id, "level": level_name.get(s.level_id, "?"),
            "name": s.name, "use": s.use, "classification": s.classification,
            "actual_area_m2": round(actual, 4),
            "zone_area_m2": round(zone, 4),
            "area_basis": "clear_inside_wall_faces" if s.id in metrics else "legacy_zone_without_wall_deduction",
            "target_area_m2": s.target_area_m2,
            "delta_m2": (round(actual - s.target_area_m2, 4)
                         if s.target_area_m2 is not None else None),
        })
    return rows


def validate_snapshot(snapshot) -> list[dict]:
    """Geometric/topological checks only; no regulated adequacy claims."""
    issues = validate_spaces(snapshot.spaces, snapshot.envelope_polygon)
    levels = {level.id: level for level in snapshot.levels}
    spaces = {space.id: space for space in snapshot.spaces}
    invalid_levels = False
    if len(levels) != len(snapshot.levels) or len({level.name for level in snapshot.levels}) != len(snapshot.levels):
        issues.append({"code": "DUPLICATE_ID", "message": "Level identities and lookup names must be unique."})
        invalid_levels = True
    if len(spaces) != len(snapshot.spaces):
        issues.append({"code": "DUPLICATE_ID", "message": "Space identities must be unique."})
    for space in snapshot.spaces:
        if space.level_id not in levels:
            issues.append({"code": "INVALID_REFERENCE", "object_id": space.id, "message": "Space references an unknown level."})
            invalid_levels = True
    if any(not math.isfinite(level.elevation_m) for level in snapshot.levels):
        issues.append({"code": "INVALID_GEOMETRY", "message": "Level elevations must be finite."})
        invalid_levels = True
    else:
        ordered = sorted(snapshot.levels, key=lambda level: level.elevation_m)
        if any(upper.elevation_m - lower.elevation_m <= .25 for lower, upper in zip(ordered, ordered[1:])):
            issues.append({"code": "INVALID_VERTICAL_CONNECTION", "message": "Adjacent level elevations must leave positive space above the 0.25 m concept slab."})
            invalid_levels = True
        roofs = [level for level in ordered if level.name == "roof"]
        if roofs and (len(roofs) != 1 or roofs[0] != ordered[-1]):
            issues.append({"code": "INVALID_VERTICAL_CONNECTION", "message": "The roof must be the highest level."})
            invalid_levels = True
    if invalid_levels:
        return issues  # References/topology must be sound before traversing architecture.
    if snapshot.pool:
        pool = snapshot.pool
        values = [pool.water_length_m, pool.water_width_m, pool.water_depth_m, pool.origin_x_m, pool.origin_y_m]
        if not all(math.isfinite(v) for v in values) or min(values[:3]) <= 0:
            issues.append({"code": "INVALID_GEOMETRY", "object_id": pool.id, "message": "Pool dimensions must be finite and positive."})
        else:
            hall = next((s for s in snapshot.spaces if s.use == "pool_hall" and s.level_id == pool.level_id), None)
            water = Polygon([(pool.origin_x_m, pool.origin_y_m), (pool.origin_x_m + pool.water_length_m, pool.origin_y_m),
                             (pool.origin_x_m + pool.water_length_m, pool.origin_y_m + pool.water_width_m),
                             (pool.origin_x_m, pool.origin_y_m + pool.water_width_m)])
            if hall is None or not Polygon(hall.polygon).covers(water):
                issues.append({"code": "OUTSIDE_POOL_HALL", "object_id": pool.id, "message": "Pool water must remain inside its host pool hall."})
            elif snapshot.architecture:
                metric = next((m for m in snapshot.architecture.space_metrics if m.space_id == hall.id), None)
                if metric and not Polygon(metric.clear_polygon).buffer(1e-8).covers(water):
                    issues.append({"code": "POOL_WALL_INTERSECTION", "object_id": pool.id,
                                   "message": "Pool water intersects the pool hall wall; reduce its size or revise the hall first."})
    architecture = snapshot.architecture
    if not architecture:
        return issues  # Legacy snapshots keep their exact model and recorded scope.
    if architecture.revision_id != snapshot.revision_id:
        issues.append({"code": "STALE_REVISION", "message": "Architecture belongs to another revision."})
    issues.extend(i for i in architecture.issues if i["code"] in {"MISSING_VERTICAL_CONNECTION", "MISALIGNED_CORE", "OUTSIDE_METHOD_DOMAIN"})
    walls = {w.id: w for w in architecture.walls}
    graph = {key: set() for key in spaces}
    roots = set()
    if len(walls) != len(architecture.walls):
        issues.append({"code": "DUPLICATE_ID", "message": "Wall identities must be unique."})
    for opening in architecture.openings:
        wall = walls.get(opening.wall_id)
        if not wall:
            issues.append({"code": "INVALID_OPENING_HOST", "object_id": opening.id, "message": "Opening has no wall host."})
            continue
        length = math.dist(wall.start, wall.end)
        if (opening.offset_m < 0 or opening.offset_m + opening.width_m > length + 1e-7
                or opening.sill_height_m + opening.height_m > wall.height_m + 1e-7):
            issues.append({"code": "INVALID_OPENING_HOST", "object_id": opening.id, "message": "Opening extends beyond its wall host."})
        if opening.kind == "window":
            continue
        ids = [key for key in opening.space_ids if key in graph]
        if len(ids) == 2:
            a, b = ids
            graph[a].add(b); graph[b].add(a)
        elif len(ids) == 1:
            level = levels[wall.level_id]
            if level.name == "ground" and wall.exterior:
                roots.add(ids[0])
            if level.name == "roof":
                # An exterior stair door enters the open-air roof access zone.
                center = Point([(wall.start[i] + (wall.end[i]-wall.start[i]) *
                                 (opening.offset_m + opening.width_m / 2) / length) for i in (0, 1)])
                for other in snapshot.spaces:
                    if other.level_id == level.id and other.use == "roof_access" and Polygon(other.polygon).distance(center) <= wall.thickness_m + 1e-7:
                        graph[ids[0]].add(other.id); graph[other.id].add(ids[0])
    for stair in architecture.stairs:
        if (stair.lower_space_id not in graph or stair.upper_space_id not in graph
                or stair.lower_level_id not in levels or stair.upper_level_id not in levels):
            issues.append({"code": "INVALID_REFERENCE", "object_id": stair.id, "message": "Stair endpoints reference missing spaces or levels."})
            continue
        if (spaces[stair.lower_space_id].level_id != stair.lower_level_id
                or spaces[stair.upper_space_id].level_id != stair.upper_level_id):
            issues.append({"code": "INVALID_REFERENCE", "object_id": stair.id, "message": "Stair endpoint spaces belong to different levels than its declared endpoints."})
            continue
        graph[stair.lower_space_id].add(stair.upper_space_id)
        graph[stair.upper_space_id].add(stair.lower_space_id)
        rise = levels[stair.upper_level_id].elevation_m - levels[stair.lower_level_id].elevation_m
        if rise <= 0 or not math.isclose(stair.riser_count * stair.riser_height_m, rise, abs_tol=1e-8):
            issues.append({"code": "INVALID_VERTICAL_CONNECTION", "object_id": stair.id, "message": "Stair rise does not reach its target level."})
    outdoor = [s for s in snapshot.spaces if s.use in {"roof_terrace", "roof_access"}]
    for a in outdoor:
        for b in outdoor:
            if a.id != b.id and Polygon(a.polygon).boundary.intersection(Polygon(b.polygon).boundary).length >= .9:
                graph[a.id].add(b.id)
    visited, pending = set(roots), list(roots)
    while pending:
        current = pending.pop()
        for neighbor in graph[current] - visited:
            visited.add(neighbor); pending.append(neighbor)
    for key in graph.keys() - visited:
        issues.append({"code": "DISCONNECTED_SPACE", "object_id": key,
                       "message": f"{spaces[key].name} has no modeled door/stair route from the entrance."})
    for metric in architecture.space_metrics:
        if metric.net_area_m2 <= 0 or min(metric.clear_width_m, metric.clear_depth_m) <= 0:
            issues.append({"code": "INVALID_CLEAR_DIMENSION", "object_id": metric.space_id,
                           "message": "Wall thickness consumes the entire room width or depth."})
    return issues
