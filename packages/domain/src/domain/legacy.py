"""Explicit, bounded conversion of the original 0.1 villa's service layout.

This is not a seed replacement or a load-time model coercion. Call only on a
candidate copied from an immutable revision, before assigning the new revision
identity and deriving its architecture. Unknown layouts are left unchanged.
"""
from __future__ import annotations

import math

from .architecture import bounds, rect, stable_id
from .models import Assumption, FT2_TO_M2, ProjectSnapshot, Space

EPS = 1e-6


def _rectangle(space):
    points = space.polygon
    if len(points) != 5 or len({tuple(p) for p in points[:-1]}) != 4:
        return False
    return all((abs(a[0]-b[0]) < EPS) != (abs(a[1]-b[1]) < EPS)
               for a, b in zip(points, points[1:]))


def _matches(space, expected):
    return _rectangle(space) and all(abs(a-b) < EPS for a, b in zip(bounds(space), expected))


def upgrade_legacy_architecture(snapshot: ProjectSnapshot) -> ProjectSnapshot:
    """Repair recognized service zones on a candidate; preserve every old ID.

    All recognition runs before mutation. Existing principal rooms, pool fields,
    terrace, site, brief, levels and metadata remain exactly as stored. The only
    changed polygons and every new zone are recorded as concept assumptions.
    The caller must derive, validate, hash and persist a *new* revision.
    """
    def unsupported(reason):
        raise ValueError("This saved villa needs a reviewed architectural conversion: " + reason
                         + ". Its saved layout has not been replaced.")

    if snapshot.schema_version != "0.1.0" or snapshot.architecture is not None:
        unsupported("it is not an original 0.1 villa")
    if snapshot.building_program is not None or snapshot.envelope_polygon is not None:
        unsupported("a custom building envelope or program is present")
    levels = {level.name: level for level in snapshot.levels}
    if (len(snapshot.levels) != 4 or set(levels) != {"basement", "ground", "upper", "roof"}
            or len({level.id for level in snapshot.levels}) != 4):
        unsupported("the original four-level stack was changed")
    ordered = [levels[name] for name in ("basement", "ground", "upper", "roof")]
    if any(not math.isfinite(level.elevation_m) for level in ordered) or any(
            not 2.6 <= upper.elevation_m-lower.elevation_m <= 4.5
            for lower, upper in zip(ordered, ordered[1:])):
        unsupported("the level heights are outside the connected concept method")
    if abs(levels["ground"].elevation_m) > EPS or levels["basement"].elevation_m >= 0:
        unsupported("the original ground and basement datum was changed")
    if len({space.id for space in snapshot.spaces}) != len(snapshot.spaces):
        unsupported("space identities are not unique")
    level_ids = {level.id for level in snapshot.levels}
    if any(space.level_id not in level_ids for space in snapshot.spaces):
        unsupported("a room references an unknown level")
    changes = []
    additions = []

    def one(spaces, use):
        matches = [space for space in spaces if space.use == use]
        if len(matches) != 1:
            unsupported(f"expected one original {use} zone")
        return matches[0]

    def adjust(space, old_bounds, new_polygon):
        if not _matches(space, old_bounds):
            unsupported(f"the {space.use} service footprint was edited")
        changes.append((space, new_polygon))

    def add(level, key, name, use, polygon):
        identity = stable_id(snapshot.project_id, f"legacy-architecture:v1:{level.id}:{key}")
        if identity in {space.id for space in snapshot.spaces}:
            unsupported("a conversion zone identity already exists")
        additions.append(Space(id=identity, level_id=level.id, name=name, use=use,
                               classification="support", polygon=polygon))

    for name, uses, target_ft2 in (("ground", ("bathroom", "service"), (180, 120)),
                                 ("upper", ("dressing", "bathroom"), (300, 360))):
        spaces = [space for space in snapshot.spaces if space.level_id == levels[name].id]
        principal = [space for space in spaces if space.classification == "principal"]
        support = [space for space in spaces if space.classification == "support"]
        if len(support) != 4 or len(principal)+len(support) != len(spaces) or not 2 <= len(principal) <= 20:
            unsupported(f"the {name} room classifications differ from the original strip layout")
        # Accept edited names, targets and strip widths while retaining the exact
        # principal polygons. Do not silently regenerate the six seed rooms.
        recognized = set()
        for y0, y1 in ((0.0, 6.95), (8.55, 15.5)):
            strip = sorted([space for space in principal if _rectangle(space)
                            and abs(bounds(space)[1]-y0) < EPS and abs(bounds(space)[3]-y1) < EPS],
                           key=lambda space: bounds(space)[0])
            cursor = 0.0
            if not strip:
                unsupported(f"the {name} principal-room strips were changed")
            for space in strip:
                x0, _, x1, _ = bounds(space)
                if abs(x0-cursor) > EPS or x1-x0 < 1.5:
                    unsupported(f"the {name} principal rooms do not form the original connected strips")
                cursor = x1
                recognized.add(space.id)
            if abs(cursor-15.0) > EPS:
                unsupported(f"the {name} principal rooms no longer meet the service strip")
        if recognized != {space.id for space in principal}:
            unsupported(f"the {name} principal-room geometry is outside the strip method")
        adjust(one(support, "circulation"), (0, 6.95, 15, 8.55), rect(0, 6.95, 18, 1.6))
        adjust(one(support, "stairs_service"), (15, 0, 18, 5.5), rect(15, 2.8, 3, 4.15))
        sy = 5.5
        for index, (use, ft2) in enumerate(zip(uses, target_ft2)):
            height = min(max(1.8, ft2*FT2_TO_M2/3), 15.5-sy)
            new_polygon = rect(15, 0, 3, 2.8) if index == 0 else rect(15, 8.55, 3, 6.95)
            adjust(one(support, use), (15, sy, 18, sy+height), new_polygon)
            sy += height

    basement = levels["basement"]
    spaces = [space for space in snapshot.spaces if space.level_id == basement.id]
    if len(spaces) != 4 or any(space.classification != "support" for space in spaces):
        unsupported("the original basement service layout was changed")
    hall = one(spaces, "pool_hall")
    if not _matches(hall, (0, 0, 12, 15.5)):
        unsupported("the original pool-hall footprint was changed")
    pool = snapshot.pool
    if pool is None or pool.level_id != basement.id:
        unsupported("the original basement pool is missing or moved")
    quantities = [pool.origin_x_m, pool.origin_y_m, pool.water_length_m, pool.water_width_m, pool.water_depth_m]
    if (not all(math.isfinite(value) for value in quantities) or min(quantities[2:]) <= 0
            or pool.origin_x_m < .30-EPS or pool.origin_y_m < .30-EPS
            or pool.origin_x_m+pool.water_length_m > 11.925+EPS
            or pool.origin_y_m+pool.water_width_m > 15.20+EPS):
        unsupported("the saved pool intersects the assumed wall thickness; its dimensions and position are retained")
    adjust(one(spaces, "plant"), (12, 0, 18, 6.2), rect(12, 0, 3, 6.95))
    adjust(one(spaces, "changing"), (12, 6.2, 18, 10.1), rect(12, 8.55, 6, 3.45))
    adjust(one(spaces, "storage"), (12, 10.1, 18, 15.5), rect(12, 12, 6, 3.5))
    add(basement, "equipment", "Equipment service", "service", rect(15, 0, 3, 2.8))
    add(basement, "stairs", "Stairs / service core", "stairs_service", rect(15, 2.8, 3, 4.15))
    add(basement, "circulation", "Basement circulation", "circulation", rect(12, 6.95, 6, 1.6))

    roof = levels["roof"]
    spaces = [space for space in snapshot.spaces if space.level_id == roof.id]
    if len(spaces) != 1 or spaces[0].use != "roof_terrace" or not _rectangle(spaces[0]):
        unsupported("the original roof terrace layout was changed")
    x0, y0, x1, y1 = bounds(spaces[0])
    if abs(x0) > EPS or abs(y0) > EPS or not 1.5 <= x1 <= 15 or not 8.55 <= y1 <= 15.5:
        unsupported("the terrace cannot meet the retained stair/access route")
    add(roof, "stairs", "Roof stair enclosure", "stairs_service", rect(15, 2.8, 3, 4.15))
    add(roof, "access", "Terrace access", "roof_access", rect(x1, 6.95, 18-x1, 1.6))

    assumption = Assumption(
        id=stable_id(snapshot.project_id, f"assumption:legacy-architecture:v1:{snapshot.revision_id}"),
        field="architecture.legacy_upgrade",
        value={"method": "original_villa_service_core_conversion_v1", "base_revision_id": snapshot.revision_id,
               "changed_space_polygons": [{"space_id": space.id, "before": space.polygon,
                                            "after": polygon} for space, polygon in changes],
               "added_spaces": [space.model_dump(mode="json") for space in additions],
               "assemblies_m": {"exterior_wall": .30, "partition": .15, "slab": .25},
               "stair_width_m": 1.2, "landing_depth_m": 1.2},
        rationale="Converted the recognized original villa into connected concept architecture. "
                  "Only the recorded support-room, circulation and stair footprints change; original "
                  "principal rooms, pool dimensions/position, terrace, level identities and site data are retained. "
                  "Support-room targets are preserved, so achieved-area differences remain visible. "
                  "Added stairs, access zones and assembly thicknesses are demonstration assumptions. "
                  "Structural capacity, stair headroom, egress, fire safety and accessibility require "
                  "project-specific professional review; no approval is established.")
    for space, polygon in changes:
        space.polygon = polygon
    snapshot.spaces.extend(additions)
    snapshot.assumptions.append(assumption)
    return snapshot
