"""Original villa upgrade preserves saved work and creates a connected revision."""
import copy

import pytest
from shapely.geometry import Polygon

from domain.architecture import enrich_snapshot, rect
from domain.commands import CommandError, apply_commands
from domain.legacy import upgrade_legacy_architecture
from domain.models import new_id
from geometry.validate import validate_snapshot
from fixtures.legacy_villa import build_legacy_villa


def test_original_villa_upgrade_is_immutable_and_preserves_every_existing_identity():
    original = build_legacy_villa(new_id())
    original.title = "My retained villa"
    original.pool.water_length_m = 11
    original.pool.origin_x_m = .5
    original.pool.origin_y_m = 6
    original.with_hash()
    before = original.model_dump_json()
    upgraded = apply_commands(original, [{"type": "upgrade_architecture"}])
    assert original.model_dump_json() == before
    assert original.architecture is None and original.schema_version == "0.1.0"
    assert upgraded.parent_revision_id == original.revision_id
    assert upgraded.revision_number == 2
    assert upgraded.content_hash == upgraded.compute_hash() != original.content_hash
    assert upgraded.architecture.revision_id == upgraded.revision_id
    assert upgraded.schema_version == "0.2.0"
    for field in ("project_id", "title", "site", "brief", "levels", "pool", "roof_terrace_area_m2", "material_palette"):
        assert getattr(upgraded, field) == getattr(original, field), field
    previous = {space.id: space for space in original.spaces}
    current = {space.id: space for space in upgraded.spaces}
    assert previous.keys() < current.keys()
    assert len(current)-len(previous) == 5
    for identifier, space in previous.items():
        assert space.model_dump(exclude={"polygon"}) == current[identifier].model_dump(exclude={"polygon"})
        if space.classification == "principal" or space.use in {"pool_hall", "roof_terrace"}:
            assert space.polygon == current[identifier].polygon
    assert upgraded.assumptions[:-1] == original.assumptions
    audit = upgraded.assumptions[-1]
    assert audit.field == "architecture.legacy_upgrade" and audit.review_status == "unreviewed"
    assert audit.value["base_revision_id"] == original.revision_id
    assert len(audit.value["changed_space_polygons"]) == 11
    for changed in audit.value["changed_space_polygons"]:
        identifier = changed["space_id"]
        assert changed["before"] == previous[identifier].polygon
        assert changed["after"] == current[identifier].polygon
    assert {space["id"] for space in audit.value["added_spaces"]} == current.keys()-previous.keys()
    assert validate_snapshot(upgraded) == []


def test_converted_levels_have_exact_plates_connected_stairs_and_stable_derived_ids():
    original = build_legacy_villa(new_id())
    one = apply_commands(original, [{"type": "upgrade_architecture"}])
    two = apply_commands(original, [{"type": "upgrade_architecture"}])
    assert {space.id for space in one.spaces} == {space.id for space in two.spaces}
    assert len(one.architecture.stairs) == 3
    assert {(stair.lower_level_id, stair.upper_level_id) for stair in one.architecture.stairs} == {
        (lower.id, upper.id) for lower, upper in zip(one.levels, one.levels[1:])}
    for level in one.levels[:-1]:
        polygons = [Polygon(space.polygon) for space in one.spaces if space.level_id == level.id]
        assert sum(polygon.area for polygon in polygons) == pytest.approx(279)
    for field in ("walls", "openings", "slabs", "stairs"):
        assert {entity.id for entity in getattr(one.architecture, field)} == {entity.id for entity in getattr(two.architecture, field)}
    assert validate_snapshot(one) == []
    assert validate_snapshot(two) == []


def test_principal_width_and_metadata_edits_survive_and_level_addition_works():
    original = build_legacy_villa(new_id())
    ground = next(level for level in original.levels if level.name == "ground")
    north = sorted([space for space in original.spaces if space.level_id == ground.id
                    and space.classification == "principal" and min(p[1] for p in space.polygon) > 8],
                   key=lambda space: min(p[0] for p in space.polygon))
    boundary = max(p[0] for p in north[0].polygon)
    for space in north[:2]:
        space.polygon = [[x+.2 if abs(x-boundary) < 1e-7 else x, y] for x, y in space.polygon]
    north[0].name = "Edited living room"
    north[0].target_area_m2 = 75
    original.with_hash()
    upgraded = apply_commands(original, [{"type": "upgrade_architecture"}])
    added = apply_commands(upgraded, [{"type": "add_level"}])
    assert added.brief.floors_above_ground == 3
    assert len(added.architecture.stairs) == 4
    assert added.pool == original.pool
    assert next(space for space in added.spaces if space.id == north[0].id) == north[0]
    assert validate_snapshot(added) == []


@pytest.mark.parametrize("edit", [
    "service_move", "principal_move", "extra_room", "custom_envelope", "nonrectangular", "pool_overlap",
    "missing_pool", "roof_move", "duplicate_level", "wrong_height", "already_architectural",
])
def test_unrecognized_or_unsafe_legacy_layout_is_rejected_without_any_mutation(edit):
    snapshot = build_legacy_villa(new_id())
    if edit == "service_move":
        space = next(space for space in snapshot.spaces if space.use == "plant")
        space.polygon = rect(12.1, 0, 5.9, 6.2)
    elif edit == "principal_move":
        space = next(space for space in snapshot.spaces if space.classification == "principal")
        space.polygon = [[x+.1, y] for x, y in space.polygon]
    elif edit == "extra_room":
        snapshot.spaces.append(snapshot.spaces[0].model_copy(update={"id":new_id()}))
    elif edit == "custom_envelope":
        snapshot.envelope_polygon = rect(0, 0, 20, 20)
    elif edit == "nonrectangular":
        snapshot.spaces[0].polygon[1][0] -= .1
    elif edit == "pool_overlap":
        snapshot.pool.water_length_m = 11
    elif edit == "missing_pool":
        snapshot.pool = None
    elif edit == "roof_move":
        space = next(space for space in snapshot.spaces if space.use == "roof_terrace")
        space.polygon = [[x+.1,y] for x,y in space.polygon]
    elif edit == "duplicate_level":
        snapshot.levels[1].id = snapshot.levels[0].id
    elif edit == "wrong_height":
        snapshot.levels[-1].elevation_m = 4
    else:
        enrich_snapshot(snapshot)
    before = snapshot.model_dump_json()
    with pytest.raises(ValueError, match="has not been replaced"):
        upgrade_legacy_architecture(snapshot)
    assert snapshot.model_dump_json() == before
    with pytest.raises(CommandError):
        apply_commands(snapshot, [{"type": "upgrade_architecture"}])
    assert snapshot.model_dump_json() == before


def test_conversion_audit_keeps_independent_before_polygons():
    snapshot = build_legacy_villa(new_id())
    before = copy.deepcopy(snapshot.spaces)
    upgrade_legacy_architecture(snapshot)
    audit = snapshot.assumptions[-1].value["changed_space_polygons"]
    by_id = {space.id: space for space in before}
    assert all(change["before"] == by_id[change["space_id"]].polygon for change in audit)
    assert all(change["before"] != change["after"] for change in audit)
