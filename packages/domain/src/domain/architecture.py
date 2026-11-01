"""Deterministic architecture for the bounded orthogonal concept grammar.

All coordinates are metres in canonical XY, Z up. These are assumed concept
assemblies, NOT structural section choices or building-code determinations.
External walls sit inside the declared outer envelope; internal walls are
centered on space-zone boundaries. The clear room ledger subtracts thickness.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict

from .models import Architecture, Opening, Slab, SpaceMetrics, Stair, Wall, WallAssembly

EPS = 1e-7
OUTDOOR = {"roof_terrace", "roof_access"}


def stable_id(project_id: str, key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nodesnap:{project_id}:{key}"))


def rect(x, y, w, d):
    return [[x, y], [x + w, y], [x + w, y + d], [x, y + d], [x, y]]


def bounds(space):
    return (min(p[0] for p in space.polygon), min(p[1] for p in space.polygon),
            max(p[0] for p in space.polygon), max(p[1] for p in space.polygon))


def _area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))) / 2


def _is_rectangle(space):
    x0, y0, x1, y1 = bounds(space)
    return (len(space.polygon) == 5 and len({tuple(p) for p in space.polygon}) == 4
            and all((abs(x - x0) < EPS or abs(x - x1) < EPS)
                    and (abs(y - y0) < EPS or abs(y - y1) < EPS)
                    for x, y in space.polygon))


def enrich_snapshot(snapshot):
    """Derive a new snapshot's architecture in place; never call on stored history.

    Repeat execution is deterministic, including stable entity identities. The
    caller sets the revision identity first and hashes after this derivation.
    """
    if (snapshot.site_layout is not None
            or snapshot.building_program and (snapshot.building_program.yard or snapshot.building_program.garage)
            or snapshot.pool and snapshot.pool.location == "outdoor"):
        from .site import coordinate_site
        coordinate_site(snapshot)
    envelope = snapshot.envelope_polygon or rect(0, 0, 18, 15.5)
    ex0, ey0 = min(p[0] for p in envelope), min(p[1] for p in envelope)
    ex1, ey1 = max(p[0] for p in envelope), max(p[1] for p in envelope)
    project = snapshot.project_id
    sid = lambda key: stable_id(project, key)
    material = {"limestone_oak": "stone", "warm_concrete": "concrete", "white_stucco": "plaster"}[snapshot.material_palette]
    architecture = Architecture(revision_id=snapshot.revision_id)
    architecture.assemblies = [
        WallAssembly(id=sid("assembly:exterior"), name="300 mm concept envelope", thickness_m=.30, material=material),
        WallAssembly(id=sid("assembly:interior"), name="150 mm concept partition", thickness_m=.15, material="plaster"),
        WallAssembly(id=sid("assembly:basement"), name="300 mm basement concept enclosure — reinforcement unresolved", thickness_m=.30, material="concrete"),
        WallAssembly(id=sid("assembly:guard"), name="Concept glass guard — design and anchorage unresolved", thickness_m=.06, material="glass"),
    ]
    levels = sorted(snapshot.levels, key=lambda l: l.elevation_m)
    by_id = {s.id: s for s in snapshot.spaces}
    level_spaces = {l.id: [s for s in snapshot.spaces if s.level_id == l.id] for l in levels}
    for i, level in enumerate(levels):
        spaces = level_spaces[level.id]
        enclosed = [s for s in spaces if s.use not in OUTDOOR]
        height = (levels[i + 1].elevation_m - level.elevation_m - .25) if i + 1 < len(levels) else 2.6
        groups = defaultdict(list)
        for space in enclosed:
            if not _is_rectangle(space):
                architecture.issues.append({"code": "OUTSIDE_METHOD_DOMAIN", "object_id": space.id,
                                           "message": "Architectural wall derivation supports rectangular zones only."})
                continue
            x0, y0, x1, y1 = bounds(space)
            for axis, line, lo, hi, side in [("h", y0, x0, x1, "south"), ("h", y1, x0, x1, "north"),
                                              ("v", x0, y0, y1, "west"), ("v", x1, y0, y1, "east")]:
                groups[(axis, round(line, 7))].append((lo, hi, space.id, side))
        # Split common boundaries at T junctions; exactly one wall owns each span.
        for (axis, line), edges in sorted(groups.items()):
            breaks = sorted(set(round(v, 7) for edge in edges for v in edge[:2]))
            for lo, hi in zip(breaks, breaks[1:]):
                if hi - lo < EPS:
                    continue
                midpoint = (lo + hi) / 2
                owners = sorted([e for e in edges if e[0] - EPS < midpoint < e[1] + EPS], key=lambda e: e[2])
                if not owners:
                    continue
                ids = sorted({e[2] for e in owners})
                exterior = (axis == "h" and (abs(line - ey0) < EPS or abs(line - ey1) < EPS)
                            or axis == "v" and (abs(line - ex0) < EPS or abs(line - ex1) < EPS)
                            or level.name == "roof")
                thickness = .30 if exterior else .15
                offset = 0.0
                if exterior and len(ids) == 1:
                    offset = thickness / 2 * (1 if owners[0][3] in ("south", "west") else -1)
                start = [lo, line + offset] if axis == "h" else [line + offset, lo]
                end = [hi, line + offset] if axis == "h" else [line + offset, hi]
                kind = "basement" if exterior and level.name == "basement" else "exterior" if exterior else "interior"
                mat = "concrete" if kind == "basement" else material if exterior else "plaster"
                # The boundary's room identity and side remain stable on resizing.
                key = f"wall:{level.id}:{':'.join(ids)}:{axis}:{owners[0][3]}"
                # Multiple fragments between the same owners are uncommon but legal.
                existing = sum(1 for wall in architecture.walls if wall.id == sid(key))
                if existing:
                    key += f":{lo:.7f}"
                architecture.walls.append(Wall(id=sid(key), level_id=level.id, start=start, end=end,
                    thickness_m=thickness, height_m=height, exterior=exterior,
                    role="enclosure" if exterior else "partition", material=mat,
                    assembly_id=sid(f"assembly:{kind}"), space_ids=ids))

        for space in spaces:
            x0, y0, x1, y1 = bounds(space)
            if space.use in OUTDOOR:
                clear = space.polygon
            else:
                # Exterior-face coordinates include the full envelope thickness;
                # shared zone boundaries include half each partition thickness.
                west = .30 if abs(x0 - ex0) < EPS or level.name == "roof" else .075
                east = .30 if abs(x1 - ex1) < EPS or level.name == "roof" else .075
                south = .30 if abs(y0 - ey0) < EPS or level.name == "roof" else .075
                north = .30 if abs(y1 - ey1) < EPS or level.name == "roof" else .075
                clear = rect(x0 + west, y0 + south, max(0, x1 - x0 - west - east), max(0, y1 - y0 - south - north))
            cx = [p[0] for p in clear]; cy = [p[1] for p in clear]
            architecture.space_metrics.append(SpaceMetrics(space_id=space.id, clear_polygon=clear,
                zone_area_m2=_area(space.polygon), net_area_m2=_area(clear),
                clear_width_m=max(cx) - min(cx), clear_depth_m=max(cy) - min(cy)))

        holes = []
        if i > 0:
            stair_space = next((s for s in spaces if s.use == "stairs_service"), None)
            if stair_space:
                metric = next(m for m in architecture.space_metrics if m.space_id == stair_space.id)
                holes.append(metric.clear_polygon)
        if snapshot.pool and snapshot.pool.location == "indoor" and snapshot.pool.level_id == level.id:
            pool = snapshot.pool
            holes.append(rect(pool.origin_x_m, pool.origin_y_m, pool.water_length_m, pool.water_width_m))
        architecture.slabs.append(Slab(id=sid(f"slab:{level.id}"), level_id=level.id,
            polygon=envelope, holes=holes, thickness_m=.25,
            kind="roof" if level.name == "roof" else "floor"))
        if level.name == "roof":
            stair_enclosure = next((s for s in spaces if s.use == "stairs_service"), None)
            if stair_enclosure:
                architecture.slabs.append(Slab(id=sid(f"slab:{level.id}:stair_cover"), level_id=level.id,
                    elevation_m=level.elevation_m + height + .18,
                    polygon=stair_enclosure.polygon, thickness_m=.18, kind="roof"))

    def add_opening(wall, kind, width, height=2.2, sill=0.0):
        length = math.dist(wall.start, wall.end)
        width = min(width, length - .30)
        if width <= .4:
            return
        architecture.openings.append(Opening(id=sid(f"opening:{wall.id}:{kind}"), wall_id=wall.id,
            kind=kind, offset_m=(length - width) / 2, width_m=width,
            height_m=min(height, wall.height_m - .15 - sill), sill_height_m=sill, space_ids=wall.space_ids))

    for wall in architecture.walls:
        owners = [by_id[k] for k in wall.space_ids]
        length = math.dist(wall.start, wall.end)
        level = next(l for l in levels if l.id == wall.level_id)
        if len(owners) == 2 and length >= 1.2:
            uses = {s.use for s in owners}
            if uses == {"circulation"} and snapshot.building_program is not None:
                add_opening(wall,"passage",length-.30,height=wall.height_m)
            elif "circulation" in uses or "roof_access" in uses:
                add_opening(wall, "door", .95)
            elif uses <= {"living", "dining", "kitchen"}:
                add_opening(wall, "passage", min(2.4, length - .6), 2.65)
        elif wall.exterior and level.name != "basement":
            owner = owners[0]
            if owner.use == "circulation" and level.name == "ground" and wall.start[0] < .4:
                add_opening(wall, "door", 1.1, 2.5)
            elif owner.use == "stairs_service" and level.name == "roof" and abs(wall.start[1] - bounds(owner)[3]) < .31 and abs(wall.start[1]-wall.end[1]) < EPS:
                add_opening(wall, "door", .95, 2.25)
            elif owner.classification == "principal" and length >= 1.6:
                add_opening(wall, "window", min(4.4, length - .8), 2.35, .45)
            elif owner.use not in {"circulation", "stairs_service"} and length >= 2:
                add_opening(wall, "window", min(1.8, length - .8), 1.15, 1.35)

    # Connect remaining support rooms through actual shared boundaries. Never
    # give one bedroom its only access through another bedroom.
    connected = {k for opening in architecture.openings if opening.kind != "window" for k in opening.space_ids}
    for space in sorted(snapshot.spaces, key=lambda s: (s.classification != "principal", s.id)):
        if space.id in connected or space.use in OUTDOOR:
            continue
        candidates = []
        for wall in architecture.walls:
            if len(wall.space_ids) != 2 or space.id not in wall.space_ids or math.dist(wall.start, wall.end) < 1.2:
                continue
            other = by_id[next(k for k in wall.space_ids if k != space.id)]
            if other.use == "stairs_service" or (space.use == "bedroom" and other.use == "bedroom"):
                continue
            candidates.append((other.id not in connected, other.classification == "principal", wall.id, wall))
        if candidates:
            wall = min(candidates, key=lambda p: p[:3])[-1]
            add_opening(wall, "door", .9)
            connected.update(wall.space_ids)

    for lower, upper in zip(levels, levels[1:]):
        lower_space = next((s for s in level_spaces[lower.id] if s.use == "stairs_service"), None)
        upper_space = next((s for s in level_spaces[upper.id] if s.use == "stairs_service"), None)
        if upper.name == "roof" and not upper_space and not snapshot.roof_terrace_area_m2:
            continue  # A bare unoccupied roof has no invented stair access.
        if not lower_space or not upper_space:
            architecture.issues.append({"code": "MISSING_VERTICAL_CONNECTION", "object_id": lower.id,
                "message": f"A continuous stair between {lower.label} and {upper.label} is not modeled."})
            continue
        if lower_space.polygon != upper_space.polygon:
            architecture.issues.append({"code": "MISALIGNED_CORE", "object_id": lower_space.id,
                "message": "Stair footprints must align between adjacent levels."})
            continue
        x0, y0, x1, y1 = bounds(lower_space)
        rise = upper.elevation_m - lower.elevation_m
        risers = max(2, math.ceil(rise / .18 / 2) * 2)
        run = y1 - y0 - 1.2 - .15
        architecture.stairs.append(Stair(id=sid(f"stair:{lower.id}:{upper.id}"),
            lower_level_id=lower.id, upper_level_id=upper.id, lower_space_id=lower_space.id,
            upper_space_id=upper_space.id, polygon=rect(x0 + .075, y0 + .075, x1 - x0 - .15, y1 - y0 - .15),
            width_m=1.2, riser_count=risers, riser_height_m=rise / risers,
            tread_depth_m=run / (risers // 2 - 1), flight_run_m=run, landing_depth_m=1.2,
            orientation="south"))

    # Generate outdoor guards from actual adjacent rectangles. Shared access
    # boundaries and the stair enclosure remain open; no template coordinates.
    if snapshot.envelope_polygon is not None:
        outdoor = [s for s in snapshot.spaces if s.use in OUTDOOR]
        for space in outdoor:
            neighbors = [other for other in snapshot.spaces if other.level_id == space.level_id
                         and other.id != space.id and other.use in OUTDOOR | {"stairs_service"}]
            for index, (a,b) in enumerate(zip(space.polygon,space.polygon[1:])):
                horizontal = abs(a[1]-b[1]) < EPS
                axis = 0 if horizontal else 1
                fixed = a[1-axis]
                lo,hi = sorted((a[axis],b[axis]))
                spans = [(lo,hi)]
                for other in neighbors:
                    for c,d in zip(other.polygon,other.polygon[1:]):
                        if abs(c[1-axis]-fixed)>EPS or abs(d[1-axis]-fixed)>EPS:
                            continue
                        cut0,cut1 = sorted((c[axis],d[axis]))
                        spans = [(u,v) for x,y in spans for u,v in ((x,min(y,cut0)),(max(x,cut1),y)) if v-u>EPS]
                for part,(u,v) in enumerate(spans):
                    start,end = ([u,fixed],[v,fixed]) if horizontal else ([fixed,u],[fixed,v])
                    architecture.walls.append(Wall(id=sid(f"guard:{space.id}:{index}:{part}"),level_id=space.level_id,
                        start=start,end=end,thickness_m=.06,height_m=1.1,exterior=True,role="guard",material="glass",
                        assembly_id=sid("assembly:guard"),space_ids=[space.id]))
    else:
        # Terrace guards are assumed geometry and keep a real access gap. Their
        # safety/anchorage remains a review task, not a passing regulated check.
        for space in snapshot.spaces:
            if space.use != "roof_terrace":
                continue
            for index, (a, b) in enumerate(zip(space.polygon, space.polygon[1:])):
                x0, y0, x1, y1 = bounds(space)
                spans = [(a, b)]
                if abs(a[0] - x1) < EPS and abs(b[0] - x1) < EPS and y1 >= 8.55:
                    spans = [([x1, y0], [x1, 6.95]), ([x1, 8.55], [x1, y1])]
                for part, (start, end) in enumerate(spans):
                    if math.dist(start, end) < EPS:
                        continue
                    architecture.walls.append(Wall(id=sid(f"guard:{space.id}:{index}:{part}"),
                        level_id=space.level_id, start=start, end=end, thickness_m=.06, height_m=1.1,
                        exterior=True, role="guard", material="glass", assembly_id=sid("assembly:guard"), space_ids=[space.id]))
        for space in snapshot.spaces:
            if space.use != "roof_access":
                continue
            x0, y0, x1, y1 = bounds(space)
            # Guard the access walk while leaving its terrace connection and
            # stair-enclosure door unobstructed.
            for index, (start, end) in enumerate([([x0, y1], [x1, y1]),
                                                 ([x1, y0], [x1, y1]),
                                                 ([x0, y0], [15.0, y0])]):
                if math.dist(start, end) < EPS:
                    continue
                architecture.walls.append(Wall(id=sid(f"guard:{space.id}:{index}"), level_id=space.level_id,
                    start=start, end=end, thickness_m=.06, height_m=1.1, exterior=True, role="guard",
                    material="glass", assembly_id=sid("assembly:guard"), space_ids=[space.id]))
    architecture.issues.extend([
        {"code": "UNVERIFIED_SOURCE", "field": "architectural_code_checks", "message": "Stair headroom, egress, guards, fire separation and accessibility require sourced project-specific checks."},
        {"code": "MISSING_INPUT", "field": "assemblies", "message": "Wall, slab, glazing and finish sizes are demonstration assumptions; structural and envelope design is unresolved."},
    ])
    snapshot.architecture = architecture
    snapshot.schema_version = "0.2.0"
    return snapshot
