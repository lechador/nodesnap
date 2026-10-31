"""Synthetic copy of the original 0.1 villa grammar (7057a1d), not customer data.

Kept independent of the current seed builder so a modern seed cannot hide a
backwards-compatibility regression. No runtime Git dependency.
"""
from datetime import datetime, timezone

from domain.architecture import rect, stable_id
from domain.models import Assumption, FT2_TO_M2, Level, PoolSystem, ProjectSnapshot, Space


def build_legacy_villa(project_id: str) -> ProjectSnapshot:
    levels = [Level(id=stable_id(project_id, name), name=name, label=label, elevation_m=elevation)
              for name, label, elevation in [("basement", "Basement", -3.2), ("ground", "Ground floor", 0),
                                            ("upper", "Upper floor", 3.4), ("roof", "Roof / terrace", 6.8)]]
    by_name = {level.name: level for level in levels}
    spaces = []

    def add(level, name, use, classification, polygon, target=None):
        spaces.append(Space(id=stable_id(project_id, f"{level}:{name}"), level_id=by_name[level].id,
                            name=name, use=use, classification=classification, polygon=polygon,
                            target_area_m2=round(target*FT2_TO_M2, 4) if target is not None else None))

    programs = {
        "ground": ([("Main living room", "living", 620), ("Dining room", "dining", 300), ("Kitchen", "kitchen", 340),
                    ("Family lounge", "family", 360), ("Study / home office", "study", 200), ("Guest bedroom", "bedroom", 260)],
                   [("Bathrooms / WCs", "bathroom", 180), ("Pantry / laundry", "service", 120)]),
        "upper": ([("Primary bedroom", "bedroom", 420), ("Bedroom 2", "bedroom", 260), ("Bedroom 3", "bedroom", 240),
                   ("Bedroom 4", "bedroom", 240), ("Library / lounge", "library", 380), ("Flexible studio / fitness", "studio", 300)],
                  [("Dressing spaces", "dressing", 300), ("Bathrooms", "bathroom", 360)]),
    }
    for level, (principal, support) in programs.items():
        for rooms, y in ((principal[:3], 8.55), (principal[3:], 0)):
            x = 0.0
            total = sum(target for _, _, target in rooms)
            for name, use, target in rooms:
                width = 15*target/total
                add(level, name, use, "principal", rect(x, y, width, 6.95), target)
                x += width
        add(level, "Circulation", "circulation", "support", rect(0, 6.95, 15, 1.6))
        add(level, "Stairs / service core", "stairs_service", "support", rect(15, 0, 3, 5.5))
        sy = 5.5
        for name, use, target in support:
            height = min(max(1.8, target*FT2_TO_M2/3), 15.5-sy)
            add(level, name, use, "support", rect(15, sy, 3, height), target)
            sy += height
    for name, use, dimensions, target in [
        ("Pool hall / deck / lounge", "pool_hall", (0, 0, 12, 15.5), 1500),
        ("Pool plant / mechanical", "plant", (12, 0, 6, 6.2), 400),
        ("Changing / shower / WC", "changing", (12, 6.2, 6, 3.9), 250),
        ("Storage", "storage", (12, 10.1, 6, 5.4), 250),
    ]:
        add("basement", name, use, "support", rect(*dimensions), target)
    add("roof", "Occupied roof terrace", "roof_terrace", "support", rect(0, 0, 9, 9.29), 900)
    snapshot = ProjectSnapshot(schema_version="0.1.0", project_id=project_id,
        revision_id=stable_id(project_id, "revision:original"),
        created_at=datetime(2026, 10, 30, tzinfo=timezone.utc), levels=levels, spaces=spaces,
        pool=PoolSystem(id=stable_id(project_id, "pool"), level_id=by_name["basement"].id),
        roof_terrace_area_m2=round(900*FT2_TO_M2, 4),
        assumptions=[Assumption(id=stable_id(project_id, "assumption:height"), field="floor_to_floor_height_m", value=3.4,
                                rationale="Demonstration concept height; legal classification not determined.")])
    return snapshot.with_hash()
