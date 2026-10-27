"""Deterministic seed villa — spec A3. Exercises the full pipeline (M1).

Envelope 18.0 x 15.5 m = 279.0 m2 per above-ground floor (~3,003 ft2).
Strip layout: corridor band across the middle, rooms north/south of it,
stair/service core at the east end. Areas are computed from geometry,
not copied from targets — the schedule reports the difference.
"""
from __future__ import annotations

from domain.models import (Assumption, Brief, Level, PoolSystem,
                           ProjectSnapshot, SiteContext, Space)
from domain.models import FT2_TO_M2, new_id

W, D = 18.0, 15.5  # envelope width (x), depth (y), metres


def _rect(space_kw, level_id, x, y, w, d):
    ring = [[x, y], [x + w, y], [x + w, y + d], [x, y + d], [x, y]]
    return Space(level_id=level_id, polygon=ring, **space_kw)


def _floor(level_id, principal, support):
    """principal/support: list of (name, use, target_ft2). Returns spaces."""
    spaces = []
    corridor_h, core_w = 1.6, 3.0
    room_w = W - core_w
    # split principal rooms: first half north strip, rest south strip
    half = (len(principal) + 1) // 2
    strips = [(principal[:half], corridor_h + (D - corridor_h) / 2),  # north
              (principal[half:], 0.0)]                               # south
    # south strip occupies y in [0, (D-corridor)/2], north above corridor
    south_h = (D - corridor_h) / 2
    for rooms, _y in strips:
        pass
    # explicit placement: south strip y=0..south_h, corridor, north strip
    def place(rooms, y0, h):
        total_ft2 = sum(r[2] for r in rooms)
        x = 0.0
        for name, use, ft2 in rooms:
            w = room_w * (ft2 / total_ft2)
            spaces.append(_rect(
                dict(name=name, use=use, classification="principal",
                     target_area_m2=round(ft2 * FT2_TO_M2, 4)),
                level_id, x, y0, w, h))
            x += w
    place(principal[:half], south_h + corridor_h, D - south_h - corridor_h)
    place(principal[half:], 0.0, south_h)
    # corridor + core
    spaces.append(_rect(dict(name="Circulation", use="circulation",
                             classification="support",
                             target_area_m2=None),
                        level_id, 0.0, south_h, room_w, corridor_h))
    # east core strip subdivided along y: stairs segment, then support rooms
    spaces.append(_rect(dict(name="Stairs / service core", use="stairs_service",
                             classification="support", target_area_m2=None),
                        level_id, room_w, 0.0, core_w, 5.5))
    sy = 5.5
    for name, use, ft2 in support:
        h = max(1.8, (ft2 * FT2_TO_M2) / core_w)
        h = min(h, D - sy)
        if h <= 0:
            break
        spaces.append(_rect(
            dict(name=name, use=use, classification="support",
                 target_area_m2=round(ft2 * FT2_TO_M2, 4)),
            level_id, room_w, sy, core_w, h))
        sy += h
    return spaces


GROUND_PRINCIPAL = [
    ("Main living room", "living", 620), ("Dining room", "dining", 300),
    ("Kitchen", "kitchen", 340), ("Family lounge", "family", 360),
    ("Study / home office", "study", 200), ("Guest bedroom", "bedroom", 260),
]
GROUND_SUPPORT = [("Bathrooms / WCs", "bathroom", 180),
                  ("Pantry / laundry", "service", 120)]
UPPER_PRINCIPAL = [
    ("Primary bedroom", "bedroom", 420), ("Bedroom 2", "bedroom", 260),
    ("Bedroom 3", "bedroom", 240), ("Bedroom 4", "bedroom", 240),
    ("Library / lounge", "library", 380), ("Flexible studio / fitness", "studio", 300),
]
UPPER_SUPPORT = [("Dressing spaces", "dressing", 300),
                 ("Bathrooms", "bathroom", 360)]


def build_seed(project_id: str) -> ProjectSnapshot:
    basement = Level(name="basement", label="Basement", elevation_m=-3.2)
    ground = Level(name="ground", label="Ground floor", elevation_m=0.0)
    upper = Level(name="upper", label="Upper floor", elevation_m=3.4)
    roof = Level(name="roof", label="Roof / terrace", elevation_m=6.8)

    spaces: list[Space] = []
    spaces += _floor(ground.id, GROUND_PRINCIPAL, GROUND_SUPPORT)
    spaces += _floor(upper.id, UPPER_PRINCIPAL, UPPER_SUPPORT)
    # basement: pool hall + support (pool water is a PoolSystem, not a room)
    spaces.append(_rect(dict(name="Pool hall / deck / lounge", use="pool_hall",
                             classification="support",
                             target_area_m2=round(1500 * FT2_TO_M2, 4)),
                        basement.id, 0.0, 0.0, 12.0, D))
    spaces.append(_rect(dict(name="Pool plant / mechanical", use="plant",
                             classification="support",
                             target_area_m2=round(400 * FT2_TO_M2, 4)),
                        basement.id, 12.0, 0.0, 6.0, 6.2))
    spaces.append(_rect(dict(name="Changing / shower / WC", use="changing",
                             classification="support",
                             target_area_m2=round(250 * FT2_TO_M2, 4)),
                        basement.id, 12.0, 6.2, 6.0, 3.9))
    spaces.append(_rect(dict(name="Storage", use="storage",
                             classification="support",
                             target_area_m2=round(250 * FT2_TO_M2, 4)),
                        basement.id, 12.0, 10.1, 6.0, 5.4))
    # roof terrace zone (separately tracked, not an enclosed room)
    spaces.append(_rect(dict(name="Occupied roof terrace", use="roof_terrace",
                             classification="support",
                             target_area_m2=round(900 * FT2_TO_M2, 4)),
                        roof.id, 0.0, 0.0, 9.0, 9.29))

    snap = ProjectSnapshot(
        project_id=project_id,
        brief=Brief(),
        site=SiteContext(),
        levels=[basement, ground, upper, roof],
        spaces=spaces,
        pool=PoolSystem(level_id=basement.id),
        roof_terrace_area_m2=round(900 * FT2_TO_M2, 4),
        assumptions=[
            Assumption(field="floor_to_floor_height_m", value=3.4,
                       rationale="Demonstration concept height; legal classification not determined."),
            Assumption(field="basement_elevation_m", value=-3.2,
                       rationale="Local reference elevation for concept generation only."),
            Assumption(field="pool.water_dimensions_m", value=[8.0, 3.5, 1.4],
                       rationale="Spec A3.2 flat-bottom conceptual pool; editable."),
            Assumption(field="site.context_m", value=[30.0, 45.0],
                       rationale="Synthetic Demo Villa NYC-01 context; not a surveyed lot."),
        ],
    )
    return snap.with_hash()
